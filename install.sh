#!/bin/bash
# Install super-agents command

echo "Installing super-agents..."

# Check if user has permission to /usr/local/bin
if [ -w "/usr/local/bin" ]; then
    cp super-agents /usr/local/bin/super-agents
    chmod +x /usr/local/bin/super-agents
    echo "✓ Installed to /usr/local/bin/super-agents"
else
    # Try with sudo
    echo "Need sudo permission to install to /usr/local/bin"
    sudo cp super-agents /usr/local/bin/super-agents
    sudo chmod +x /usr/local/bin/super-agents
    echo "✓ Installed to /usr/local/bin/super-agents"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  super-agents        - Setup AET in current directory"
echo "  super-agents status - Check AET status"
echo "  super-agents clean  - Remove AET from current directory"
echo ""
echo "Each directory gets its own isolated AET system."