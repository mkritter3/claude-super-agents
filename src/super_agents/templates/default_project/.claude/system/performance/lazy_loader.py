#!/usr/bin/env python3
"""
Lazy loading system for CLI performance improvements.

Implements intelligent lazy imports and module caching to reduce startup time.
Targets 20% startup improvement and 10% runtime improvement as per roadmap.
"""

import sys
import time
import types
import importlib
import functools
from typing import Dict, Any, Optional, Callable, Set, List
from pathlib import Path
import threading

class LazyModule:
    """Lazy module loader that defers imports until first access."""
    
    def __init__(self, module_name: str, fallback: Optional[Any] = None):
        self.module_name = module_name
        self.fallback = fallback
        self._module = None
        self._import_failed = False
        self._lock = threading.Lock()
    
    def __getattr__(self, name: str) -> Any:
        """Load module on first attribute access."""
        if self._import_failed and self.fallback is not None:
            return getattr(self.fallback, name, None)
        
        if self._module is None:
            with self._lock:
                if self._module is None:  # Double-check locking
                    try:
                        self._module = importlib.import_module(self.module_name)
                    except ImportError:
                        self._import_failed = True
                        if self.fallback is not None:
                            return getattr(self.fallback, name, None)
                        raise
        
        return getattr(self._module, name)
    
    def __call__(self, *args, **kwargs):
        """Support for modules that are callable."""
        module = self._get_module()
        if hasattr(module, '__call__'):
            return module(*args, **kwargs)
        raise TypeError(f"'{self.module_name}' module is not callable")
    
    def _get_module(self):
        """Internal method to get the loaded module."""
        if self._module is None:
            self.__getattr__('__name__')  # Trigger loading
        return self._module
    
    @property
    def is_loaded(self) -> bool:
        """Check if module has been loaded."""
        return self._module is not None
    
    @property
    def import_failed(self) -> bool:
        """Check if import failed."""
        return self._import_failed

class LazyImportManager:
    """Manages lazy imports for the entire application."""
    
    def __init__(self):
        self.lazy_modules: Dict[str, LazyModule] = {}
        self.load_times: Dict[str, float] = {}
        self.critical_modules: Set[str] = set()
        self._lock = threading.Lock()
    
    def register_lazy_module(self, module_name: str, fallback: Optional[Any] = None, 
                           critical: bool = False) -> LazyModule:
        """Register a module for lazy loading."""
        with self._lock:
            if module_name not in self.lazy_modules:
                self.lazy_modules[module_name] = LazyModule(module_name, fallback)
                if critical:
                    self.critical_modules.add(module_name)
            return self.lazy_modules[module_name]
    
    def preload_critical_modules(self):
        """Preload critical modules in background."""
        def preload():
            for module_name in self.critical_modules:
                if module_name in self.lazy_modules:
                    lazy_mod = self.lazy_modules[module_name]
                    if not lazy_mod.is_loaded and not lazy_mod.import_failed:
                        try:
                            start_time = time.time()
                            lazy_mod._get_module()
                            self.load_times[module_name] = time.time() - start_time
                        except ImportError:
                            pass
        
        # Run preloading in background thread
        thread = threading.Thread(target=preload, daemon=True)
        thread.start()
    
    def get_load_stats(self) -> Dict[str, Any]:
        """Get loading statistics for performance monitoring."""
        loaded_count = sum(1 for mod in self.lazy_modules.values() if mod.is_loaded)
        failed_count = sum(1 for mod in self.lazy_modules.values() if mod.import_failed)
        
        return {
            "total_modules": len(self.lazy_modules),
            "loaded_modules": loaded_count,
            "failed_modules": failed_count,
            "load_times": self.load_times.copy(),
            "average_load_time": sum(self.load_times.values()) / len(self.load_times) if self.load_times else 0
        }

# Global lazy import manager
_lazy_manager = LazyImportManager()

def lazy_import(module_name: str, fallback: Optional[Any] = None, 
                critical: bool = False) -> LazyModule:
    """
    Create a lazy import for a module.
    
    Args:
        module_name: Name of module to import
        fallback: Fallback object if import fails
        critical: Whether to preload this module in background
    
    Returns:
        LazyModule proxy object
    
    Example:
        # Instead of: import requests
        requests = lazy_import('requests')
        
        # Use normally:
        response = requests.get('http://example.com')
    """
    return _lazy_manager.register_lazy_module(module_name, fallback, critical)

def preload_critical():
    """Preload critical modules in background."""
    _lazy_manager.preload_critical_modules()

def get_lazy_import_stats() -> Dict[str, Any]:
    """Get lazy import performance statistics."""
    return _lazy_manager.get_load_stats()

# Common lazy imports for super-agents
class MockFallback:
    """Fallback object that returns None for any attribute/call."""
    def __getattr__(self, name): return None
    def __call__(self, *args, **kwargs): return None

# Pre-configure common lazy imports
subprocess = lazy_import('subprocess', critical=True)
json = lazy_import('json', critical=True)
sqlite3 = lazy_import('sqlite3', critical=True)
shutil = lazy_import('shutil')
urllib = lazy_import('urllib')

# Optional dependencies with fallbacks
requests = lazy_import('requests', MockFallback())
flask = lazy_import('flask', MockFallback())
numpy = lazy_import('numpy', MockFallback())
rich = lazy_import('rich', MockFallback())

def timed_import(func: Callable) -> Callable:
    """Decorator to time import-heavy functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Log slow imports (>100ms)
        if end_time - start_time > 0.1:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Slow import in {func.__name__}: {end_time - start_time:.3f}s")
        
        return result
    return wrapper

class ImportCache:
    """Cache for expensive import operations."""
    
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, float] = {}
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str, loader: Callable[[], Any]) -> Any:
        """Get from cache or load and cache."""
        with self._lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            
            # Load and cache
            value = loader()
            
            # Evict oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
            return value
    
    def invalidate(self, key: str):
        """Remove item from cache."""
        with self._lock:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": getattr(self, '_hits', 0) / max(getattr(self, '_requests', 1), 1)
        }

# Global import cache
_import_cache = ImportCache()

def cached_import(module_name: str) -> Any:
    """Import with caching for performance."""
    return _import_cache.get(
        module_name, 
        lambda: importlib.import_module(module_name)
    )

def optimize_module_loading():
    """Apply global optimizations for module loading."""
    # Precompile frequently used regex patterns
    import re
    
    common_patterns = [
        r'\.py$', r'\.md$', r'\.json$', r'\.yaml$', r'\.yml$',
        r'^[a-zA-Z_][a-zA-Z0-9_]*$',  # Valid Python identifier
        r'\d{4}-\d{2}-\d{2}',  # Date pattern
        r'[\w\.-]+@[\w\.-]+\.\w+',  # Email pattern
    ]
    
    for pattern in common_patterns:
        try:
            re.compile(pattern)
        except re.error:
            pass
    
    # Set up lazy imports for heavy modules
    preload_critical()

# Module-level initialization
if __name__ != "__main__":
    # Only run optimization if imported as module
    optimize_module_loading()