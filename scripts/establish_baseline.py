#!/usr/bin/env python3
"""
Baseline establishment script for CLI performance profiling.

This script establishes performance baselines for the top 5 CLI commands
as required by the roadmap.
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Top 5 commands to baseline based on usage patterns
COMMANDS_TO_BASELINE = [
    {
        "name": "main",
        "command": ["super-agents", "--profile", "--save-baseline"],
        "description": "Default command (start system)"
    },
    {
        "name": "init", 
        "command": ["super-agents", "init", "--profile", "--save-baseline", "--force"],
        "description": "Project initialization"
    },
    {
        "name": "status",
        "command": ["super-agents", "status", "--profile", "--save-baseline"],
        "description": "System status check"
    },
    {
        "name": "stop",
        "command": ["super-agents", "--stop", "--profile", "--save-baseline"],
        "description": "Stop Knowledge Manager"
    },
    {
        "name": "upgrade",
        "command": ["super-agents", "upgrade", "--profile", "--save-baseline"],
        "description": "Project upgrade"
    }
]

def run_command_with_timeout(cmd, timeout=30):
    """Run a command with timeout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def establish_baselines():
    """Establish performance baselines for major commands."""
    console.print("[bold cyan]Establishing Performance Baselines[/bold cyan]")
    console.print("This will run each major command 3 times and average the results.\n")
    
    baseline_file = Path(".claude/performance_baseline.json")
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for cmd_info in COMMANDS_TO_BASELINE:
            task = progress.add_task(f"Baselining {cmd_info['name']}...", total=None)
            
            console.print(f"\n[yellow]Running baseline for: {cmd_info['description']}[/yellow]")
            
            times = []
            for i in range(3):
                console.print(f"  Run {i+1}/3...")
                start_time = time.time()
                
                success, stdout, stderr = run_command_with_timeout(cmd_info["command"])
                
                end_time = time.time()
                run_time = end_time - start_time
                times.append(run_time)
                
                if not success:
                    console.print(f"  [red]Warning: Command failed on run {i+1}[/red]")
                    console.print(f"  [dim]Error: {stderr}[/dim]")
                else:
                    console.print(f"  [green]✓[/green] Completed in {run_time:.3f}s")
                
                # Brief pause between runs
                time.sleep(1)
            
            # Calculate average
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                results[cmd_info["name"]] = {
                    "average_time": avg_time,
                    "min_time": min_time,
                    "max_time": max_time,
                    "runs": times,
                    "description": cmd_info["description"],
                    "timestamp": time.time()
                }
                
                console.print(f"  [bold green]Baseline: {avg_time:.3f}s average ({min_time:.3f}s - {max_time:.3f}s)[/bold green]")
            
            progress.remove_task(task)
    
    # Save results
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    console.print(f"\n[bold green]✓ Baselines saved to {baseline_file}[/bold green]")
    
    # Print summary
    console.print("\n[bold cyan]Performance Baseline Summary[/bold cyan]")
    for name, data in results.items():
        console.print(f"  {name}: {data['average_time']:.3f}s - {data['description']}")
    
    return results

def validate_baselines():
    """Validate that baselines were established correctly."""
    baseline_file = Path(".claude/performance_baseline.json")
    
    if not baseline_file.exists():
        console.print("[red]No baseline file found![/red]")
        return False
    
    try:
        with open(baseline_file, 'r') as f:
            baselines = json.load(f)
        
        console.print(f"[green]Found baselines for {len(baselines)} commands:[/green]")
        
        for name, data in baselines.items():
            avg_time = data.get('average_time', 0)
            description = data.get('description', 'Unknown')
            console.print(f"  ✓ {name}: {avg_time:.3f}s ({description})")
        
        return len(baselines) >= 3  # At least 3 commands baselined
        
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[red]Invalid baseline file: {e}[/red]")
        return False

def main():
    """Main baseline establishment process."""
    console.print("[bold]CLI Performance Baseline Establishment[/bold]")
    console.print("=" * 50)
    
    # Check if we're in a super-agents project
    if not Path("pyproject.toml").exists():
        console.print("[yellow]Warning: Not in super-agents project root[/yellow]")
        console.print("Please run this script from the project root directory.")
        return 1
    
    # Establish baselines
    try:
        results = establish_baselines()
        
        if validate_baselines():
            console.print("\n[bold green]✓ Baseline establishment successful![/bold green]")
            console.print("You can now use --profile on commands to compare against baseline.")
            return 0
        else:
            console.print("\n[red]✗ Baseline validation failed[/red]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Baseline establishment cancelled[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error during baseline establishment: {e}[/red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())