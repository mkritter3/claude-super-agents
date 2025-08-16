"""
Status command - Shows detailed status of the current project
"""

import os
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout

console = Console()


def check_agents_configured() -> tuple[int, int]:
    """
    Check agent configuration status
    Returns (status_code, agent_count)
    status_code: 0=fully configured, 1=partial, 2=not configured
    """
    claude_dir = Path(".claude")
    claude_md = Path("CLAUDE.md")
    
    if not claude_dir.exists():
        return (2, 0)
    
    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        return (2, 0)
    
    # Count agent files
    agent_count = len(list(agents_dir.glob("*.md")))
    
    # Full configuration requires 23 agents + CLAUDE.md
    if agent_count >= 23 and claude_md.exists():
        return (0, agent_count)
    elif agent_count > 0:
        return (1, agent_count)
    else:
        return (2, 0)


def get_km_status() -> dict:
    """Get Knowledge Manager status"""
    status = {
        "running": False,
        "port": None,
        "pid": None,
        "responding": False
    }
    
    port_file = Path(".claude/km.port")
    pid_file = Path(".claude/km.pid")
    
    if port_file.exists() and pid_file.exists():
        try:
            status["port"] = int(port_file.read_text().strip())
            status["pid"] = int(pid_file.read_text().strip())
            
            # Check if process is running
            os.kill(status["pid"], 0)
            status["running"] = True
            
            # Test if responding
            try:
                import urllib.request
                response = urllib.request.urlopen(f"http://localhost:{status['port']}/health", timeout=2)
                if response.status == 200:
                    status["responding"] = True
            except:
                pass
                
        except (ValueError, OSError):
            pass
    
    return status


def get_event_statistics() -> dict:
    """Get autonomous event statistics"""
    stats = {
        "total_events": 0,
        "recent_events": [],
        "event_types": {}
    }
    
    event_log = Path(".claude/events/log.ndjson")
    
    if event_log.exists():
        lines = event_log.read_text().strip().split('\n')
        stats["total_events"] = len(lines)
        
        # Parse recent events
        for line in lines[-5:]:  # Last 5 events
            try:
                event = json.loads(line)
                stats["recent_events"].append({
                    "timestamp": event.get("timestamp", ""),
                    "type": event.get("event_type", ""),
                    "agent": event.get("agent", "")
                })
                
                # Count event types
                event_type = event.get("event_type", "unknown")
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
            except:
                continue
    
    return stats


def get_system_health() -> dict:
    """Get overall system health metrics"""
    health = {
        "agents": "Unknown",
        "km": "Unknown",
        "database": "Unknown",
        "hooks": "Unknown"
    }
    
    # Check agents
    config_status, agent_count = check_agents_configured()
    if config_status == 0:
        health["agents"] = f"Healthy ({agent_count} agents)"
    elif config_status == 1:
        health["agents"] = f"Partial ({agent_count} agents)"
    else:
        health["agents"] = "Not configured"
    
    # Check KM
    km_status = get_km_status()
    if km_status["responding"]:
        health["km"] = f"Healthy (port {km_status['port']})"
    elif km_status["running"]:
        health["km"] = "Running but not responding"
    else:
        health["km"] = "Not running"
    
    # Check database
    db_path = Path(".claude/registry/registry.db")
    if db_path.exists():
        health["database"] = f"Present ({db_path.stat().st_size // 1024} KB)"
    else:
        health["database"] = "Not initialized"
    
    # Check hooks
    hooks_dir = Path(".claude/hooks")
    if hooks_dir.exists():
        hook_count = len(list(hooks_dir.glob("*")))
        health["hooks"] = f"Configured ({hook_count} hooks)"
    else:
        health["hooks"] = "Not configured"
    
    return health


def show_status():
    """Display comprehensive status information"""
    
    # Create header
    console.print("\n" + "═" * 60)
    console.print("  📊 [bold cyan]AET System Status[/bold cyan]")
    console.print("═" * 60 + "\n")
    
    # Project info
    console.print(f"[bold]Project:[/bold] {os.getcwd()}")
    console.print(f"[bold]Time:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # System Health
    health = get_system_health()
    health_table = Table(title="System Components", show_header=True, header_style="bold magenta")
    health_table.add_column("Component", style="cyan", width=20)
    health_table.add_column("Status", width=40)
    
    for component, status in health.items():
        style = "green" if "Healthy" in status else "yellow" if "Running" in status or "Present" in status else "red"
        health_table.add_row(component.capitalize(), f"[{style}]{status}[/{style}]")
    
    console.print(health_table)
    console.print()
    
    # Knowledge Manager Details
    km_status = get_km_status()
    if km_status["running"]:
        km_panel = Panel.fit(
            f"[green]Running[/green] on port {km_status['port']} (PID: {km_status['pid']})\n"
            f"Status: {'[green]Responding[/green]' if km_status['responding'] else '[yellow]Not responding[/yellow]'}\n"
            f"URL: http://localhost:{km_status['port']}/health",
            title="Knowledge Manager",
            border_style="green" if km_status["responding"] else "yellow"
        )
    else:
        km_panel = Panel.fit(
            "[red]Not running[/red]\n"
            "Start with: super-agents",
            title="Knowledge Manager",
            border_style="red"
        )
    
    console.print(km_panel)
    console.print()
    
    # Autonomous Events
    event_stats = get_event_statistics()
    if event_stats["total_events"] > 0:
        events_table = Table(title="Autonomous Events", show_header=True, header_style="bold cyan")
        events_table.add_column("Timestamp", style="dim", width=20)
        events_table.add_column("Type", width=20)
        events_table.add_column("Agent", width=20)
        
        for event in event_stats["recent_events"]:
            timestamp = event.get("timestamp", "Unknown")
            if isinstance(timestamp, (int, float)):
                timestamp = str(timestamp)
            events_table.add_row(
                timestamp[-8:] if timestamp and timestamp != "Unknown" else "Unknown",
                event.get("type", "Unknown"),
                event.get("agent", "System")
            )
        
        console.print(events_table)
        console.print(f"\n[dim]Total events: {event_stats['total_events']}[/dim]")
    else:
        console.print("[yellow]No autonomous events recorded yet[/yellow]")
    
    console.print()
    
    # Available Agents
    agents_dir = Path(".claude/agents")
    if agents_dir.exists():
        agent_files = sorted(agents_dir.glob("*.md"))
        if agent_files:
            console.print("[bold]Available Agents:[/bold]")
            
            # Group agents by category
            categories = {
                "core": [],
                "operational": [],
                "infrastructure": [],
                "fullstack": []
            }
            
            for agent_file in agent_files:
                agent_name = agent_file.stem
                
                if agent_name in ["pm-agent", "architect-agent", "developer-agent", "reviewer-agent", "integrator-agent"]:
                    categories["core"].append(agent_name)
                elif agent_name in ["contract-guardian", "test-executor", "monitoring-agent", "documentation-agent", 
                                   "data-migration-agent", "performance-optimizer-agent", "incident-response-agent"]:
                    categories["operational"].append(agent_name)
                elif agent_name in ["builder-agent", "dependency-agent", "filesystem-guardian", 
                                   "integration-tester", "verifier-agent"]:
                    categories["infrastructure"].append(agent_name)
                else:
                    categories["fullstack"].append(agent_name)
            
            for category, agents in categories.items():
                if agents:
                    console.print(f"\n  [cyan]{category.capitalize()} Agents:[/cyan]")
                    for agent in agents:
                        console.print(f"    • {agent}")
    
    # Quick Actions
    console.print("\n[bold]Quick Actions:[/bold]")
    console.print("  • Start system: [cyan]super-agents[/cyan]")
    console.print("  • Stop KM: [cyan]super-agents --stop[/cyan]")
    console.print("  • Upgrade: [cyan]super-agents upgrade[/cyan]")
    console.print("  • View help: [cyan]super-agents --help[/cyan]")
    
    console.print("\n" + "═" * 60 + "\n")