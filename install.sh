#!/bin/bash

# Super-Agents Installation Script
# This script installs the super-agents command globally using pip

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Super-Agents Global Installation"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION is too old"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} pip3 is not installed"
    echo "Installing pip..."
    python3 -m ensurepip --default-pip || {
        echo -e "${RED}✗${NC} Failed to install pip"
        echo "Please install pip manually"
        exit 1
    }
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/super_agents" ]; then
    echo -e "${RED}✗${NC} This script must be run from the super-agents project directory"
    echo "Please cd to the super-agents directory and run ./install.sh"
    exit 1
fi

# Offer installation options
echo ""
echo "Installation Options:"
echo "  1. Install globally (recommended)"
echo "  2. Install in user space (no sudo required)"
echo "  3. Install in development mode (for contributors)"
echo ""
read -p "Choose an option [1/2/3]: " INSTALL_OPTION

case $INSTALL_OPTION in
    1)
        echo ""
        echo -e "${CYAN}Installing super-agents globally...${NC}"
        echo "This may require sudo password"
        echo ""
        
        # Install globally
        sudo pip3 install . || {
            echo -e "${RED}✗${NC} Installation failed"
            echo "Try option 2 (user installation) instead"
            exit 1
        }
        
        INSTALL_TYPE="global"
        LOCATION=$(which super-agents)
        ;;
        
    2)
        echo ""
        echo -e "${CYAN}Installing super-agents in user space...${NC}"
        echo ""
        
        # Install for user
        pip3 install --user . || {
            echo -e "${RED}✗${NC} Installation failed"
            exit 1
        }
        
        INSTALL_TYPE="user"
        
        # Check if user's pip bin directory is in PATH
        USER_BIN="$HOME/.local/bin"
        if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
            echo ""
            echo -e "${YELLOW}⚠${NC} Warning: $USER_BIN is not in your PATH"
            echo ""
            echo "Add this line to your ~/.bashrc or ~/.zshrc:"
            echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
            echo ""
            echo "Then reload your shell or run:"
            echo "  source ~/.bashrc  # or ~/.zshrc"
        fi
        
        LOCATION="$USER_BIN/super-agents"
        ;;
        
    3)
        echo ""
        echo -e "${CYAN}Installing super-agents in development mode...${NC}"
        echo "Changes to the source code will be immediately reflected"
        echo ""
        
        # Install in editable/development mode
        pip3 install -e . || {
            echo -e "${RED}✗${NC} Installation failed"
            exit 1
        }
        
        INSTALL_TYPE="development"
        LOCATION=$(which super-agents)
        ;;
        
    *)
        echo -e "${RED}✗${NC} Invalid option"
        exit 1
        ;;
esac

# Verify installation
echo ""
echo "Verifying installation..."

if command -v super-agents &> /dev/null; then
    VERSION=$(super-agents --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ Installation Successful!${NC}"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Installation type: $INSTALL_TYPE"
    echo "Version: $VERSION"
    echo "Location: $LOCATION"
    echo ""
    echo "You can now use 'super-agents' from any directory!"
    echo ""
    echo "Quick Start:"
    echo "  1. Navigate to any project: cd ~/my-project"
    echo "  2. Initialize AET system: super-agents init"
    echo "  3. Launch with agents: super-agents"
    echo ""
    echo "Commands:"
    echo "  super-agents           - Auto-setup and launch"
    echo "  super-agents init      - Initialize project"
    echo "  super-agents upgrade   - Upgrade existing project"
    echo "  super-agents --wild    - Launch with --dangerously-skip-permissions"
    echo "  super-agents --help    - Show all commands"
    echo ""
else
    echo -e "${RED}✗${NC} Installation verification failed"
    echo "The super-agents command is not available"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if the installation directory is in your PATH"
    echo "  2. Try reopening your terminal"
    echo "  3. Run: pip3 show super-agents"
    exit 1
fi

# Offer to uninstall old version if it exists
if [ -f "/usr/local/bin/super-agents" ] && [ "$INSTALL_TYPE" != "global" ]; then
    echo -e "${YELLOW}⚠${NC} Old global installation detected at /usr/local/bin/super-agents"
    read -p "Remove old installation? (y/N): " REMOVE_OLD
    if [[ $REMOVE_OLD =~ ^[Yy]$ ]]; then
        sudo rm /usr/local/bin/super-agents
        echo -e "${GREEN}✓${NC} Old installation removed"
    fi
fi

echo "════════════════════════════════════════════════════════════"
echo "