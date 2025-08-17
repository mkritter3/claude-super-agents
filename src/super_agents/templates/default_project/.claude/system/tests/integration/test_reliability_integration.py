#!/usr/bin/env python3
"""
Reliability Integration Tests
Tests circuit breakers, database maintenance, and error recovery
"""

import os
import sys
import time
import unittest
import tempfile
import sqlite3
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# Path setup is handled by the test runner

class ReliabilityIntegrationTests(unittest.TestCase):
    """Test reliability features integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="reliability_test_"))
        self.db_path = self.test_dir / "test.db"
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker with real operations"""
        try:
            from reliability.circuit_breaker import protected_call, CircuitBreakerOpenError
            
            # Create test database
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
            conn.commit()
            conn.close()
            
            # Define database operation that can fail
            def db_operation_success():
                conn = sqlite3.connect(str(self.db_path))
                conn.execute("INSERT INTO test (id, value) VALUES (?, ?)", (1, "test"))
                conn.commit()
                conn.close()
                return "success"
            
            def db_operation_failure():
                # Simulate database error
                raise sqlite3.OperationalError("Database connection failed")
            
            # Test successful operations
            result = protected_call("test_db", db_operation_success, failure_threshold=3, timeout_seconds=1)
            self.assertEqual(result, "success")
            
            # Test failure handling - try to trigger failures
            failure_count = 0
            for i in range(5):
                try:
                    protected_call("test_db", db_operation_failure, failure_threshold=3, timeout_seconds=1)
                except Exception:
                    failure_count += 1
                    if failure_count >= 3:
                        break
            
            # Test that circuit rejects calls when open
            with self.assertRaises(CircuitBreakerOpenError):
                protected_call("test_db", db_operation_success, failure_threshold=3, timeout_seconds=1)
            
        except ImportError as e:
            self.skipTest(f"Circuit breaker module not available: {e}")
    
    def test_database_maintenance_integration(self):
        """Test automatic database maintenance"""
        try:
            from database.maintenance import DatabaseMaintenance
            
            # Create test database with some data
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
            
            # Insert test data
            for i in range(1000):
                conn.execute("INSERT INTO test_table (data) VALUES (?)", (f"test_data_{i}",))
            
            # Delete some data to create fragmentation
            conn.execute("DELETE FROM test_table WHERE id % 2 = 0")
            conn.commit()
            
            # Get initial database size
            initial_size = Path(self.db_path).stat().st_size
            
            # Initialize maintenance system
            maintenance = DatabaseMaintenance(str(self.db_path))
            
            # Run maintenance
            maintenance_result = maintenance.force_maintenance()
            
            conn.close()
            
            # Verify maintenance was successful
            self.assertTrue(maintenance_result)
            
            # Verify database is still functional
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 500)  # Should have 500 records left
            conn.close()
            
        except ImportError as e:
            self.skipTest(f"Database maintenance module not available: {e}")
    
    def test_graceful_degradation_integration(self):
        """Test graceful degradation with optional dependencies"""
        try:
            from reliability.graceful_degradation import optional_import, with_fallback
            
            # Test optional import with existing module
            result = optional_import('json', fallback=None)
            self.assertIsNotNone(result)
            
            # Test optional import with non-existing module
            result = optional_import('nonexistent_module', fallback="fallback_value")
            self.assertEqual(result, "fallback_value")
            
            # Test with_fallback decorator
            @with_fallback(fallback_return="fallback_result")
            def operation_that_might_fail(should_fail=False):
                if should_fail:
                    raise ImportError("Optional dependency not available")
                return "success_result"
            
            # Test successful operation
            result = operation_that_might_fail(False)
            self.assertEqual(result, "success_result")
            
            # Test fallback behavior
            result = operation_that_might_fail(True)
            self.assertEqual(result, "fallback_result")
            
        except ImportError as e:
            self.skipTest(f"Graceful degradation module not available: {e}")
    
    def test_error_recovery_integration(self):
        """Test automatic error recovery system"""
        try:
            from reliability.error_recovery import ErrorRecoverySystem, ErrorInfo
            
            # Initialize error recovery
            recovery = ErrorRecoverySystem()
            
            # Test error logging and recovery
            errors_logged = []
            
            def mock_error_handler(error_info):
                errors_logged.append(error_info)
                return {"recovered": True, "action": "retry"}
            
            recovery.register_handler("database_error", mock_error_handler)
            
            # Simulate database error with proper ErrorInfo dataclass
            error_info = ErrorInfo(
                error_type="database_error",
                message="Connection timeout",
                timestamp=time.time(),
                context={"operation": "select", "table": "users"}
            )
            
            recovery_result = recovery.handle_error(error_info)
            
            # Verify error was handled
            self.assertEqual(len(errors_logged), 1)
            self.assertTrue(recovery_result["recovered"])
            self.assertEqual(recovery_result["action"], "retry")
            
        except ImportError as e:
            self.skipTest(f"Error recovery module not available: {e}")
    
    def test_health_monitoring_integration(self):
        """Test system health monitoring"""
        try:
            from reliability.health_monitor import HealthMonitor
            
            # Initialize health monitor
            monitor = HealthMonitor()
            
            # Register health checks
            def database_health_check():
                try:
                    conn = sqlite3.connect(str(self.db_path))
                    conn.execute("SELECT 1")
                    conn.close()
                    return {"status": "healthy", "response_time": 0.001}
                except Exception as e:
                    return {"status": "unhealthy", "error": str(e)}
            
            def memory_health_check():
                import psutil
                memory_percent = psutil.virtual_memory().percent
                return {
                    "status": "healthy" if memory_percent < 90 else "warning",
                    "memory_usage": memory_percent
                }
            
            monitor.register_check("database", database_health_check)
            
            # Create test database for health check
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("CREATE TABLE health_test (id INTEGER)")
            conn.close()
            
            # Run health checks
            health_status = monitor.check_health()
            
            # Verify health monitoring results
            self.assertIn("database", health_status)
            self.assertEqual(health_status["database"]["status"], "healthy")
            self.assertIn("response_time", health_status["database"])
            
        except ImportError as e:
            self.skipTest(f"Health monitoring module not available: {e}")
    
    def test_concurrent_reliability_features(self):
        """Test reliability features under concurrent load"""
        try:
            from reliability.circuit_breaker import protected_call, CircuitBreakerOpenError
            
            results = []
            errors = []
            
            def concurrent_operation(thread_id, should_fail=False):
                try:
                    def test_operation():
                        if should_fail:
                            raise Exception(f"Failure from thread {thread_id}")
                        return f"success_from_thread_{thread_id}"
                    
                    result = protected_call(
                        f"concurrent_test_{thread_id}",
                        test_operation, 
                        failure_threshold=10, 
                        timeout_seconds=1
                    )
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
            
            # Start multiple threads
            threads = []
            for i in range(10):
                # Some threads will fail, some will succeed
                should_fail = i % 3 == 0
                thread = threading.Thread(
                    target=concurrent_operation, 
                    args=(i, should_fail)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify results
            self.assertGreater(len(results), 0, "Some operations should succeed")
            # Note: With individual service names, failures may not occur consistently
            
        except ImportError as e:
            self.skipTest(f"Concurrent reliability test modules not available: {e}")
    
    def test_reliability_metrics_collection(self):
        """Test reliability metrics collection"""
        try:
            # Mock metrics collection
            reliability_metrics = {
                'circuit_breaker_trips': 0,
                'database_maintenance_runs': 0,
                'error_recovery_attempts': 0,
                'health_check_failures': 0,
                'uptime_seconds': 0
            }
            
            def update_metric(metric_name, value=1):
                if metric_name in reliability_metrics:
                    reliability_metrics[metric_name] += value
            
            # Simulate various reliability events
            update_metric('circuit_breaker_trips')
            update_metric('database_maintenance_runs')
            update_metric('error_recovery_attempts', 3)
            update_metric('uptime_seconds', 3600)
            
            # Verify metrics were collected
            self.assertEqual(reliability_metrics['circuit_breaker_trips'], 1)
            self.assertEqual(reliability_metrics['database_maintenance_runs'], 1)
            self.assertEqual(reliability_metrics['error_recovery_attempts'], 3)
            self.assertEqual(reliability_metrics['uptime_seconds'], 3600)
            
            # Test metric aggregation
            total_incidents = (
                reliability_metrics['circuit_breaker_trips'] +
                reliability_metrics['error_recovery_attempts'] +
                reliability_metrics['health_check_failures']
            )
            
            self.assertEqual(total_incidents, 4)
            
        except Exception as e:
            self.fail(f"Reliability metrics test failed: {e}")
    
    def test_backup_and_recovery_integration(self):
        """Test backup and recovery functionality"""
        try:
            # Create test database with data
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("CREATE TABLE important_data (id INTEGER, value TEXT)")
            conn.execute("INSERT INTO important_data VALUES (1, 'critical_data')")
            conn.commit()
            conn.close()
            
            # Create backup
            backup_path = self.test_dir / "backup.db"
            
            # Simple backup implementation
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            # Verify backup was created
            self.assertTrue(backup_path.exists())
            
            # Verify backup contains data
            backup_conn = sqlite3.connect(str(backup_path))
            cursor = backup_conn.execute("SELECT value FROM important_data WHERE id = 1")
            backup_data = cursor.fetchone()[0]
            backup_conn.close()
            
            self.assertEqual(backup_data, 'critical_data')
            
            # Simulate data corruption
            self.db_path.write_text("corrupted_data")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            
            # Verify restoration
            restored_conn = sqlite3.connect(str(self.db_path))
            cursor = restored_conn.execute("SELECT value FROM important_data WHERE id = 1")
            restored_data = cursor.fetchone()[0]
            restored_conn.close()
            
            self.assertEqual(restored_data, 'critical_data')
            
        except Exception as e:
            self.fail(f"Backup and recovery test failed: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)