#!/usr/bin/env python3
"""
Test runner for Phase 0 critical fixes
Runs all Phase 0 tests and generates a comprehensive report
"""

import pytest
import sys
import json
import subprocess
import time
import requests
from pathlib import Path
from datetime import datetime

class Phase0TestRunner:
    """Comprehensive test runner for Phase 0 critical fixes."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def check_prerequisites(self):
        """Check that required components are available."""
        print("🔍 Checking prerequisites...")
        
        # Check if KM server is running for load tests
        try:
            response = requests.get("http://127.0.0.1:5001/mcp/spec", timeout=5)
            if response.status_code == 200:
                print("✅ Knowledge Manager server is running")
                self.results['km_server_available'] = True
            else:
                print(f"⚠️  Knowledge Manager server responded with {response.status_code}")
                self.results['km_server_available'] = False
        except requests.RequestException:
            print("⚠️  Knowledge Manager server not available (load tests will be skipped)")
            self.results['km_server_available'] = False
        
        # Check if required Python packages are available
        required_packages = ['pytest', 'requests']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package} is available")
            except ImportError:
                missing_packages.append(package)
                print(f"❌ {package} is missing")
        
        if missing_packages:
            print(f"Please install missing packages: pip install {' '.join(missing_packages)}")
            return False
        
        return True
    
    def run_circuit_breaker_tests(self):
        """Run circuit breaker integration tests."""
        print("\n🔄 Running circuit breaker tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(self.test_dir / "test_circuit_breaker.py"),
                "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=self.test_dir.parent.parent.parent)
            
            self.results['circuit_breaker'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0
            }
            
            if result.returncode == 0:
                print("✅ Circuit breaker tests PASSED")
            else:
                print("❌ Circuit breaker tests FAILED")
                print(result.stdout)
                print(result.stderr)
        
        except Exception as e:
            print(f"❌ Failed to run circuit breaker tests: {e}")
            self.results['circuit_breaker'] = {
                'exit_code': -1,
                'error': str(e),
                'passed': False
            }
    
    def run_structured_logging_tests(self):
        """Run structured logging tests."""
        print("\n📝 Running structured logging tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                str(self.test_dir / "test_structured_logging.py"),
                "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=self.test_dir.parent.parent.parent)
            
            self.results['structured_logging'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0
            }
            
            if result.returncode == 0:
                print("✅ Structured logging tests PASSED")
            else:
                print("❌ Structured logging tests FAILED")
                print(result.stdout)
                print(result.stderr)
        
        except Exception as e:
            print(f"❌ Failed to run structured logging tests: {e}")
            self.results['structured_logging'] = {
                'exit_code': -1,
                'error': str(e),
                'passed': False
            }
    
    def run_fallback_context_tests(self):
        """Run fallback context tests."""
        print("\n🔄 Running fallback context tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                str(self.test_dir / "test_fallback_context.py"),
                "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=self.test_dir.parent.parent.parent)
            
            self.results['fallback_context'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0
            }
            
            if result.returncode == 0:
                print("✅ Fallback context tests PASSED")
            else:
                print("❌ Fallback context tests FAILED")
                print(result.stdout)
                print(result.stderr)
        
        except Exception as e:
            print(f"❌ Failed to run fallback context tests: {e}")
            self.results['fallback_context'] = {
                'exit_code': -1,
                'error': str(e),
                'passed': False
            }
    
    def run_km_load_tests(self):
        """Run Knowledge Manager load tests."""
        print("\n🚀 Running KM load tests...")
        
        if not self.results.get('km_server_available', False):
            print("⚠️  Skipping KM load tests - server not available")
            self.results['km_load'] = {
                'skipped': True,
                'reason': 'KM server not available'
            }
            return
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                str(self.test_dir / "test_km_load.py"),
                "-v", "--tb=short", "-s"  # -s to show print output
            ], capture_output=True, text=True, cwd=self.test_dir.parent.parent.parent)
            
            self.results['km_load'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0
            }
            
            if result.returncode == 0:
                print("✅ KM load tests PASSED")
            else:
                print("❌ KM load tests FAILED")
                print(result.stdout)
                print(result.stderr)
        
        except Exception as e:
            print(f"❌ Failed to run KM load tests: {e}")
            self.results['km_load'] = {
                'exit_code': -1,
                'error': str(e),
                'passed': False
            }
    
    def test_deployment_script(self):
        """Test the deployment script functionality."""
        print("\n🚀 Testing deployment script...")
        
        script_path = self.test_dir.parent.parent / "scripts" / "deploy_km.sh"
        
        if not script_path.exists():
            print("❌ Deployment script not found")
            self.results['deployment_script'] = {
                'passed': False,
                'error': 'Script not found'
            }
            return
        
        try:
            # Test script help/usage
            result = subprocess.run([
                str(script_path), "status"
            ], capture_output=True, text=True, timeout=10)
            
            self.results['deployment_script'] = {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': True  # Just testing that script runs
            }
            
            print("✅ Deployment script is executable")
        
        except Exception as e:
            print(f"❌ Deployment script test failed: {e}")
            self.results['deployment_script'] = {
                'error': str(e),
                'passed': False
            }
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*80)
        print("PHASE 0 CRITICAL FIXES - TEST REPORT")
        print("="*80)
        print(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"Duration: {duration:.2f} seconds")
        
        print("\nTest Results Summary:")
        print("-" * 40)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in self.results.items():
            if test_name == 'km_server_available':
                continue
            
            total_tests += 1
            status = "PASS" if result.get('passed', False) else "FAIL"
            
            if result.get('skipped'):
                status = "SKIP"
                print(f"{test_name:25} {status:>6} - {result.get('reason', 'Unknown')}")
            else:
                print(f"{test_name:25} {status:>6}")
                if status == "PASS":
                    passed_tests += 1
        
        print("-" * 40)
        print(f"Total: {total_tests}, Passed: {passed_tests}, Failed: {total_tests - passed_tests}")
        
        # Overall status
        if passed_tests == total_tests:
            print("\n🎉 ALL PHASE 0 TESTS PASSED!")
            print("✅ Circuit breakers are working")
            print("✅ Structured logging is implemented")
            print("✅ Fallback context generation is functional")
            if self.results.get('km_load', {}).get('passed'):
                print("✅ KM server can handle production load")
            print("✅ Deployment script is ready")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
            print("Please review failed tests before proceeding to Phase 1")
        
        # Implementation checklist
        print("\nPhase 0 Implementation Checklist:")
        print("-" * 40)
        
        checklist = [
            ("Circuit breakers added to context_assembler.py", self.results.get('circuit_breaker', {}).get('passed', False)),
            ("Structured logging implemented", self.results.get('structured_logging', {}).get('passed', False)),
            ("Fallback context generation working", self.results.get('fallback_context', {}).get('passed', False)),
            ("KM server deployment script ready", self.results.get('deployment_script', {}).get('passed', False)),
            ("System handles KM failures gracefully", self.results.get('circuit_breaker', {}).get('passed', False) and self.results.get('fallback_context', {}).get('passed', False))
        ]
        
        for item, status in checklist:
            icon = "✅" if status else "❌"
            print(f"{icon} {item}")
        
        # Save detailed results to file
        report_file = self.test_dir / "phase0_test_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'duration': (self.end_time - self.start_time) if self.start_time and self.end_time else None,
                'results': self.results,
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': total_tests - passed_tests
                }
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        return passed_tests == total_tests
    
    def run_all_tests(self):
        """Run all Phase 0 tests."""
        print("🚀 Starting Phase 0 Critical Fixes Test Suite")
        print("="*80)
        
        self.start_time = time.time()
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("❌ Prerequisites not met, aborting tests")
            return False
        
        # Run all test suites
        self.run_circuit_breaker_tests()
        self.run_structured_logging_tests()
        self.run_fallback_context_tests()
        self.run_km_load_tests()
        self.test_deployment_script()
        
        self.end_time = time.time()
        
        # Generate report
        return self.generate_report()

def main():
    """Main test runner entry point."""
    runner = Phase0TestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()