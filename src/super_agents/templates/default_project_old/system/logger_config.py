#!/usr/bin/env python3
"""
Structured Logging Configuration for AET System
Provides JSON logging format with ticket_id and agent context.
"""

import logging
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'ticket_id': getattr(record, 'ticket_id', None),
            'job_id': getattr(record, 'job_id', None),
            'agent': getattr(record, 'agent', None),
            'component': getattr(record, 'component', None)
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
        
        return json.dumps(log_obj, default=str)

class AETLogger:
    """Centralized logger configuration for AET system."""
    
    def __init__(self):
        self.loggers = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Configure root logger with structured formatting."""
        # Create logs directory if it doesn't exist
        log_dir = Path(".claude/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler with structured format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
        
        # File handler for persistent logs
        file_handler = logging.FileHandler(log_dir / "aet.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.FileHandler(log_dir / "aet_errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str, component: str = None) -> logging.Logger:
        """Get a configured logger for a specific component."""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            
            # Add component context if provided
            if component:
                logger = LoggerAdapter(logger, {'component': component})
            
            self.loggers[name] = logger
        
        return self.loggers[name]

class LoggerAdapter(logging.LoggerAdapter):
    """Adapter to add context to log records."""
    
    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        """Process log message to add context."""
        # Merge extra context
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        
        return msg, kwargs

class ContextualLogger:
    """Logger that maintains context throughout a task/operation."""
    
    def __init__(self, logger: logging.Logger, 
                 ticket_id: str = None, 
                 job_id: str = None, 
                 agent: str = None):
        self.logger = logger
        self.context = {
            'ticket_id': ticket_id,
            'job_id': job_id,
            'agent': agent
        }
    
    def _log_with_context(self, level: int, msg: Any, *args, **kwargs):
        """Log message with persistent context."""
        extra = kwargs.get('extra', {})
        extra.update({k: v for k, v in self.context.items() if v is not None})
        kwargs['extra'] = extra
        
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: Any, *args, **kwargs):
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: Any, *args, **kwargs):
        self._log_with_context(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: Any, *args, **kwargs):
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: Any, *args, **kwargs):
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: Any, *args, **kwargs):
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: Any, *args, **kwargs):
        """Log exception with full stack trace."""
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)

# Global logger instance
_aet_logger = AETLogger()

def get_logger(name: str, component: str = None) -> logging.Logger:
    """Get a configured logger instance."""
    return _aet_logger.get_logger(name, component)

def get_contextual_logger(name: str, 
                         ticket_id: str = None, 
                         job_id: str = None, 
                         agent: str = None,
                         component: str = None) -> ContextualLogger:
    """Get a contextual logger with persistent context."""
    base_logger = get_logger(name, component)
    return ContextualLogger(base_logger, ticket_id, job_id, agent)

def log_performance(func_name: str, duration: float, 
                   ticket_id: str = None, 
                   component: str = None):
    """Log performance metrics."""
    logger = get_logger("performance", component)
    logger.info("Performance metric", extra={
        'function': func_name,
        'duration_seconds': duration,
        'ticket_id': ticket_id,
        'metric_type': 'execution_time'
    })

def log_system_event(event_type: str, details: Dict[str, Any],
                    ticket_id: str = None,
                    component: str = None):
    """Log system events."""
    logger = get_logger("system", component)
    logger.info(f"System event: {event_type}", extra={
        'event_type': event_type,
        'ticket_id': ticket_id,
        **details
    })

# Setup logging on module import
if not hasattr(logging.getLogger(), '_aet_configured'):
    _aet_logger._setup_root_logger()
    logging.getLogger()._aet_configured = True

if __name__ == "__main__":
    # Test the logging configuration
    logger = get_contextual_logger("test", 
                                  ticket_id="AET-001", 
                                  job_id="job-123", 
                                  agent="test-agent")
    
    logger.info("Testing structured logging")
    logger.warning("This is a warning with context")
    
    try:
        raise ValueError("Test exception")
    except Exception:
        logger.exception("Exception caught during testing")
    
    # Test performance logging
    log_performance("test_function", 1.25, ticket_id="AET-001")
    
    # Test system event logging
    log_system_event("task_started", {
        "task_type": "development",
        "estimated_duration": 3600
    }, ticket_id="AET-001")