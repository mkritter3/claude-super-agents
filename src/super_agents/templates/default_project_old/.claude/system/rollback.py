#!/usr/bin/env python3
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime

class RollbackManager:
    def __init__(self):
        self.backup_dir = Path(".claude/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, label: str) -> str:
        """Create backup of current state."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{label}_{timestamp}"
        
        try:
            # Get current commit
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
        except subprocess.CalledProcessError:
            # If not in git repo, use timestamp as commit
            commit = timestamp
        
        # Create backup directory
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir()
        
        # Backup critical files
        files_to_backup = [
            ".claude/events/log.ndjson",
            ".claude/snapshots/tasks.json", 
            ".claude/registry/files.db",
            ".claude/registry/metrics.db",
            ".claude/registry/knowledge.db"
        ]
        
        for file_path in files_to_backup:
            src = Path(file_path)
            if src.exists():
                dst = backup_path / src.name
                shutil.copy2(src, dst)
            else:
                # Create empty file as placeholder
                (backup_path / src.name).touch()
        
        # Create git tag if possible
        try:
            subprocess.run(
                ["git", "tag", f"backup_{backup_name}", commit],
                check=False  # Don't fail if git not available
            )
        except:
            pass
        
        # Save metadata
        metadata = {
            "label": label,
            "timestamp": timestamp,
            "commit": commit,
            "tag": f"backup_{backup_name}",
            "created_at": datetime.now().isoformat()
        }
        
        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Backup created: {backup_name}")
        return str(backup_path)
    
    def rollback_to(self, backup_name: str) -> Tuple[bool, str]:
        """Rollback to a specific backup."""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return False, f"Backup {backup_name} not found"
        
        metadata_file = backup_path / "metadata.json"
        if not metadata_file.exists():
            return False, f"Backup metadata not found for {backup_name}"
        
        # Load metadata
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            return False, f"Error reading backup metadata: {e}"
        
        try:
            # Git reset to backup commit if possible
            try:
                subprocess.run(
                    ["git", "reset", "--hard", metadata['commit']],
                    check=True
                )
                print(f"Git reset to {metadata['commit']}")
            except subprocess.CalledProcessError:
                print("Warning: Could not reset git state")
            
            # Restore files
            files_to_restore = [
                ("log.ndjson", ".claude/events/log.ndjson"),
                ("tasks.json", ".claude/snapshots/tasks.json"),
                ("files.db", ".claude/registry/files.db"),
                ("metrics.db", ".claude/registry/metrics.db"),
                ("knowledge.db", ".claude/registry/knowledge.db")
            ]
            
            for backup_file, target_path in files_to_restore:
                src = backup_path / backup_file
                dst = Path(target_path)
                
                if src.exists() and src.stat().st_size > 0:
                    # Ensure target directory exists
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    print(f"Restored {target_path}")
            
            return True, f"Rolled back to {backup_name}"
            
        except Exception as e:
            return False, f"Rollback failed: {str(e)}"
    
    def list_backups(self) -> List[Dict]:
        """List available backups."""
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            metadata['path'] = str(backup_dir)
                            metadata['name'] = backup_dir.name
                            backups.append(metadata)
                    except Exception as e:
                        print(f"Error reading metadata for {backup_dir.name}: {e}")
        
        return sorted(backups, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup."""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return False
        
        try:
            # Remove git tag if it exists
            try:
                subprocess.run(
                    ["git", "tag", "-d", f"backup_{backup_name}"],
                    check=False
                )
            except:
                pass
            
            # Remove backup directory
            shutil.rmtree(backup_path)
            return True
        except Exception as e:
            print(f"Error deleting backup: {e}")
            return False
    
    def verify_backup(self, backup_name: str) -> Tuple[bool, str]:
        """Verify backup integrity."""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return False, f"Backup {backup_name} not found"
        
        metadata_file = backup_path / "metadata.json"
        if not metadata_file.exists():
            return False, "Metadata file missing"
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            return False, f"Error reading metadata: {e}"
        
        # Check required files exist
        required_files = ["log.ndjson", "tasks.json", "files.db"]
        missing_files = []
        
        for file_name in required_files:
            if not (backup_path / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            return False, f"Missing files: {', '.join(missing_files)}"
        
        return True, "Backup is valid"

if __name__ == "__main__":
    import sys
    
    manager = RollbackManager()
    
    if len(sys.argv) < 2:
        print("Usage: rollback.py <command> [args]")
        print("Commands:")
        print("  backup <label>       - Create backup with label")
        print("  list                 - List available backups")
        print("  rollback <name>      - Rollback to backup")
        print("  delete <name>        - Delete backup")
        print("  verify <name>        - Verify backup integrity")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "backup":
        label = sys.argv[2] if len(sys.argv) > 2 else "manual"
        backup_path = manager.create_backup(label)
        print(f"Backup created at: {backup_path}")
    
    elif command == "list":
        backups = manager.list_backups()
        if backups:
            print(f"Found {len(backups)} backups:")
            for backup in backups:
                print(f"  {backup['name']}: {backup['label']} ({backup['timestamp']})")
        else:
            print("No backups found")
    
    elif command == "rollback":
        if len(sys.argv) < 3:
            print("Usage: rollback.py rollback <backup_name>")
            sys.exit(1)
        
        backup_name = sys.argv[2]
        success, message = manager.rollback_to(backup_name)
        print(message)
        sys.exit(0 if success else 1)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: rollback.py delete <backup_name>")
            sys.exit(1)
        
        backup_name = sys.argv[2]
        success = manager.delete_backup(backup_name)
        if success:
            print(f"Deleted backup: {backup_name}")
        else:
            print(f"Failed to delete backup: {backup_name}")
    
    elif command == "verify":
        if len(sys.argv) < 3:
            print("Usage: rollback.py verify <backup_name>")
            sys.exit(1)
        
        backup_name = sys.argv[2]
        valid, message = manager.verify_backup(backup_name)
        print(f"Backup {backup_name}: {message}")
        sys.exit(0 if valid else 1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)