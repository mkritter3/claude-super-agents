#!/usr/bin/env python3
"""
Week 5: Final Stress Testing Suite
Comprehensive load testing and system limits validation
"""

import os
import sys
import time
import threading
import multiprocessing
import subprocess
import tempfile
import shutil
import json
import psutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class StressTestResult:
    """Result of a stress test"""
    test_name: str
    success: bool
    duration: float
    peak_memory_mb: float
    peak_cpu_percent: float
    operations_completed: int
    operations_per_second: float
    error_count: int
    errors: List[str]


class SystemMonitor:
    """Monitor system resources during stress tests"""
    
    def __init__(self):
        self.monitoring = False
        self.peak_memory = 0
        self.peak_cpu = 0
        self.measurements = []
        
    def start_monitoring(self):
        """Start system resource monitoring"""
        self.monitoring = True
        self.peak_memory = 0
        self.peak_cpu = 0
        self.measurements = []
        
        def monitor_loop():
            process = psutil.Process()
            while self.monitoring:
                try:
                    # Get memory usage in MB
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()
                    
                    self.peak_memory = max(self.peak_memory, memory_mb)
                    self.peak_cpu = max(self.peak_cpu, cpu_percent)
                    
                    self.measurements.append({
                        'timestamp': time.time(),
                        'memory_mb': memory_mb,
                        'cpu_percent': cpu_percent
                    })
                    
                    time.sleep(0.1)  # 100ms sampling
                except psutil.NoSuchProcess:
                    break
        
        self.monitor_thread = threading.Thread(target=monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system resource monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join()


class StressTestSuite:
    """Comprehensive stress testing suite"""
    
    def __init__(self):
        self.results = []
        self.temp_dirs = []
        
    def cleanup(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def create_test_project(self) -> Path:
        """Create a temporary test project"""
        temp_dir = Path(tempfile.mkdtemp(prefix="stress_test_"))
        self.temp_dirs.append(temp_dir)
        
        # Initialize a test project
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            
            # Run super-agents init
            result = subprocess.run(
                [sys.executable, "-m", "super_agents", "init"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to initialize test project: {result.stderr}")
                
        finally:
            os.chdir(original_cwd)
        
        return temp_dir
    
    def stress_test_cli_initialization(self, num_projects: int = 50) -> StressTestResult:
        """Test CLI initialization under load"""
        print(f"🧪 Stress testing CLI initialization ({num_projects} projects)...")
        
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = time.time()
        errors = []
        completed = 0
        
        def init_project(project_id):
            try:
                temp_dir = Path(tempfile.mkdtemp(prefix=f"stress_init_{project_id}_"))
                self.temp_dirs.append(temp_dir)
                
                original_cwd = Path.cwd()
                try:
                    os.chdir(temp_dir)
                    
                    result = subprocess.run(
                        [sys.executable, "-m", "super_agents", "init"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        return True
                    else:
                        errors.append(f"Project {project_id}: {result.stderr}")
                        return False
                        
                finally:
                    os.chdir(original_cwd)
                    
            except Exception as e:
                errors.append(f"Project {project_id}: {str(e)}")
                return False
        
        # Run initializations in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(init_project, i) for i in range(num_projects)]
            
            for future in futures:
                if future.result():
                    completed += 1
        
        end_time = time.time()
        monitor.stop_monitoring()
        
        duration = end_time - start_time
        ops_per_second = completed / duration if duration > 0 else 0
        
        return StressTestResult(
            test_name="CLI Initialization",
            success=len(errors) == 0,
            duration=duration,
            peak_memory_mb=monitor.peak_memory,
            peak_cpu_percent=monitor.peak_cpu,
            operations_completed=completed,
            operations_per_second=ops_per_second,
            error_count=len(errors),
            errors=errors[:10]  # Keep first 10 errors
        )
    
    def stress_test_knowledge_manager(self, num_instances: int = 20) -> StressTestResult:
        """Test Knowledge Manager under concurrent load"""
        print(f"🧪 Stress testing Knowledge Manager ({num_instances} instances)...")
        
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = time.time()
        errors = []
        completed = 0
        
        def start_km_instance(instance_id):
            try:
                temp_dir = self.create_test_project()
                
                original_cwd = Path.cwd()
                try:
                    os.chdir(temp_dir)
                    
                    # Start Knowledge Manager
                    result = subprocess.run(
                        [sys.executable, "-m", "super_agents", "--status"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        return True
                    else:
                        errors.append(f"Instance {instance_id}: {result.stderr}")
                        return False
                        
                finally:
                    os.chdir(original_cwd)
                    
            except Exception as e:
                errors.append(f"Instance {instance_id}: {str(e)}")
                return False
        
        # Run KM instances in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(start_km_instance, i) for i in range(num_instances)]
            
            for future in futures:
                if future.result():
                    completed += 1
        
        end_time = time.time()
        monitor.stop_monitoring()
        
        duration = end_time - start_time
        ops_per_second = completed / duration if duration > 0 else 0
        
        return StressTestResult(
            test_name="Knowledge Manager Load",
            success=len(errors) == 0,
            duration=duration,
            peak_memory_mb=monitor.peak_memory,
            peak_cpu_percent=monitor.peak_cpu,
            operations_completed=completed,
            operations_per_second=ops_per_second,
            error_count=len(errors),
            errors=errors[:10]
        )
    
    def stress_test_performance_optimizations(self, num_operations: int = 1000) -> StressTestResult:
        """Test performance optimizations under heavy load"""
        print(f"🧪 Stress testing performance optimizations ({num_operations} operations)...")
        
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = time.time()
        errors = []
        completed = 0
        
        # Create a test project
        test_project = self.create_test_project()
        
        def performance_operation(op_id):
            try:
                original_cwd = Path.cwd()
                try:
                    os.chdir(test_project)
                    
                    # Add system path for template imports
                    sys.path.insert(0, str(Path('.claude/system')))
                    
                    # Test lazy loading
                    from performance.lazy_loader import lazy_import
                    test_module = lazy_import(f'test_module_{op_id % 100}')
                    
                    # Test caching
                    from performance.caching import cached
                    
                    @cached(ttl=60)
                    def cached_operation(value):
                        return f"cached_result_{value}"
                    
                    result = cached_operation(op_id % 50)  # Reuse cache keys
                    
                    # Test indexing
                    from performance.indexing import ProjectIndexer
                    indexer = ProjectIndexer()
                    
                    # Create a test file to index
                    test_file = Path(f"test_{op_id}.py")
                    test_file.write_text(f"# Test file {op_id}")
                    
                    indexer.index_file(test_file)
                    
                    return True
                    
                finally:
                    os.chdir(original_cwd)
                    
            except Exception as e:
                errors.append(f"Operation {op_id}: {str(e)}")
                return False
        
        # Run operations in parallel
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(performance_operation, i) for i in range(num_operations)]
            
            for future in futures:
                if future.result():
                    completed += 1
        
        end_time = time.time()
        monitor.stop_monitoring()
        
        duration = end_time - start_time
        ops_per_second = completed / duration if duration > 0 else 0
        
        return StressTestResult(
            test_name="Performance Optimizations",
            success=len(errors) == 0,
            duration=duration,
            peak_memory_mb=monitor.peak_memory,
            peak_cpu_percent=monitor.peak_cpu,
            operations_completed=completed,
            operations_per_second=ops_per_second,
            error_count=len(errors),
            errors=errors[:10]
        )
    
    def stress_test_template_system(self, num_templates: int = 100) -> StressTestResult:
        """Test template system under load"""
        print(f"🧪 Stress testing template system ({num_templates} template operations)...")
        
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        start_time = time.time()
        errors = []
        completed = 0
        
        def template_operation(template_id):
            try:
                # Create project
                temp_dir = Path(tempfile.mkdtemp(prefix=f"template_test_{template_id}_"))
                self.temp_dirs.append(temp_dir)
                
                original_cwd = Path.cwd()
                try:
                    os.chdir(temp_dir)
                    
                    # Initialize project
                    result = subprocess.run(
                        [sys.executable, "-m", "super_agents", "init"],
                        capture_output=True,
                        text=True,
                        timeout=20
                    )
                    
                    if result.returncode != 0:
                        errors.append(f"Template {template_id}: Init failed")
                        return False
                    
                    # Test template delegation
                    result = subprocess.run(
                        [sys.executable, "-m", "super_agents", "--status"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        return True
                    else:
                        errors.append(f"Template {template_id}: Status failed")
                        return False
                        
                finally:
                    os.chdir(original_cwd)
                    
            except Exception as e:
                errors.append(f"Template {template_id}: {str(e)}")
                return False
        
        # Run template operations in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(template_operation, i) for i in range(num_templates)]
            
            for future in futures:
                if future.result():
                    completed += 1
        
        end_time = time.time()
        monitor.stop_monitoring()
        
        duration = end_time - start_time
        ops_per_second = completed / duration if duration > 0 else 0
        
        return StressTestResult(
            test_name="Template System",
            success=len(errors) == 0,
            duration=duration,
            peak_memory_mb=monitor.peak_memory,
            peak_cpu_percent=monitor.peak_cpu,
            operations_completed=completed,
            operations_per_second=ops_per_second,
            error_count=len(errors),
            errors=errors[:10]
        )
    
    def run_all_stress_tests(self) -> Dict[str, Any]:
        """Run all stress tests and generate comprehensive report"""
        print("🚀 Starting Comprehensive Stress Testing Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all stress tests
        tests = [
            lambda: self.stress_test_cli_initialization(50),
            lambda: self.stress_test_knowledge_manager(20),
            lambda: self.stress_test_performance_optimizations(1000),
            lambda: self.stress_test_template_system(100)
        ]
        
        for test in tests:
            try:
                result = test()
                self.results.append(result)
                
                # Print immediate results
                status = "✅ PASSED" if result.success else "❌ FAILED"
                print(f"{status} {result.test_name}")
                print(f"  Duration: {result.duration:.2f}s")
                print(f"  Operations/sec: {result.operations_per_second:.1f}")
                print(f"  Peak Memory: {result.peak_memory_mb:.1f} MB")
                print(f"  Peak CPU: {result.peak_cpu_percent:.1f}%")
                
                if result.error_count > 0:
                    print(f"  Errors: {result.error_count}")
                    for error in result.errors[:3]:
                        print(f"    • {error}")
                
                print()
                
            except Exception as e:
                print(f"❌ CRASHED {test.__name__}: {e}")
                self.results.append(StressTestResult(
                    test_name=f"CRASHED_{test.__name__}",
                    success=False,
                    duration=0,
                    peak_memory_mb=0,
                    peak_cpu_percent=0,
                    operations_completed=0,
                    operations_per_second=0,
                    error_count=1,
                    errors=[str(e)]
                ))
        
        total_time = time.time() - start_time
        
        # Generate comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": total_time,
            "total_tests": len(self.results),
            "passed_tests": sum(1 for r in self.results if r.success),
            "failed_tests": sum(1 for r in self.results if not r.success),
            "overall_success": all(r.success for r in self.results),
            "system_limits": {
                "max_memory_mb": max(r.peak_memory_mb for r in self.results),
                "max_cpu_percent": max(r.peak_cpu_percent for r in self.results),
                "total_operations": sum(r.operations_completed for r in self.results),
                "avg_ops_per_second": sum(r.operations_per_second for r in self.results) / len(self.results)
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "peak_memory_mb": r.peak_memory_mb,
                    "peak_cpu_percent": r.peak_cpu_percent,
                    "operations_completed": r.operations_completed,
                    "operations_per_second": r.operations_per_second,
                    "error_count": r.error_count,
                    "errors": r.errors
                }
                for r in self.results
            ]
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save stress test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"stress_test_report_{timestamp}.json"
        
        report_dir = Path("docs/stress_tests")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / filename
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Stress test report saved: {report_file}")
        return report_file


def main():
    """Main stress testing function"""
    suite = StressTestSuite()
    
    try:
        # Run all stress tests
        report = suite.run_all_stress_tests()
        
        # Save detailed report
        report_file = suite.save_report(report)
        
        # Print summary
        print("=" * 60)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed_tests']}")
        print(f"Failed: {report['failed_tests']}")
        print(f"Overall Success: {'✅ YES' if report['overall_success'] else '❌ NO'}")
        print(f"Total Duration: {report['total_duration']:.2f}s")
        print(f"Max Memory Usage: {report['system_limits']['max_memory_mb']:.1f} MB")
        print(f"Max CPU Usage: {report['system_limits']['max_cpu_percent']:.1f}%")
        print(f"Total Operations: {report['system_limits']['total_operations']}")
        print(f"Avg Ops/Second: {report['system_limits']['avg_ops_per_second']:.1f}")
        
        if not report['overall_success']:
            print("\n❌ FAILED TESTS:")
            for result in report['test_results']:
                if not result['success']:
                    print(f"  • {result['test_name']}: {result['error_count']} errors")
        
        print(f"\n📋 Detailed report: {report_file}")
        
        # Return appropriate exit code
        return 0 if report['overall_success'] else 1
        
    finally:
        # Clean up
        suite.cleanup()


if __name__ == '__main__':
    exit(main())