#!/usr/bin/env python3
import sys
import os

# Add the port as an environment variable
os.environ['KM_PORT'] = '5001'

# Import and run the original server
sys.path.insert(0, '.claude/system')
try:
    from km_server import app
    app.run(port=5001, debug=False, host='127.0.0.1')
except ImportError as e:
    print(f"Error: Could not import km_server: {e}")
    print("Make sure km_server.py exists in .claude/system/")
    sys.exit(1)
