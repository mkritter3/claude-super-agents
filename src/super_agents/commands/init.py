"""
Initialize command - Sets up a new project with AET agents
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from importlib import resources
from rich.console import Console
from rich.prompt import Confirm

console = Console()


def check_project_initialized() -> bool:
    """Check if the current project has been initialized with AET agents"""
    # Check for key files/directories
    claude_dir = Path(".claude")
    claude_md = Path("CLAUDE.md")
    
    if not claude_dir.exists() or not claude_md.exists():
        return False
    
    # Check for agents
    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        return False
    
    # Count agent files
    agent_count = len(list(agents_dir.glob("*.md")))
    
    # Full configuration requires 23 agents + CLAUDE.md
    return agent_count >= 23


def create_manifest(files_created: List[str]) -> None:
    """Create a manifest file tracking all created files"""
    manifest = {
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "files": files_created,
        "metadata": {
            "project_path": os.getcwd(),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        }
    }
    
    manifest_path = Path(".super_agents_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    console.print("[dim]Created manifest file: .super_agents_manifest.json[/dim]")


def copy_template_files(source_path: Path, dest_path: Path, force: bool = False) -> List[str]:
    """
    Copy template files from package to destination with safety checks
    Returns list of created files for manifest
    """
    files_created = []
    conflicts = []
    
    # First, scan for conflicts
    for root, dirs, files in os.walk(source_path):
        rel_root = Path(root).relative_to(source_path)
        dest_root = dest_path / rel_root
        
        for file_name in files:
            dest_file = dest_root / file_name
            if dest_file.exists() and not force:
                conflicts.append(str(dest_file.relative_to(dest_path)))
    
    # Handle conflicts
    if conflicts and not force:
        console.print("\n[yellow]⚠ The following files already exist:[/yellow]")
        for conflict in conflicts[:10]:  # Show first 10
            console.print(f"  • {conflict}")
        if len(conflicts) > 10:
            console.print(f"  ... and {len(conflicts) - 10} more files")
        
        console.print("\n[bold]Options:[/bold]")
        console.print("  1. Backup existing files and continue")
        console.print("  2. Skip existing files")
        console.print("  3. Cancel initialization")
        
        choice = console.input("\nChoose an option [1/2/3]: ")
        
        if choice == "3":
            console.print("[red]Initialization cancelled[/red]")
            return []
        elif choice == "1":
            # Create backup
            backup_dir = Path(f".super_agents_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            backup_dir.mkdir(exist_ok=True)
            console.print(f"[green]Creating backup in {backup_dir}[/green]")
            
            for conflict in conflicts:
                src = dest_path / conflict
                dst = backup_dir / conflict
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            
            force = True  # Now we can overwrite
        # Choice 2 means we skip existing files (force remains False)
    
    # Copy files
    for root, dirs, files in os.walk(source_path):
        rel_root = Path(root).relative_to(source_path)
        dest_root = dest_path / rel_root
        
        # Create directories
        dest_root.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for file_name in files:
            src_file = Path(root) / file_name
            dest_file = dest_root / file_name
            
            if dest_file.exists() and not force:
                console.print(f"[dim]Skipping existing file: {dest_file.relative_to(dest_path)}[/dim]")
                continue
            
            shutil.copy2(src_file, dest_file)
            files_created.append(str(dest_file.relative_to(dest_path)))
            
            # Make scripts executable
            if file_name.endswith(('.py', '.sh')) or file_name == 'aet':
                os.chmod(dest_file, 0o755)
    
    return files_created


def setup_context7_integration() -> None:
    """Setup Context7 documentation integration hooks"""
    console.print("[cyan]Setting up Context7 documentation integration...[/cyan]")
    
    settings_file = Path(".claude/settings.json")
    settings = {}
    
    # Load existing settings if present
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        except:
            settings = {}
    
    # Add hooks configuration
    if 'hooks' not in settings:
        settings['hooks'] = {}
    
    if 'PreToolUse' not in settings['hooks']:
        settings['hooks']['PreToolUse'] = []
    
    # Check if Context7 hook already exists
    context7_hook_exists = False
    for hook_group in settings['hooks']['PreToolUse']:
        if hook_group.get('matcher') == 'Task':
            for hook in hook_group.get('hooks', []):
                if 'context7-fetch.py' in hook.get('command', ''):
                    context7_hook_exists = True
                    break
    
    # Add Context7 hook if not present
    if not context7_hook_exists:
        context7_hook = {
            'matcher': 'Task',
            'hooks': [{
                'type': 'command',
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/context7-fetch.py',
                'timeout': 15
            }]
        }
        settings['hooks']['PreToolUse'].append(context7_hook)
        
        # Write back to file
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        console.print("[green]✓[/green] Context7 integration configured")
    else:
        console.print("[dim]Context7 integration already configured[/dim]")


def initialize_database() -> None:
    """Initialize the registry database"""
    db_path = Path(".claude/registry/registry.db")
    schema_path = Path(".claude/system/schema.sql")
    
    if schema_path.exists():
        import sqlite3
        
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        
        conn.close()
        console.print("[green]✓[/green] Database initialized")


def initialize_project(force: bool = False) -> bool:
    """
    Initialize a new project with AET agents
    Returns True on success, False on failure
    """
    try:
        console.print("\n[bold cyan]Initializing AET project...[/bold cyan]\n")
        
        dest_path = Path.cwd()
        
        # Access template files from package
        import super_agents
        package_dir = Path(super_agents.__file__).parent
        
        # Check if we're running from source (development) or installed package
        if (package_dir / "templates").exists():
            # Running from source
            template_path = package_dir / "templates" / "default_project"
        else:
            # Try to use importlib.resources (Python 3.9+)
            try:
                import importlib.resources as pkg_resources
                
                with pkg_resources.as_file(
                    pkg_resources.files('super_agents').joinpath('templates/default_project')
                ) as template_path:
                    if not template_path.exists():
                        # Fallback: copy from original project directory
                        console.print("[yellow]Template files not found in package, using source directory[/yellow]")
                        source_dir = Path(__file__).parent.parent.parent.parent  # Go up to project root
                        
                        # Create template directory structure
                        template_dest = package_dir / "templates" / "default_project"
                        template_dest.mkdir(parents=True, exist_ok=True)
                        
                        # Copy necessary files
                        if (source_dir / ".claude").exists():
                            shutil.copytree(source_dir / ".claude", template_dest / ".claude", dirs_exist_ok=True)
                        if (source_dir / "CLAUDE.md").exists():
                            shutil.copy2(source_dir / "CLAUDE.md", template_dest / "CLAUDE.md")
                        
                        template_path = template_dest
                    
                    # Copy template files
                    files_created = copy_template_files(template_path, dest_path, force)
                    
            except (ImportError, AttributeError):
                # Python < 3.9 fallback
                console.print("[yellow]Using legacy resource access method[/yellow]")
                
                # For now, require templates to be in package directory
                template_path = package_dir / "templates" / "default_project"
                if not template_path.exists():
                    console.print("[red]Template files not found. Please reinstall the package.[/red]")
                    return False
                
                files_created = copy_template_files(template_path, dest_path, force)
        
        if not files_created and not force:
            return False
        
        # Create essential directories if they don't exist
        essential_dirs = [
            ".claude/events",
            ".claude/workspaces", 
            ".claude/snapshots",
            ".claude/registry",
            ".claude/backups",
            ".claude/dlq",
            ".claude/adr",
            ".claude/summaries",
            ".claude/commands",
            ".claude/logs",
            ".claude/state",
            ".claude/triggers",
            ".claude/ambient",
            ".claude/test_reports",
            ".claude/monitoring",
            ".claude/hooks"
        ]
        
        for dir_path in essential_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize event log
        event_log = Path(".claude/events/log.ndjson")
        if not event_log.exists():
            event_log.touch()
        
        # Initialize tasks snapshot
        tasks_file = Path(".claude/snapshots/tasks.json")
        if not tasks_file.exists():
            with open(tasks_file, 'w') as f:
                json.dump({}, f)
        
        # Initialize database
        initialize_database()
        
        # Setup Context7 integration
        setup_context7_integration()
        
        # Create manifest
        if files_created:
            create_manifest(files_created)
        
        console.print("\n[green]✓[/green] AET agents installed successfully!")
        console.print(f"[dim]Created {len(files_created)} files[/dim]")
        
        # Show next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Run 'super-agents' to start the system")
        console.print("  2. Use 'super-agents --help' to see all commands")
        console.print("  3. Check CLAUDE.md for orchestration instructions")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error during initialization: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False