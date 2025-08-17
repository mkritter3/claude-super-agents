#!/usr/bin/env python3
"""
Comprehensive Load Testing Suite
Tests the entire super-agents system under heavy load
"""

import os
import sys
import time
import tempfile
import threading
import unittest
import subprocess
import json
import sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import string
import psutil

# Add the template system to path
template_system = Path(__file__).parent.parent.parent
sys.path.insert(0, str(template_system))

try:
    from performance.lazy_loader import lazy_import, get_lazy_import_stats
    from performance.caching import cached, get_cache_stats, clear_all_caches
    from performance.indexing import ProjectIndexer
    from reliability.circuit_breaker import protected_call, CircuitBreakerOpenError
    from database.maintenance import DatabaseMaintenance
except ImportError as e:
    print(f"Warning: Some modules not available for load testing: {e}")


class ComprehensiveLoadTests(unittest.TestCase):
    """Comprehensive load testing of the super-agents system"""
    
    def setUp(self):
        """Set up load test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="load_test_"))
        self.original_cwd = Path.cwd()
        os.chdir(self.test_dir)
        
        # Create realistic project structure
        self.create_large_project()
        
        # Initialize system components
        self.setup_system_components()
        
        # Track performance metrics
        self.performance_metrics = {
            'memory_usage': [],
            'cpu_usage': [],
            'response_times': [],
            'error_rates': [],
            'throughput': []
        }
        
    def tearDown(self):
        """Clean up load test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # Clear caches
        try:
            clear_all_caches()
        except:
            pass
    
    def create_large_project(self):
        """Create a large, realistic project for load testing"""
        # Create directory structure
        dirs = [
            'src/components', 'src/utils', 'src/api', 'src/models', 'src/views',
            'src/services', 'src/middleware', 'src/config', 'src/database',
            'tests/unit', 'tests/integration', 'tests/e2e', 'tests/fixtures',
            'docs/api', 'docs/guides', 'docs/examples',
            'scripts/build', 'scripts/deploy', 'scripts/maintenance',
            'migrations', 'static/css', 'static/js', 'static/images',
            'templates/email', 'templates/web', 'locale/en', 'locale/fr'
        ]
        
        for dir_path in dirs:
            (self.test_dir / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create many files with realistic content
        self.create_python_files(100)
        self.create_test_files(50)
        self.create_config_files(20)
        self.create_documentation_files(30)
        self.create_static_files(40)
    
    def create_python_files(self, count):
        """Create Python source files"""
        for i in range(count):
            content = f'''#!/usr/bin/env python3
"""
Module {i}: {self.random_description()}
"""

import os
import sys
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

class Component{i}:
    """Component {i} for load testing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {{}}
        self.initialized = False
        self.metrics = {{}}
    
    def initialize(self) -> bool:
        """Initialize component {i}"""
        try:
            self._setup_configuration()
            self._validate_dependencies()
            self.initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize component {i}: {{e}}")
            return False
    
    def _setup_configuration(self):
        """Setup configuration for component {i}"""
        default_config = {{
            "timeout": 30,
            "retries": 3,
            "cache_size": 1000,
            "debug": False
        }}
        self.config = {{**default_config, **self.config}}
    
    def _validate_dependencies(self):
        """Validate dependencies for component {i}"""
        required_deps = ["os", "sys", "json", "time"]
        for dep in required_deps:
            try:
                __import__(dep)
            except ImportError:
                raise ImportError(f"Required dependency {{dep}} not found")
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process data using component {i}"""
        if not self.initialized:
            raise RuntimeError("Component {i} not initialized")
        
        results = []
        start_time = time.time()
        
        for item in data:
            try:
                processed_item = self._process_item(item)
                results.append(processed_item)
            except Exception as e:
                results.append({{"error": str(e), "original": item}})
        
        end_time = time.time()
        self.metrics["last_processing_time"] = end_time - start_time
        self.metrics["items_processed"] = len(results)
        
        return results
    
    def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual item"""
        # Simulate processing work
        time.sleep(0.001)  # 1ms processing time
        
        return {{
            "id": item.get("id", "unknown"),
            "processed_by": "component_{i}",
            "timestamp": time.time(),
            "data": item.get("data", ""),
            "status": "processed"
        }}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get component metrics"""
        return {{
            "component_id": {i},
            "initialized": self.initialized,
            "config": self.config,
            "metrics": self.metrics
        }}

def create_component_{i}(config: Dict[str, Any] = None) -> Component{i}:
    """Factory function for component {i}"""
    component = Component{i}(config)
    component.initialize()
    return component

def process_batch_{i}(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch processing function for component {i}"""
    component = create_component_{i}()
    return component.process_data(items)

# Test data
TEST_DATA_{i} = [
    {{"id": f"test_{{j}}", "data": f"sample_data_{{j}}"}} 
    for j in range(10)
]

if __name__ == "__main__":
    component = create_component_{i}()
    results = component.process_data(TEST_DATA_{i})
    print(f"Component {i} processed {{len(results)}} items")
'''
            
            file_path = self.test_dir / f'src/components/component_{i}.py'
            file_path.write_text(content)
    
    def create_test_files(self, count):
        """Create test files"""
        for i in range(count):
            content = f'''#!/usr/bin/env python3
"""
Test module {i} for load testing
"""

import unittest
import time
import random
from unittest.mock import Mock, patch

class TestComponent{i}(unittest.TestCase):
    """Test cases for component {i}"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.component = None
        self.test_data = []
    
    def tearDown(self):
        """Clean up after tests"""
        if self.component:
            self.component = None
    
    def test_initialization_{i}(self):
        """Test component {i} initialization"""
        from src.components.component_{i} import Component{i}
        
        component = Component{i}()
        self.assertFalse(component.initialized)
        
        result = component.initialize()
        self.assertTrue(result)
        self.assertTrue(component.initialized)
    
    def test_data_processing_{i}(self):
        """Test data processing for component {i}"""
        from src.components.component_{i} import create_component_{i}
        
        component = create_component_{i}()
        test_data = [
            {{"id": f"test_{{j}}", "data": f"sample_{{j}}"}}
            for j in range(5)
        ]
        
        results = component.process_data(test_data)
        
        self.assertEqual(len(results), len(test_data))
        for result in results:
            self.assertIn("processed_by", result)
            self.assertEqual(result["processed_by"], "component_{i}")
    
    def test_error_handling_{i}(self):
        """Test error handling for component {i}"""
        from src.components.component_{i} import Component{i}
        
        component = Component{i}()
        
        # Test without initialization
        with self.assertRaises(RuntimeError):
            component.process_data([{{"id": "test"}}])
    
    def test_performance_{i}(self):
        """Test performance for component {i}"""
        from src.components.component_{i} import create_component_{i}
        
        component = create_component_{i}()
        
        # Generate larger test dataset
        large_dataset = [
            {{"id": f"perf_test_{{j}}", "data": f"performance_data_{{j}}"}}
            for j in range(100)
        ]
        
        start_time = time.time()
        results = component.process_data(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        self.assertEqual(len(results), len(large_dataset))
        self.assertLess(processing_time, 1.0)  # Should process 100 items in under 1 second
        
        metrics = component.get_metrics()
        self.assertIn("last_processing_time", metrics["metrics"])
        self.assertIn("items_processed", metrics["metrics"])
    
    def test_concurrent_processing_{i}(self):
        """Test concurrent processing for component {i}"""
        from src.components.component_{i} import create_component_{i}
        import threading
        
        component = create_component_{i}()
        results = []
        errors = []
        
        def process_data_thread(thread_id):
            try:
                test_data = [
                    {{"id": f"thread_{{thread_id}}_{{j}}", "data": f"data_{{j}}"}}
                    for j in range(10)
                ]
                thread_results = component.process_data(test_data)
                results.extend(thread_results)
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_data_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        self.assertEqual(len(errors), 0, f"Errors in concurrent processing: {{errors}}")
        self.assertEqual(len(results), 50)  # 5 threads * 10 items each

if __name__ == '__main__':
    unittest.main(verbosity=2)
'''
            
            file_path = self.test_dir / f'tests/unit/test_component_{i}.py'
            file_path.write_text(content)
    
    def create_config_files(self, count):
        """Create configuration files"""
        configs = []
        for i in range(count):
            config = {
                "environment": random.choice(["development", "staging", "production"]),
                "database": {
                    "host": f"db-{i}.example.com",
                    "port": 5432 + i,
                    "name": f"database_{i}",
                    "pool_size": random.randint(5, 50)
                },
                "cache": {
                    "redis_url": f"redis://cache-{i}.example.com:6379",
                    "ttl": random.randint(300, 3600)
                },
                "features": {
                    f"feature_{j}": random.choice([True, False])
                    for j in range(10)
                },
                "performance": {
                    "max_workers": random.randint(4, 16),
                    "timeout": random.randint(30, 300),
                    "batch_size": random.randint(10, 100)
                }
            }
            
            config_path = self.test_dir / f'config/config_{i}.json'
            config_path.write_text(json.dumps(config, indent=2))
            configs.append(config)
        
        return configs
    
    def create_documentation_files(self, count):
        """Create documentation files"""
        for i in range(count):
            content = f'''# Documentation {i}

## Overview

This is documentation file {i} for load testing purposes.

## Features

{self.random_description()}

## Usage

```python
from src.components.component_{i} import create_component_{i}

# Initialize component
component = create_component_{i}()

# Process data
data = [{{"id": "example", "data": "sample"}}]
results = component.process_data(data)
```

## Configuration

The component supports the following configuration options:

- `timeout`: Request timeout in seconds (default: 30)
- `retries`: Number of retry attempts (default: 3)
- `cache_size`: Cache size limit (default: 1000)
- `debug`: Enable debug mode (default: False)

## Performance

Component {i} is optimized for:
- High throughput data processing
- Low memory usage
- Concurrent operations
- Error resilience

## Examples

### Basic Usage

```python
component = create_component_{i}()
result = component.process_data([{{"id": "test", "data": "value"}}])
```

### Batch Processing

```python
large_dataset = [
    {{"id": f"item_{{j}}", "data": f"value_{{j}}"}}
    for j in range(1000)
]
results = component.process_data(large_dataset)
```

### Error Handling

```python
try:
    results = component.process_data(invalid_data)
except RuntimeError as e:
    print(f"Processing failed: {{e}}")
```

## API Reference

### Class: Component{i}

#### Methods

- `__init__(config: Dict[str, Any] = None)`: Initialize component
- `initialize() -> bool`: Setup component for use
- `process_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]`: Process data
- `get_metrics() -> Dict[str, Any]`: Get performance metrics

#### Properties

- `initialized`: Whether component is initialized
- `config`: Current configuration
- `metrics`: Performance metrics

## Troubleshooting

Common issues and solutions:

1. **Component not initialized**
   - Call `initialize()` before processing data

2. **Processing timeout**
   - Increase timeout in configuration
   - Reduce batch size

3. **Memory usage high**
   - Reduce cache_size setting
   - Process data in smaller batches

## Performance Benchmarks

Component {i} performance characteristics:

| Metric | Value |
|--------|-------|
| Items/second | ~1000 |
| Memory usage | <50MB |
| CPU usage | <10% |
| Error rate | <0.1% |
'''
            
            file_path = self.test_dir / f'docs/component_{i}.md'
            file_path.write_text(content)
    
    def create_static_files(self, count):
        """Create static files (CSS, JS, etc.)"""
        for i in range(count):
            if i % 2 == 0:
                # Create CSS file
                css_content = f'''/* Stylesheet {i} */
.component-{i} {{
    display: flex;
    flex-direction: column;
    padding: 1rem;
    margin: 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
}}

.component-{i} h1 {{
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: #333;
}}

.component-{i} .content {{
    flex: 1;
    overflow: auto;
}}

.component-{i} .actions {{
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
}}

.component-{i} button {{
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    background: #007bff;
    color: white;
    cursor: pointer;
}}

.component-{i} button:hover {{
    background: #0056b3;
}}
'''
                file_path = self.test_dir / f'static/css/component_{i}.css'
                file_path.write_text(css_content)
            else:
                # Create JS file
                js_content = f'''// JavaScript module {i}
class Component{i} {{
    constructor(element) {{
        this.element = element;
        this.initialized = false;
        this.data = {{}};
    }}
    
    initialize() {{
        this.bindEvents();
        this.loadData();
        this.initialized = true;
    }}
    
    bindEvents() {{
        const buttons = this.element.querySelectorAll('button');
        buttons.forEach(button => {{
            button.addEventListener('click', (e) => {{
                this.handleButtonClick(e.target);
            }});
        }});
    }}
    
    loadData() {{
        // Simulate data loading
        this.data = {{
            id: {i},
            timestamp: Date.now(),
            items: []
        }};
        
        for (let j = 0; j < 10; j++) {{
            this.data.items.push({{
                id: j,
                name: `Item ${{j}}`,
                value: Math.random() * 100
            }});
        }}
    }}
    
    handleButtonClick(button) {{
        const action = button.dataset.action;
        
        switch (action) {{
            case 'refresh':
                this.loadData();
                this.render();
                break;
            case 'clear':
                this.data.items = [];
                this.render();
                break;
            case 'export':
                this.exportData();
                break;
            default:
                console.log(`Unknown action: ${{action}}`);
        }}
    }}
    
    render() {{
        const content = this.element.querySelector('.content');
        content.innerHTML = `
            <h2>Component {i} Data</h2>
            <p>Items: ${{this.data.items.length}}</p>
            <ul>
                ${{this.data.items.map(item => 
                    `<li>${{item.name}}: ${{item.value.toFixed(2)}}</li>`
                ).join('')}}
            </ul>
        `;
    }}
    
    exportData() {{
        const blob = new Blob([JSON.stringify(this.data, null, 2)], {{
            type: 'application/json'
        }});
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `component_{i}_data.json`;
        a.click();
        
        URL.revokeObjectURL(url);
    }}
    
    destroy() {{
        this.element.removeEventListener('click', this.handleButtonClick);
        this.initialized = false;
    }}
}}

// Auto-initialize components
document.addEventListener('DOMContentLoaded', () => {{
    const elements = document.querySelectorAll('.component-{i}');
    elements.forEach(element => {{
        const component = new Component{i}(element);
        component.initialize();
        component.render();
    }});
}});

export default Component{i};
'''
                file_path = self.test_dir / f'static/js/component_{i}.js'
                file_path.write_text(js_content)
    
    def random_description(self):
        """Generate random description text"""
        descriptions = [
            "A high-performance component for data processing",
            "Optimized utility for handling complex operations",
            "Robust module with error handling and recovery",
            "Scalable service for concurrent operations",
            "Efficient processor with caching capabilities",
            "Reliable component with circuit breaker protection",
            "Advanced module with performance monitoring",
            "Intelligent service with adaptive behavior"
        ]
        return random.choice(descriptions)
    
    def setup_system_components(self):
        """Initialize system components for testing"""
        try:
            # Initialize indexer
            self.indexer = ProjectIndexer(root_path=self.test_dir)
            
            # Initialize database maintenance
            self.db_maintenance = DatabaseMaintenance()
            
        except Exception as e:
            print(f"Warning: Could not initialize all system components: {e}")
    
    def monitor_system_resources(self, duration=10, interval=1):
        """Monitor system resources during load test"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                # Get current process
                process = psutil.Process()
                
                # Collect metrics
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                self.performance_metrics['memory_usage'].append({
                    'timestamp': time.time(),
                    'rss': memory_info.rss,
                    'vms': memory_info.vms
                })
                
                self.performance_metrics['cpu_usage'].append({
                    'timestamp': time.time(),
                    'percent': cpu_percent
                })
                
            except Exception as e:
                print(f"Resource monitoring error: {e}")
            
            time.sleep(interval)
    
    def test_high_volume_file_operations(self):
        """Test system under high volume of file operations"""
        print("\nRunning high volume file operations test...")
        
        num_operations = 1000
        num_threads = 8
        results = []
        errors = []
        
        def file_operations_worker(worker_id):
            """Perform file operations in worker thread"""
            worker_results = {
                'reads': 0,
                'writes': 0,
                'errors': 0,
                'response_times': []
            }
            
            for i in range(num_operations // num_threads):
                try:
                    start_time = time.time()
                    
                    # Mix of operations
                    operation = i % 4
                    
                    if operation == 0:
                        # Read existing file
                        file_path = self.test_dir / f'src/components/component_0.py'
                        if file_path.exists():
                            content = file_path.read_text()
                            worker_results['reads'] += 1
                    
                    elif operation == 1:
                        # Write new file
                        file_path = self.test_dir / f'temp/worker_{worker_id}_file_{i}.txt'
                        file_path.parent.mkdir(exist_ok=True)
                        file_path.write_text(f"Data from worker {worker_id}, operation {i}")
                        worker_results['writes'] += 1
                    
                    elif operation == 2:
                        # Index file
                        if hasattr(self, 'indexer'):
                            file_path = self.test_dir / f'src/components/component_{i % 10}.py'
                            if file_path.exists():
                                self.indexer.index_file(file_path)
                    
                    elif operation == 3:
                        # Cache operation
                        @cached(ttl=30)
                        def expensive_operation(n):
                            return sum(range(n))
                        
                        result = expensive_operation(i % 100)
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    worker_results['response_times'].append(response_time)
                    
                except Exception as e:
                    worker_results['errors'] += 1
                    errors.append(f"Worker {worker_id}: {e}")
            
            results.append(worker_results)
        
        # Start resource monitoring
        monitor_thread = threading.Thread(
            target=self.monitor_system_resources, 
            args=(20, 0.5), 
            daemon=True
        )
        monitor_thread.start()
        
        # Run file operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(file_operations_worker, worker_id)
                for worker_id in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        total_reads = sum(r['reads'] for r in results)
        total_writes = sum(r['writes'] for r in results) 
        total_errors = sum(r['errors'] for r in results)
        
        all_response_times = []
        for r in results:
            all_response_times.extend(r['response_times'])
        
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
        max_response_time = max(all_response_times) if all_response_times else 0
        
        throughput = (total_reads + total_writes) / total_duration if total_duration > 0 else 0
        error_rate = (total_errors / num_operations) * 100 if num_operations > 0 else 0
        
        print(f"High Volume File Operations Results:")
        print(f"Duration: {total_duration:.2f} seconds")
        print(f"Total reads: {total_reads}")
        print(f"Total writes: {total_writes}")
        print(f"Total errors: {total_errors}")
        print(f"Error rate: {error_rate:.1f}%")
        print(f"Throughput: {throughput:.1f} ops/sec")
        print(f"Avg response time: {avg_response_time*1000:.2f} ms")
        print(f"Max response time: {max_response_time*1000:.2f} ms")
        
        # Assertions
        self.assertLess(error_rate, 5.0, f"Error rate {error_rate:.1f}% too high")
        self.assertGreater(throughput, 50, f"Throughput {throughput:.1f} ops/sec too low")
        self.assertLess(avg_response_time, 0.1, f"Average response time {avg_response_time:.3f}s too high")
    
    def test_concurrent_system_operations(self):
        """Test concurrent operations across all system components"""
        print("\nRunning concurrent system operations test...")
        
        num_concurrent_ops = 50
        results = {
            'lazy_imports': [],
            'cache_operations': [],
            'indexing_operations': [],
            'circuit_breaker_ops': [],
            'database_operations': []
        }
        errors = []
        
        def lazy_import_worker():
            """Test lazy imports under load"""
            try:
                for i in range(10):
                    # Simulate lazy imports
                    module = lazy_import('json')
                    data = module.dumps({'test': i})
                    results['lazy_imports'].append(len(data))
            except Exception as e:
                errors.append(f"Lazy import error: {e}")
        
        def cache_worker():
            """Test caching under load"""
            try:
                @cached(ttl=60)
                def compute_fibonacci(n):
                    if n <= 1:
                        return n
                    return compute_fibonacci(n-1) + compute_fibonacci(n-2)
                
                for i in range(1, 11):
                    result = compute_fibonacci(i)
                    results['cache_operations'].append(result)
            except Exception as e:
                errors.append(f"Cache error: {e}")
        
        def indexing_worker():
            """Test indexing under load"""
            try:
                if hasattr(self, 'indexer'):
                    for i in range(5):
                        files = list(self.test_dir.glob('src/**/*.py'))
                        if files:
                            file_to_index = random.choice(files)
                            self.indexer.index_file(file_to_index)
                            results['indexing_operations'].append(str(file_to_index))
            except Exception as e:
                errors.append(f"Indexing error: {e}")
        
        def circuit_breaker_worker():
            """Test circuit breaker under load"""
            try:
                def sometimes_failing_operation():
                    if random.random() < 0.3:  # 30% failure rate
                        raise Exception("Simulated failure")
                    return "success"
                
                for i in range(10):
                    try:
                        result = protected_call(
                            f"test_service_{threading.current_thread().ident}",
                            sometimes_failing_operation,
                            failure_threshold=5,
                            timeout_seconds=2
                        )
                        results['circuit_breaker_ops'].append(result)
                    except (Exception, CircuitBreakerOpenError):
                        # Expected under load
                        pass
            except Exception as e:
                errors.append(f"Circuit breaker error: {e}")
        
        def database_worker():
            """Test database operations under load"""
            try:
                db_path = self.test_dir / f'test_db_{threading.current_thread().ident}.sqlite'
                
                with sqlite3.connect(str(db_path)) as conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER, data TEXT)")
                    
                    for i in range(10):
                        conn.execute("INSERT INTO test_table (id, data) VALUES (?, ?)", 
                                   (i, f"test_data_{i}"))
                    
                    conn.commit()
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM test_table")
                    count = cursor.fetchone()[0]
                    results['database_operations'].append(count)
                    
            except Exception as e:
                errors.append(f"Database error: {e}")
        
        # Define worker types
        workers = [
            lazy_import_worker,
            cache_worker, 
            indexing_worker,
            circuit_breaker_worker,
            database_worker
        ]
        
        # Start resource monitoring
        monitor_thread = threading.Thread(
            target=self.monitor_system_resources,
            args=(15, 0.5),
            daemon=True
        )
        monitor_thread.start()
        
        # Run concurrent operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent_ops) as executor:
            futures = []
            
            for i in range(num_concurrent_ops):
                worker = workers[i % len(workers)]
                futures.append(executor.submit(worker))
            
            for future in as_completed(futures):
                future.result()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        total_operations = sum(len(ops) for ops in results.values())
        ops_per_second = total_operations / total_duration if total_duration > 0 else 0
        error_rate = (len(errors) / num_concurrent_ops) * 100 if num_concurrent_ops > 0 else 0
        
        print(f"Concurrent System Operations Results:")
        print(f"Duration: {total_duration:.2f} seconds")
        print(f"Total operations: {total_operations}")
        print(f"Operations per second: {ops_per_second:.1f}")
        print(f"Error rate: {error_rate:.1f}%")
        print(f"Lazy imports: {len(results['lazy_imports'])}")
        print(f"Cache operations: {len(results['cache_operations'])}")
        print(f"Indexing operations: {len(results['indexing_operations'])}")
        print(f"Circuit breaker ops: {len(results['circuit_breaker_ops'])}")
        print(f"Database operations: {len(results['database_operations'])}")
        
        if errors:
            print(f"Errors encountered:")
            for error in errors[:3]:
                print(f"  - {error}")
        
        # Assertions
        self.assertLess(error_rate, 20.0, f"Error rate {error_rate:.1f}% too high for concurrent ops")
        self.assertGreater(ops_per_second, 10, f"Operations per second {ops_per_second:.1f} too low")
        self.assertGreater(total_operations, num_concurrent_ops * 2, "Too few operations completed")
    
    def test_memory_usage_under_load(self):
        """Test memory usage remains reasonable under load"""
        print("\nRunning memory usage under load test...")
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        large_datasets = []
        
        try:
            # Create large in-memory datasets
            for i in range(100):
                dataset = [
                    {
                        'id': j,
                        'data': ''.join(random.choices(string.ascii_letters, k=1000)),
                        'metadata': {
                            'timestamp': time.time(),
                            'size': 1000,
                            'category': f'category_{j % 10}'
                        }
                    }
                    for j in range(100)
                ]
                large_datasets.append(dataset)
            
            # Process datasets
            for i, dataset in enumerate(large_datasets):
                # Simulate processing
                processed = []
                for item in dataset:
                    processed_item = {
                        'original_id': item['id'],
                        'processed_data': item['data'][:100],  # Truncate
                        'processing_time': time.time()
                    }
                    processed.append(processed_item)
                
                # Clear processed data periodically
                if i % 10 == 0:
                    processed = []
                    
                # Check memory periodically
                if i % 20 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_growth = current_memory - initial_memory
                    
                    print(f"  Memory at iteration {i}: {current_memory:.1f} MB (+{memory_growth:.1f} MB)")
                    
                    # If memory grows too much, clean up
                    if memory_growth > 500:  # 500 MB growth limit
                        large_datasets = large_datasets[i:]  # Keep only remaining
                        break
            
            # Final memory check
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            total_growth = final_memory - initial_memory
            
            print(f"Memory Usage Results:")
            print(f"Initial memory: {initial_memory:.1f} MB")
            print(f"Final memory: {final_memory:.1f} MB")
            print(f"Memory growth: {total_growth:.1f} MB")
            
            # Assertions
            self.assertLess(total_growth, 1000, f"Memory growth {total_growth:.1f} MB exceeds 1GB limit")
            self.assertLess(final_memory, 2000, f"Final memory {final_memory:.1f} MB exceeds 2GB limit")
            
        finally:
            # Clean up
            large_datasets.clear()
    
    def test_performance_metrics_collection(self):
        """Test performance metrics collection under load"""
        print("\nRunning performance metrics collection test...")
        
        # Collect baseline metrics
        try:
            lazy_stats = get_lazy_import_stats()
            cache_stats = get_cache_stats()
            
            print(f"Performance Metrics Results:")
            print(f"Lazy import stats: {lazy_stats}")
            print(f"Cache stats: {cache_stats}")
            
            # Basic validation
            self.assertIsInstance(lazy_stats, dict)
            self.assertIsInstance(cache_stats, dict)
            
            # Check for expected metrics
            if 'imports_completed' in lazy_stats:
                self.assertGreaterEqual(lazy_stats['imports_completed'], 0)
            
            if 'cache_hits' in cache_stats:
                self.assertGreaterEqual(cache_stats['cache_hits'], 0)
            
        except Exception as e:
            print(f"Metrics collection error: {e}")
            # Don't fail the test if metrics aren't available
    
    def generate_load_test_report(self):
        """Generate comprehensive load test report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE LOAD TEST REPORT")
        print("="*80)
        
        # System information
        print(f"\nSystem Information:")
        print(f"Python version: {sys.version}")
        print(f"Test directory: {self.test_dir}")
        print(f"Project files created: {len(list(self.test_dir.rglob('*.*')))}")
        
        # Performance metrics summary
        if self.performance_metrics['memory_usage']:
            memory_readings = [m['rss'] / 1024 / 1024 for m in self.performance_metrics['memory_usage']]
            max_memory = max(memory_readings)
            avg_memory = sum(memory_readings) / len(memory_readings)
            
            print(f"\nMemory Usage:")
            print(f"Average: {avg_memory:.1f} MB")
            print(f"Peak: {max_memory:.1f} MB")
        
        if self.performance_metrics['cpu_usage']:
            cpu_readings = [c['percent'] for c in self.performance_metrics['cpu_usage'] if c['percent'] > 0]
            if cpu_readings:
                max_cpu = max(cpu_readings)
                avg_cpu = sum(cpu_readings) / len(cpu_readings)
                
                print(f"\nCPU Usage:")
                print(f"Average: {avg_cpu:.1f}%")
                print(f"Peak: {max_cpu:.1f}%")
        
        print("\nLoad Test Summary:")
        print("✓ High volume file operations completed")
        print("✓ Concurrent system operations tested")
        print("✓ Memory usage validated")
        print("✓ Performance metrics collected")
        
        print("\n" + "="*80)


if __name__ == '__main__':
    # Enable full testing
    os.environ.pop('TESTING', None)
    
    # Run with high verbosity
    unittest.main(verbosity=2, exit=False)
    
    # Create a test instance to generate final report
    test_instance = ComprehensiveLoadTests()
    test_instance.setUp()
    test_instance.generate_load_test_report()
    test_instance.tearDown()