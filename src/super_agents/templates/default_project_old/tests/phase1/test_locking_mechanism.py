#!/usr/bin/env python3
"""
Phase 1 Locking Tests: Lock Acquisition and Cleanup
Tests the enhanced locking mechanism in parallel_orchestrator.py
"""

import unittest
import tempfile
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add system path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from parallel_orchestrator import ParallelOrchestrator
from file_registry import FileRegistry


class TestLockingMechanism(unittest.TestCase):
    """Test enhanced locking mechanism with cleanup from Phase 1."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test directories
        os.makedirs(".claude/registry", exist_ok=True)
        os.makedirs(".claude/snapshots", exist_ok=True)
        os.makedirs(".claude/workspaces", exist_ok=True)
        
        # Mock the orchestrator dependencies
        with patch('parallel_orchestrator.TaskOrchestrator.__init__', return_value=None):
            self.orchestrator = ParallelOrchestrator(max_workers=2)
            
        # Set up registry manually
        self.orchestrator.registry = FileRegistry(db_path=f"{self.temp_dir}/.claude/registry/test.db")
        
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self.orchestrator, 'resource_manager'):
            self.orchestrator.resource_manager.shutdown()
        if hasattr(self.orchestrator, 'registry'):
            self.orchestrator.registry.close()
        os.chdir(self.original_cwd)
    
    def test_successful_lock_acquisition(self):
        """Test successful acquisition of file locks."""
        ticket_id = "TEST-LOCK-001"
        files = {"src/test1.py", "src/test2.py"}
        
        # Should successfully acquire locks
        success = self.orchestrator.acquire_file_locks(ticket_id, files)
        self.assertTrue(success, "Should successfully acquire locks on available files")
        
        # Verify locks are recorded in registry
        for file_path in files:
            cursor = self.orchestrator.registry.conn.cursor()
            cursor.execute("""
                SELECT lock_owner, lock_status FROM files 
                WHERE path = ? AND lock_status = 'locked'
            """, (file_path,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, f"Lock should be recorded for {file_path}")
            self.assertEqual(row['lock_owner'], ticket_id)
    
    def test_lock_conflict_detection(self):
        """Test that lock conflicts are properly detected."""
        ticket1 = "TEST-LOCK-002A"
        ticket2 = "TEST-LOCK-002B" 
        files = {"src/shared.py"}
        
        # First ticket acquires lock
        success1 = self.orchestrator.acquire_file_locks(ticket1, files)
        self.assertTrue(success1, "First ticket should acquire lock")
        
        # Second ticket should fail to acquire same lock
        success2 = self.orchestrator.acquire_file_locks(ticket2, files)
        self.assertFalse(success2, "Second ticket should fail to acquire conflicting lock")
    
    def test_partial_failure_cleanup(self):
        """Test cleanup when partial lock acquisition fails."""
        ticket1 = "TEST-LOCK-003A"
        ticket2 = "TEST-LOCK-003B"
        
        # First ticket locks one file
        files1 = {"src/file1.py"}
        success1 = self.orchestrator.acquire_file_locks(ticket1, files1)
        self.assertTrue(success1, "First ticket should acquire initial lock")
        
        # Second ticket tries to lock multiple files, including conflicting one
        files2 = {"src/file2.py", "src/file1.py", "src/file3.py"}  # file1.py conflicts
        success2 = self.orchestrator.acquire_file_locks(ticket2, files2)
        self.assertFalse(success2, "Second ticket should fail due to conflict")
        
        # Verify that no locks were left for ticket2 (cleanup occurred)
        cursor = self.orchestrator.registry.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM files 
            WHERE lock_owner = ? AND lock_status = 'locked'
        """, (ticket2,))
        count = cursor.fetchone()['count']
        self.assertEqual(count, 0, "Failed ticket should have no remaining locks")
        
        # Verify file2.py and file3.py are not locked by anyone
        for file_path in ["src/file2.py", "src/file3.py"]:
            cursor.execute("""
                SELECT lock_status FROM files 
                WHERE path = ? AND lock_status = 'locked'
            """, (file_path,))
            row = cursor.fetchone()
            self.assertIsNone(row, f"{file_path} should not be locked after cleanup")
    
    def test_lock_release(self):
        """Test proper release of all locks for a ticket."""
        ticket_id = "TEST-LOCK-004"
        files = {"src/test1.py", "src/test2.py", "src/test3.py"}
        
        # Acquire locks
        success = self.orchestrator.acquire_file_locks(ticket_id, files)
        self.assertTrue(success, "Should acquire locks")
        
        # Release locks
        self.orchestrator.release_file_locks(ticket_id)
        
        # Verify all locks are released
        cursor = self.orchestrator.registry.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM files 
            WHERE lock_owner = ? AND lock_status = 'locked'
        """, (ticket_id,))
        count = cursor.fetchone()['count']
        self.assertEqual(count, 0, "All locks should be released")
    
    def test_concurrent_lock_acquisition(self):
        """Test concurrent lock acquisition by multiple threads."""
        files = {"src/concurrent_test.py"}
        results = {}
        
        def acquire_lock_thread(ticket_id):
            """Thread function to acquire locks."""
            success = self.orchestrator.acquire_file_locks(ticket_id, files)
            results[ticket_id] = success
            if success:
                time.sleep(0.1)  # Hold lock briefly
                self.orchestrator.release_file_locks(ticket_id)
        
        # Start multiple threads trying to acquire same lock
        threads = []
        for i in range(5):
            ticket_id = f"CONCURRENT-{i}"
            thread = threading.Thread(target=acquire_lock_thread, args=(ticket_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        # Exactly one thread should have succeeded
        successful_tickets = [ticket for ticket, success in results.items() if success]
        self.assertEqual(len(successful_tickets), 1, 
                        f"Exactly one thread should succeed, got: {successful_tickets}")
    
    def test_exception_handling_during_acquisition(self):
        """Test proper cleanup when exceptions occur during lock acquisition."""
        ticket_id = "TEST-LOCK-006"
        files = {"src/test1.py", "src/test2.py"}
        
        # Mock the registry to raise exception on second file
        original_acquire = self.orchestrator.registry.acquire_lock
        call_count = 0
        
        def mock_acquire_lock(path, ticket):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_acquire(path, ticket)  # First call succeeds
            else:
                raise Exception("Simulated database error")  # Second call fails
        
        with patch.object(self.orchestrator.registry, 'acquire_lock', side_effect=mock_acquire_lock):
            success = self.orchestrator.acquire_file_locks(ticket_id, files)
            self.assertFalse(success, "Should fail due to exception")
        
        # Verify cleanup occurred - no locks should remain
        cursor = self.orchestrator.registry.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM files 
            WHERE lock_owner = ? AND lock_status = 'locked'
        """, (ticket_id,))
        count = cursor.fetchone()['count']
        self.assertEqual(count, 0, "No locks should remain after exception")
    
    def test_lock_expiration_cleanup(self):
        """Test that expired locks are properly cleaned up."""
        ticket_id = "TEST-LOCK-007"
        files = {"src/expiring.py"}
        
        # Acquire lock with very short duration
        success = self.orchestrator.acquire_file_locks(ticket_id, files)
        self.assertTrue(success, "Should acquire lock")
        
        # Manually expire the lock by setting past expiry time
        cursor = self.orchestrator.registry.conn.cursor()
        cursor.execute("""
            UPDATE files 
            SET lock_expiry = datetime('now', '-1 hour')
            WHERE lock_owner = ?
        """, (ticket_id,))
        self.orchestrator.registry.conn.commit()
        
        # Cleanup expired locks
        cleaned_count = self.orchestrator.registry.cleanup_expired_locks()
        self.assertGreater(cleaned_count, 0, "Should clean up expired locks")
        
        # Verify lock is no longer active
        cursor.execute("""
            SELECT COUNT(*) as count FROM files 
            WHERE lock_owner = ? AND lock_status = 'locked'
        """, (ticket_id,))
        count = cursor.fetchone()['count']
        self.assertEqual(count, 0, "Expired lock should be cleaned up")
    
    def test_resource_manager_integration(self):
        """Test integration with ResourceManager."""
        # Test that ResourceManager is properly initialized
        self.assertIsNotNone(self.orchestrator.resource_manager, 
                           "ResourceManager should be initialized")
        
        # Test resource status reporting
        status = self.orchestrator.resource_manager.get_resource_status()
        self.assertIn('cpu_percent', status)
        self.assertIn('memory_percent', status)
        self.assertIn('active_tasks', status)
        
        # Test resource permit acquisition
        ticket_id = "RESOURCE-TEST-001"
        permit_granted = self.orchestrator.resource_manager.acquire_resource_permit(ticket_id)
        self.assertTrue(permit_granted, "Should grant resource permit under normal conditions")
        
        # Clean up
        self.orchestrator.resource_manager.release_resource_permit(ticket_id)
    
    def test_no_deadlocks_in_concurrent_operations(self):
        """Test that concurrent operations don't cause deadlocks."""
        num_threads = 4
        num_files = 3
        results = []
        
        def concurrent_operation(thread_id):
            """Simulate concurrent file operations."""
            ticket_id = f"DEADLOCK-TEST-{thread_id}"
            files = {f"src/file{i}.py" for i in range(num_files)}
            
            try:
                # Try to acquire locks
                if self.orchestrator.acquire_file_locks(ticket_id, files):
                    time.sleep(0.1)  # Simulate work
                    self.orchestrator.release_file_locks(ticket_id)
                    results.append(f"SUCCESS-{thread_id}")
                else:
                    results.append(f"BLOCKED-{thread_id}")
            except Exception as e:
                results.append(f"ERROR-{thread_id}: {e}")
        
        # Start concurrent threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion with timeout to detect deadlocks
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive(), "Thread should complete (no deadlock)")
        
        # All threads should have completed with some result
        self.assertEqual(len(results), num_threads, 
                        f"All threads should complete, got results: {results}")


class TestResourceManagerEnforcement(unittest.TestCase):
    """Test ResourceManager enforcement capabilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create minimal orchestrator for resource manager testing
        with patch('parallel_orchestrator.TaskOrchestrator.__init__', return_value=None):
            self.orchestrator = ParallelOrchestrator(max_workers=2)
    
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self.orchestrator, 'resource_manager'):
            self.orchestrator.resource_manager.shutdown()
        os.chdir(self.original_cwd)
    
    def test_task_limit_enforcement(self):
        """Test that task limits are enforced."""
        rm = self.orchestrator.resource_manager
        rm.max_concurrent_tasks = 2
        
        # Acquire maximum allowed permits
        permit1 = rm.acquire_resource_permit("TASK-1")
        permit2 = rm.acquire_resource_permit("TASK-2")
        self.assertTrue(permit1, "First permit should be granted")
        self.assertTrue(permit2, "Second permit should be granted")
        
        # Third permit should be queued/denied
        permit3 = rm.acquire_resource_permit("TASK-3", timeout=1)
        self.assertFalse(permit3, "Third permit should be denied/queued")
        
        # Release one permit
        rm.release_resource_permit("TASK-1")
        
        # Now permit should be available
        permit4 = rm.acquire_resource_permit("TASK-4")
        self.assertTrue(permit4, "Permit should be available after release")
        
        # Clean up
        rm.release_resource_permit("TASK-2")
        rm.release_resource_permit("TASK-4")
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_resource_limit_enforcement(self, mock_memory, mock_cpu):
        """Test CPU and memory limit enforcement."""
        rm = self.orchestrator.resource_manager
        
        # Mock high resource usage
        mock_cpu.return_value = 90.0  # Above 70% limit
        mock_memory.return_value = MagicMock(percent=90.0)  # Above 80% limit
        
        # Give some time for monitoring to pick up values
        time.sleep(0.1)
        
        # Permit should be denied due to high resource usage
        permit = rm.acquire_resource_permit("HIGH-RESOURCE-TASK", timeout=1)
        self.assertFalse(permit, "Permit should be denied due to high resource usage")


if __name__ == "__main__":
    unittest.main()