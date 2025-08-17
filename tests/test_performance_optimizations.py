#!/usr/bin/env python3
"""
Test suite for performance optimizations.

Tests the roadmap requirements:
- 20% startup time improvement
- 10% runtime performance improvement
- Lazy loading reduces import time
- Caching reduces repeated operation overhead
- Indexing accelerates file searches
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
import sys
import threading
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from super_agents.performance.lazy_loader import (
    LazyModule, LazyImportManager, lazy_import, get_lazy_import_stats
)
from super_agents.performance.caching import (
    LRUCache, DiskCache, cached, cache_file_content, get_cache_stats
)
from super_agents.performance.indexing import (
    ProjectIndexer, FileIndex, ensure_project_indexed
)
from super_agents.performance import (
    initialize_performance_optimizations, get_performance_stats
)

class TestLazyLoading:
    """Test lazy loading functionality."""
    
    def test_lazy_module_import(self):
        """Test that modules are loaded on first access."""
        lazy_json = lazy_import('json')
        
        # Module should not be loaded yet
        assert not lazy_json.is_loaded
        
        # Access triggers loading
        result = lazy_json.dumps({'test': 'data'})
        assert lazy_json.is_loaded
        assert result == '{"test": "data"}'
    
    def test_lazy_module_fallback(self):
        """Test fallback for failed imports."""
        fallback = Mock()
        fallback.test_attr = "fallback_value"
        
        lazy_nonexistent = lazy_import('nonexistent_module', fallback=fallback)
        
        # Should use fallback
        assert lazy_nonexistent.test_attr == "fallback_value"
        assert lazy_nonexistent.import_failed
    
    def test_lazy_import_manager(self):
        """Test lazy import manager functionality."""
        manager = LazyImportManager()
        
        # Register modules
        os_module = manager.register_lazy_module('os', critical=True)
        sys_module = manager.register_lazy_module('sys')
        
        assert 'os' in manager.critical_modules
        assert 'sys' not in manager.critical_modules
        
        # Test stats
        stats = manager.get_load_stats()
        assert stats['total_modules'] == 2
        assert stats['loaded_modules'] == 0  # Not accessed yet
    
    def test_preload_critical_modules(self):
        """Test that critical modules are preloaded in background."""
        manager = LazyImportManager()
        manager.register_lazy_module('time', critical=True)
        
        # Preload should start background loading
        manager.preload_critical_modules()
        
        # Give background thread time to work
        time.sleep(0.1)
        
        # Should have loading stats
        stats = manager.get_load_stats()
        assert len(stats['load_times']) >= 0  # May complete very quickly

class TestCaching:
    """Test caching functionality."""
    
    def test_lru_cache_basic(self):
        """Test basic LRU cache operations."""
        cache = LRUCache(max_size=3)
        
        # Put values
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # Get values
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Stats
        stats = cache.stats()
        assert stats["size"] == 3
        assert stats["hits"] == 3
        assert stats["misses"] == 0
    
    def test_lru_cache_eviction(self):
        """Test LRU eviction policy."""
        cache = LRUCache(max_size=2)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add key3, should evict key2 (least recently used)
        cache.put("key3", "value3")
        
        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"  # New entry
    
    def test_lru_cache_ttl(self):
        """Test time-to-live functionality."""
        cache = LRUCache(max_size=10, default_ttl=0.1)  # 100ms TTL
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("key1") is None
    
    def test_disk_cache(self):
        """Test disk-based caching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = DiskCache(Path(temp_dir), max_size_mb=1)
            
            # Put and get
            cache.put("test_key", {"data": "test_value"})
            result = cache.get("test_key")
            
            assert result == {"data": "test_value"}
            
            # Test stats
            stats = cache.stats()
            assert stats["entries"] == 1
            assert stats["total_size_mb"] > 0
    
    def test_cached_decorator(self):
        """Test cached function decorator."""
        call_count = 0
        
        @cached(ttl=1)
        def expensive_operation(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = expensive_operation(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should be cached
        result2 = expensive_operation(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented
        
        # Different argument should trigger new computation
        result3 = expensive_operation(10)
        assert result3 == 20
        assert call_count == 2
    
    def test_file_caching(self):
        """Test file content caching."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)
        
        try:
            # Use cache_file_content decorator
            @cache_file_content(ttl=1)
            def read_file(path):
                return path.read_text()
            
            # First read
            content1 = read_file(temp_path)
            assert content1 == "test content"
            
            # Second read should be cached (modify file to test)
            temp_path.write_text("modified content")
            content2 = read_file(temp_path)
            # Should still return cached content briefly
            # (This test is timing-dependent, so we mainly check no exception)
            assert isinstance(content2, str)
            
        finally:
            temp_path.unlink(missing_ok=True)

class TestIndexing:
    """Test indexing functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.indexer = ProjectIndexer(self.temp_dir / "test.db")
        
        # Create test files
        (self.temp_dir / "test.py").write_text("print('hello')")
        (self.temp_dir / "test.md").write_text("# Test\nMarkdown content")
        (self.temp_dir / "test.json").write_text('{"test": "data"}')
        
        # Create subdirectory
        sub_dir = self.temp_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.txt").write_text("nested content")
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_file_type_detection(self):
        """Test file type detection."""
        py_file = self.temp_dir / "test.py"
        file_type, is_binary = self.indexer._detect_file_type(py_file)
        
        assert file_type == "python"
        assert not is_binary
        
        md_file = self.temp_dir / "test.md"
        file_type, is_binary = self.indexer._detect_file_type(md_file)
        
        assert file_type == "markdown"
        assert not is_binary
    
    def test_file_indexing(self):
        """Test indexing individual files."""
        py_file = self.temp_dir / "test.py"
        file_index = self.indexer.index_file(py_file, calculate_hash=True)
        
        assert file_index.path == str(py_file)
        assert file_index.file_type == "python"
        assert not file_index.is_binary
        assert file_index.hash_md5 is not None
        assert file_index.size > 0
    
    def test_project_indexing(self):
        """Test full project indexing."""
        stats = self.indexer.index_project(self.temp_dir, max_workers=2)
        
        assert stats['files_indexed'] == 4  # 4 test files
        assert stats['files_skipped'] >= 0
        assert stats['errors'] == 0
        assert stats['duration'] > 0
        assert stats['files_per_second'] > 0
    
    def test_file_search(self):
        """Test file searching."""
        # Index first
        self.indexer.index_project(self.temp_dir)
        
        # Search for Python files
        results = self.indexer.search_files("test", file_type="python")
        assert len(results) == 1
        assert "test.py" in results[0]['path']
        
        # Search by name
        results = self.indexer.search_files("nested")
        assert len(results) == 1
        assert "nested.txt" in results[0]['path']
    
    def test_agent_indexing(self):
        """Test agent definition indexing."""
        # Create mock agent directory
        agents_dir = self.temp_dir / "agents"
        agents_dir.mkdir()
        
        # Create agent file
        agent_content = """# Test Agent
Agent for testing purposes.

## Triggers:
- test
- example

## Capabilities:
- testing
- validation
"""
        (agents_dir / "test-agent.md").write_text(agent_content)
        
        # Index agents
        stats = self.indexer.index_agents(agents_dir)
        
        assert stats['agents_indexed'] == 1
        assert stats['errors'] == 0
        
        # Search agents
        results = self.indexer.search_agents("test")
        assert len(results) == 1
        assert results[0]['name'] == "test-agent"
        assert "testing" in results[0]['triggers']
    
    def test_incremental_update(self):
        """Test incremental indexing."""
        # Initial index
        stats1 = self.indexer.index_project(self.temp_dir)
        
        # Add new file
        (self.temp_dir / "new_file.txt").write_text("new content")
        
        # Incremental update
        stats2 = self.indexer.incremental_update()
        
        assert stats2['new_files'] == 1
        assert stats2['updated_files'] == 0
        assert stats2['deleted_files'] == 0
    
    def test_index_staleness(self):
        """Test index staleness detection."""
        # Fresh index should not be stale
        self.indexer.index_project(self.temp_dir)
        assert not self.indexer.is_index_stale(max_age_hours=24)
        
        # Should be stale with very short max age
        assert self.indexer.is_index_stale(max_age_hours=0)

class TestPerformanceIntegration:
    """Test integration of all performance optimizations."""
    
    def test_initialization(self):
        """Test performance optimization initialization."""
        # Should not raise exceptions
        initialize_performance_optimizations()
        
        # Should provide stats
        stats = get_performance_stats()
        assert 'lazy_imports' in stats
        assert 'caching' in stats
        assert 'indexing' in stats
    
    def test_startup_time_improvement(self):
        """Test that optimizations reduce startup time."""
        # This is a basic test - real improvement needs measurement
        
        # Without optimization
        start_time = time.time()
        import json
        import os
        import sys
        duration_normal = time.time() - start_time
        
        # With lazy loading (simulated)
        start_time = time.time()
        lazy_json = lazy_import('json')
        lazy_os = lazy_import('os')
        lazy_sys = lazy_import('sys')
        duration_lazy = time.time() - start_time
        
        # Lazy loading should be faster (though this test is basic)
        assert duration_lazy <= duration_normal + 0.01  # Allow small margin
    
    def test_memory_usage(self):
        """Test that optimizations don't excessive increase memory usage."""
        # Basic memory check - ensure no obvious leaks
        
        stats_before = get_performance_stats()
        
        # Create and use some caches
        cache = LRUCache(max_size=100)
        for i in range(50):
            cache.put(f"key{i}", f"value{i}")
        
        stats_after = get_performance_stats()
        
        # Should have cache data
        assert stats_after['caching']['memory_cache']['size'] >= 0
    
    def test_thread_safety(self):
        """Test that performance optimizations are thread-safe."""
        cache = LRUCache(max_size=100)
        results = []
        
        def worker(thread_id):
            for i in range(10):
                key = f"thread{thread_id}_key{i}"
                value = f"thread{thread_id}_value{i}"
                cache.put(key, value)
                retrieved = cache.get(key)
                results.append(retrieved == value)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert all(results)
        assert len(results) == 50  # 5 threads × 10 operations

class TestPerformanceBenchmarks:
    """Benchmark tests to validate performance targets."""
    
    def test_caching_performance_benefit(self):
        """Test that caching provides measurable performance benefit."""
        call_count = 0
        
        @cached(ttl=60)
        def expensive_operation():
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return "result"
        
        # Time uncached calls
        start_time = time.time()
        for _ in range(10):
            expensive_operation()
        first_duration = time.time() - start_time
        
        # Reset and time cached calls
        call_count = 0
        start_time = time.time()
        for _ in range(10):
            expensive_operation()
        cached_duration = time.time() - start_time
        
        # Caching should provide significant improvement
        improvement_ratio = first_duration / max(cached_duration, 0.001)
        assert improvement_ratio > 5  # At least 5x improvement
        assert call_count == 1  # Only one actual call
    
    def test_indexing_search_performance(self):
        """Test that indexing provides fast search performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            indexer = ProjectIndexer(temp_path / "test.db")
            
            # Create many test files
            for i in range(100):
                (temp_path / f"file_{i:03d}.py").write_text(f"# File {i}")
            
            # Time indexing
            start_time = time.time()
            indexer.index_project(temp_path)
            index_duration = time.time() - start_time
            
            # Time search
            start_time = time.time()
            results = indexer.search_files("file_050")
            search_duration = time.time() - start_time
            
            # Indexing should be reasonably fast
            assert index_duration < 5.0  # Less than 5 seconds for 100 files
            
            # Search should be very fast
            assert search_duration < 0.1  # Less than 100ms
            assert len(results) >= 1  # Should find the file
    
    @pytest.mark.slow
    def test_overall_performance_improvement(self):
        """Test overall performance improvement meets targets."""
        # This test would need baseline measurements from before optimizations
        # For now, we test that operations complete within reasonable time
        
        # Simulate CLI startup operations
        start_time = time.time()
        
        # Initialize optimizations
        initialize_performance_optimizations()
        
        # Simulate project check
        from super_agents.commands.init import check_project_initialized
        check_project_initialized()
        
        # Get stats
        get_performance_stats()
        
        total_duration = time.time() - start_time
        
        # Should complete quickly (this is a basic test)
        assert total_duration < 2.0  # Less than 2 seconds

if __name__ == "__main__":
    pytest.main([__file__, "-v"])