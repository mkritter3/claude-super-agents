#!/usr/bin/env python3
import sys
import os

# Add the port as an environment variable
os.environ['KM_PORT'] = '5001'

# Import and run the original server
sys.path.insert(0, '.claude/system')
from km_server import app

if __name__ == '__main__':
    app.run(port=5001, debug=False, host='127.0.0.1')
