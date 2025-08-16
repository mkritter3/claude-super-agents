#!/bin/bash

################################################################################
# Super-Agents Installation Script
# 
# Purpose: Install the super-agents command globally or locally on any system
# 
# This script performs the following operations:
# 1. Validates system requirements (Python 3.8+, pip)
# 2. Offers three installation modes:
#    - Global: System-wide installation (requires sudo)
#    - User: Local installation in ~/.local/bin (no sudo)
#    - Development: Editable install for contributors
# 3. Handles PATH configuration for user installations
# 4. Verifies successful installation
# 5. Provides troubleshooting guidance
#
# Usage:
#   ./install.sh              # Interactive installation
#   
# Requirements:
#   - Python 3.8 or higher
#   - pip package manager
#   - Git (for development mode)
#
# Installation creates:
#   - super-agents command (globally accessible)
#   - Python package in site-packages
#   - Entry point in appropriate bin directory
#
# Exit codes:
#   0 - Success
#   1 - Requirements not met or installation failed
################################################################################

set -e  # Exit on error

# Terminal color codes for enhanced readability
RED='\033[0;31m'      # Error messages
GREEN='\033[0;32m'    # Success messages
YELLOW='\033[1;33m'   # Warnings
CYAN='\033[0;36m'     # Information
NC='\033[0m'          # Reset color

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Super-Agents Global Installation"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 1: Validate Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Step 2: Validate Python version meets minimum requirement (3.8)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION is too old"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"

# Step 3: Validate pip package manager availability
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} pip3 is not installed"
    echo "Installing pip..."
    python3 -m ensurepip --default-pip || {
        echo -e "${RED}✗${NC} Failed to install pip"
        echo "Please install pip manually"
        exit 1
    }
fi

# Step 4: Validate script is run from project root directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/super_agents" ]; then
    echo -e "${RED}✗${NC} This script must be run from the super-agents project directory"
    echo "Please cd to the super-agents directory and run ./install.sh"
    exit 1
fi

# Step 5: Present installation options to user
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
        
        # Option 1: Global installation with sudo
        # Installs to system Python site-packages
        # Creates command in /usr/local/bin or similar
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
        
        # Option 2: User-local installation without sudo
        # Installs to ~/.local/lib/python*/site-packages
        # Creates command in ~/.local/bin
        pip3 install --user . || {
            echo -e "${RED}✗${NC} Installation failed"
            exit 1
        }
        
        INSTALL_TYPE="user"
        
        # Important: Check if user's pip bin directory is in PATH
        # Without this, the command won't be accessible
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
        
        # Option 3: Development mode (editable install)
        # Links to source directory instead of copying
        # Changes to source code are immediately reflected
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

# Step 6: Verify installation succeeded and command is accessible
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

# Step 7: Clean up old installations if present
# This prevents conflicts between different installation methods
if [ -f "/usr/local/bin/super-agents" ] && [ "$INSTALL_TYPE" != "global" ]; then
    echo -e "${YELLOW}⚠${NC} Old global installation detected at /usr/local/bin/super-agents"
    read -p "Remove old installation? (y/N): " REMOVE_OLD
    if [[ $REMOVE_OLD =~ ^[Yy]$ ]]; then
        sudo rm /usr/local/bin/super-agents
        echo -e "${GREEN}✓${NC} Old installation removed"
    fi
fi

echo "════════════════════════════════════════════════════════════"