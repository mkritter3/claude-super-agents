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
    # Check if database exists and is valid first
    if [ -f .claude/registry/registry.db ]; then
        if ! sqlite3 .claude/registry/registry.db "SELECT 1 FROM sqlite_master LIMIT 1;" &>/dev/null; then
            echo "⚠️  Existing database appears corrupted, recreating..."
            rm -f .claude/registry/registry.db
        fi
    fi
    
    # Initialize database and capture errors
    if sqlite3 .claude/registry/registry.db < .claude/system/schema.sql; then
        echo "✅ Database initialized successfully"
    else
        echo "❌ Database initialization failed"
        echo "   Please check .claude/system/schema.sql for errors"
        exit 1
    fi
else
    echo "⚠️  Schema file not found, skipping database initialization"
fi

# Make scripts executable
echo "🔧 Setting script permissions..."
if [ -f .claude/aet ]; then
    chmod +x .claude/aet
fi

if [ -f .claude/setup.sh ]; then
    chmod +x .claude/setup.sh
fi

# Make Python scripts executable
if [ -d .claude/system ]; then
    find .claude/system -name "*.py" -exec chmod +x {} \;
fi

echo "✅ Scripts made executable"

# Install enhanced dependencies (Phase 1.4, 1.5)
echo ""
echo "📦 Checking Python dependencies for enhanced features..."
if command -v pip3 &> /dev/null; then
    # Check if psutil is installed (Phase 1.4)
    if ! python3 -c "import psutil" 2>/dev/null; then
        echo "Installing psutil for process management..."
        pip3 install -q psutil 2>/dev/null || pip3 install -q --user psutil 2>/dev/null || {
            echo "⚠️  Could not install psutil. Process management features may be limited."
        }
    fi
    
    # Check if cryptography is installed (Phase 1.5)
    if ! python3 -c "import cryptography" 2>/dev/null; then
        echo "Installing cryptography for secure credential storage..."
        pip3 install -q cryptography 2>/dev/null || pip3 install -q --user cryptography 2>/dev/null || {
            echo "⚠️  Could not install cryptography. Security features may be limited."
        }
    fi
fi

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
        # Try system-wide installation first
        if pip3 install -q -r requirements-upgrade.txt; then
            echo "✅ Python dependencies installed"
        else
            # Fallback to user installation
            echo "⚠️  System-wide install failed. Trying with --user flag..."
            if pip3 install -q --user -r requirements-upgrade.txt; then
                echo "✅ Python dependencies installed (user)"
            else
                echo "⚠️  Could not install all dependencies. Manual installation may be required."
                echo "    Run: pip3 install -r requirements-upgrade.txt"
            fi
        fi
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
if python3 .claude/system/aet.py init; then
    echo "✅ AET system initialized"
else
    echo "⚠️  Note: Full initialization will complete on first task creation"
fi

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