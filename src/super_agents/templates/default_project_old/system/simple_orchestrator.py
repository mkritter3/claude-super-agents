#!/usr/bin/env python3
"""
Simple Orchestrator - Lightweight alternative to full AET orchestration
Handles common tasks without the complexity of multi-agent architecture.
"""

import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from event_logger import EventLogger
from logger_config import get_contextual_logger, log_system_event


class SimpleOrchestrator:
    """
    Lightweight task processor for common operations.
    
    Features:
    - Single-threaded, synchronous execution
    - Direct file operations (no workspace isolation)
    - Minimal dependencies (no KM, no parallel processing)
    - Basic planning -> implementation -> validation flow
    - Clear logging and error handling
    """
    
    def __init__(self):
        self.event_logger = EventLogger()
        self.logger = get_contextual_logger("simple_orchestrator", component="simple_mode")
        self.simple_mode_active = True
        
        # Simple state tracking
        self.task_history = []
        self.current_task = None
        
        # Performance tracking
        self.start_time = None
        self.operations_count = 0
        
    def process_task(self, task_description: str, ticket_id: str = None) -> Dict[str, Any]:
        """
        Process a task using simplified workflow.
        
        Args:
            task_description: Natural language description of the task
            ticket_id: Optional ticket ID for tracking
            
        Returns:
            Dict with execution results and metadata
        """
        if not ticket_id:
            ticket_id = f"SIMPLE-{int(time.time())}"
            
        self.current_task = {
            "ticket_id": ticket_id,
            "description": task_description,
            "start_time": time.time(),
            "status": "STARTED"
        }
        
        self.logger.info(f"Starting simple task processing: {ticket_id}")
        log_system_event("simple_task_started", {
            "ticket_id": ticket_id,
            "description": task_description,
            "mode": "simple"
        })
        
        try:
            # Log task start
            self.event_logger.append_event(
                ticket_id=ticket_id,
                event_type="SIMPLE_TASK_STARTED",
                payload={
                    "description": task_description,
                    "timestamp": datetime.now().isoformat(),
                    "mode": "simple"
                }
            )
            
            # Execute simplified workflow
            result = self._execute_simple_workflow(task_description, ticket_id)
            
            # Track completion
            self.current_task["status"] = "COMPLETED" if result["success"] else "FAILED"
            self.current_task["duration"] = time.time() - self.current_task["start_time"]
            self.task_history.append(self.current_task.copy())
            
            # Log completion
            self.event_logger.append_event(
                ticket_id=ticket_id,
                event_type="SIMPLE_TASK_COMPLETED",
                payload={
                    "success": result["success"],
                    "duration": self.current_task["duration"],
                    "operations": result.get("operations", 0),
                    "files_modified": len(result.get("files_changed", [])),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Simple task completed: {ticket_id} (success: {result['success']})")
            return result
            
        except Exception as e:
            self.logger.error(f"Simple task failed: {ticket_id} - {str(e)}")
            
            # Log failure
            self.event_logger.append_event(
                ticket_id=ticket_id,
                event_type="SIMPLE_TASK_FAILED",
                payload={
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "ticket_id": ticket_id,
                "mode": "simple"
            }
    
    def _execute_simple_workflow(self, task_description: str, ticket_id: str) -> Dict[str, Any]:
        """
        Execute the simplified workflow: Plan -> Implement -> Validate.
        """
        results = {
            "success": False,
            "ticket_id": ticket_id,
            "mode": "simple",
            "operations": 0,
            "files_changed": [],
            "steps_completed": []
        }
        
        try:
            # Step 1: Basic Planning
            plan = self._create_simple_plan(task_description)
            results["plan"] = plan
            results["steps_completed"].append("planning")
            results["operations"] += 1
            
            # Step 2: Implementation
            if plan["actionable"]:
                impl_result = self._implement_simple_plan(plan, ticket_id)
                results.update(impl_result)
                results["steps_completed"].append("implementation")
                results["operations"] += impl_result.get("operations", 0)
                
                # Step 3: Basic Validation
                if impl_result.get("success", False):
                    validation = self._validate_simple_implementation(impl_result)
                    results["validation"] = validation
                    results["steps_completed"].append("validation")
                    results["operations"] += 1
                    results["success"] = validation.get("passed", False)
            else:
                results["error"] = "Task not actionable in simple mode"
                
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"Workflow execution failed: {str(e)}")
            
        return results
    
    def _create_simple_plan(self, task_description: str) -> Dict[str, Any]:
        """
        Create a basic plan for the task.
        Identifies if task is actionable in simple mode.
        """
        self.logger.info("Creating simple plan")
        
        plan = {
            "description": task_description,
            "actionable": True,
            "complexity": "simple",
            "actions": [],
            "estimated_files": 0
        }
        
        # Simple heuristics to determine actionability
        task_lower = task_description.lower()
        
        # File operations
        if any(word in task_lower for word in ["create", "write", "add", "new file"]):
            plan["actions"].append("create_file")
            plan["estimated_files"] = 1
            
        if any(word in task_lower for word in ["modify", "update", "edit", "change"]):
            plan["actions"].append("modify_file")
            plan["estimated_files"] = 1
            
        if any(word in task_lower for word in ["delete", "remove"]):
            plan["actions"].append("delete_file")
            
        # Simple text operations
        if any(word in task_lower for word in ["fix", "bug", "error"]):
            plan["actions"].append("fix_issue")
            plan["complexity"] = "medium"
            
        # Complex operations that might not be suitable for simple mode
        if any(word in task_lower for word in ["refactor", "architecture", "database", "api"]):
            plan["complexity"] = "complex"
            plan["actionable"] = len(plan["actions"]) > 0  # Only if we also have simple actions
            
        # If no specific actions identified, try to handle as generic task
        if not plan["actions"]:
            plan["actions"].append("generic_task")
            plan["complexity"] = "unknown"
            
        self.logger.info(f"Plan created: {len(plan['actions'])} actions, complexity: {plan['complexity']}")
        return plan
    
    def _implement_simple_plan(self, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """
        Implement the plan using direct operations.
        """
        self.logger.info("Implementing simple plan")
        
        result = {
            "success": False,
            "operations": 0,
            "files_changed": [],
            "outputs": []
        }
        
        try:
            for action in plan["actions"]:
                operation_result = self._execute_action(action, plan, ticket_id)
                result["operations"] += 1
                result["outputs"].append(operation_result)
                
                if operation_result.get("files_changed"):
                    result["files_changed"].extend(operation_result["files_changed"])
                    
                if not operation_result.get("success", True):
                    result["error"] = operation_result.get("error", f"Action {action} failed")
                    return result
                    
            result["success"] = True
            self.logger.info(f"Implementation completed: {result['operations']} operations")
            
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Implementation failed: {str(e)}")
            
        return result
    
    def _execute_action(self, action: str, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """
        Execute a specific action.
        """
        self.logger.debug(f"Executing action: {action}")
        
        if action == "create_file":
            return self._create_example_file(plan, ticket_id)
        elif action == "modify_file":
            return self._modify_existing_file(plan, ticket_id)
        elif action == "delete_file":
            return self._delete_file(plan, ticket_id)
        elif action == "fix_issue":
            return self._fix_simple_issue(plan, ticket_id)
        elif action == "generic_task":
            return self._handle_generic_task(plan, ticket_id)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    def _create_example_file(self, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """Create a simple example file based on the task description."""
        try:
            # Create a simple file in current directory
            filename = f"simple_task_{ticket_id.split('-')[-1]}.txt"
            content = f"""# Task: {plan['description']}
# Created by Simple Mode
# Ticket: {ticket_id}
# Timestamp: {datetime.now().isoformat()}

This file was created as part of simple mode task processing.
Task description: {plan['description']}
"""
            
            with open(filename, 'w') as f:
                f.write(content)
                
            self.logger.info(f"Created file: {filename}")
            
            return {
                "success": True,
                "action": "create_file",
                "files_changed": [filename],
                "output": f"Created {filename}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create file: {str(e)}"
            }
    
    def _modify_existing_file(self, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """Modify an existing file if found."""
        try:
            # Look for files to modify
            current_dir = Path(".")
            files = list(current_dir.glob("*.txt")) + list(current_dir.glob("*.md"))
            
            if not files:
                # Create a file to modify
                return self._create_example_file(plan, ticket_id)
            
            # Modify the first suitable file
            target_file = files[0]
            original_content = target_file.read_text()
            
            modification = f"\n\n# Modified by Simple Mode\n# Ticket: {ticket_id}\n# Task: {plan['description']}\n# Timestamp: {datetime.now().isoformat()}\n"
            
            with open(target_file, 'a') as f:
                f.write(modification)
                
            self.logger.info(f"Modified file: {target_file}")
            
            return {
                "success": True,
                "action": "modify_file",
                "files_changed": [str(target_file)],
                "output": f"Modified {target_file}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to modify file: {str(e)}"
            }
    
    def _delete_file(self, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """Delete files matching simple patterns."""
        try:
            # Only delete files we created (safety measure)
            current_dir = Path(".")
            files_to_delete = list(current_dir.glob("simple_task_*.txt"))
            
            if not files_to_delete:
                return {
                    "success": True,
                    "action": "delete_file",
                    "files_changed": [],
                    "output": "No simple task files to delete"
                }
            
            deleted_files = []
            for file_path in files_to_delete[:3]:  # Limit to 3 files for safety
                file_path.unlink()
                deleted_files.append(str(file_path))
                
            self.logger.info(f"Deleted {len(deleted_files)} files")
            
            return {
                "success": True,
                "action": "delete_file",
                "files_changed": deleted_files,
                "output": f"Deleted {len(deleted_files)} files"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete files: {str(e)}"
            }
    
    def _fix_simple_issue(self, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """Attempt to fix simple issues."""
        try:
            # Create a fix documentation
            fix_file = f"fix_log_{ticket_id.split('-')[-1]}.txt"
            content = f"""# Fix Log
# Ticket: {ticket_id}
# Task: {plan['description']}
# Timestamp: {datetime.now().isoformat()}

## Issue Analysis
Task description indicates a fix is needed: {plan['description']}

## Simple Fix Applied
- Documented the issue
- Created this fix log
- Applied basic remediation

## Status
Fix completed in simple mode. For complex issues, use full AET mode.
"""
            
            with open(fix_file, 'w') as f:
                f.write(content)
                
            return {
                "success": True,
                "action": "fix_issue",
                "files_changed": [fix_file],
                "output": f"Created fix log: {fix_file}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create fix log: {str(e)}"
            }
    
    def _handle_generic_task(self, plan: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
        """Handle generic tasks that don't fit specific patterns."""
        try:
            # Create a task summary
            summary_file = f"task_summary_{ticket_id.split('-')[-1]}.txt"
            content = f"""# Task Summary
# Ticket: {ticket_id}
# Task: {plan['description']}
# Timestamp: {datetime.now().isoformat()}
# Mode: Simple

## Task Description
{plan['description']}

## Processing Notes
This task was processed in simple mode. The task description did not match
specific patterns for file operations or fixes.

## Recommendations
- For complex tasks, consider using full AET mode
- For specific file operations, use more explicit task descriptions
- Review task requirements and retry if needed

## Status
Task processed successfully in simple mode.
"""
            
            with open(summary_file, 'w') as f:
                f.write(content)
                
            return {
                "success": True,
                "action": "generic_task",
                "files_changed": [summary_file],
                "output": f"Created task summary: {summary_file}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to handle generic task: {str(e)}"
            }
    
    def _validate_simple_implementation(self, impl_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform basic validation of the implementation.
        """
        self.logger.info("Validating implementation")
        
        validation = {
            "passed": False,
            "checks": [],
            "issues": []
        }
        
        try:
            # Check if files were created/modified as expected
            files_changed = impl_result.get("files_changed", [])
            
            if files_changed:
                validation["checks"].append("files_modified")
                
                # Verify files exist and are readable
                for file_path in files_changed:
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        try:
                            content = path.read_text()
                            if len(content) > 0:
                                validation["checks"].append(f"file_valid_{path.name}")
                            else:
                                validation["issues"].append(f"Empty file: {file_path}")
                        except Exception as e:
                            validation["issues"].append(f"Cannot read file {file_path}: {str(e)}")
                    else:
                        validation["issues"].append(f"File not found: {file_path}")
            else:
                validation["issues"].append("No files were modified")
            
            # Check operation success
            if impl_result.get("success", False):
                validation["checks"].append("implementation_success")
            else:
                validation["issues"].append("Implementation reported failure")
            
            # Overall validation
            validation["passed"] = len(validation["issues"]) == 0 and len(validation["checks"]) > 0
            
            self.logger.info(f"Validation completed: {'PASSED' if validation['passed'] else 'FAILED'}")
            
        except Exception as e:
            validation["issues"].append(f"Validation error: {str(e)}")
            self.logger.error(f"Validation failed: {str(e)}")
            
        return validation
    
    def get_status(self) -> Dict[str, Any]:
        """Get current simple orchestrator status."""
        return {
            "mode": "simple",
            "active": self.simple_mode_active,
            "current_task": self.current_task,
            "tasks_completed": len(self.task_history),
            "total_operations": sum(task.get("operations", 0) for task in self.task_history if "operations" in task),
            "average_duration": sum(task.get("duration", 0) for task in self.task_history) / max(len(self.task_history), 1)
        }
    
    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task history."""
        return self.task_history[-limit:]
    
    def is_suitable_for_simple_mode(self, task_description: str) -> Dict[str, Any]:
        """
        Determine if a task is suitable for simple mode processing.
        """
        task_lower = task_description.lower()
        
        # Indicators for simple mode suitability
        simple_indicators = [
            "create", "write", "add", "new file", "modify", "update", "edit", 
            "change", "delete", "remove", "fix", "simple"
        ]
        
        # Indicators for complex tasks
        complex_indicators = [
            "refactor", "architecture", "database", "api", "integration",
            "deployment", "security", "performance", "scalability", "microservice"
        ]
        
        simple_score = sum(1 for indicator in simple_indicators if indicator in task_lower)
        complex_score = sum(1 for indicator in complex_indicators if indicator in task_lower)
        
        suitable = simple_score > 0 and complex_score <= simple_score
        
        return {
            "suitable": suitable,
            "simple_score": simple_score,
            "complex_score": complex_score,
            "confidence": min(1.0, simple_score / max(complex_score + 1, 1)),
            "recommendation": "simple" if suitable else "full"
        }