#!/bin/bash
# Install super-agents-local wrapper

echo "Installing super-agents-local wrapper..."

# Check if user has permission to /usr/local/bin
if [ -w "/usr/local/bin" ]; then
    cp super-agents-local /usr/local/bin/super-agents-local
    chmod +x /usr/local/bin/super-agents-local
    echo "✓ Installed to /usr/local/bin/super-agents-local"
else
    # Try with sudo
    echo "Need sudo permission to install to /usr/local/bin"
    sudo cp super-agents-local /usr/local/bin/super-agents-local
    sudo chmod +x /usr/local/bin/super-agents-local
    echo "✓ Installed to /usr/local/bin/super-agents-local"
fi

# Create alias for convenience
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias sa=" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# Super-agents local wrapper" >> "$SHELL_RC"
        echo "alias sa='super-agents-local'" >> "$SHELL_RC"
        echo "✓ Added 'sa' alias to $SHELL_RC"
        echo "  Run 'source $SHELL_RC' or restart terminal to use"
    fi
fi

echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  super-agents-local       - Setup AET in current directory"
echo "  super-agents-local status - Check AET status"
echo "  sa                       - Short alias (after restart)"
echo ""
echo "Each directory gets its own isolated AET system."