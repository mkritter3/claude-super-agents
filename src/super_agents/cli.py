#!/usr/bin/env python3
"""
Super Agents CLI - Main command-line interface
"""

import click
import os
import sys
import subprocess
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from super_agents import __version__
from super_agents.commands.init import initialize_project
from super_agents.commands.upgrade import upgrade_project
from super_agents.commands.km_manager import KnowledgeManagerController
from super_agents.commands.status import show_status

console = Console()


@click.group(invoke_without_command=True)
@click.option('--wild', is_flag=True, help="Run Claude with '--dangerously-skip-permissions'")
@click.option('--stop', is_flag=True, help="Stop the Knowledge Manager")
@click.option('--status', is_flag=True, help="Show status of current project's AET system")
@click.option('--list', is_flag=True, help="List all projects with running KM instances")
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, wild, stop, status, list):
    """
    Super Agents - Autonomous Engineering Team (AET) System
    
    A production-ready multi-agent orchestration system with true autonomous operations.
    """
    # Handle direct flags
    if stop:
        km = KnowledgeManagerController()
        km.stop()
        return
    
    if status:
        show_status()
        return
    
    if list:
        km = KnowledgeManagerController()
        km.list_all_instances()
        return
    
    # If no command specified, run default behavior
    if ctx.invoked_subcommand is None:
        # Default behavior: init if needed, start KM, launch Claude
        run_default(wild)


def run_default(wild=False):
    """Default behavior when no subcommand is given"""
    from super_agents.commands.init import check_project_initialized
    
    # Check if project is initialized
    if not check_project_initialized():
        console.print("[yellow]No AET agents found - initializing project...[/yellow]")
        if not initialize_project():
            console.print("[red]Failed to initialize project[/red]")
            sys.exit(1)
    else:
        console.print("[green]✓[/green] AET agents already configured in this project")
    
    # Start Knowledge Manager
    km = KnowledgeManagerController()
    km_port = km.start()
    
    if not km_port:
        console.print("[red]Failed to start Knowledge Manager[/red]")
        sys.exit(1)
    
    # Launch Claude
    console.print("\n" + "═" * 60)
    console.print("  🚀 Launching Claude with AET agents...")
    console.print("═" * 60)
    console.print(f"\nProject: {os.getcwd()}")
    console.print(f"Knowledge Manager: http://localhost:{km_port}/health\n")
    
    # Show available agents
    try:
        agents_dir = Path(".claude/agents")
        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*.md"))
            if agent_files:
                console.print("Available agents:")
                for agent_file in sorted(agent_files):
                    console.print(f"  • {agent_file.stem}")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not list agents: {e}[/yellow]")
    
    console.print("\nPress Ctrl+C to exit Claude and stop services")
    console.print("═" * 60 + "\n")
    
    # Launch Claude
    try:
        # Check if claude command exists
        claude_path = shutil.which("claude")
        if not claude_path:
            console.print("[red]Error: 'claude' command not found![/red]")
            console.print("[yellow]Please ensure Claude Code is installed and in your PATH[/yellow]")
            console.print("[dim]Visit: https://claude.ai/code for installation instructions[/dim]")
            return
            
        if wild:
            console.print("[yellow]🐺 Launching Claude in WILD mode (--dangerously-skip-permissions)[/yellow]")
            subprocess.run(["claude", "--dangerously-skip-permissions"], check=False)
        else:
            console.print("[green]Launching Claude with normal security permissions[/green]")
            subprocess.run(["claude"], check=False)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Error launching Claude: {e}[/red]")
    
    # After Claude exits, ask about stopping KM
    console.print("")
    if click.confirm("Stop Knowledge Manager?", default=True):
        km.stop()
    else:
        console.print(f"[green]Knowledge Manager left running on port {km_port}[/green]")
        console.print("[dim]Stop later with: super-agents --stop[/dim]")


@main.command()
@click.option('--force', is_flag=True, help="Force initialization even if files exist")
def init(force):
    """Initialize a new project with AET agents"""
    if initialize_project(force=force):
        console.print("[green]✓[/green] Project initialized successfully!")
    else:
        console.print("[red]✗[/red] Failed to initialize project")
        sys.exit(1)


@main.command()
@click.option('--backup-dir', help="Custom backup directory path")
def upgrade(backup_dir):
    """Upgrade an existing project to the latest version"""
    if upgrade_project(backup_dir=backup_dir):
        console.print("[green]✓[/green] Project upgraded successfully!")
    else:
        console.print("[red]✗[/red] Failed to upgrade project")
        sys.exit(1)


@main.command()
def status():
    """Show detailed status of the current project"""
    show_status()


@main.command()
def stop():
    """Stop the Knowledge Manager for this project"""
    km = KnowledgeManagerController()
    km.stop()


@main.command()
def list():
    """List all projects with running KM instances"""
    km = KnowledgeManagerController()
    km.list_all_instances()


@main.command()
def recover():
    """Run error recovery system"""
    console.print(Panel.fit("🔧 Running AET Error Recovery", style="bold yellow"))
    
    recovery_script = Path(".claude/system/error_recovery.py")
    if recovery_script.exists():
        subprocess.run([sys.executable, str(recovery_script), "--recover"])
    else:
        console.print("[red]Error recovery system not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
def monitor():
    """Monitor process health"""
    console.print(Panel.fit("📊 AET Process Monitor", style="bold cyan"))
    
    monitor_script = Path(".claude/system/process_manager.py")
    if monitor_script.exists():
        subprocess.run([sys.executable, str(monitor_script), "--monitor"])
    else:
        console.print("[red]Process manager not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
def validate():
    """Validate system integrity"""
    console.print(Panel.fit("✅ AET System Validation", style="bold green"))
    
    validate_script = Path(".claude/system/atomic_operations.py")
    if validate_script.exists():
        console.print("\n[bold]Event Log:[/bold]")
        subprocess.run([sys.executable, str(validate_script), "--validate-log"])
        console.print("\n[bold]Trigger Files:[/bold]")
        subprocess.run([sys.executable, str(validate_script), "--validate-triggers"])
    else:
        console.print("[red]Atomic operations system not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
def security():
    """Security audit and management"""
    console.print(Panel.fit("🔒 AET Security Manager", style="bold red"))
    
    security_script = Path(".claude/system/security_manager.py")
    if security_script.exists():
        subprocess.run([sys.executable, str(security_script), "--audit-report"])
    else:
        console.print("[red]Security manager not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
def optimize():
    """Model optimization matrix"""
    console.print(Panel.fit("🎯 AET Model Optimizer", style="bold magenta"))
    
    optimizer_script = Path(".claude/system/model_optimizer.py")
    if optimizer_script.exists():
        subprocess.run([sys.executable, str(optimizer_script), "--matrix"])
    else:
        console.print("[red]Model optimizer not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
def parallel():
    """Start parallel executor with worker pool"""
    console.print(Panel.fit("⚡ AET Parallel Executor (Phase 1.1)", style="bold yellow"))
    
    parallel_script = Path(".claude/system/parallel_executor.py")
    if parallel_script.exists():
        console.print("Starting parallel executor with optimal worker count...")
        subprocess.run([sys.executable, str(parallel_script), "--start"])
    else:
        console.print("[red]Parallel executor not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
@click.argument('task_spec')
def submit(task_spec):
    """
    Submit task for parallel execution
    
    TASK_SPEC format: AGENT:TASK
    Example: developer-agent:implement_feature
    """
    parallel_script = Path(".claude/system/parallel_executor.py")
    if parallel_script.exists():
        subprocess.run([sys.executable, str(parallel_script), "--submit", task_spec])
    else:
        console.print("[red]Parallel executor not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
def queue_stats():
    """Show parallel queue statistics"""
    console.print(Panel.fit("📊 Parallel Queue Statistics", style="bold cyan"))
    
    parallel_script = Path(".claude/system/parallel_executor.py")
    if parallel_script.exists():
        subprocess.run([sys.executable, str(parallel_script), "--stats"])
    else:
        console.print("[red]Parallel executor not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


@main.command()
@click.argument('task_id')
def task(task_id):
    """Check status of specific task"""
    parallel_script = Path(".claude/system/parallel_executor.py")
    if parallel_script.exists():
        subprocess.run([sys.executable, str(parallel_script), "--status", task_id])
    else:
        console.print("[red]Parallel executor not found[/red]")
        console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")


if __name__ == '__main__':
    main()