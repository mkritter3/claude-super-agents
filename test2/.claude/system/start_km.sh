#!/bin/bash
set -euo pipefail

# Start Knowledge Manager Server

echo "Starting Knowledge Manager server..."

# Check if already running
if [ -f .claude/km.pid ]; then
    PID=$(cat .claude/km.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Knowledge Manager already running with PID: $PID"
        exit 0
    else
        echo "Stale PID file found, removing..."
        rm .claude/km.pid
    fi
fi

# Install dependencies if needed
echo "Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    pip install flask
fi

# Optional: Install sentence-transformers for semantic search
if ! python3 -c "import sentence_transformers" 2>/dev/null; then
    echo "Warning: sentence-transformers not installed"
    echo "Semantic search will use keyword matching fallback"
    echo "To install: pip install sentence-transformers"
fi

# Start KM server in background
echo "Starting server on port 5001..."
cd "$(dirname "$0")/../.."
python3 .claude/system/km_server.py &
KM_PID=$!

echo "Knowledge Manager started with PID: $KM_PID"
echo $KM_PID > .claude/km.pid

# Wait a moment for server to start
sleep 2

# Check if server is responding
if curl -s http://127.0.0.1:5001/mcp/spec > /dev/null; then
    echo "✓ Knowledge Manager server is responding"
    
    # Register with Claude Code if available
    if command -v claude &> /dev/null; then
        echo "Registering with Claude Code..."
        claude mcp add km --transport http --scope project http://127.0.0.1:5001/mcp || true
        echo "✓ MCP server registered"
    else
        echo "Note: Claude Code CLI not found, manual MCP registration required"
    fi
else
    echo "✗ Server not responding, check logs"
    exit 1
fi

echo "Knowledge Manager setup complete!"
echo "Server URL: http://127.0.0.1:5001"
echo "MCP Endpoint: http://127.0.0.1:5001/mcp"