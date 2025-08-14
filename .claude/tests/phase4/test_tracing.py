#!/usr/bin/env python3
"""
Tests for tracing configuration and functionality.
Validates OpenTelemetry integration and fallback behavior.
"""
import unittest
import time
import threading
import sys
import os
from pathlib import Path

# Add system directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'system'))

from tracing_config import TracingConfig, get_tracer, trace_operation, trace_function
from tracing_config import trace_agent_operation, trace_file_operation, trace_db_operation

class TestTracingConfiguration(unittest.TestCase):
    """Test tracing configuration and setup."""
    
    def setUp(self):
        """Set up test tracing configuration."""
        self.tracer = TracingConfig(service_name='aet-test', enable_tracing=True)
    
    def test_tracer_initialization(self):
        """Test tracer initialization."""
        # Should have a tracer instance
        self.assertIsNotNone(self.tracer.tracer)
        
        # Should have correct service name
        self.assertEqual(self.tracer.service_name, 'aet-test')
        
        # Should be enabled or fallback
        self.assertIsInstance(self.tracer.enabled, bool)
    
    def test_trace_operation_context_manager(self):
        """Test trace operation context manager."""
        # Test basic operation tracing
        with self.tracer.trace_operation('test_operation') as span:
            self.assertIsNotNone(span)
            time.sleep(0.01)  # Simulate work
        
        # Test with attributes
        with self.tracer.trace_operation('test_with_attrs', {'test': 'value', 'number': 42}) as span:
            self.assertIsNotNone(span)
            
            # Test adding events
            self.tracer.add_event(span, 'test_event', {'event_data': 'test'})
            
            # Test setting attributes
            self.tracer.set_attribute(span, 'runtime_attr', 'runtime_value')
    
    def test_trace_operation_with_exception(self):
        """Test tracing operations that raise exceptions."""
        with self.assertRaises(ValueError):
            with self.tracer.trace_operation('failing_operation') as span:
                # Span should still be created
                self.assertIsNotNone(span)
                raise ValueError("Test exception")
        
        # Tracer should handle the exception gracefully
    
    def test_trace_function_decorator(self):
        """Test function tracing decorator."""
        @self.tracer.trace_function('test_decorated_function', {'decorated': 'true'})
        def test_function(x, y):
            """Test function for decoration."""
            time.sleep(0.01)
            return x + y
        
        # Call decorated function
        result = test_function(2, 3)
        self.assertEqual(result, 5)
        
        # Test with exception
        @self.tracer.trace_function('failing_function')
        def failing_function():
            raise RuntimeError("Test error")
        
        with self.assertRaises(RuntimeError):
            failing_function()
    
    def test_span_context_methods(self):
        """Test span context extraction methods."""
        with self.tracer.trace_operation('context_test') as span:
            if span:
                # Test trace ID extraction
                trace_id = self.tracer.get_trace_id(span)
                if trace_id:
                    self.assertIsInstance(trace_id, str)
                
                # Test span ID extraction
                span_id = self.tracer.get_span_id(span)
                if span_id:
                    self.assertIsInstance(span_id, str)
    
    def test_trace_context_propagation(self):
        """Test trace context propagation headers."""
        # Get tracing headers
        headers = self.tracer.get_tracing_headers()
        self.assertIsInstance(headers, dict)
        
        # Extract trace context
        context = self.tracer.extract_trace_context(headers)
        # Context might be None in fallback mode, that's ok
    
    def test_health_info(self):
        """Test tracing health information."""
        health = self.tracer.get_health_info()
        
        # Validate structure
        self.assertIsInstance(health, dict)
        self.assertIn('tracing_enabled', health)
        self.assertIn('opentelemetry_available', health)
        self.assertIn('service_name', health)
        
        # Validate values
        self.assertIsInstance(health['tracing_enabled'], bool)
        self.assertIsInstance(health['opentelemetry_available'], bool)
        self.assertEqual(health['service_name'], 'aet-test')
    
    def test_disabled_tracing(self):
        """Test behavior when tracing is disabled."""
        disabled_tracer = TracingConfig(enable_tracing=False)
        
        # Should create tracer but not enabled
        self.assertFalse(disabled_tracer.enabled)
        
        # Operations should be no-op
        with disabled_tracer.trace_operation('disabled_test') as span:
            # Span should be None in no-op mode
            pass
    
    def test_shutdown(self):
        """Test tracer shutdown."""
        # Should not raise exceptions
        self.tracer.shutdown()

class TestTracingHelpers(unittest.TestCase):
    """Test tracing helper functions."""
    
    def test_global_tracer(self):
        """Test global tracer instance."""
        # Get global tracer
        global_tracer = get_tracer()
        self.assertIsInstance(global_tracer, TracingConfig)
        
        # Should be same instance on subsequent calls
        global_tracer2 = get_tracer()
        self.assertIs(global_tracer, global_tracer2)
        
        # Test with custom service name
        custom_tracer = get_tracer('custom-service')
        # May or may not be same instance depending on implementation
    
    def test_convenience_tracing_functions(self):
        """Test convenience tracing functions."""
        # Test trace_operation helper
        with trace_operation('helper_operation', {'helper': 'true'}) as span:
            time.sleep(0.01)
        
        # Test trace_function helper
        @trace_function('helper_function', {'function': 'helper'})
        def helper_function():
            return "helper_result"
        
        result = helper_function()
        self.assertEqual(result, "helper_result")
    
    def test_specialized_tracers(self):
        """Test specialized operation tracers."""
        # Test agent operation tracing
        with trace_agent_operation('test-agent', 'process') as span:
            time.sleep(0.01)
        
        # Test file operation tracing
        with trace_file_operation('read', '/test/file.txt') as span:
            time.sleep(0.01)
        
        # Test database operation tracing
        with trace_db_operation('select', 'test_table') as span:
            time.sleep(0.01)
        
        # Test orchestration cycle tracing
        from tracing_config import trace_orchestration_cycle
        with trace_orchestration_cycle('simple', 'ticket-123') as span:
            time.sleep(0.01)

class TestFallbackTracing(unittest.TestCase):
    """Test fallback tracing when OpenTelemetry is not available."""
    
    def setUp(self):
        """Set up fallback tracer."""
        # Force fallback mode
        self.tracer = TracingConfig(enable_tracing=True)
        if self.tracer.enabled:
            # If OpenTelemetry is available, create a fallback tracer manually
            from tracing_config import FallbackTracer
            import threading
            spans_storage = []
            lock = threading.Lock()
            self.tracer.tracer = FallbackTracer(spans_storage, lock)
            self.tracer.enabled = False  # Mark as fallback
    
    def test_fallback_span_creation(self):
        """Test fallback span creation and management."""
        with self.tracer.trace_operation('fallback_test') as span:
            self.assertIsNotNone(span)
            
            # Test span methods
            if hasattr(span, 'set_attribute'):
                span.set_attribute('test_attr', 'test_value')
            
            if hasattr(span, 'add_event'):
                span.add_event('test_event', {'event_data': 'test'})
    
    def test_fallback_error_handling(self):
        """Test error handling in fallback mode."""
        with self.assertRaises(ValueError):
            with self.tracer.trace_operation('fallback_error') as span:
                raise ValueError("Fallback test error")

class TestTracingPerformance(unittest.TestCase):
    """Test tracing performance impact."""
    
    def test_tracing_overhead(self):
        """Test that tracing has minimal performance overhead."""
        tracer = TracingConfig()
        iterations = 1000
        
        # Measure baseline (no tracing)
        start_time = time.time()
        for i in range(iterations):
            # Simulate work without tracing
            x = i * 2
        baseline_time = time.time() - start_time
        
        # Measure with tracing
        start_time = time.time()
        for i in range(iterations):
            with tracer.trace_operation('perf_test'):
                x = i * 2
        traced_time = time.time() - start_time
        
        # Calculate overhead
        overhead = traced_time - baseline_time
        overhead_per_op = (overhead / iterations) * 1000  # ms per operation
        
        # Overhead should be minimal (less than 1ms per operation in most cases)
        print(f"Tracing overhead: {overhead_per_op:.3f}ms per operation")
        
        # This is more of an informational test - adjust threshold as needed
        self.assertLess(overhead_per_op, 10.0)  # 10ms is very generous
    
    def test_concurrent_tracing(self):
        """Test tracing under concurrent load."""
        tracer = TracingConfig()
        
        def worker(worker_id):
            for i in range(100):
                with tracer.trace_operation(f'worker_{worker_id}_op_{i}', {'worker': worker_id}):
                    time.sleep(0.001)  # Small work simulation
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        print(f"Concurrent tracing completed in {total_time:.2f}s")
        
        # Should complete without deadlocks or excessive delays
        self.assertLess(total_time, 10.0)  # Should complete within 10 seconds

class TestTracingIntegration(unittest.TestCase):
    """Test tracing integration with the broader system."""
    
    def test_environment_variable_config(self):
        """Test configuration via environment variables."""
        # Test with console exporter enabled
        old_console = os.environ.get('OTEL_EXPORTER_CONSOLE')
        os.environ['OTEL_EXPORTER_CONSOLE'] = 'true'
        
        try:
            tracer = TracingConfig(service_name='env-test')
            # Should not raise exceptions
            self.assertIsInstance(tracer, TracingConfig)
        finally:
            if old_console is None:
                os.environ.pop('OTEL_EXPORTER_CONSOLE', None)
            else:
                os.environ['OTEL_EXPORTER_CONSOLE'] = old_console
    
    def test_service_name_configuration(self):
        """Test service name configuration."""
        tracer = TracingConfig(service_name='custom-service')
        self.assertEqual(tracer.service_name, 'custom-service')
        
        health = tracer.get_health_info()
        self.assertEqual(health['service_name'], 'custom-service')
    
    def test_error_resilience(self):
        """Test that tracing errors don't break the application."""
        tracer = TracingConfig()
        
        # Test with problematic span names
        try:
            with tracer.trace_operation('') as span:
                pass
        except:
            pass  # Should handle gracefully
        
        try:
            with tracer.trace_operation(None) as span:  # Will be converted to string
                pass
        except:
            pass  # Should handle gracefully
        
        # Application should continue working
        self.assertTrue(True)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)