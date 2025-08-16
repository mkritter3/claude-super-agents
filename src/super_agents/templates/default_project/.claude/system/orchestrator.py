#!/usr/bin/env python3
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from event_logger import EventLogger
from workspace_manager import WorkspaceManager
from logger_config import get_contextual_logger, log_system_event
from hallucination_guard import HallucinationGuard, VerificationLevel, create_hallucination_resistant_prompt

class TaskOrchestrator:
    def __init__(self):
        self.event_logger = EventLogger()
        self.workspace_manager = WorkspaceManager()
        self.hallucination_guard = HallucinationGuard()
        self.snapshot_path = Path(".claude/snapshots/tasks.json")
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_contextual_logger("orchestrator", component="orchestrator")
        
        # State transitions
        self.transitions = {
            # Original backend-focused workflow
            "CREATED": ("pm-agent", "PLANNING"),
            "PLANNING": ("architect-agent", "DESIGNING"),
            "DESIGNING": ("developer-agent", "IMPLEMENTING"),
            "IMPLEMENTING": ("reviewer-agent", "REVIEWING"),
            "REVIEWING": ("test-executor", "TESTING"),
            "TESTING": ("integrator-agent", "INTEGRATING"),
            "INTEGRATING": (None, "COMPLETED"),
            
            # Full-stack workflow transitions
            "PRODUCT_PLANNING": ("product-agent", "UX_DESIGN"),
            "UX_DESIGN": ("ux-agent", "ARCHITECTURE"),
            "ARCHITECTURE": ("architect-agent", "FRONTEND_DEV"),
            "FRONTEND_DEV": ("frontend-agent", "BACKEND_DEV"),
            "BACKEND_DEV": ("developer-agent", "DATABASE_DESIGN"),
            "DATABASE_DESIGN": ("database-agent", "SECURITY_REVIEW"),
            "SECURITY_REVIEW": ("security-agent", "TESTING"),
            "DEVOPS_PREP": ("devops-agent", "INTEGRATION"),
            "INTEGRATION": ("integrator-agent", "COMPLETED"),
            
            # Specialized workflows
            "FRONTEND_ONLY": ("frontend-agent", "UX_VALIDATION"),
            "UX_VALIDATION": ("ux-agent", "TESTING"),
            "DATABASE_ONLY": ("database-agent", "MIGRATION_PLANNING"),
            "MIGRATION_PLANNING": ("data-migration-agent", "TESTING"),
            "SECURITY_ONLY": ("security-agent", "COMPLIANCE_CHECK"),
            "COMPLIANCE_CHECK": ("contract-guardian", "COMPLETED"),
            "DEVOPS_ONLY": ("devops-agent", "MONITORING_SETUP"),
            "MONITORING_SETUP": ("monitoring-agent", "COMPLETED")
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
    
    def _detect_operation_type(self, context: Dict) -> str:
        """Detect the type of operation based on context."""
        original_prompt = context.get('original_prompt', '').lower()
        
        # Critical operations
        if any(keyword in original_prompt for keyword in ['schema', 'migration', 'database']):
            return "schema_changes"
        if any(keyword in original_prompt for keyword in ['api', 'endpoint', 'interface']):
            return "api_modifications"
        if any(keyword in original_prompt for keyword in ['security', 'auth', 'permission']):
            return "security_updates"
        if any(keyword in original_prompt for keyword in ['deploy', 'infrastructure', 'docker']):
            return "deployment_configs"
        
        # Standard operations
        if any(keyword in original_prompt for keyword in ['review', 'analyze', 'audit']):
            return "review"
        if any(keyword in original_prompt for keyword in ['plan', 'design', 'architecture']):
            return "planning"
        if any(keyword in original_prompt for keyword in ['implement', 'code', 'develop']):
            return "code_changes"
        
        return "general"
    
    def _get_verification_instructions(self, verification_level: VerificationLevel) -> str:
        """Get verification instructions for the agent."""
        instructions_map = {
            VerificationLevel.BASIC: "Say 'I don't know' if uncertain. Base responses on provided context only.",
            VerificationLevel.EVIDENCE: "Provide direct quotes from files as evidence for all factual claims.",
            VerificationLevel.CONSENSUS: "Show step-by-step reasoning and rate confidence levels.",
            VerificationLevel.CRITICAL: "CRITICAL: Every claim needs file evidence. Retract unsupported claims."
        }
        return instructions_map.get(verification_level, instructions_map[VerificationLevel.BASIC])
    
    def invoke_agent(self, agent_name: str, context: Dict) -> Tuple[bool, Dict]:
        """Request Claude to delegate to subagent with hallucination protection."""
        
        # Determine verification level based on agent and operation
        ticket_id = context['workspace']['ticket_id']
        operation_type = self._detect_operation_type(context)
        verification_level = self.hallucination_guard.get_verification_requirements(
            agent_name, operation_type, ticket_id
        )
        
        # Get workspace files for context
        workspace_path = Path(context['workspace']['path'])
        workspace_files = []
        if workspace_path.exists():
            workspace_files = [str(f.relative_to(workspace_path)) 
                             for f in workspace_path.rglob("*") 
                             if f.is_file() and f.suffix in ['.py', '.js', '.ts', '.md', '.json']]
        
        # Enhance context with hallucination protection
        enhanced_context = context.copy()
        enhanced_context['hallucination_protection'] = {
            'verification_level': verification_level.value,
            'agent_name': agent_name,
            'operation_type': operation_type,
            'requires_evidence': verification_level in [VerificationLevel.EVIDENCE, VerificationLevel.CRITICAL],
            'workspace_files': workspace_files[:50],  # Limit for prompt size
            'verification_instructions': self._get_verification_instructions(verification_level)
        }
        
        # Write enhanced context to workspace for agent to discover
        context_file = Path(f"{context['workspace']['path']}/../context.json")
        with open(context_file, 'w') as f:
            json.dump(enhanced_context, f, indent=2)
        
        # Log delegation request with verification info
        self.event_logger.append_event(
            ticket_id=context['workspace']['ticket_id'],
            event_type="AGENT_DELEGATION_REQUEST",
            payload={
                "agent": agent_name,
                "context_file": str(context_file),
                "verification_level": verification_level.value,
                "operation_type": operation_type
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