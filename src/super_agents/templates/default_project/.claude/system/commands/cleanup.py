#!/usr/bin/env python3
"""
Super Agents Cleanup System
Robust and safe removal of super-agents files with backup restoration
"""

import os
import sys
import json
import hashlib
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Confirm
    console = Console()
except ImportError:
    # Fallback for environments without rich
    class SimpleConsole:
        def print(self, text, style=None):
            print(text)
    
    class SimpleConfirm:
        @staticmethod
        def ask(prompt: str) -> bool:
            response = input(f"{prompt} (y/n): ").lower().strip()
            return response in ('y', 'yes')
    
    console = SimpleConsole()
    Confirm = SimpleConfirm


@dataclass
class ModifiedFile:
    """Information about a file that was modified by the user"""
    path: str
    template_hash: str
    current_hash: str
    size: int


@dataclass
class CleanupPlan:
    """Plan for cleanup operation"""
    files_to_delete: List[str]
    directories_to_delete: List[str]
    backups_to_restore: List[Tuple[str, str]]  # (original_path, backup_path)
    modified_files: List[ModifiedFile]
    running_processes: List[str]


class SuperAgentsCleanup:
    """Handles safe cleanup and restoration of super-agents installations"""
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.manifest_path = self.project_dir / '.claude' / '.super_agents_manifest.json'
        self.manifest_data = None
        
    def load_manifest(self) -> bool:
        """Load the super-agents manifest"""
        try:
            if not self.manifest_path.exists():
                console.print("[yellow]⚠ Super-agents manifest not found.[/yellow]")
                console.print("[dim]This installation may have been created before manifest tracking.[/dim]")
                
                # Offer to create a retroactive manifest
                if Confirm.ask("Would you like to create a manifest for this installation?"):
                    if self.create_retroactive_manifest():
                        return self.load_manifest()  # Retry loading
                    else:
                        return False
                else:
                    console.print("[red]❌ Cleanup cannot proceed without manifest.[/red]")
                    return False
            
            with open(self.manifest_path, 'r') as f:
                self.manifest_data = json.load(f)
            
            console.print("[green]✓[/green] Found super-agents manifest")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error loading manifest: {e}[/red]")
            return False
    
    def create_retroactive_manifest(self) -> bool:
        """Create a manifest for an existing installation by scanning files"""
        try:
            console.print("[dim]Scanning installation to create manifest...[/dim]")
            
            # Get template path to compare against
            template_source = self._get_template_path()
            if not template_source:
                console.print("[red]❌ Cannot find template for comparison[/red]")
                return False
            
            managed_files = []
            managed_directories = []
            
            # Scan for super-agents files by comparing with template
            for root, dirs, files in os.walk(template_source):
                rel_root = Path(root).relative_to(template_source)
                local_dir = self.project_dir / rel_root
                
                if local_dir.exists():
                    managed_directories.append(str(rel_root))
                    
                    for file_name in files:
                        local_file = local_dir / file_name
                        if local_file.exists():
                            managed_files.append(str(rel_root / file_name))
            
            # Add common super-agents files that might not be in template
            additional_files = ['.mcp.json', 'CLAUDE.md', 'km_bridge_local.py']
            for file_name in additional_files:
                file_path = self.project_dir / file_name
                if file_path.exists() and file_name not in managed_files:
                    managed_files.append(file_name)
            
            # Calculate hashes for existing files
            managed_files_with_hashes = {}
            for file_rel_path in managed_files:
                file_path = self.project_dir / file_rel_path
                if file_path.exists():
                    file_hash = self._calculate_file_hash(file_path)
                    managed_files_with_hashes[file_rel_path] = {
                        "hash": file_hash,
                        "size": file_path.stat().st_size
                    }
            
            # Create manifest
            manifest = {
                "schema_version": "1.0",
                "created_at": datetime.now().isoformat(),
                "installation_type": "retroactive",
                "managed_assets": {
                    "directories": managed_directories,
                    "files": managed_files_with_hashes
                },
                "overwritten_files": {},  # Can't determine retroactively
                "metadata": {
                    "python_executable": sys.executable,
                    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    "total_files": len(managed_files_with_hashes),
                    "total_directories": len(managed_directories)
                }
            }
            
            # Write manifest
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            console.print(f"[green]✓[/green] Created retroactive manifest ({len(managed_files_with_hashes)} files tracked)")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error creating retroactive manifest: {e}[/red]")
            return False
    
    def _get_template_path(self) -> Path:
        """Find the template directory"""
        try:
            # Try to find template relative to the current system
            current_file = Path(__file__)
            template_path = current_file.parent.parent.parent.parent.parent / "templates" / "default_project"
            
            if template_path.exists():
                return template_path
            
            # Try alternative locations
            import super_agents
            package_dir = Path(super_agents.__file__).parent
            template_path = package_dir / "templates" / "default_project"
            
            if template_path.exists():
                return template_path
                
            return None
            
        except Exception:
            return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        import hashlib
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def check_running_processes(self) -> List[str]:
        """Check for running super-agents processes"""
        running_processes = []
        
        # Check for Knowledge Manager PID file
        km_pid_file = self.project_dir / '.claude' / 'km.pid'
        if km_pid_file.exists():
            try:
                pid = int(km_pid_file.read_text().strip())
                # Check if process is actually running
                try:
                    os.kill(pid, 0)  # Signal 0 checks if process exists
                    running_processes.append(f"Knowledge Manager (PID: {pid})")
                except OSError:
                    # Process not running, clean up stale PID file
                    km_pid_file.unlink(missing_ok=True)
            except (ValueError, FileNotFoundError):
                pass
        
        # Check for other potential PID files
        claude_dir = self.project_dir / '.claude'
        if claude_dir.exists():
            for pid_file in claude_dir.glob('*.pid'):
                try:
                    pid = int(pid_file.read_text().strip())
                    try:
                        os.kill(pid, 0)
                        service_name = pid_file.stem.replace('_', ' ').title()
                        running_processes.append(f"{service_name} (PID: {pid})")
                    except OSError:
                        # Clean up stale PID file
                        pid_file.unlink(missing_ok=True)
                except (ValueError, FileNotFoundError):
                    continue
        
        return running_processes
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def analyze_modifications(self) -> List[ModifiedFile]:
        """Analyze which managed files have been modified by the user"""
        modified_files = []
        
        if not self.manifest_data or 'managed_assets' not in self.manifest_data:
            return modified_files
        
        for file_info in self.manifest_data['managed_assets'].get('files', []):
            file_path = self.project_dir / file_info['path']
            if not file_path.exists():
                continue
            
            template_hash = file_info.get('template_hash_sha256', '')
            current_hash = self.calculate_file_hash(file_path)
            
            if template_hash and current_hash and template_hash != current_hash:
                try:
                    size = file_path.stat().st_size
                    modified_files.append(ModifiedFile(
                        path=file_info['path'],
                        template_hash=template_hash,
                        current_hash=current_hash,
                        size=size
                    ))
                except OSError:
                    pass
        
        return modified_files
    
    def create_cleanup_plan(self) -> Optional[CleanupPlan]:
        """Create a comprehensive cleanup plan"""
        if not self.manifest_data:
            return None
        
        # Get files and directories to delete
        files_to_delete = []
        directories_to_delete = []
        
        managed_assets = self.manifest_data.get('managed_assets', {})
        
        # Files to delete
        for file_info in managed_assets.get('files', []):
            file_path = self.project_dir / file_info['path']
            if file_path.exists():
                files_to_delete.append(file_info['path'])
        
        # Directories to delete (in reverse order for safe deletion)
        for dir_path in reversed(managed_assets.get('directories', [])):
            full_dir_path = self.project_dir / dir_path
            if full_dir_path.exists():
                directories_to_delete.append(dir_path)
        
        # Backups to restore
        backups_to_restore = []
        for backup_info in self.manifest_data.get('overwritten_files', []):
            original_path = backup_info['original_path']
            backup_path = backup_info['backup_path']
            full_backup_path = self.project_dir / backup_path
            
            if full_backup_path.exists():
                backups_to_restore.append((original_path, backup_path))
        
        # Check for running processes
        running_processes = self.check_running_processes()
        
        # Analyze modifications
        modified_files = self.analyze_modifications()
        
        return CleanupPlan(
            files_to_delete=files_to_delete,
            directories_to_delete=directories_to_delete,
            backups_to_restore=backups_to_restore,
            modified_files=modified_files,
            running_processes=running_processes
        )
    
    def validate_safety(self, plan: CleanupPlan) -> bool:
        """Validate that it's safe to proceed with cleanup"""
        safety_issues = []
        
        # Check for running processes
        if plan.running_processes:
            safety_issues.append("Running processes detected")
            console.print("[red]❌ Cannot proceed: super-agents processes are still running[/red]")
            console.print("\nRunning processes:")
            for process in plan.running_processes:
                console.print(f"  • {process}")
            console.print("\n[yellow]Please stop all processes first:[/yellow]")
            console.print("  super-agents stop")
            return False
        
        # All safety checks passed
        if not safety_issues:
            console.print("[green]✓[/green] Safety validation passed")
        
        return len(safety_issues) == 0
    
    def display_cleanup_plan(self, plan: CleanupPlan):
        """Display the cleanup plan to the user"""
        console.print("\n" + "═" * 60)
        console.print("  🧹 SUPER-AGENTS CLEANUP PLAN")
        console.print("═" * 60)
        
        # Files to be deleted
        if plan.files_to_delete:
            console.print(f"\n[bold]Files to be deleted ({len(plan.files_to_delete)}):[/bold]")
            for file_path in plan.files_to_delete[:10]:  # Show first 10
                console.print(f"  • {file_path}")
            if len(plan.files_to_delete) > 10:
                console.print(f"  ... and {len(plan.files_to_delete) - 10} more files")
        
        # Modified files warning
        if plan.modified_files:
            console.print(f"\n[bold red]⚠️  WARNING: Modified files will also be deleted ({len(plan.modified_files)}):[/bold red]")
            for mod_file in plan.modified_files:
                size_kb = mod_file.size / 1024
                console.print(f"  • {mod_file.path} ({size_kb:.1f} KB)")
            console.print("\n[red]These files contain your changes and will be permanently lost![/red]")
        
        # Directories to be deleted
        if plan.directories_to_delete:
            console.print(f"\n[bold]Directories to be removed ({len(plan.directories_to_delete)}):[/bold]")
            for dir_path in plan.directories_to_delete:
                console.print(f"  • {dir_path}")
        
        # Backups to be restored
        if plan.backups_to_restore:
            console.print(f"\n[bold green]Original files to be restored ({len(plan.backups_to_restore)}):[/bold green]")
            for original_path, backup_path in plan.backups_to_restore:
                console.print(f"  • {original_path}")
        
        console.print("\n" + "═" * 60)
    
    def get_user_confirmation(self, plan: CleanupPlan, force: bool = False) -> bool:
        """Get user confirmation for the cleanup operation"""
        if force:
            console.print("[yellow]Force mode enabled - skipping confirmation[/yellow]")
            return True
        
        console.print("\n[bold red]This operation cannot be undone![/bold red]")
        
        if plan.modified_files:
            console.print("\n[bold red]⚠️  CRITICAL WARNING:[/bold red]")
            console.print(f"[red]{len(plan.modified_files)} files contain your modifications and will be permanently deleted![/red]")
        
        try:
            return Confirm.ask("\nAre you sure you want to proceed with cleanup?", default=False)
        except:
            # Fallback for environments without rich
            response = input("\nAre you sure you want to proceed with cleanup? (y/N): ").strip().lower()
            return response in ['y', 'yes']
    
    def execute_cleanup(self, plan: CleanupPlan) -> bool:
        """Execute the cleanup plan"""
        console.print("\n🧹 Starting cleanup operation...")
        
        success = True
        
        # Phase 1: Restore backups
        if plan.backups_to_restore:
            console.print(f"\n📂 Restoring {len(plan.backups_to_restore)} backed up files...")
            for original_path, backup_path in plan.backups_to_restore:
                try:
                    full_backup_path = self.project_dir / backup_path
                    full_original_path = self.project_dir / original_path
                    
                    if full_backup_path.exists():
                        # Create parent directory if needed
                        full_original_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(full_backup_path), str(full_original_path))
                        console.print(f"  ✓ Restored {original_path}")
                    else:
                        console.print(f"  ⚠️  Backup not found: {backup_path}")
                except Exception as e:
                    console.print(f"  ❌ Failed to restore {original_path}: {e}")
                    success = False
        
        # Phase 2: Delete files
        if plan.files_to_delete:
            console.print(f"\n🗑️  Deleting {len(plan.files_to_delete)} files...")
            for file_path in plan.files_to_delete:
                try:
                    full_path = self.project_dir / file_path
                    if full_path.exists():
                        full_path.unlink()
                        console.print(f"  ✓ Deleted {file_path}")
                except Exception as e:
                    console.print(f"  ❌ Failed to delete {file_path}: {e}")
                    success = False
        
        # Phase 3: Delete directories
        if plan.directories_to_delete:
            console.print(f"\n📁 Removing {len(plan.directories_to_delete)} directories...")
            for dir_path in plan.directories_to_delete:
                try:
                    full_path = self.project_dir / dir_path
                    if full_path.exists():
                        try:
                            full_path.rmdir()  # Only removes if empty
                            console.print(f"  ✓ Removed {dir_path}")
                        except OSError:
                            console.print(f"  ⚠️  Directory not empty: {dir_path}")
                except Exception as e:
                    console.print(f"  ❌ Failed to remove {dir_path}: {e}")
                    success = False
        
        # Phase 4: Clean up backup directory
        backup_dir = self.project_dir / '.claude' / '.backups'
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
                console.print("  ✓ Cleaned up backup directory")
            except Exception as e:
                console.print(f"  ⚠️  Could not remove backup directory: {e}")
        
        # Phase 5: Delete manifest (last step)
        try:
            if self.manifest_path.exists():
                self.manifest_path.unlink()
                console.print("  ✓ Removed super-agents manifest")
        except Exception as e:
            console.print(f"  ❌ Failed to remove manifest: {e}")
            success = False
        
        return success
    
    def cleanup(self, force: bool = False, dry_run: bool = False) -> bool:
        """Main cleanup method"""
        console.print(Panel.fit("🧹 Super-Agents Cleanup System", style="bold yellow"))
        
        # Load manifest
        if not self.load_manifest():
            return False
        
        # Create cleanup plan
        plan = self.create_cleanup_plan()
        if not plan:
            console.print("[red]❌ Could not create cleanup plan[/red]")
            return False
        
        # Validate safety
        if not self.validate_safety(plan):
            return False
        
        # Display plan
        self.display_cleanup_plan(plan)
        
        # Dry run mode
        if dry_run:
            console.print("\n[yellow]🔍 DRY RUN MODE - No changes will be made[/yellow]")
            return True
        
        # Get user confirmation
        if not self.get_user_confirmation(plan, force):
            console.print("\n[yellow]Cleanup cancelled by user[/yellow]")
            return False
        
        # Execute cleanup
        success = self.execute_cleanup(plan)
        
        if success:
            console.print("\n[green]✅ Cleanup completed successfully![/green]")
            console.print("[dim]All super-agents files have been removed and original files restored.[/dim]")
        else:
            console.print("\n[red]⚠️  Cleanup completed with some errors[/red]")
            console.print("[dim]You may need to manually remove remaining files.[/dim]")
        
        return success


def main():
    """CLI entry point for cleanup command"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up super-agents installation")
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompts')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--project-dir', type=Path,
                       help='Project directory (default: current directory)')
    
    args = parser.parse_args()
    
    cleanup_system = SuperAgentsCleanup(args.project_dir)
    success = cleanup_system.cleanup(force=args.force, dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()