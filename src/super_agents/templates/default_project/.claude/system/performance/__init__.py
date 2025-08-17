#!/usr/bin/env python3
"""
Performance optimization module for super-agents CLI.

This module provides comprehensive performance improvements including:
- Lazy loading of modules to reduce startup time
- Intelligent caching for expensive operations
- File and metadata indexing for fast lookups
- Performance monitoring and baseline tracking

Targets 20% startup improvement and 10% runtime improvement as per roadmap.
"""

import time
import functools
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .lazy_loader import (
    lazy_import, preload_critical, get_lazy_import_stats,
    timed_import, optimize_module_loading
)
from .caching import (
    cached, cache_file_content, cached_subprocess_run, 
    cached_file_read, cached_json_load, clear_all_caches,
    get_cache_stats, invalidate_file_caches
)
from .indexing import (
    ProjectIndexer, get_project_indexer, ensure_project_indexed
)

# Version and metadata
__version__ = "1.0.0"
__all__ = [
    'initialize_performance_optimizations',
    'lazy_import', 
    'cached',
    'cache_file_content',
    'get_performance_stats',
    'clear_all_caches',
    'ensure_project_indexed',
    'performance_context'
]

def initialize_performance_optimizations():
    """
    Initialize all performance optimizations.
    
    Should be called early in CLI startup to maximize benefits.
    """
    # Initialize lazy loading
    optimize_module_loading()
    
    # Preload critical modules in background
    preload_critical()
    
    # Ensure project is indexed (background operation)
    # Skip in test environment to avoid database conflicts
    import os
    if not os.environ.get('PYTEST_CURRENT_TEST') and not os.environ.get('TESTING'):
        try:
            import threading
            def background_index():
                ensure_project_indexed()
            
            thread = threading.Thread(target=background_index, daemon=True)
            thread.start()
        except Exception:
            # If background indexing fails, continue without it
            pass

def get_performance_stats() -> Dict[str, Any]:
    """Get comprehensive performance statistics."""
    stats = {
        'lazy_imports': get_lazy_import_stats(),
        'caching': get_cache_stats(),
        'indexing': {}
    }
    
    try:
        indexer = get_project_indexer()
        stats['indexing'] = {
            'file_stats': indexer.get_file_stats(),
            'is_stale': indexer.is_index_stale()
        }
    except Exception as e:
        stats['indexing'] = {'error': str(e)}
    
    return stats

class PerformanceContext:
    """Context manager for performance-critical operations."""
    
    def __init__(self, operation_name: str, enable_caching: bool = True):
        self.operation_name = operation_name
        self.enable_caching = enable_caching
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Log slow operations (>1 second)
        if duration > 1.0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Slow operation {self.operation_name}: {duration:.3f}s")
        
        return False
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

def performance_context(operation_name: str, enable_caching: bool = True):
    """Create a performance monitoring context."""
    return PerformanceContext(operation_name, enable_caching)

def optimize_for_command(command_name: str) -> Callable:
    """
    Decorator to optimize specific CLI commands.
    
    Args:
        command_name: Name of the command for profiling
    
    Example:
        @optimize_for_command("init")
        def initialize_project():
            # command implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with performance_context(f"command_{command_name}"):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Optimization presets for different scenarios
class OptimizationPresets:
    """Predefined optimization configurations."""
    
    @staticmethod
    def startup_optimized():
        """Configuration optimized for fast startup."""
        return {
            'lazy_loading': True,
            'preload_critical': True,
            'memory_cache_size': 500,  # Smaller cache for startup
            'background_indexing': True
        }
    
    @staticmethod
    def runtime_optimized():
        """Configuration optimized for runtime performance."""
        return {
            'lazy_loading': True,
            'preload_critical': True,
            'memory_cache_size': 2000,  # Larger cache for runtime
            'aggressive_caching': True,
            'background_indexing': False  # Already indexed
        }
    
    @staticmethod
    def memory_constrained():
        """Configuration for memory-constrained environments."""
        return {
            'lazy_loading': True,
            'preload_critical': False,
            'memory_cache_size': 100,
            'disk_cache_enabled': True,
            'aggressive_caching': False
        }

def apply_optimization_preset(preset_name: str = "startup_optimized"):
    """Apply a predefined optimization preset."""
    presets = {
        'startup_optimized': OptimizationPresets.startup_optimized(),
        'runtime_optimized': OptimizationPresets.runtime_optimized(),
        'memory_constrained': OptimizationPresets.memory_constrained()
    }
    
    config = presets.get(preset_name, OptimizationPresets.startup_optimized())
    
    if config.get('lazy_loading', True):
        optimize_module_loading()
    
    if config.get('preload_critical', True):
        preload_critical()
    
    if config.get('background_indexing', True):
        try:
            import threading
            thread = threading.Thread(target=ensure_project_indexed, daemon=True)
            thread.start()
        except Exception:
            pass

# Initialize optimizations when module is imported
if __name__ != "__main__":
    initialize_performance_optimizations()