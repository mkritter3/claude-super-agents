#!/usr/bin/env python3
"""
AET Atomic Operations System
Implements atomic file writes and event log rotation
Part of Phase 1.6: Autonomous Core Hardening
"""

import os
import json
import hashlib
import tempfile
import shutil
import fcntl
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import gzip
import logging
from contextlib import contextmanager

class AtomicFileOperations:
    """Provides atomic file operations for AET system reliability"""
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.events_dir = self.claude_dir / "events"
        self.triggers_dir = self.claude_dir / "triggers"
        self.state_dir = self.claude_dir / "state"
        self.archives_dir = self.claude_dir / "archives"
        
        # Ensure directories exist
        for dir_path in [self.events_dir, self.triggers_dir, self.state_dir, self.archives_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Setup logging
        self.logger = self._setup_logger()
        
        # Event log settings
        self.max_event_log_size = 100 * 1024 * 1024  # 100MB
        self.max_event_log_age = timedelta(days=30)
        self.event_log_path = self.events_dir / "log.ndjson"
        
    def _setup_logger(self) -> logging.Logger:
        """Setup atomic operations logger"""
        logger = logging.getLogger("AET_AtomicOps")
        logger.setLevel(logging.INFO)
        
        logs_dir = self.claude_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(logs_dir / "atomic_operations.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    @contextmanager
    def file_lock(self, path: Path, exclusive: bool = True):
        """Context manager for file locking"""
        lock_path = path.with_suffix(path.suffix + '.lock')
        lock_file = open(lock_path, 'w')
        
        try:
            # Acquire lock
            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(lock_file.fileno(), lock_type)
            yield
        finally:
            # Release lock
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            # Clean up lock file
            try:
                lock_path.unlink()
            except:
                pass
                
    def atomic_write_json(self, path: Path, data: Dict[str, Any], 
                         include_checksum: bool = True) -> bool:
        """Write JSON file atomically with optional checksum"""
        try:
            # Add metadata
            if include_checksum:
                data_copy = data.copy()
                data_copy['_metadata'] = {
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0'
                }
                
                # Calculate checksum of data (excluding metadata)
                data_str = json.dumps(data, sort_keys=True)
                checksum = hashlib.sha256(data_str.encode()).hexdigest()
                data_copy['_metadata']['checksum'] = checksum
            else:
                data_copy = data
                
            # Write to temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=path.parent,
                prefix='.tmp_',
                suffix=path.suffix
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(data_copy, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                    
                # Atomic rename
                Path(temp_path).replace(path)
                self.logger.info(f"Atomically wrote {path.name}")
                return True
                
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to atomically write {path}: {e}")
            return False
            
    def atomic_write_text(self, path: Path, content: str) -> bool:
        """Write text file atomically"""
        try:
            # Write to temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=path.parent,
                prefix='.tmp_',
                suffix=path.suffix
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                    
                # Atomic rename
                Path(temp_path).replace(path)
                self.logger.info(f"Atomically wrote {path.name}")
                return True
                
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to atomically write {path}: {e}")
            return False
            
    def append_event(self, event: Dict[str, Any]) -> bool:
        """Append event to log with file locking"""
        try:
            # Add timestamp if not present
            if 'timestamp' not in event:
                event['timestamp'] = datetime.now().isoformat()
                
            # Use file locking for concurrent access
            with self.file_lock(self.event_log_path):
                with open(self.event_log_path, 'a') as f:
                    json.dump(event, f)
                    f.write('\n')
                    f.flush()
                    os.fsync(f.fileno())
                    
            # Check if rotation needed
            self._check_and_rotate_event_log()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to append event: {e}")
            return False
            
    def _check_and_rotate_event_log(self):
        """Check and rotate event log if needed"""
        try:
            if not self.event_log_path.exists():
                return
                
            # Check size
            size = self.event_log_path.stat().st_size
            if size > self.max_event_log_size:
                self._rotate_event_log("size_limit")
                return
                
            # Check age (based on first line)
            with open(self.event_log_path, 'r') as f:
                first_line = f.readline().strip()
                if first_line:
                    try:
                        first_event = json.loads(first_line)
                        timestamp_str = first_event.get('timestamp', '')
                        if timestamp_str:
                            first_time = datetime.fromisoformat(timestamp_str)
                            if datetime.now() - first_time > self.max_event_log_age:
                                self._rotate_event_log("age_limit")
                    except:
                        pass
                        
        except Exception as e:
            self.logger.error(f"Failed to check event log rotation: {e}")
            
    def _rotate_event_log(self, reason: str):
        """Rotate the event log"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"log_{timestamp}_{reason}.ndjson.gz"
            archive_path = self.archives_dir / archive_name
            
            # Compress and archive
            with self.file_lock(self.event_log_path):
                with open(self.event_log_path, 'rb') as f_in:
                    with gzip.open(archive_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                        
                # Clear the current log
                open(self.event_log_path, 'w').close()
                
            self.logger.info(f"Rotated event log to {archive_name} (reason: {reason})")
            
            # Clean up old archives
            self._cleanup_old_archives()
            
        except Exception as e:
            self.logger.error(f"Failed to rotate event log: {e}")
            
    def _cleanup_old_archives(self):
        """Clean up archives older than 90 days"""
        try:
            cutoff = datetime.now() - timedelta(days=90)
            
            for archive in self.archives_dir.glob("log_*.ndjson.gz"):
                try:
                    # Extract timestamp from filename
                    parts = archive.stem.split('_')
                    if len(parts) >= 3:
                        date_str = parts[1]
                        time_str = parts[2]
                        archive_time = datetime.strptime(
                            f"{date_str}_{time_str}", 
                            '%Y%m%d_%H%M%S'
                        )
                        
                        if archive_time < cutoff:
                            archive.unlink()
                            self.logger.info(f"Deleted old archive: {archive.name}")
                            
                except Exception as e:
                    self.logger.warning(f"Failed to process archive {archive.name}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old archives: {e}")
            
    def validate_json_file(self, path: Path) -> bool:
        """Validate JSON file integrity including checksum if present"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            # Check for checksum
            if '_metadata' in data and 'checksum' in data['_metadata']:
                stored_checksum = data['_metadata']['checksum']
                
                # Calculate actual checksum
                data_copy = data.copy()
                del data_copy['_metadata']
                data_str = json.dumps(data_copy, sort_keys=True)
                actual_checksum = hashlib.sha256(data_str.encode()).hexdigest()
                
                if stored_checksum != actual_checksum:
                    self.logger.error(f"Checksum mismatch for {path.name}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate {path}: {e}")
            return False
            
    def validate_event_log(self) -> tuple[int, int]:
        """Validate event log integrity"""
        valid = 0
        invalid = 0
        
        try:
            with open(self.event_log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        json.loads(line)
                        valid += 1
                    except json.JSONDecodeError:
                        invalid += 1
                        self.logger.warning(f"Invalid event at line {line_num}")
                        
        except Exception as e:
            self.logger.error(f"Failed to validate event log: {e}")
            
        return valid, invalid
        
    def create_trigger(self, agent_name: str, trigger_data: Dict[str, Any]) -> bool:
        """Create trigger file atomically"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        trigger_file = self.triggers_dir / f"{agent_name}_trigger_{timestamp}.json"
        
        trigger_data['agent'] = agent_name
        trigger_data['created_at'] = datetime.now().isoformat()
        
        return self.atomic_write_json(trigger_file, trigger_data)
        
    def update_state(self, key: str, value: Any) -> bool:
        """Update state file atomically"""
        state_file = self.state_dir / f"{key}.state"
        
        state_data = {
            'key': key,
            'value': value,
            'updated_at': datetime.now().isoformat()
        }
        
        return self.atomic_write_json(state_file, state_data)


def main():
    """CLI interface for atomic operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AET Atomic Operations")
    parser.add_argument('--validate-log', action='store_true', 
                       help='Validate event log integrity')
    parser.add_argument('--rotate-log', action='store_true',
                       help='Force rotate event log')
    parser.add_argument('--validate-triggers', action='store_true',
                       help='Validate all trigger files')
    parser.add_argument('--test-atomic', action='store_true',
                       help='Test atomic write operations')
    
    args = parser.parse_args()
    
    ops = AtomicFileOperations()
    
    if args.validate_log:
        valid, invalid = ops.validate_event_log()
        print(f"Event log validation: {valid} valid, {invalid} invalid")
        
    elif args.rotate_log:
        ops._rotate_event_log("manual")
        print("Event log rotated")
        
    elif args.validate_triggers:
        valid = 0
        invalid = 0
        for trigger_file in ops.triggers_dir.glob("*.json"):
            if ops.validate_json_file(trigger_file):
                valid += 1
            else:
                invalid += 1
        print(f"Trigger validation: {valid} valid, {invalid} invalid")
        
    elif args.test_atomic:
        # Test atomic write
        test_file = ops.state_dir / "test.json"
        test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
        
        if ops.atomic_write_json(test_file, test_data):
            print("✓ Atomic write successful")
            
            if ops.validate_json_file(test_file):
                print("✓ File validation successful")
            else:
                print("✗ File validation failed")
                
            test_file.unlink()
        else:
            print("✗ Atomic write failed")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()