#!/usr/bin/env python3
"""
Test suite for Event Replay Enhancements - Phase 2
Tests enhanced event replay functionality with filtering and validation.
"""

import json
import time
import shutil
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from event_logger import EventLogger


class TestEventReplay(unittest.TestCase):
    """Test enhanced event replay functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path("/tmp/aet_test_event_replay")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Change to test directory
        self.original_cwd = Path.cwd()
        import os
        os.chdir(self.test_dir)
        
        # Initialize event logger
        self.event_logger = EventLogger()
        
        # Create test events with proper checksums
        self.test_events = self._create_test_events()
        
    def tearDown(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_events(self):
        """Create sample events with proper checksums for testing."""
        base_time = int(time.time() * 1000)
        
        events = []
        
        for i in range(10):
            payload = {
                "test_data": f"data_{i}",
                "index": i,
                "timestamp": base_time + i * 1000
            }
            
            # Calculate proper checksum
            payload_json = json.dumps(payload, sort_keys=True)
            checksum = hashlib.sha256(payload_json.encode()).hexdigest()
            
            event = {
                "event_id": f"evt_{i:03d}",
                "ticket_id": f"TICKET-{i % 3}",  # 3 different tickets
                "timestamp": base_time + i * 1000,
                "type": "TEST_EVENT",
                "payload": payload,
                "checksum": checksum
            }
            events.append(event)
        
        return events
    
    def _write_events_to_log(self, events):
        """Write events to log file."""
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
    
    def test_basic_replay(self):
        """Test basic event replay functionality."""
        self._write_events_to_log(self.test_events)
        
        events = self.event_logger.replay_events()
        
        self.assertEqual(len(events), len(self.test_events))
        self.assertEqual(events[0]['event_id'], 'evt_000')
        self.assertEqual(events[-1]['event_id'], 'evt_009')
    
    def test_replay_with_ticket_filter(self):
        """Test replay with ticket ID filtering."""
        self._write_events_to_log(self.test_events)
        
        # Filter by TICKET-0 (should get events 0, 3, 6, 9)
        events = self.event_logger.replay_events(ticket_id="TICKET-0")
        
        self.assertEqual(len(events), 4)
        for event in events:
            self.assertEqual(event['ticket_id'], 'TICKET-0')
        
        # Check specific event IDs
        event_ids = [e['event_id'] for e in events]
        self.assertIn('evt_000', event_ids)
        self.assertIn('evt_003', event_ids)
        self.assertIn('evt_006', event_ids)
        self.assertIn('evt_009', event_ids)
    
    def test_replay_with_timestamp_filter(self):
        """Test replay with timestamp filtering."""
        self._write_events_to_log(self.test_events)
        
        base_time = self.test_events[0]['timestamp']
        
        # Filter from timestamp 5000ms after start (should get events 5-9)
        from_timestamp = base_time + 5000
        events = self.event_logger.replay_events(from_timestamp=from_timestamp)
        
        self.assertEqual(len(events), 5)
        for event in events:
            self.assertGreaterEqual(event['timestamp'], from_timestamp)
        
        # Filter to timestamp 7000ms after start (should get events 0-7)
        to_timestamp = base_time + 7000
        events = self.event_logger.replay_events(to_timestamp=to_timestamp)
        
        self.assertEqual(len(events), 8)
        for event in events:
            self.assertLessEqual(event['timestamp'], to_timestamp)
    
    def test_replay_with_timestamp_range(self):
        """Test replay with both from and to timestamp filters."""
        self._write_events_to_log(self.test_events)
        
        base_time = self.test_events[0]['timestamp']
        
        # Filter range from 2000ms to 6000ms (should get events 2, 3, 4, 5, 6)
        from_timestamp = base_time + 2000
        to_timestamp = base_time + 6000
        
        events = self.event_logger.replay_events(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp
        )
        
        self.assertEqual(len(events), 5)
        
        for event in events:
            self.assertGreaterEqual(event['timestamp'], from_timestamp)
            self.assertLessEqual(event['timestamp'], to_timestamp)
    
    def test_replay_with_progress_callback(self):
        """Test replay with progress reporting."""
        self._write_events_to_log(self.test_events)
        
        progress_reports = []
        
        def progress_callback(percent):
            progress_reports.append(percent)
        
        events = self.event_logger.replay_events(
            progress_callback=progress_callback
        )
        
        self.assertEqual(len(events), len(self.test_events))
        # Should have received some progress reports
        self.assertGreater(len(progress_reports), 0)
    
    def test_replay_with_checksum_validation(self):
        """Test replay with checksum validation."""
        # Create events with both valid and invalid checksums
        valid_events = self.test_events[:5]
        
        # Create invalid checksum event
        invalid_event = self.test_events[5].copy()
        invalid_event['checksum'] = 'invalid_checksum_123'
        
        mixed_events = valid_events + [invalid_event] + self.test_events[6:]
        
        self._write_events_to_log(mixed_events)
        
        # Replay with checksum validation
        events = self.event_logger.replay_events(validate_checksums=True)
        
        # Should get all events except the one with invalid checksum
        self.assertEqual(len(events), len(mixed_events) - 1)
        
        # Invalid event should not be in results
        event_ids = [e['event_id'] for e in events]
        self.assertNotIn('evt_005', event_ids)
        
        # Check that corrupted events log was created
        corrupted_log = Path(".claude/events/corrupted_events.json")
        self.assertTrue(corrupted_log.exists())
        
        with open(corrupted_log, 'r') as f:
            corrupted_data = json.load(f)
        
        self.assertEqual(len(corrupted_data), 1)
        self.assertEqual(corrupted_data[0]['event_id'], 'evt_005')
        self.assertEqual(corrupted_data[0]['error'], 'checksum_mismatch')
    
    def test_replay_with_json_corruption(self):
        """Test replay handling of JSON corruption."""
        # Write some good events and some corrupted JSON
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            # Good events
            for event in self.test_events[:3]:
                f.write(json.dumps(event) + '\n')
            
            # Corrupted JSON lines
            f.write('{"invalid": json}\n')  # Invalid JSON
            f.write('incomplete line without\n')  # Incomplete
            
            # More good events
            for event in self.test_events[3:6]:
                f.write(json.dumps(event) + '\n')
        
        # Replay should handle corruption gracefully
        events = self.event_logger.replay_events()
        
        # Should get only the valid events
        self.assertEqual(len(events), 6)
        
        # Check corrupted events were logged
        corrupted_log = Path(".claude/events/corrupted_events.json")
        self.assertTrue(corrupted_log.exists())
        
        with open(corrupted_log, 'r') as f:
            corrupted_data = json.load(f)
        
        # Should have 2 corrupted entries
        self.assertEqual(len(corrupted_data), 2)
        
        for corrupted in corrupted_data:
            self.assertIn('json_decode_error', corrupted['error'])
    
    def test_replay_combined_filters(self):
        """Test replay with multiple filters combined."""
        self._write_events_to_log(self.test_events)
        
        base_time = self.test_events[0]['timestamp']
        
        # Filter by ticket and timestamp range
        events = self.event_logger.replay_events(
            ticket_id="TICKET-1",
            from_timestamp=base_time + 2000,
            to_timestamp=base_time + 8000
        )
        
        # Should get TICKET-1 events in timestamp range (events 1, 4, 7)
        expected_event_ids = ['evt_001', 'evt_004', 'evt_007']
        
        self.assertEqual(len(events), 3)
        
        for event in events:
            self.assertEqual(event['ticket_id'], 'TICKET-1')
            self.assertIn(event['event_id'], expected_event_ids)
            self.assertGreaterEqual(event['timestamp'], base_time + 2000)
            self.assertLessEqual(event['timestamp'], base_time + 8000)
    
    def test_replay_empty_log(self):
        """Test replay with empty log file."""
        # Create empty log file
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch()
        
        events = self.event_logger.replay_events()
        self.assertEqual(len(events), 0)
    
    def test_replay_nonexistent_log(self):
        """Test replay when log file doesn't exist."""
        events = self.event_logger.replay_events()
        self.assertEqual(len(events), 0)
    
    def test_get_event_count(self):
        """Test event counting functionality."""
        self._write_events_to_log(self.test_events)
        
        # Total count
        total_count = self.event_logger.get_event_count()
        self.assertEqual(total_count, len(self.test_events))
        
        # Count by ticket
        ticket_0_count = self.event_logger.get_event_count(ticket_id="TICKET-0")
        self.assertEqual(ticket_0_count, 4)  # Events 0, 3, 6, 9
        
        ticket_1_count = self.event_logger.get_event_count(ticket_id="TICKET-1") 
        self.assertEqual(ticket_1_count, 3)  # Events 1, 4, 7
        
        ticket_2_count = self.event_logger.get_event_count(ticket_id="TICKET-2")
        self.assertEqual(ticket_2_count, 3)  # Events 2, 5, 8
    
    def test_get_event_count_with_corruption(self):
        """Test event counting with corrupted events."""
        # Write mixed good/bad events
        log_path = Path(".claude/events/log.ndjson")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'w') as f:
            # Good events
            for event in self.test_events[:5]:
                f.write(json.dumps(event) + '\n')
            
            # Bad JSON
            f.write('{"invalid": json}\n')
            
            # More good events
            for event in self.test_events[5:]:
                f.write(json.dumps(event) + '\n')
        
        # Count should skip corrupted events
        total_count = self.event_logger.get_event_count()
        self.assertEqual(total_count, len(self.test_events))  # Should count only valid events
    
    def test_validate_event_checksum_method(self):
        """Test the checksum validation method directly."""
        # Valid event
        valid_event = self.test_events[0]
        self.assertTrue(self.event_logger._validate_event_checksum(valid_event))
        
        # Invalid checksum
        invalid_event = valid_event.copy()
        invalid_event['checksum'] = 'wrong_checksum'
        self.assertFalse(self.event_logger._validate_event_checksum(invalid_event))
        
        # Missing checksum (should return True - skip validation)
        no_checksum_event = {
            'event_id': 'test',
            'payload': {'test': 'data'}
        }
        self.assertTrue(self.event_logger._validate_event_checksum(no_checksum_event))
        
        # Missing payload
        no_payload_event = {
            'event_id': 'test',
            'checksum': 'some_checksum'
        }
        self.assertTrue(self.event_logger._validate_event_checksum(no_payload_event))


def run_event_replay_tests():
    """Run all event replay tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_event_replay_tests()