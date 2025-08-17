#!/usr/bin/env python3
"""
Find the correct Python executable for MCP bridge
"""
import sys
import subprocess
import os

def find_python_with_requests():
    """Find a Python executable that has requests module"""
    candidates = [
        # Try pipx first (preferred)
        "/Users/michaelritter/.local/pipx/venvs/super-agents/bin/python",
        # System Python with --break-system-packages
        "/opt/homebrew/bin/python3",
        # Current Python
        sys.executable,
    ]
    
    for python_path in candidates:
        if os.path.exists(python_path):
            try:
                # Test if requests is available
                result = subprocess.run([
                    python_path, "-c", "import requests; print('OK')"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    print(python_path)
                    return
            except:
                continue
    
    # If no Python with requests found, use system Python with install command
    print("/opt/homebrew/bin/python3")

if __name__ == "__main__":
    find_python_with_requests()