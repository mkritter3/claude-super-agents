#!/usr/bin/env python3
"""
File-based circuit breaker with thread-safe locking for CLI reliability improvements.

Implements the roadmap requirement to prevent repeated failures to external 
services with enhanced thread safety and cross-platform compatibility.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import filelock, fall back to no locking if not available
try:
    import filelock
    FILELOCK_AVAILABLE = True
except ImportError:
    FILELOCK_AVAILABLE = False
    logger.warning("filelock not available, circuit breaker will not use file locking")

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class FileBasedCircuitBreaker:
    """
    File-based circuit breaker with thread-safe operations.
    
    Features:
    - Thread-safe file operations with locking
    - Graceful degradation when locking unavailable
    - Configurable failure thresholds and timeouts
    - Persistent state across CLI invocations
    - Cross-platform compatibility
    """
    
    def __init__(self, 
                 service_name: str, 
                 failure_threshold: int = 3, 
                 timeout_seconds: int = 300,
                 config_dir: Optional[Path] = None):
        """
        Initialize circuit breaker.
        
        Args:
            service_name: Name of the service to protect
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying again (default 5 minutes)
            config_dir: Directory for state files (default: ~/.config/claude-super-agents)
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        
        # Set up file paths
        if config_dir is None:
            config_dir = Path.home() / ".config" / "claude-super-agents"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = config_dir / "circuit_breaker_state.json"
        self.lock_file = config_dir / "circuit_breaker.lock"
        
        # Initialize state
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """Ensure state file exists with valid structure."""
        if not self.state_file.exists():
            initial_state = {}
            self._save_state_unsafe(initial_state)
    
    @contextmanager
    def _file_lock(self):
        """Context manager for file locking with fallback."""
        if FILELOCK_AVAILABLE:
            lock = filelock.FileLock(str(self.lock_file))
            try:
                with lock:
                    yield
            except Exception as e:
                logger.warning(f"File locking failed, proceeding without lock: {e}")
                yield
        else:
            # No locking available, proceed anyway
            yield
    
    def _load_state(self) -> Dict[str, Any]:
        """Load circuit breaker state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load circuit breaker state: {e}")
        
        return {}
    
    def _save_state_unsafe(self, state: Dict[str, Any]):
        """Save state without locking (for internal use)."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save circuit breaker state: {e}")
    
    def _save_state(self, state: Dict[str, Any]):
        """Save circuit breaker state to file with locking."""
        with self._file_lock():
            self._save_state_unsafe(state)
    
    def _get_service_state(self) -> Dict[str, Any]:
        """Get state for this specific service."""
        with self._file_lock():
            state = self._load_state()
            return state.get(self.service_name, {
                "failures": 0,
                "last_failure_ts": 0,
                "state": CircuitState.CLOSED.value,
                "last_success_ts": 0
            })
    
    def _update_service_state(self, updates: Dict[str, Any]):
        """Update state for this specific service."""
        with self._file_lock():
            state = self._load_state()
            service_state = state.get(self.service_name, {})
            service_state.update(updates)
            state[self.service_name] = service_state
            self._save_state_unsafe(state)
    
    def should_allow_request(self) -> bool:
        """
        Check if circuit breaker should allow a request.
        
        Returns:
            True if request should be allowed, False if blocked
        """
        service_state = self._get_service_state()
        current_state = CircuitState(service_state.get("state", CircuitState.CLOSED.value))
        failures = service_state.get("failures", 0)
        last_failure_ts = service_state.get("last_failure_ts", 0)
        
        current_time = time.time()
        
        if current_state == CircuitState.CLOSED:
            # Normal operation
            return True
        
        elif current_state == CircuitState.OPEN:
            # Circuit is open, check if timeout has passed
            if current_time - last_failure_ts >= self.timeout_seconds:
                # Move to half-open state
                self._update_service_state({
                    "state": CircuitState.HALF_OPEN.value
                })
                logger.info(f"Circuit breaker for {self.service_name} moved to HALF_OPEN")
                return True
            else:
                # Still in timeout period
                return False
        
        elif current_state == CircuitState.HALF_OPEN:
            # Testing state - allow one request
            return True
        
        return False
    
    def record_success(self):
        """Record a successful operation."""
        service_state = self._get_service_state()
        current_state = CircuitState(service_state.get("state", CircuitState.CLOSED.value))
        
        updates = {
            "failures": 0,
            "last_success_ts": time.time(),
            "state": CircuitState.CLOSED.value
        }
        
        self._update_service_state(updates)
        
        if current_state != CircuitState.CLOSED:
            logger.info(f"Circuit breaker for {self.service_name} recovered and CLOSED")
    
    def record_failure(self):
        """Record a failed operation."""
        service_state = self._get_service_state()
        current_state = CircuitState(service_state.get("state", CircuitState.CLOSED.value))
        failures = service_state.get("failures", 0) + 1
        current_time = time.time()
        
        updates = {
            "failures": failures,
            "last_failure_ts": current_time
        }
        
        # Determine new state
        if current_state == CircuitState.HALF_OPEN:
            # Failed during testing, go back to open
            updates["state"] = CircuitState.OPEN.value
            logger.warning(f"Circuit breaker for {self.service_name} failed during HALF_OPEN, returning to OPEN")
        
        elif failures >= self.failure_threshold:
            # Too many failures, open the circuit
            updates["state"] = CircuitState.OPEN.value
            logger.warning(f"Circuit breaker for {self.service_name} OPENED after {failures} failures")
        else:
            # Still under threshold, stay closed
            updates["state"] = CircuitState.CLOSED.value
        
        self._update_service_state(updates)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        service_state = self._get_service_state()
        current_time = time.time()
        
        return {
            "service_name": self.service_name,
            "state": service_state.get("state", CircuitState.CLOSED.value),
            "failures": service_state.get("failures", 0),
            "last_failure_ts": service_state.get("last_failure_ts", 0),
            "last_success_ts": service_state.get("last_success_ts", 0),
            "failure_threshold": self.failure_threshold,
            "timeout_seconds": self.timeout_seconds,
            "time_until_retry": max(0, 
                service_state.get("last_failure_ts", 0) + self.timeout_seconds - current_time
            ) if service_state.get("state") == CircuitState.OPEN.value else 0
        }
    
    def reset(self):
        """Reset circuit breaker to closed state (for testing/admin purposes)."""
        updates = {
            "failures": 0,
            "last_failure_ts": 0,
            "state": CircuitState.CLOSED.value,
            "last_success_ts": time.time()
        }
        self._update_service_state(updates)
        logger.info(f"Circuit breaker for {self.service_name} manually reset")

@contextmanager
def circuit_breaker_protection(service_name: str, 
                             failure_threshold: int = 3,
                             timeout_seconds: int = 300):
    """
    Context manager for circuit breaker protection.
    
    Usage:
        with circuit_breaker_protection("api_service") as breaker:
            if breaker.should_allow_request():
                # Make the request
                result = make_api_call()
                breaker.record_success()
                return result
            else:
                # Circuit is open, handle gracefully
                return fallback_response()
    """
    breaker = FileBasedCircuitBreaker(service_name, failure_threshold, timeout_seconds)
    
    try:
        yield breaker
    except Exception as e:
        # Record failure for any unhandled exception
        breaker.record_failure()
        raise

def protected_call(service_name: str, 
                  func: Callable,
                  fallback: Optional[Callable] = None,
                  failure_threshold: int = 3,
                  timeout_seconds: int = 300) -> Any:
    """
    Execute a function with circuit breaker protection.
    
    Args:
        service_name: Name of the service for circuit breaker
        func: Function to execute
        fallback: Optional fallback function if circuit is open
        failure_threshold: Number of failures before opening circuit
        timeout_seconds: Time to wait before retrying
    
    Returns:
        Result of func() or fallback() if circuit is open
    
    Raises:
        CircuitBreakerOpenError: If circuit is open and no fallback provided
    """
    breaker = FileBasedCircuitBreaker(service_name, failure_threshold, timeout_seconds)
    
    if not breaker.should_allow_request():
        if fallback:
            logger.info(f"Circuit breaker for {service_name} is OPEN, using fallback")
            return fallback()
        else:
            raise CircuitBreakerOpenError(f"Circuit breaker for {service_name} is OPEN")
    
    try:
        result = func()
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure()
        raise

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and no fallback is available."""
    pass

# Global circuit breakers registry
_circuit_breakers: Dict[str, FileBasedCircuitBreaker] = {}

def get_circuit_breaker(service_name: str, 
                       failure_threshold: int = 3,
                       timeout_seconds: int = 300) -> FileBasedCircuitBreaker:
    """Get or create a circuit breaker for a service."""
    key = f"{service_name}_{failure_threshold}_{timeout_seconds}"
    
    if key not in _circuit_breakers:
        _circuit_breakers[key] = FileBasedCircuitBreaker(
            service_name, failure_threshold, timeout_seconds
        )
    
    return _circuit_breakers[key]

def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """Get states of all active circuit breakers."""
    return {name: breaker.get_state() for name, breaker in _circuit_breakers.items()}