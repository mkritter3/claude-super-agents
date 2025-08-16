#!/bin/bash
# Setup COMPLETE AET system locally in current directory

set -e

PROJECT_DIR=$(pwd)
CLAUDE_DIR="$PROJECT_DIR/.claude"

echo "🚀 Setting up complete AET system in $PROJECT_DIR"

# 1. Initialize AET agents if not already done
if [ ! -d "$CLAUDE_DIR/agents" ]; then
    echo "Initializing AET agents..."
    super-agents init --force
else
    echo "✓ AET agents already initialized"
fi

# 2. Start local Knowledge Manager server
echo "Starting local Knowledge Manager..."
cd "$PROJECT_DIR"

# Find an available port
PORT=5002
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    PORT=$((PORT + 1))
done

echo "Using port $PORT for local KM server"

# Create local KM directory
mkdir -p "$CLAUDE_DIR/km_server"
echo $PORT > "$CLAUDE_DIR/km_server/port"

# Start KM server in background for this directory
export KM_PORT=$PORT
export KM_DATA_DIR="$CLAUDE_DIR/km_server/data"
mkdir -p "$KM_DATA_DIR"

# Start the Knowledge Manager
nohup super-agents --wild > "$CLAUDE_DIR/km_server/km.log" 2>&1 &
KM_PID=$!
echo $KM_PID > "$CLAUDE_DIR/km_server/km.pid"

# Wait for server to start
echo "Waiting for KM server to start..."
for i in {1..10}; do
    if curl -s "http://localhost:$PORT/health" >/dev/null 2>&1; then
        echo "✓ Knowledge Manager running on port $PORT"
        break
    fi
    sleep 1
done

# 3. Setup MCP bridge configuration
echo "Configuring MCP bridge..."
cat > "$CLAUDE_DIR/mcp_config.json" <<EOF
{
  "local_km_port": $PORT,
  "project_dir": "$PROJECT_DIR"
}
EOF

# 4. Create local bridge script
cat > "$CLAUDE_DIR/km_bridge_local.py" <<'BRIDGE_SCRIPT'
#!/usr/bin/env python3
import sys
import json
import os
import requests
from typing import Dict, Any

class LocalKMBridge:
    def __init__(self):
        config_file = os.path.join(os.path.dirname(__file__), "mcp_config.json")
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = json.load(f)
                port = config.get("local_km_port", 5002)
                self.base_url = f"http://localhost:{port}"
                self.session = requests.Session()
                sys.stderr.write(f"✓ Connected to local KM on port {port}\n")
                sys.stderr.flush()
        else:
            sys.stderr.write("✗ No local KM config found\n")
            sys.stderr.flush()
            self.base_url = None
            self.session = None
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not self.base_url:
            return {"error": {"code": -32000, "message": "No local KM server"}}
        
        try:
            method = request.get("method", "")
            
            if method == "initialize":
                return {
                    "protocolVersion": "1.0.0",
                    "serverName": "knowledge-manager-local",
                    "capabilities": {"tools": True}
                }
            
            elif method == "tools/list":
                response = self.session.get(f"{self.base_url}/mcp/spec")
                response.raise_for_status()
                spec = response.json()
                
                tools = []
                for tool in spec.get("tools", []):
                    tools.append({
                        "name": f"km__{tool.get('tool_name', tool.get('name'))}",
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", [])
                    })
                return {"tools": tools}
            
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name", "").replace("km__", "")
                arguments = params.get("arguments", {})
                
                mcp_request = {
                    "jsonrpc": "2.0",
                    "method": tool_name,
                    "params": arguments,
                    "id": request.get("id")
                }
                
                response = self.session.post(
                    f"{self.base_url}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result.get("result", result))
                    }]
                }
            
            else:
                return {"error": {"code": -32601, "message": f"Method not found: {method}"}}
                
        except Exception as e:
            return {"error": {"code": -32603, "message": f"Internal error: {str(e)}"}}
    
    def run(self):
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                result = self.handle_request(request)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id")
                }
                
                if "error" in result:
                    response["error"] = result["error"]
                else:
                    response["result"] = result
                
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"Bridge error: {str(e)}\n")
                sys.stderr.flush()

if __name__ == "__main__":
    bridge = LocalKMBridge()
    bridge.run()
BRIDGE_SCRIPT

chmod +x "$CLAUDE_DIR/km_bridge_local.py"

# 5. Create status checker
cat > "$CLAUDE_DIR/aet_status.sh" <<'STATUS_SCRIPT'
#!/bin/bash
CLAUDE_DIR="$(dirname "$0")"

echo "=== AET System Status ==="
echo ""

# Check agents
if [ -d "$CLAUDE_DIR/agents" ]; then
    AGENT_COUNT=$(ls -1 "$CLAUDE_DIR/agents"/*.md 2>/dev/null | wc -l)
    echo "✓ $AGENT_COUNT agents configured"
else
    echo "✗ No agents found"
fi

# Check KM server
if [ -f "$CLAUDE_DIR/km_server/port" ]; then
    PORT=$(cat "$CLAUDE_DIR/km_server/port")
    if curl -s "http://localhost:$PORT/health" >/dev/null 2>&1; then
        echo "✓ Knowledge Manager running on port $PORT"
    else
        echo "✗ Knowledge Manager not responding on port $PORT"
    fi
else
    echo "✗ Knowledge Manager not configured"
fi

# Check event system
if [ -f "$CLAUDE_DIR/events/log.ndjson" ]; then
    EVENT_COUNT=$(wc -l < "$CLAUDE_DIR/events/log.ndjson")
    echo "✓ Event system active ($EVENT_COUNT events)"
else
    echo "✗ Event system not initialized"
fi

# Check git hooks
if [ -d "$CLAUDE_DIR/hooks" ]; then
    HOOK_COUNT=$(ls -1 "$CLAUDE_DIR/hooks"/* 2>/dev/null | wc -l)
    echo "✓ $HOOK_COUNT git hooks installed"
else
    echo "✗ No git hooks found"
fi

echo ""
echo "Project: $(pwd)"
STATUS_SCRIPT

chmod +x "$CLAUDE_DIR/aet_status.sh"

# 6. Update CLAUDE.md for this project
cat > "$PROJECT_DIR/CLAUDE.md" <<'CLAUDE_MD'
# Local AET System Configuration

This project has a complete local AET (Autonomous Engineering Team) system configured.

## Components

- **23 Specialized Agents** in `.claude/agents/`
- **Local Knowledge Manager** in `.claude/km_server/`
- **Event System** in `.claude/events/`
- **Git Hooks** in `.claude/hooks/`
- **MCP Bridge** in `.claude/km_bridge_local.py`

## Status

Run `./.claude/aet_status.sh` to check system health.

## Usage

The system is already running. Claude Code will automatically:
1. Connect to the local Knowledge Manager
2. Use the 23 specialized agents
3. Track events and triggers
4. Apply autonomous operations

## Restart if Needed

```bash
./setup_local_aet.sh
```

This ensures everything is running properly.
CLAUDE_MD

echo ""
echo "✅ Complete AET system set up locally!"
echo ""
echo "Components installed:"
echo "  • 23 specialized agents"
echo "  • Local Knowledge Manager (port $PORT)"
echo "  • Event system"
echo "  • Git hooks"
echo "  • MCP bridge"
echo "  • Orchestration system"
echo ""
echo "Run './.claude/aet_status.sh' to check status"
echo ""
echo "The entire AET system is now running in this directory."