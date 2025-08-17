#!/usr/bin/env python3
"""
Performance validation script for CLI performance improvements.

This script validates that performance optimizations meet the roadmap targets:
- 20% startup time improvement
- 10% runtime performance improvement

Runs comparative benchmarks between optimized and unoptimized code paths.
"""

import os
import sys
import time
import json
import subprocess
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

class PerformanceBenchmark:
    """Performance benchmarking framework."""
    
    def __init__(self, iterations: int = 5):
        self.iterations = iterations
        self.results = {}
        
    def time_operation(self, name: str, operation: callable, *args, **kwargs) -> Dict[str, float]:
        """Time an operation multiple times and return statistics."""
        times = []
        
        for _ in range(self.iterations):
            start_time = time.perf_counter()
            operation(*args, **kwargs)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0,
            'min': min(times),
            'max': max(times),
            'samples': times
        }
    
    def compare_operations(self, baseline_name: str, optimized_name: str, 
                          baseline_op: callable, optimized_op: callable,
                          *args, **kwargs) -> Dict[str, Any]:
        """Compare two operations and calculate improvement."""
        console.print(f"[cyan]Benchmarking: {baseline_name} vs {optimized_name}[/cyan]")
        
        # Benchmark baseline
        baseline_stats = self.time_operation(baseline_name, baseline_op, *args, **kwargs)
        
        # Benchmark optimized
        optimized_stats = self.time_operation(optimized_name, optimized_op, *args, **kwargs)
        
        # Calculate improvement
        baseline_time = baseline_stats['mean']
        optimized_time = optimized_stats['mean']
        improvement_percent = ((baseline_time - optimized_time) / baseline_time) * 100
        
        result = {
            'baseline': baseline_stats,
            'optimized': optimized_stats,
            'improvement_percent': improvement_percent,
            'improvement_ratio': baseline_time / optimized_time if optimized_time > 0 else 0,
            'meets_target': False
        }
        
        self.results[f"{baseline_name}_vs_{optimized_name}"] = result
        return result

def benchmark_module_imports():
    """Benchmark module import performance."""
    benchmark = PerformanceBenchmark(iterations=10)
    
    def normal_imports():
        """Normal import approach."""
        import json
        import subprocess
        import sqlite3
        import shutil
        import urllib.request
        return [json, subprocess, sqlite3, shutil, urllib]
    
    def lazy_imports():
        """Lazy import approach."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from super_agents.performance.lazy_loader import lazy_import
        
        json = lazy_import('json')
        subprocess = lazy_import('subprocess')
        sqlite3 = lazy_import('sqlite3')
        shutil = lazy_import('shutil')
        urllib = lazy_import('urllib')
        return [json, subprocess, sqlite3, shutil, urllib]
    
    return benchmark.compare_operations(
        "Normal Imports", "Lazy Imports",
        normal_imports, lazy_imports
    )

def benchmark_file_operations():
    """Benchmark file operation performance."""
    benchmark = PerformanceBenchmark(iterations=20)
    
    # Create test file
    test_file = Path("/tmp/perf_test.json")
    test_data = {"test": "data", "numbers": list(range(100))}
    test_file.write_text(json.dumps(test_data))
    
    def normal_file_read():
        """Normal file reading."""
        return json.loads(test_file.read_text())
    
    def cached_file_read():
        """Cached file reading."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from super_agents.performance.caching import cached_json_load
        return cached_json_load(test_file)
    
    try:
        result = benchmark.compare_operations(
            "Normal File Read", "Cached File Read",
            normal_file_read, cached_file_read
        )
        return result
    finally:
        test_file.unlink(missing_ok=True)

def benchmark_subprocess_calls():
    """Benchmark subprocess call performance."""
    benchmark = PerformanceBenchmark(iterations=15)
    
    def normal_subprocess():
        """Normal subprocess call."""
        result = subprocess.run(['echo', 'test'], capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    
    def cached_subprocess():
        """Cached subprocess call."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from super_agents.performance.caching import cached_subprocess_run
        return cached_subprocess_run(['echo', 'test'])
    
    return benchmark.compare_operations(
        "Normal Subprocess", "Cached Subprocess",
        normal_subprocess, cached_subprocess
    )

def benchmark_project_indexing():
    """Benchmark project indexing performance."""
    benchmark = PerformanceBenchmark(iterations=3)  # Fewer iterations for heavy operations
    
    def manual_file_search():
        """Manual recursive file search."""
        files = []
        for root, dirs, filenames in os.walk('.'):
            for filename in filenames:
                if filename.endswith('.py'):
                    files.append(os.path.join(root, filename))
        return len(files)
    
    def indexed_file_search():
        """Indexed file search."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from super_agents.performance.indexing import get_project_indexer
        
        indexer = get_project_indexer()
        indexer.index_project(Path('.'), max_workers=2)
        results = indexer.search_files('.py', file_type='python')
        return len(results)
    
    return benchmark.compare_operations(
        "Manual File Search", "Indexed File Search",
        manual_file_search, indexed_file_search
    )

def benchmark_cli_startup():
    """Benchmark CLI startup performance."""
    benchmark = PerformanceBenchmark(iterations=5)
    
    def startup_without_optimizations():
        """CLI startup without performance optimizations."""
        # Simulate the CLI without lazy imports
        start_time = time.perf_counter()
        
        # Import all CLI dependencies normally
        import click
        import rich.console
        import rich.panel
        import subprocess
        import shutil
        import json
        
        end_time = time.perf_counter()
        return end_time - start_time
    
    def startup_with_optimizations():
        """CLI startup with performance optimizations."""
        start_time = time.perf_counter()
        
        # Use lazy imports
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from super_agents.performance.lazy_loader import lazy_import
        from super_agents.performance import initialize_performance_optimizations
        
        initialize_performance_optimizations()
        
        # Simulate CLI imports
        click = lazy_import('click', critical=True)
        rich_console = lazy_import('rich.console')
        rich_panel = lazy_import('rich.panel')
        subprocess = lazy_import('subprocess')
        shutil = lazy_import('shutil')
        json = lazy_import('json')
        
        end_time = time.perf_counter()
        return end_time - start_time
    
    return benchmark.compare_operations(
        "Startup Without Optimization", "Startup With Optimization",
        startup_without_optimizations, startup_with_optimizations
    )

def run_full_benchmark() -> Dict[str, Any]:
    """Run comprehensive performance benchmark."""
    console.print("[bold cyan]Running Performance Validation[/bold cyan]")
    console.print("Testing performance improvements against roadmap targets...\n")
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task1 = progress.add_task("CLI Startup Performance...", total=1)
        results['cli_startup'] = benchmark_cli_startup()
        progress.update(task1, advance=1)
        
        task2 = progress.add_task("Module Import Performance...", total=1)
        results['module_imports'] = benchmark_module_imports()
        progress.update(task2, advance=1)
        
        task3 = progress.add_task("File Operation Performance...", total=1)
        results['file_operations'] = benchmark_file_operations()
        progress.update(task3, advance=1)
        
        task4 = progress.add_task("Subprocess Performance...", total=1)
        results['subprocess_calls'] = benchmark_subprocess_calls()
        progress.update(task4, advance=1)
        
        task5 = progress.add_task("Project Indexing Performance...", total=1)
        results['project_indexing'] = benchmark_project_indexing()
        progress.update(task5, advance=1)
    
    return results

def analyze_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze benchmark results against targets."""
    analysis = {
        'meets_startup_target': False,  # 20% improvement
        'meets_runtime_target': False,  # 10% improvement
        'startup_improvements': [],
        'runtime_improvements': [],
        'summary': {}
    }
    
    startup_tests = ['cli_startup', 'module_imports']
    runtime_tests = ['file_operations', 'subprocess_calls', 'project_indexing']
    
    # Analyze startup performance
    startup_improvements = []
    for test_name in startup_tests:
        if test_name in results:
            improvement = results[test_name]['improvement_percent']
            startup_improvements.append(improvement)
            analysis['startup_improvements'].append({
                'test': test_name,
                'improvement': improvement
            })
    
    # Analyze runtime performance
    runtime_improvements = []
    for test_name in runtime_tests:
        if test_name in results:
            improvement = results[test_name]['improvement_percent']
            runtime_improvements.append(improvement)
            analysis['runtime_improvements'].append({
                'test': test_name,
                'improvement': improvement
            })
    
    # Calculate averages
    avg_startup_improvement = statistics.mean(startup_improvements) if startup_improvements else 0
    avg_runtime_improvement = statistics.mean(runtime_improvements) if runtime_improvements else 0
    
    # Check targets
    analysis['meets_startup_target'] = avg_startup_improvement >= 20.0
    analysis['meets_runtime_target'] = avg_runtime_improvement >= 10.0
    
    analysis['summary'] = {
        'average_startup_improvement': avg_startup_improvement,
        'average_runtime_improvement': avg_runtime_improvement,
        'startup_target': 20.0,
        'runtime_target': 10.0
    }
    
    return analysis

def create_performance_report(results: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    """Create detailed performance report."""
    console.print("\n[bold green]Performance Validation Results[/bold green]")
    console.print("=" * 60)
    
    # Summary table
    summary_table = Table(title="Performance Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Target", style="yellow")
    summary_table.add_column("Actual", style="green")
    summary_table.add_column("Status", style="bold")
    
    startup_improvement = analysis['summary']['average_startup_improvement']
    runtime_improvement = analysis['summary']['average_runtime_improvement']
    
    startup_status = "✓ PASS" if analysis['meets_startup_target'] else "✗ FAIL"
    runtime_status = "✓ PASS" if analysis['meets_runtime_target'] else "✗ FAIL"
    
    summary_table.add_row(
        "Startup Improvement",
        "20%",
        f"{startup_improvement:.1f}%",
        startup_status
    )
    summary_table.add_row(
        "Runtime Improvement", 
        "10%",
        f"{runtime_improvement:.1f}%",
        runtime_status
    )
    
    console.print(summary_table)
    
    # Detailed results table
    console.print("\n[bold cyan]Detailed Results[/bold cyan]")
    
    details_table = Table()
    details_table.add_column("Test", style="cyan")
    details_table.add_column("Baseline (ms)", justify="right")
    details_table.add_column("Optimized (ms)", justify="right")
    details_table.add_column("Improvement", justify="right", style="green")
    details_table.add_column("Ratio", justify="right")
    
    for test_name, result in results.items():
        baseline_ms = result['baseline']['mean'] * 1000
        optimized_ms = result['optimized']['mean'] * 1000
        improvement = result['improvement_percent']
        ratio = result['improvement_ratio']
        
        details_table.add_row(
            test_name.replace('_', ' ').title(),
            f"{baseline_ms:.2f}",
            f"{optimized_ms:.2f}",
            f"{improvement:+.1f}%",
            f"{ratio:.2f}x"
        )
    
    console.print(details_table)
    
    # Recommendations
    console.print("\n[bold yellow]Recommendations[/bold yellow]")
    
    if not analysis['meets_startup_target']:
        console.print("⚠️  Startup performance target not met. Consider:")
        console.print("   • More aggressive lazy loading")
        console.print("   • Precompiled modules")
        console.print("   • Reduced import dependencies")
    
    if not analysis['meets_runtime_target']:
        console.print("⚠️  Runtime performance target not met. Consider:")
        console.print("   • Larger cache sizes")
        console.print("   • More aggressive caching policies")
        console.print("   • Background preloading")
    
    if analysis['meets_startup_target'] and analysis['meets_runtime_target']:
        console.print("🎉 All performance targets met!")
        console.print("   Performance optimizations are working effectively.")

def save_results(results: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    """Save benchmark results to file."""
    output_file = Path(".claude/performance_validation.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        'timestamp': time.time(),
        'results': results,
        'analysis': analysis,
        'system_info': {
            'python_version': sys.version,
            'platform': sys.platform
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    console.print(f"\n[dim]Results saved to: {output_file}[/dim]")

def main():
    """Main performance validation process."""
    console.print("[bold]CLI Performance Validation[/bold]")
    console.print("Validating roadmap performance targets...")
    console.print("- 20% startup time improvement")
    console.print("- 10% runtime performance improvement\n")
    
    try:
        # Run benchmarks
        results = run_full_benchmark()
        
        # Analyze results
        analysis = analyze_results(results)
        
        # Create report
        create_performance_report(results, analysis)
        
        # Save results
        save_results(results, analysis)
        
        # Exit code based on results
        if analysis['meets_startup_target'] and analysis['meets_runtime_target']:
            console.print("\n[bold green]✓ Performance validation PASSED[/bold green]")
            return 0
        else:
            console.print("\n[bold red]✗ Performance validation FAILED[/bold red]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Performance validation cancelled[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error during validation: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1

if __name__ == "__main__":
    sys.exit(main())