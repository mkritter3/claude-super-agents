#!/usr/bin/env python3
"""
Orchestrator Bridge - Connects Operational Orchestrator to Parallel Executor
This bridges the gap between trigger files and the parallel execution queue
Part of the architectural fix for Phase 1.1
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Import both systems we're bridging
from parallel_executor import ParallelExecutor, TaskPriority
from operational_orchestrator import OperationalOrchestrator
from agent_dependency_graph import AgentDependencyGraph

@dataclass
class AgentTaskMapping:
    """Maps trigger types to parallel executor tasks"""
    agent: str
    task_type: str
    priority: TaskPriority
    params: Dict[str, Any]

class OrchestratorBridge:
    """
    Bridges the Operational Orchestrator with the Parallel Executor
    Converts trigger events into queued tasks for parallel execution
    """
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        
        # Initialize both systems
        self.orchestrator = OperationalOrchestrator(self.project_dir)
        self.executor = ParallelExecutor(self.project_dir)
        self.dependency_graph = AgentDependencyGraph(self.project_dir)
        
        # Setup logging
        self._setup_logging()
        
        # Track processed triggers to avoid duplicates
        self.processed_triggers = set()
        
    def _setup_logging(self):
        """Setup bridge logger"""
        log_dir = self.claude_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("OrchestratorBridge")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_dir / "orchestrator_bridge.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        
    def process_event(self, event: Dict[str, Any]) -> List[str]:
        """
        Process an event and submit appropriate tasks to parallel executor
        Returns list of submitted task IDs
        """
        event_type = event.get('event_type')
        task_ids = []
        
        self.logger.info(f"Processing event: {event_type}")
        
        # Determine which agents should run based on event
        agents_to_run = self._determine_agents(event)
        
        # Get optimal execution order from dependency graph
        if agents_to_run:
            execution_order = self.dependency_graph.get_execution_order(agents_to_run)
            
            # Submit tasks level by level (preserving dependencies)
            previous_level_ids = []
            
            for level in execution_order:
                level_task_ids = []
                
                for agent in level:
                    # Create task with dependencies on previous level
                    task_id = self._submit_agent_task(
                        agent=agent,
                        event=event,
                        dependencies=previous_level_ids
                    )
                    
                    if task_id:
                        level_task_ids.append(task_id)
                        task_ids.append(task_id)
                        
                previous_level_ids = level_task_ids
                
        self.logger.info(f"Submitted {len(task_ids)} tasks for event {event_type}")
        return task_ids
        
    def _determine_agents(self, event: Dict[str, Any]) -> List[str]:
        """Determine which agents should run based on event type and data"""
        agents = []
        event_type = event.get('event_type')
        
        # Map event types to agents (consolidating logic from multiple places)
        if event_type == 'CODE_COMMITTED':
            files = event.get('data', {}).get('files_changed', [])
            
            # Always run for code changes
            agents.extend(['test-executor', 'documentation-agent'])
            
            # Conditional agents based on file types
            if any('.py' in f for f in files):
                agents.append('performance-optimizer-agent')
                
            if any('api' in f.lower() or 'schema' in f.lower() for f in files):
                agents.append('contract-guardian')
                
            if any('migration' in f or '.sql' in f for f in files):
                agents.extend(['database-agent', 'data-migration-agent'])
                
            if any(f.startswith('src/frontend') or '.tsx' in f or '.jsx' in f for f in files):
                agents.extend(['frontend-agent', 'ux-agent'])
                
        elif event_type == 'DEPLOYMENT_INITIATED':
            agents.extend(['monitoring-agent', 'security-agent', 'devops-agent'])
            
        elif event_type == 'ERROR_SPIKE_DETECTED':
            agents.append('incident-response-agent')
            
        elif event_type == 'REQUIREMENTS_UPDATED':
            agents.extend(['product-agent', 'pm-agent', 'architect-agent'])
            
        # Remove duplicates while preserving order
        seen = set()
        unique_agents = []
        for agent in agents:
            if agent not in seen:
                seen.add(agent)
                unique_agents.append(agent)
                
        return unique_agents
        
    def _submit_agent_task(self, agent: str, event: Dict[str, Any],
                          dependencies: List[str] = None) -> Optional[str]:
        """Submit a single agent task to the parallel executor"""
        
        # Determine priority based on agent
        priority_map = {
            'contract-guardian': TaskPriority.CRITICAL,
            'security-agent': TaskPriority.CRITICAL,
            'incident-response-agent': TaskPriority.CRITICAL,
            'test-executor': TaskPriority.HIGH,
            'data-migration-agent': TaskPriority.HIGH,
            'developer-agent': TaskPriority.NORMAL,
            'architect-agent': TaskPriority.NORMAL,
            'documentation-agent': TaskPriority.LOW,
            'performance-optimizer-agent': TaskPriority.LOW,
        }
        
        priority = priority_map.get(agent, TaskPriority.NORMAL)
        
        # Build task parameters
        params = {
            'event_type': event.get('event_type'),
            'event_data': event.get('data', {}),
            'timestamp': event.get('timestamp', time.time()),
            'triggered_by': 'orchestrator_bridge'
        }
        
        # Submit to parallel executor
        try:
            task_id = self.executor.submit_task(
                agent=agent,
                params=params,
                priority=priority,
                dependencies=dependencies
            )
            
            self.logger.info(f"Submitted task {task_id} for agent {agent} with priority {priority.name}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit task for {agent}: {e}")
            return None
            
    def process_trigger_files(self):
        """
        Process existing trigger files and convert them to tasks
        This provides backward compatibility during transition
        """
        trigger_dir = self.claude_dir / "triggers"
        processed_count = 0
        
        for trigger_file in trigger_dir.glob("*_trigger_*.json"):
            # Skip if already processed
            if trigger_file.name in self.processed_triggers:
                continue
                
            try:
                with open(trigger_file, 'r') as f:
                    trigger_data = json.load(f)
                    
                # Extract agent from filename
                agent = trigger_file.stem.split('_trigger_')[0]
                
                # Submit as task
                task_id = self.executor.submit_task(
                    agent=agent,
                    params=trigger_data,
                    priority=TaskPriority.NORMAL
                )
                
                # Mark as processed
                self.processed_triggers.add(trigger_file.name)
                processed_count += 1
                
                # Optionally archive the trigger file
                archive_dir = self.claude_dir / "triggers" / "archived"
                archive_dir.mkdir(exist_ok=True)
                trigger_file.rename(archive_dir / trigger_file.name)
                
                self.logger.info(f"Processed trigger file {trigger_file.name} → task {task_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to process trigger {trigger_file}: {e}")
                
        if processed_count > 0:
            self.logger.info(f"Processed {processed_count} trigger files into task queue")
            
    def monitor_events(self):
        """
        Monitor event log and submit tasks for new events
        This replaces the multiple monitoring systems
        """
        event_log = self.claude_dir / "events" / "log.ndjson"
        processed_position = 0
        
        self.logger.info("Starting event monitor...")
        
        while True:
            try:
                # Check for new events
                if event_log.exists():
                    with open(event_log, 'r') as f:
                        # Skip to last position
                        f.seek(processed_position)
                        
                        for line in f:
                            if line.strip():
                                try:
                                    event = json.loads(line)
                                    # Process event and submit tasks
                                    self.process_event(event)
                                except json.JSONDecodeError:
                                    self.logger.warning(f"Invalid JSON in event log: {line}")
                                    
                        # Update position
                        processed_position = f.tell()
                        
                # Also process any legacy trigger files
                self.process_trigger_files()
                
                # Sleep before next check
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Event monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Event monitor error: {e}")
                time.sleep(5)  # Wait longer on error


def main():
    """CLI interface for the orchestrator bridge"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrator Bridge")
    parser.add_argument('--monitor', action='store_true',
                       help='Start monitoring events and submitting tasks')
    parser.add_argument('--process-triggers', action='store_true',
                       help='Process existing trigger files')
    parser.add_argument('--test-event', metavar='TYPE',
                       help='Submit a test event (e.g., CODE_COMMITTED)')
    
    args = parser.parse_args()
    
    bridge = OrchestratorBridge()
    
    if args.monitor:
        print("Starting Orchestrator Bridge monitor...")
        print("This connects events to the parallel executor")
        print("Press Ctrl+C to stop")
        bridge.monitor_events()
        
    elif args.process_triggers:
        print("Processing existing trigger files...")
        bridge.process_trigger_files()
        print("Done!")
        
    elif args.test_event:
        # Create a test event
        test_event = {
            'timestamp': time.time(),
            'event_type': args.test_event,
            'data': {
                'files_changed': ['src/test.py', 'tests/test_test.py'],
                'test': True
            }
        }
        
        print(f"Processing test event: {args.test_event}")
        task_ids = bridge.process_event(test_event)
        print(f"Submitted tasks: {task_ids}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()