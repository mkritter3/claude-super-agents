#!/usr/bin/env python3
import json
import time
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional
import fcntl  # For file locking
from logger_config import get_contextual_logger

class EventLogger:
    def __init__(self, log_path: str = ".claude/events/log.ndjson"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self.logger = get_contextual_logger("event_logger", component="event_logger")
        
    def append_event(self, 
                    ticket_id: str,
                    event_type: str,
                    payload: Dict[str, Any],
                    parent_event_id: Optional[str] = None,
                    agent: Optional[str] = None) -> str:
        """Append event atomically with write-lock."""
        
        # Generate event ID
        timestamp = int(time.time() * 1000)
        self._counter += 1
        event_id = f"evt_{timestamp}_{self._counter:04d}"
        
        # Build event
        event = {
            "event_id": event_id,
            "ticket_id": ticket_id,
            "parent_event_id": parent_event_id or "",
            "timestamp": timestamp,
            "type": event_type,
            "agent": agent or "",
            "payload": payload,
            "checksum": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
            "idempotency_key": f"{ticket_id}_{event_type}_{timestamp}"
        }
        
        # Atomic append with lock
        try:
            with open(self.log_path, 'a') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(event) + '\n')
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            self.logger.debug("Event logged", extra={
                'event_id': event_id,
                'event_type': event_type,
                'ticket_id': ticket_id,
                'agent': agent
            })
            
        except Exception as e:
            self.logger.error("Failed to log event", extra={
                'event_id': event_id,
                'event_type': event_type,
                'ticket_id': ticket_id,
                'error': str(e)
            })
            raise
        
        return event_id
    
    def replay_events(self, 
                     ticket_id: Optional[str] = None,
                     from_timestamp: Optional[int] = None,
                     to_timestamp: Optional[int] = None,
                     progress_callback: Optional[callable] = None,
                     validate_checksums: bool = False) -> list:
        """
        Replay events with enhanced filtering and validation.
        
        Args:
            ticket_id: Optional ticket filter
            from_timestamp: Optional start timestamp filter
            to_timestamp: Optional end timestamp filter  
            progress_callback: Optional callback for progress reporting
            validate_checksums: Whether to validate event checksums
            
        Returns:
            List of events matching filters
        """
        events = []
        corrupted_events = []
        
        if not self.log_path.exists():
            return events
            
        # Get file size for progress tracking
        file_size = self.log_path.stat().st_size
        bytes_read = 0
        
        try:
            with open(self.log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    bytes_read += len(line.encode('utf-8'))
                    
                    try:
                        event = json.loads(line.strip())
                        
                        # Validate checksum if requested
                        if validate_checksums and not self._validate_event_checksum(event):
                            self.logger.warning("Corrupted event detected", extra={
                                'event_id': event.get('event_id', 'unknown'),
                                'line_number': line_num
                            })
                            corrupted_events.append({
                                'line_number': line_num,
                                'event_id': event.get('event_id', 'unknown'),
                                'error': 'checksum_mismatch'
                            })
                            continue
                        
                        # Apply filters
                        if ticket_id and event.get('ticket_id') != ticket_id:
                            continue
                            
                        if from_timestamp and event.get('timestamp', 0) < from_timestamp:
                            continue
                            
                        if to_timestamp and event.get('timestamp', 0) > to_timestamp:
                            continue
                        
                        events.append(event)
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning("Invalid JSON in event log", extra={
                            'line_number': line_num,
                            'error': str(e)
                        })
                        corrupted_events.append({
                            'line_number': line_num,
                            'event_id': 'unknown',
                            'error': f'json_decode_error: {e}'
                        })
                        continue
                    
                    # Report progress
                    if progress_callback and line_num % 100 == 0:
                        progress = bytes_read / file_size if file_size > 0 else 0
                        progress_callback(int(progress * 100))
                        
        except Exception as e:
            self.logger.error("Failed to replay events", extra={'error': str(e)})
            raise
        
        # Log summary
        self.logger.info("Event replay completed", extra={
            'events_loaded': len(events),
            'corrupted_events': len(corrupted_events),
            'filters_applied': {
                'ticket_id': ticket_id,
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp
            }
        })
        
        # Store corrupted events info for debugging
        if corrupted_events:
            self._log_corrupted_events(corrupted_events)
        
        return events
    
    def _validate_event_checksum(self, event: Dict[str, Any]) -> bool:
        """Validate event payload checksum."""
        try:
            if 'checksum' not in event or 'payload' not in event:
                return True  # Skip validation if no checksum
                
            payload_json = json.dumps(event['payload'], sort_keys=True)
            calculated_checksum = hashlib.sha256(payload_json.encode()).hexdigest()
            
            return event['checksum'] == calculated_checksum
            
        except Exception:
            return False
    
    def _log_corrupted_events(self, corrupted_events: list):
        """Log corrupted events to separate file for analysis."""
        try:
            corrupted_log_path = self.log_path.parent / "corrupted_events.json"
            
            existing_corrupted = []
            if corrupted_log_path.exists():
                with open(corrupted_log_path, 'r') as f:
                    existing_corrupted = json.load(f)
            
            existing_corrupted.extend(corrupted_events)
            
            with open(corrupted_log_path, 'w') as f:
                json.dump(existing_corrupted, f, indent=2)
                
            self.logger.warning("Corrupted events logged", extra={
                'corrupted_count': len(corrupted_events),
                'corrupted_log_path': str(corrupted_log_path)
            })
            
        except Exception as e:
            self.logger.error("Failed to log corrupted events", extra={'error': str(e)})
    
    def get_event_count(self, ticket_id: Optional[str] = None) -> int:
        """Get count of events, optionally filtered by ticket."""
        if not self.log_path.exists():
            return 0
            
        count = 0
        try:
            with open(self.log_path, 'r') as f:
                for line in f:
                    if ticket_id is None:
                        count += 1
                    else:
                        try:
                            event = json.loads(line.strip())
                            if event.get('ticket_id') == ticket_id:
                                count += 1
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            self.logger.error("Failed to count events", extra={'error': str(e)})
            
        return count

if __name__ == "__main__":
    # CLI interface for bash integration
    import sys
    logger = EventLogger()
    
    if len(sys.argv) < 4:
        logger = get_contextual_logger("event_logger", component="event_logger")
        logger.info("Usage: event_logger.py <ticket_id> <event_type> <payload_json>")
        sys.exit(1)
    
    event_id = logger.append_event(
        ticket_id=sys.argv[1],
        event_type=sys.argv[2],
        payload=json.loads(sys.argv[3])
    )
    logger = get_contextual_logger("event_logger", component="event_logger")
    logger.info("Event logged", extra={'event_id': event_id})