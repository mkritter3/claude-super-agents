#!/usr/bin/env python3
"""
Load testing for Knowledge Manager server deployment
"""

import pytest
import requests
import time
import threading
import statistics
import subprocess
import signal
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

class TestKMLoadTesting:
    """Load testing for Knowledge Manager server."""
    
    @classmethod
    def setup_class(cls):
        """Setup class-level test environment."""
        cls.km_url = "http://127.0.0.1:5001"
        cls.test_timeout = 10  # seconds
        cls.results = defaultdict(list)
    
    def test_server_availability(self):
        """Test that KM server is running and responding."""
        try:
            response = requests.get(f"{self.km_url}/mcp/spec", timeout=5)
            assert response.status_code == 200, f"KM server not responding: {response.status_code}"
        except requests.RequestException as e:
            pytest.skip(f"KM server not available: {e}")
    
    def test_single_request_performance(self):
        """Test single request performance baseline."""
        start_time = time.time()
        
        try:
            response = requests.get(f"{self.km_url}/mcp/spec", timeout=self.test_timeout)
            end_time = time.time()
            
            duration = end_time - start_time
            
            assert response.status_code == 200
            assert duration < 2.0, f"Single request too slow: {duration}s"
            
            self.results['single_request'].append(duration)
            
        except requests.RequestException as e:
            pytest.fail(f"Single request failed: {e}")
    
    def test_concurrent_requests(self):
        """Test concurrent request handling."""
        num_workers = 10
        requests_per_worker = 10
        total_requests = num_workers * requests_per_worker
        
        def make_request():
            """Make a single request and return timing info."""
            start_time = time.time()
            try:
                response = requests.get(f"{self.km_url}/mcp/spec", timeout=self.test_timeout)
                end_time = time.time()
                return {
                    'success': response.status_code == 200,
                    'duration': end_time - start_time,
                    'status_code': response.status_code
                }
            except requests.RequestException as e:
                end_time = time.time()
                return {
                    'success': False,
                    'duration': end_time - start_time,
                    'error': str(e)
                }
        
        # Execute concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]
            results = [future.result() for future in as_completed(futures)]
        end_time = time.time()
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        success_rate = len(successful_requests) / total_requests
        total_duration = end_time - start_time
        requests_per_second = total_requests / total_duration
        
        if successful_requests:
            durations = [r['duration'] for r in successful_requests]
            avg_duration = statistics.mean(durations)
            p95_duration = statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0]
        else:
            avg_duration = 0
            p95_duration = 0
        
        # Store results for reporting
        self.results['concurrent_test'] = {
            'total_requests': total_requests,
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': success_rate,
            'total_duration': total_duration,
            'requests_per_second': requests_per_second,
            'avg_duration': avg_duration,
            'p95_duration': p95_duration
        }
        
        # Assertions
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
        assert requests_per_second >= 50, f"Throughput too low: {requests_per_second:.1f} req/s"
        assert avg_duration < 1.0, f"Average response time too high: {avg_duration:.3f}s"
        assert p95_duration < 2.0, f"P95 response time too high: {p95_duration:.3f}s"
    
    def test_sustained_load(self):
        """Test sustained load over time."""
        duration_seconds = 30
        requests_per_second = 20
        
        def sustained_requester():
            """Make requests at specified rate."""
            results = []
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration_seconds:
                request_start = time.time()
                
                try:
                    response = requests.get(f"{self.km_url}/mcp/spec", timeout=self.test_timeout)
                    request_end = time.time()
                    
                    results.append({
                        'timestamp': request_start,
                        'duration': request_end - request_start,
                        'success': response.status_code == 200,
                        'status_code': response.status_code
                    })
                except requests.RequestException as e:
                    request_end = time.time()
                    results.append({
                        'timestamp': request_start,
                        'duration': request_end - request_start,
                        'success': False,
                        'error': str(e)
                    })
                
                request_count += 1
                
                # Control request rate
                sleep_time = (1.0 / requests_per_second) - (time.time() - request_start)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            return results
        
        # Run sustained load test
        results = sustained_requester()
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        success_rate = len(successful_results) / len(results)
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
        else:
            avg_duration = 0
            max_duration = 0
        
        actual_rps = len(results) / duration_seconds
        
        # Store results
        self.results['sustained_load'] = {
            'total_requests': len(results),
            'successful_requests': len(successful_results),
            'success_rate': success_rate,
            'duration_seconds': duration_seconds,
            'target_rps': requests_per_second,
            'actual_rps': actual_rps,
            'avg_duration': avg_duration,
            'max_duration': max_duration
        }
        
        # Assertions
        assert success_rate >= 0.95, f"Sustained load success rate too low: {success_rate:.2%}"
        assert avg_duration < 1.0, f"Sustained load avg response time too high: {avg_duration:.3f}s"
        assert max_duration < 5.0, f"Sustained load max response time too high: {max_duration:.3f}s"
    
    def test_post_request_performance(self):
        """Test POST request performance with realistic payload."""
        test_payload = {
            'tool_name': 'query',
            'tool_input': {
                'question': 'What are the best practices for implementing circuit breakers?',
                'ticket_id': 'LOAD-TEST-001',
                'limit': 10
            }
        }
        
        num_requests = 50
        results = []
        
        for i in range(num_requests):
            start_time = time.time()
            try:
                response = requests.post(f"{self.km_url}/mcp", 
                                       json=test_payload, 
                                       timeout=self.test_timeout)
                end_time = time.time()
                
                results.append({
                    'success': response.status_code == 200,
                    'duration': end_time - start_time,
                    'status_code': response.status_code
                })
            except requests.RequestException as e:
                end_time = time.time()
                results.append({
                    'success': False,
                    'duration': end_time - start_time,
                    'error': str(e)
                })
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        success_rate = len(successful_results) / len(results)
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            avg_duration = statistics.mean(durations)
            p95_duration = statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0]
        else:
            avg_duration = 0
            p95_duration = 0
        
        # Store results
        self.results['post_requests'] = {
            'total_requests': num_requests,
            'successful_requests': len(successful_results),
            'success_rate': success_rate,
            'avg_duration': avg_duration,
            'p95_duration': p95_duration
        }
        
        # Assertions
        assert success_rate >= 0.90, f"POST request success rate too low: {success_rate:.2%}"
        assert avg_duration < 2.0, f"POST request avg response time too high: {avg_duration:.3f}s"
    
    def test_memory_stability(self):
        """Test that server memory usage remains stable under load."""
        # This is a basic test - in production you'd want proper memory monitoring
        num_requests = 100
        
        def make_large_request():
            """Make request with larger payload."""
            payload = {
                'tool_name': 'query',
                'tool_input': {
                    'question': ' '.join(['performance test'] * 100),  # Larger payload
                    'ticket_id': f'MEM-TEST-{time.time()}',
                    'limit': 20
                }
            }
            
            try:
                response = requests.post(f"{self.km_url}/mcp", 
                                       json=payload, 
                                       timeout=self.test_timeout)
                return response.status_code == 200
            except requests.RequestException:
                return False
        
        # Make many requests to test memory stability
        successful_count = 0
        for i in range(num_requests):
            if make_large_request():
                successful_count += 1
            
            # Small delay to allow garbage collection
            if i % 10 == 0:
                time.sleep(0.1)
        
        success_rate = successful_count / num_requests
        assert success_rate >= 0.90, f"Memory stability test failed: {success_rate:.2%} success rate"
    
    @classmethod
    def teardown_class(cls):
        """Print load test results summary."""
        print("\n" + "="*80)
        print("KNOWLEDGE MANAGER LOAD TEST RESULTS")
        print("="*80)
        
        if 'single_request' in cls.results:
            durations = cls.results['single_request']
            print(f"Single Request Performance:")
            print(f"  Average: {statistics.mean(durations):.3f}s")
        
        if 'concurrent_test' in cls.results:
            data = cls.results['concurrent_test']
            print(f"\nConcurrent Requests Test:")
            print(f"  Total Requests: {data['total_requests']}")
            print(f"  Success Rate: {data['success_rate']:.2%}")
            print(f"  Throughput: {data['requests_per_second']:.1f} req/s")
            print(f"  Average Duration: {data['avg_duration']:.3f}s")
            print(f"  P95 Duration: {data['p95_duration']:.3f}s")
        
        if 'sustained_load' in cls.results:
            data = cls.results['sustained_load']
            print(f"\nSustained Load Test:")
            print(f"  Target RPS: {data['target_rps']}")
            print(f"  Actual RPS: {data['actual_rps']:.1f}")
            print(f"  Success Rate: {data['success_rate']:.2%}")
            print(f"  Average Duration: {data['avg_duration']:.3f}s")
            print(f"  Max Duration: {data['max_duration']:.3f}s")
        
        if 'post_requests' in cls.results:
            data = cls.results['post_requests']
            print(f"\nPOST Request Performance:")
            print(f"  Success Rate: {data['success_rate']:.2%}")
            print(f"  Average Duration: {data['avg_duration']:.3f}s")
            print(f"  P95 Duration: {data['p95_duration']:.3f}s")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print output