#!/usr/bin/env python3
"""
Phase 1 Resource Manager Tests: Resource Enforcement
Tests the ResourceManager class with actual enforcement capabilities
"""

import unittest
import tempfile
import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add system path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from parallel_orchestrator import ResourceManager


class TestResourceManager(unittest.TestCase):
    """Test ResourceManager enforcement and monitoring."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create ResourceManager with test limits
        self.rm = ResourceManager(
            max_cpu_percent=70.0,
            max_memory_percent=80.0,
            max_concurrent_tasks=3
        )
        
        # Give monitoring thread time to start
        time.sleep(0.1)
        
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'rm'):
            self.rm.shutdown()
        os.chdir(self.original_cwd)
    
    def test_resource_manager_initialization(self):
        """Test proper initialization of ResourceManager."""
        self.assertEqual(self.rm.max_cpu_percent, 70.0)
        self.assertEqual(self.rm.max_memory_percent, 80.0)
        self.assertEqual(self.rm.max_concurrent_tasks, 3)
        self.assertEqual(self.rm.current_tasks, 0)
        self.assertTrue(self.rm._monitoring, "Monitoring should be active")
    
    def test_resource_status_reporting(self):
        """Test resource status reporting functionality."""
        status = self.rm.get_resource_status()
        
        # Check required fields are present
        required_fields = [
            'cpu_percent', 'memory_percent', 'active_tasks', 'queued_tasks',
            'cpu_limit_exceeded', 'memory_limit_exceeded', 'task_limit_exceeded'
        ]
        
        for field in required_fields:
            self.assertIn(field, status, f"Status should include {field}")
        
        # Check data types
        self.assertIsInstance(status['cpu_percent'], (int, float))
        self.assertIsInstance(status['memory_percent'], (int, float))
        self.assertIsInstance(status['active_tasks'], int)
        self.assertIsInstance(status['queued_tasks'], int)
        self.assertIsInstance(status['cpu_limit_exceeded'], bool)
        self.assertIsInstance(status['memory_limit_exceeded'], bool)
        self.assertIsInstance(status['task_limit_exceeded'], bool)
    
    def test_task_limit_enforcement(self):
        """Test that task limits are actually enforced."""
        # Fill up to task limit
        permits_granted = []
        for i in range(self.rm.max_concurrent_tasks):
            permit = self.rm.acquire_resource_permit(f"TASK-{i}")
            permits_granted.append(permit)
        
        # All permits up to limit should be granted
        self.assertTrue(all(permits_granted), "All permits up to limit should be granted")
        self.assertEqual(self.rm.current_tasks, self.rm.max_concurrent_tasks)
        
        # Next permit should be denied/queued
        permit_over_limit = self.rm.acquire_resource_permit("TASK-OVER-LIMIT", timeout=1)
        self.assertFalse(permit_over_limit, "Permit over limit should be denied/queued")
        
        # Release one permit
        self.rm.release_resource_permit("TASK-0")
        self.assertEqual(self.rm.current_tasks, self.rm.max_concurrent_tasks - 1)
        
        # Now permit should be available
        new_permit = self.rm.acquire_resource_permit("TASK-NEW")
        self.assertTrue(new_permit, "Permit should be available after release")
        
        # Clean up remaining permits
        for i in range(1, self.rm.max_concurrent_tasks):
            self.rm.release_resource_permit(f"TASK-{i}")
        self.rm.release_resource_permit("TASK-NEW")
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_cpu_limit_enforcement(self, mock_memory, mock_cpu):
        """Test CPU usage limit enforcement."""
        # Mock normal memory, high CPU
        mock_memory.return_value = MagicMock(percent=50.0)  # Normal memory
        mock_cpu.return_value = 85.0  # Above 70% limit
        
        # Allow monitoring to pick up the values
        time.sleep(1.5)  # CPU monitoring has 1s interval
        
        # Permit should be denied due to high CPU
        permit = self.rm.acquire_resource_permit("HIGH-CPU-TASK", timeout=1)
        self.assertFalse(permit, "Permit should be denied due to high CPU usage")
        
        # Check status reflects CPU limit exceeded
        status = self.rm.get_resource_status()
        self.assertTrue(status['cpu_limit_exceeded'], "Status should show CPU limit exceeded")
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_memory_limit_enforcement(self, mock_memory, mock_cpu):
        """Test memory usage limit enforcement."""
        # Mock normal CPU, high memory
        mock_cpu.return_value = 30.0  # Normal CPU
        mock_memory.return_value = MagicMock(percent=90.0)  # Above 80% limit
        
        # Allow monitoring to pick up the values
        time.sleep(1.5)
        
        # Permit should be denied due to high memory
        permit = self.rm.acquire_resource_permit("HIGH-MEMORY-TASK", timeout=1)
        self.assertFalse(permit, "Permit should be denied due to high memory usage")
        
        # Check status reflects memory limit exceeded
        status = self.rm.get_resource_status()
        self.assertTrue(status['memory_limit_exceeded'], "Status should show memory limit exceeded")
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_resource_recovery(self, mock_memory, mock_cpu):
        """Test that permits are granted when resources recover."""
        # Start with high resource usage
        mock_cpu.return_value = 85.0  # High CPU
        mock_memory.return_value = MagicMock(percent=90.0)  # High memory
        
        # Allow monitoring to detect high usage
        time.sleep(1.5)
        
        # Permit should be denied
        permit1 = self.rm.acquire_resource_permit("TASK-1", timeout=1)
        self.assertFalse(permit1, "Should be denied due to high resource usage")
        
        # Now simulate resource recovery
        mock_cpu.return_value = 30.0  # Normal CPU
        mock_memory.return_value = MagicMock(percent=40.0)  # Normal memory
        
        # Allow monitoring to detect recovery
        time.sleep(1.5)
        
        # Permit should now be granted
        permit2 = self.rm.acquire_resource_permit("TASK-2")
        self.assertTrue(permit2, "Should be granted after resource recovery")
        
        # Clean up
        self.rm.release_resource_permit("TASK-2")
    
    def test_queue_processing(self):
        """Test task queue processing when resources become available."""
        # Fill up task slots
        for i in range(self.rm.max_concurrent_tasks):
            permit = self.rm.acquire_resource_permit(f"INITIAL-{i}")
            self.assertTrue(permit)
        
        # Queue additional tasks (should be denied immediately)
        queued_tasks = []
        for i in range(2):
            permit = self.rm.acquire_resource_permit(f"QUEUED-{i}", timeout=1)
            self.assertFalse(permit, "Should be queued due to task limit")
            queued_tasks.append(f"QUEUED-{i}")
        
        # Check queue has tasks
        status = self.rm.get_resource_status()
        self.assertGreater(status['queued_tasks'], 0, "Queue should have tasks")
        
        # Release one task slot
        self.rm.release_resource_permit("INITIAL-0")
        
        # Process queued tasks
        processed_tasks = list(self.rm.process_queued_tasks())
        self.assertGreater(len(processed_tasks), 0, "Should process queued tasks")
        
        # Clean up remaining tasks
        for i in range(1, self.rm.max_concurrent_tasks):
            self.rm.release_resource_permit(f"INITIAL-{i}")
        for task in processed_tasks:
            self.rm.release_resource_permit(task)
    
    def test_emergency_throttling(self):
        """Test emergency throttling functionality."""
        original_max_tasks = self.rm.max_concurrent_tasks
        
        # Trigger emergency throttling
        self.rm.emergency_throttle()
        
        # Max tasks should be reduced
        self.assertLess(self.rm.max_concurrent_tasks, original_max_tasks, 
                       "Emergency throttling should reduce max tasks")
        self.assertGreaterEqual(self.rm.max_concurrent_tasks, 1,
                              "Should maintain at least 1 task slot")
    
    def test_concurrent_permit_acquisition(self):
        """Test concurrent resource permit acquisition."""
        results = {}
        
        def acquire_permit_thread(thread_id):
            """Thread function to acquire resource permits."""
            permit = self.rm.acquire_resource_permit(f"CONCURRENT-{thread_id}")
            results[thread_id] = permit
            if permit:
                time.sleep(0.1)  # Hold permit briefly
                self.rm.release_resource_permit(f"CONCURRENT-{thread_id}")
        
        # Start more threads than available slots
        num_threads = self.rm.max_concurrent_tasks + 2
        threads = []
        
        for i in range(num_threads):
            thread = threading.Thread(target=acquire_permit_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(), "Thread should complete")
        
        # Count successful permits
        successful_permits = sum(1 for success in results.values() if success)
        
        # Should not exceed max concurrent tasks
        self.assertLessEqual(successful_permits, self.rm.max_concurrent_tasks,
                           "Should not exceed max concurrent tasks")
        self.assertGreater(successful_permits, 0, "At least some permits should be granted")
    
    def test_resource_monitoring_thread(self):
        """Test that resource monitoring thread is working."""
        # Check that monitoring thread is alive
        self.assertTrue(self.rm._monitoring, "Monitoring should be active")
        self.assertTrue(self.rm._monitor_thread.is_alive(), "Monitor thread should be running")
        
        # Let monitoring collect some data
        time.sleep(2.0)
        
        # Should have collected some readings
        self.assertGreater(len(self.rm._cpu_readings), 0, "Should have CPU readings")
        self.assertGreater(len(self.rm._memory_readings), 0, "Should have memory readings")
        
        # Readings should be within reasonable bounds
        for reading in self.rm._cpu_readings:
            self.assertGreaterEqual(reading, 0, "CPU reading should be non-negative")
            self.assertLessEqual(reading, 100, "CPU reading should be <= 100%")
        
        for reading in self.rm._memory_readings:
            self.assertGreaterEqual(reading, 0, "Memory reading should be non-negative")
            self.assertLessEqual(reading, 100, "Memory reading should be <= 100%")
    
    def test_resource_manager_shutdown(self):
        """Test proper shutdown of ResourceManager."""
        # Check initial state
        self.assertTrue(self.rm._monitoring, "Should be monitoring initially")
        self.assertTrue(self.rm._monitor_thread.is_alive(), "Monitor thread should be running")
        
        # Shutdown
        self.rm.shutdown()
        
        # Check shutdown state
        self.assertFalse(self.rm._monitoring, "Should stop monitoring after shutdown")
        
        # Wait for thread to finish
        self.rm._monitor_thread.join(timeout=10)
        self.assertFalse(self.rm._monitor_thread.is_alive(), "Monitor thread should stop")
    
    def test_rolling_window_resource_readings(self):
        """Test that resource readings maintain a rolling window."""
        # Let monitoring collect readings beyond window size
        time.sleep(3.0)  # Enough time for more than 10 readings
        
        # Should maintain rolling window of max 10 readings
        self.assertLessEqual(len(self.rm._cpu_readings), 10, 
                           "Should maintain max 10 CPU readings")
        self.assertLessEqual(len(self.rm._memory_readings), 10,
                           "Should maintain max 10 memory readings")
        
        # Should have some readings
        self.assertGreater(len(self.rm._cpu_readings), 0, "Should have CPU readings")
        self.assertGreater(len(self.rm._memory_readings), 0, "Should have memory readings")
    
    @patch('psutil.cpu_percent')
    def test_monitoring_error_handling(self, mock_cpu):
        """Test that monitoring handles errors gracefully."""
        # Make CPU monitoring fail
        mock_cpu.side_effect = Exception("Monitoring error")
        
        # Wait for monitoring to attempt several readings
        time.sleep(3.0)
        
        # Resource manager should still be functional
        status = self.rm.get_resource_status()
        self.assertIsInstance(status, dict, "Should still return status dict")
        
        # Should handle errors gracefully
        permit = self.rm.acquire_resource_permit("ERROR-TEST")
        self.assertIsInstance(permit, bool, "Should still process permits")
        
        if permit:
            self.rm.release_resource_permit("ERROR-TEST")


class TestResourceManagerIntegration(unittest.TestCase):
    """Integration tests for ResourceManager with real system resources."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.rm = ResourceManager(
            max_cpu_percent=90.0,  # High limits for integration testing
            max_memory_percent=95.0,
            max_concurrent_tasks=2
        )
        time.sleep(0.1)  # Let monitoring start
    
    def tearDown(self):
        """Clean up integration test environment."""
        self.rm.shutdown()
    
    def test_real_resource_monitoring(self):
        """Test monitoring with real system resources."""
        # Let monitoring collect real data
        time.sleep(2.0)
        
        status = self.rm.get_resource_status()
        
        # Should have real resource data
        self.assertGreater(status['cpu_percent'], 0, "Should have real CPU data")
        self.assertGreater(status['memory_percent'], 0, "Should have real memory data")
        
        # Values should be reasonable
        self.assertLess(status['cpu_percent'], 100, "CPU should be < 100%")
        self.assertLess(status['memory_percent'], 100, "Memory should be < 100%")
    
    def test_permit_acquisition_under_normal_load(self):
        """Test permit acquisition under normal system load."""
        # Under normal conditions, permits should be granted
        permits = []
        for i in range(self.rm.max_concurrent_tasks):
            permit = self.rm.acquire_resource_permit(f"NORMAL-{i}")
            permits.append((f"NORMAL-{i}", permit))
        
        # All permits should be granted under normal load
        granted_count = sum(1 for _, granted in permits if granted)
        self.assertEqual(granted_count, self.rm.max_concurrent_tasks,
                        "All permits should be granted under normal load")
        
        # Clean up
        for task_id, granted in permits:
            if granted:
                self.rm.release_resource_permit(task_id)


if __name__ == "__main__":
    # Run with verbose output for better debugging
    unittest.main(verbosity=2)