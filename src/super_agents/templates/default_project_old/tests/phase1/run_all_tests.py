#!/usr/bin/env python3
"""
Phase 1 Test Runner
Runs all Phase 1 tests and provides comprehensive reporting
"""

import unittest
import sys
import os
import time
from pathlib import Path
from io import StringIO

# Add system path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

# Import test modules
from test_path_validation import TestPathValidation
from test_locking_mechanism import TestLockingMechanism, TestResourceManagerEnforcement
from test_resource_manager import TestResourceManager, TestResourceManagerIntegration


class Phase1TestResult:
    """Custom test result tracking for Phase 1."""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.errors = []
        self.failures = []
        self.start_time = None
        self.end_time = None
    
    def start_timing(self):
        """Start timing the test run."""
        self.start_time = time.time()
    
    def end_timing(self):
        """End timing the test run."""
        self.end_time = time.time()
    
    def get_duration(self):
        """Get test run duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def add_result(self, test_result):
        """Add a unittest result to our tracking."""
        self.total_tests += test_result.testsRun
        self.passed_tests += test_result.testsRun - len(test_result.failures) - len(test_result.errors) - len(test_result.skipped)
        self.failed_tests += len(test_result.failures)
        self.skipped_tests += len(test_result.skipped)
        self.errors.extend(test_result.errors)
        self.failures.extend(test_result.failures)
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("PHASE 1 TEST SUMMARY")
        print("="*70)
        print(f"Total Tests:    {self.total_tests}")
        print(f"Passed:         {self.passed_tests}")
        print(f"Failed:         {self.failed_tests}")
        print(f"Skipped:        {self.skipped_tests}")
        print(f"Duration:       {self.get_duration():.2f} seconds")
        
        if self.failed_tests == 0 and len(self.errors) == 0:
            print(f"\n✅ ALL TESTS PASSED! Phase 1 implementation is working correctly.")
        else:
            print(f"\n❌ {self.failed_tests + len(self.errors)} TESTS FAILED")
        
        print("="*70)
        
        if self.failures:
            print("\nFAILURES:")
            for test, traceback in self.failures:
                print(f"\n❌ {test}")
                print(f"   {traceback}")
        
        if self.errors:
            print("\nERRORS:")
            for test, traceback in self.errors:
                print(f"\n💥 {test}")
                print(f"   {traceback}")


def run_test_suite(test_class, suite_name):
    """Run a test suite and return results."""
    print(f"\n🧪 Running {suite_name}...")
    print("-" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_class)
    
    # Run tests with custom result
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)
    
    # Print individual test results
    output = stream.getvalue()
    print(output)
    
    return result


def check_dependencies():
    """Check that all required dependencies are available."""
    missing_deps = []
    
    try:
        import psutil
    except ImportError:
        missing_deps.append("psutil")
    
    try:
        import sqlite3
    except ImportError:
        missing_deps.append("sqlite3")
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install psutil")
        return False
    
    return True


def check_file_structure():
    """Check that required files exist and set up test directories."""
    required_files = [
        "../../system/file_registry.py",
        "../../system/parallel_orchestrator.py", 
        "../../system/logger_config.py"
    ]
    
    missing_files = []
    base_path = Path(__file__).parent
    
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing_files.append(str(full_path))
    
    if missing_files:
        print(f"❌ Missing required files:")
        for file_path in missing_files:
            print(f"   {file_path}")
        return False
    
    # Create necessary directories for testing
    test_dirs = [
        ".claude/logs",
        ".claude/registry", 
        ".claude/snapshots",
        ".claude/workspaces"
    ]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    return True


def main():
    """Main test runner."""
    print("Phase 1 AET Enhancement Test Suite")
    print("Testing: Path Validation, Locking Mechanism, Resource Manager")
    
    # Pre-flight checks
    print("\n🔍 Pre-flight checks...")
    if not check_dependencies():
        sys.exit(1)
    
    if not check_file_structure():
        sys.exit(1)
    
    print("✅ All dependencies and files present")
    
    # Initialize result tracking
    overall_result = Phase1TestResult()
    overall_result.start_timing()
    
    # Test suites to run
    test_suites = [
        (TestPathValidation, "Path Validation Security Tests"),
        (TestLockingMechanism, "Locking Mechanism Tests"),
        (TestResourceManagerEnforcement, "Resource Manager Enforcement Tests"),
        (TestResourceManager, "Resource Manager Core Tests"),
        (TestResourceManagerIntegration, "Resource Manager Integration Tests"),
    ]
    
    # Run each test suite
    for test_class, suite_name in test_suites:
        try:
            result = run_test_suite(test_class, suite_name)
            overall_result.add_result(result)
        except Exception as e:
            print(f"❌ Error running {suite_name}: {e}")
            overall_result.errors.append((suite_name, str(e)))
    
    overall_result.end_timing()
    
    # Print comprehensive summary
    overall_result.print_summary()
    
    # Print security-specific results
    print("\n🔐 SECURITY TEST RESULTS:")
    if overall_result.failed_tests == 0:
        print("✅ Path traversal protection: WORKING")
        print("✅ Symlink rejection: WORKING") 
        print("✅ Invalid character filtering: WORKING")
        print("✅ Workspace boundary enforcement: WORKING")
    else:
        print("❌ Some security tests failed - review failures above")
    
    # Print locking-specific results
    print("\n🔒 LOCKING MECHANISM RESULTS:")
    if overall_result.failed_tests == 0:
        print("✅ Database-only locking: WORKING")
        print("✅ Partial failure cleanup: WORKING")
        print("✅ Deadlock prevention: WORKING")
        print("✅ Lock release on exception: WORKING")
    else:
        print("❌ Some locking tests failed - review failures above")
    
    # Print resource management results
    print("\n⚡ RESOURCE MANAGEMENT RESULTS:")
    if overall_result.failed_tests == 0:
        print("✅ CPU limit enforcement: WORKING")
        print("✅ Memory limit enforcement: WORKING") 
        print("✅ Task queuing: WORKING")
        print("✅ Resource monitoring: WORKING")
    else:
        print("❌ Some resource management tests failed - review failures above")
    
    # Return exit code
    if overall_result.failed_tests == 0 and len(overall_result.errors) == 0:
        print(f"\n🎉 PHASE 1 COMPLETE: All {overall_result.total_tests} tests passed!")
        return 0
    else:
        print(f"\n💥 PHASE 1 INCOMPLETE: {overall_result.failed_tests + len(overall_result.errors)} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())