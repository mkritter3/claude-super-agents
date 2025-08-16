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

# Run the bridge with the correct Python and project context
exec "$PYTHON_BIN" "$BRIDGE_SCRIPT" "$@"