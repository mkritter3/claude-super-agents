#!/usr/bin/env python3
"""
Test suite for StateRebuilder - Phase 2 State Recovery System
Tests core rebuilder functionality including transactional integrity.
"""

import json
import time
import shutil
import sqlite3
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from state_rebuilder import StateRebuilder
from event_logger import EventLogger


class TestStateRebuilder(unittest.TestCase):
    """Test StateRebuilder functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path("/tmp/aet_test_phase2")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Change to test directory
        self.original_cwd = Path.cwd()
        import os
        os.chdir(self.test_dir)
        
        # Initialize test components
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
        """Create sample events for testing."""
        base_time = int(time.time() * 1000)
        
        events = [
            {
                "event_id": "evt_001",
                "ticket_id": "TICKET-001",
                "timestamp": base_time,
                "type": "TASK_CREATED",
                "payload": {
                    "job_id": "job_001", 
                    "prompt": "Test task",
                    "description": "Test task description"
                },
                "checksum": "test_checksum_001"
            },
            {
                "event_id": "evt_002", 
                "ticket_id": "TICKET-001",
                "timestamp": base_time + 1000,
                "type": "AGENT_STARTED",
                "payload": {"agent": "pm-agent"},
                "checksum": "test_checksum_002"
            },
            {
                "event_id": "evt_003",
                "ticket_id": "TICKET-001", 
                "timestamp": base_time + 2000,
                "type": "AGENT_COMPLETED",
                "payload": {"agent": "pm-agent", "output": "Planning completed"},
                "checksum": "test_checksum_003"
            },
            {
                "event_id": "evt_004",
                "ticket_id": "TICKET-002",
                "timestamp": base_time + 3000,
                "type": "TASK_CREATED",
                "payload": {
                    "job_id": "job_002",
                    "prompt": "Second test task",
                    "description": "Second test task description"
                },
                "checksum": "test_checksum_004"
            },
            {
                "event_id": "evt_005",
                "ticket_id": "TICKET-001",
                "timestamp": base_time + 4000,
                "type": "FILE_CREATED",
                "payload": {
                    "path": "src/test.py",
                    "component": "test_component",
                    "checksum": "file_checksum_001",
                    "size": 1024
                },
                "checksum": "test_checksum_005"
            }
        ]
        
        return events
    
    def _write_test_events_to_log(self, events):
        """Write test events to event log."""
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
    
    def test_rebuild_from_events_success(self):
        """Test successful state rebuild from events."""
        # Write test events
        self._write_test_events_to_log(self.test_events)
        
        # Rebuild state
        result = self.rebuilder.rebuild_from_events()
        
        # Verify success
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['events_processed'], len(self.test_events))
        self.assertGreater(result['events_per_second'], 0)
        
        # Verify snapshots were created
        snapshots_file = Path(".claude/snapshots/tasks.json")
        self.assertTrue(snapshots_file.exists())
        
        with open(snapshots_file, 'r') as f:
            snapshots = json.load(f)
        
        # Should have 2 tasks
        self.assertEqual(len(snapshots), 2)
        self.assertIn("TICKET-001", snapshots)
        self.assertIn("TICKET-002", snapshots)
        
        # Verify task 1 progressed through PM agent
        task1 = snapshots["TICKET-001"]
        self.assertEqual(task1['status'], 'PLANNING')
        self.assertEqual(task1['retry_count'], 0)
        
        # Verify task 2 is still created
        task2 = snapshots["TICKET-002"]
        self.assertEqual(task2['status'], 'CREATED')
    
    def test_rebuild_with_timestamp_filter(self):
        """Test rebuild with timestamp filtering."""
        # Write test events
        self._write_test_events_to_log(self.test_events)
        
        # Rebuild from middle timestamp (should skip first 2 events)
        from_timestamp = self.test_events[2]['timestamp']
        result = self.rebuilder.rebuild_from_events(from_timestamp=from_timestamp)
        
        # Should process only last 3 events
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['events_processed'], 3)
    
    def test_idempotent_event_application(self):
        """Test that applying events multiple times has no additional effect."""
        # Write test events
        self._write_test_events_to_log(self.test_events)
        
        # First rebuild
        result1 = self.rebuilder.rebuild_from_events()
        self.assertEqual(result1['status'], 'success')
        
        # Get snapshots after first rebuild
        with open(Path(".claude/snapshots/tasks.json"), 'r') as f:
            snapshots1 = json.load(f)
        
        # Second rebuild (should be idempotent)
        result2 = self.rebuilder.rebuild_from_events()
        self.assertEqual(result2['status'], 'success')
        self.assertEqual(result2['events_skipped'], len(self.test_events))
        self.assertEqual(result2['events_processed'], 0)
        
        # Snapshots should be identical
        with open(Path(".claude/snapshots/tasks.json"), 'r') as f:
            snapshots2 = json.load(f)
        
        self.assertEqual(snapshots1, snapshots2)
    
    def test_corrupted_event_handling(self):
        """Test handling of corrupted events."""
        # Create events with one corrupted
        events = self.test_events[:2]  # Good events
        corrupted_event = {"invalid": "json structure"}  # Missing required fields
        
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
            # Write corrupted JSON
            f.write('{"invalid": json}\n')  # Invalid JSON
            f.write(json.dumps(corrupted_event) + '\n')  # Missing fields
        
        # Rebuild should handle corrupted events gracefully
        result = self.rebuilder.rebuild_from_events()
        
        # Should process good events and skip corrupted ones
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['events_processed'], 2)
    
    def test_transactional_rollback_on_failure(self):
        """Test transaction rollback when rebuild fails."""
        # Write test events
        self._write_test_events_to_log(self.test_events)
        
        # Mock a failure during state swap
        with patch.object(self.rebuilder, '_swap_to_active_state') as mock_swap:
            mock_swap.side_effect = Exception("Simulated swap failure")
            
            result = self.rebuilder.rebuild_from_events()
            
            # Should fail and cleanup temp state
            self.assertEqual(result['status'], 'failed')
            self.assertIn("Simulated swap failure", result['error'])
            
            # Temp directory should be cleaned up
            self.assertFalse(self.rebuilder.temp_dir.exists())
    
    def test_performance_benchmark(self):
        """Test rebuild performance with larger dataset."""
        # Create 1000 test events (smaller than 10K for unit test speed)
        large_events = []
        base_time = int(time.time() * 1000)
        
        for i in range(1000):
            event = {
                "event_id": f"evt_{i:04d}",
                "ticket_id": f"TICKET-{i % 10}",  # 10 different tickets
                "timestamp": base_time + i * 1000,
                "type": "TASK_CREATED" if i % 5 == 0 else "AGENT_STARTED",
                "payload": {"test": f"data_{i}"},
                "checksum": f"checksum_{i}"
            }
            large_events.append(event)
        
        # Write events
        self._write_test_events_to_log(large_events)
        
        # Benchmark rebuild
        start_time = time.time()
        result = self.rebuilder.rebuild_from_events()
        duration = time.time() - start_time
        
        # Verify performance
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['events_processed'], 1000)
        
        # Should process events quickly (target: >100 events/sec for small dataset)
        events_per_second = result['events_per_second']
        self.assertGreater(events_per_second, 100, 
                          f"Performance too slow: {events_per_second:.1f} events/sec")
        
        print(f"Performance: {events_per_second:.1f} events/sec for 1000 events")
    
    def test_file_registry_rebuild(self):
        """Test rebuilding file registry from events."""
        # Create file events
        file_events = [
            {
                "event_id": "evt_file_001",
                "ticket_id": "TICKET-FILE",
                "timestamp": int(time.time() * 1000),
                "type": "FILE_CREATED",
                "payload": {
                    "path": "src/test1.py",
                    "component": "test_comp",
                    "checksum": "abc123",
                    "size": 1024,
                    "metadata": {"author": "test"}
                },
                "checksum": "test_checksum_file_001"
            },
            {
                "event_id": "evt_file_002", 
                "ticket_id": "TICKET-FILE",
                "timestamp": int(time.time() * 1000) + 1000,
                "type": "FILE_UPDATED",
                "payload": {
                    "path": "src/test1.py",
                    "checksum": "def456",
                    "size": 2048,
                    "metadata": {"author": "test", "version": 2}
                },
                "checksum": "test_checksum_file_002"
            }
        ]
        
        # Write events
        self._write_test_events_to_log(file_events)
        
        # Rebuild
        result = self.rebuilder.rebuild_from_events()
        self.assertEqual(result['status'], 'success')
        
        # Verify registry database
        registry_path = Path(".claude/registry/files.db")
        self.assertTrue(registry_path.exists())
        
        with sqlite3.connect(registry_path) as conn:
            cursor = conn.execute("SELECT * FROM files WHERE path = ?", ("src/test1.py",))
            file_record = cursor.fetchone()
            
            self.assertIsNotNone(file_record)
            # Should have updated checksum and size
            self.assertIn("def456", file_record)  # Updated checksum
            self.assertIn(2048, file_record)      # Updated size
    
    def test_verify_state_consistency(self):
        """Test state consistency verification."""
        # Write test events and rebuild
        self._write_test_events_to_log(self.test_events)
        self.rebuilder.rebuild_from_events()
        
        # Verify consistency
        result = self.rebuilder.verify_state_consistency()
        
        self.assertEqual(result['status'], 'consistent')
        self.assertEqual(len(result['issues']), 0)
    
    def test_verify_state_with_corruption(self):
        """Test state verification with corrupted state."""
        # Write test events and rebuild
        self._write_test_events_to_log(self.test_events)
        self.rebuilder.rebuild_from_events()
        
        # Corrupt snapshots file
        snapshots_file = Path(".claude/snapshots/tasks.json")
        with open(snapshots_file, 'w') as f:
            f.write('{"invalid": json}')  # Invalid JSON
        
        # Verify should detect corruption
        result = self.rebuilder.verify_state_consistency()
        
        self.assertEqual(result['status'], 'error')
        self.assertGreater(len(result['issues']), 0)


def run_state_rebuilder_tests():
    """Run all state rebuilder tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_state_rebuilder_tests()