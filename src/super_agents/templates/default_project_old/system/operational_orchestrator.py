#!/usr/bin/env python3
"""
Operational Orchestrator - Autonomous operations management for AET

This orchestrator runs alongside the main orchestrator and handles:
- Continuous monitoring of system health
- Automatic triggering of operational agents
- Event-driven workflows
- Ambient intelligence operations
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OperationalState(Enum):
    """System operational states"""
    DEVELOPMENT = "development"
    REVIEW = "review"
    STAGING = "staging"
    PRODUCTION = "production"
    INCIDENT = "incident"
    MAINTENANCE = "maintenance"
    ROLLBACK = "rollback"

class EventSeverity(Enum):
    """Event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class OperationalEvent:
    """Represents an operational event"""
    event_id: str
    event_type: str
    severity: EventSeverity
    timestamp: float
    source: str
    data: Dict[str, Any]
    requires_action: bool = False
    
    def to_json(self) -> str:
        return json.dumps({
            **asdict(self),
            'severity': self.severity.value
        })

class OperationalTrigger:
    """Manages automatic agent triggers based on events"""
    
    TRIGGER_RULES = {
        "CODE_MERGED": ["monitoring-agent", "documentation-agent"],
        "SCHEMA_CHANGED": ["data-migration-agent", "contract-guardian"],
        "TEST_FAILED": ["incident-response-agent"],
        "PERFORMANCE_DEGRADED": ["performance-optimizer-agent"],
        "DEPLOYMENT_STARTED": ["monitoring-agent"],
        "ERROR_THRESHOLD_EXCEEDED": ["incident-response-agent"],
        "BACKUP_NEEDED": ["data-migration-agent"],
        "DOCUMENTATION_OUTDATED": ["documentation-agent"],
        "SECURITY_ALERT": ["incident-response-agent", "monitoring-agent"]
    }
    
    def get_agents_for_event(self, event_type: str) -> List[str]:
        """Get list of agents to trigger for an event type"""
        return self.TRIGGER_RULES.get(event_type, [])

class EventWatcher:
    """Watches for events from various sources"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.event_log = base_path / "events" / "log.ndjson"
        self.last_processed = 0
        self.watchers = {
            'filesystem': self.watch_filesystem,
            'git': self.watch_git,
            'logs': self.watch_logs,
            'metrics': self.watch_metrics
        }
    
    async def watch_filesystem(self) -> List[OperationalEvent]:
        """Watch for filesystem changes"""
        events = []
        
        # Check for schema changes
        migrations_dir = self.base_path.parent / "migrations"
        if migrations_dir.exists():
            for migration in migrations_dir.glob("*.sql"):
                if migration.stat().st_mtime > self.last_processed:
                    events.append(OperationalEvent(
                        event_id=f"evt_{int(time.time())}",
                        event_type="SCHEMA_CHANGED",
                        severity=EventSeverity.HIGH,
                        timestamp=time.time(),
                        source="filesystem",
                        data={"file": str(migration)},
                        requires_action=True
                    ))
        
        return events
    
    async def watch_git(self) -> List[OperationalEvent]:
        """Watch for git events"""
        events = []
        
        # Check for recent merges
        git_log = os.popen("git log --oneline -n 1 --since='1 minute ago'").read()
        if git_log:
            events.append(OperationalEvent(
                event_id=f"evt_{int(time.time())}",
                event_type="CODE_MERGED",
                severity=EventSeverity.MEDIUM,
                timestamp=time.time(),
                source="git",
                data={"commit": git_log.strip()},
                requires_action=True
            ))
        
        return events
    
    async def watch_logs(self) -> List[OperationalEvent]:
        """Watch application logs for errors"""
        events = []
        
        # Simulate log watching (in production, tail actual logs)
        error_log = self.base_path / "logs" / "errors.log"
        if error_log.exists():
            with open(error_log) as f:
                lines = f.readlines()
                error_count = sum(1 for line in lines if "ERROR" in line)
                if error_count > 10:  # Threshold
                    events.append(OperationalEvent(
                        event_id=f"evt_{int(time.time())}",
                        event_type="ERROR_THRESHOLD_EXCEEDED",
                        severity=EventSeverity.HIGH,
                        timestamp=time.time(),
                        source="logs",
                        data={"error_count": error_count},
                        requires_action=True
                    ))
        
        return events
    
    async def watch_metrics(self) -> List[OperationalEvent]:
        """Watch performance metrics"""
        events = []
        
        # Check performance metrics
        metrics_file = self.base_path / "metrics" / "performance.json"
        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics = json.load(f)
                if metrics.get("response_time_p95", 0) > 500:  # 500ms threshold
                    events.append(OperationalEvent(
                        event_id=f"evt_{int(time.time())}",
                        event_type="PERFORMANCE_DEGRADED",
                        severity=EventSeverity.HIGH,
                        timestamp=time.time(),
                        source="metrics",
                        data=metrics,
                        requires_action=True
                    ))
        
        return events
    
    async def check_all(self) -> List[OperationalEvent]:
        """Check all watchers for events"""
        all_events = []
        
        for watcher_name, watcher_func in self.watchers.items():
            try:
                events = await watcher_func()
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Error in {watcher_name} watcher: {e}")
        
        self.last_processed = time.time()
        return all_events

class OperationalWorkflow:
    """Defines and executes operational workflows"""
    
    WORKFLOWS = {
        "post_merge": [
            ("test-executor", "run_integration_tests"),
            ("monitoring-agent", "update_dashboards"),
            ("documentation-agent", "regenerate_api_docs"),
            ("performance-optimizer-agent", "baseline_performance")
        ],
        
        "incident_detected": [
            ("incident-response-agent", "triage"),
            ("monitoring-agent", "gather_metrics"),
            ("performance-optimizer-agent", "analyze_bottlenecks"),
            ("documentation-agent", "update_runbook")
        ],
        
        "schema_change": [
            ("contract-guardian", "validate_change"),
            ("data-migration-agent", "generate_migration"),
            ("test-executor", "test_migration"),
            ("documentation-agent", "update_schema_docs")
        ],
        
        "deployment": [
            ("monitoring-agent", "setup_monitoring"),
            ("documentation-agent", "update_deployment_docs"),
            ("performance-optimizer-agent", "establish_baseline")
        ],
        
        "performance_issue": [
            ("performance-optimizer-agent", "profile_application"),
            ("monitoring-agent", "detailed_metrics"),
            ("documentation-agent", "document_optimization")
        ]
    }
    
    def get_workflow(self, trigger: str) -> List[tuple]:
        """Get workflow steps for a trigger"""
        return self.WORKFLOWS.get(trigger, [])

class AmbientOperations:
    """Operations that happen without explicit user requests"""
    
    AMBIENT_RULES = [
        {
            "name": "auto_backup",
            "condition": lambda ctx: time.time() - ctx.get("last_backup", 0) > 86400,
            "action": "create_backup",
            "silent": True,
            "agents": ["data-migration-agent"]
        },
        {
            "name": "schema_validation",
            "condition": lambda ctx: ctx.get("schema_changed", False),
            "action": "validate_schema",
            "silent": False,
            "agents": ["contract-guardian", "data-migration-agent"]
        },
        {
            "name": "performance_monitoring",
            "condition": lambda ctx: ctx.get("in_production", False),
            "action": "continuous_monitoring",
            "silent": True,
            "agents": ["monitoring-agent", "performance-optimizer-agent"]
        },
        {
            "name": "documentation_sync",
            "condition": lambda ctx: ctx.get("code_changes", 0) > 5,
            "action": "update_docs",
            "silent": True,
            "agents": ["documentation-agent"]
        },
        {
            "name": "security_scan",
            "condition": lambda ctx: time.time() - ctx.get("last_security_scan", 0) > 3600,
            "action": "security_audit",
            "silent": False,
            "agents": ["incident-response-agent"]
        }
    ]
    
    def check_rules(self, context: Dict) -> List[Dict]:
        """Check which ambient rules should fire"""
        triggered_rules = []
        
        for rule in self.AMBIENT_RULES:
            if rule["condition"](context):
                triggered_rules.append(rule)
        
        return triggered_rules

class OperationalStateMachine:
    """Manages operational state transitions"""
    
    STATES = {
        OperationalState.DEVELOPMENT: {
            "allowed_agents": ["developer-agent", "test-executor"],
            "next_states": [OperationalState.REVIEW]
        },
        OperationalState.REVIEW: {
            "allowed_agents": ["reviewer-agent", "contract-guardian"],
            "next_states": [OperationalState.STAGING, OperationalState.DEVELOPMENT]
        },
        OperationalState.STAGING: {
            "allowed_agents": ["data-migration-agent", "monitoring-agent", "test-executor"],
            "next_states": [OperationalState.PRODUCTION, OperationalState.REVIEW]
        },
        OperationalState.PRODUCTION: {
            "allowed_agents": ["incident-response-agent", "performance-optimizer-agent", "monitoring-agent"],
            "next_states": [OperationalState.INCIDENT, OperationalState.MAINTENANCE]
        },
        OperationalState.INCIDENT: {
            "allowed_agents": ["incident-response-agent", "monitoring-agent"],
            "auto_trigger": True,
            "next_states": [OperationalState.PRODUCTION, OperationalState.ROLLBACK]
        },
        OperationalState.ROLLBACK: {
            "allowed_agents": ["data-migration-agent", "incident-response-agent"],
            "auto_trigger": True,
            "next_states": [OperationalState.PRODUCTION, OperationalState.STAGING]
        }
    }
    
    def __init__(self):
        self.current_state = OperationalState.DEVELOPMENT
        self.state_history = []
    
    def can_transition_to(self, new_state: OperationalState) -> bool:
        """Check if transition to new state is allowed"""
        allowed_states = self.STATES[self.current_state]["next_states"]
        return new_state in allowed_states
    
    def transition_to(self, new_state: OperationalState) -> bool:
        """Transition to a new state"""
        if self.can_transition_to(new_state):
            self.state_history.append({
                "from": self.current_state,
                "to": new_state,
                "timestamp": time.time()
            })
            self.current_state = new_state
            logger.info(f"State transition: {self.state_history[-1]['from']} -> {new_state}")
            return True
        return False
    
    def get_allowed_agents(self) -> List[str]:
        """Get agents allowed in current state"""
        return self.STATES[self.current_state]["allowed_agents"]

class OperationalOrchestrator:
    """Main operational orchestrator"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.event_watcher = EventWatcher(base_path)
        self.trigger_manager = OperationalTrigger()
        self.workflow_manager = OperationalWorkflow()
        self.ambient_ops = AmbientOperations()
        self.state_machine = OperationalStateMachine()
        
        # Initialize paths
        self.ensure_directories()
        
        # Load context
        self.context = self.load_context()
        
        # Task queue
        self.task_queue = asyncio.Queue()
        self.running = False
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        dirs = [
            self.base_path / "events",
            self.base_path / "triggers",
            self.base_path / "state",
            self.base_path / "logs",
            self.base_path / "metrics",
            self.base_path / "workspaces" / "operational"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def load_context(self) -> Dict:
        """Load operational context"""
        context_file = self.base_path / "state" / "operational_context.json"
        if context_file.exists():
            with open(context_file) as f:
                return json.load(f)
        return {
            "last_backup": 0,
            "last_security_scan": 0,
            "code_changes": 0,
            "in_production": False,
            "schema_changed": False
        }
    
    def save_context(self):
        """Save operational context"""
        context_file = self.base_path / "state" / "operational_context.json"
        with open(context_file, 'w') as f:
            json.dump(self.context, f, indent=2)
    
    async def process_event(self, event: OperationalEvent):
        """Process a single operational event"""
        logger.info(f"Processing event: {event.event_type} (severity: {event.severity.value})")
        
        # Get agents to trigger
        agents = self.trigger_manager.get_agents_for_event(event.event_type)
        
        # Check if agents are allowed in current state
        allowed_agents = self.state_machine.get_allowed_agents()
        agents = [a for a in agents if a in allowed_agents]
        
        if agents:
            # Create task for each agent
            for agent in agents:
                task = {
                    "agent": agent,
                    "event": event,
                    "timestamp": time.time()
                }
                await self.task_queue.put(task)
                logger.info(f"Queued task for {agent}")
        
        # Log event
        with open(self.base_path / "events" / "operational.ndjson", 'a') as f:
            f.write(event.to_json() + "\n")
    
    async def execute_task(self, task: Dict):
        """Execute a task by triggering an agent"""
        agent = task["agent"]
        event = task["event"]
        
        # Create trigger file for orchestrator to pick up
        trigger_file = self.base_path / "triggers" / f"{agent}_{int(time.time())}.json"
        trigger_data = {
            "agent": agent,
            "event": asdict(event),
            "context": self.context,
            "state": self.state_machine.current_state.value
        }
        
        with open(trigger_file, 'w') as f:
            json.dump(trigger_data, f, indent=2)
        
        logger.info(f"Created trigger for {agent}: {trigger_file}")
    
    async def check_ambient_operations(self):
        """Check and execute ambient operations"""
        triggered_rules = self.ambient_ops.check_rules(self.context)
        
        for rule in triggered_rules:
            if not rule["silent"]:
                logger.info(f"Ambient operation triggered: {rule['name']}")
            
            # Create tasks for ambient agents
            for agent in rule["agents"]:
                task = {
                    "agent": agent,
                    "event": OperationalEvent(
                        event_id=f"ambient_{int(time.time())}",
                        event_type=f"AMBIENT_{rule['name'].upper()}",
                        severity=EventSeverity.LOW,
                        timestamp=time.time(),
                        source="ambient",
                        data={"rule": rule["name"]},
                        requires_action=False
                    ),
                    "timestamp": time.time()
                }
                await self.task_queue.put(task)
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Check for events
                events = await self.event_watcher.check_all()
                for event in events:
                    await self.process_event(event)
                
                # Check ambient operations
                await self.check_ambient_operations()
                
                # Process task queue
                while not self.task_queue.empty():
                    task = await self.task_queue.get()
                    await self.execute_task(task)
                
                # Save context
                self.save_context()
                
                # Sleep before next check
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def start(self):
        """Start the operational orchestrator"""
        logger.info("Starting Operational Orchestrator")
        self.running = True
        
        # Start monitoring loop
        await self.monitor_loop()
    
    def stop(self):
        """Stop the operational orchestrator"""
        logger.info("Stopping Operational Orchestrator")
        self.running = False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Operational Orchestrator for AET")
    parser.add_argument("--base-path", default=".claude", help="Base path for AET system")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    args = parser.parse_args()
    
    base_path = Path(args.base_path)
    orchestrator = OperationalOrchestrator(base_path)
    
    try:
        asyncio.run(orchestrator.start())
    except KeyboardInterrupt:
        orchestrator.stop()
        logger.info("Orchestrator stopped by user")

if __name__ == "__main__":
    main()