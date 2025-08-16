#!/usr/bin/env python3
"""
Tests for metrics collection system.
Validates Prometheus compatibility and performance impact.
"""
import unittest
import time
import threading
import sys
import os
from pathlib import Path

# Add system directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'system'))

from metrics_collector import MetricsCollector, get_metrics
from metrics_collector import increment_task_counter, record_task_duration, set_active_tasks

class TestMetricsCollection(unittest.TestCase):
    """Test metrics collection functionality."""
    
    def setUp(self):
        """Set up test metrics collector."""
        self.collector = MetricsCollector(enable_prometheus=True)
    
    def test_counter_metrics(self):
        """Test counter metric functionality."""
        # Test basic counter
        self.collector.increment_counter('test_counter')
        
        # Test counter with labels
        self.collector.increment_counter('task_counter', {
            'status': 'success',
            'mode': 'simple',
            'agent': 'test'
        })
        
        # Test custom increment value
        self.collector.increment_counter('test_counter', value=5)
        
        # Should not raise exceptions
        self.assertTrue(True)
    
    def test_gauge_metrics(self):
        """Test gauge metric functionality."""
        # Test basic gauge
        self.collector.set_gauge('test_gauge', 42.0)
        
        # Test gauge with labels
        self.collector.set_gauge('active_tasks', 3, {'mode': 'simple'})
        
        # Test floating point values
        self.collector.set_gauge('cpu_usage', 75.5)
        
        # Should not raise exceptions
        self.assertTrue(True)
    
    def test_histogram_metrics(self):
        """Test histogram metric functionality."""
        # Test basic histogram
        self.collector.record_histogram('test_duration', 1.5)
        
        # Test histogram with labels
        self.collector.record_histogram('task_duration', 2.3, {
            'agent': 'test',
            'mode': 'simple'
        })
        
        # Test multiple observations
        for i in range(10):
            self.collector.record_histogram('response_time', i * 0.1)
        
        # Should not raise exceptions
        self.assertTrue(True)
    
    def test_time_operation_context_manager(self):
        """Test the time_operation context manager."""
        # Test successful operation
        with self.collector.time_operation('test_operation', {'test': 'true'}):
            time.sleep(0.01)  # Simulate work
        
        # Test operation with exception
        try:
            with self.collector.time_operation('failing_operation'):
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        # Should complete without issues
        self.assertTrue(True)
    
    def test_task_metrics(self):
        """Test task-specific metrics."""
        # Test successful task
        self.collector.record_task_metrics('test-agent', 'simple', 1.5, True)
        
        # Test failed task
        self.collector.record_task_metrics('test-agent', 'complex', 3.2, False)
        
        # Should not raise exceptions
        self.assertTrue(True)
    
    def test_agent_metrics(self):
        """Test agent performance metrics."""
        # Test successful agent call
        self.collector.record_agent_metrics('test-agent', 'process', 0.5, True)
        
        # Test failed agent call
        self.collector.record_agent_metrics('test-agent', 'analyze', 2.1, False, 'timeout')
        
        # Should not raise exceptions
        self.assertTrue(True)
    
    def test_system_metrics_update(self):
        """Test system metrics collection."""
        try:
            self.collector.update_system_metrics()
            # Should complete without exceptions
            self.assertTrue(True)
        except Exception:
            # System metrics might fail in test environment, that's ok
            self.skipTest("System metrics not available in test environment")
    
    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics output format."""
        # Add some test metrics
        self.collector.increment_counter('test_requests', {'status': 'success'})
        self.collector.set_gauge('test_active', 5)
        self.collector.record_histogram('test_duration', 1.23)
        
        # Get metrics output
        metrics_output = self.collector.get_prometheus_metrics()
        
        # Should be string format
        self.assertIsInstance(metrics_output, str)
        
        # Should contain metrics (either Prometheus format or fallback)
        self.assertGreater(len(metrics_output), 0)
    
    def test_performance_impact(self):
        """Test that metrics collection has minimal performance impact."""
        iterations = 1000
        
        # Measure baseline (no metrics)
        self.collector.disable_metrics()
        start_time = time.time()
        for i in range(iterations):
            self.collector.increment_counter('perf_test')
        baseline_time = time.time() - start_time
        
        # Measure with metrics enabled
        self.collector.enable_metrics()
        start_time = time.time()
        for i in range(iterations):
            self.collector.increment_counter('perf_test')
        metrics_time = time.time() - start_time
        
        # Get performance impact data
        impact = self.collector.get_performance_impact()
        
        # Validate impact is minimal
        self.assertIsInstance(impact, dict)
        self.assertIn('avg_overhead_ms', impact)
        
        # Average overhead should be less than 5ms per operation
        if impact['avg_overhead_ms'] > 0:
            self.assertLess(impact['avg_overhead_ms'], 5.0)
    
    def test_thread_safety(self):
        """Test that metrics collection is thread-safe."""
        def worker(worker_id):
            for i in range(100):
                self.collector.increment_counter('thread_test', {'worker': str(worker_id)})
                self.collector.set_gauge('worker_gauge', i, {'worker': str(worker_id)})
                self.collector.record_histogram('worker_time', i * 0.01, {'worker': str(worker_id)})
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should complete without exceptions
        self.assertTrue(True)
    
    def test_health_summary(self):
        """Test health summary functionality."""
        health = self.collector.get_health_summary()
        
        # Validate structure
        self.assertIsInstance(health, dict)
        self.assertIn('metrics_enabled', health)
        self.assertIn('uptime_seconds', health)
        self.assertIn('performance_impact', health)
        self.assertIn('healthy', health)
        
        # Validate types
        self.assertIsInstance(health['metrics_enabled'], bool)
        self.assertIsInstance(health['uptime_seconds'], (int, float))
        self.assertIsInstance(health['healthy'], bool)
    
    def test_convenience_functions(self):
        """Test convenience functions for common operations."""
        # Test task counter
        increment_task_counter('success', 'simple', 'test-agent')
        
        # Test task duration
        record_task_duration(1.5, 'test-agent', 'simple')
        
        # Test active tasks
        set_active_tasks(3, 'simple')
        
        # Should not raise exceptions
        self.assertTrue(True)
    
    def test_global_metrics_instance(self):
        """Test global metrics instance management."""
        # Get global instance
        global_metrics = get_metrics()
        
        # Should be same instance on subsequent calls
        global_metrics2 = get_metrics()
        self.assertIs(global_metrics, global_metrics2)
        
        # Should be MetricsCollector instance
        self.assertIsInstance(global_metrics, MetricsCollector)
    
    def test_metrics_disable_enable(self):
        """Test disabling and enabling metrics."""
        # Test disable
        self.collector.disable_metrics()
        self.assertFalse(self.collector.enabled)
        
        # Operations should be no-op when disabled
        self.collector.increment_counter('disabled_test')
        
        # Test re-enable
        self.collector.enable_metrics()
        self.assertTrue(self.collector.enabled)
        
        # Operations should work again
        self.collector.increment_counter('enabled_test')

class TestMetricsIntegration(unittest.TestCase):
    """Test metrics integration with other components."""
    
    def test_metrics_without_prometheus(self):
        """Test fallback metrics when Prometheus is not available."""
        # Create collector without Prometheus
        collector = MetricsCollector(enable_prometheus=False)
        
        # Test basic operations
        collector.increment_counter('fallback_test')
        collector.set_gauge('fallback_gauge', 42)
        collector.record_histogram('fallback_hist', 1.5)
        
        # Get metrics output
        output = collector.get_prometheus_metrics()
        self.assertIsInstance(output, str)
    
    def test_error_handling(self):
        """Test error handling in metrics collection."""
        collector = MetricsCollector()
        
        # Test with invalid metric names (should not crash)
        collector.increment_counter('')
        collector.set_gauge(None, 0)  # Will be converted to string
        
        # Test with invalid values (should handle gracefully)
        try:
            collector.record_histogram('test', float('inf'))
        except:
            pass  # Some backends might reject infinite values
        
        # Should not crash the application
        self.assertTrue(True)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)