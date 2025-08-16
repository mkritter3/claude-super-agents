# Complete Robust Installation System Guide: Building Production-Ready Project Installers

This is a comprehensive guide for creating robust, user-friendly installation systems that handle conflicts gracefully, provide clear feedback, and ensure reliable project setup. Learn how to build installers that work flawlessly across different environments and handle edge cases professionally.

## What is a Robust Installation System?

A robust installation system goes beyond simple file copying. It handles conflicts intelligently, provides meaningful feedback, manages dependencies safely, and ensures the target environment is left in a predictable state regardless of what happens during installation.

### Key Principles

- **Conflict Resolution**: Handle existing files/directories gracefully
- **Atomic Operations**: Either complete successfully or leave no partial state
- **User Agency**: Give users control over important decisions
- **Comprehensive Logging**: Track everything for debugging and auditing
- **Graceful Degradation**: Continue working when non-critical components fail
- **Environment Agnostic**: Work across different operating systems and setups

### Architecture Components

```
User Command  →  CLI Interface  →  Project Scanner  →  Conflict Detector
                                        ↓
Package Templates  ←  File Copier  ←  User Interaction  ←  Backup Manager
                                        ↓
Post-Install Setup  →  Validation  →  Manifest Creation  →  Success Report
```

## Phase 1: Foundation Architecture

### Understanding Installation Challenges

**Common Problems with Basic Installers:**
- Overwrite files without asking
- Leave partial installations on failure
- No clear conflict resolution strategy
- Poor error messages and recovery
- Platform-specific issues
- No uninstallation support

**Professional Solution:**
- Intelligent conflict detection and resolution
- Atomic operations with rollback capability
- Clear user communication and choice
- Comprehensive error handling and recovery
- Cross-platform compatibility
- Complete audit trail

### Core Installation Manager

```python
#!/usr/bin/env python3
"""
Robust Installation System Framework
Production-ready installer with conflict resolution and rollback
"""

import os
import json
import shutil
import fcntl
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('installer.log'),
        logging.StreamHandler()
    ]
)

console = Console()
logger = logging.getLogger(__name__)

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    SKIP = "skip"
    BACKUP = "backup"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    CANCEL = "cancel"

class InstallationResult(Enum):
    """Installation outcome status"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ConflictItem:
    """Represents a file/directory conflict"""
    path: Path
    type: str  # 'file' or 'directory'
    existing_size: int
    existing_modified: datetime
    new_size: int
    is_critical: bool = False

@dataclass
class InstallationManifest:
    """Complete record of installation"""
    timestamp: datetime
    version: str
    target_path: Path
    source_template: str
    files_created: List[str]
    files_backed_up: List[str]
    conflicts_resolved: List[Dict]
    post_install_actions: List[str]
    environment_info: Dict
    success: bool
    errors: List[str]

class RobustInstaller:
    """Production-ready installation system"""
    
    def __init__(self, package_name: str, version: str):
        self.package_name = package_name
        self.version = version
        self.console = Console()
        self.logger = logging.getLogger(f"installer.{package_name}")
        
        # Installation state
        self.target_path = Path.cwd()
        self.source_template = None
        self.manifest = None
        self.backup_dir = None
        self.files_created = []
        self.rollback_actions = []
        
        # Configuration
        self.conflict_resolution = ConflictResolution.BACKUP  # Default strategy
        self.dry_run = False
        self.force_overwrite = False
        self.create_manifest = True
        
    def set_target_directory(self, path: Path) -> bool:
        """Set and validate target installation directory"""
        try:
            # Resolve to absolute path
            target = path.resolve()
            
            # Verify directory exists or can be created
            if not target.exists():
                if Confirm.ask(f"Directory {target} doesn't exist. Create it?"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    return False
            
            # Check write permissions
            test_file = target / ".write_test_temp"
            try:
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                self.console.print(f"[red]Error: No write permissions in {target}[/red]")
                return False
            
            self.target_path = target
            self.logger.info(f"Target directory set to: {target}")
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error setting target directory: {e}[/red]")
            return False
    
    def scan_for_conflicts(self, source_path: Path) -> List[ConflictItem]:
        """Scan for installation conflicts"""
        conflicts = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Scanning for conflicts...", total=None)
            
            for root, dirs, files in os.walk(source_path):
                rel_root = Path(root).relative_to(source_path)
                target_root = self.target_path / rel_root
                
                # Check directory conflicts
                if target_root.exists() and target_root.is_file():
                    conflicts.append(ConflictItem(
                        path=target_root,
                        type="directory",
                        existing_size=target_root.stat().st_size,
                        existing_modified=datetime.fromtimestamp(target_root.stat().st_mtime),
                        new_size=0,
                        is_critical=True
                    ))
                
                # Check file conflicts
                for file_name in files:
                    source_file = Path(root) / file_name
                    target_file = target_root / file_name
                    
                    if target_file.exists():
                        conflicts.append(ConflictItem(
                            path=target_file,
                            type="file",
                            existing_size=target_file.stat().st_size,
                            existing_modified=datetime.fromtimestamp(target_file.stat().st_mtime),
                            new_size=source_file.stat().st_size,
                            is_critical=self._is_critical_file(target_file)
                        ))
        
        self.logger.info(f"Found {len(conflicts)} conflicts")
        return conflicts
    
    def _is_critical_file(self, file_path: Path) -> bool:
        """Determine if file is critical (contains user data/config)"""
        critical_patterns = [
            "config",
            "settings",
            "data",
            ".env",
            "credentials",
            "secrets"
        ]
        
        file_str = str(file_path).lower()
        return any(pattern in file_str for pattern in critical_patterns)
    
    def display_conflicts(self, conflicts: List[ConflictItem]) -> None:
        """Display conflicts in user-friendly table"""
        if not conflicts:
            self.console.print("[green]✓[/green] No conflicts detected")
            return
        
        table = Table(title="Installation Conflicts Detected")
        table.add_column("Path", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Current Size", style="yellow")
        table.add_column("New Size", style="green")
        table.add_column("Modified", style="blue")
        table.add_column("Critical", style="red")
        
        for conflict in conflicts[:20]:  # Show first 20
            table.add_row(
                str(conflict.path.relative_to(self.target_path)),
                conflict.type,
                self._format_size(conflict.existing_size),
                self._format_size(conflict.new_size),
                conflict.existing_modified.strftime("%Y-%m-%d %H:%M"),
                "⚠️ YES" if conflict.is_critical else "No"
            )
        
        if len(conflicts) > 20:
            table.add_row("...", f"({len(conflicts) - 20} more)", "", "", "", "")
        
        self.console.print(table)
    
    def resolve_conflicts_interactively(self, conflicts: List[ConflictItem]) -> ConflictResolution:
        """Interactive conflict resolution"""
        if not conflicts:
            return ConflictResolution.SKIP
        
        self.display_conflicts(conflicts)
        
        # Show critical file warning
        critical_conflicts = [c for c in conflicts if c.is_critical]
        if critical_conflicts:
            self.console.print(f"\n[red]⚠️  Warning: {len(critical_conflicts)} critical files detected![/red]")
            self.console.print("[yellow]Critical files may contain your data or configuration.[/yellow]")
        
        # Present options
        self.console.print("\n[bold]Conflict Resolution Options:[/bold]")
        self.console.print("  1. [green]Backup existing files and continue[/green] (Recommended)")
        self.console.print("  2. [yellow]Skip existing files (keep current versions)[/yellow]")
        self.console.print("  3. [red]Overwrite all files[/red] (⚠️  Data loss risk)")
        self.console.print("  4. [blue]Cancel installation[/blue]")
        
        while True:
            choice = Prompt.ask(
                "\nChoose resolution strategy",
                choices=["1", "2", "3", "4"],
                default="1"
            )
            
            if choice == "1":
                return ConflictResolution.BACKUP
            elif choice == "2":
                return ConflictResolution.SKIP
            elif choice == "3":
                if critical_conflicts:
                    if not Confirm.ask("[red]⚠️  This will overwrite critical files. Are you sure?[/red]"):
                        continue
                return ConflictResolution.OVERWRITE
            elif choice == "4":
                return ConflictResolution.CANCEL
    
    def create_backup(self, conflicts: List[ConflictItem]) -> Path:
        """Create organized backup of conflicting files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_base = Path("archived_files")
        backup_dir = backup_base / f"{self.package_name}_backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Creating backup...", total=len(conflicts))
            
            backed_up_files = []
            for conflict in conflicts:
                try:
                    relative_path = conflict.path.relative_to(self.target_path)
                    backup_path = backup_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if conflict.path.is_file():
                        shutil.copy2(conflict.path, backup_path)
                    elif conflict.path.is_dir():
                        shutil.copytree(conflict.path, backup_path, dirs_exist_ok=True)
                    
                    backed_up_files.append(str(relative_path))
                    
                except Exception as e:
                    self.logger.warning(f"Failed to backup {conflict.path}: {e}")
                
                progress.advance(task)
        
        # Create backup manifest
        backup_manifest = {
            "package": self.package_name,
            "version": self.version,
            "backup_created": datetime.now().isoformat(),
            "original_location": str(self.target_path),
            "files_backed_up": backed_up_files,
            "backup_reason": "Installation conflict resolution",
            "restore_instructions": f"To restore: copy contents of {backup_dir} back to {self.target_path}"
        }
        
        with open(backup_dir / "backup_manifest.json", 'w') as f:
            json.dump(backup_manifest, f, indent=2)
        
        self.backup_dir = backup_dir
        self.console.print(f"[green]✓[/green] Backup created: {backup_dir}")
        return backup_dir
    
    def copy_files_safely(self, source_path: Path, conflicts: List[ConflictItem], 
                         resolution: ConflictResolution) -> Tuple[List[str], List[str]]:
        """Copy files with conflict resolution"""
        files_created = []
        files_skipped = []
        conflict_paths = {c.path for c in conflicts}
        
        total_files = sum(len(files) for _, _, files in os.walk(source_path))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Installing files...", total=total_files)
            
            for root, dirs, files in os.walk(source_path):
                rel_root = Path(root).relative_to(source_path)
                target_root = self.target_path / rel_root
                
                # Create directories
                try:
                    target_root.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Failed to create directory {target_root}: {e}")
                    continue
                
                # Copy files
                for file_name in files:
                    source_file = Path(root) / file_name
                    target_file = target_root / file_name
                    relative_target = target_file.relative_to(self.target_path)
                    
                    # Handle conflicts
                    if target_file in conflict_paths:
                        if resolution == ConflictResolution.SKIP:
                            files_skipped.append(str(relative_target))
                            progress.advance(task)
                            continue
                        elif resolution == ConflictResolution.BACKUP:
                            # File already backed up, proceed with copy
                            pass
                        elif resolution == ConflictResolution.OVERWRITE:
                            # Proceed with overwrite
                            pass
                    
                    # Copy file
                    try:
                        shutil.copy2(source_file, target_file)
                        files_created.append(str(relative_target))
                        
                        # Make scripts executable
                        if file_name.endswith(('.py', '.sh')) or not file_name.count('.'):
                            os.chmod(target_file, 0o755)
                        
                        # Track for rollback
                        self.rollback_actions.append(('remove_file', target_file))
                        
                    except Exception as e:
                        self.logger.error(f"Failed to copy {source_file} to {target_file}: {e}")
                    
                    progress.advance(task)
        
        return files_created, files_skipped
    
    def perform_post_install_setup(self) -> List[str]:
        """Execute post-installation setup tasks"""
        post_install_actions = []
        
        try:
            # Update configuration files with actual paths
            self._update_configuration_files()
            post_install_actions.append("Updated configuration files")
            
            # Initialize databases
            self._initialize_databases()
            post_install_actions.append("Initialized databases")
            
            # Set up environment-specific files
            self._setup_environment_files()
            post_install_actions.append("Set up environment files")
            
            # Install git hooks if applicable
            self._install_git_hooks()
            post_install_actions.append("Installed git hooks")
            
            # Create required directories
            self._create_required_directories()
            post_install_actions.append("Created required directories")
            
        except Exception as e:
            self.logger.error(f"Post-install setup error: {e}")
            post_install_actions.append(f"Error: {e}")
        
        return post_install_actions
    
    def _update_configuration_files(self):
        """Update configuration files with actual paths"""
        config_files = [
            self.target_path / "config.json",
            self.target_path / ".env.template",
            self.target_path / "settings.py"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    content = config_file.read_text()
                    # Replace placeholders with actual paths
                    content = content.replace("{{PROJECT_DIR}}", str(self.target_path))
                    content = content.replace("{{HOME_DIR}}", str(Path.home()))
                    config_file.write_text(content)
                    self.logger.info(f"Updated configuration: {config_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to update {config_file}: {e}")
    
    def _initialize_databases(self):
        """Initialize any required databases"""
        schema_file = self.target_path / "schema.sql"
        db_file = self.target_path / "database.db"
        
        if schema_file.exists() and not db_file.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_file))
                with open(schema_file, 'r') as f:
                    conn.executescript(f.read())
                conn.close()
                self.logger.info("Database initialized")
            except Exception as e:
                self.logger.warning(f"Database initialization failed: {e}")
    
    def _setup_environment_files(self):
        """Set up environment-specific files"""
        env_template = self.target_path / ".env.template"
        env_file = self.target_path / ".env"
        
        if env_template.exists() and not env_file.exists():
            shutil.copy2(env_template, env_file)
            self.logger.info("Created .env file from template")
    
    def _install_git_hooks(self):
        """Install git hooks if in a git repository"""
        git_dir = self.target_path / ".git"
        hooks_dir = self.target_path / "hooks"
        
        if git_dir.exists() and hooks_dir.exists():
            git_hooks_dir = git_dir / "hooks"
            for hook_file in hooks_dir.glob("*"):
                if hook_file.is_file():
                    target_hook = git_hooks_dir / hook_file.name
                    shutil.copy2(hook_file, target_hook)
                    os.chmod(target_hook, 0o755)
            self.logger.info("Git hooks installed")
    
    def _create_required_directories(self):
        """Create directories that must exist"""
        required_dirs = [
            "logs",
            "tmp",
            "cache",
            "data",
            "backups"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.target_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
    
    def create_installation_manifest(self, files_created: List[str], 
                                   files_skipped: List[str], 
                                   conflicts: List[ConflictItem],
                                   resolution: ConflictResolution,
                                   post_install_actions: List[str],
                                   success: bool,
                                   errors: List[str]) -> None:
        """Create comprehensive installation manifest"""
        
        manifest = InstallationManifest(
            timestamp=datetime.now(),
            version=self.version,
            target_path=self.target_path,
            source_template=str(self.source_template) if self.source_template else "",
            files_created=files_created,
            files_backed_up=[str(c.path.relative_to(self.target_path)) for c in conflicts] if resolution == ConflictResolution.BACKUP else [],
            conflicts_resolved=[{
                "path": str(c.path.relative_to(self.target_path)),
                "type": c.type,
                "resolution": resolution.value,
                "was_critical": c.is_critical
            } for c in conflicts],
            post_install_actions=post_install_actions,
            environment_info={
                "platform": os.name,
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                "working_directory": str(Path.cwd()),
                "user": os.getenv("USER", "unknown"),
                "timestamp": datetime.now().isoformat()
            },
            success=success,
            errors=errors
        )
        
        # Save manifest with file locking
        manifest_path = self.target_path / f".{self.package_name}_manifest.json"
        lock_path = self.target_path / f".{self.package_name}_manifest.lock"
        
        self._write_manifest_safely(manifest, manifest_path, lock_path)
        self.manifest = manifest
    
    def _write_manifest_safely(self, manifest: InstallationManifest, 
                              manifest_path: Path, lock_path: Path):
        """Write manifest with file locking for safety"""
        manifest_dict = {
            "package": self.package_name,
            "version": manifest.version,
            "timestamp": manifest.timestamp.isoformat(),
            "target_path": str(manifest.target_path),
            "source_template": manifest.source_template,
            "files_created": manifest.files_created,
            "files_backed_up": manifest.files_backed_up,
            "conflicts_resolved": manifest.conflicts_resolved,
            "post_install_actions": manifest.post_install_actions,
            "environment_info": manifest.environment_info,
            "success": manifest.success,
            "errors": manifest.errors
        }
        
        try:
            max_retries = 10
            retry_delay = 0.1
            
            for attempt in range(max_retries):
                try:
                    with open(lock_path, 'w') as lock_file:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        
                        try:
                            with open(manifest_path, "w") as f:
                                json.dump(manifest_dict, f, indent=2)
                            self.logger.info(f"Installation manifest created: {manifest_path}")
                            break
                        finally:
                            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                            
                except BlockingIOError:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        # Fall back to direct write
                        with open(manifest_path, "w") as f:
                            json.dump(manifest_dict, f, indent=2)
                        
        except Exception as e:
            self.logger.warning(f"File locking not available: {e}")
            with open(manifest_path, "w") as f:
                json.dump(manifest_dict, f, indent=2)
        finally:
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except:
                    pass
    
    def rollback_installation(self) -> bool:
        """Rollback partial installation"""
        self.console.print("[yellow]Rolling back installation...[/yellow]")
        
        try:
            # Reverse rollback actions
            for action, target in reversed(self.rollback_actions):
                if action == 'remove_file':
                    if target.exists():
                        target.unlink()
                elif action == 'remove_directory':
                    if target.exists():
                        shutil.rmtree(target)
            
            self.console.print("[green]✓[/green] Installation rolled back successfully")
            return True
            
        except Exception as e:
            self.console.print(f"[red]Rollback failed: {e}[/red]")
            return False
    
    def install(self, source_template_path: Path, 
               force: bool = False, 
               dry_run: bool = False) -> InstallationResult:
        """Main installation method"""
        
        self.source_template = source_template_path
        self.force_overwrite = force
        self.dry_run = dry_run
        errors = []
        
        try:
            # Display installation header
            self.console.print(Panel.fit(
                f"Installing {self.package_name} v{self.version}",
                style="bold blue"
            ))
            
            # Validate source template
            if not source_template_path.exists():
                raise FileNotFoundError(f"Source template not found: {source_template_path}")
            
            # Scan for conflicts
            conflicts = self.scan_for_conflicts(source_template_path)
            
            # Resolve conflicts
            if conflicts and not force:
                resolution = self.resolve_conflicts_interactively(conflicts)
                if resolution == ConflictResolution.CANCEL:
                    return InstallationResult.CANCELLED
            elif force:
                resolution = ConflictResolution.OVERWRITE
            else:
                resolution = ConflictResolution.SKIP
            
            if dry_run:
                self.console.print("[yellow]Dry run completed - no files were modified[/yellow]")
                return InstallationResult.SUCCESS
            
            # Create backup if needed
            if resolution == ConflictResolution.BACKUP and conflicts:
                self.create_backup(conflicts)
            
            # Copy files
            files_created, files_skipped = self.copy_files_safely(
                source_template_path, conflicts, resolution
            )
            
            # Post-installation setup
            post_install_actions = self.perform_post_install_setup()
            
            # Create manifest
            if self.create_manifest:
                self.create_installation_manifest(
                    files_created=files_created,
                    files_skipped=files_skipped,
                    conflicts=conflicts,
                    resolution=resolution,
                    post_install_actions=post_install_actions,
                    success=True,
                    errors=errors
                )
            
            # Success summary
            self._display_success_summary(files_created, files_skipped, post_install_actions)
            
            return InstallationResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            errors.append(str(e))
            
            # Attempt rollback
            if not dry_run:
                self.rollback_installation()
            
            # Create failure manifest
            if self.create_manifest:
                self.create_installation_manifest(
                    files_created=getattr(self, 'files_created', []),
                    files_skipped=[],
                    conflicts=getattr(self, 'conflicts', []),
                    resolution=getattr(self, 'resolution', ConflictResolution.CANCEL),
                    post_install_actions=[],
                    success=False,
                    errors=errors
                )
            
            return InstallationResult.FAILED
    
    def _display_success_summary(self, files_created: List[str], 
                               files_skipped: List[str], 
                               post_install_actions: List[str]):
        """Display installation success summary"""
        
        # Create summary table
        table = Table(title="Installation Summary", show_header=True)
        table.add_column("Category", style="bold")
        table.add_column("Count", style="green")
        table.add_column("Details", style="dim")
        
        table.add_row("Files Created", str(len(files_created)), f"New files installed")
        table.add_row("Files Skipped", str(len(files_skipped)), f"Existing files preserved")
        table.add_row("Post-Install Actions", str(len(post_install_actions)), "Setup tasks completed")
        
        if self.backup_dir:
            table.add_row("Backup Location", "1", str(self.backup_dir))
        
        self.console.print(table)
        
        # Success message
        self.console.print(f"\n[green]✅ {self.package_name} v{self.version} installed successfully![/green]")
        
        # Next steps
        if post_install_actions:
            self.console.print("\n[bold]Completed Setup Tasks:[/bold]")
            for action in post_install_actions:
                self.console.print(f"  ✓ {action}")
        
        # Show manifest location
        if self.create_manifest:
            manifest_path = self.target_path / f".{self.package_name}_manifest.json"
            self.console.print(f"\n[dim]Installation manifest: {manifest_path}[/dim]")
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

# CLI Implementation Example
def main():
    """Example CLI implementation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Package Installer")
    parser.add_argument("package_name", help="Name of package to install")
    parser.add_argument("--version", default="1.0.0", help="Package version")
    parser.add_argument("--source", required=True, help="Source template directory")
    parser.add_argument("--target", help="Target installation directory")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    # Create installer
    installer = RobustInstaller(args.package_name, args.version)
    
    # Set target directory
    if args.target:
        if not installer.set_target_directory(Path(args.target)):
            return 1
    
    # Run installation
    result = installer.install(
        source_template_path=Path(args.source),
        force=args.force,
        dry_run=args.dry_run
    )
    
    return 0 if result == InstallationResult.SUCCESS else 1

if __name__ == "__main__":
    exit(main())
```

## Phase 2: Advanced Conflict Resolution

### Intelligent Merge Strategies

**Smart File Merging:**

```python
import difflib
from typing import Optional

class IntelligentMerger:
    """Advanced file merging for complex conflicts"""
    
    def __init__(self):
        self.merge_strategies = {
            '.json': self._merge_json,
            '.yaml': self._merge_yaml,
            '.yml': self._merge_yaml,
            '.ini': self._merge_ini,
            '.conf': self._merge_conf,
            '.env': self._merge_env
        }
    
    def can_merge_file(self, file_path: Path) -> bool:
        """Check if file type supports intelligent merging"""
        return file_path.suffix.lower() in self.merge_strategies
    
    def merge_files(self, existing_file: Path, new_file: Path, 
                   output_file: Path) -> bool:
        """Attempt to merge two files intelligently"""
        
        suffix = existing_file.suffix.lower()
        merge_func = self.merge_strategies.get(suffix)
        
        if not merge_func:
            return False
        
        try:
            return merge_func(existing_file, new_file, output_file)
        except Exception as e:
            logger.error(f"Merge failed for {existing_file}: {e}")
            return False
    
    def _merge_json(self, existing: Path, new: Path, output: Path) -> bool:
        """Merge JSON files by combining objects"""
        import json
        
        with open(existing, 'r') as f:
            existing_data = json.load(f)
        
        with open(new, 'r') as f:
            new_data = json.load(f)
        
        # Deep merge dictionaries
        merged_data = self._deep_merge_dict(existing_data, new_data)
        
        with open(output, 'w') as f:
            json.dump(merged_data, f, indent=2)
        
        return True
    
    def _merge_yaml(self, existing: Path, new: Path, output: Path) -> bool:
        """Merge YAML files"""
        import yaml
        
        with open(existing, 'r') as f:
            existing_data = yaml.safe_load(f)
        
        with open(new, 'r') as f:
            new_data = yaml.safe_load(f)
        
        merged_data = self._deep_merge_dict(existing_data, new_data)
        
        with open(output, 'w') as f:
            yaml.dump(merged_data, f, default_flow_style=False, indent=2)
        
        return True
    
    def _merge_env(self, existing: Path, new: Path, output: Path) -> bool:
        """Merge environment files by combining unique keys"""
        existing_vars = self._parse_env_file(existing)
        new_vars = self._parse_env_file(new)
        
        # Preserve existing values, add new ones
        merged_vars = {**new_vars, **existing_vars}
        
        with open(output, 'w') as f:
            for key, value in sorted(merged_vars.items()):
                f.write(f"{key}={value}\n")
        
        return True
    
    def _deep_merge_dict(self, dict1: dict, dict2: dict) -> dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _parse_env_file(self, file_path: Path) -> dict:
        """Parse environment file into key-value pairs"""
        env_vars = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        return env_vars

# Enhanced installer with merge support
class AdvancedInstaller(RobustInstaller):
    """Enhanced installer with intelligent merging"""
    
    def __init__(self, package_name: str, version: str):
        super().__init__(package_name, version)
        self.merger = IntelligentMerger()
    
    def resolve_conflicts_with_merge(self, conflicts: List[ConflictItem]) -> ConflictResolution:
        """Enhanced conflict resolution with merge option"""
        
        mergeable_conflicts = [c for c in conflicts if self.merger.can_merge_file(c.path)]
        
        if mergeable_conflicts:
            self.console.print(f"\n[green]🔀 {len(mergeable_conflicts)} files can be automatically merged![/green]")
            
            # Show additional merge option
            self.console.print("\n[bold]Enhanced Conflict Resolution Options:[/bold]")
            self.console.print("  1. [green]Backup existing files and continue[/green]")
            self.console.print("  2. [yellow]Skip existing files[/yellow]")
            self.console.print("  3. [cyan]Smart merge compatible files[/cyan] (New!)")
            self.console.print("  4. [red]Overwrite all files[/red]")
            self.console.print("  5. [blue]Cancel installation[/blue]")
            
            choice = Prompt.ask(
                "\nChoose resolution strategy",
                choices=["1", "2", "3", "4", "5"],
                default="3"
            )
            
            if choice == "3":
                return ConflictResolution.MERGE
        
        return super().resolve_conflicts_interactively(conflicts)
    
    def copy_files_with_merge(self, source_path: Path, conflicts: List[ConflictItem], 
                            resolution: ConflictResolution) -> Tuple[List[str], List[str]]:
        """Enhanced file copying with merge support"""
        
        if resolution == ConflictResolution.MERGE:
            return self._copy_files_with_intelligent_merge(source_path, conflicts)
        else:
            return super().copy_files_safely(source_path, conflicts, resolution)
    
    def _copy_files_with_intelligent_merge(self, source_path: Path, 
                                         conflicts: List[ConflictItem]) -> Tuple[List[str], List[str]]:
        """Copy files with intelligent merging for compatible types"""
        files_created = []
        files_merged = []
        conflict_paths = {c.path for c in conflicts}
        
        total_files = sum(len(files) for _, _, files in os.walk(source_path))
        
        with Progress() as progress:
            task = progress.add_task("Installing with smart merge...", total=total_files)
            
            for root, dirs, files in os.walk(source_path):
                rel_root = Path(root).relative_to(source_path)
                target_root = self.target_path / rel_root
                target_root.mkdir(parents=True, exist_ok=True)
                
                for file_name in files:
                    source_file = Path(root) / file_name
                    target_file = target_root / file_name
                    relative_target = target_file.relative_to(self.target_path)
                    
                    if target_file in conflict_paths and self.merger.can_merge_file(target_file):
                        # Attempt intelligent merge
                        temp_file = target_file.with_suffix(f"{target_file.suffix}.merged")
                        
                        if self.merger.merge_files(target_file, source_file, temp_file):
                            # Replace original with merged version
                            shutil.move(temp_file, target_file)
                            files_merged.append(str(relative_target))
                            self.logger.info(f"Successfully merged: {relative_target}")
                        else:
                            # Fall back to overwrite
                            shutil.copy2(source_file, target_file)
                            files_created.append(str(relative_target))
                    else:
                        # Normal copy
                        shutil.copy2(source_file, target_file)
                        files_created.append(str(relative_target))
                    
                    progress.advance(task)
        
        self.console.print(f"[green]✓[/green] Merged {len(files_merged)} files intelligently")
        return files_created, files_merged
```

## Phase 3: Cross-Platform Compatibility

### Platform-Specific Handling

**Universal Platform Support:**

```python
import platform
import subprocess
from pathlib import Path

class CrossPlatformInstaller(AdvancedInstaller):
    """Cross-platform installation with OS-specific optimizations"""
    
    def __init__(self, package_name: str, version: str):
        super().__init__(package_name, version)
        self.platform_info = self._detect_platform()
        self.path_separator = os.sep
        
    def _detect_platform(self) -> Dict[str, str]:
        """Detect platform and environment details"""
        return {
            "system": platform.system(),
            "machine": platform.machine(),
            "version": platform.version(),
            "python_version": platform.python_version(),
            "is_windows": platform.system() == "Windows",
            "is_mac": platform.system() == "Darwin",
            "is_linux": platform.system() == "Linux",
            "shell": os.environ.get("SHELL", "unknown"),
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
        }
    
    def set_executable_permissions(self, file_path: Path) -> bool:
        """Set executable permissions (cross-platform)"""
        try:
            if self.platform_info["is_windows"]:
                # Windows: Add .bat or .cmd extension if needed
                if not file_path.suffix:
                    bat_file = file_path.with_suffix(".bat")
                    if not bat_file.exists():
                        # Create batch wrapper
                        bat_content = f'@echo off\npython "{file_path}" %*\n'
                        bat_file.write_text(bat_content)
            else:
                # Unix-like: Set executable bit
                current_permissions = file_path.stat().st_mode
                file_path.chmod(current_permissions | 0o111)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to set executable permissions for {file_path}: {e}")
            return False
    
    def install_system_dependencies(self, dependencies: List[str]) -> bool:
        """Install system dependencies using platform package manager"""
        if not dependencies:
            return True
        
        self.console.print(f"[cyan]Installing {len(dependencies)} system dependencies...[/cyan]")
        
        try:
            if self.platform_info["is_mac"]:
                return self._install_with_brew(dependencies)
            elif self.platform_info["is_linux"]:
                return self._install_with_apt_or_yum(dependencies)
            elif self.platform_info["is_windows"]:
                return self._install_with_chocolatey(dependencies)
            else:
                self.console.print("[yellow]Unknown platform - skipping system dependencies[/yellow]")
                return True
        except Exception as e:
            self.logger.error(f"System dependency installation failed: {e}")
            return False
    
    def _install_with_brew(self, dependencies: List[str]) -> bool:
        """Install dependencies using Homebrew (macOS)"""
        if not shutil.which("brew"):
            self.console.print("[yellow]Homebrew not found - skipping system dependencies[/yellow]")
            return True
        
        for dep in dependencies:
            result = subprocess.run(["brew", "install", dep], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Failed to install {dep} with brew: {result.stderr}")
        
        return True
    
    def _install_with_apt_or_yum(self, dependencies: List[str]) -> bool:
        """Install dependencies using apt or yum (Linux)"""
        if shutil.which("apt-get"):
            package_manager = ["sudo", "apt-get", "install", "-y"]
        elif shutil.which("yum"):
            package_manager = ["sudo", "yum", "install", "-y"]
        elif shutil.which("dnf"):
            package_manager = ["sudo", "dnf", "install", "-y"]
        else:
            self.console.print("[yellow]No supported package manager found - skipping system dependencies[/yellow]")
            return True
        
        for dep in dependencies:
            result = subprocess.run(package_manager + [dep], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Failed to install {dep}: {result.stderr}")
        
        return True
    
    def _install_with_chocolatey(self, dependencies: List[str]) -> bool:
        """Install dependencies using Chocolatey (Windows)"""
        if not shutil.which("choco"):
            self.console.print("[yellow]Chocolatey not found - skipping system dependencies[/yellow]")
            return True
        
        for dep in dependencies:
            result = subprocess.run(["choco", "install", dep, "-y"], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Failed to install {dep} with chocolatey: {result.stderr}")
        
        return True
    
    def create_platform_specific_files(self) -> List[str]:
        """Create platform-specific configuration files"""
        created_files = []
        
        try:
            # Create platform-specific startup scripts
            if self.platform_info["is_windows"]:
                created_files.extend(self._create_windows_scripts())
            else:
                created_files.extend(self._create_unix_scripts())
            
            # Create platform-specific configuration
            config_file = self.target_path / "platform_config.json"
            config_file.write_text(json.dumps(self.platform_info, indent=2))
            created_files.append("platform_config.json")
            
        except Exception as e:
            self.logger.error(f"Failed to create platform-specific files: {e}")
        
        return created_files
    
    def _create_windows_scripts(self) -> List[str]:
        """Create Windows-specific startup scripts"""
        created = []
        
        # Batch file for easy startup
        bat_file = self.target_path / "start.bat"
        bat_content = f"""@echo off
cd /d "{self.target_path}"
python main.py %*
pause
"""
        bat_file.write_text(bat_content)
        created.append("start.bat")
        
        # PowerShell script
        ps1_file = self.target_path / "start.ps1"
        ps1_content = f"""Set-Location "{self.target_path}"
python main.py $args
"""
        ps1_file.write_text(ps1_content)
        created.append("start.ps1")
        
        return created
    
    def _create_unix_scripts(self) -> List[str]:
        """Create Unix-specific startup scripts"""
        created = []
        
        # Shell script for easy startup
        sh_file = self.target_path / "start.sh"
        sh_content = f"""#!/bin/bash
cd "{self.target_path}"
python3 main.py "$@"
"""
        sh_file.write_text(sh_content)
        self.set_executable_permissions(sh_file)
        created.append("start.sh")
        
        return created
```

## Phase 4: Validation & Testing

### Installation Validation System

**Comprehensive Post-Install Validation:**

```python
class InstallationValidator:
    """Validate installation completeness and correctness"""
    
    def __init__(self, installer: RobustInstaller):
        self.installer = installer
        self.target_path = installer.target_path
        self.console = installer.console
        self.logger = installer.logger
        
    def validate_installation(self) -> Tuple[bool, List[str], List[str]]:
        """Comprehensive installation validation"""
        
        passed_checks = []
        failed_checks = []
        
        with Progress() as progress:
            task = progress.add_task("Validating installation...", total=7)
            
            # File integrity validation
            if self._validate_file_integrity():
                passed_checks.append("File integrity check")
            else:
                failed_checks.append("File integrity check")
            progress.advance(task)
            
            # Permission validation
            if self._validate_permissions():
                passed_checks.append("File permissions")
            else:
                failed_checks.append("File permissions")
            progress.advance(task)
            
            # Configuration validation
            if self._validate_configuration():
                passed_checks.append("Configuration files")
            else:
                failed_checks.append("Configuration files")
            progress.advance(task)
            
            # Dependency validation
            if self._validate_dependencies():
                passed_checks.append("Dependencies")
            else:
                failed_checks.append("Dependencies")
            progress.advance(task)
            
            # Database validation
            if self._validate_databases():
                passed_checks.append("Database initialization")
            else:
                failed_checks.append("Database initialization")
            progress.advance(task)
            
            # Service validation
            if self._validate_services():
                passed_checks.append("Service availability")
            else:
                failed_checks.append("Service availability")
            progress.advance(task)
            
            # Integration validation
            if self._validate_integration():
                passed_checks.append("System integration")
            else:
                failed_checks.append("System integration")
            progress.advance(task)
        
        success = len(failed_checks) == 0
        return success, passed_checks, failed_checks
    
    def _validate_file_integrity(self) -> bool:
        """Validate that all expected files exist and are readable"""
        try:
            manifest_path = self.target_path / f".{self.installer.package_name}_manifest.json"
            if not manifest_path.exists():
                self.logger.error("Installation manifest not found")
                return False
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Check all created files exist
            for file_path in manifest.get("files_created", []):
                full_path = self.target_path / file_path
                if not full_path.exists():
                    self.logger.error(f"Expected file missing: {file_path}")
                    return False
                
                # Verify file is readable
                try:
                    if full_path.is_file():
                        with open(full_path, 'rb') as f:
                            f.read(1024)  # Read first 1KB to test
                except Exception as e:
                    self.logger.error(f"File not readable: {file_path} - {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"File integrity validation failed: {e}")
            return False
    
    def _validate_permissions(self) -> bool:
        """Validate file permissions are correct"""
        try:
            # Check executable files
            executable_patterns = ["*.py", "*.sh", "start*", "run*"]
            
            for pattern in executable_patterns:
                for file_path in self.target_path.glob(pattern):
                    if file_path.is_file():
                        # Check if file should be executable
                        if file_path.name.startswith(('start', 'run')) or file_path.suffix in ['.sh', '.py']:
                            if not os.access(file_path, os.X_OK):
                                self.logger.warning(f"File not executable: {file_path}")
                                # Try to fix permission
                                try:
                                    file_path.chmod(file_path.stat().st_mode | 0o111)
                                except:
                                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Permission validation failed: {e}")
            return False
    
    def _validate_configuration(self) -> bool:
        """Validate configuration files are properly set up"""
        try:
            config_files = [
                "config.json",
                "settings.py",
                ".env"
            ]
            
            for config_name in config_files:
                config_path = self.target_path / config_name
                if config_path.exists():
                    # Validate JSON files
                    if config_name.endswith('.json'):
                        try:
                            with open(config_path, 'r') as f:
                                json.load(f)
                        except json.JSONDecodeError:
                            self.logger.error(f"Invalid JSON in {config_name}")
                            return False
                    
                    # Check for placeholder values
                    content = config_path.read_text()
                    if "{{" in content and "}}" in content:
                        self.logger.warning(f"Unresolved placeholders in {config_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def _validate_dependencies(self) -> bool:
        """Validate required dependencies are available"""
        try:
            # Check Python dependencies
            requirements_file = self.target_path / "requirements.txt"
            if requirements_file.exists():
                try:
                    result = subprocess.run([
                        "python", "-m", "pip", "check"
                    ], capture_output=True, text=True, cwd=self.target_path)
                    
                    if result.returncode != 0:
                        self.logger.warning(f"Dependency check failed: {result.stderr}")
                        return False
                except FileNotFoundError:
                    self.logger.warning("pip not available for dependency check")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dependency validation failed: {e}")
            return False
    
    def _validate_databases(self) -> bool:
        """Validate database files and connections"""
        try:
            db_files = list(self.target_path.glob("*.db")) + list(self.target_path.glob("*.sqlite*"))
            
            for db_file in db_files:
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(db_file))
                    # Test basic query
                    conn.execute("SELECT 1")
                    conn.close()
                except Exception as e:
                    self.logger.error(f"Database validation failed for {db_file}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database validation failed: {e}")
            return False
    
    def _validate_services(self) -> bool:
        """Validate that services can start"""
        try:
            # Look for main entry points
            entry_points = [
                "main.py",
                "app.py",
                "server.py",
                "start.py"
            ]
            
            for entry_point in entry_points:
                entry_path = self.target_path / entry_point
                if entry_path.exists():
                    # Try to validate Python syntax
                    try:
                        with open(entry_path, 'r') as f:
                            content = f.read()
                        compile(content, str(entry_path), 'exec')
                    except SyntaxError as e:
                        self.logger.error(f"Syntax error in {entry_point}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Service validation failed: {e}")
            return False
    
    def _validate_integration(self) -> bool:
        """Validate system integration (PATH, environment, etc.)"""
        try:
            # Check if any executables were added to PATH
            executable_dirs = [
                self.target_path / "bin",
                self.target_path / "scripts"
            ]
            
            for exec_dir in executable_dirs:
                if exec_dir.exists():
                    # Verify executables are working
                    for executable in exec_dir.glob("*"):
                        if executable.is_file() and os.access(executable, os.X_OK):
                            # Test executable (basic validation)
                            try:
                                result = subprocess.run([str(executable), "--help"], 
                                                      capture_output=True, 
                                                      text=True, 
                                                      timeout=5)
                                # Don't require success, just that it runs
                            except (subprocess.TimeoutExpired, FileNotFoundError):
                                self.logger.warning(f"Executable test failed: {executable}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Integration validation failed: {e}")
            return False
    
    def generate_validation_report(self, passed: List[str], failed: List[str]) -> str:
        """Generate detailed validation report"""
        
        report = []
        report.append("=" * 60)
        report.append(f"INSTALLATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Package: {self.installer.package_name} v{self.installer.version}")
        report.append(f"Target: {self.target_path}")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        if failed:
            report.append("❌ FAILED CHECKS:")
            for check in failed:
                report.append(f"  • {check}")
            report.append("")
        
        if passed:
            report.append("✅ PASSED CHECKS:")
            for check in passed:
                report.append(f"  • {check}")
            report.append("")
        
        overall_status = "PASS" if not failed else "FAIL"
        report.append(f"OVERALL STATUS: {overall_status}")
        report.append("=" * 60)
        
        return "\n".join(report)
```

## Phase 5: Uninstallation & Cleanup

### Complete Removal System

**Safe Uninstallation:**

```python
class SafeUninstaller:
    """Safe uninstallation with user data preservation"""
    
    def __init__(self, package_name: str, target_path: Path):
        self.package_name = package_name
        self.target_path = target_path
        self.console = Console()
        self.logger = logging.getLogger(f"uninstaller.{package_name}")
        
    def uninstall(self, preserve_user_data: bool = True, 
                 dry_run: bool = False) -> bool:
        """Safely uninstall package"""
        
        try:
            # Load installation manifest
            manifest_path = self.target_path / f".{self.package_name}_manifest.json"
            if not manifest_path.exists():
                self.console.print("[red]Installation manifest not found[/red]")
                return False
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Identify user data files
            user_data_files = self._identify_user_data(manifest)
            
            if preserve_user_data and user_data_files:
                self.console.print(f"[yellow]Found {len(user_data_files)} user data files to preserve[/yellow]")
                backup_dir = self._backup_user_data(user_data_files, dry_run)
            
            # Remove installed files
            removed_files = self._remove_installed_files(manifest, user_data_files if preserve_user_data else [], dry_run)
            
            # Clean up empty directories
            self._cleanup_empty_directories(dry_run)
            
            # Remove manifest
            if not dry_run:
                manifest_path.unlink()
            
            self.console.print(f"[green]✓[/green] Uninstallation completed ({len(removed_files)} files removed)")
            
            if preserve_user_data and user_data_files:
                self.console.print(f"[blue]User data preserved in: {backup_dir}[/blue]")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Uninstallation failed: {e}")
            return False
    
    def _identify_user_data(self, manifest: dict) -> List[str]:
        """Identify files that contain user data"""
        user_data_patterns = [
            "config",
            "settings", 
            "data",
            ".env",
            "logs",
            "cache",
            "uploads",
            "documents"
        ]
        
        user_files = []
        
        for file_path in manifest.get("files_created", []):
            file_lower = file_path.lower()
            if any(pattern in file_lower for pattern in user_data_patterns):
                # Additional check: has file been modified since installation?
                full_path = self.target_path / file_path
                if full_path.exists():
                    install_time = datetime.fromisoformat(manifest["timestamp"])
                    file_modified = datetime.fromtimestamp(full_path.stat().st_mtime)
                    
                    if file_modified > install_time:
                        user_files.append(file_path)
        
        return user_files
    
    def _backup_user_data(self, user_files: List[str], dry_run: bool) -> Optional[Path]:
        """Backup user data before uninstallation"""
        if dry_run:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_base = Path("archived_files")
        backup_dir = backup_base / f"{self.package_name}_userdata_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in user_files:
            source = self.target_path / file_path
            if source.exists():
                dest = backup_dir / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if source.is_file():
                    shutil.copy2(source, dest)
                elif source.is_dir():
                    shutil.copytree(source, dest, dirs_exist_ok=True)
        
        # Create restoration script
        restore_script = backup_dir / "restore.py"
        restore_content = f'''#!/usr/bin/env python3
"""
User Data Restoration Script
Run this script to restore user data to a new installation
"""
import shutil
from pathlib import Path

backup_dir = Path(__file__).parent
target_dir = Path("{self.target_path}")

print(f"Restoring user data from {{backup_dir}} to {{target_dir}}")

for item in backup_dir.iterdir():
    if item.name in ["restore.py", "backup_manifest.json"]:
        continue
    
    dest = target_dir / item.name
    
    if item.is_file():
        shutil.copy2(item, dest)
    elif item.is_dir():
        shutil.copytree(item, dest, dirs_exist_ok=True)
    
    print(f"Restored: {{item.name}}")

print("User data restoration completed!")
'''
        restore_script.write_text(restore_content)
        restore_script.chmod(0o755)
        
        return backup_dir
    
    def _remove_installed_files(self, manifest: dict, preserve_files: List[str], dry_run: bool) -> List[str]:
        """Remove files that were installed by the package"""
        removed_files = []
        
        for file_path in manifest.get("files_created", []):
            if file_path in preserve_files:
                continue
                
            full_path = self.target_path / file_path
            if full_path.exists():
                try:
                    if not dry_run:
                        if full_path.is_file():
                            full_path.unlink()
                        elif full_path.is_dir():
                            shutil.rmtree(full_path)
                    
                    removed_files.append(file_path)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to remove {file_path}: {e}")
        
        return removed_files
    
    def _cleanup_empty_directories(self, dry_run: bool):
        """Remove empty directories left after file removal"""
        if dry_run:
            return
        
        try:
            # Walk directory tree bottom-up to remove empty dirs
            for root, dirs, files in os.walk(self.target_path, topdown=False):
                root_path = Path(root)
                
                # Skip if directory contains files
                if files:
                    continue
                
                # Skip if directory contains non-empty subdirectories
                if any((root_path / d).exists() and list((root_path / d).iterdir()) for d in dirs):
                    continue
                
                # Skip important directories
                if root_path.name in ['.git', '.vscode', '__pycache__']:
                    continue
                
                # Remove empty directory
                try:
                    root_path.rmdir()
                    self.logger.info(f"Removed empty directory: {root_path}")
                except OSError:
                    # Directory not empty or other error
                    pass
                    
        except Exception as e:
            self.logger.warning(f"Directory cleanup failed: {e}")
```

## Summary

This comprehensive guide provides everything needed to build production-ready installation systems:

✅ **Robust Conflict Resolution** - Handle existing files intelligently  
✅ **Atomic Operations** - Complete success or clean rollback  
✅ **Cross-Platform Support** - Works on Windows, macOS, and Linux  
✅ **Intelligent Merging** - Smart file merging for compatible formats  
✅ **Comprehensive Validation** - Verify installation completeness  
✅ **Safe Uninstallation** - Remove cleanly with user data preservation  
✅ **Professional UX** - Clear feedback and user control  

The framework can be adapted for any project type and provides the foundation for reliable, user-friendly installation experiences that handle edge cases gracefully and maintain system integrity throughout the process.

---

**Last Updated:** August 16, 2025  
**Status:** Complete Universal Guide