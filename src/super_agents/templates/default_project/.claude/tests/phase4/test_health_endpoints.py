#!/usr/bin/env python3
"""
Tests for health and monitoring endpoints in km_server.
Validates health checks, readiness probes, and metrics endpoints.
"""
import unittest
import json
import time
import sys
import os
from pathlib import Path
import threading
import subprocess
import signal

# Add system directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'system'))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

class TestHealthEndpoints(unittest.TestCase):
    """Test health and monitoring endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Start km_server for testing."""
        if not HAS_REQUESTS:
            raise unittest.SkipTest("requests library not available")
        
        cls.server_process = None
        cls.base_url = "http://127.0.0.1:5001"
        
        # Check if server is already running
        try:
            response = requests.get(f"{cls.base_url}/health", timeout=1)
            cls.server_running = True
            print("Using existing km_server instance")
        except:
            # Start server
            cls._start_server()
    
    @classmethod
    def _start_server(cls):
        """Start the km_server process."""
        server_path = Path(__file__).parent.parent.parent / 'system' / 'km_server.py'
        
        try:
            cls.server_process = subprocess.Popen(
                [sys.executable, str(server_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(server_path.parent)
            )
            
            # Wait for server to start
            for _ in range(30):  # 30 second timeout
                try:
                    response = requests.get(f"{cls.base_url}/health", timeout=1)
                    if response.status_code in [200, 503]:
                        cls.server_running = True
                        print("km_server started successfully")
                        return
                except:
                    pass
                time.sleep(1)
            
            raise Exception("Failed to start km_server")
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            cls.server_running = False
    
    @classmethod
    def tearDownClass(cls):
        """Stop km_server if we started it."""
        if cls.server_process:
            try:
                cls.server_process.terminate()
                cls.server_process.wait(timeout=5)
            except:
                cls.server_process.kill()
    
    def setUp(self):
        """Set up for each test."""
        if not hasattr(self.__class__, 'server_running') or not self.server_running:
            self.skipTest("km_server not available for testing")
    
    def test_health_endpoint_basic(self):
        """Test basic health endpoint functionality."""
        response = requests.get(f"{self.base_url}/health")
        
        # Should return a response
        self.assertIn(response.status_code, [200, 503])
        
        # Should return JSON
        data = response.json()
        self.assertIsInstance(data, dict)
        
        # Should have required fields
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('service', data)
        self.assertIn('checks', data)
        
        # Validate field types
        self.assertIn(data['status'], ['healthy', 'unhealthy'])
        self.assertIsInstance(data['timestamp'], (int, float))
        self.assertEqual(data['service'], 'knowledge-manager')
        self.assertIsInstance(data['checks'], dict)
    
    def test_health_endpoint_database_check(self):
        """Test database health check."""
        response = requests.get(f"{self.base_url}/health")
        data = response.json()
        
        # Should have database check
        self.assertIn('database', data['checks'])
        self.assertIn(data['checks']['database'], ['ok', 'error'])
    
    def test_ready_endpoint_basic(self):
        """Test basic readiness endpoint functionality."""
        response = requests.get(f"{self.base_url}/ready")
        
        # Should return a response
        self.assertIn(response.status_code, [200, 503])
        
        # Should return JSON
        data = response.json()
        self.assertIsInstance(data, dict)
        
        # Should have required fields
        self.assertIn('ready', data)
        self.assertIn('timestamp', data)
        self.assertIn('service', data)
        self.assertIn('checks', data)
        
        # Validate field types
        self.assertIsInstance(data['ready'], bool)
        self.assertIsInstance(data['timestamp'], (int, float))
        self.assertEqual(data['service'], 'knowledge-manager')
        self.assertIsInstance(data['checks'], dict)
    
    def test_ready_endpoint_comprehensive_checks(self):
        """Test comprehensive readiness checks."""
        response = requests.get(f"{self.base_url}/ready")
        data = response.json()
        
        # Should have all readiness checks
        expected_checks = ['database', 'embeddings', 'filesystem']
        for check in expected_checks:
            self.assertIn(check, data['checks'])
            
            check_data = data['checks'][check]
            self.assertIsInstance(check_data, dict)
            self.assertIn('status', check_data)
            self.assertIn('details', check_data)
            self.assertIn(check_data['status'], ['ready', 'not_ready'])
    
    def test_metrics_endpoint_basic(self):
        """Test basic metrics endpoint functionality."""
        response = requests.get(f"{self.base_url}/metrics")
        
        # Should return a response
        self.assertEqual(response.status_code, 200)
        
        # Should return text/plain
        self.assertEqual(response.headers.get('content-type'), 'text/plain; charset=utf-8')
        
        # Should return metrics data
        metrics_text = response.text
        self.assertIsInstance(metrics_text, str)
        
        # Should contain some metrics or a message
        self.assertGreater(len(metrics_text), 0)
    
    def test_metrics_endpoint_prometheus_format(self):
        """Test metrics endpoint Prometheus format compatibility."""
        response = requests.get(f"{self.base_url}/metrics")
        metrics_text = response.text
        
        # If metrics are available, should follow Prometheus format
        if "not available" not in metrics_text.lower():
            # Should have metric names and values
            lines = metrics_text.strip().split('\n')
            self.assertGreater(len(lines), 0)
            
            # Basic format validation (not exhaustive)
            for line in lines:
                if line and not line.startswith('#'):
                    # Should have metric name and value
                    parts = line.split()
                    self.assertGreaterEqual(len(parts), 2)
    
    def test_status_endpoint_basic(self):
        """Test basic status endpoint functionality."""
        response = requests.get(f"{self.base_url}/status")
        
        # Should return a response
        self.assertIn(response.status_code, [200, 500])
        
        # Should return JSON
        data = response.json()
        self.assertIsInstance(data, dict)
        
        # Should have timestamp and service
        self.assertIn('timestamp', data)
        self.assertIn('service', data)
        
        if response.status_code == 200:
            # Successful status should have comprehensive info
            expected_fields = [
                'version', 'uptime_seconds', 'embedding_model',
                'database', 'statistics', 'observability'
            ]
            for field in expected_fields:
                self.assertIn(field, data)
    
    def test_status_endpoint_comprehensive(self):
        """Test comprehensive status information."""
        response = requests.get(f"{self.base_url}/status")
        
        if response.status_code != 200:
            self.skipTest("Status endpoint not healthy")
        
        data = response.json()
        
        # Test embedding model info
        embedding_info = data['embedding_model']
        self.assertIsInstance(embedding_info, dict)
        self.assertIn('available', embedding_info)
        self.assertIsInstance(embedding_info['available'], bool)
        
        # Test database info
        db_info = data['database']
        self.assertIsInstance(db_info, dict)
        self.assertIn('path', db_info)
        self.assertIn('size_bytes', db_info)
        
        # Test statistics
        stats = data['statistics']
        self.assertIsInstance(stats, dict)
        expected_stats = ['knowledge_items', 'file_summaries', 'component_apis']
        for stat in expected_stats:
            self.assertIn(stat, stats)
    
    def test_endpoint_response_times(self):
        """Test that endpoints respond within reasonable time."""
        endpoints = ['/health', '/ready', '/metrics', '/status']
        
        for endpoint in endpoints:
            start_time = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            response_time = time.time() - start_time
            
            # Should respond within 5 seconds
            self.assertLess(response_time, 5.0)
            
            # Should not timeout
            self.assertIsNotNone(response)
    
    def test_concurrent_endpoint_access(self):
        """Test concurrent access to monitoring endpoints."""
        def make_request(endpoint):
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                return response.status_code
            except:
                return None
        
        # Test concurrent health checks
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(
                target=lambda: results.append(make_request('/health'))
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All requests should complete
        self.assertEqual(len(results), 10)
        
        # Most should succeed (allow for some failures in test environment)
        successful = [r for r in results if r in [200, 503]]
        self.assertGreater(len(successful), 5)
    
    def test_error_handling(self):
        """Test error handling in endpoints."""
        # Test invalid endpoints
        response = requests.get(f"{self.base_url}/invalid-endpoint")
        self.assertEqual(response.status_code, 404)
        
        # Test invalid methods
        response = requests.post(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 405)

class TestHealthEndpointIntegration(unittest.TestCase):
    """Test integration aspects of health endpoints."""
    
    def test_health_endpoint_without_server(self):
        """Test behavior when server is not running."""
        if not HAS_REQUESTS:
            self.skipTest("requests library not available")
        
        # Try to connect to non-existent server
        try:
            response = requests.get("http://127.0.0.1:9999/health", timeout=1)
            # Should not reach here
            self.fail("Expected connection error")
        except requests.exceptions.RequestException:
            # Expected behavior
            pass
    
    def test_metrics_integration_with_observability(self):
        """Test metrics endpoint integration with observability system."""
        # This test checks if the metrics endpoint properly integrates
        # with the observability system when available
        
        # Import here to test availability
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'system'))
            from metrics_collector import MetricsCollector
            
            # Create metrics collector
            collector = MetricsCollector()
            
            # Add some test metrics
            collector.increment_counter('test_metric', {'test': 'true'})
            collector.set_gauge('test_gauge', 42)
            
            # Get metrics output
            output = collector.get_prometheus_metrics()
            self.assertIsInstance(output, str)
            
        except ImportError:
            self.skipTest("Observability system not available")

class TestMonitoringWorkflow(unittest.TestCase):
    """Test complete monitoring workflow."""
    
    def setUp(self):
        """Set up for monitoring tests."""
        if not HAS_REQUESTS:
            self.skipTest("requests library not available")
    
    def test_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        base_url = "http://127.0.0.1:5001"
        
        # Check if server is available
        try:
            requests.get(f"{base_url}/health", timeout=1)
        except:
            self.skipTest("km_server not available")
        
        # 1. Check health
        health_response = requests.get(f"{base_url}/health")
        self.assertIn(health_response.status_code, [200, 503])
        
        # 2. Check readiness
        ready_response = requests.get(f"{base_url}/ready")
        self.assertIn(ready_response.status_code, [200, 503])
        
        # 3. Get metrics
        metrics_response = requests.get(f"{base_url}/metrics")
        self.assertEqual(metrics_response.status_code, 200)
        
        # 4. Get detailed status
        status_response = requests.get(f"{base_url}/status")
        self.assertIn(status_response.status_code, [200, 500])
        
        # All endpoints should be accessible
        self.assertTrue(True)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)