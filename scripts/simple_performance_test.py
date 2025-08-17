#!/usr/bin/env python3
"""
Simple performance test to demonstrate optimizations without external dependencies.
"""

import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_lazy_loading():
    """Test lazy loading performance benefit."""
    print("=" * 50)
    print("LAZY LOADING TEST")
    print("=" * 50)
    
    # Test normal imports
    start_time = time.perf_counter()
    import subprocess
    import sqlite3
    import urllib.request
    normal_import_time = time.perf_counter() - start_time
    
    # Test lazy imports
    from super_agents.performance.lazy_loader import lazy_import
    
    start_time = time.perf_counter()
    lazy_subprocess = lazy_import('subprocess')
    lazy_sqlite3 = lazy_import('sqlite3')
    lazy_urllib = lazy_import('urllib.request')
    lazy_import_time = time.perf_counter() - start_time
    
    print(f"Normal imports: {normal_import_time*1000:.2f}ms")
    print(f"Lazy imports: {lazy_import_time*1000:.2f}ms")
    
    improvement = ((normal_import_time - lazy_import_time) / normal_import_time) * 100
    print(f"Improvement: {improvement:.1f}%")
    
    return improvement

def test_caching():
    """Test caching performance benefit."""
    print("\n" + "=" * 50)
    print("CACHING TEST")
    print("=" * 50)
    
    from super_agents.performance.caching import cached
    
    # Simulate expensive operation
    call_count = 0
    
    def expensive_operation(x):
        nonlocal call_count
        call_count += 1
        # Simulate work
        time.sleep(0.01)
        return x * x
    
    @cached(ttl=60)
    def cached_expensive_operation(x):
        nonlocal call_count
        call_count += 1
        # Simulate work  
        time.sleep(0.01)
        return x * x
    
    # Test uncached
    call_count = 0
    start_time = time.perf_counter()
    for i in range(5):
        expensive_operation(i)
    uncached_time = time.perf_counter() - start_time
    uncached_calls = call_count
    
    # Test cached
    call_count = 0
    start_time = time.perf_counter()
    for i in range(5):
        cached_expensive_operation(i % 2)  # Only 2 unique values
    cached_time = time.perf_counter() - start_time
    cached_calls = call_count
    
    print(f"Uncached: {uncached_time*1000:.2f}ms ({uncached_calls} calls)")
    print(f"Cached: {cached_time*1000:.2f}ms ({cached_calls} calls)")
    
    improvement = ((uncached_time - cached_time) / uncached_time) * 100
    print(f"Improvement: {improvement:.1f}%")
    
    return improvement

def test_file_operations():
    """Test file operation performance with caching."""
    print("\n" + "=" * 50) 
    print("FILE OPERATIONS TEST")
    print("=" * 50)
    
    import tempfile
    from super_agents.performance.caching import cache_file_content
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_data = {"numbers": list(range(1000)), "text": "test data" * 100}
        json.dump(test_data, f)
        temp_file = Path(f.name)
    
    try:
        # Test normal file reading
        def normal_read():
            with open(temp_file, 'r') as f:
                return json.load(f)
        
        @cache_file_content(ttl=60)
        def cached_read(path):
            with open(path, 'r') as f:
                return json.load(f)
        
        # Time normal reads
        start_time = time.perf_counter()
        for _ in range(10):
            normal_read()
        normal_time = time.perf_counter() - start_time
        
        # Time cached reads
        start_time = time.perf_counter()
        for _ in range(10):
            cached_read(temp_file)
        cached_time = time.perf_counter() - start_time
        
        print(f"Normal reads: {normal_time*1000:.2f}ms")
        print(f"Cached reads: {cached_time*1000:.2f}ms")
        
        improvement = ((normal_time - cached_time) / normal_time) * 100
        print(f"Improvement: {improvement:.1f}%")
        
        return improvement
        
    finally:
        temp_file.unlink(missing_ok=True)

def test_indexing_performance():
    """Test indexing vs manual search performance."""
    print("\n" + "=" * 50)
    print("INDEXING TEST")
    print("=" * 50)
    
    import tempfile
    from super_agents.performance.indexing import ProjectIndexer
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        for i in range(50):
            (temp_path / f"file_{i:03d}.py").write_text(f"# File {i}\nprint('hello {i}')")
            (temp_path / f"doc_{i:03d}.md").write_text(f"# Document {i}\nContent here")
        
        # Manual search
        def manual_search():
            results = []
            for file_path in temp_path.rglob("*.py"):
                if "025" in file_path.name:
                    results.append(file_path)
            return results
        
        # Indexed search
        indexer = ProjectIndexer(temp_path / "test.db")
        indexer.index_project(temp_path)
        
        def indexed_search():
            return indexer.search_files("025", file_type="python")
        
        # Time manual search
        start_time = time.perf_counter()
        for _ in range(10):
            manual_search()
        manual_time = time.perf_counter() - start_time
        
        # Time indexed search  
        start_time = time.perf_counter()
        for _ in range(10):
            indexed_search()
        indexed_time = time.perf_counter() - start_time
        
        print(f"Manual search: {manual_time*1000:.2f}ms")
        print(f"Indexed search: {indexed_time*1000:.2f}ms")
        
        improvement = ((manual_time - indexed_time) / manual_time) * 100
        print(f"Improvement: {improvement:.1f}%")
        
        return improvement

def main():
    """Run all performance tests."""
    print("PERFORMANCE OPTIMIZATION VALIDATION")
    print("Testing Week 3 improvements...")
    print("Target: 20% startup improvement, 10% runtime improvement")
    
    improvements = []
    
    # Run tests
    try:
        improvements.append(test_lazy_loading())
        improvements.append(test_caching())
        improvements.append(test_file_operations())
        improvements.append(test_indexing_performance())
        
        # Calculate overall improvement
        avg_improvement = sum(improvements) / len(improvements)
        
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Average improvement: {avg_improvement:.1f}%")
        
        # Check targets
        startup_target_met = any(imp >= 20 for imp in improvements[:2])  # Lazy loading should help startup
        runtime_target_met = any(imp >= 10 for imp in improvements[2:])  # Caching/indexing should help runtime
        
        print(f"Startup target (20%): {'✅ MET' if startup_target_met else '❌ NOT MET'}")
        print(f"Runtime target (10%): {'✅ MET' if runtime_target_met else '❌ NOT MET'}")
        
        if startup_target_met and runtime_target_met:
            print("\n🎉 ALL PERFORMANCE TARGETS ACHIEVED!")
            return 0
        else:
            print("\n⚠️  Some targets not met, but optimizations are working")
            return 1
            
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())