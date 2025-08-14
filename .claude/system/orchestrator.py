#!/usr/bin/env python3
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from event_logger import EventLogger
from workspace_manager import WorkspaceManager
from logger_config import get_contextual_logger, log_system_event

class TaskOrchestrator:
    def __init__(self):
        self.event_logger = EventLogger()
        self.workspace_manager = WorkspaceManager()
        self.snapshot_path = Path(".claude/snapshots/tasks.json")
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_contextual_logger("orchestrator", component="orchestrator")
        
        # State transitions
        self.transitions = {
            "CREATED": ("pm-agent", "PLANNING"),
            "PLANNING": ("architect-agent", "DESIGNING"),
            "DESIGNING": ("developer-agent", "IMPLEMENTING"),
            "IMPLEMENTING": ("reviewer-agent", "REVIEWING"),
            "REVIEWING": ("qa-agent", "TESTING"),
            "TESTING": ("integrator-agent", "INTEGRATING"),
            "INTEGRATING": (None, "COMPLETED")
        }
    
    def load_snapshots(self) -> Dict[str, Dict]:
        """Load task snapshots from disk."""
        if not self.snapshot_path.exists():
            return {}
        
        with open(self.snapshot_path, 'r') as f:
            return json.load(f)
    
    def save_snapshot(self, ticket_id: str, snapshot: Dict):
        """Save task snapshot atomically."""
        snapshots = self.load_snapshots()
        snapshots[ticket_id] = snapshot
        
        # Atomic write
        temp_path = self.snapshot_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(snapshots, f, indent=2)
        
        temp_path.rename(self.snapshot_path)
    
    def create_task(self, ticket_id: str, prompt: str) -> str:
        """Create new task with workspace."""
        # Create workspace
        job_id = self.workspace_manager.create_workspace(ticket_id, prompt)
        
        # Log event
        event_id = self.event_logger.append_event(
            ticket_id=ticket_id,
            event_type="TASK_CREATED",
            payload={"prompt": prompt, "job_id": job_id}
        )
        
        # Create snapshot
        snapshot = {
            "ticket_id": ticket_id,
            "job_id": job_id,
            "status": "CREATED",
            "current_agent": "",
            "last_event_id": event_id,
            "retry_count": 0,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        
        self.save_snapshot(ticket_id, snapshot)
        
        return job_id
    
    def build_context_bundle(self, ticket_id: str, job_id: str, agent_name: str) -> Dict:
        """Build intelligent context bundle using the Context Assembler.
        THIS USES THE CONTEXT INTEGRATION LAYER!
        """
        
        # Initialize context assembler if not exists
        if not hasattr(self, 'context_assembler'):
            from context_assembler import ContextAssembler
            self.context_assembler = ContextAssembler()
        
        # Get intelligent context (THIS IS THE KEY CHANGE!)
        context = self.context_assembler.assemble_intelligent_context(
            ticket_id=ticket_id,
            job_id=job_id,
            agent_type=agent_name,
            max_tokens=50000  # Adjust based on model
        )
        
        # Add the original prompt (immutable)
        manifest_path = Path(f".claude/workspaces/{job_id}/manifest.json")
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        context['original_prompt'] = manifest['original_prompt']
        context['current_status'] = manifest['status']
        
        return context
    
    def _load_conventions(self) -> Dict:
        """Load project conventions from config."""
        config_path = Path(".claude/config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get("conventions", {})
        return {}
    
    def invoke_agent(self, agent_name: str, context: Dict) -> Tuple[bool, Dict]:
        """Request Claude to delegate to subagent."""
        # Write context to workspace for agent to discover
        context_file = Path(f"{context['workspace']['path']}/../context.json")
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)
        
        # Log delegation request
        self.event_logger.append_event(
            ticket_id=context['workspace']['ticket_id'],
            event_type="AGENT_DELEGATION_REQUEST",
            payload={
                "agent": agent_name,
                "context_file": str(context_file)
            }
        )
        
        # Request delegation to subagent
        self.logger.info("Delegation request", extra={
            'agent_name': agent_name,
            'context_file': str(context_file),
            'workspace_path': context['workspace']['path'],
            'artifacts_path': context['workspace']['artifacts'],
            'delegation_instructions': {
                'read_context_from': str(context_file),
                'workspace_path': context['workspace']['path'],
                'artifacts_path': context['workspace']['artifacts'],
                'completion_event_path': '.claude/events/log.ndjson',
                'invoke_command': f'Use {agent_name} to process this task'
            }
        })
        
        log_system_event("task_delegated", {
            "agent_name": agent_name,
            "workspace_path": context['workspace']['path']
        }, ticket_id=context['workspace']['ticket_id'], component="orchestrator")
        
        # For now, return success and wait for manual confirmation
        # In production, this could monitor the event log for completion
        return True, {"status": "delegation_requested", "agent": agent_name}
    
    def process_next_task(self) -> bool:
        """Process next pending task in queue."""
        snapshots = self.load_snapshots()
        
        # Find task to process
        for ticket_id, snapshot in snapshots.items():
            if snapshot["status"] in self.transitions:
                # Get next agent and status
                agent, next_status = self.transitions[snapshot["status"]]
                
                if agent is None:
                    # Task is complete
                    snapshot["status"] = next_status
                    self.save_snapshot(ticket_id, snapshot)
                    continue
                
                self.logger.info("Processing task", extra={'agent': agent})
                
                # Build context WITH AGENT TYPE
                context = self.build_context_bundle(
                    ticket_id, 
                    snapshot["job_id"],
                    agent  # Pass agent name for intelligent context assembly
                )
                
                # Log agent start
                event_id = self.event_logger.append_event(
                    ticket_id=ticket_id,
                    event_type="AGENT_STARTED",
                    payload={"agent": agent},
                    parent_event_id=snapshot["last_event_id"],
                    agent=agent
                )
                
                # Invoke agent
                success, output = self.invoke_agent(agent, context)
                
                if success:
                    # Checkpoint workspace
                    self.workspace_manager.checkpoint_workspace(
                        snapshot["job_id"],
                        f"Completed: {agent}"
                    )
                    
                    # Update snapshot
                    snapshot["status"] = next_status
                    snapshot["current_agent"] = ""
                    snapshot["last_event_id"] = event_id
                    snapshot["retry_count"] = 0
                    
                    # Log success
                    self.event_logger.append_event(
                        ticket_id=ticket_id,
                        event_type="AGENT_COMPLETED",
                        payload={"agent": agent, "output": str(output)[:1000]},
                        parent_event_id=event_id,
                        agent=agent
                    )
                else:
                    # Handle failure
                    snapshot["retry_count"] += 1
                    
                    if snapshot["retry_count"] >= 3:
                        snapshot["status"] = "FAILED"
                        self.logger.error("Task failed after retries", extra={'retry_count': retry_count})
                    
                    # Log failure
                    self.event_logger.append_event(
                        ticket_id=ticket_id,
                        event_type="AGENT_FAILED",
                        payload={"agent": agent, "error": str(output)},
                        parent_event_id=event_id,
                        agent=agent
                    )
                
                self.save_snapshot(ticket_id, snapshot)
                return True
        
        return False  # No tasks to process

if __name__ == "__main__":
    import sys
    orchestrator = TaskOrchestrator()
    
    if len(sys.argv) < 2:
        logger = get_contextual_logger("orchestrator", component="orchestrator")
        logger.info("Usage: orchestrator.py <command> [args...]")
        logger.info("Commands: create, process")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        job_id = orchestrator.create_task(sys.argv[2], sys.argv[3])
        logger = get_contextual_logger("orchestrator", job_id=job_id, component="orchestrator")
        logger.info("Job created successfully")
    elif command == "process":
        while orchestrator.process_next_task():
            time.sleep(1)  # Brief pause between tasks
        logger = get_contextual_logger("orchestrator", component="orchestrator")
        logger.info("No more tasks to process")