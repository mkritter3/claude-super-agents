#!/bin/bash

# Install super-agents command globally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the actual source directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/super-agents"
INSTALL_PATH="/usr/local/bin/super-agents"
CONFIG_FILE="$HOME/.super-agents-config"

echo "Installing super-agents command globally..."

# Verify required files exist
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}✗${NC} Error: super-agents script not found at $SCRIPT_PATH"
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/.claude" ]; then
    echo -e "${RED}✗${NC} Error: .claude directory not found at $SCRIPT_DIR/.claude"
    echo "Make sure you're running this from the claude-super-agents directory"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/CLAUDE.md" ]; then
    echo -e "${RED}✗${NC} Error: CLAUDE.md not found at $SCRIPT_DIR/CLAUDE.md"
    echo "Make sure you're running this from the claude-super-agents directory"
    exit 1
fi

# Store the source directory in config file
echo "Storing source directory in $CONFIG_FILE..."
echo "$SCRIPT_DIR" > "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"
echo -e "${GREEN}✓${NC} Source directory stored: $SCRIPT_DIR"

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

echo -e "${GREEN}✓${NC} super-agents command installed successfully!"
echo ""
echo "Configuration:"
echo "  • Source directory: $SCRIPT_DIR"
echo "  • Config file: $CONFIG_FILE"
echo "  • Global command: $INSTALL_PATH"
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
echo ""
echo "To uninstall:"
echo "  sudo rm $INSTALL_PATH"
echo "  rm $CONFIG_FILE"