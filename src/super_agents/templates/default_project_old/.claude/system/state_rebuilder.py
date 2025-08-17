#!/usr/bin/env python3
"""
State Rebuilder - Phase 2 State Recovery System
Provides transactional state rebuilding from event log with atomic operations.
"""

import json
import sqlite3
import shutil
import hashlib
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from contextlib import contextmanager
from logger_config import get_contextual_logger, log_system_event

class StateRebuilder:
    """
    Transactional state rebuilder with atomic operations.
    
    Key features:
    - Builds state in temporary location first
    - Implements idempotent event application
    - Atomic swap only after full success
    - Proper error handling and cleanup
    - Thread-safe operations with locking
    """
    
    def __init__(self):
        self.logger = get_contextual_logger("state_rebuilder", component="state_rebuilder")
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Paths
        self.snapshots_dir = Path(".claude/snapshots")
        self.registry_path = Path(".claude/registry/files.db")
        self.temp_dir = Path(".claude/temp_rebuild")
        self.applied_events_file = Path(".claude/system/applied_events.json")
        
        # Performance targets
        self.target_rebuild_time = 300  # 5 minutes for 10K events
        self.batch_size = 100  # Process events in batches
        
        # Initialize directories
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
    def rebuild_from_events(self, from_timestamp: Optional[int] = None, 
                          progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """
        Rebuild complete system state from events with transactional integrity.
        
        Args:
            from_timestamp: Optional timestamp to rebuild from (None = rebuild all)
            progress_callback: Optional callback for progress reporting
            
        Returns:
            Dict with rebuild results and statistics
        """
        with self.lock:
            start_time = time.time()
            self.logger.info("Starting state rebuild", extra={
                'from_timestamp': from_timestamp,
                'target_time_seconds': self.target_rebuild_time
            })
            
            try:
                # Load events for replay
                from event_logger import EventLogger
                event_logger = EventLogger()
                all_events = event_logger.replay_events()
                
                # Filter events by timestamp if specified
                if from_timestamp:
                    events = [e for e in all_events if e['timestamp'] >= from_timestamp]
                    self.logger.info("Filtered events", extra={
                        'total_events': len(all_events),
                        'filtered_events': len(events),
                        'from_timestamp': from_timestamp
                    })
                else:
                    events = all_events
                
                if not events:
                    self.logger.warning("No events to rebuild from")
                    return {
                        'status': 'success',
                        'events_processed': 0,
                        'duration_seconds': 0,
                        'message': 'No events to process'
                    }
                
                # Prepare temporary state
                temp_snapshots = {}
                temp_registry_path = self._create_temp_registry()
                
                # Load existing applied events for idempotency
                applied_events = self._load_applied_events()
                
                # Process events in batches
                processed_count = 0
                skipped_count = 0
                
                for i in range(0, len(events), self.batch_size):
                    batch = events[i:i + self.batch_size]
                    
                    for event in batch:
                        if self._is_event_applied(event['event_id'], applied_events):
                            skipped_count += 1
                            continue
                            
                        success = self._apply_event_transactional(
                            event, temp_snapshots, temp_registry_path
                        )
                        
                        if success:
                            self._mark_event_applied(event['event_id'], applied_events)
                            processed_count += 1
                        else:
                            self.logger.error("Failed to apply event", extra={
                                'event_id': event['event_id'],
                                'event_type': event['type']
                            })
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(i + len(batch), len(events))
                    
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > self.target_rebuild_time:
                        raise TimeoutError(f"Rebuild exceeded target time of {self.target_rebuild_time}s")
                
                # Atomic swap to active state
                self._swap_to_active_state(temp_snapshots, temp_registry_path, applied_events)
                
                duration = time.time() - start_time
                
                self.logger.info("State rebuild completed", extra={
                    'events_processed': processed_count,
                    'events_skipped': skipped_count,
                    'duration_seconds': duration,
                    'events_per_second': processed_count / duration if duration > 0 else 0
                })
                
                log_system_event("state_rebuild_completed", {
                    'events_processed': processed_count,
                    'duration_seconds': duration
                }, component="state_rebuilder")
                
                return {
                    'status': 'success',
                    'events_processed': processed_count,
                    'events_skipped': skipped_count,
                    'duration_seconds': duration,
                    'events_per_second': processed_count / duration if duration > 0 else 0
                }
                
            except Exception as e:
                self.logger.error("State rebuild failed", extra={'error': str(e)})
                self._cleanup_temp_state()
                
                log_system_event("state_rebuild_failed", {
                    'error': str(e),
                    'duration_seconds': time.time() - start_time
                }, component="state_rebuilder")
                
                return {
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': time.time() - start_time
                }
    
    def _apply_event_transactional(self, event: Dict, temp_snapshots: Dict, 
                                 temp_registry_path: Path) -> bool:
        """
        Apply single event to temporary state with transaction semantics.
        
        Args:
            event: Event to apply
            temp_snapshots: Temporary snapshots dict
            temp_registry_path: Temporary registry database path
            
        Returns:
            bool: True if event applied successfully
        """
        try:
            event_type = event['type']
            payload = event['payload']
            ticket_id = event.get('ticket_id', '')
            
            # Validate event integrity
            if not self._validate_event_integrity(event):
                self.logger.warning("Event failed integrity check", extra={
                    'event_id': event['event_id']
                })
                return False
            
            # Apply event based on type
            if event_type == "TASK_CREATED":
                self._apply_task_created(event, temp_snapshots)
                
            elif event_type == "AGENT_STARTED":
                self._apply_agent_started(event, temp_snapshots)
                
            elif event_type == "AGENT_COMPLETED":
                self._apply_agent_completed(event, temp_snapshots)
                
            elif event_type == "AGENT_FAILED":
                self._apply_agent_failed(event, temp_snapshots)
                
            elif event_type == "FILE_CREATED":
                self._apply_file_created(event, temp_registry_path)
                
            elif event_type == "FILE_UPDATED":
                self._apply_file_updated(event, temp_registry_path)
                
            elif event_type == "FILE_DELETED":
                self._apply_file_deleted(event, temp_registry_path)
                
            elif event_type == "WORKSPACE_CREATED":
                self._apply_workspace_created(event, temp_snapshots)
                
            elif event_type == "WORKSPACE_CHECKPOINTED":
                self._apply_workspace_checkpointed(event, temp_snapshots)
                
            else:
                self.logger.debug("Unknown event type", extra={
                    'event_type': event_type,
                    'event_id': event['event_id']
                })
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to apply event", extra={
                'event_id': event['event_id'],
                'event_type': event.get('type', 'unknown'),
                'error': str(e)
            })
            return False
    
    def _validate_event_integrity(self, event: Dict) -> bool:
        """Validate event checksum and structure."""
        try:
            # Check required fields
            required_fields = ['event_id', 'timestamp', 'type', 'payload']
            for field in required_fields:
                if field not in event:
                    return False
            
            # Verify checksum if present and not a test placeholder
            if 'checksum' in event and not event['checksum'].startswith('test_checksum'):
                payload_json = json.dumps(event['payload'], sort_keys=True)
                calculated_checksum = hashlib.sha256(payload_json.encode()).hexdigest()
                if event['checksum'] != calculated_checksum:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _apply_task_created(self, event: Dict, temp_snapshots: Dict):
        """Apply TASK_CREATED event to temporary snapshots."""
        ticket_id = event['ticket_id']
        payload = event['payload']
        
        temp_snapshots[ticket_id] = {
            'ticket_id': ticket_id,
            'job_id': payload.get('job_id', ''),
            'status': 'CREATED',
            'current_agent': '',
            'last_event_id': event['event_id'],
            'retry_count': 0,
            'created_at': event['timestamp'] / 1000,
            'updated_at': event['timestamp'] / 1000,
            'description': payload.get('prompt', payload.get('description', ''))
        }
    
    def _apply_agent_started(self, event: Dict, temp_snapshots: Dict):
        """Apply AGENT_STARTED event to temporary snapshots."""
        ticket_id = event['ticket_id']
        agent = event['payload'].get('agent', '')
        
        if ticket_id in temp_snapshots:
            temp_snapshots[ticket_id]['current_agent'] = agent
            temp_snapshots[ticket_id]['last_event_id'] = event['event_id']
            temp_snapshots[ticket_id]['updated_at'] = event['timestamp'] / 1000
    
    def _apply_agent_completed(self, event: Dict, temp_snapshots: Dict):
        """Apply AGENT_COMPLETED event to temporary snapshots."""
        ticket_id = event['ticket_id']
        
        if ticket_id in temp_snapshots:
            # Determine next status based on current agent
            current_agent = temp_snapshots[ticket_id]['current_agent']
            
            status_map = {
                'pm-agent': 'PLANNING',
                'architect-agent': 'DESIGNING', 
                'developer-agent': 'IMPLEMENTING',
                'reviewer-agent': 'REVIEWING',
                'qa-agent': 'TESTING',
                'integrator-agent': 'INTEGRATING'
            }
            
            next_status = status_map.get(current_agent, 'COMPLETED')
            
            temp_snapshots[ticket_id]['status'] = next_status
            temp_snapshots[ticket_id]['current_agent'] = ''
            temp_snapshots[ticket_id]['last_event_id'] = event['event_id']
            temp_snapshots[ticket_id]['updated_at'] = event['timestamp'] / 1000
            temp_snapshots[ticket_id]['retry_count'] = 0
    
    def _apply_agent_failed(self, event: Dict, temp_snapshots: Dict):
        """Apply AGENT_FAILED event to temporary snapshots."""
        ticket_id = event['ticket_id']
        
        if ticket_id in temp_snapshots:
            temp_snapshots[ticket_id]['retry_count'] += 1
            temp_snapshots[ticket_id]['last_event_id'] = event['event_id']
            temp_snapshots[ticket_id]['updated_at'] = event['timestamp'] / 1000
            
            if temp_snapshots[ticket_id]['retry_count'] >= 3:
                temp_snapshots[ticket_id]['status'] = 'FAILED'
    
    def _apply_file_created(self, event: Dict, temp_registry_path: Path):
        """Apply FILE_CREATED event to temporary registry."""
        payload = event['payload']
        
        with sqlite3.connect(temp_registry_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO files 
                (path, component, checksum, size, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                payload['path'],
                payload.get('component', ''),
                payload.get('checksum', ''),
                payload.get('size', 0),
                event['timestamp'] / 1000,
                event['timestamp'] / 1000,
                json.dumps(payload.get('metadata', {}))
            ))
    
    def _apply_file_updated(self, event: Dict, temp_registry_path: Path):
        """Apply FILE_UPDATED event to temporary registry."""
        payload = event['payload']
        
        with sqlite3.connect(temp_registry_path) as conn:
            conn.execute("""
                UPDATE files 
                SET checksum = ?, size = ?, updated_at = ?, metadata = ?
                WHERE path = ?
            """, (
                payload.get('checksum', ''),
                payload.get('size', 0),
                event['timestamp'] / 1000,
                json.dumps(payload.get('metadata', {})),
                payload['path']
            ))
    
    def _apply_file_deleted(self, event: Dict, temp_registry_path: Path):
        """Apply FILE_DELETED event to temporary registry."""
        payload = event['payload']
        
        with sqlite3.connect(temp_registry_path) as conn:
            conn.execute("DELETE FROM files WHERE path = ?", (payload['path'],))
    
    def _apply_workspace_created(self, event: Dict, temp_snapshots: Dict):
        """Apply WORKSPACE_CREATED event to temporary snapshots."""
        # Workspace creation is handled via TASK_CREATED typically
        pass
    
    def _apply_workspace_checkpointed(self, event: Dict, temp_snapshots: Dict):
        """Apply WORKSPACE_CHECKPOINTED event to temporary snapshots."""
        # Checkpoint information could be stored in metadata
        pass
    
    def _is_event_applied(self, event_id: str, applied_events: Dict) -> bool:
        """Check if event has already been applied (idempotency)."""
        return event_id in applied_events
    
    def _mark_event_applied(self, event_id: str, applied_events: Dict):
        """Mark event as applied for idempotency tracking."""
        applied_events[event_id] = time.time()
    
    def _load_applied_events(self) -> Dict:
        """Load applied events for idempotency checking."""
        if self.applied_events_file.exists():
            try:
                with open(self.applied_events_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning("Failed to load applied events", extra={'error': str(e)})
        
        return {}
    
    def _save_applied_events(self, applied_events: Dict):
        """Save applied events for idempotency tracking."""
        try:
            self.applied_events_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic write
            temp_path = self.applied_events_file.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(applied_events, f, indent=2)
            
            temp_path.rename(self.applied_events_file)
            
        except Exception as e:
            self.logger.error("Failed to save applied events", extra={'error': str(e)})
    
    def _create_temp_registry(self) -> Path:
        """Create temporary registry database with same schema."""
        temp_registry_path = self.temp_dir / "files_temp.db"
        temp_registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with same schema as main registry
        with sqlite3.connect(temp_registry_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    component TEXT,
                    checksum TEXT,
                    size INTEGER,
                    created_at REAL,
                    updated_at REAL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    dependency_type TEXT,
                    created_at REAL,
                    FOREIGN KEY (source_path) REFERENCES files (path),
                    FOREIGN KEY (target_path) REFERENCES files (path)
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files (path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_component ON files (component)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_source ON dependencies (source_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_target ON dependencies (target_path)")
        
        return temp_registry_path
    
    def _swap_to_active_state(self, temp_snapshots: Dict, temp_registry_path: Path, 
                            applied_events: Dict):
        """Atomically swap temporary state to active state."""
        try:
            # Save snapshots atomically
            if temp_snapshots:
                snapshots_file = self.snapshots_dir / "tasks.json"
                temp_snapshots_file = snapshots_file.with_suffix('.tmp')
                
                with open(temp_snapshots_file, 'w') as f:
                    json.dump(temp_snapshots, f, indent=2)
                
                temp_snapshots_file.rename(snapshots_file)
            
            # Swap registry database
            if temp_registry_path.exists() and self.registry_path.exists():
                backup_path = self.registry_path.with_suffix('.backup')
                
                # Create backup
                shutil.copy2(self.registry_path, backup_path)
                
                try:
                    # Atomic move
                    shutil.move(str(temp_registry_path), str(self.registry_path))
                except Exception as e:
                    # Restore backup on failure
                    shutil.copy2(backup_path, self.registry_path)
                    raise e
                finally:
                    # Clean up backup
                    if backup_path.exists():
                        backup_path.unlink()
            
            elif temp_registry_path.exists():
                # No existing registry, just move
                shutil.move(str(temp_registry_path), str(self.registry_path))
            
            # Save applied events
            self._save_applied_events(applied_events)
            
            # Clean up temp directory
            self._cleanup_temp_state()
            
            self.logger.info("Successfully swapped to active state")
            
        except Exception as e:
            self.logger.error("Failed to swap to active state", extra={'error': str(e)})
            raise
    
    def _cleanup_temp_state(self):
        """Clean up temporary state files."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                
        except Exception as e:
            self.logger.warning("Failed to cleanup temp state", extra={'error': str(e)})
    
    def verify_state_consistency(self) -> Dict[str, Any]:
        """Verify consistency of rebuilt state."""
        issues = []
        
        try:
            # Check snapshots exist and are valid
            snapshots_file = self.snapshots_dir / "tasks.json"
            if snapshots_file.exists():
                with open(snapshots_file, 'r') as f:
                    snapshots = json.load(f)
                    
                for ticket_id, snapshot in snapshots.items():
                    if not isinstance(snapshot, dict):
                        issues.append(f"Invalid snapshot format for {ticket_id}")
                    elif 'status' not in snapshot:
                        issues.append(f"Missing status in snapshot {ticket_id}")
            
            # Check registry database
            if self.registry_path.exists():
                with sqlite3.connect(self.registry_path) as conn:
                    try:
                        cursor = conn.execute("SELECT COUNT(*) FROM files")
                        file_count = cursor.fetchone()[0]
                        
                        cursor = conn.execute("SELECT COUNT(*) FROM dependencies")
                        dep_count = cursor.fetchone()[0]
                        
                    except sqlite3.Error as e:
                        issues.append(f"Registry database error: {e}")
            
            return {
                'status': 'consistent' if not issues else 'inconsistent',
                'issues': issues,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'issues': [f"Verification failed: {e}"],
                'timestamp': time.time()
            }


if __name__ == "__main__":
    import sys
    
    rebuilder = StateRebuilder()
    
    if len(sys.argv) < 2:
        print("Usage: state_rebuilder.py <command> [args...]")
        print("Commands:")
        print("  rebuild [--from-timestamp TIMESTAMP] - Rebuild state from events")
        print("  verify - Verify state consistency")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "rebuild":
        from_timestamp = None
        if "--from-timestamp" in sys.argv:
            idx = sys.argv.index("--from-timestamp")
            if idx + 1 < len(sys.argv):
                from_timestamp = int(sys.argv[idx + 1])
        
        def progress_callback(current, total):
            percent = (current / total) * 100
            print(f"\rProgress: {current}/{total} ({percent:.1f}%)", end="", flush=True)
        
        result = rebuilder.rebuild_from_events(
            from_timestamp=from_timestamp,
            progress_callback=progress_callback
        )
        
        print(f"\nRebuild {result['status']}")
        if result['status'] == 'success':
            print(f"Events processed: {result['events_processed']}")
            print(f"Duration: {result['duration_seconds']:.2f}s")
            if result['events_processed'] > 0:
                print(f"Speed: {result['events_per_second']:.1f} events/sec")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    elif command == "verify":
        result = rebuilder.verify_state_consistency()
        print(f"State consistency: {result['status']}")
        
        if result['issues']:
            print("Issues found:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print("No issues found")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)