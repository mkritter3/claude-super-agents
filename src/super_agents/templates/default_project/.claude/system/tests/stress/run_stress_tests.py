#!/usr/bin/env python3
"""
Stress Test Runner
Executes all stress tests for the super-agents system
"""

import os
import sys
import time
import unittest
import subprocess
from pathlib import Path

def main():
    """Run all stress tests with comprehensive reporting"""
    print("="*80)
    print("SUPER AGENTS STRESS TEST SUITE")
    print("="*80)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Setup test environment
    test_dir = Path(__file__).parent
    template_system = test_dir.parent
    sys.path.insert(0, str(template_system))
    
    # Ensure we're not in testing mode for stress tests
    os.environ.pop('TESTING', None)
    os.environ.pop('PYTEST_CURRENT_TEST', None)
    
    # Define stress tests
    stress_tests = [
        ('Background Indexer Stress Tests', 'test_background_indexer_stress.py'),
        ('Comprehensive Load Tests', 'test_comprehensive_load.py')
    ]
    
    # Track results
    results = {}
    total_start_time = time.time()
    
    for test_name, test_file in stress_tests:
        print(f"\n{'='*60}")
        print(f"RUNNING: {test_name}")
        print(f"{'='*60}")
        
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f"❌ Test file not found: {test_file}")
            results[test_name] = {'status': 'FAILED', 'reason': 'File not found'}
            continue
        
        try:
            start_time = time.time()
            
            # Run the test
            result = subprocess.run([
                sys.executable, str(test_path)
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ {test_name} PASSED")
                results[test_name] = {
                    'status': 'PASSED', 
                    'duration': duration,
                    'output': result.stdout
                }
            else:
                print(f"❌ {test_name} FAILED")
                print(f"Return code: {result.returncode}")
                if result.stderr:
                    print(f"Error output:\n{result.stderr}")
                results[test_name] = {
                    'status': 'FAILED',
                    'duration': duration,
                    'return_code': result.returncode,
                    'stderr': result.stderr,
                    'stdout': result.stdout
                }
            
            print(f"Duration: {duration:.2f} seconds")
            
        except subprocess.TimeoutExpired:
            print(f"⏱️ {test_name} TIMED OUT")
            results[test_name] = {'status': 'TIMEOUT', 'reason': 'Test exceeded 10 minute limit'}
            
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
            results[test_name] = {'status': 'ERROR', 'reason': str(e)}
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Generate summary report
    print("\n" + "="*80)
    print("STRESS TEST SUMMARY REPORT")
    print("="*80)
    
    passed_tests = [name for name, result in results.items() if result['status'] == 'PASSED']
    failed_tests = [name for name, result in results.items() if result['status'] != 'PASSED']
    
    print(f"\nOverall Results:")
    print(f"Total tests: {len(stress_tests)}")
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success rate: {(len(passed_tests)/len(stress_tests)*100):.1f}%")
    print(f"Total duration: {total_duration:.2f} seconds")
    
    print(f"\nDetailed Results:")
    for test_name, result in results.items():
        status_emoji = "✅" if result['status'] == 'PASSED' else "❌"
        print(f"{status_emoji} {test_name}: {result['status']}")
        
        if 'duration' in result:
            print(f"   Duration: {result['duration']:.2f}s")
        
        if result['status'] == 'FAILED':
            if 'return_code' in result:
                print(f"   Return code: {result['return_code']}")
            if 'reason' in result:
                print(f"   Reason: {result['reason']}")
        
        if result['status'] in ['TIMEOUT', 'ERROR'] and 'reason' in result:
            print(f"   Reason: {result['reason']}")
    
    # Performance insights
    print(f"\nPerformance Insights:")
    
    successful_durations = [
        result['duration'] for result in results.values() 
        if result['status'] == 'PASSED' and 'duration' in result
    ]
    
    if successful_durations:
        avg_duration = sum(successful_durations) / len(successful_durations)
        max_duration = max(successful_durations)
        min_duration = min(successful_durations)
        
        print(f"Average test duration: {avg_duration:.2f}s")
        print(f"Fastest test: {min_duration:.2f}s")
        print(f"Slowest test: {max_duration:.2f}s")
    
    # System recommendations
    print(f"\nSystem Recommendations:")
    
    if len(failed_tests) == 0:
        print("🎉 All stress tests passed! System is performing well under load.")
        print("   - Performance optimizations are working effectively")
        print("   - Background indexer handles concurrency properly")
        print("   - Memory usage is within acceptable limits")
        print("   - System is ready for production load")
    else:
        print("⚠️  Some stress tests failed. Consider the following:")
        for test_name in failed_tests:
            result = results[test_name]
            if 'timeout' in result['status'].lower():
                print(f"   - {test_name}: Increase timeout or optimize performance")
            elif 'memory' in str(result.get('stderr', '')).lower():
                print(f"   - {test_name}: Investigate memory usage patterns")
            elif 'database' in str(result.get('stderr', '')).lower():
                print(f"   - {test_name}: Check database connection limits")
            else:
                print(f"   - {test_name}: Review test output for specific issues")
    
    # Resource usage recommendations
    print(f"\nResource Usage Guidelines:")
    print("- Monitor memory usage in production environments")
    print("- Configure appropriate SQLite timeout values")
    print("- Use connection pooling for high-concurrency scenarios")
    print("- Consider background indexing frequency based on file change rate")
    
    print(f"\nCompleted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Exit with appropriate code
    if len(failed_tests) == 0:
        print("\n🚀 All stress tests passed! System is stress-test certified.")
        return 0
    else:
        print(f"\n⚠️  {len(failed_tests)} out of {len(stress_tests)} stress tests failed.")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)