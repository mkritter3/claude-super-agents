#!/bin/bash

# Super-Agents Uninstall Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Super-Agents Uninstaller"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if super-agents is installed via pip
if pip3 show super-agents &> /dev/null; then
    echo -e "${GREEN}✓${NC} Found pip installation of super-agents"
    
    # Get installation details
    INSTALL_LOCATION=$(pip3 show super-agents | grep Location | cut -d' ' -f2)
    VERSION=$(pip3 show super-agents | grep Version | cut -d' ' -f2)
    
    echo "  Version: $VERSION"
    echo "  Location: $INSTALL_LOCATION"
    echo ""
    
    read -p "Uninstall super-agents? (y/N): " CONFIRM
    if [[ $CONFIRM =~ ^[Yy]$ ]]; then
        echo "Uninstalling..."
        pip3 uninstall -y super-agents
        echo -e "${GREEN}✓${NC} Package uninstalled"
    else
        echo "Uninstall cancelled"
        exit 0
    fi
else
    echo -e "${YELLOW}⚠${NC} No pip installation found"
fi

# Check for old symlink installation
if [ -L "/usr/local/bin/super-agents" ]; then
    echo ""
    echo -e "${YELLOW}⚠${NC} Found old symlink at /usr/local/bin/super-agents"
    read -p "Remove old symlink? (y/N): " REMOVE_LINK
    if [[ $REMOVE_LINK =~ ^[Yy]$ ]]; then
        sudo rm /usr/local/bin/super-agents
        echo -e "${GREEN}✓${NC} Old symlink removed"
    fi
fi

# Check for config file
CONFIG_FILE="$HOME/.super-agents-config"
if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "Found configuration file: $CONFIG_FILE"
    read -p "Remove configuration file? (y/N): " REMOVE_CONFIG
    if [[ $REMOVE_CONFIG =~ ^[Yy]$ ]]; then
        rm "$CONFIG_FILE"
        echo -e "${GREEN}✓${NC} Configuration file removed"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ Uninstall Complete${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Note: Project files in individual directories were not removed."
echo "To clean up a project, delete its .claude directory and CLAUDE.md file."
echo ""