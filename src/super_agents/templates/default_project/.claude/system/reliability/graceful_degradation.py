"""
Graceful degradation for optional dependencies
"""

import functools
import importlib
from typing import Any, Optional, Callable


def optional_import(module_name: str, fallback: Any = None) -> Any:
    """
    Import a module with graceful degradation
    
    Args:
        module_name: Name of module to import
        fallback: Value to return if import fails
        
    Returns:
        Imported module or fallback value
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return fallback


def with_fallback(fallback_return: Any = None):
    """
    Decorator to provide fallback for functions that might fail
    
    Args:
        fallback_return: Value to return if function fails
        
    Returns:
        Decorated function with fallback behavior
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ImportError, ModuleNotFoundError):
                return fallback_return
        return wrapper
    return decorator


# Example usage for sentence-transformers graceful degradation
sentence_transformers = optional_import('sentence_transformers', fallback=None)

@with_fallback(fallback_return="Feature not available - sentence-transformers not installed")
def create_embeddings(texts: list) -> Any:
    """Create embeddings with graceful degradation"""
    if sentence_transformers is None:
        raise ImportError("sentence-transformers not available")
    
    model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(texts)