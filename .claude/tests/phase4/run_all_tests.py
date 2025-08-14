#!/usr/bin/env python3
"""
Test runner for Phase 4 observability tests.
Runs all observability-related tests and provides comprehensive reporting.
"""
import unittest
import sys
import time
import os
from pathlib import Path
from io import StringIO

# Add system directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'system'))

# Import test modules
from test_metrics import TestMetricsCollection, TestMetricsIntegration
from test_tracing import TestTracingConfiguration, TestTracingHelpers, TestFallbackTracing, TestTracingPerformance, TestTracingIntegration
from test_health_endpoints import TestHealthEndpoints, TestHealthEndpointIntegration, TestMonitoringWorkflow
from test_performance_impact import TestPerformanceImpact, TestObservabilityScaling

class Phase4TestRunner:
    """Custom test runner for Phase 4 observability tests."""
    
    def __init__(self):
        self.start_time = None
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.errors = []
        
    def run_all_tests(self):
        """Run all Phase 4 tests and collect results."""
        print("="*80)
        print("PHASE 4 OBSERVABILITY TESTS")
        print("="*80)
        print()
        
        self.start_time = time.time()
        
        # Define test suites
        test_suites = [
            ("Metrics Collection", [
                TestMetricsCollection,
                TestMetricsIntegration
            ]),
            ("Tracing Configuration", [
                TestTracingConfiguration,
                TestTracingHelpers,
                TestFallbackTracing,
                TestTracingPerformance,
                TestTracingIntegration
            ]),
            ("Health Endpoints", [
                TestHealthEndpoints,
                TestHealthEndpointIntegration,
                TestMonitoringWorkflow
            ]),
            ("Performance Impact", [
                TestPerformanceImpact,
                TestObservabilityScaling
            ])
        ]
        
        # Run each test suite
        for suite_name, test_classes in test_suites:
            print(f"\n{'='*60}")
            print(f"RUNNING: {suite_name}")
            print(f"{'='*60}")
            
            suite_results = self._run_test_suite(test_classes)
            self.results[suite_name] = suite_results
        
        # Generate final report
        self._generate_final_report()
    
    def _run_test_suite(self, test_classes):
        """Run a specific test suite."""
        suite_results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'duration': 0
        }
        
        suite_start = time.time()
        
        for test_class in test_classes:
            print(f"\n  Running {test_class.__name__}...")
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromTestCase(test_class)
            
            # Run tests with custom result collector
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=2)
            result = runner.run(suite)
            
            # Collect results
            suite_results['total'] += result.testsRun
            suite_results['passed'] += result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
            suite_results['failed'] += len(result.failures)
            suite_results['skipped'] += len(result.skipped)
            
            # Collect errors and failures
            for test, error in result.errors:
                suite_results['errors'].append(f"{test}: {error}")
                self.errors.append(f"{test_class.__name__}.{test}: {error}")
            
            for test, failure in result.failures:
                suite_results['errors'].append(f"{test}: {failure}")
                self.errors.append(f"{test_class.__name__}.{test}: {failure}")
            
            # Print summary for this test class
            class_passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
            print(f"    {class_passed}/{result.testsRun} tests passed", end="")
            if result.skipped:
                print(f" ({len(result.skipped)} skipped)", end="")
            if result.failures or result.errors:
                print(f" ({len(result.failures + result.errors)} failed)", end="")
            print()
        
        suite_results['duration'] = time.time() - suite_start
        
        # Update totals
        self.total_tests += suite_results['total']
        self.passed_tests += suite_results['passed']
        self.failed_tests += suite_results['failed']
        self.skipped_tests += suite_results['skipped']
        
        return suite_results
    
    def _generate_final_report(self):
        """Generate comprehensive final report."""
        total_duration = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("PHASE 4 TEST RESULTS SUMMARY")
        print("="*80)
        
        # Overall statistics
        print(f"\nOverall Results:")
        print(f"  Total Tests:    {self.total_tests}")
        print(f"  Passed:         {self.passed_tests}")
        print(f"  Failed:         {self.failed_tests}")
        print(f"  Skipped:        {self.skipped_tests}")
        print(f"  Success Rate:   {(self.passed_tests/self.total_tests)*100:.1f}%" if self.total_tests > 0 else "  Success Rate:   N/A")
        print(f"  Total Duration: {total_duration:.2f}s")
        
        # Per-suite breakdown
        print(f"\nPer-Suite Results:")
        for suite_name, results in self.results.items():
            success_rate = (results['passed']/results['total'])*100 if results['total'] > 0 else 0
            print(f"  {suite_name:<20} {results['passed']}/{results['total']} ({success_rate:.1f}%) - {results['duration']:.2f}s")
        
        # Check for specific observability features
        print(f"\nObservability Feature Status:")
        self._check_observability_features()
        
        # Performance summary
        print(f"\nPerformance Summary:")
        self._generate_performance_summary()
        
        # Errors and failures
        if self.errors:
            print(f"\nErrors and Failures ({len(self.errors)}):")
            for i, error in enumerate(self.errors[:10], 1):  # Show first 10 errors
                print(f"  {i}. {error.split(':')[0]}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
        
        # Recommendations
        print(f"\nRecommendations:")
        self._generate_recommendations()
        
        # Final status
        print("\n" + "="*80)
        if self.failed_tests == 0:
            print("✅ ALL TESTS PASSED - Phase 4 observability is ready for production!")
        elif self.failed_tests < self.total_tests * 0.1:  # Less than 10% failure rate
            print("⚠️  MOSTLY SUCCESSFUL - Minor issues detected, review failures")
        else:
            print("❌ SIGNIFICANT ISSUES - Major problems detected, requires attention")
        print("="*80)
        
        return self.failed_tests == 0
    
    def _check_observability_features(self):
        """Check availability of observability features."""
        features = {
            "Prometheus Client": self._check_prometheus(),
            "OpenTelemetry": self._check_opentelemetry(),
            "PSUtil (System Metrics)": self._check_psutil(),
            "Requests (Health Tests)": self._check_requests()
        }
        
        for feature, available in features.items():
            status = "✅ Available" if available else "❌ Missing"
            print(f"    {feature:<25} {status}")
    
    def _check_prometheus(self):
        """Check if Prometheus client is available."""
        try:
            import prometheus_client
            return True
        except ImportError:
            return False
    
    def _check_opentelemetry(self):
        """Check if OpenTelemetry is available."""
        try:
            import opentelemetry
            return True
        except ImportError:
            return False
    
    def _check_psutil(self):
        """Check if psutil is available."""
        try:
            import psutil
            return True
        except ImportError:
            return False
    
    def _check_requests(self):
        """Check if requests is available."""
        try:
            import requests
            return True
        except ImportError:
            return False
    
    def _generate_performance_summary(self):
        """Generate performance impact summary."""
        # Try to get performance data from metrics collector
        try:
            from metrics_collector import get_metrics
            metrics = get_metrics()
            impact = metrics.get_performance_impact()
            
            print(f"    Metrics Overhead:   {impact.get('avg_overhead_ms', 0):.3f}ms avg")
            print(f"    Max Overhead:       {impact.get('max_overhead_ms', 0):.3f}ms")
            
            if impact.get('avg_overhead_ms', 0) < 1.0:
                print(f"    Performance Impact: ✅ Excellent (< 1ms)")
            elif impact.get('avg_overhead_ms', 0) < 5.0:
                print(f"    Performance Impact: ✅ Good (< 5ms)")
            else:
                print(f"    Performance Impact: ⚠️  High (> 5ms)")
                
        except Exception as e:
            print(f"    Performance data not available: {e}")
    
    def _generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check failure rate
        if self.failed_tests > 0:
            failure_rate = (self.failed_tests / self.total_tests) * 100
            if failure_rate > 20:
                recommendations.append("🔴 High failure rate - Review system dependencies and configuration")
            elif failure_rate > 10:
                recommendations.append("🟡 Moderate failure rate - Some observability features may be limited")
        
        # Check for missing dependencies
        if not self._check_prometheus():
            recommendations.append("📦 Install prometheus_client for full metrics support: pip install prometheus_client")
        
        if not self._check_opentelemetry():
            recommendations.append("📦 Install OpenTelemetry for distributed tracing: pip install opentelemetry-api opentelemetry-sdk")
        
        if not self._check_psutil():
            recommendations.append("📦 Install psutil for system metrics: pip install psutil")
        
        # Performance recommendations
        try:
            from metrics_collector import get_metrics
            impact = get_metrics().get_performance_impact()
            if impact.get('avg_overhead_ms', 0) > 5.0:
                recommendations.append("⚡ Consider reducing metrics verbosity for better performance")
        except:
            pass
        
        # General recommendations
        if self.skipped_tests > self.total_tests * 0.3:
            recommendations.append("⚠️  Many tests skipped - Install optional dependencies for full coverage")
        
        if not recommendations:
            recommendations.append("✅ All observability components are properly configured!")
        
        for rec in recommendations:
            print(f"    {rec}")

def main():
    """Main test runner entry point."""
    runner = Phase4TestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()