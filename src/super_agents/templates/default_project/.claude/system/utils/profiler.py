#!/usr/bin/env python3
"""
Performance profiling utilities for CLI reliability improvements.

Implements the roadmap requirement for systematic performance measurement
and baseline establishment.
"""

import cProfile
import pstats
import time
import json
import functools
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from rich.console import Console
from rich.table import Table

console = Console()

class PerformanceProfiler:
    """Performance profiler with baseline tracking and reporting."""
    
    def __init__(self, baseline_file: str = ".claude/performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.profiler = None
        self.start_time = None
        
    def start_profiling(self):
        """Start performance profiling."""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.start_time = time.time()
        
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return results."""
        if self.profiler is None:
            return {}
            
        end_time = time.time()
        self.profiler.disable()
        
        # Create stats object
        stats = pstats.Stats(self.profiler)
        stats.sort_stats('cumulative')
        
        # Extract key metrics
        total_time = end_time - self.start_time
        total_calls = stats.total_calls
        
        # Get top time consumers
        stats.sort_stats('tottime')
        top_functions = []
        
        for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:10]:
            top_functions.append({
                "function": f"{func[0]}:{func[1]}({func[2]})",
                "total_time": tt,
                "cumulative_time": ct,
                "calls": cc,
                "time_per_call": tt / cc if cc > 0 else 0
            })
        
        return {
            "total_time": total_time,
            "total_calls": total_calls,
            "top_functions": top_functions,
            "timestamp": time.time()
        }
    
    def save_baseline(self, command: str, results: Dict[str, Any]):
        """Save performance baseline for a command."""
        baselines = self.load_baselines()
        baselines[command] = results
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baselines, f, indent=2)
            
    def load_baselines(self) -> Dict[str, Any]:
        """Load existing performance baselines."""
        if not self.baseline_file.exists():
            return {}
            
        try:
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    
    def compare_with_baseline(self, command: str, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current results with baseline."""
        baselines = self.load_baselines()
        
        if command not in baselines:
            return {"status": "no_baseline", "message": "No baseline found for this command"}
        
        baseline = baselines[command]
        current_time = current_results["total_time"]
        baseline_time = baseline["total_time"]
        
        if baseline_time == 0:
            return {"status": "invalid_baseline", "message": "Invalid baseline time"}
        
        improvement = (baseline_time - current_time) / baseline_time * 100
        
        return {
            "status": "compared",
            "baseline_time": baseline_time,
            "current_time": current_time,
            "improvement_percent": improvement,
            "regression": improvement < -3,  # 3% tolerance as per roadmap
            "significant_improvement": improvement > 10
        }
    
    def print_results(self, command: str, results: Dict[str, Any], comparison: Optional[Dict[str, Any]] = None):
        """Print profiling results in a nice format."""
        console.print(f"\n[bold cyan]Performance Profile: {command}[/bold cyan]")
        
        # Basic metrics table
        metrics_table = Table(title="Performance Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="magenta")
        
        metrics_table.add_row("Total Time", f"{results['total_time']:.3f}s")
        metrics_table.add_row("Total Calls", f"{results['total_calls']:,}")
        
        if comparison and comparison["status"] == "compared":
            improvement = comparison["improvement_percent"]
            if improvement > 0:
                metrics_table.add_row("vs Baseline", f"[green]+{improvement:.1f}% faster[/green]")
            else:
                color = "red" if comparison["regression"] else "yellow"
                metrics_table.add_row("vs Baseline", f"[{color}]{improvement:.1f}% slower[/{color}]")
        
        console.print(metrics_table)
        
        # Top functions table
        if results["top_functions"]:
            func_table = Table(title="Top 10 Time Consumers")
            func_table.add_column("Function", style="cyan")
            func_table.add_column("Total Time", style="magenta")
            func_table.add_column("Calls", style="green")
            func_table.add_column("Time/Call", style="yellow")
            
            for func in results["top_functions"]:
                func_table.add_row(
                    func["function"].split("/")[-1],  # Show just filename part
                    f"{func['total_time']:.3f}s",
                    f"{func['calls']:,}",
                    f"{func['time_per_call']:.6f}s"
                )
            
            console.print(func_table)

@contextmanager
def profile_command(command: str, save_baseline: bool = False, compare: bool = True):
    """Context manager for profiling CLI commands."""
    profiler = PerformanceProfiler()
    
    profiler.start_profiling()
    try:
        yield profiler
    finally:
        results = profiler.stop_profiling()
        
        if results:
            comparison = None
            if compare:
                comparison = profiler.compare_with_baseline(command, results)
            
            if save_baseline:
                profiler.save_baseline(command, results)
                console.print(f"[green]Baseline saved for command: {command}[/green]")
            
            profiler.print_results(command, results, comparison)

def profile_function(func: Callable) -> Callable:
    """Decorator to profile individual functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = PerformanceProfiler()
        profiler.start_profiling()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            profile_results = profiler.stop_profiling()
            if profile_results:
                console.print(f"[dim]Function {func.__name__} took {profile_results['total_time']:.3f}s[/dim]")
    
    return wrapper

def time_function(func: Callable) -> Callable:
    """Lightweight timing decorator."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            end_time = time.time()
            console.print(f"[dim]{func.__name__}: {end_time - start_time:.3f}s[/dim]")
    
    return wrapper

class PerformanceMonitor:
    """Monitor for tracking performance metrics over time."""
    
    def __init__(self, metrics_file: str = ".claude/performance_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
    
    def record_metric(self, command: str, metric_name: str, value: float):
        """Record a performance metric."""
        metrics = self.load_metrics()
        
        if command not in metrics:
            metrics[command] = {}
        
        if metric_name not in metrics[command]:
            metrics[command][metric_name] = []
        
        metrics[command][metric_name].append({
            "value": value,
            "timestamp": time.time()
        })
        
        # Keep only last 100 measurements
        metrics[command][metric_name] = metrics[command][metric_name][-100:]
        
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def load_metrics(self) -> Dict[str, Any]:
        """Load existing metrics."""
        if not self.metrics_file.exists():
            return {}
        
        try:
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    
    def get_average(self, command: str, metric_name: str, last_n: int = 10) -> Optional[float]:
        """Get average of last N measurements."""
        metrics = self.load_metrics()
        
        if command not in metrics or metric_name not in metrics[command]:
            return None
        
        recent_values = [
            m["value"] for m in metrics[command][metric_name][-last_n:]
        ]
        
        if not recent_values:
            return None
        
        return sum(recent_values) / len(recent_values)

# Global monitor instance
monitor = PerformanceMonitor()