#!/bin/bash
#
# Install Git hooks for autonomous operations
#
# This script installs the autonomous operational hooks into the git repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing autonomous operational hooks...${NC}"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Source directory (where our hooks are)
HOOK_SOURCE_DIR=".claude/hooks"

# Target directory (git hooks directory) 
HOOK_TARGET_DIR=".git/hooks"

# Check if source hooks exist
if [ ! -d "$HOOK_SOURCE_DIR" ]; then
    echo -e "${RED}Error: Hook source directory $HOOK_SOURCE_DIR not found${NC}"
    exit 1
fi

# Function to install a hook
install_hook() {
    local hook_name=$1
    local source_file="$HOOK_SOURCE_DIR/$hook_name"
    local target_file="$HOOK_TARGET_DIR/$hook_name"
    
    if [ -f "$source_file" ]; then
        # Check if target hook already exists
        if [ -f "$target_file" ]; then
            echo -e "${YELLOW}Warning: $hook_name already exists, backing up...${NC}"
            cp "$target_file" "$target_file.backup.$(date +%s)"
        fi
        
        # Copy and make executable
        cp "$source_file" "$target_file"
        chmod +x "$target_file"
        
        echo -e "${GREEN}✓ Installed $hook_name${NC}"
    else
        echo -e "${YELLOW}- $hook_name not found, skipping${NC}"
    fi
}

# Install all hooks
echo "Installing operational hooks..."

install_hook "pre-commit"
install_hook "post-commit"
install_hook "post-merge" 
install_hook "pre-push"
install_hook "post-receive"

# Create symlinks to enable development
if [ -d "$HOOK_SOURCE_DIR" ]; then
    echo "Creating development symlinks..."
    
    # For development, we can symlink to make updates easier
    for hook_file in "$HOOK_SOURCE_DIR"/*; do
        if [ -f "$hook_file" ] && [ -x "$hook_file" ]; then
            hook_name=$(basename "$hook_file")
            
            # Skip the install script itself
            if [ "$hook_name" = "install-hooks.sh" ]; then
                continue
            fi
            
            target_file="$HOOK_TARGET_DIR/$hook_name"
            
            # If we already copied the file, replace with symlink for development
            if [ -f "$target_file" ] && [ ! -L "$target_file" ]; then
                rm "$target_file"
                ln -s "../../$HOOK_SOURCE_DIR/$hook_name" "$target_file"
                echo -e "${GREEN}✓ Created development symlink for $hook_name${NC}"
            fi
        fi
    done
fi

# Verify installation
echo
echo "Verifying hook installation..."

for hook in pre-commit post-commit post-merge pre-push post-receive; do
    target_file="$HOOK_TARGET_DIR/$hook"
    if [ -f "$target_file" ] && [ -x "$target_file" ]; then
        echo -e "${GREEN}✓ $hook installed and executable${NC}"
    else
        echo -e "${RED}✗ $hook missing or not executable${NC}"
    fi
done

echo
echo -e "${GREEN}Autonomous operational hooks installation complete!${NC}"
echo 
echo "These hooks will now automatically:"
echo "• Scan commits for secrets and credentials (pre-commit)"
echo "• Monitor code commits for operational triggers (post-commit)"
echo "• Detect schema changes and trigger migrations (post-commit)"
echo "• Set up monitoring for new deployments (post-merge)"
echo "• Update documentation when code changes (post-commit)"
echo "• Trigger performance analysis on relevant changes (post-commit)"
echo
echo "The operational agents will now work autonomously based on your git activity."
echo "Secret detection will prevent credential leaks before they enter the repository."