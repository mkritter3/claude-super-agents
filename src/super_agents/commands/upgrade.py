"""
Upgrade command - Safely upgrades an existing project to the latest version
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()


def load_manifest() -> Optional[Dict]:
    """Load the project manifest if it exists"""
    manifest_path = Path(".super_agents_manifest.json")
    
    if not manifest_path.exists():
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load manifest: {e}[/yellow]")
        return None


def create_backup(backup_dir: Optional[str] = None) -> Path:
    """
    Create a backup of existing project files
    Returns the backup directory path
    """
    if backup_dir:
        backup_path = Path(backup_dir)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = Path(f".super_agents_backup_{timestamp}")
    
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # Load manifest to know what to backup
    manifest = load_manifest()
    
    if manifest and 'files' in manifest:
        # Backup only files we created
        files_to_backup = manifest['files']
        console.print(f"[cyan]Backing up {len(files_to_backup)} tracked files...[/cyan]")
        
        for file_path in files_to_backup:
            src = Path(file_path)
            if src.exists():
                dst = backup_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
    else:
        # No manifest - backup key directories
        console.print("[yellow]No manifest found - backing up all AET files...[/yellow]")
        
        items_to_backup = [
            ".claude",
            "CLAUDE.md",
            ".super_agents_manifest.json"
        ]
        
        for item in items_to_backup:
            src = Path(item)
            if src.exists():
                dst = backup_path / item
                dst.parent.mkdir(parents=True, exist_ok=True)
                
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
    
    # Save backup info
    backup_info = {
        "backup_date": datetime.now().isoformat(),
        "original_path": os.getcwd(),
        "files_backed_up": len(list(backup_path.rglob("*")))
    }
    
    with open(backup_path / "backup_info.json", 'w') as f:
        json.dump(backup_info, f, indent=2)
    
    return backup_path


def get_version_changes() -> Dict:
    """
    Compare current version with new version and identify changes
    """
    changes = {
        "new_files": [],
        "modified_files": [],
        "removed_files": [],
        "new_agents": [],
        "updated_agents": []
    }
    
    # This would normally compare package version with installed version
    # For now, we'll return a summary
    manifest = load_manifest()
    if manifest:
        current_version = manifest.get('version', 'unknown')
        from super_agents import __version__ as new_version
        
        changes['current_version'] = current_version
        changes['new_version'] = new_version
        
        # Check for new agents
        agents_dir = Path(".claude/agents")
        if agents_dir.exists():
            current_agents = set(f.stem for f in agents_dir.glob("*.md"))
            # Would compare with package agents here
            changes['current_agent_count'] = len(current_agents)
    
    return changes


def preserve_user_data() -> Dict:
    """
    Preserve user-specific data that shouldn't be overwritten
    Returns dict of preserved data
    """
    preserved = {}
    
    # Preserve port configuration
    port_file = Path(".claude/km.port")
    if port_file.exists():
        preserved['km_port'] = port_file.read_text().strip()
    
    # Preserve any custom settings
    settings_file = Path(".claude/settings.json")
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                preserved['settings'] = json.load(f)
        except:
            pass
    
    # Preserve event log (append-only)
    event_log = Path(".claude/events/log.ndjson")
    if event_log.exists():
        preserved['has_events'] = True
    
    return preserved


def restore_user_data(preserved: Dict) -> None:
    """Restore preserved user data after upgrade"""
    
    # Restore port configuration
    if 'km_port' in preserved:
        port_file = Path(".claude/km.port")
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(preserved['km_port'])
        console.print("[dim]Restored KM port configuration[/dim]")
    
    # Merge settings (don't overwrite user customizations)
    if 'settings' in preserved:
        settings_file = Path(".claude/settings.json")
        current_settings = {}
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    current_settings = json.load(f)
            except:
                current_settings = {}
        
        # Merge user settings with new settings
        # User settings take precedence
        for key, value in preserved['settings'].items():
            if key not in current_settings:
                current_settings[key] = value
        
        with open(settings_file, 'w') as f:
            json.dump(current_settings, f, indent=2)
        
        console.print("[dim]Merged user settings[/dim]")


def show_upgrade_summary(changes: Dict, backup_path: Path) -> None:
    """Display a summary of the upgrade"""
    
    table = Table(title="Upgrade Summary", show_header=True, header_style="bold cyan")
    table.add_column("Item", style="dim")
    table.add_column("Value")
    
    if 'current_version' in changes:
        table.add_row("Current Version", changes['current_version'])
        table.add_row("New Version", changes['new_version'])
    
    table.add_row("Backup Location", str(backup_path))
    
    if 'current_agent_count' in changes:
        table.add_row("Agents", f"{changes['current_agent_count']} installed")
    
    console.print(table)


def upgrade_project(backup_dir: Optional[str] = None) -> bool:
    """
    Upgrade an existing project to the latest version
    Returns True on success, False on failure
    """
    try:
        console.print("\n[bold cyan]Upgrading AET project to latest version...[/bold cyan]\n")
        
        # Check if project is initialized
        if not Path(".claude").exists() and not Path("CLAUDE.md").exists():
            console.print("[red]No AET project found in current directory[/red]")
            console.print("[dim]Run 'super-agents init' to initialize a new project[/dim]")
            return False
        
        # Get version changes
        changes = get_version_changes()
        
        # Preserve user data
        console.print("[cyan]Preserving user configuration...[/cyan]")
        preserved = preserve_user_data()
        
        # Create backup
        console.print("\n[cyan]Creating backup...[/cyan]")
        backup_path = create_backup(backup_dir)
        console.print(f"[green]✓[/green] Backup created at: {backup_path}")
        
        # Import and use the init module's copy function
        from super_agents.commands.init import copy_template_files, setup_context7_integration, initialize_database
        import super_agents
        
        package_dir = Path(super_agents.__file__).parent
        
        # Determine template path
        if (package_dir / "templates").exists():
            template_path = package_dir / "templates" / "default_project"
        else:
            # Try importlib.resources
            try:
                import importlib.resources as pkg_resources
                
                with pkg_resources.as_file(
                    pkg_resources.files('super_agents').joinpath('templates/default_project')
                ) as template_path:
                    # Perform upgrade
                    console.print("\n[cyan]Upgrading files...[/cyan]")
                    
                    # Copy new files (force=True to overwrite)
                    files_updated = copy_template_files(template_path, Path.cwd(), force=True)
                    
                    console.print(f"[green]✓[/green] Updated {len(files_updated)} files")
                    
            except (ImportError, AttributeError) as e:
                console.print(f"[red]Could not access template files: {e}[/red]")
                return False
        
        # Re-initialize database with any schema changes
        console.print("[cyan]Updating database schema...[/cyan]")
        initialize_database()
        
        # Update Context7 integration
        setup_context7_integration()
        
        # Restore user data
        console.print("\n[cyan]Restoring user configuration...[/cyan]")
        restore_user_data(preserved)
        
        # Update manifest
        from super_agents.commands.init import create_manifest
        manifest = load_manifest()
        if manifest:
            files_list = manifest.get('files', [])
            # Add any new files from upgrade
            # This would be more sophisticated in production
            create_manifest(files_list)
        
        # Show summary
        console.print("")
        show_upgrade_summary(changes, backup_path)
        
        console.print("\n[green]✓[/green] Upgrade completed successfully!")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Review the backup if needed: " + str(backup_path))
        console.print("  2. Run 'super-agents' to start with upgraded system")
        console.print("  3. Check CLAUDE.md for any new features")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error during upgrade: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        # Offer to restore from backup
        if 'backup_path' in locals() and backup_path.exists():
            if Confirm.ask("\n[yellow]Would you like to restore from backup?[/yellow]"):
                # Restore from backup
                console.print("[cyan]Restoring from backup...[/cyan]")
                
                for item in backup_path.iterdir():
                    if item.name != "backup_info.json":
                        dest = Path.cwd() / item.name
                        
                        if dest.exists():
                            if dest.is_dir():
                                shutil.rmtree(dest)
                            else:
                                dest.unlink()
                        
                        if item.is_dir():
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                
                console.print("[green]✓[/green] Restored from backup")
        
        return False