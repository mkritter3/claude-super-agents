#!/bin/bash
# KM Bridge Wrapper - Manages Python environment and project context
# This ensures the bridge uses the correct Python with dependencies

# Path to Python with requests installed
PYTHON_BIN="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python"

# Path to the bridge script
BRIDGE_SCRIPT="$(dirname "$0")/km_stdio_bridge.py"

# Detect project context
# Claude sets the working directory to the project path
# Use readlink -f to canonicalize the path (resolve symlinks, relative paths, etc.)
if command -v readlink >/dev/null 2>&1; then
    PROJECT_PATH=$(readlink -f "$(pwd)")
else
    # Fallback for systems without readlink -f
    PROJECT_PATH=$(cd "$(pwd)" && pwd -P)
fi
export CLAUDE_PROJECT_PATH="$PROJECT_PATH"

# Generate a unique project ID from the canonicalized path
export CLAUDE_PROJECT_ID=$(echo "$PROJECT_PATH" | md5sum | cut -c1-8 2>/dev/null || echo "$PROJECT_PATH" | md5 | cut -c1-8)

echo "KM Bridge starting for project: $PROJECT_PATH (ID: $CLAUDE_PROJECT_ID)" >&2

# Check if KM is running for this project, if not, start it
PORT_FILE="$HOME/.claude/km_ports/${CLAUDE_PROJECT_ID}.port"
if [ ! -f "$PORT_FILE" ]; then
    echo "No KM server for project $CLAUDE_PROJECT_ID, starting one..." >&2
    
    # Try to use the project manager if available
    PROJECT_MANAGER="$(dirname "$0")/km_project_manager.py"
    if [ -x "$PROJECT_MANAGER" ]; then
        "$PYTHON_BIN" "$PROJECT_MANAGER" start --project "$PROJECT_PATH" >&2
    else
        # Fallback: just ensure super-agents is running
        echo "Please start Knowledge Manager for this project:" >&2
        echo "  cd '$PROJECT_PATH'" >&2
        echo "  super-agents --wild" >&2
    fi
elif [ -f "$PORT_FILE" ]; then
    PORT=$(cat "$PORT_FILE")
    # Quick check if server is actually running
    if ! curl -s "http://localhost:$PORT/health" >/dev/null 2>&1; then
        echo "KM server for project $CLAUDE_PROJECT_ID not responding, restarting..." >&2
        PROJECT_MANAGER="$(dirname "$0")/km_project_manager.py"
        if [ -x "$PROJECT_MANAGER" ]; then
            "$PYTHON_BIN" "$PROJECT_MANAGER" start --project "$PROJECT_PATH" >&2
        fi
    fi
fi

# Run the bridge with the correct Python and project context
exec "$PYTHON_BIN" "$BRIDGE_SCRIPT" "$@"