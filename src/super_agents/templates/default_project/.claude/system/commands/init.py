"""
Initialize command - Sets up a new project with AET agents
"""

import os
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Use performance optimizations from template system
from performance.lazy_loader import lazy_import
from performance.caching import cached, cached_file_read

# Lazy imports for better performance
json = lazy_import('json', critical=True)
shutil = lazy_import('shutil')
fcntl = lazy_import('fcntl')
subprocess = lazy_import('subprocess', critical=True)
resources = lazy_import('importlib.resources')
rich_console = lazy_import('rich.console')
rich_prompt = lazy_import('rich.prompt')

# Create console lazily
def get_console():
    if not hasattr(get_console, '_console'):
        Console = rich_console.Console
        get_console._console = Console()
    return get_console._console

console = get_console()


def detect_python_executable() -> str:
    """
    Detect the correct Python executable that has required dependencies.
    Returns the full path to a working Python executable.
    """
    candidates = [
        # Try pipx super-agents environment first (preferred)
        "/Users/michaelritter/.local/pipx/venvs/super-agents/bin/python",
        # Try user's local Python installations
        os.path.expanduser("~/.local/pipx/venvs/super-agents/bin/python"),
        # Try system Python with brew
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        # Current Python interpreter
        sys.executable,
        # Fallback to system python3
        "python3",
    ]
    
    for python_path in candidates:
        if python_path.startswith("/") and not os.path.exists(python_path):
            continue
            
        try:
            # Test if this Python has the requests module
            result = subprocess.run([
                python_path, "-c", "import requests; print('OK')"
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                console.print(f"[dim]Using Python: {python_path}[/dim]")
                return python_path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    # If no Python with requests found, warn user and use system Python
    console.print("[yellow]Warning: No Python installation with 'requests' module found.[/yellow]")
    console.print("[yellow]You may need to install dependencies: pip install requests[/yellow]")
    return "python3"


@cached(ttl=60)  # Cache for 1 minute
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


def calculate_file_hash(file_path: Path) -> str:
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


def create_manifest(files_created: List[str], backups_created: List[tuple] = None) -> None:
    """Create a manifest file tracking all created files with hashes for cleanup system"""
    import hashlib
    
    # Separate files and directories
    managed_files = []
    managed_directories = set()
    
    for file_path_str in files_created:
        file_path = Path(file_path_str)
        
        if file_path.exists() and file_path.is_file():
            # Calculate hash of the file
            file_hash = calculate_file_hash(file_path)
            
            managed_files.append({
                "path": file_path_str,
                "template_hash_sha256": file_hash,
                "executable": os.access(file_path, os.X_OK)
            })
            
            # Add parent directories to the set
            parent = file_path.parent
            while parent != Path('.'):
                managed_directories.add(str(parent))
                parent = parent.parent
    
    # Convert directories set to sorted list for consistent ordering
    managed_directories = sorted(managed_directories)
    
    # Format backup information
    overwritten_files = []
    if backups_created:
        for original_path, backup_path in backups_created:
            overwritten_files.append({
                "original_path": original_path,
                "backup_path": backup_path
            })
    
    manifest = {
        "schema_version": "1.0",
        "init_timestamp_utc": datetime.now().isoformat() + "Z",
        "managed_assets": {
            "directories": managed_directories,
            "files": managed_files
        },
        "overwritten_files": overwritten_files,
        "metadata": {
            "project_path": os.getcwd(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "total_files": len(managed_files),
            "total_directories": len(managed_directories)
        }
    }
    
    manifest_path = Path(".claude/.super_agents_manifest.json")
    lock_path = Path(".claude/.super_agents_manifest.lock")
    
    # Use file locking to prevent concurrent writes (Unix/Linux/macOS only)
    # On Windows, file locking works differently, so we'll gracefully degrade
    try:
        max_retries = 10
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Create or open lock file
                with open(lock_path, 'w') as lock_file:
                    # Try to acquire exclusive lock (non-blocking)
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    
                    # Write manifest while holding lock
                    try:
                        with open(manifest_path, "w") as f:
                            json.dump(manifest, f, indent=2)
                        console.print("[dim]Created manifest file: .super_agents_manifest.json[/dim]")
                        break
                    finally:
                        # Release lock
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                        
            except BlockingIOError:
                # Another process has the lock, wait and retry
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    console.print("[yellow]Warning: Could not acquire lock for manifest file after retries[/yellow]")
                    # Fall back to direct write
                    with open(manifest_path, "w") as f:
                        json.dump(manifest, f, indent=2)
            except Exception as e:
                console.print(f"[yellow]Warning: File locking not available, writing directly[/yellow]")
                # Fall back to direct write (Windows or other systems without fcntl)
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)
                break
    except (ImportError, AttributeError):
        # fcntl not available (Windows), write directly
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        console.print("[dim]Created manifest file: .super_agents_manifest.json[/dim]")
    
    # Clean up lock file if it exists
    try:
        if lock_path.exists():
            lock_path.unlink()
    except:
        pass


def copy_template_files(source_path: Path, dest_path: Path, force: bool = False, python_executable: str = None) -> tuple[List[str], List[tuple]]:
    """
    Copy template files from package to destination with safety checks and robust error handling
    Returns tuple of (files_created, backups_created) for manifest
    """
    files_created = []
    backups_created = []
    conflicts = []
    
    # Check write permissions on destination
    try:
        test_file = dest_path / ".write_test_temp"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        console.print(f"[red]Error: No write permissions in {dest_path}[/red]")
        console.print("[yellow]Please check directory permissions or choose a different location[/yellow]")
        return [], []
    except OSError as e:
        console.print(f"[red]Error: Cannot write to {dest_path}: {e}[/red]")
        return [], []
    
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
            return [], []
        elif choice == "1":
            # Create organized backup in .claude/.backups directory
            backup_dir = Path(".claude/.backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Creating backups in {backup_dir}[/green]")
            
            for conflict in conflicts:
                try:
                    src = dest_path / conflict
                    # Create backup with timestamp to avoid collisions
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_filename = f"{timestamp}_{Path(conflict).name}.bak"
                    dst = backup_dir / backup_filename
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    
                    # Track the backup for manifest
                    backups_created.append((conflict, str(dst.relative_to(dest_path))))
                    console.print(f"[dim]Backed up: {conflict} -> {dst.relative_to(dest_path)}[/dim]")
                except (PermissionError, OSError) as e:
                    console.print(f"[yellow]Warning: Could not backup {conflict}: {e}[/yellow]")
            
            # Create a backup manifest for easy reference
            manifest = {
                "backup_created": datetime.now().isoformat(),
                "original_location": str(dest_path),
                "files_backed_up": conflicts,
                "backup_reason": "super-agents initialization conflict resolution"
            }
            
            with open(backup_dir / "backup_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            console.print(f"[dim]Backup manifest created: {backup_dir}/backup_manifest.json[/dim]")
            force = True  # Now we can overwrite
        # Choice 2 means we skip existing files (force remains False)
    
    # Copy files
    for root, dirs, files in os.walk(source_path):
        rel_root = Path(root).relative_to(source_path)
        dest_root = dest_path / rel_root
        
        # Create directories with error handling
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            console.print(f"[red]Error: Cannot create directory {dest_root}[/red]")
            continue
        except OSError as e:
            console.print(f"[red]Error creating directory {dest_root}: {e}[/red]")
            continue
        
        # Copy files with error handling
        for file_name in files:
            src_file = Path(root) / file_name
            dest_file = dest_root / file_name
            
            if dest_file.exists() and not force:
                console.print(f"[dim]Skipping existing file: {dest_file.relative_to(dest_path)}[/dim]")
                continue
            
            try:
                # Handle template files with substitution
                if file_name == '.mcp.json' and python_executable:
                    # Read template content and substitute Python executable
                    with open(src_file, 'r') as f:
                        content = f.read()
                    
                    # Substitute the Python executable placeholder
                    content = content.replace('{{PYTHON_EXECUTABLE}}', python_executable)
                    
                    # Write the processed content
                    with open(dest_file, 'w') as f:
                        f.write(content)
                    
                    console.print(f"[dim]Processed template: {dest_file.relative_to(dest_path)} (Python: {python_executable})[/dim]")
                else:
                    # Regular file copy
                    shutil.copy2(src_file, dest_file)
                
                files_created.append(str(dest_file.relative_to(dest_path)))
                
                # Make scripts executable
                if file_name.endswith(('.py', '.sh')) or file_name == 'aet':
                    os.chmod(dest_file, 0o755)
            except PermissionError:
                console.print(f"[yellow]Warning: Permission denied copying {file_name}[/yellow]")
            except OSError as e:
                if e.errno == 28:  # No space left on device
                    console.print(f"[red]Error: No space left on device[/red]")
                    return files_created, backups_created
                else:
                    console.print(f"[yellow]Warning: Could not copy {file_name}: {e}[/yellow]")
    
    return files_created


def setup_mcp_configuration() -> None:
    """Setup MCP configuration for the Knowledge Manager"""
    console.print("[cyan]Setting up MCP configuration...[/cyan]")
    
    # Update mcp_config.json with current project directory
    mcp_config_file = Path(".claude/mcp_config.json")
    if mcp_config_file.exists():
        try:
            with open(mcp_config_file, 'r') as f:
                config = json.load(f)
            
            # Replace placeholder with actual project directory
            config['project_dir'] = str(Path.cwd())
            
            with open(mcp_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            console.print("[green]✓[/green] MCP configuration updated")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not update MCP config: {e}[/yellow]")
    
    # Check if .mcp.json was created from template, if not create it
    mcp_file = Path(".mcp.json")
    if not mcp_file.exists():
        # This should normally be created from template, but create as fallback
        python_executable = detect_python_executable()
        
        mcp_config = {
            "mcpServers": {
                "km": {
                    "command": python_executable,
                    "args": [".claude/km_bridge_local.py"]
                }
            }
        }
        
        with open(mcp_file, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        console.print(f"[green]✓[/green] Claude Code MCP configuration created (using {python_executable})")
    else:
        console.print("[green]✓[/green] Claude Code MCP configuration ready")


# Context7 integration removed - no longer needed in template


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
        
        # Detect the correct Python executable for MCP bridge
        python_executable = detect_python_executable()
        
        # Access template files from package
        import super_agents
        package_dir = Path(super_agents.__file__).parent
        
        # Check if we're running from source (development) or installed package
        files_created = []
        backups_created = []
        if (package_dir / "templates").exists():
            # Running from source
            template_path = package_dir / "templates" / "default_project"
            files_created, backups_created = copy_template_files(template_path, dest_path, force, python_executable)
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
                        
                        # Copy necessary files only if template doesn't exist
                        # This prevents duplication of .claude subdirectories
                        if not (template_dest / ".claude").exists():
                            if (source_dir / ".claude").exists():
                                shutil.copytree(source_dir / ".claude", template_dest / ".claude", dirs_exist_ok=True)
                        if not (template_dest / "CLAUDE.md").exists():
                            if (source_dir / "CLAUDE.md").exists():
                                shutil.copy2(source_dir / "CLAUDE.md", template_dest / "CLAUDE.md")
                        
                        template_path = template_dest
                    
                    # Copy template files
                    files_created, backups_created = copy_template_files(template_path, dest_path, force, python_executable)
                    
            except (ImportError, AttributeError):
                # Python < 3.9 fallback
                console.print("[yellow]Using legacy resource access method[/yellow]")
                
                # For now, require templates to be in package directory
                template_path = package_dir / "templates" / "default_project"
                if not template_path.exists():
                    console.print("[red]Template files not found. Please reinstall the package.[/red]")
                    return False
                
                files_created, backups_created = copy_template_files(template_path, dest_path, force, python_executable)
        
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
        
        # Setup MCP configuration
        setup_mcp_configuration()
        
        # Context7 integration removed
        
        # Create manifest
        if files_created:
            create_manifest(files_created, backups_created)
        
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