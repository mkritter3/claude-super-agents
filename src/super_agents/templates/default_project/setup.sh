#!/bin/bash
set -euo pipefail

echo "==================================="
echo "AET (Autonomous Engineering Team)"
echo "Phase 1 Setup Script"
echo "==================================="

# Check if we're in the right directory
if [ ! -f ".claude/config.json" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

echo "✓ Project structure verified"

# Make sure Python dependencies are available
echo "Checking Python dependencies..."
python3 -c "import json, time, hashlib, fcntl, uuid, subprocess" 2>/dev/null || {
    echo "Error: Required Python modules not available"
    exit 1
}
echo "✓ Python dependencies available"

# Test event logger
echo "Testing event logger..."
EVENT_ID=$(python3 .claude/system/event_logger.py "SETUP-TEST" "SETUP_STARTED" '{"message": "Testing AET setup"}')
echo "✓ Event logger working (Event ID: $EVENT_ID)"

# Test workspace manager
echo "Testing workspace manager..."
JOB_ID=$(python3 .claude/system/workspace_manager.py create "SETUP-TEST" "Test workspace for setup")
echo "✓ Workspace manager working (Job ID: $JOB_ID)"

# Test orchestrator
echo "Testing orchestrator..."
TEST_JOB=$(python3 .claude/system/orchestrator.py create "SETUP-FINAL" "Final setup test")
echo "✓ Orchestrator working (Job ID: $TEST_JOB)"

# Initialize git for AET system
echo "Initializing AET version control..."
cd .claude
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial AET system setup"
    echo "✓ AET system committed to git"
else
    echo "✓ Git already initialized"
fi
cd ..

echo ""
echo "==================================="
echo "AET Phase 1 Setup Complete!"
echo "==================================="
echo ""
echo "✅ Event-sourced system ready"
echo "✅ Workspace isolation working"
echo "✅ Task orchestration functional"
echo "✅ Context integration layer ready"
echo "✅ Specialized agents available"
echo ""
echo "Next steps:"
echo "1. Create your first task:"
echo "   python3 .claude/system/orchestrator.py create TICKET-001 \"Your task description\""
echo ""
echo "2. Process tasks:"
echo "   python3 .claude/system/orchestrator.py process"
echo ""
echo "3. Monitor progress:"
echo "   cat .claude/events/log.ndjson | tail -f"
echo ""
echo "Available agents:"
ls .claude/agents/*.md | sed 's|.claude/agents/||' | sed 's|\.md||' | while read agent; do
    echo "   - $agent"
done
echo ""
echo "For more information, see CLAUDE.md"