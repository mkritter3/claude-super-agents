"""
Error recovery system for automatic error handling
"""

import time
import logging
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass


@dataclass
class ErrorInfo:
    """Information about an error that occurred"""
    error_type: str
    message: str
    timestamp: float
    context: Dict[str, Any]
    retry_count: int = 0


class ErrorRecoverySystem:
    """Automatic error recovery system"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.error_log: list = []
        self.max_retries = 3
        self.retry_delay = 1.0
        
    def register_handler(self, error_type: str, handler: Callable) -> None:
        """
        Register an error handler for a specific error type
        
        Args:
            error_type: Type of error to handle
            handler: Function to handle the error
        """
        self.handlers[error_type] = handler
        
    def handle_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """
        Handle an error using registered handlers
        
        Args:
            error_info: Information about the error
            
        Returns:
            Recovery result with action taken
        """
        # Log the error
        self.error_log.append(error_info)
        
        # Find appropriate handler
        handler = self.handlers.get(error_info.error_type)
        if handler:
            try:
                return handler(error_info)
            except Exception as e:
                logging.error(f"Error handler failed: {e}")
                return {"recovered": False, "action": "handler_failed"}
        
        # Default recovery strategy
        if error_info.retry_count < self.max_retries:
            return {
                "recovered": True,
                "action": "retry",
                "delay": self.retry_delay * (error_info.retry_count + 1)
            }
        else:
            return {"recovered": False, "action": "max_retries_exceeded"}
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_log:
            return {"total_errors": 0}
            
        error_types = {}
        for error in self.error_log:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
            
        return {
            "total_errors": len(self.error_log),
            "error_types": error_types,
            "recent_errors": self.error_log[-10:]  # Last 10 errors
        }