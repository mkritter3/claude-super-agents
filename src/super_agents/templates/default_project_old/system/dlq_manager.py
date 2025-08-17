#!/usr/bin/env python3
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class DeadLetterQueue:
    def __init__(self, base_path: str = ".claude/dlq"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def add_failed_task(self,
                       ticket_id: str,
                       job_id: str,
                       reason: str,
                       workspace_path: str,
                       attempts: int = 3):
        """Move failed task to DLQ."""
        
        # Create DLQ entry
        dlq_entry = {
            "ticket_id": ticket_id,
            "job_id": job_id,
            "reason": reason,
            "attempts": attempts,
            "quarantined_at": datetime.now().isoformat(),
            "workspace_backup": f"{self.base_path}/{job_id}"
        }
        
        # Backup workspace
        workspace_src = Path(workspace_path)
        if workspace_src.exists():
            workspace_dst = self.base_path / job_id
            if workspace_dst.exists():
                shutil.rmtree(workspace_dst)
            shutil.copytree(workspace_src, workspace_dst)
        
        # Write DLQ entry
        entry_file = self.base_path / f"{ticket_id}.json"
        with open(entry_file, 'w') as f:
            json.dump(dlq_entry, f, indent=2)
        
        return str(entry_file)
    
    def list_failed_tasks(self) -> List[Dict]:
        """List all tasks in DLQ."""
        tasks = []
        
        for entry_file in self.base_path.glob("*.json"):
            try:
                with open(entry_file, 'r') as f:
                    task = json.load(f)
                    task['file'] = str(entry_file)
                    tasks.append(task)
            except Exception as e:
                print(f"Error reading DLQ entry {entry_file}: {e}")
        
        return tasks
    
    def retry_task(self, ticket_id: str) -> bool:
        """Attempt to retry a failed task."""
        entry_file = self.base_path / f"{ticket_id}.json"
        
        if not entry_file.exists():
            print(f"DLQ entry not found for {ticket_id}")
            return False
        
        try:
            with open(entry_file, 'r') as f:
                task = json.load(f)
            
            # Restore workspace
            workspace_backup = Path(task['workspace_backup'])
            if workspace_backup.exists():
                original_workspace = Path(f".claude/workspaces/{task['job_id']}")
                
                # Remove existing workspace if present
                if original_workspace.exists():
                    shutil.rmtree(original_workspace)
                
                # Restore from backup
                shutil.copytree(workspace_backup, original_workspace)
                
                # Remove from DLQ
                entry_file.unlink()
                shutil.rmtree(workspace_backup)
                
                # Reset task status in snapshot
                try:
                    from orchestrator import TaskOrchestrator
                    orchestrator = TaskOrchestrator()
                    snapshots = orchestrator.load_snapshots()
                    
                    if ticket_id in snapshots:
                        snapshots[ticket_id]['status'] = 'CREATED'
                        snapshots[ticket_id]['retry_count'] = 0
                        orchestrator.save_snapshot(ticket_id, snapshots[ticket_id])
                        print(f"Task {ticket_id} restored and reset to CREATED status")
                    else:
                        print(f"Warning: No snapshot found for {ticket_id}")
                except Exception as e:
                    print(f"Error resetting task snapshot: {e}")
                
                return True
            else:
                print(f"Workspace backup not found: {workspace_backup}")
                return False
        
        except Exception as e:
            print(f"Error retrying task {ticket_id}: {e}")
            return False
    
    def remove_task(self, ticket_id: str) -> bool:
        """Permanently remove a task from DLQ."""
        entry_file = self.base_path / f"{ticket_id}.json"
        
        if not entry_file.exists():
            return False
        
        try:
            with open(entry_file, 'r') as f:
                task = json.load(f)
            
            # Remove workspace backup
            workspace_backup = Path(task['workspace_backup'])
            if workspace_backup.exists():
                shutil.rmtree(workspace_backup)
            
            # Remove entry
            entry_file.unlink()
            return True
            
        except Exception as e:
            print(f"Error removing task {ticket_id}: {e}")
            return False
    
    def get_task_details(self, ticket_id: str) -> Optional[Dict]:
        """Get details of a task in DLQ."""
        entry_file = self.base_path / f"{ticket_id}.json"
        
        if not entry_file.exists():
            return None
        
        try:
            with open(entry_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading task details for {ticket_id}: {e}")
            return None

if __name__ == "__main__":
    import sys
    
    dlq = DeadLetterQueue()
    
    if len(sys.argv) < 2:
        print("Usage: dlq_manager.py <command> [args]")
        print("Commands:")
        print("  list                 - List all failed tasks")
        print("  retry <ticket_id>    - Retry a failed task")
        print("  remove <ticket_id>   - Remove a task from DLQ")
        print("  details <ticket_id>  - Show task details")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        tasks = dlq.list_failed_tasks()
        if tasks:
            print(f"Found {len(tasks)} failed tasks in DLQ:")
            for task in tasks:
                print(f"  {task['ticket_id']}: {task['reason']} (attempts: {task['attempts']})")
        else:
            print("No failed tasks in DLQ")
    
    elif command == "retry":
        if len(sys.argv) < 3:
            print("Usage: dlq_manager.py retry <ticket_id>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        success = dlq.retry_task(ticket_id)
        if success:
            print(f"Successfully retried task {ticket_id}")
        else:
            print(f"Failed to retry task {ticket_id}")
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: dlq_manager.py remove <ticket_id>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        success = dlq.remove_task(ticket_id)
        if success:
            print(f"Successfully removed task {ticket_id}")
        else:
            print(f"Failed to remove task {ticket_id}")
    
    elif command == "details":
        if len(sys.argv) < 3:
            print("Usage: dlq_manager.py details <ticket_id>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        details = dlq.get_task_details(ticket_id)
        if details:
            print(json.dumps(details, indent=2))
        else:
            print(f"Task {ticket_id} not found in DLQ")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)