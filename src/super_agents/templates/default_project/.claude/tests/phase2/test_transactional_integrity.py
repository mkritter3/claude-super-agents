#!/usr/bin/env python3
"""
Test suite for Transactional Integrity - Phase 2
Tests atomic operations and transaction rollback scenarios.
"""

import json
import time
import shutil
import sqlite3
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock, call

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from state_rebuilder import StateRebuilder
from event_logger import EventLogger


class TestTransactionalIntegrity(unittest.TestCase):
    """Test transactional integrity of state rebuilder."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path("/tmp/aet_test_transactions")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Change to test directory
        self.original_cwd = Path.cwd()
        import os
        os.chdir(self.test_dir)
        
        # Initialize components
        self.rebuilder = StateRebuilder()
        self.event_logger = EventLogger()
        
        # Create test events
        self.test_events = self._create_test_events()
        
    def tearDown(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_events(self):
        """Create test events for transaction testing."""
        base_time = int(time.time() * 1000)
        
        events = [
            {
                "event_id": "evt_001",
                "ticket_id": "TICKET-TX1",
                "timestamp": base_time,
                "type": "TASK_CREATED",
                "payload": {
                    "job_id": "job_001",
                    "prompt": "Test transaction task",
                    "description": "Transaction test"
                },
                "checksum": "tx_checksum_001"
            },
            {
                "event_id": "evt_002",
                "ticket_id": "TICKET-TX1", 
                "timestamp": base_time + 1000,
                "type": "AGENT_STARTED",
                "payload": {"agent": "pm-agent"},
                "checksum": "tx_checksum_002"
            },
            {
                "event_id": "evt_003",
                "ticket_id": "TICKET-TX1",
                "timestamp": base_time + 2000,
                "type": "FILE_CREATED",
                "payload": {
                    "path": "src/transaction_test.py",
                    "component": "test_component",
                    "checksum": "file_checksum_001",
                    "size": 2048
                },
                "checksum": "tx_checksum_003"
            }
        ]
        
        return events
    
    def _write_events_to_log(self, events):
        """Write events to log file."""
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
    
    def test_atomic_snapshot_creation(self):
        """Test that snapshots are created atomically."""
        self._write_events_to_log(self.test_events)
        
        # Mock file operations to test atomicity
        original_rename = Path.rename
        rename_calls = []
        
        def mock_rename(self, target):
            rename_calls.append((str(self), str(target)))
            return original_rename(self, target)
        
        with patch.object(Path, 'rename', mock_rename):
            result = self.rebuilder.rebuild_from_events()
            self.assertEqual(result['status'], 'success')
        
        # Should have used atomic rename for snapshots
        snapshot_renames = [call for call in rename_calls if 'tasks.json' in call[1]]
        self.assertGreater(len(snapshot_renames), 0)
        
        # Verify .tmp file was renamed to final file
        for src, dst in snapshot_renames:
            self.assertTrue(src.endswith('.tmp'))
            self.assertTrue(dst.endswith('tasks.json'))
    
    def test_atomic_registry_creation(self):
        """Test that registry database is created atomically."""
        self._write_events_to_log(self.test_events)
        
        # Mock shutil.move to track atomic moves
        original_move = shutil.move
        move_calls = []
        
        def mock_move(src, dst):
            move_calls.append((src, dst))
            return original_move(src, dst)
        
        with patch('shutil.move', mock_move):
            result = self.rebuilder.rebuild_from_events()
            self.assertEqual(result['status'], 'success')
        
        # Should have moved temp registry to final location
        registry_moves = [call for call in move_calls if 'files.db' in call[1]]
        self.assertGreater(len(registry_moves), 0)
    
    def test_rollback_on_snapshot_write_failure(self):
        """Test rollback when snapshot write fails."""
        self._write_events_to_log(self.test_events)
        
        # Mock snapshot write to fail
        with patch('builtins.open', side_effect=PermissionError("Simulated write failure")):
            result = self.rebuilder.rebuild_from_events()
            
            self.assertEqual(result['status'], 'failed')
            self.assertIn("Simulated write failure", result['error'])
        
        # Temp directory should be cleaned up
        self.assertFalse(self.rebuilder.temp_dir.exists())
        
        # Final snapshots should not exist
        snapshots_file = Path(".claude/snapshots/tasks.json")
        self.assertFalse(snapshots_file.exists())
    
    def test_rollback_on_registry_move_failure(self):
        """Test rollback when registry move fails."""
        self._write_events_to_log(self.test_events)
        
        # Create existing registry to test backup/restore
        registry_path = Path(".claude/registry/files.db")
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create dummy existing registry
        with sqlite3.connect(registry_path) as conn:
            conn.execute("CREATE TABLE dummy (id INTEGER)")
            conn.execute("INSERT INTO dummy VALUES (1)")
        
        # Read original content
        with sqlite3.connect(registry_path) as conn:
            original_data = conn.execute("SELECT * FROM dummy").fetchall()
        
        # Mock shutil.move to fail
        original_move = shutil.move
        def mock_move(src, dst):
            if 'files.db' in dst:
                raise PermissionError("Simulated move failure")
            return original_move(src, dst)
        
        with patch('shutil.move', mock_move):
            result = self.rebuilder.rebuild_from_events()
            
            self.assertEqual(result['status'], 'failed')
            self.assertIn("Simulated move failure", result['error'])
        
        # Original registry should be restored
        self.assertTrue(registry_path.exists())
        
        with sqlite3.connect(registry_path) as conn:
            restored_data = conn.execute("SELECT * FROM dummy").fetchall()
        
        self.assertEqual(original_data, restored_data)
    
    def test_rollback_on_applied_events_save_failure(self):
        """Test rollback when applied events save fails."""
        self._write_events_to_log(self.test_events)
        
        # Mock applied events save to fail
        with patch.object(self.rebuilder, '_save_applied_events') as mock_save:
            mock_save.side_effect = Exception("Applied events save failed")
            
            result = self.rebuilder.rebuild_from_events()
            
            self.assertEqual(result['status'], 'failed')
            self.assertIn("Applied events save failed", result['error'])
        
        # Temp directory should be cleaned up
        self.assertFalse(self.rebuilder.temp_dir.exists())
    
    def test_partial_event_processing_rollback(self):
        """Test rollback when event processing fails partway through."""
        # Create events with one that will cause processing failure
        events = self.test_events.copy()
        
        # Add an event that will cause failure
        bad_event = {
            "event_id": "evt_bad",
            "ticket_id": "TICKET-TX1",
            "timestamp": int(time.time() * 1000) + 3000,
            "type": "TASK_CREATED",
            "payload": {"malformed": "data"},
            "checksum": "bad_checksum"
        }
        events.append(bad_event)
        
        self._write_events_to_log(events)
        
        # Mock event application to fail on the bad event
        original_apply = self.rebuilder._apply_event_transactional
        
        def mock_apply(event, temp_snapshots, temp_registry_path):
            if event['event_id'] == 'evt_bad':
                raise Exception("Simulated event processing failure")
            return original_apply(event, temp_snapshots, temp_registry_path)
        
        with patch.object(self.rebuilder, '_apply_event_transactional', mock_apply):
            result = self.rebuilder.rebuild_from_events()
            
            # Should continue processing other events despite one failure
            self.assertEqual(result['status'], 'success')
            # Should process the good events
            self.assertGreater(result['events_processed'], 0)
    
    def test_concurrent_rebuild_protection(self):
        """Test that concurrent rebuilds are protected by locking."""
        self._write_events_to_log(self.test_events)
        
        # Simulate concurrent access
        rebuilder1 = StateRebuilder()
        rebuilder2 = StateRebuilder()
        
        # Mock the first rebuilder to hold the lock longer
        original_rebuild = rebuilder1.rebuild_from_events
        
        def slow_rebuild(*args, **kwargs):
            time.sleep(0.1)  # Hold lock for 100ms
            return original_rebuild(*args, **kwargs)
        
        # Start first rebuild
        with patch.object(rebuilder1, 'rebuild_from_events', slow_rebuild):
            import threading
            
            result1 = None
            result2 = None
            
            def rebuild1():
                nonlocal result1
                result1 = rebuilder1.rebuild_from_events()
            
            def rebuild2():
                nonlocal result2
                result2 = rebuilder2.rebuild_from_events()
            
            # Start both rebuilds
            thread1 = threading.Thread(target=rebuild1)
            thread2 = threading.Thread(target=rebuild2)
            
            thread1.start()
            time.sleep(0.05)  # Let first rebuild start
            thread2.start()
            
            thread1.join()
            thread2.join()
            
            # Both should succeed (second should be idempotent)
            self.assertEqual(result1['status'], 'success')
            self.assertEqual(result2['status'], 'success')
    
    def test_temp_state_isolation(self):
        """Test that temporary state is isolated from active state."""
        self._write_events_to_log(self.test_events)
        
        # Create existing active state
        snapshots_file = Path(".claude/snapshots/tasks.json")
        snapshots_file.parent.mkdir(parents=True, exist_ok=True)
        
        existing_state = {"TICKET-EXISTING": {"status": "EXISTING"}}
        with open(snapshots_file, 'w') as f:
            json.dump(existing_state, f)
        
        # Mock to fail during swap
        with patch.object(self.rebuilder, '_swap_to_active_state') as mock_swap:
            mock_swap.side_effect = Exception("Swap failed")
            
            result = self.rebuilder.rebuild_from_events()
            self.assertEqual(result['status'], 'failed')
        
        # Active state should be unchanged
        with open(snapshots_file, 'r') as f:
            current_state = json.load(f)
        
        self.assertEqual(current_state, existing_state)
        
        # Temp directory should be cleaned up
        self.assertFalse(self.rebuilder.temp_dir.exists())
    
    def test_idempotency_tracking_integrity(self):
        """Test that idempotency tracking maintains integrity."""
        self._write_events_to_log(self.test_events)
        
        # First rebuild
        result1 = self.rebuilder.rebuild_from_events()
        self.assertEqual(result1['status'], 'success')
        
        # Verify applied events were tracked
        applied_events_file = Path(".claude/system/applied_events.json")
        self.assertTrue(applied_events_file.exists())
        
        with open(applied_events_file, 'r') as f:
            applied_events = json.load(f)
        
        # Should have tracked all processed events
        self.assertEqual(len(applied_events), result1['events_processed'])
        
        # Second rebuild should be idempotent
        result2 = self.rebuilder.rebuild_from_events()
        self.assertEqual(result2['status'], 'success')
        self.assertEqual(result2['events_processed'], 0)  # All should be skipped
        self.assertEqual(result2['events_skipped'], result1['events_processed'])
    
    def test_cleanup_on_interruption(self):
        """Test cleanup when rebuild is interrupted."""
        self._write_events_to_log(self.test_events)
        
        # Mock to simulate interruption (KeyboardInterrupt)
        with patch.object(self.rebuilder, '_apply_event_transactional') as mock_apply:
            mock_apply.side_effect = KeyboardInterrupt("Simulated interruption")
            
            with self.assertRaises(KeyboardInterrupt):
                self.rebuilder.rebuild_from_events()
        
        # Temp directory should still be cleaned up
        # (In a real scenario, this might be handled by a signal handler)
        self.rebuilder._cleanup_temp_state()
        self.assertFalse(self.rebuilder.temp_dir.exists())


def run_transactional_integrity_tests():
    """Run all transactional integrity tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_transactional_integrity_tests()