#!/usr/bin/env python3
"""
Test suite for Recovery Scenarios - Phase 2
Tests corruption recovery and various failure scenarios.
"""

import json
import time
import shutil
import sqlite3
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from state_rebuilder import StateRebuilder
from event_logger import EventLogger


class TestRecoveryScenarios(unittest.TestCase):
    """Test recovery from various corruption and failure scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path("/tmp/aet_test_recovery")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Change to test directory
        self.original_cwd = Path.cwd()
        import os
        os.chdir(self.test_dir)
        
        # Initialize components
        self.rebuilder = StateRebuilder()
        self.event_logger = EventLogger()
        
        # Create comprehensive test events
        self.test_events = self._create_comprehensive_test_events()
        
    def tearDown(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_comprehensive_test_events(self):
        """Create comprehensive test events for recovery testing."""
        base_time = int(time.time() * 1000)
        events = []
        
        # Task creation and progression
        for i in range(3):
            ticket_id = f"TICKET-{i}"
            
            # Task created
            payload = {
                "job_id": f"job_{i}",
                "prompt": f"Test task {i}",
                "description": f"Test task description {i}"
            }
            checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            
            events.append({
                "event_id": f"evt_task_{i}_001",
                "ticket_id": ticket_id,
                "timestamp": base_time + i * 1000,
                "type": "TASK_CREATED",
                "payload": payload,
                "checksum": checksum
            })
            
            # Agent started
            payload = {"agent": "pm-agent"}
            checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            
            events.append({
                "event_id": f"evt_task_{i}_002",
                "ticket_id": ticket_id,
                "timestamp": base_time + i * 1000 + 100,
                "type": "AGENT_STARTED",
                "payload": payload,
                "checksum": checksum
            })
            
            # File created
            payload = {
                "path": f"src/test_{i}.py",
                "component": f"component_{i}",
                "checksum": f"file_checksum_{i}",
                "size": 1024 * (i + 1),
                "metadata": {"author": f"test_user_{i}"}
            }
            checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            
            events.append({
                "event_id": f"evt_task_{i}_003",
                "ticket_id": ticket_id,
                "timestamp": base_time + i * 1000 + 200,
                "type": "FILE_CREATED",
                "payload": payload,
                "checksum": checksum
            })
        
        return events
    
    def _write_events_to_log(self, events):
        """Write events to log file."""
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
    
    def _corrupt_snapshots_file(self, corruption_type="invalid_json"):
        """Corrupt the snapshots file in various ways."""
        snapshots_file = Path(".claude/snapshots/tasks.json")
        snapshots_file.parent.mkdir(parents=True, exist_ok=True)
        
        if corruption_type == "invalid_json":
            with open(snapshots_file, 'w') as f:
                f.write('{"invalid": json syntax}')
        
        elif corruption_type == "missing_fields":
            with open(snapshots_file, 'w') as f:
                json.dump({
                    "TICKET-0": {"incomplete": "snapshot"}
                }, f)
        
        elif corruption_type == "empty_file":
            snapshots_file.touch()
        
        elif corruption_type == "permission_denied":
            snapshots_file.touch()
            snapshots_file.chmod(0o000)  # No permissions
    
    def _corrupt_registry_database(self, corruption_type="missing_table"):
        """Corrupt the registry database in various ways."""
        registry_path = Path(".claude/registry/files.db")
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        if corruption_type == "missing_table":
            # Create DB without required tables
            with sqlite3.connect(registry_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
        
        elif corruption_type == "corrupt_schema":
            # Create DB with wrong schema
            with sqlite3.connect(registry_path) as conn:
                conn.execute("CREATE TABLE files (wrong_column TEXT)")
        
        elif corruption_type == "locked_database":
            # Create a locked database connection
            with sqlite3.connect(registry_path) as conn:
                conn.execute("BEGIN EXCLUSIVE")
                # Leave connection open to keep lock
    
    def test_recover_from_corrupted_snapshots(self):
        """Test recovery from corrupted snapshots file."""
        # Write events and create initial state
        self._write_events_to_log(self.test_events)
        
        # First build state successfully
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Corrupt snapshots in various ways
        corruption_types = ["invalid_json", "missing_fields", "empty_file"]
        
        for corruption_type in corruption_types:
            with self.subTest(corruption_type=corruption_type):
                self._corrupt_snapshots_file(corruption_type)
                
                # Rebuild should recover from corruption
                result = self.rebuilder.rebuild_from_events()
                self.assertEqual(result['status'], 'success')
                
                # Verify state was rebuilt correctly
                snapshots_file = Path(".claude/snapshots/tasks.json")
                self.assertTrue(snapshots_file.exists())
                
                with open(snapshots_file, 'r') as f:
                    snapshots = json.load(f)
                
                # Should have 3 tasks
                self.assertEqual(len(snapshots), 3)
                
                for i in range(3):
                    ticket_id = f"TICKET-{i}"
                    self.assertIn(ticket_id, snapshots)
                    self.assertEqual(snapshots[ticket_id]['status'], 'CREATED')
    
    def test_recover_from_corrupted_registry(self):
        """Test recovery from corrupted registry database."""
        self._write_events_to_log(self.test_events)
        
        # First build state successfully
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Corrupt registry database
        self._corrupt_registry_database("missing_table")
        
        # Rebuild should recover from corruption
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Verify registry was rebuilt correctly
        registry_path = Path(".claude/registry/files.db")
        self.assertTrue(registry_path.exists())
        
        with sqlite3.connect(registry_path) as conn:
            # Check that files table exists and has correct schema
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check files were recreated
            cursor = conn.execute("SELECT COUNT(*) FROM files")
            file_count = cursor.fetchone()[0]
            self.assertEqual(file_count, 3)  # 3 files from test events
    
    def test_recover_from_missing_state_files(self):
        """Test recovery when state files are completely missing."""
        self._write_events_to_log(self.test_events)
        
        # Ensure no existing state
        if Path(".claude/snapshots").exists():
            shutil.rmtree(Path(".claude/snapshots"))
        if Path(".claude/registry").exists():
            shutil.rmtree(Path(".claude/registry"))
        
        # Rebuild should create state from scratch
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Verify state was created
        self.assertTrue(Path(".claude/snapshots/tasks.json").exists())
        self.assertTrue(Path(".claude/registry/files.db").exists())
        
        # Verify content is correct
        with open(Path(".claude/snapshots/tasks.json"), 'r') as f:
            snapshots = json.load(f)
        
        self.assertEqual(len(snapshots), 3)
    
    def test_recover_from_partial_event_log_corruption(self):
        """Test recovery from partially corrupted event log."""
        # Create mix of good and corrupted events
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            # Good events
            for event in self.test_events[:3]:
                f.write(json.dumps(event) + '\n')
            
            # Corrupted events
            f.write('{"corrupted": json}\n')  # Invalid JSON
            f.write('incomplete line\n')       # Incomplete JSON
            
            # More good events
            for event in self.test_events[3:6]:
                f.write(json.dumps(event) + '\n')
            
            # Event with invalid checksum
            bad_event = self.test_events[6].copy()
            bad_event['checksum'] = 'invalid_checksum'
            f.write(json.dumps(bad_event) + '\n')
            
            # Final good events
            for event in self.test_events[7:]:
                f.write(json.dumps(event) + '\n')
        
        # Rebuild should handle corruption gracefully
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Should have processed only valid events
        self.assertGreater(result['events_processed'], 0)
        
        # Check that corrupted events were logged
        corrupted_log = Path(".claude/events/corrupted_events.json")
        self.assertTrue(corrupted_log.exists())
    
    def test_recover_from_disk_full_scenario(self):
        """Test recovery from disk full scenario during rebuild."""
        self._write_events_to_log(self.test_events)
        
        # Mock file write to simulate disk full
        original_open = open
        write_count = 0
        
        def disk_full_open(path, mode='r', *args, **kwargs):
            nonlocal write_count
            if 'w' in mode:
                write_count += 1
                if write_count > 2:  # Fail after 2 writes
                    raise OSError("No space left on device")
            return original_open(path, mode, *args, **kwargs)
        
        with patch('builtins.open', disk_full_open):
            result = self.rebuilder.rebuild_from_events()
            
            # Should fail gracefully
            self.assertEqual(result['status'], 'failed')
            self.assertIn("No space left on device", result['error'])
        
        # Temp directory should be cleaned up
        self.assertFalse(self.rebuilder.temp_dir.exists())
        
        # After "disk space recovered", rebuild should work
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
    
    def test_recover_from_permission_denied(self):
        """Test recovery from permission denied errors."""
        self._write_events_to_log(self.test_events)
        
        # Create directory structure with restricted permissions
        restricted_dir = Path(".claude/snapshots")
        restricted_dir.mkdir(parents=True, exist_ok=True)
        restricted_dir.chmod(0o555)  # Read-only
        
        try:
            result = self.rebuilder.rebuild_from_events()
            
            # Should fail due to permissions
            self.assertEqual(result['status'], 'failed')
            
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)
        
        # After permissions fixed, rebuild should work
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
    
    def test_recover_from_network_interruption_simulation(self):
        """Test recovery from simulated network interruption during rebuild."""
        self._write_events_to_log(self.test_events)
        
        # Simulate network timeout during file operations
        import socket
        original_connect = socket.socket.connect
        
        def timeout_connect(self, address):
            raise socket.timeout("Connection timed out")
        
        # This simulates a scenario where the rebuilder might be accessing
        # remote storage or logging to a remote service
        with patch.object(socket.socket, 'connect', timeout_connect):
            # Rebuild should still work (local operations)
            result = self.rebuilder.rebuild_from_events()
            self.assertEqual(result['status'], 'success')
    
    def test_automatic_corruption_detection(self):
        """Test automatic detection of corruption during rebuild."""
        self._write_events_to_log(self.test_events)
        
        # Build initial state
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Corrupt snapshots after successful build
        self._corrupt_snapshots_file("invalid_json")
        
        # Verify consistency check detects corruption
        consistency_result = self.rebuilder.verify_state_consistency()
        
        # Should detect inconsistency or error
        self.assertIn(consistency_result['status'], ['inconsistent', 'error'])
        self.assertGreater(len(consistency_result['issues']), 0)
    
    def test_incremental_recovery(self):
        """Test incremental recovery from a specific timestamp."""
        # Write initial events
        self._write_events_to_log(self.test_events[:6])
        
        # Build initial state
        result1 = self.rebuilder.rebuild_from_events()
        self.assertEqual(result1['status'], 'success')
        
        # Add more events
        additional_events = self.test_events[6:]
        all_events = self.test_events[:6] + additional_events
        self._write_events_to_log(all_events)
        
        # Incremental rebuild from timestamp of first additional event
        from_timestamp = additional_events[0]['timestamp']
        result2 = self.rebuilder.rebuild_from_events(from_timestamp=from_timestamp)
        
        self.assertEqual(result2['status'], 'success')
        # Should process only the additional events
        self.assertEqual(result2['events_processed'], len(additional_events))
    
    def test_concurrent_corruption_and_recovery(self):
        """Test recovery when corruption occurs during concurrent operations."""
        self._write_events_to_log(self.test_events)
        
        # Start rebuild
        def corrupt_during_rebuild():
            time.sleep(0.05)  # Let rebuild start
            self._corrupt_snapshots_file("invalid_json")
        
        import threading
        corruption_thread = threading.Thread(target=corrupt_during_rebuild)
        
        # Mock to slow down rebuild for race condition testing
        original_apply = self.rebuilder._apply_event_transactional
        def slow_apply(*args, **kwargs):
            time.sleep(0.01)  # Slow down each event
            return original_apply(*args, **kwargs)
        
        with patch.object(self.rebuilder, '_apply_event_transactional', slow_apply):
            corruption_thread.start()
            
            result = self.rebuilder.rebuild_from_events()
            
            corruption_thread.join()
        
        # Should handle concurrent corruption gracefully
        self.assertEqual(result['status'], 'success')
    
    def test_recovery_stress_test(self):
        """Stress test recovery with multiple types of corruption."""
        # Create larger dataset
        large_events = []
        base_time = int(time.time() * 1000)
        
        for i in range(50):  # 50 events for stress test
            payload = {"test": f"data_{i}", "index": i}
            checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            
            large_events.append({
                "event_id": f"stress_evt_{i:03d}",
                "ticket_id": f"STRESS-TICKET-{i % 5}",
                "timestamp": base_time + i * 100,
                "type": "TASK_CREATED" if i % 10 == 0 else "AGENT_STARTED",
                "payload": payload,
                "checksum": checksum
            })
        
        self._write_events_to_log(large_events)
        
        # Introduce multiple corruptions
        self._corrupt_snapshots_file("invalid_json")
        self._corrupt_registry_database("missing_table")
        
        # Add corrupted events to log
        log_path = Path(".claude/events/log.ndjson")
        with open(log_path, 'a') as f:
            f.write('{"corrupted": event}\n')
            f.write('incomplete\n')
        
        # Recovery should handle all corruptions
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Should process most events (excluding corrupted ones)
        self.assertGreater(result['events_processed'], 40)
        
        # Final state should be consistent
        consistency_result = self.rebuilder.verify_state_consistency()
        self.assertEqual(consistency_result['status'], 'consistent')


def run_recovery_scenarios_tests():
    """Run all recovery scenario tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_recovery_scenarios_tests()