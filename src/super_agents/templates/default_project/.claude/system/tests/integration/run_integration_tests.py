#!/usr/bin/env python3
"""
Integration Test Runner
Runs all integration tests for the template system
"""

import os
import sys
import unittest
import time
import json
from pathlib import Path
from datetime import datetime

# Add template system to path - use resolve() to get absolute path
integration_dir = Path(__file__).resolve().parent
system_dir = integration_dir.parent.parent  # integration -> tests -> system
sys.path.insert(0, str(system_dir))

def run_integration_tests():
    """Run all integration tests and generate report"""
    
    print("🧪 Running Super Agents Integration Test Suite")
    print("=" * 60)
    
    # Discover and run tests
    test_dir = Path(__file__).parent
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern='test_*.py')
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Generate test report
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": round(end_time - start_time, 2),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success_rate": round((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100, 2) if result.testsRun > 0 else 0,
        "details": {
            "failures": [
                {
                    "test": str(test),
                    "error": traceback
                }
                for test, traceback in result.failures
            ],
            "errors": [
                {
                    "test": str(test),
                    "error": traceback
                }
                for test, traceback in result.errors
            ],
            "skipped": [
                {
                    "test": str(test),
                    "reason": reason
                }
                for test, reason in result.skipped
            ]
        }
    }
    
    # Save test report
    report_dir = Path(__file__).parent.parent.parent.parent / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(test_report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {test_report['tests_run']}")
    print(f"Successes: {test_report['tests_run'] - test_report['failures'] - test_report['errors']}")
    print(f"Failures: {test_report['failures']}")
    print(f"Errors: {test_report['errors']}")
    print(f"Skipped: {test_report['skipped']}")
    print(f"Success Rate: {test_report['success_rate']}%")
    print(f"Duration: {test_report['duration_seconds']} seconds")
    print(f"Report saved: {report_file}")
    
    # Print detailed results if there were issues
    if test_report['failures'] > 0:
        print("\n❌ FAILURES:")
        for failure in test_report['details']['failures']:
            print(f"  • {failure['test']}")
    
    if test_report['errors'] > 0:
        print("\n💥 ERRORS:")
        for error in test_report['details']['errors']:
            print(f"  • {error['test']}")
    
    if test_report['skipped'] > 0:
        print("\n⏭️ SKIPPED:")
        for skipped in test_report['details']['skipped']:
            print(f"  • {skipped['test']}: {skipped['reason']}")
    
    # Return success status
    return test_report['failures'] == 0 and test_report['errors'] == 0


def run_specific_test_suite(test_name):
    """Run a specific test suite"""
    test_files = {
        'template': 'test_template_system.py',
        'performance': 'test_performance_integration.py', 
        'reliability': 'test_reliability_integration.py'
    }
    
    if test_name not in test_files:
        print(f"❌ Unknown test suite: {test_name}")
        print(f"Available test suites: {', '.join(test_files.keys())}")
        return False
    
    test_file = test_files[test_name]
    test_path = Path(__file__).parent / test_file
    
    if not test_path.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"🧪 Running {test_name} integration tests")
    print("=" * 50)
    
    # Import and run specific test
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_path.stem)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.failures == 0 and result.errors == 0


def validate_test_environment():
    """Validate that the test environment is properly set up"""
    print("🔍 Validating test environment...")
    
    issues = []
    
    # Check if template system exists
    template_system = Path(__file__).parent.parent.parent  # Go up 3 levels from integration test dir
    if not template_system.exists():
        issues.append("Template system directory not found")
    
    # Check for key modules
    required_modules = [
        'commands',
        'performance', 
        'reliability',
        'database',
        'utils'
    ]
    
    for module in required_modules:
        module_path = template_system / module
        if not module_path.exists():
            issues.append(f"Required module '{module}' not found")
    
    # Check for Python version
    if sys.version_info < (3, 7):
        issues.append(f"Python 3.7+ required, found {sys.version}")
    
    if issues:
        print("❌ Test environment issues found:")
        for issue in issues:
            print(f"  • {issue}")
        return False
    
    print("✅ Test environment validation passed")
    return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Super Agents integration tests')
    parser.add_argument('--suite', choices=['template', 'performance', 'reliability'], 
                       help='Run specific test suite')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate test environment')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests only (skip long-running tests)')
    
    args = parser.parse_args()
    
    # Validate environment first
    if not validate_test_environment():
        sys.exit(1)
    
    if args.validate_only:
        print("✅ Environment validation complete")
        sys.exit(0)
    
    # Set environment variable for quick tests
    if args.quick:
        os.environ['QUICK_TESTS_ONLY'] = '1'
    
    # Run tests
    if args.suite:
        success = run_specific_test_suite(args.suite)
    else:
        success = run_integration_tests()
    
    if success:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed")
        sys.exit(1)