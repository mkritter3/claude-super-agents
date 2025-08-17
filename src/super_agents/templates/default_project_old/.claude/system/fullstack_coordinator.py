#!/usr/bin/env python3
"""
Full-Stack Workflow Coordinator

This module coordinates complex full-stack workflows between multiple agents,
ensuring proper handoffs, dependency resolution, and workflow orchestration
for the expanded 23-agent autonomous engineering team.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from event_logger import EventLogger
from workspace_manager import WorkspaceManager
from logger_config import get_contextual_logger

class FullStackCoordinator:
    """
    Coordinates complex full-stack workflows between multiple agents.
    
    This coordinator handles:
    1. Feature development workflows (product → frontend → backend → database)
    2. Database change coordination with safety nets
    3. Security-first deployment coordination
    4. Cross-agent dependency resolution
    5. Workflow checkpoints and rollback procedures
    """
    
    def __init__(self):
        self.event_logger = EventLogger()
        self.workspace_manager = WorkspaceManager()
        self.logger = get_contextual_logger("fullstack_coordinator", component="coordination")
        
        # Workflow definitions
        self.workflow_definitions = {
            "full_stack_feature": [
                {"stage": "product_planning", "agent": "product-agent", "required": True},
                {"stage": "ux_design", "agent": "ux-agent", "required": True},
                {"stage": "architecture", "agent": "architect-agent", "required": True},
                {"stage": "frontend_dev", "agent": "frontend-agent", "required": True},
                {"stage": "backend_dev", "agent": "developer-agent", "required": True},
                {"stage": "database_design", "agent": "database-agent", "required": False},
                {"stage": "security_review", "agent": "security-agent", "required": True},
                {"stage": "testing", "agent": "test-executor", "required": True},
                {"stage": "devops_prep", "agent": "devops-agent", "required": True},
                {"stage": "integration", "agent": "integrator-agent", "required": True}
            ],
            
            "database_migration": [
                {"stage": "schema_analysis", "agent": "database-agent", "required": True},
                {"stage": "migration_planning", "agent": "data-migration-agent", "required": True},
                {"stage": "contract_validation", "agent": "contract-guardian", "required": True},
                {"stage": "security_review", "agent": "security-agent", "required": True},
                {"stage": "testing", "agent": "test-executor", "required": True},
                {"stage": "monitoring_setup", "agent": "monitoring-agent", "required": True}
            ],
            
            "security_deployment": [
                {"stage": "security_audit", "agent": "security-agent", "required": True},
                {"stage": "contract_validation", "agent": "contract-guardian", "required": True},
                {"stage": "infrastructure_review", "agent": "devops-agent", "required": True},
                {"stage": "monitoring_setup", "agent": "monitoring-agent", "required": True},
                {"stage": "testing", "agent": "test-executor", "required": True},
                {"stage": "deployment", "agent": "integrator-agent", "required": True}
            ],
            
            "frontend_feature": [
                {"stage": "ux_design", "agent": "ux-agent", "required": True},
                {"stage": "frontend_dev", "agent": "frontend-agent", "required": True},
                {"stage": "testing", "agent": "test-executor", "required": True},
                {"stage": "integration", "agent": "integrator-agent", "required": True}
            ]
        }
        
        # Coordination state
        self.active_workflows = {}
        self.coordination_state_path = Path(".claude/state/coordination_state.json")
        self.coordination_state_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.load_coordination_state()
    
    def load_coordination_state(self):
        """Load coordination state from disk"""
        if self.coordination_state_path.exists():
            try:
                with open(self.coordination_state_path, 'r') as f:
                    saved_state = json.load(f)
                    self.active_workflows.update(saved_state.get("active_workflows", {}))
                self.logger.info("Loaded coordination state", extra={
                    "active_workflows": len(self.active_workflows)
                })
            except Exception as e:
                self.logger.error("Failed to load coordination state", extra={"error": str(e)})
    
    def save_coordination_state(self):
        """Save coordination state to disk"""
        try:
            state = {
                "active_workflows": self.active_workflows,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.coordination_state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save coordination state", extra={"error": str(e)})
    
    def coordinate_feature_development(self, ticket_id: str, requirements: Dict) -> str:
        """
        Complete product feature workflow coordination.
        
        Orchestrates the full workflow from product requirements to deployment,
        ensuring all agents work together seamlessly.
        """
        workflow_id = f"workflow_{ticket_id}_{int(time.time())}"
        
        self.logger.info("Starting full-stack feature development", extra={
            "workflow_id": workflow_id,
            "ticket_id": ticket_id,
            "requirements": requirements
        })
        
        # Create workflow state
        workflow_state = {
            "workflow_id": workflow_id,
            "workflow_type": "full_stack_feature",
            "ticket_id": ticket_id,
            "requirements": requirements,
            "status": "INITIATED",
            "current_stage": "product_planning",
            "completed_stages": [],
            "failed_stages": [],
            "agent_results": {},
            "created_at": time.time(),
            "updated_at": time.time(),
            "coordination_checkpoints": []
        }
        
        # Log workflow initiation
        event_id = self.event_logger.append_event(
            ticket_id=ticket_id,
            event_type="FULLSTACK_WORKFLOW_INITIATED",
            payload={
                "workflow_id": workflow_id,
                "workflow_type": "full_stack_feature",
                "requirements": requirements
            }
        )
        
        workflow_state["initiation_event_id"] = event_id
        self.active_workflows[workflow_id] = workflow_state
        self.save_coordination_state()
        
        # Start the workflow
        self._execute_workflow_stage(workflow_id, "product_planning")
        
        return workflow_id
    
    def coordinate_database_changes(self, ticket_id: str, schema_changes: Dict) -> str:
        """
        Database change coordination with safety nets.
        
        Ensures safe database evolution with proper validation, testing,
        and rollback procedures.
        """
        workflow_id = f"db_workflow_{ticket_id}_{int(time.time())}"
        
        self.logger.info("Starting database change coordination", extra={
            "workflow_id": workflow_id,
            "ticket_id": ticket_id,
            "schema_changes": schema_changes
        })
        
        # Create workflow state
        workflow_state = {
            "workflow_id": workflow_id,
            "workflow_type": "database_migration",
            "ticket_id": ticket_id,
            "schema_changes": schema_changes,
            "status": "INITIATED",
            "current_stage": "schema_analysis",
            "completed_stages": [],
            "failed_stages": [],
            "agent_results": {},
            "safety_checks": {
                "breaking_changes": False,
                "data_loss_risk": False,
                "rollback_plan": None
            },
            "created_at": time.time(),
            "updated_at": time.time(),
            "coordination_checkpoints": []
        }
        
        # Log workflow initiation
        event_id = self.event_logger.append_event(
            ticket_id=ticket_id,
            event_type="DATABASE_WORKFLOW_INITIATED",
            payload={
                "workflow_id": workflow_id,
                "schema_changes": schema_changes,
                "safety_level": "maximum"
            }
        )
        
        workflow_state["initiation_event_id"] = event_id
        self.active_workflows[workflow_id] = workflow_state
        self.save_coordination_state()
        
        # Start the workflow with safety checks
        self._execute_workflow_stage(workflow_id, "schema_analysis")
        
        return workflow_id
    
    def coordinate_security_deployment(self, ticket_id: str, deployment_config: Dict) -> str:
        """
        Security-first deployment coordination.
        
        Ensures all security checks pass before deployment with comprehensive
        validation and monitoring setup.
        """
        workflow_id = f"security_deploy_{ticket_id}_{int(time.time())}"
        
        self.logger.info("Starting security deployment coordination", extra={
            "workflow_id": workflow_id,
            "ticket_id": ticket_id,
            "deployment_config": deployment_config
        })
        
        # Create workflow state
        workflow_state = {
            "workflow_id": workflow_id,
            "workflow_type": "security_deployment",
            "ticket_id": ticket_id,
            "deployment_config": deployment_config,
            "status": "INITIATED",
            "current_stage": "security_audit",
            "completed_stages": [],
            "failed_stages": [],
            "agent_results": {},
            "security_gates": {
                "vulnerability_scan": False,
                "compliance_check": False,
                "penetration_test": False,
                "security_review": False
            },
            "created_at": time.time(),
            "updated_at": time.time(),
            "coordination_checkpoints": []
        }
        
        # Log workflow initiation
        event_id = self.event_logger.append_event(
            ticket_id=ticket_id,
            event_type="SECURITY_DEPLOYMENT_INITIATED",
            payload={
                "workflow_id": workflow_id,
                "deployment_config": deployment_config,
                "security_level": "maximum"
            }
        )
        
        workflow_state["initiation_event_id"] = event_id
        self.active_workflows[workflow_id] = workflow_state
        self.save_coordination_state()
        
        # Start the workflow with security emphasis
        self._execute_workflow_stage(workflow_id, "security_audit")
        
        return workflow_id
    
    def _execute_workflow_stage(self, workflow_id: str, stage_name: str):
        """Execute a specific workflow stage"""
        if workflow_id not in self.active_workflows:
            self.logger.error("Workflow not found", extra={"workflow_id": workflow_id})
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow_type = workflow["workflow_type"]
        
        if workflow_type not in self.workflow_definitions:
            self.logger.error("Unknown workflow type", extra={
                "workflow_type": workflow_type,
                "workflow_id": workflow_id
            })
            return False
        
        # Find the stage definition
        stage_def = None
        for stage in self.workflow_definitions[workflow_type]:
            if stage["stage"] == stage_name:
                stage_def = stage
                break
        
        if not stage_def:
            self.logger.error("Stage not found in workflow", extra={
                "stage_name": stage_name,
                "workflow_type": workflow_type
            })
            return False
        
        # Log stage execution
        self.event_logger.append_event(
            ticket_id=workflow["ticket_id"],
            event_type="WORKFLOW_STAGE_STARTED",
            payload={
                "workflow_id": workflow_id,
                "stage": stage_name,
                "agent": stage_def["agent"]
            }
        )
        
        # Update workflow state
        workflow["current_stage"] = stage_name
        workflow["status"] = f"EXECUTING_{stage_name.upper()}"
        workflow["updated_at"] = time.time()
        
        # Create checkpoint
        checkpoint = {
            "stage": stage_name,
            "timestamp": time.time(),
            "status": "started",
            "agent": stage_def["agent"]
        }
        workflow["coordination_checkpoints"].append(checkpoint)
        
        self.save_coordination_state()
        
        self.logger.info("Executing workflow stage", extra={
            "workflow_id": workflow_id,
            "stage": stage_name,
            "agent": stage_def["agent"],
            "required": stage_def["required"]
        })
        
        return True
    
    def mark_stage_completed(self, workflow_id: str, stage_name: str, agent_result: Dict):
        """Mark a workflow stage as completed"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        
        # Update workflow state
        workflow["completed_stages"].append(stage_name)
        workflow["agent_results"][stage_name] = agent_result
        workflow["updated_at"] = time.time()
        
        # Update checkpoint
        for checkpoint in workflow["coordination_checkpoints"]:
            if checkpoint["stage"] == stage_name and checkpoint["status"] == "started":
                checkpoint["status"] = "completed"
                checkpoint["result"] = agent_result
                checkpoint["completed_at"] = time.time()
                break
        
        # Log completion
        self.event_logger.append_event(
            ticket_id=workflow["ticket_id"],
            event_type="WORKFLOW_STAGE_COMPLETED",
            payload={
                "workflow_id": workflow_id,
                "stage": stage_name,
                "result": agent_result
            }
        )
        
        # Check if we should proceed to next stage
        self._check_workflow_progression(workflow_id)
        
        self.save_coordination_state()
        return True
    
    def mark_stage_failed(self, workflow_id: str, stage_name: str, error_info: Dict):
        """Mark a workflow stage as failed"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        
        # Update workflow state
        workflow["failed_stages"].append({
            "stage": stage_name,
            "error": error_info,
            "timestamp": time.time()
        })
        workflow["status"] = f"FAILED_{stage_name.upper()}"
        workflow["updated_at"] = time.time()
        
        # Log failure
        self.event_logger.append_event(
            ticket_id=workflow["ticket_id"],
            event_type="WORKFLOW_STAGE_FAILED",
            payload={
                "workflow_id": workflow_id,
                "stage": stage_name,
                "error": error_info
            }
        )
        
        # Check if workflow should be terminated or retried
        self._handle_workflow_failure(workflow_id, stage_name, error_info)
        
        self.save_coordination_state()
        return True
    
    def _check_workflow_progression(self, workflow_id: str):
        """Check if workflow should progress to next stage"""
        workflow = self.active_workflows[workflow_id]
        workflow_type = workflow["workflow_type"]
        current_stage = workflow["current_stage"]
        
        # Find current stage index
        stages = self.workflow_definitions[workflow_type]
        current_index = -1
        for i, stage in enumerate(stages):
            if stage["stage"] == current_stage:
                current_index = i
                break
        
        # Check if there's a next stage
        if current_index >= 0 and current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            self._execute_workflow_stage(workflow_id, next_stage["stage"])
        else:
            # Workflow completed
            self._complete_workflow(workflow_id)
    
    def _complete_workflow(self, workflow_id: str):
        """Mark workflow as completed"""
        workflow = self.active_workflows[workflow_id]
        workflow["status"] = "COMPLETED"
        workflow["completed_at"] = time.time()
        
        # Log completion
        self.event_logger.append_event(
            ticket_id=workflow["ticket_id"],
            event_type="WORKFLOW_COMPLETED",
            payload={
                "workflow_id": workflow_id,
                "workflow_type": workflow["workflow_type"],
                "duration": workflow["completed_at"] - workflow["created_at"],
                "stages_completed": len(workflow["completed_stages"]),
                "stages_failed": len(workflow["failed_stages"])
            }
        )
        
        self.logger.info("Workflow completed", extra={
            "workflow_id": workflow_id,
            "workflow_type": workflow["workflow_type"],
            "stages_completed": len(workflow["completed_stages"])
        })
        
        self.save_coordination_state()
    
    def _handle_workflow_failure(self, workflow_id: str, stage_name: str, error_info: Dict):
        """Handle workflow failure with retry or termination logic"""
        workflow = self.active_workflows[workflow_id]
        
        # For now, terminate on failure
        # In production, this could implement retry logic
        workflow["status"] = "TERMINATED"
        workflow["termination_reason"] = f"Stage {stage_name} failed: {error_info.get('message', 'Unknown error')}"
        
        self.logger.warning("Workflow terminated due to failure", extra={
            "workflow_id": workflow_id,
            "failed_stage": stage_name,
            "error": error_info
        })
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get current workflow status"""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id].copy()
        return None
    
    def list_active_workflows(self) -> List[Dict]:
        """List all active workflows"""
        return [
            {
                "workflow_id": wf_id,
                "workflow_type": wf["workflow_type"],
                "status": wf["status"],
                "current_stage": wf.get("current_stage"),
                "created_at": wf["created_at"]
            }
            for wf_id, wf in self.active_workflows.items()
            if wf["status"] not in ["COMPLETED", "TERMINATED"]
        ]
    
    def get_coordination_metrics(self) -> Dict:
        """Get coordination performance metrics"""
        total_workflows = len(self.active_workflows)
        completed = sum(1 for wf in self.active_workflows.values() if wf["status"] == "COMPLETED")
        failed = sum(1 for wf in self.active_workflows.values() if wf["status"] == "TERMINATED")
        active = total_workflows - completed - failed
        
        return {
            "total_workflows": total_workflows,
            "completed_workflows": completed,
            "failed_workflows": failed,
            "active_workflows": active,
            "success_rate": (completed / total_workflows * 100) if total_workflows > 0 else 0,
            "average_stages_per_workflow": sum(
                len(wf["completed_stages"]) for wf in self.active_workflows.values()
            ) / total_workflows if total_workflows > 0 else 0
        }


if __name__ == "__main__":
    # Example usage and testing
    coordinator = FullStackCoordinator()
    
    # Test feature development workflow
    requirements = {
        "feature_name": "User Authentication System",
        "description": "Complete OAuth2 and JWT authentication",
        "complexity": "high",
        "requires_database": True,
        "requires_frontend": True,
        "security_level": "high"
    }
    
    workflow_id = coordinator.coordinate_feature_development("TEST-123", requirements)
    print(f"Started workflow: {workflow_id}")
    
    # Get status
    status = coordinator.get_workflow_status(workflow_id)
    print(f"Workflow status: {status['status']}")
    
    # Get metrics
    metrics = coordinator.get_coordination_metrics()
    print(f"Coordination metrics: {metrics}")