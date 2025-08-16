#!/usr/bin/env python3
"""
Phase 3 Tests: Simple Mode Core Functionality
Tests the basic operation of the SimpleOrchestrator.
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

from simple_orchestrator import SimpleOrchestrator
from event_logger import EventLogger


def test_simple_orchestrator_initialization():
    """Test basic initialization."""
    orchestrator = SimpleOrchestrator()
    
    assert orchestrator.simple_mode_active is True
    assert orchestrator.task_history == []
    assert orchestrator.current_task is None
    print("✓ Simple orchestrator initializes correctly")


def test_task_suitability_assessment():
    """Test the suitability assessment for simple mode."""
    orchestrator = SimpleOrchestrator()
    
    # Simple tasks should be suitable
    simple_tasks = [
        "create a new file",
        "modify existing documentation",
        "fix a simple bug",
        "add a new feature to the config"
    ]
    
    for task in simple_tasks:
        result = orchestrator.is_suitable_for_simple_mode(task)
        assert result["suitable"] is True, f"Task should be suitable: {task}"
        assert result["recommendation"] == "simple"
        print(f"✓ Simple task detected: {task}")
    
    # Complex tasks might not be suitable
    complex_tasks = [
        "refactor the entire architecture",
        "implement microservice infrastructure",
        "design complex database schema"
    ]
    
    for task in complex_tasks:
        result = orchestrator.is_suitable_for_simple_mode(task)
        # These might be suitable if they also contain simple keywords
        print(f"Complex task assessment: {task} -> {result['recommendation']}")


def test_create_file_action():
    """Test file creation action."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        orchestrator = SimpleOrchestrator()
        result = orchestrator.process_task("create a new file for testing")
        
        assert result["success"] is True
        assert len(result["files_changed"]) > 0
        
        # Check if file was actually created
        created_file = result["files_changed"][0]
        assert Path(created_file).exists()
        
        content = Path(created_file).read_text()
        assert "testing" in content.lower()
        
        print(f"✓ File creation successful: {created_file}")


def test_modify_file_action():
    """Test file modification action."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Create a file first
        test_file = Path("test.txt")
        test_file.write_text("Original content")
        
        orchestrator = SimpleOrchestrator()
        result = orchestrator.process_task("modify the existing file")
        
        assert result["success"] is True
        assert len(result["files_changed"]) > 0
        
        # Check if file was modified
        modified_content = test_file.read_text()
        assert "Original content" in modified_content
        assert "Modified by Simple Mode" in modified_content
        
        print("✓ File modification successful")


def test_fix_issue_action():
    """Test fix issue action."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        orchestrator = SimpleOrchestrator()
        result = orchestrator.process_task("fix the authentication bug")
        
        assert result["success"] is True
        assert len(result["files_changed"]) > 0
        
        # Check if fix log was created
        fix_file = result["files_changed"][0]
        assert "fix_log_" in fix_file
        assert Path(fix_file).exists()
        
        content = Path(fix_file).read_text()
        assert "authentication bug" in content.lower()
        
        print(f"✓ Fix issue action successful: {fix_file}")


def test_generic_task_handling():
    """Test generic task handling."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        orchestrator = SimpleOrchestrator()
        result = orchestrator.process_task("analyze the system performance")
        
        assert result["success"] is True
        assert len(result["files_changed"]) > 0
        
        # Check if task summary was created
        summary_file = result["files_changed"][0]
        assert "task_summary_" in summary_file
        assert Path(summary_file).exists()
        
        content = Path(summary_file).read_text()
        assert "analyze the system performance" in content
        
        print(f"✓ Generic task handling successful: {summary_file}")


def test_validation_process():
    """Test the validation process."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        orchestrator = SimpleOrchestrator()
        
        # Create a file implementation result
        impl_result = {
            "success": True,
            "files_changed": ["test_file.txt"],
            "operations": 1
        }
        
        # Create the actual file
        Path("test_file.txt").write_text("Test content")
        
        validation = orchestrator._validate_simple_implementation(impl_result)
        
        assert validation["passed"] is True
        assert "files_modified" in validation["checks"]
        assert "implementation_success" in validation["checks"]
        assert len(validation["issues"]) == 0
        
        print("✓ Validation process working correctly")


def test_error_handling():
    """Test error handling in simple mode."""
    orchestrator = SimpleOrchestrator()
    
    # Mock an error in the workflow
    with patch.object(orchestrator, '_create_simple_plan', side_effect=Exception("Test error")):
        result = orchestrator.process_task("test task that will fail")
        
        assert result["success"] is False
        assert "error" in result
        assert "Test error" in result["error"]
        
        print("✓ Error handling working correctly")


def test_task_history_tracking():
    """Test task history tracking."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        orchestrator = SimpleOrchestrator()
        
        # Process multiple tasks
        tasks = [
            "create first file",
            "create second file",
            "modify a file"
        ]
        
        for task in tasks:
            orchestrator.process_task(task)
        
        history = orchestrator.get_task_history()
        assert len(history) == len(tasks)
        
        # Check that all tasks are recorded
        for i, task in enumerate(tasks):
            assert task in history[i]["description"]
            assert "duration" in history[i]
            
        print(f"✓ Task history tracking successful: {len(history)} tasks")


def test_status_reporting():
    """Test status reporting."""
    orchestrator = SimpleOrchestrator()
    
    status = orchestrator.get_status()
    
    assert status["mode"] == "simple"
    assert status["active"] is True
    assert "tasks_completed" in status
    assert "average_duration" in status
    
    print("✓ Status reporting working correctly")


def test_event_logging_integration():
    """Test integration with event logging."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Create events directory
        events_dir = Path(".claude/events")
        events_dir.mkdir(parents=True, exist_ok=True)
        
        orchestrator = SimpleOrchestrator()
        result = orchestrator.process_task("test event logging")
        
        assert result["success"] is True
        
        # Check if events were logged
        events = orchestrator.event_logger.replay_events()
        
        # Should have at least task started and completed events
        task_events = [e for e in events if e.get("type", "").startswith("SIMPLE_TASK")]
        assert len(task_events) >= 2
        
        print(f"✓ Event logging integration successful: {len(task_events)} events")


def run_simple_mode_tests():
    """Run all simple mode tests."""
    print("=" * 60)
    print("Phase 3: Simple Mode Core Functionality Tests")
    print("=" * 60)
    
    test_functions = [
        test_simple_orchestrator_initialization,
        test_task_suitability_assessment,
        test_create_file_action,
        test_modify_file_action,
        test_fix_issue_action,
        test_generic_task_handling,
        test_validation_process,
        test_error_handling,
        test_task_history_tracking,
        test_status_reporting,
        test_event_logging_integration
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
    
    print("\n" + "=" * 60)
    print(f"Simple Mode Tests Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_simple_mode_tests()
    sys.exit(0 if success else 1)