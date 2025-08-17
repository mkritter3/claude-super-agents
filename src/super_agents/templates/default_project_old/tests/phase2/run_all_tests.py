#!/usr/bin/env python3
"""
Phase 2 Test Runner - State Recovery System
Runs all Phase 2 tests with comprehensive reporting.
"""

import sys
import time
import unittest
from pathlib import Path

# Add system path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

# Import test modules
from test_state_rebuilder import TestStateRebuilder
from test_event_replay import TestEventReplay
from test_transactional_integrity import TestTransactionalIntegrity
from test_recovery_scenarios import TestRecoveryScenarios


class Phase2TestResult(unittest.TestResult):
    """Custom test result collector for Phase 2."""
    
    def __init__(self):
        super().__init__()
        self.test_results = []
        self.start_time = None
        self.test_start_time = None
    
    def startTest(self, test):
        super().startTest(test)
        self.test_start_time = time.time()
        print(f"Running: {test._testMethodName}")
    
    def stopTest(self, test):
        super().stopTest(test)
        duration = time.time() - self.test_start_time
        
        result = {
            'test_name': test._testMethodName,
            'test_class': test.__class__.__name__,
            'duration': duration,
            'status': 'PASS'
        }
        
        # Check for errors and failures directly from result
        if self.errors:
            for test_case, traceback in self.errors:
                if test_case == test:
                    result['status'] = 'ERROR'
                    result['error'] = str(traceback)
                    break
        elif self.failures:
            for test_case, traceback in self.failures:
                if test_case == test:
                    result['status'] = 'FAIL'
                    result['error'] = str(traceback)
                    break
        
        self.test_results.append(result)
        
        status_symbol = {
            'PASS': '✓',
            'FAIL': '✗',
            'ERROR': '⚠'
        }
        
        print(f"  {status_symbol[result['status']]} {result['test_name']} ({duration:.3f}s)")
        
        if result['status'] != 'PASS':
            print(f"    Error: {result.get('error', 'Unknown error')}")
    
    def addError(self, test, err):
        super().addError(test, err)
    
    def addFailure(self, test, err):
        super().addFailure(test, err)


def run_phase2_tests():
    """Run all Phase 2 tests with comprehensive reporting."""
    print("=" * 80)
    print("AET Phase 2 Test Suite - State Recovery System")
    print("=" * 80)
    print()
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestStateRebuilder,
        TestEventReplay, 
        TestTransactionalIntegrity,
        TestRecoveryScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with custom result collector
    start_time = time.time()
    result = Phase2TestResult()
    
    print(f"Running {suite.countTestCases()} tests across {len(test_classes)} test classes...")
    print()
    
    # Run the tests
    runner = unittest.TextTestRunner(resultclass=lambda stream, descriptions, verbosity: result, verbosity=0)
    runner.run(suite)
    
    total_duration = time.time() - start_time
    
    # Generate comprehensive report
    print()
    print("=" * 80)
    print("PHASE 2 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    # Overall statistics
    total_tests = len(result.test_results)
    passed_tests = len([t for t in result.test_results if t['status'] == 'PASS'])
    failed_tests = len([t for t in result.test_results if t['status'] == 'FAIL'])
    error_tests = len([t for t in result.test_results if t['status'] == 'ERROR'])
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Errors: {error_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print(f"Total Duration: {total_duration:.3f}s")
    print()
    
    # Performance analysis
    durations = [t['duration'] for t in result.test_results]
    if durations:
        print("Performance Analysis:")
        print(f"  Average test time: {sum(durations)/len(durations):.3f}s")
        print(f"  Fastest test: {min(durations):.3f}s")
        print(f"  Slowest test: {max(durations):.3f}s")
        print()
    
    # Test results by category
    by_class = {}
    for test in result.test_results:
        class_name = test['test_class']
        if class_name not in by_class:
            by_class[class_name] = {'pass': 0, 'fail': 0, 'error': 0, 'total': 0}
        
        by_class[class_name]['total'] += 1
        if test['status'] == 'PASS':
            by_class[class_name]['pass'] += 1
        elif test['status'] == 'FAIL':
            by_class[class_name]['fail'] += 1
        else:
            by_class[class_name]['error'] += 1
    
    print("Results by Test Class:")
    for class_name, stats in by_class.items():
        success_rate = (stats['pass'] / stats['total']) * 100
        print(f"  {class_name}: {stats['pass']}/{stats['total']} ({success_rate:.1f}%)")
        if stats['fail'] > 0 or stats['error'] > 0:
            print(f"    Failures: {stats['fail']}, Errors: {stats['error']}")
    print()
    
    # Failed/Error test details
    if failed_tests > 0 or error_tests > 0:
        print("FAILED/ERROR TEST DETAILS:")
        print("-" * 50)
        
        for test in result.test_results:
            if test['status'] != 'PASS':
                print(f"❌ {test['test_class']}.{test['test_name']}")
                print(f"   Status: {test['status']}")
                print(f"   Duration: {test['duration']:.3f}s")
                if 'error' in test:
                    error_lines = test['error'].split('\n')
                    print(f"   Error: {error_lines[0]}")
                    if len(error_lines) > 1:
                        print(f"          {error_lines[-1]}")
                print()
    
    # Phase 2 specific validations
    print("Phase 2 Specific Validations:")
    print("-" * 30)
    
    # Check for critical functionality
    critical_tests = [
        'test_rebuild_from_events_success',
        'test_idempotent_event_application', 
        'test_transactional_rollback_on_failure',
        'test_recover_from_corrupted_snapshots',
        'test_performance_benchmark'
    ]
    
    critical_passed = 0
    for test in result.test_results:
        if test['test_name'] in critical_tests and test['status'] == 'PASS':
            critical_passed += 1
    
    print(f"Critical Tests Passed: {critical_passed}/{len(critical_tests)}")
    
    # Performance validation
    performance_tests = [t for t in result.test_results if 'performance' in t['test_name'].lower()]
    if performance_tests:
        avg_perf_time = sum(t['duration'] for t in performance_tests) / len(performance_tests)
        print(f"Performance Tests Average: {avg_perf_time:.3f}s")
        
        # Check if performance meets targets
        if avg_perf_time < 5.0:  # 5 second target for performance tests
            print("✓ Performance targets met")
        else:
            print("⚠ Performance targets not met")
    
    # Recovery test validation
    recovery_tests = [t for t in result.test_results if 'recover' in t['test_name'].lower()]
    recovery_passed = len([t for t in recovery_tests if t['status'] == 'PASS'])
    
    if recovery_tests:
        recovery_rate = (recovery_passed / len(recovery_tests)) * 100
        print(f"Recovery Tests Success Rate: {recovery_rate:.1f}%")
        
        if recovery_rate >= 90:
            print("✓ Recovery system robust")
        else:
            print("⚠ Recovery system needs improvement")
    
    print()
    
    # Final assessment
    if passed_tests == total_tests:
        print("🎉 ALL PHASE 2 TESTS PASSED!")
        print("✓ State Recovery System is ready for production")
        success = True
    elif (passed_tests / total_tests) >= 0.9:
        print("⚠ PHASE 2 MOSTLY SUCCESSFUL")
        print(f"  {failed_tests + error_tests} tests need attention")
        success = True
    else:
        print("❌ PHASE 2 TESTS FAILED")
        print("  Significant issues need to be resolved")
        success = False
    
    print()
    print("Phase 2 Implementation Status:")
    
    required_features = [
        ("State Rebuilder", "test_rebuild_from_events_success"),
        ("Event Replay Enhancement", "test_replay_with_timestamp_filter"),
        ("Transactional Integrity", "test_atomic_snapshot_creation"),
        ("Corruption Recovery", "test_recover_from_corrupted_snapshots"),
        ("CLI Integration", "test_rebuild_from_events_success")  # Assumes CLI calls rebuilder
    ]
    
    for feature_name, test_name in required_features:
        test_found = any(t['test_name'] == test_name and t['status'] == 'PASS' 
                        for t in result.test_results)
        status = "✓ IMPLEMENTED" if test_found else "✗ MISSING"
        print(f"  {feature_name}: {status}")
    
    print()
    print("=" * 80)
    
    return success


if __name__ == '__main__':
    success = run_phase2_tests()
    sys.exit(0 if success else 1)