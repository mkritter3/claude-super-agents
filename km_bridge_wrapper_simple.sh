#!/bin/bash
# Simple KM Bridge Wrapper - Just runs the bridge with correct Python

# Path to Python with requests installed
PYTHON_BIN="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python"

# Path to the simple bridge script  
BRIDGE_SCRIPT="$(dirname "$0")/km_stdio_bridge_simple.py"

# Check if local server exists, give helpful message if not
if [ ! -f "./.claude/km_server/port" ]; then
    echo "ℹ️  No local KM server in this directory" >&2
    echo "Run 'super-agents --wild' to start one" >&2
fi

# Run the bridge
exec "$PYTHON_BIN" "$BRIDGE_SCRIPT" "$@"