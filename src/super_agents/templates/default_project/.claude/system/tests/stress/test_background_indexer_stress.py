#!/usr/bin/env python3
"""
Background Indexer Stress Tests
Tests the background indexer under concurrent SQLite access patterns
Per Gemini's recommendation to regain confidence in the component
"""

import os
import sys
import time
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import string

# Add the template system to path
template_system = Path(__file__).parent.parent.parent
sys.path.insert(0, str(template_system))

try:
    from performance.indexing import ProjectIndexer
except ImportError:
    # Skip if performance module not available
    ProjectIndexer = None


class BackgroundIndexerStressTests(unittest.TestCase):
    """Stress test the background indexer for SQLite concurrency issues"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="indexer_stress_"))
        self.original_cwd = Path.cwd()
        os.chdir(self.test_dir)
        
        # Create test project structure
        self.create_test_project()
        
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_project(self):
        """Create a realistic project structure for testing"""
        # Create various directories and files
        dirs_to_create = [
            'src/components',
            'src/utils', 
            'src/api',
            'tests/unit',
            'tests/integration',
            'docs',
            'config',
            'scripts'
        ]
        
        for dir_path in dirs_to_create:
            (self.test_dir / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create test files with various content
        files_to_create = [
            ('src/main.py', 'def main():\n    print("Hello World")\n'),
            ('src/components/button.py', 'class Button:\n    def __init__(self):\n        pass\n'),
            ('src/utils/helpers.py', 'def helper_func():\n    return True\n'),
            ('src/api/client.py', 'import requests\n\nclass APIClient:\n    pass\n'),
            ('tests/test_main.py', 'import unittest\n\nclass TestMain(unittest.TestCase):\n    pass\n'),
            ('README.md', '# Test Project\n\nThis is a test project.'),
            ('requirements.txt', 'requests==2.28.0\npytest==7.1.0\n'),
            ('config/settings.py', 'DEBUG = True\nDATABASE_URL = "sqlite:///db.sqlite3"\n')
        ]
        
        for file_path, content in files_to_create:
            full_path = self.test_dir / file_path
            full_path.write_text(content)
    
    @unittest.skipIf(ProjectIndexer is None, "ProjectIndexer not available")
    def test_concurrent_file_indexing(self):
        """Test multiple threads indexing files simultaneously"""
        num_threads = 8
        files_per_thread = 20
        results = []
        errors = []
        
        def create_and_index_files(thread_id):
            """Create files and index them concurrently"""
            try:
                # Create unique files for this thread
                thread_dir = self.test_dir / f'thread_{thread_id}'
                thread_dir.mkdir(exist_ok=True)
                
                for i in range(files_per_thread):
                    # Create random content
                    content = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
                    file_path = thread_dir / f'file_{i}.py'
                    file_path.write_text(f'# Generated file {i}\n{content}\n')
                
                # Initialize indexer for this thread
                indexer = ProjectIndexer(root_path=self.test_dir)
                
                # Index the files created by this thread
                files_indexed = 0
                for i in range(files_per_thread):
                    file_path = thread_dir / f'file_{i}.py'
                    try:
                        indexer.index_file(file_path)
                        files_indexed += 1
                    except Exception as e:
                        errors.append(f"Thread {thread_id}: {e}")
                
                results.append({
                    'thread_id': thread_id,
                    'files_created': files_per_thread,
                    'files_indexed': files_indexed,
                    'success': files_indexed == files_per_thread
                })
                
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {e}")
        
        # Start concurrent indexing threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_and_index_files, thread_id) 
                for thread_id in range(num_threads)
            ]
            
            # Wait for all threads to complete
            for future in as_completed(futures):
                future.result()
        
        # Verify results
        self.assertEqual(len(results), num_threads, f"Expected {num_threads} results, got {len(results)}")
        
        successful_threads = sum(1 for r in results if r['success'])
        total_files_indexed = sum(r['files_indexed'] for r in results)
        expected_total_files = num_threads * files_per_thread
        
        # Report results
        success_rate = (successful_threads / num_threads) * 100
        indexing_rate = (total_files_indexed / expected_total_files) * 100
        
        print(f"\nConcurrent Indexing Results:")
        print(f"Threads: {num_threads}")
        print(f"Files per thread: {files_per_thread}")
        print(f"Successful threads: {successful_threads}/{num_threads} ({success_rate:.1f}%)")
        print(f"Files indexed: {total_files_indexed}/{expected_total_files} ({indexing_rate:.1f}%)")
        print(f"Errors: {len(errors)}")
        
        if errors:
            print("Errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        # We expect at least 80% success rate under stress
        self.assertGreaterEqual(success_rate, 80, f"Success rate {success_rate:.1f}% below 80% threshold")
        self.assertGreaterEqual(indexing_rate, 80, f"Indexing rate {indexing_rate:.1f}% below 80% threshold")
    
    @unittest.skipIf(ProjectIndexer is None, "ProjectIndexer not available")
    def test_database_contention_under_load(self):
        """Test database handles contention properly under heavy load"""
        indexer = ProjectIndexer(root_path=self.test_dir)
        
        # Create initial index
        indexer.ensure_database_exists()
        
        num_operations = 100
        num_threads = 5
        operations_completed = []
        database_errors = []
        
        def database_stress_operations(thread_id):
            """Perform various database operations simultaneously"""
            try:
                local_indexer = ProjectIndexer(root_path=self.test_dir)
                operations = 0
                
                for i in range(num_operations // num_threads):
                    try:
                        # Mix of operations that stress the database
                        operation = i % 4
                        
                        if operation == 0:
                            # Get file stats
                            stats = local_indexer.get_file_stats()
                            self.assertIsInstance(stats, dict)
                            
                        elif operation == 1:
                            # Search for files (read operation)
                            local_indexer.search_files("*.py")
                            
                        elif operation == 2:
                            # Check if index is stale (read operation)
                            local_indexer.is_index_stale()
                            
                        elif operation == 3:
                            # Update file metadata (write operation)
                            test_file = self.test_dir / 'src' / 'main.py'
                            if test_file.exists():
                                local_indexer.index_file(test_file)
                        
                        operations += 1
                        
                        # Small random delay to increase contention
                        time.sleep(random.uniform(0.001, 0.005))
                        
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e).lower():
                            database_errors.append(f"Thread {thread_id}: Database locked error")
                        else:
                            database_errors.append(f"Thread {thread_id}: SQLite error: {e}")
                    except Exception as e:
                        database_errors.append(f"Thread {thread_id}: Unexpected error: {e}")
                
                operations_completed.append({
                    'thread_id': thread_id,
                    'operations': operations
                })
                
            except Exception as e:
                database_errors.append(f"Thread {thread_id} setup failed: {e}")
        
        # Run stress test
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(database_stress_operations, thread_id)
                for thread_id in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze results
        total_operations = sum(op['operations'] for op in operations_completed)
        operations_per_second = total_operations / duration if duration > 0 else 0
        
        print(f"\nDatabase Contention Test Results:")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Total operations: {total_operations}")
        print(f"Operations per second: {operations_per_second:.1f}")
        print(f"Database errors: {len(database_errors)}")
        print(f"Threads completed: {len(operations_completed)}/{num_threads}")
        
        if database_errors:
            print("Database errors encountered:")
            for error in database_errors[:3]:  # Show first 3 errors
                print(f"  - {error}")
        
        # Verify acceptable error rate
        error_rate = (len(database_errors) / total_operations) * 100 if total_operations > 0 else 100
        
        # Under stress, we allow some database lock errors but they should be minimal
        self.assertLessEqual(error_rate, 10, f"Database error rate {error_rate:.1f}% exceeds 10% threshold")
        self.assertGreaterEqual(operations_per_second, 10, "Operations per second too low")
    
    @unittest.skipIf(ProjectIndexer is None, "ProjectIndexer not available") 
    def test_background_indexing_with_file_changes(self):
        """Test background indexing while files are being modified"""
        indexer = ProjectIndexer(root_path=self.test_dir)
        
        # Initial index
        indexer.index_project()
        initial_stats = indexer.get_file_stats()
        
        file_modification_errors = []
        indexing_errors = []
        
        def modify_files_continuously():
            """Continuously modify files while indexing happens"""
            try:
                for i in range(50):
                    # Modify existing files
                    test_file = self.test_dir / 'src' / 'main.py'
                    content = f'# Modified at {time.time()}\ndef main():\n    print("Version {i}")\n'
                    test_file.write_text(content)
                    
                    # Create new files
                    new_file = self.test_dir / f'dynamic_file_{i}.py'
                    new_file.write_text(f'# Dynamic file {i}\nprint("Created at {time.time()}")\n')
                    
                    time.sleep(0.1)  # 100ms between modifications
                    
            except Exception as e:
                file_modification_errors.append(f"File modification error: {e}")
        
        def background_indexing():
            """Run background indexing continuously"""
            try:
                local_indexer = ProjectIndexer(root_path=self.test_dir)
                
                for i in range(20):  # 20 indexing cycles
                    try:
                        # Re-index the project
                        local_indexer.index_project(max_workers=2)
                        
                        # Verify index is functional
                        stats = local_indexer.get_file_stats()
                        self.assertIsInstance(stats, dict)
                        
                        time.sleep(0.25)  # 250ms between indexing cycles
                        
                    except Exception as e:
                        indexing_errors.append(f"Indexing cycle {i}: {e}")
                        
            except Exception as e:
                indexing_errors.append(f"Background indexing setup error: {e}")
        
        # Start both operations concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            file_future = executor.submit(modify_files_continuously)
            index_future = executor.submit(background_indexing)
            
            # Wait for both to complete
            file_future.result()
            index_future.result()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Get final stats
        final_stats = indexer.get_file_stats()
        
        print(f"\nBackground Indexing with File Changes Results:")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Initial files: {initial_stats.get('total_files', 0)}")
        print(f"Final files: {final_stats.get('total_files', 0)}")
        print(f"File modification errors: {len(file_modification_errors)}")
        print(f"Indexing errors: {len(indexing_errors)}")
        
        if file_modification_errors:
            print("File modification errors:")
            for error in file_modification_errors[:2]:
                print(f"  - {error}")
        
        if indexing_errors:
            print("Indexing errors:")
            for error in indexing_errors[:2]:
                print(f"  - {error}")
        
        # Verify that indexing handled concurrent file changes
        self.assertLessEqual(len(file_modification_errors), 2, "Too many file modification errors")
        self.assertLessEqual(len(indexing_errors), 5, "Too many indexing errors")
        
        # Final files should be more than initial (we added 50 dynamic files)
        files_added = final_stats.get('total_files', 0) - initial_stats.get('total_files', 0)
        self.assertGreaterEqual(files_added, 30, f"Expected at least 30 new files, got {files_added}")
    
    @unittest.skipIf(ProjectIndexer is None, "ProjectIndexer not available")
    def test_indexer_recovery_from_corruption(self):
        """Test that indexer can recover from database corruption"""
        indexer = ProjectIndexer(root_path=self.test_dir)
        
        # Create initial index
        indexer.index_project()
        initial_stats = indexer.get_file_stats()
        
        # Simulate database corruption
        db_path = indexer.db_path
        
        # Corrupt the database file
        with open(db_path, 'wb') as f:
            f.write(b'CORRUPTED DATABASE CONTENT')
        
        # Verify corruption is detected
        corrupted_indexer = ProjectIndexer(root_path=self.test_dir)
        
        # The indexer should handle corruption gracefully
        try:
            # This should trigger database recreation
            corrupted_indexer.ensure_database_exists()
            
            # Re-index after corruption
            corrupted_indexer.index_project()
            
            # Verify recovery
            recovered_stats = corrupted_indexer.get_file_stats()
            
            print(f"\nDatabase Recovery Test Results:")
            print(f"Initial files: {initial_stats.get('total_files', 0)}")
            print(f"Recovered files: {recovered_stats.get('total_files', 0)}")
            
            # After recovery, we should have similar file counts
            initial_count = initial_stats.get('total_files', 0)
            recovered_count = recovered_stats.get('total_files', 0)
            
            # Allow some variance due to timing
            count_difference = abs(initial_count - recovered_count)
            self.assertLessEqual(count_difference, 2, 
                               f"Recovery file count differs too much: {initial_count} vs {recovered_count}")
            
            # Verify basic functionality works after recovery
            search_results = corrupted_indexer.search_files("*.py")
            self.assertIsInstance(search_results, list)
            
        except Exception as e:
            self.fail(f"Indexer failed to recover from corruption: {e}")


if __name__ == '__main__':
    # Set environment to enable full testing
    os.environ.pop('TESTING', None)
    
    unittest.main(verbosity=2)