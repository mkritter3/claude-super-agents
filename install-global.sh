#!/bin/bash

# Install super-agents command globally

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/super-agents"
INSTALL_PATH="/usr/local/bin/super-agents"

echo "Installing super-agents command globally..."

# Make the script executable
chmod +x "$SCRIPT_PATH"

# Check if /usr/local/bin exists
if [ ! -d "/usr/local/bin" ]; then
    echo "Creating /usr/local/bin directory..."
    sudo mkdir -p /usr/local/bin
fi

# Create or update the symlink
if [ -L "$INSTALL_PATH" ]; then
    echo "Updating existing installation..."
    sudo rm "$INSTALL_PATH"
elif [ -f "$INSTALL_PATH" ]; then
    echo "Backing up existing file..."
    sudo mv "$INSTALL_PATH" "$INSTALL_PATH.backup"
fi

sudo ln -s "$SCRIPT_PATH" "$INSTALL_PATH"

echo "✓ super-agents command installed successfully!"
echo ""
echo "You can now use 'super-agents' from any directory to:"
echo "  • Set up AET agents in a project"
echo "  • Start the Knowledge Manager"
echo "  • Launch Claude with your agents"
echo ""
echo "Usage:"
echo "  super-agents           - Setup and launch"
echo "  super-agents --upgrade - Upgrade existing agents"
echo "  super-agents --stop    - Stop Knowledge Manager"
echo "  super-agents --help    - Show help"