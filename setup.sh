#!/bin/bash

# AET System Setup Script
# This script initializes a clean AET installation

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     AET - Autonomous Engineering Team Setup              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Setting up directory structure..."

# Create necessary directories
mkdir -p .claude/{events,workspaces,snapshots,registry,backups,dlq,adr,summaries,commands,logs,state,triggers,ambient,test_reports,monitoring}

echo "✅ Directories created"

# Initialize empty event log if it doesn't exist
if [ ! -f .claude/events/log.ndjson ]; then
    touch .claude/events/log.ndjson
    echo "✅ Event log initialized"
fi

# Initialize task snapshots
if [ ! -f .claude/snapshots/tasks.json ]; then
    echo "{}" > .claude/snapshots/tasks.json
    echo "✅ Task snapshots initialized"
fi

# Initialize the SQLite database
echo "🗄️  Initializing database..."
if [ -f .claude/system/schema.sql ]; then
    sqlite3 .claude/registry/registry.db < .claude/system/schema.sql 2>/dev/null || true
    echo "✅ Database initialized"
else
    echo "⚠️  Schema file not found, skipping database initialization"
fi

# Make scripts executable
chmod +x .claude/aet 2>/dev/null || true
chmod +x .claude/setup.sh 2>/dev/null || true
chmod +x .claude/system/*.py 2>/dev/null || true

echo "✅ Scripts made executable"

# Check Python installation
echo ""
echo "🐍 Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check Git installation
echo "🔧 Checking Git installation..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | grep -oE '[0-9]+\.[0-9]+')
    echo "✅ Git $GIT_VERSION found"
else
    echo "❌ Git not found. Please install Git."
    exit 1
fi

# Check SQLite installation
echo "🗄️  Checking SQLite installation..."
if command -v sqlite3 &> /dev/null; then
    SQLITE_VERSION=$(sqlite3 --version | grep -oE '[0-9]+\.[0-9]+')
    echo "✅ SQLite $SQLITE_VERSION found"
else
    echo "❌ SQLite3 not found. Please install SQLite3."
    exit 1
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ -f requirements-upgrade.txt ]; then
    if command -v pip3 &> /dev/null; then
        pip3 install -q -r requirements-upgrade.txt 2>/dev/null && echo "✅ Python dependencies installed" || {
            echo "⚠️  Some dependencies failed to install. Trying with --user flag..."
            pip3 install -q --user -r requirements-upgrade.txt && echo "✅ Python dependencies installed (user)" || {
                echo "⚠️  Could not install all dependencies. Manual installation may be required."
                echo "    Run: pip3 install -r requirements-upgrade.txt"
            }
        }
    else
        echo "⚠️  pip3 not found. Please install dependencies manually:"
        echo "    pip3 install -r requirements-upgrade.txt"
    fi
else
    echo "⚠️  requirements-upgrade.txt not found"
fi

# Run system initialization
echo ""
echo "🚀 Initializing AET system..."
cd "$SCRIPT_DIR"
python3 .claude/system/aet.py init 2>/dev/null || {
    echo "⚠️  Note: Full initialization will complete on first task creation"
}

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           ✅ AET System Setup Complete!                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Quick Start Commands:"
echo ""
echo "  Create a task:"
echo "    ./.claude/aet create \"Your task description\""
echo ""
echo "  Process tasks:"
echo "    ./.claude/aet process"
echo ""
echo "  Check status:"
echo "    ./.claude/aet status"
echo ""
echo "  View help:"
echo "    ./.claude/aet --help"
echo ""
echo "📚 Full documentation: README.md"
echo ""
echo "⚠️  Important: Start the Knowledge Manager before using the system:"
echo "    cd .claude/system && python3 km_server.py"
echo ""