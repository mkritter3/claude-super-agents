#!/usr/bin/env python3
"""
Tests for performance impact of observability components.
Validates that monitoring overhead is within acceptable limits.
"""
import unittest
import time
import sys
import os
import threading
import gc
import resource
from pathlib import Path
from contextlib import contextmanager

# Add system directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'system'))

from metrics_collector import MetricsCollector
from tracing_config import TracingConfig

class TestPerformanceImpact(unittest.TestCase):
    """Test performance impact of observability components."""
    
    def setUp(self):
        """Set up performance testing."""
        # Force garbage collection before tests
        gc.collect()
        
        # Create observability components
        self.metrics = MetricsCollector()
        self.tracer = TracingConfig()
    
    @contextmanager
    def measure_performance(self):
        """Context manager to measure performance metrics."""
        # Get initial resource usage
        start_time = time.time()
        start_cpu = time.process_time()
        
        try:
            start_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except:
            start_memory = 0
        
        # Yield control
        yield
        
        # Calculate final metrics
        end_time = time.time()
        end_cpu = time.process_time()
        
        try:
            end_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except:
            end_memory = start_memory
        
        # Store results
        self.wall_time = end_time - start_time
        self.cpu_time = end_cpu - start_cpu
        self.memory_delta = end_memory - start_memory
    
    def test_metrics_collection_overhead(self):
        """Test overhead of metrics collection operations."""
        iterations = 10000
        
        # Measure baseline (no metrics)
        with self.measure_performance():
            for i in range(iterations):
                # Simulate typical application operations
                x = i * 2
                y = x + 1
                z = str(y)
        
        baseline_time = self.wall_time
        baseline_cpu = self.cpu_time
        
        # Measure with metrics collection
        with self.measure_performance():
            for i in range(iterations):
                # Same operations with metrics
                x = i * 2
                self.metrics.increment_counter('test_counter', {'iteration': str(i % 10)})
                
                y = x + 1
                self.metrics.set_gauge('test_gauge', y)
                
                z = str(y)
                self.metrics.record_histogram('test_duration', 0.001)
        
        metrics_time = self.wall_time
        metrics_cpu = self.cpu_time
        
        # Calculate overhead
        time_overhead = metrics_time - baseline_time
        cpu_overhead = metrics_cpu - baseline_cpu
        
        # Time overhead per operation
        time_per_op = (time_overhead / iterations) * 1000  # milliseconds
        cpu_per_op = (cpu_overhead / iterations) * 1000   # milliseconds
        
        print(f"Metrics overhead: {time_per_op:.3f}ms wall time, {cpu_per_op:.3f}ms CPU per operation")
        
        # Validate overhead is acceptable (less than 1ms per operation)
        self.assertLess(time_per_op, 1.0, "Metrics collection overhead too high")
        self.assertLess(cpu_per_op, 1.0, "Metrics CPU overhead too high")
        
        # Get performance impact from metrics collector
        impact = self.metrics.get_performance_impact()
        if impact['avg_overhead_ms'] > 0:
            self.assertLess(impact['avg_overhead_ms'], 5.0, "Reported overhead too high")
    
    def test_tracing_overhead(self):
        """Test overhead of tracing operations."""
        iterations = 1000  # Fewer iterations as tracing can be more expensive
        
        # Measure baseline (no tracing)
        with self.measure_performance():
            for i in range(iterations):
                # Simulate typical application operations
                self._simulate_work(i)
        
        baseline_time = self.wall_time
        baseline_cpu = self.cpu_time
        
        # Measure with tracing
        with self.measure_performance():
            for i in range(iterations):
                with self.tracer.trace_operation(f'test_operation_{i % 10}', {'iteration': i}):
                    self._simulate_work(i)
        
        tracing_time = self.wall_time
        tracing_cpu = self.cpu_time
        
        # Calculate overhead
        time_overhead = tracing_time - baseline_time
        cpu_overhead = tracing_cpu - baseline_cpu
        
        # Time overhead per operation
        time_per_op = (time_overhead / iterations) * 1000  # milliseconds
        cpu_per_op = (cpu_overhead / iterations) * 1000   # milliseconds
        
        print(f"Tracing overhead: {time_per_op:.3f}ms wall time, {cpu_per_op:.3f}ms CPU per operation")
        
        # Validate overhead is acceptable (less than 5ms per operation for tracing)
        self.assertLess(time_per_op, 5.0, "Tracing overhead too high")
        self.assertLess(cpu_per_op, 5.0, "Tracing CPU overhead too high")
    
    def test_combined_observability_overhead(self):
        """Test overhead when using both metrics and tracing together."""
        iterations = 1000
        
        # Measure baseline
        with self.measure_performance():
            for i in range(iterations):
                self._simulate_work(i)
        
        baseline_time = self.wall_time
        
        # Measure with both metrics and tracing
        with self.measure_performance():
            for i in range(iterations):
                with self.tracer.trace_operation(f'combined_op_{i % 10}', {'iteration': i}) as span:
                    self.metrics.increment_counter('combined_counter', {'op': str(i % 10)})
                    
                    result = self._simulate_work(i)
                    
                    self.metrics.record_histogram('combined_duration', 0.001)
                    self.tracer.add_event(span, 'work_completed', {'result': str(result)})
        
        combined_time = self.wall_time
        
        # Calculate total overhead
        total_overhead = combined_time - baseline_time
        overhead_per_op = (total_overhead / iterations) * 1000  # milliseconds
        
        print(f"Combined observability overhead: {overhead_per_op:.3f}ms per operation")
        
        # Combined overhead should still be reasonable (less than 10ms per operation)
        self.assertLess(overhead_per_op, 10.0, "Combined observability overhead too high")
    
    def test_memory_impact(self):
        """Test memory impact of observability components."""
        initial_memory = self._get_memory_usage()
        
        # Create and use observability components
        metrics = MetricsCollector()
        tracer = TracingConfig()
        
        # Generate some metrics and traces
        for i in range(1000):
            metrics.increment_counter('memory_test', {'batch': str(i // 100)})
            metrics.set_gauge('memory_gauge', i)
            
            with tracer.trace_operation(f'memory_trace_{i}'):
                pass
        
        # Force garbage collection
        gc.collect()
        
        final_memory = self._get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Memory increase should be reasonable (less than 50MB for this test)
        self.assertLess(memory_increase, 50.0, "Memory usage increase too high")
    
    def test_concurrent_performance_impact(self):
        """Test performance impact under concurrent load."""
        iterations_per_thread = 500
        num_threads = 5
        
        def worker(worker_id, results):
            start_time = time.time()
            
            for i in range(iterations_per_thread):
                # Use both metrics and tracing
                with self.tracer.trace_operation(f'worker_{worker_id}_op_{i}') as span:
                    self.metrics.increment_counter('concurrent_counter', {
                        'worker': str(worker_id),
                        'batch': str(i // 100)
                    })
                    
                    result = self._simulate_work(i)
                    
                    self.metrics.record_histogram('concurrent_duration', result * 0.001)
                    self.tracer.set_attribute(span, 'result', str(result))
            
            end_time = time.time()
            results[worker_id] = end_time - start_time
        
        # Run concurrent workers
        threads = []
        results = {}
        
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i, results))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        worker_times = list(results.values())
        avg_worker_time = sum(worker_times) / len(worker_times)
        max_worker_time = max(worker_times)
        
        total_operations = iterations_per_thread * num_threads
        ops_per_second = total_operations / total_time
        
        print(f"Concurrent performance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average worker time: {avg_worker_time:.2f}s")
        print(f"  Max worker time: {max_worker_time:.2f}s")
        print(f"  Operations per second: {ops_per_second:.1f}")
        
        # Should maintain reasonable throughput
        self.assertGreater(ops_per_second, 100, "Concurrent throughput too low")
        
        # No worker should take excessively long
        self.assertLess(max_worker_time, total_time * 2, "Worker time variance too high")
    
    def test_observability_disabling_impact(self):
        """Test performance when observability is disabled."""
        iterations = 5000
        
        # Test with observability enabled
        self.metrics.enable_metrics()
        
        with self.measure_performance():
            for i in range(iterations):
                self.metrics.increment_counter('disable_test')
                self.metrics.set_gauge('disable_gauge', i)
        
        enabled_time = self.wall_time
        
        # Test with observability disabled
        self.metrics.disable_metrics()
        
        with self.measure_performance():
            for i in range(iterations):
                self.metrics.increment_counter('disable_test')
                self.metrics.set_gauge('disable_gauge', i)
        
        disabled_time = self.wall_time
        
        # Re-enable for cleanup
        self.metrics.enable_metrics()
        
        print(f"Enabled time: {enabled_time:.3f}s, Disabled time: {disabled_time:.3f}s")
        
        # Disabled should be significantly faster
        self.assertLess(disabled_time, enabled_time * 0.5, "Disabling observability doesn't improve performance enough")
    
    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        # Create a large number of unique metrics
        num_unique_metrics = 1000
        iterations_per_metric = 10
        
        with self.measure_performance():
            for metric_id in range(num_unique_metrics):
                for iteration in range(iterations_per_metric):
                    self.metrics.increment_counter(f'large_dataset_metric_{metric_id}', {
                        'iteration': str(iteration),
                        'category': str(metric_id % 10)
                    })
        
        total_operations = num_unique_metrics * iterations_per_metric
        ops_per_second = total_operations / self.wall_time
        
        print(f"Large dataset performance: {ops_per_second:.1f} ops/sec")
        
        # Should maintain reasonable performance even with many unique metrics
        self.assertGreater(ops_per_second, 1000, "Large dataset performance too low")
    
    def _simulate_work(self, input_value):
        """Simulate typical application work."""
        # Simple computation to simulate real work
        result = 0
        for i in range(input_value % 50):
            result += i * 2
        return result
    
    def _get_memory_usage(self):
        """Get current memory usage in MB."""
        try:
            # Get RSS (Resident Set Size) in MB
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On macOS, ru_maxrss is in bytes; on Linux, it's in KB
            if sys.platform == 'darwin':
                return rss / (1024 * 1024)  # Convert bytes to MB
            else:
                return rss / 1024  # Convert KB to MB
        except:
            return 0.0

class TestObservabilityScaling(unittest.TestCase):
    """Test how observability components scale with load."""
    
    def test_metrics_scaling(self):
        """Test how metrics collection scales with increasing load."""
        metrics = MetricsCollector()
        
        # Test different load levels
        load_levels = [100, 500, 1000, 2000]
        results = {}
        
        for load in load_levels:
            start_time = time.time()
            
            for i in range(load):
                metrics.increment_counter('scaling_test', {'load': str(load)})
                metrics.set_gauge('scaling_gauge', i)
                metrics.record_histogram('scaling_hist', i * 0.001)
            
            duration = time.time() - start_time
            ops_per_second = load / duration
            results[load] = ops_per_second
            
            print(f"Load {load}: {ops_per_second:.1f} ops/sec")
        
        # Performance should scale reasonably (not degrade drastically)
        # Allow for some performance degradation but not more than 50%
        baseline_ops = results[load_levels[0]]
        max_load_ops = results[load_levels[-1]]
        
        degradation_ratio = baseline_ops / max_load_ops
        self.assertLess(degradation_ratio, 2.0, "Performance degrades too much with increased load")
    
    def test_error_handling_performance(self):
        """Test performance impact of error handling in observability."""
        metrics = MetricsCollector()
        iterations = 1000
        
        # Test normal operations
        start_time = time.time()
        for i in range(iterations):
            metrics.increment_counter('error_test_normal', {'iteration': str(i)})
        normal_time = time.time() - start_time
        
        # Test operations that might cause errors (invalid values, etc.)
        start_time = time.time()
        for i in range(iterations):
            try:
                # Test with potentially problematic values
                metrics.increment_counter('', {'': ''})  # Empty strings
                metrics.set_gauge('error_test', float('inf'))  # Infinity
                metrics.record_histogram('error_test', -1)  # Negative value
            except:
                pass  # Ignore errors, just measure performance impact
        error_time = time.time() - start_time
        
        print(f"Normal operations: {normal_time:.3f}s, Error handling: {error_time:.3f}s")
        
        # Error handling shouldn't be more than 10x slower
        self.assertLess(error_time, normal_time * 10, "Error handling too slow")

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)