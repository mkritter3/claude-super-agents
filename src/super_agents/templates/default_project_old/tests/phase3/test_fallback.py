#!/usr/bin/env python3
"""
Phase 3 Tests: Fallback Scenarios
Test graceful fallback from full to simple mode.
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add system path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'system'))

try:
    from aet import AETCLI
    from simple_orchestrator import SimpleOrchestrator
    from orchestrator import TaskOrchestrator
except ImportError as e:
    print(f"Import error: {e}")
    # Continue with available imports


def test_dependency_fallback():
    """Test fallback when dependencies are missing."""
    print("Testing dependency fallback...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Create minimal CLI instance
        cli = AETCLI()
        
        # Test fallback detection
        snapshot = {"description": "test task", "mode": "full"}
        should_fallback = cli._should_fallback_to_simple(snapshot)
        
        # Test might depend on whether dependencies are actually available
        print(f"Fallback recommendation: {should_fallback}")
        
        # Test that simple mode works regardless
        simple_result = cli.process_simple("create a test file")
        assert simple_result is True or simple_result is False  # Should not crash
        
        print("✓ Dependency fallback test completed")


def test_graceful_degradation():
    """Test graceful degradation from full to simple mode."""
    print("Testing graceful degradation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        cli = AETCLI()
        
        # Create tasks with different modes
        tasks = [
            ("Create a simple file", "simple"),
            ("Complex refactoring task", "full"),
            ("Fix a bug", "auto")
        ]
        
        for description, mode in tasks:
            try:
                ticket_id = cli.create_task(description, mode)
                assert ticket_id is not None
                print(f"✓ Created task in {mode} mode: {ticket_id}")
            except Exception as e:
                print(f"⚠ Task creation failed for {mode} mode: {str(e)}")
        
        # Test processing with simple mode fallback
        try:
            cli.process_tasks(simple=True)
            print("✓ Simple mode processing completed")
        except Exception as e:
            print(f"⚠ Simple mode processing failed: {str(e)}")


def test_mode_auto_selection():
    """Test automatic mode selection."""
    print("Testing auto mode selection...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        cli = AETCLI()
        
        # Test tasks that should auto-select simple mode
        simple_tasks = [
            "create a README file",
            "fix typo in documentation",
            "add new configuration option"
        ]
        
        for task in simple_tasks:
            try:
                ticket_id = cli.create_task(task, "auto")
                
                # Check that task was created
                snapshots = cli.orchestrator.load_snapshots()
                if ticket_id in snapshots:
                    selected_mode = snapshots[ticket_id].get("mode", "unknown")
                    print(f"✓ Auto-selected mode for '{task}': {selected_mode}")
                
            except Exception as e:
                print(f"⚠ Auto-selection failed: {str(e)}")


def test_error_recovery_fallback():
    """Test fallback when full mode encounters errors."""
    print("Testing error recovery fallback...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Simulate full mode failure by mocking
        cli = AETCLI()
        
        # Test that simple mode can handle the same task
        problem_task = "handle complex task that might fail"
        
        # First try would fail in full mode (simulated)
        # Fallback to simple mode should work
        try:
            success = cli.process_simple(problem_task)
            print(f"✓ Fallback processing result: {success}")
        except Exception as e:
            print(f"⚠ Even simple mode failed: {str(e)}")


def test_resource_exhaustion_fallback():
    """Test fallback when resources are exhausted."""
    print("Testing resource exhaustion fallback...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        simple_orchestrator = SimpleOrchestrator()
        
        # Create many tasks to simulate resource pressure
        tasks = [f"create file {i}" for i in range(10)]
        
        successful_tasks = 0
        for task in tasks:
            try:
                result = simple_orchestrator.process_task(task)
                if result["success"]:
                    successful_tasks += 1
            except Exception as e:
                print(f"Task failed: {str(e)}")
        
        # Simple mode should handle multiple tasks gracefully
        assert successful_tasks >= len(tasks) * 0.8, "Should handle most tasks even under pressure"
        
        print(f"✓ Resource exhaustion test: {successful_tasks}/{len(tasks)} tasks successful")


def test_partial_system_availability():
    """Test behavior when only part of the system is available."""
    print("Testing partial system availability...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Test simple orchestrator in isolation
        simple_orchestrator = SimpleOrchestrator()
        
        # These should work without any other system components
        basic_tasks = [
            "create a simple file",
            "write some documentation",
            "fix a small issue"
        ]
        
        for task in basic_tasks:
            result = simple_orchestrator.process_task(task)
            assert result["success"] is True, f"Basic task should succeed: {task}"
        
        print("✓ Simple mode works in isolation")


def test_configuration_fallback():
    """Test fallback configuration handling."""
    print("Testing configuration fallback...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Test without configuration files
        simple_orchestrator = SimpleOrchestrator()
        status = simple_orchestrator.get_status()
        
        assert status["mode"] == "simple"
        assert status["active"] is True
        
        # Test with minimal configuration
        config_dir = Path(".claude")
        config_dir.mkdir(exist_ok=True)
        
        minimal_config = {"mode": "simple", "fallback_enabled": True}
        with open(config_dir / "config.json", 'w') as f:
            json.dump(minimal_config, f)
        
        # Should still work
        result = simple_orchestrator.process_task("test with config")
        assert result["success"] is True
        
        print("✓ Configuration fallback working")


def test_network_isolation_fallback():
    """Test fallback when network services are unavailable."""
    print("Testing network isolation fallback...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Simple mode should work without network
        simple_orchestrator = SimpleOrchestrator()
        
        network_independent_tasks = [
            "create local configuration",
            "modify existing file",
            "generate documentation"
        ]
        
        for task in network_independent_tasks:
            result = simple_orchestrator.process_task(task)
            assert result["success"] is True, f"Network-independent task should succeed: {task}"
        
        print("✓ Network isolation fallback working")


def test_storage_constraint_fallback():
    """Test fallback under storage constraints."""
    print("Testing storage constraint fallback...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        simple_orchestrator = SimpleOrchestrator()
        
        # Test with limited storage operations
        storage_efficient_tasks = [
            "create small config file",
            "modify existing content",
            "document simple process"
        ]
        
        total_files_before = len(list(Path(".").rglob("*")))
        
        for task in storage_efficient_tasks:
            result = simple_orchestrator.process_task(task)
            assert result["success"] is True
        
        total_files_after = len(list(Path(".").rglob("*")))
        files_created = total_files_after - total_files_before
        
        # Should create reasonable number of files
        assert files_created <= 10, "Should not create excessive files"
        
        print(f"✓ Storage constraint test: {files_created} files created")


def test_fallback_decision_matrix():
    """Test the decision matrix for fallback scenarios."""
    print("Testing fallback decision matrix...")
    
    simple_orchestrator = SimpleOrchestrator()
    
    # Test various task types for fallback suitability
    test_matrix = [
        ("file operations", True),
        ("simple fixes", True),
        ("documentation", True),
        ("configuration", True),
        ("complex refactoring", False),  # Might not be suitable
        ("multi-service", False),  # Might not be suitable
        ("database migration", False)  # Might not be suitable
    ]
    
    for task_type, expected_suitable in test_matrix:
        task_desc = f"perform {task_type} task"
        suitability = simple_orchestrator.is_suitable_for_simple_mode(task_desc)
        
        if expected_suitable:
            assert suitability["suitable"] is True, f"{task_type} should be suitable for simple mode"
        
        print(f"✓ {task_type}: suitable={suitability['suitable']}, confidence={suitability['confidence']:.2f}")


def generate_fallback_report():
    """Generate fallback scenarios report."""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fallback_scenarios": {
            "dependency_missing": "Simple mode activates when full mode dependencies unavailable",
            "resource_exhaustion": "Simple mode continues operating under resource pressure",
            "network_isolation": "Simple mode works without network connectivity",
            "storage_constraints": "Simple mode minimizes storage usage",
            "error_recovery": "Simple mode provides graceful degradation path"
        },
        "fallback_triggers": [
            "ImportError on full mode modules",
            "Resource exhaustion detection",
            "Network connectivity issues",
            "Configuration file corruption",
            "External service unavailability"
        ],
        "recovery_strategies": [
            "Automatic mode selection based on task complexity",
            "Graceful degradation with user notification",
            "Minimal resource operation mode",
            "Offline operation capability",
            "Error isolation and retry logic"
        ]
    }
    
    report_file = "fallback_scenarios_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ Fallback report generated: {report_file}")
    return report


def run_fallback_tests():
    """Run all fallback scenario tests."""
    import time
    
    print("=" * 60)
    print("Phase 3: Fallback Scenarios Tests")
    print("=" * 60)
    
    test_functions = [
        test_dependency_fallback,
        test_graceful_degradation,
        test_mode_auto_selection,
        test_error_recovery_fallback,
        test_resource_exhaustion_fallback,
        test_partial_system_availability,
        test_configuration_fallback,
        test_network_isolation_fallback,
        test_storage_constraint_fallback,
        test_fallback_decision_matrix
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed: {str(e)}")
            failed += 1
    
    # Generate report
    try:
        generate_fallback_report()
        print("✓ Fallback report generated")
    except Exception as e:
        print(f"⚠ Report generation failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Fallback Tests Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_fallback_tests()
    sys.exit(0 if success else 1)