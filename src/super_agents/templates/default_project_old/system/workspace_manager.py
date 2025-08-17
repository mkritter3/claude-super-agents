#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class WorkspaceManager:
    def __init__(self, base_path: str = ".claude/workspaces"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def create_workspace(self, ticket_id: str, prompt: str) -> str:
        """Create isolated workspace with git initialization."""
        job_id = f"JOB-{uuid.uuid4().hex[:8]}"
        workspace_path = self.base_path / job_id
        
        # Create directory structure
        workspace_path.mkdir(parents=True)
        (workspace_path / "workspace").mkdir()
        (workspace_path / "artifacts").mkdir()
        
        # Initialize git in workspace
        subprocess.run(
            ["git", "init"],
            cwd=workspace_path / "workspace",
            check=True,
            capture_output=True
        )
        
        # Create initial manifest
        manifest = {
            "job_id": job_id,
            "ticket_id": ticket_id,
            "status": "INITIALIZED",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "original_prompt": prompt,
            "current_agent": "",
            "last_event_id": "",
            "git_head": "",
            "artifacts": []
        }
        
        manifest_path = workspace_path / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create history log
        (workspace_path / "history.log").touch()
        
        return job_id
    
    def update_manifest(self, job_id: str, updates: Dict[str, Any]):
        """Update workspace manifest atomically."""
        manifest_path = self.base_path / job_id / "manifest.json"
        
        # Read current manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Update fields
        manifest.update(updates)
        manifest["updated_at"] = datetime.now().isoformat()
        
        # Atomic write (write to temp, then rename)
        temp_path = manifest_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        temp_path.rename(manifest_path)
    
    def checkpoint_workspace(self, job_id: str, message: str):
        """Create git commit checkpoint in workspace."""
        workspace_path = self.base_path / job_id / "workspace"
        
        # Add all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=workspace_path,
            check=True
        )
        
        # Commit with message
        result = subprocess.run(
            ["git", "commit", "-m", message, "--allow-empty"],
            cwd=workspace_path,
            capture_output=True,
            text=True
        )
        
        # Get commit hash
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        # Update manifest with git head
        self.update_manifest(job_id, {"git_head": commit_hash})
        
        return commit_hash
    
    def rollback_workspace(self, job_id: str, commit: str = "HEAD~1"):
        """Rollback workspace to previous commit."""
        workspace_path = self.base_path / job_id / "workspace"
        
        subprocess.run(
            ["git", "reset", "--hard", commit],
            cwd=workspace_path,
            check=True
        )

if __name__ == "__main__":
    # CLI interface
    import sys
    manager = WorkspaceManager()
    
    if len(sys.argv) < 2:
        print("Usage: workspace_manager.py <command> [args...]")
        print("Commands: create, update, checkpoint, rollback")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        job_id = manager.create_workspace(sys.argv[2], sys.argv[3])
        print(job_id)
    elif command == "checkpoint":
        commit = manager.checkpoint_workspace(sys.argv[2], sys.argv[3])
        print(commit)
    # Add other commands as needed