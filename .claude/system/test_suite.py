#!/usr/bin/env python3
"""
AET System Test Suite
Comprehensive testing for all components.
"""

import json
import time
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import AET components
from event_logger import EventLogger
from workspace_manager import WorkspaceManager
from file_registry import FileRegistry
from orchestrator import TaskOrchestrator
from parallel_orchestrator import ParallelOrchestrator
from metrics import MetricsCollector
from dlq_manager import DeadLetterQueue
from rollback import RollbackManager
from reliability import HealthChecker, CircuitBreaker, RetryStrategy

class TestEventLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_path = Path(self.temp_dir) / "test_log.ndjson"
        self.logger = EventLogger(str(self.log_path))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_append_event(self):
        """Test event appending."""
        event = {"type": "TEST", "message": "test event"}
        self.logger.append_event(event)
        
        # Verify file exists and contains event
        self.assertTrue(self.log_path.exists())
        
        with open(self.log_path, 'r') as f:
            stored_event = json.loads(f.read().strip())
        
        self.assertEqual(stored_event["type"], "TEST")
        self.assertEqual(stored_event["message"], "test event")
        self.assertIn("timestamp", stored_event)
    
    def test_replay_events(self):
        """Test event replay."""
        events = [
            {"type": "EVENT1", "data": "first"},
            {"type": "EVENT2", "data": "second"},
            {"type": "EVENT3", "data": "third"}
        ]
        
        for event in events:
            self.logger.append_event(event)
        
        replayed = self.logger.replay_events()
        self.assertEqual(len(replayed), 3)
        self.assertEqual(replayed[0]["type"], "EVENT1")
        self.assertEqual(replayed[2]["type"], "EVENT3")

class TestWorkspaceManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(str(self.temp_dir))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_create_workspace(self):
        """Test workspace creation."""
        job_id = self.workspace_manager.create_workspace("TEST-001")
        
        workspace_path = Path(self.temp_dir) / job_id / "workspace"
        self.assertTrue(workspace_path.exists())
        
        # Check git initialization
        git_path = workspace_path / ".git"
        self.assertTrue(git_path.exists())
    
    def test_cleanup_workspace(self):
        """Test workspace cleanup."""
        job_id = self.workspace_manager.create_workspace("TEST-002")
        workspace_path = Path(self.temp_dir) / job_id
        
        self.assertTrue(workspace_path.exists())
        
        self.workspace_manager.cleanup_workspace(job_id)
        self.assertFalse(workspace_path.exists())

class TestFileRegistry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_files.db"
        self.registry = FileRegistry(str(self.db_path))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_register_file(self):
        """Test file registration."""
        file_path = "src/test.py"
        content_hash = "abc123"
        component = "test_component"
        
        file_id = self.registry.register_file(
            file_path, content_hash, component, "TEST-001"
        )
        
        self.assertIsNotNone(file_id)
        
        # Verify in database
        cursor = self.registry.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        
        self.assertEqual(row['path'], file_path)
        self.assertEqual(row['content_hash'], content_hash)
        self.assertEqual(row['component'], component)
    
    def test_get_file_info(self):
        """Test file info retrieval."""
        file_path = "src/another.py"
        content_hash = "def456"
        
        file_id = self.registry.register_file(
            file_path, content_hash, "another_component", "TEST-002"
        )
        
        info = self.registry.get_file_info(file_path)
        self.assertIsNotNone(info)
        self.assertEqual(info['file_id'], file_id)
        self.assertEqual(info['content_hash'], content_hash)

class TestParallelOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Mock the parent class dependencies
        with patch('orchestrator.TaskOrchestrator.__init__'):
            self.orchestrator = ParallelOrchestrator(max_workers=2)
            self.orchestrator.registry = MagicMock()
            self.orchestrator.workspace_manager = MagicMock()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_file_locks(self):
        """Test file locking mechanism."""
        ticket1 = "TEST-001"
        ticket2 = "TEST-002"
        files = {"file1.py", "file2.py"}
        
        # Acquire locks for ticket1
        success = self.orchestrator.acquire_file_locks(ticket1, files)
        self.assertTrue(success)
        
        # Try to acquire same files for ticket2 (should fail)
        success = self.orchestrator.acquire_file_locks(ticket2, files)
        self.assertFalse(success)
        
        # Release locks for ticket1
        self.orchestrator.release_file_locks(ticket1)
        
        # Now ticket2 should be able to acquire
        success = self.orchestrator.acquire_file_locks(ticket2, files)
        self.assertTrue(success)

class TestMetricsCollector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_metrics.db"
        self.metrics = MetricsCollector(str(self.db_path))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_task_metrics(self):
        """Test task metric recording."""
        ticket_id = "TEST-001"
        agent_name = "test-agent"
        
        # Start task
        metric_id = self.metrics.record_task_start(ticket_id, agent_name)
        self.assertIsNotNone(metric_id)
        
        # End task
        time.sleep(0.1)  # Small delay to ensure duration > 0
        self.metrics.record_task_end(metric_id, True)
        
        # Get performance metrics
        performance = self.metrics.get_agent_performance(agent_name)
        
        self.assertEqual(performance['total_tasks'], 1)
        self.assertEqual(performance['successful'], 1)
        self.assertEqual(performance['success_rate'], 1.0)
        self.assertGreater(performance['avg_duration_seconds'], 0)

class TestDeadLetterQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dlq = DeadLetterQueue(str(self.temp_dir))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_add_failed_task(self):
        """Test adding task to DLQ."""
        ticket_id = "FAILED-001"
        job_id = "job_123"
        reason = "Agent timeout"
        
        # Create dummy workspace
        workspace_path = Path(self.temp_dir) / "workspace"
        workspace_path.mkdir()
        (workspace_path / "test.txt").write_text("test content")
        
        entry_path = self.dlq.add_failed_task(
            ticket_id, job_id, reason, str(workspace_path)
        )
        
        self.assertTrue(Path(entry_path).exists())
        
        # Verify DLQ entry
        tasks = self.dlq.list_failed_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['ticket_id'], ticket_id)
        self.assertEqual(tasks[0]['reason'], reason)

class TestRollbackManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        Path.chdir(self.temp_dir)
        
        # Create dummy AET structure
        (Path(".claude/backups")).mkdir(parents=True)
        (Path(".claude/events")).mkdir(parents=True)
        (Path(".claude/snapshots")).mkdir(parents=True)
        (Path(".claude/registry")).mkdir(parents=True)
        
        # Create dummy files
        (Path(".claude/events/log.ndjson")).write_text("{}\n")
        (Path(".claude/snapshots/tasks.json")).write_text("{}")
        (Path(".claude/registry/files.db")).write_text("")
        
        self.rollback = RollbackManager()
    
    def tearDown(self):
        Path.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_create_backup(self):
        """Test backup creation."""
        label = "test_backup"
        backup_path = self.rollback.create_backup(label)
        
        self.assertTrue(Path(backup_path).exists())
        
        # Check backup contains expected files
        backup_dir = Path(backup_path)
        self.assertTrue((backup_dir / "metadata.json").exists())
        self.assertTrue((backup_dir / "log.ndjson").exists())
        self.assertTrue((backup_dir / "tasks.json").exists())
    
    def test_list_backups(self):
        """Test backup listing."""
        # Create a backup
        self.rollback.create_backup("test_list")
        
        backups = self.rollback.list_backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]['label'], "test_list")

class TestReliability(unittest.TestCase):
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        @breaker
        def failing_function():
            raise Exception("Simulated failure")
        
        # First failure
        with self.assertRaises(Exception):
            failing_function()
        self.assertEqual(breaker.failure_count, 1)
        self.assertEqual(breaker.state, 'CLOSED')
        
        # Second failure (should open circuit)
        with self.assertRaises(Exception):
            failing_function()
        self.assertEqual(breaker.failure_count, 2)
        self.assertEqual(breaker.state, 'OPEN')
        
        # Third call should fail due to open circuit
        with self.assertRaises(Exception) as cm:
            failing_function()
        self.assertIn("Circuit breaker OPEN", str(cm.exception))
    
    def test_retry_strategy(self):
        """Test retry strategy."""
        retry = RetryStrategy(max_attempts=3, backoff_base=0.1)  # Fast for testing
        
        call_count = 0
        
        @retry
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Not yet")
            return "success"
        
        result = sometimes_failing_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        Path.chdir(self.temp_dir)
        
        # Create AET directory structure
        dirs = [
            ".claude/agents", ".claude/events", ".claude/workspaces",
            ".claude/registry", ".claude/snapshots", ".claude/system"
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True)
    
    def tearDown(self):
        Path.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_task_lifecycle(self):
        """Test complete task lifecycle."""
        # Initialize components
        event_logger = EventLogger()
        workspace_manager = WorkspaceManager()
        file_registry = FileRegistry()
        
        # Create task
        ticket_id = "INTEGRATION-001"
        job_id = workspace_manager.create_workspace(ticket_id)
        
        # Log task creation
        event_logger.append_event({
            "type": "TASK_CREATED",
            "ticket_id": ticket_id,
            "job_id": job_id
        })
        
        # Register a file
        file_id = file_registry.register_file(
            "src/test.py", "hash123", "test_component", ticket_id
        )
        
        # Verify task workspace exists
        workspace_path = Path(f".claude/workspaces/{job_id}/workspace")
        self.assertTrue(workspace_path.exists())
        
        # Verify event was logged
        events = event_logger.replay_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "TASK_CREATED")
        
        # Verify file was registered
        file_info = file_registry.get_file_info("src/test.py")
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info["file_id"], file_id)
        
        # Cleanup
        workspace_manager.cleanup_workspace(job_id)
        self.assertFalse(workspace_path.exists())

def run_performance_tests():
    """Run performance benchmarks."""
    print("Running performance tests...")
    
    # Test event log performance
    temp_dir = tempfile.mkdtemp()
    try:
        logger = EventLogger(f"{temp_dir}/perf_log.ndjson")
        
        start_time = time.time()
        for i in range(1000):
            logger.append_event({"type": "PERF_TEST", "index": i})
        end_time = time.time()
        
        events_per_second = 1000 / (end_time - start_time)
        print(f"Event logging: {events_per_second:.1f} events/second")
        
        # Test replay performance
        start_time = time.time()
        events = logger.replay_events()
        end_time = time.time()
        
        replay_time = end_time - start_time
        print(f"Event replay: {len(events)} events in {replay_time:.3f}s")
        
    finally:
        shutil.rmtree(temp_dir)

def run_load_tests():
    """Run load tests with multiple workers."""
    print("Running load tests...")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Test parallel orchestrator under load
        with patch('orchestrator.TaskOrchestrator.__init__'):
            orchestrator = ParallelOrchestrator(max_workers=5)
            orchestrator.registry = MagicMock()
            orchestrator.workspace_manager = MagicMock()
            
            # Simulate concurrent file access
            import threading
            import random
            
            def worker(worker_id):
                for i in range(10):
                    ticket_id = f"LOAD-{worker_id}-{i}"
                    files = {f"file_{random.randint(1, 20)}.py"}
                    
                    acquired = orchestrator.acquire_file_locks(ticket_id, files)
                    if acquired:
                        time.sleep(0.01)  # Simulate work
                        orchestrator.release_file_locks(ticket_id)
            
            threads = []
            start_time = time.time()
            
            for i in range(10):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            print(f"Load test completed in {end_time - start_time:.2f}s")
            
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "="*50)
    
    # Run performance tests
    run_performance_tests()
    
    print("\n" + "="*50)
    
    # Run load tests
    run_load_tests()
    
    print("\nAll tests completed!")