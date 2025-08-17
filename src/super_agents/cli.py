#!/usr/bin/env python3
"""
Super Agents CLI - Streamlined command-line interface that delegates to template
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from super_agents import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.option('--stop', is_flag=True, help="Stop the Knowledge Manager")
@click.option('--status', is_flag=True, help="Show status of current project's AET system")
@click.option('--list', is_flag=True, help="List all projects with running KM instances")
@click.option('--profile', is_flag=True, help="Enable performance profiling")
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, stop, status, list, profile):
    """
    Super Agents - Autonomous Engineering Team (AET) System
    
    A production-ready multi-agent orchestration system with true autonomous operations.
    """
    # Store options in context for delegation
    ctx.ensure_object(dict)
    ctx.obj['profile'] = profile
    
    # Handle direct flags by delegating to template
    if stop:
        delegate_to_template('stop')
        return
    
    if status:
        delegate_to_template('status')
        return
    
    if list:
        delegate_to_template('list')
        return
    
    # If no command specified, run default behavior
    if ctx.invoked_subcommand is None:
        # Default behavior: ensure project is initialized, then start
        if not is_project_initialized():
            console.print("[yellow]No AET agents found - initializing project...[/yellow]")
            if not initialize_project():
                console.print("[red]Failed to initialize project[/red]")
                sys.exit(1)
        
        # Delegate to template for startup
        delegate_to_template('start', ['--profile'] if profile else [])


def is_project_initialized() -> bool:
    """Check if the current directory has been initialized with AET"""
    return Path('.claude').exists() and Path('.claude/system').exists()


def initialize_project() -> bool:
    """Initialize a new project by copying the template"""
    try:
        # Find the template directory
        template_source = get_template_path()
        if not template_source:
            console.print("[red]Could not find template directory[/red]")
            return False
        
        current_dir = Path.cwd()
        
        # Use template's proper initialization system with Python executable substitution
        console.print("Copying AET template...")
        
        # Add template system to path to import copy_template_files
        sys.path.insert(0, str(template_source / '.claude/system'))
        
        try:
            from commands.init import copy_template_files, create_manifest
            
            # Find Python executable
            python_executable = shutil.which('python3') or shutil.which('python') or sys.executable
            
            # Copy template files with proper substitution
            files_created, backups_created = copy_template_files(
                template_source, 
                current_dir, 
                force=False,
                python_executable=python_executable
            )
            
            # Create manifest for cleanup system
            create_manifest(files_created, backups_created)
            
            console.print("[green]✓[/green] AET template copied successfully")
            make_scripts_executable()
            return True
            
        except ImportError as e:
            console.print(f"[red]Error importing template initialization: {e}[/red]")
            return False
        finally:
            # Remove template system from path
            if str(template_source / '.claude/system') in sys.path:
                sys.path.remove(str(template_source / '.claude/system'))
        
    except Exception as e:
        console.print(f"[red]Error during initialization: {e}[/red]")
        return False


def get_template_path() -> Path:
    """Find the template directory in the installed package"""
    try:
        # Try to find template relative to this file
        current_file = Path(__file__)
        template_path = current_file.parent / "templates" / "default_project"
        
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


def make_scripts_executable():
    """Make key scripts executable"""
    scripts = [
        ".claude/aet",
        ".claude/aet_status.sh", 
        ".claude/setup.sh",
        ".claude/km_bridge_local.py"
    ]
    
    for script in scripts:
        script_path = Path(script)
        if script_path.exists():
            script_path.chmod(0o755)


def delegate_to_template(command: str, extra_args: list = None):
    """Delegate a command to the template's command system"""
    if extra_args is None:
        extra_args = []
        
    # Check if project is initialized
    if not is_project_initialized():
        console.print("[red]Project not initialized. Run 'super-agents init' first.[/red]")
        sys.exit(1)
    
    # Add .claude/system to Python path and run the command
    template_commands = Path('.claude/system/commands')
    if not template_commands.exists():
        console.print("[red]Template commands not found. Run 'super-agents upgrade'.[/red]")
        sys.exit(1)
    
    # Import and run the template command
    sys.path.insert(0, str(Path('.claude/system')))
    
    try:
        if command == 'start':
            from commands.km_manager import KnowledgeManagerController
            from commands.init import check_project_initialized
            
            # Start the Knowledge Manager using template logic
            console.print("[green]✓[/green] AET agents already configured in this project")
            km = KnowledgeManagerController()
            km_port = km.start()
            
            if not km_port:
                console.print("[red]Failed to start Knowledge Manager[/red]")
                sys.exit(1)
            
            # Show ready message
            show_ready_message(km_port)
            
        elif command == 'stop':
            from commands.km_manager import KnowledgeManagerController
            km = KnowledgeManagerController()
            km.stop()
            
        elif command == 'status':
            from commands.status import show_status
            show_status()
            
        elif command == 'list':
            from commands.km_manager import KnowledgeManagerController
            km = KnowledgeManagerController()
            km.list_all_instances()
            
        elif command == 'cleanup':
            from commands.cleanup import SuperAgentsCleanup
            cleanup_system = SuperAgentsCleanup()
            
            # Parse arguments from extra_args
            force = '--force' in extra_args
            dry_run = '--dry-run' in extra_args
            
            success = cleanup_system.cleanup(force=force, dry_run=dry_run)
            sys.exit(0 if success else 1)
            
    except ImportError as e:
        console.print(f"[red]Failed to import template command: {e}[/red]")
        console.print("[dim]Try running 'super-agents upgrade' to update the template[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")
        sys.exit(1)


def show_ready_message(km_port: int):
    """Show the system ready message"""
    console.print("\n" + "═" * 60)
    console.print("  📊 AET System Ready")
    console.print("═" * 60)
    console.print(f"\nProject: {os.getcwd()}")
    console.print(f"Knowledge Manager: http://localhost:{km_port}/health")
    console.print(f"MCP Configuration: Ready for Claude Code integration\n")
    
    # Show available agents
    try:
        agents_dir = Path(".claude/agents")
        if agents_dir.exists() and agents_dir.is_dir():
            agent_files = [f for f in agents_dir.glob("*.md") if f.is_file()]
            if agent_files:
                console.print("Available agents:")
                for agent_file in sorted(agent_files):
                    agent_name = agent_file.stem
                    console.print(f"  • {agent_name}")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not list agents: {e}[/yellow]")
    
    console.print("\nNext steps:")
    console.print("  • Run 'claude' in this directory to start Claude Code with MCP integration")
    console.print("  • Use 'super-agents --stop' to stop the Knowledge Manager")
    console.print("  • Use 'super-agents status' to check system health")
    console.print("═" * 60)


@main.command()
@click.option('--force', is_flag=True, help="Force initialization even if files exist")
def init(force):
    """Initialize a new project with AET agents"""
    if is_project_initialized() and not force:
        console.print("[yellow]Project already initialized. Use --force to reinitialize.[/yellow]")
        return
    
    if initialize_project():
        console.print("[green]✓[/green] Project initialized successfully!")
        console.print("[dim]Run 'super-agents' to start the system[/dim]")
    else:
        console.print("[red]✗[/red] Failed to initialize project")
        sys.exit(1)


@main.command()
@click.option('--backup-dir', help="Custom backup directory path")
def upgrade(backup_dir):
    """Upgrade an existing project to the latest version"""
    delegate_to_template('upgrade', ['--backup-dir', backup_dir] if backup_dir else [])


@main.command()
@click.option('--force', is_flag=True, help="Skip confirmation prompts")
@click.option('--dry-run', is_flag=True, help="Show what would be done without making changes")
def cleanup(force, dry_run):
    """Clean up super-agents installation and restore original files"""
    delegate_to_template('cleanup', 
                        (['--force'] if force else []) + 
                        (['--dry-run'] if dry_run else []))


@main.command()
def status():
    """Show detailed status of the current project"""
    delegate_to_template('status')


@main.command()
def stop():
    """Stop the Knowledge Manager for this project"""
    delegate_to_template('stop')


@main.command()
def list():
    """List all projects with running KM instances"""
    delegate_to_template('list')


# All other commands delegate to template scripts
@main.command()
def recover():
    """Run error recovery system"""
    run_template_script('error_recovery.py', ['--recover'])


@main.command()
def monitor():
    """Monitor process health"""
    run_template_script('process_manager.py', ['--monitor'])


@main.command()
def validate():
    """Validate system integrity"""
    run_template_script('atomic_operations.py', ['--validate-log'])


@main.command()
def security():
    """Security audit and management"""
    run_template_script('security_manager.py', ['--audit-report'])


@main.command()
def optimize():
    """Model optimization matrix"""
    run_template_script('model_optimizer.py', ['--matrix'])


@main.command()
def parallel():
    """Start parallel executor with worker pool"""
    run_template_script('parallel_executor.py', ['--start'])


@main.command()
@click.argument('task_spec')
def submit(task_spec):
    """Submit task for parallel execution"""
    run_template_script('parallel_executor.py', ['--submit', task_spec])


@main.command()
def queue_stats():
    """Show parallel queue statistics"""
    run_template_script('parallel_executor.py', ['--stats'])


@main.command()
@click.argument('task_id')
def task(task_id):
    """Check status of specific task"""
    run_template_script('parallel_executor.py', ['--status', task_id])


def run_template_script(script_name: str, args: list = None):
    """Run a script from the template system directory"""
    if not is_project_initialized():
        console.print("[red]Project not initialized. Run 'super-agents init' first.[/red]")
        sys.exit(1)
    
    script_path = Path(f".claude/system/{script_name}")
    if not script_path.exists():
        console.print(f"[red]{script_name} not found[/red]")
        console.print("[dim]Run 'super-agents upgrade' to update the template[/dim]")
        sys.exit(1)
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    subprocess.run(cmd)


if __name__ == '__main__':
    main()