#!/usr/bin/env python3
"""
Production reliability features: circuit breakers, retries, health checks.
"""

import time
import json
import functools
from typing import Callable, Any, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception(f"Circuit breaker OPEN for {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).seconds > self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

class RetryStrategy:
    """Configurable retry strategy with backoff."""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 backoff_base: float = 2.0,
                 max_delay: float = 60.0,
                 exceptions: tuple = (Exception,)):
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.max_delay = max_delay
        self.exceptions = exceptions
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_attempts):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e
                    
                    if attempt < self.max_attempts - 1:
                        delay = min(
                            self.backoff_base ** attempt,
                            self.max_delay
                        )
                        from logger_config import get_contextual_logger
                        logger = get_contextual_logger("reliability", component="retry_strategy")
                        logger.info("Retrying operation", extra={
                            'attempt': attempt + 1,
                            'max_attempts': self.max_attempts,
                            'function': func.__name__,
                            'delay_seconds': delay
                        })
                        time.sleep(delay)
                    else:
                        from logger_config import get_contextual_logger
                        logger = get_contextual_logger("reliability", component="retry_strategy")
                        logger.error("All retry attempts failed", extra={
                            'function': func.__name__,
                            'max_attempts': self.max_attempts
                        })
            
            raise last_exception
        
        return wrapper

class HealthChecker:
    """System health monitoring."""
    
    def __init__(self, check_interval: int = 300):  # 5 minutes
        self.check_interval = check_interval
        self.last_check = None
        self.health_status = {}
    
    def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        now = datetime.now()
        
        # Skip if checked recently
        if (self.last_check and 
            (now - self.last_check).seconds < self.check_interval):
            return self.health_status
        
        self.last_check = now
        health = {
            "timestamp": now.isoformat(),
            "overall_status": "HEALTHY",
            "components": {}
        }
        
        # Check critical paths
        health["components"]["event_log"] = self._check_event_log()
        health["components"]["registry"] = self._check_registry()
        health["components"]["workspaces"] = self._check_workspaces()
        health["components"]["knowledge_manager"] = self._check_km()
        
        # Determine overall status
        component_statuses = [c["status"] for c in health["components"].values()]
        if "CRITICAL" in component_statuses:
            health["overall_status"] = "CRITICAL"
        elif "DEGRADED" in component_statuses:
            health["overall_status"] = "DEGRADED"
        
        self.health_status = health
        return health
    
    def _check_event_log(self) -> Dict[str, Any]:
        """Check event log health."""
        log_path = Path(".claude/events/log.ndjson")
        
        if not log_path.exists():
            return {"status": "CRITICAL", "message": "Event log missing"}
        
        try:
            # Check if writable
            with open(log_path, 'a') as f:
                pass
            
            # Check size (warn if > 100MB)
            size_mb = log_path.stat().st_size / (1024 * 1024)
            if size_mb > 100:
                return {
                    "status": "DEGRADED", 
                    "message": f"Event log large: {size_mb:.1f}MB"
                }
            
            return {"status": "HEALTHY", "size_mb": size_mb}
            
        except Exception as e:
            return {"status": "CRITICAL", "message": f"Event log error: {e}"}
    
    def _check_registry(self) -> Dict[str, Any]:
        """Check file registry health."""
        registry_path = Path(".claude/registry/files.db")
        
        if not registry_path.exists():
            return {"status": "CRITICAL", "message": "Registry database missing"}
        
        try:
            import sqlite3
            conn = sqlite3.connect(str(registry_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM files")
            file_count = cursor.fetchone()[0]
            conn.close()
            
            return {"status": "HEALTHY", "file_count": file_count}
            
        except Exception as e:
            return {"status": "CRITICAL", "message": f"Registry error: {e}"}
    
    def _check_workspaces(self) -> Dict[str, Any]:
        """Check workspace directory health."""
        workspace_dir = Path(".claude/workspaces")
        
        if not workspace_dir.exists():
            return {"status": "DEGRADED", "message": "Workspace directory missing"}
        
        try:
            workspace_count = len(list(workspace_dir.iterdir()))
            
            # Check disk space (warn if < 1GB free)
            import shutil
            free_bytes = shutil.disk_usage(workspace_dir).free
            free_gb = free_bytes / (1024**3)
            
            if free_gb < 1:
                return {
                    "status": "DEGRADED",
                    "message": f"Low disk space: {free_gb:.2f}GB free",
                    "workspace_count": workspace_count
                }
            
            return {
                "status": "HEALTHY", 
                "workspace_count": workspace_count,
                "free_space_gb": free_gb
            }
            
        except Exception as e:
            return {"status": "DEGRADED", "message": f"Workspace check error: {e}"}
    
    def _check_km(self) -> Dict[str, Any]:
        """Check Knowledge Manager health."""
        pid_file = Path(".claude/km.pid")
        
        if not pid_file.exists():
            return {"status": "DEGRADED", "message": "KM not running"}
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is running
            import os
            import signal
            try:
                os.kill(pid, 0)  # Send null signal to check if process exists
            except OSError:
                return {"status": "DEGRADED", "message": "KM process not found"}
            
            # Try to connect to KM server
            try:
                import requests
                response = requests.get("http://127.0.0.1:5001/mcp/spec", timeout=5)
                if response.status_code == 200:
                    return {"status": "HEALTHY", "pid": pid}
                else:
                    return {"status": "DEGRADED", "message": f"KM HTTP {response.status_code}"}
            except Exception:
                return {"status": "DEGRADED", "message": "KM not responding"}
            
        except Exception as e:
            return {"status": "DEGRADED", "message": f"KM check error: {e}"}

class LogRotator:
    """Log rotation for event logs."""
    
    def __init__(self, max_size_mb: int = 50, max_files: int = 5):
        self.max_size_mb = max_size_mb
        self.max_files = max_files
    
    def rotate_if_needed(self, log_path: Path):
        """Rotate log file if it exceeds size limit."""
        if not log_path.exists():
            return
        
        size_mb = log_path.stat().st_size / (1024 * 1024)
        
        if size_mb > self.max_size_mb:
            from logger_config import get_contextual_logger
            logger = get_contextual_logger("reliability", component="log_rotator")
            logger.info("Rotating log file", extra={
                'log_path': str(log_path),
                'size_mb': size_mb
            })
            self._rotate_log(log_path)
    
    def _rotate_log(self, log_path: Path):
        """Perform log rotation."""
        # Move existing rotated logs
        for i in range(self.max_files - 1, 0, -1):
            old_path = Path(f"{log_path}.{i}")
            new_path = Path(f"{log_path}.{i + 1}")
            
            if old_path.exists():
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)
        
        # Move current log to .1
        rotated_path = Path(f"{log_path}.1")
        if rotated_path.exists():
            rotated_path.unlink()
        
        log_path.rename(rotated_path)
        
        # Create new empty log
        log_path.touch()

# Singleton instances
health_checker = HealthChecker()
log_rotator = LogRotator()

# Decorators for common use
def with_circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    """Decorator to add circuit breaker to function."""
    return CircuitBreaker(failure_threshold, recovery_timeout)

def with_retry(max_attempts: int = 3, backoff_base: float = 2.0):
    """Decorator to add retry logic to function."""
    return RetryStrategy(max_attempts, backoff_base)

def with_health_check(func: Callable) -> Callable:
    """Decorator to perform health check before function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        health = health_checker.check_system_health()
        
        if health["overall_status"] == "CRITICAL":
            raise Exception(f"System health critical: {health}")
        
        return func(*args, **kwargs)
    
    return wrapper

if __name__ == "__main__":
    # Run health check
    health = health_checker.check_system_health()
    print(json.dumps(health, indent=2))
    
    # Rotate logs if needed
    log_rotator.rotate_if_needed(Path(".claude/events/log.ndjson"))