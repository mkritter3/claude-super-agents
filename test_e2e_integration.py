#!/usr/bin/env python3
"""
End-to-End Integration Test for AET System
Tests the critical architectural issues identified by Gemini
"""

import os
import sys
import json
import time
import sqlite3
import tempfile
from pathlib import Path

# Add system path for imports
sys.path.insert(0, '.claude/system')

from parallel_executor import ParallelExecutor
from operational_orchestrator import OperationalOrchestrator
from orchestrator_bridge import OrchestratorBridge

def test_orchestrator_to_parallel_executor_connection():
    """
    Test 1: Verify that the orchestrator submits tasks to parallel executor
    This test uses the OrchestratorBridge to fix the disconnection
    """
    print("\n" + "="*60)
    print("TEST 1: Orchestrator → Parallel Executor Connection (WITH BRIDGE)")
    print("="*60)
    
    # Setup
    project_dir = Path.cwd()
    bridge = OrchestratorBridge(project_dir)  # Use the bridge instead
    executor = ParallelExecutor(project_dir)
    
    # Clear the task queue
    conn = sqlite3.connect(str(executor.queue_db))
    conn.execute("DELETE FROM task_queue")
    conn.commit()
    conn.close()
    
    # Create a test event
    test_event = {
        "timestamp": time.time(),
        "event_type": "CODE_COMMITTED",
        "agent": "system",
        "data": {
            "files_changed": ["src/main.py", "tests/test_main.py", "src/api.py"],
            "commit_hash": "abc123",
            "message": "Test commit for E2E testing"
        }
    }
    
    print(f"✓ Created test event: CODE_COMMITTED")
    
    # Process the event with the BRIDGE
    print("Processing event with OrchestratorBridge...")
    task_ids = bridge.process_event(test_event)
    
    print(f"Bridge returned task IDs: {task_ids}")
    
    # Check if tasks were created in parallel executor queue
    conn = sqlite3.connect(str(executor.queue_db))
    cursor = conn.execute("SELECT COUNT(*) FROM task_queue")
    task_count = cursor.fetchone()[0]
    
    # Also get details of the tasks
    cursor = conn.execute("SELECT agent, priority, status FROM task_queue")
    tasks = cursor.fetchall()
    conn.close()
    
    print(f"\nTasks in ParallelExecutor queue: {task_count}")
    for agent, priority, status in tasks:
        print(f"  - {agent} (priority: {priority}, status: {status})")
    
    # Check trigger files created (should be fewer/none with bridge)
    trigger_dir = project_dir / ".claude" / "triggers"
    trigger_files = list(trigger_dir.glob("*_trigger_*.json"))
    print(f"Trigger files created: {len(trigger_files)}")
    
    # ASSERTION: This should PASS with the bridge
    try:
        assert task_count > 0, "No tasks submitted to ParallelExecutor queue!"
        assert len(task_ids) == task_count, f"Task ID mismatch: returned {len(task_ids)} but found {task_count}"
        print("\n✅ TEST PASSED: Bridge correctly submits to ParallelExecutor")
        return True
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

def test_duplicate_trigger_creation():
    """
    Test 2: Verify that multiple orchestration systems create duplicate triggers
    This test should initially show duplication issues
    """
    print("\n" + "="*60)
    print("TEST 2: Duplicate Trigger Detection")
    print("="*60)
    
    project_dir = Path.cwd()
    trigger_dir = project_dir / ".claude" / "triggers"
    
    # Clear existing triggers
    for trigger_file in trigger_dir.glob("*.json"):
        trigger_file.unlink()
    
    # Simulate a commit event that would trigger multiple systems
    test_event = {
        "timestamp": time.time(),
        "event_type": "CODE_COMMITTED",
        "files": ["src/api.py"],
        "commit_hash": "test123"
    }
    
    # Write to event log (triggers event_watchers.py)
    event_log = project_dir / ".claude" / "events" / "log.ndjson"
    with open(event_log, 'a') as f:
        json.dump(test_event, f)
        f.write('\n')
    
    # Wait for async processing
    time.sleep(2)
    
    # Count triggers for the same agent
    trigger_files = list(trigger_dir.glob("*.json"))
    agent_triggers = {}
    
    for trigger_file in trigger_files:
        # Parse agent name from filename
        agent_name = trigger_file.stem.split('_trigger_')[0]
        if agent_name not in agent_triggers:
            agent_triggers[agent_name] = []
        agent_triggers[agent_name].append(trigger_file)
    
    # Check for duplicates
    duplicates = []
    for agent, files in agent_triggers.items():
        if len(files) > 1:
            duplicates.append((agent, len(files)))
            print(f"⚠️  Agent '{agent}' has {len(files)} trigger files (duplicate!)")
    
    # ASSERTION: We expect duplicates initially
    if duplicates:
        print(f"\n❌ TEST CONFIRMS ISSUE: Found {len(duplicates)} agents with duplicate triggers")
        return False
    else:
        print("\n✅ TEST PASSED: No duplicate triggers found")
        return True

def test_end_to_end_flow():
    """
    Test 3: Full end-to-end flow from commit to agent execution
    This should work after fixes are applied
    """
    print("\n" + "="*60)
    print("TEST 3: End-to-End Flow (Commit → Agent Execution)")
    print("="*60)
    
    project_dir = Path.cwd()
    
    # This test will only pass after we fix the architecture
    print("⏸️  This test requires architectural fixes to pass")
    print("   It validates: Commit → Hook → Log → Orchestrator → Executor → Agent")
    
    # Steps:
    # 1. Create a test file and commit it
    # 2. Verify post-commit hook writes to log.ndjson
    # 3. Verify orchestrator processes the event
    # 4. Verify task appears in parallel executor queue
    # 5. Verify agent would be executed
    
    return False  # Will implement after fixes

def main():
    """Run all E2E tests"""
    print("\n" + "="*70)
    print(" AET SYSTEM END-TO-END INTEGRATION TESTS")
    print(" Testing critical architectural issues identified by Gemini")
    print("="*70)
    
    results = []
    
    # Test 1: Connection between systems
    results.append(("Orchestrator→Executor Connection", 
                   test_orchestrator_to_parallel_executor_connection()))
    
    # Test 2: Duplicate triggers
    results.append(("Duplicate Trigger Detection",
                   test_duplicate_trigger_creation()))
    
    # Test 3: Full E2E (will fail until fixes applied)
    results.append(("End-to-End Flow",
                   test_end_to_end_flow()))
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n  ⚠️  Some tests failed, confirming architectural issues")
        print("  Next step: Apply fixes to connect systems properly")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)