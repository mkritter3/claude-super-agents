#!/usr/bin/env python3
"""
AET Error Recovery System
Implements automatic recovery for common failures with exponential backoff
Part of Phase 1.3: Error Handling & Recovery
"""

import time
import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import subprocess
import signal

# Setup logging with rotation
from logging.handlers import RotatingFileHandler

class ErrorRecoverySystem:
    """Handles automatic recovery from common AET system failures"""
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.state_dir = self.claude_dir / "state"
        self.logs_dir = self.claude_dir / "logs"
        
        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup rotating logger
        self.logger = self._setup_logger()
        
        # Recovery strategies
        self.recovery_strategies = {
            "km_server_crash": self._recover_km_server,
            "database_locked": self._recover_database_lock,
            "port_conflict": self._recover_port_conflict,
            "stale_pid": self._recover_stale_pid,
            "event_log_corruption": self._recover_event_log,
            "trigger_file_corruption": self._recover_trigger_files
        }
        
        # Exponential backoff settings
        self.max_retries = 5
        self.base_delay = 1  # seconds
        self.max_delay = 60  # seconds
        
    def _setup_logger(self) -> logging.Logger:
        """Setup rotating file logger"""
        logger = logging.getLogger("AET_ErrorRecovery")
        logger.setLevel(logging.INFO)
        
        # Rotating file handler - 10MB max, keep 5 backups
        handler = RotatingFileHandler(
            self.logs_dir / "error_recovery.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    def exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay
        
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        """Execute function with exponential backoff retry"""
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"Recovery successful after {attempt} retries")
                return result
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                    
                delay = self.exponential_backoff(attempt)
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                
        return None
        
    def _recover_km_server(self) -> bool:
        """Recover crashed Knowledge Manager server"""
        self.logger.info("Attempting KM server recovery...")
        
        km_pid_file = self.state_dir / "km.pid"
        km_port_file = self.state_dir / "km.port"
        
        # Clean up stale PID
        if km_pid_file.exists():
            try:
                pid = int(km_pid_file.read_text().strip())
                # Check if process exists
                os.kill(pid, 0)
            except (OSError, ValueError):
                # Process doesn't exist, clean up
                km_pid_file.unlink(missing_ok=True)
                self.logger.info("Removed stale KM PID file")
                
        # Try to restart KM server
        if km_port_file.exists():
            port = km_port_file.read_text().strip()
            
            # Start KM with recovered port
            try:
                env = os.environ.copy()
                env['PYTHONPATH'] = str(self.claude_dir / "system")
                env['KM_PORT'] = port
                
                process = subprocess.Popen(
                    [sys.executable, str(self.claude_dir / "system" / "km_server.py")],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                
                # Wait for startup
                time.sleep(3)
                
                # Check if started successfully
                if process.poll() is None:
                    # Save new PID
                    km_pid_file.write_text(str(process.pid))
                    self.logger.info(f"KM server recovered on port {port} (PID: {process.pid})")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Failed to restart KM server: {e}")
                
        return False
        
    def _recover_database_lock(self) -> bool:
        """Recover from SQLite database lock"""
        self.logger.info("Attempting database lock recovery...")
        
        registry_db = self.claude_dir / "registry" / "registry.db"
        
        if not registry_db.exists():
            return True  # No database to recover
            
        # Check for lock files
        lock_files = [
            registry_db.with_suffix(".db-journal"),
            registry_db.with_suffix(".db-wal"),
            registry_db.with_suffix(".db-shm")
        ]
        
        for lock_file in lock_files:
            if lock_file.exists():
                try:
                    lock_file.unlink()
                    self.logger.info(f"Removed database lock file: {lock_file.name}")
                except Exception as e:
                    self.logger.error(f"Failed to remove lock file {lock_file}: {e}")
                    return False
                    
        # Try to verify database is accessible
        try:
            import sqlite3
            conn = sqlite3.connect(registry_db, timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            self.logger.info("Database lock recovered successfully")
            return True
        except Exception as e:
            self.logger.error(f"Database still locked after recovery: {e}")
            return False
            
    def _recover_port_conflict(self) -> bool:
        """Recover from port conflict by finding new port"""
        self.logger.info("Attempting port conflict recovery...")
        
        km_port_file = self.state_dir / "km.port"
        
        # Find available port
        import socket
        for port in range(5001, 5101):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', port))
                sock.close()
                
                # Save new port
                km_port_file.write_text(str(port))
                self.logger.info(f"Recovered with new port: {port}")
                return True
                
            except OSError:
                continue
                
        self.logger.error("No available ports found in range 5001-5100")
        return False
        
    def _recover_stale_pid(self) -> bool:
        """Clean up stale PID files"""
        self.logger.info("Cleaning up stale PID files...")
        
        cleaned = 0
        for pid_file in self.state_dir.glob("*.pid"):
            try:
                pid = int(pid_file.read_text().strip())
                # Check if process exists
                os.kill(pid, 0)
            except (OSError, ValueError):
                # Process doesn't exist, clean up
                pid_file.unlink()
                self.logger.info(f"Removed stale PID file: {pid_file.name}")
                cleaned += 1
                
        return cleaned > 0
        
    def _recover_event_log(self) -> bool:
        """Recover corrupted event log"""
        self.logger.info("Attempting event log recovery...")
        
        event_log = self.claude_dir / "events" / "log.ndjson"
        
        if not event_log.exists():
            # Create new empty log
            event_log.parent.mkdir(parents=True, exist_ok=True)
            event_log.touch()
            self.logger.info("Created new event log")
            return True
            
        # Try to read and validate each line
        valid_lines = []
        corrupted = 0
        
        try:
            with open(event_log, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json.loads(line)
                        valid_lines.append(line)
                    except json.JSONDecodeError:
                        corrupted += 1
                        self.logger.warning(f"Skipping corrupted event at line {line_num}")
                        
            if corrupted > 0:
                # Backup corrupted file
                backup = event_log.with_suffix('.ndjson.corrupted')
                event_log.rename(backup)
                
                # Write valid lines to new file
                with open(event_log, 'w') as f:
                    for line in valid_lines:
                        f.write(line + '\n')
                        
                self.logger.info(f"Recovered {len(valid_lines)} valid events, skipped {corrupted} corrupted")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to recover event log: {e}")
            return False
            
        return True
        
    def _recover_trigger_files(self) -> bool:
        """Recover corrupted trigger files using atomic writes"""
        self.logger.info("Checking trigger files...")
        
        triggers_dir = self.claude_dir / "triggers"
        if not triggers_dir.exists():
            triggers_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info("Created triggers directory")
            return True
            
        recovered = 0
        for trigger_file in triggers_dir.glob("*.json"):
            try:
                with open(trigger_file, 'r') as f:
                    data = json.load(f)
                    
                # Validate basic structure
                if not isinstance(data, dict):
                    raise ValueError("Invalid trigger structure")
                    
            except (json.JSONDecodeError, ValueError) as e:
                # Backup corrupted file
                backup = trigger_file.with_suffix('.json.corrupted')
                trigger_file.rename(backup)
                self.logger.warning(f"Backed up corrupted trigger: {trigger_file.name}")
                recovered += 1
                
        if recovered > 0:
            self.logger.info(f"Recovered from {recovered} corrupted trigger files")
            
        return True
        
    def health_check_with_retry(self, service: str, check_func: Callable) -> bool:
        """Perform health check with exponential backoff retry"""
        self.logger.info(f"Health checking {service}...")
        
        def wrapped_check():
            if check_func():
                return True
            raise Exception(f"{service} health check failed")
            
        try:
            return self.retry_with_backoff(wrapped_check)
        except Exception:
            self.logger.error(f"{service} failed health check after retries")
            return False
            
    def recover_all(self) -> Dict[str, bool]:
        """Run all recovery strategies"""
        self.logger.info("Starting comprehensive recovery...")
        
        results = {}
        for name, strategy in self.recovery_strategies.items():
            try:
                results[name] = strategy()
            except Exception as e:
                self.logger.error(f"Recovery strategy {name} failed: {e}")
                results[name] = False
                
        # Summary
        succeeded = sum(1 for v in results.values() if v)
        total = len(results)
        self.logger.info(f"Recovery complete: {succeeded}/{total} strategies succeeded")
        
        return results


def main():
    """CLI interface for error recovery"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AET Error Recovery System")
    parser.add_argument('--recover', action='store_true', help='Run all recovery strategies')
    parser.add_argument('--health-check', action='store_true', help='Perform health checks')
    parser.add_argument('--strategy', choices=[
        'km_server_crash', 'database_locked', 'port_conflict',
        'stale_pid', 'event_log_corruption', 'trigger_file_corruption'
    ], help='Run specific recovery strategy')
    
    args = parser.parse_args()
    
    recovery = ErrorRecoverySystem()
    
    if args.recover:
        results = recovery.recover_all()
        for strategy, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {strategy}")
            
    elif args.strategy:
        strategy_func = recovery.recovery_strategies.get(args.strategy)
        if strategy_func:
            success = strategy_func()
            print(f"Recovery {'succeeded' if success else 'failed'}")
            sys.exit(0 if success else 1)
            
    elif args.health_check:
        # Example health checks
        def check_km():
            pid_file = recovery.state_dir / "km.pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    return True
                except (OSError, ValueError):
                    pass
            return False
            
        km_healthy = recovery.health_check_with_retry("KM Server", check_km)
        print(f"KM Server: {'Healthy' if km_healthy else 'Unhealthy'}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()