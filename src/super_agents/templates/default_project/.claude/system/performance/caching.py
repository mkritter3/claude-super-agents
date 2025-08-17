#!/usr/bin/env python3
"""
Intelligent caching system for CLI performance improvements.

Implements multi-tier caching for expensive operations like file reads, 
subprocess calls, and database queries. Targets performance improvements
as specified in the roadmap.
"""

import os
import time
import json
import pickle
import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Tuple, Union, List
from functools import wraps
from datetime import datetime, timedelta

class CacheEntry:
    """Single cache entry with metadata."""
    
    def __init__(self, value: Any, ttl: Optional[float] = None):
        self.value = value
        self.created_at = time.time()
        self.last_accessed = self.created_at
        self.access_count = 0
        self.ttl = ttl
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def access(self) -> Any:
        """Access the value and update metadata."""
        self.last_accessed = time.time()
        self.access_count += 1
        return self.value
    
    def age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at

class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, args: Tuple, kwargs: Dict) -> str:
        """Create cache key from function arguments."""
        key_data = (args, tuple(sorted(kwargs.items())))
        return hashlib.md5(str(key_data).encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired:
                    self._hits += 1
                    return entry.access()
                else:
                    # Remove expired entry
                    del self.cache[key]
            
            self._misses += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Put value in cache."""
        with self._lock:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl
            
            # Evict expired entries first
            self._evict_expired()
            
            # Evict LRU entries if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = CacheEntry(value, ttl)
    
    def _evict_expired(self) -> None:
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self.cache.items() 
            if entry.is_expired
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_lru(self) -> None:
        """Remove least recently used entry."""
        if not self.cache:
            return
        
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed
        )
        del self.cache[lru_key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / max(total_requests, 1)
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "total_requests": total_requests
            }

class DiskCache:
    """Persistent disk cache for expensive operations."""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.index_file = self.cache_dir / "index.json"
        self._lock = threading.Lock()
        self._load_index()
    
    def _load_index(self) -> None:
        """Load cache index from disk."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            else:
                self.index = {}
        except (json.JSONDecodeError, OSError):
            self.index = {}
    
    def _save_index(self) -> None:
        """Save cache index to disk."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except OSError:
            pass
    
    def _make_filename(self, key: str) -> Path:
        """Create filename for cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"
    
    def get(self, key: str, max_age: Optional[float] = None) -> Optional[Any]:
        """Get value from disk cache."""
        with self._lock:
            if key not in self.index:
                return None
            
            entry_info = self.index[key]
            
            # Check age if specified
            if max_age is not None:
                age = time.time() - entry_info['created_at']
                if age > max_age:
                    self.invalidate(key)
                    return None
            
            # Load from disk
            cache_file = self._make_filename(key)
            try:
                with open(cache_file, 'rb') as f:
                    value = pickle.load(f)
                
                # Update access time
                entry_info['last_accessed'] = time.time()
                entry_info['access_count'] = entry_info.get('access_count', 0) + 1
                self._save_index()
                
                return value
                
            except (OSError, pickle.PickleError):
                # Remove corrupted entry
                self.invalidate(key)
                return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in disk cache."""
        with self._lock:
            cache_file = self._make_filename(key)
            
            try:
                # Save to disk
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
                
                # Update index
                self.index[key] = {
                    'created_at': time.time(),
                    'last_accessed': time.time(),
                    'access_count': 0,
                    'size_bytes': cache_file.stat().st_size
                }
                
                self._save_index()
                self._enforce_size_limit()
                
            except (OSError, pickle.PickleError):
                pass
    
    def invalidate(self, key: str) -> None:
        """Remove entry from cache."""
        with self._lock:
            if key in self.index:
                cache_file = self._make_filename(key)
                cache_file.unlink(missing_ok=True)
                del self.index[key]
                self._save_index()
    
    def _enforce_size_limit(self) -> None:
        """Remove old entries if cache exceeds size limit."""
        total_size = sum(
            entry.get('size_bytes', 0) 
            for entry in self.index.values()
        )
        
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size <= max_size_bytes:
            return
        
        # Sort by last access time (oldest first)
        sorted_keys = sorted(
            self.index.keys(),
            key=lambda k: self.index[k].get('last_accessed', 0)
        )
        
        # Remove oldest entries until under limit
        for key in sorted_keys:
            if total_size <= max_size_bytes:
                break
            
            entry = self.index[key]
            total_size -= entry.get('size_bytes', 0)
            self.invalidate(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            for key in list(self.index.keys()):
                self.invalidate(key)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_size = sum(
                entry.get('size_bytes', 0) 
                for entry in self.index.values()
            )
            
            return {
                "entries": len(self.index),
                "total_size_mb": total_size / (1024 * 1024),
                "max_size_mb": self.max_size_mb,
                "utilization": total_size / (self.max_size_mb * 1024 * 1024)
            }

# Global cache instances
_memory_cache = LRUCache(max_size=1000, default_ttl=300)  # 5 minutes default TTL
_disk_cache = DiskCache(Path.home() / ".cache" / "super-agents", max_size_mb=100)

def cached(ttl: Optional[float] = None, disk: bool = False, 
           max_age: Optional[float] = None) -> Callable:
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (for memory cache)
        disk: Use disk cache instead of memory cache
        max_age: Maximum age for disk cache entries
    
    Example:
        @cached(ttl=60)  # Cache for 1 minute
        def expensive_operation(param):
            time.sleep(1)
            return f"result for {param}"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__module__}.{func.__name__}:{hash((args, tuple(kwargs.items())))}"
            
            if disk:
                # Try disk cache
                result = _disk_cache.get(cache_key, max_age=max_age)
                if result is not None:
                    return result
            else:
                # Try memory cache
                result = _memory_cache.get(cache_key)
                if result is not None:
                    return result
            
            # Cache miss - compute result
            result = func(*args, **kwargs)
            
            # Store in cache
            if disk:
                _disk_cache.put(cache_key, result)
            else:
                _memory_cache.put(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator

def cache_file_content(ttl: float = 300) -> Callable:
    """
    Cache file content with automatic invalidation on file changes.
    
    Args:
        ttl: Time to live in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(file_path: Union[str, Path], *args, **kwargs):
            file_path = Path(file_path)
            
            # Create cache key based on file path and mtime
            try:
                mtime = file_path.stat().st_mtime
                cache_key = f"file:{file_path}:{mtime}"
            except OSError:
                # File doesn't exist, don't cache
                return func(file_path, *args, **kwargs)
            
            # Try cache
            result = _memory_cache.get(cache_key)
            if result is not None:
                return result
            
            # Cache miss
            result = func(file_path, *args, **kwargs)
            _memory_cache.put(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator

@cached(ttl=60, disk=True)
def cached_subprocess_run(cmd: List[str], **kwargs) -> Tuple[int, str, str]:
    """Cached subprocess execution for idempotent commands."""
    import subprocess
    
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        **kwargs
    )
    
    return result.returncode, result.stdout, result.stderr

@cache_file_content(ttl=600)  # 10 minutes
def cached_file_read(file_path: Path) -> str:
    """Read file with caching."""
    return file_path.read_text()

@cache_file_content(ttl=600)
def cached_json_load(file_path: Path) -> Any:
    """Load JSON file with caching."""
    import json
    with open(file_path, 'r') as f:
        return json.load(f)

def invalidate_file_caches(file_path: Union[str, Path]) -> None:
    """Invalidate all caches for a specific file."""
    file_path = Path(file_path)
    
    # Clear memory cache entries for this file
    keys_to_remove = [
        key for key in _memory_cache.cache.keys()
        if key.startswith(f"file:{file_path}:")
    ]
    
    for key in keys_to_remove:
        _memory_cache.cache.pop(key, None)

def clear_all_caches() -> None:
    """Clear all caches."""
    _memory_cache.clear()
    _disk_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    return {
        "memory_cache": _memory_cache.stats(),
        "disk_cache": _disk_cache.stats()
    }