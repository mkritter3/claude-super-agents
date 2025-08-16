# Knowledge Manager MCP Bridge - Multi-Instance Setup

## Overview
This setup allows multiple Claude Desktop instances to run simultaneously, each connecting to their own Knowledge Manager (KM) server without conflicts.

## Key Components

### 1. `km_stdio_bridge.py`
- Dynamic port discovery - automatically finds available KM servers
- Project-aware - uses project path to identify which KM instance to connect to
- Fallback mechanism - connects to first available if project-specific not found

### 2. `km_bridge_wrapper.sh`
- Ensures correct Python environment (with requests module)
- Detects and passes project context to the bridge
- Generates unique project ID from working directory

### 3. `km_project_manager.py` (Optional)
- Manages separate KM instances per project
- Prevents port conflicts
- Tracks which KM instance belongs to which project

## How It Works

1. **Single Claude Instance**: Works automatically
   - Bridge finds first available KM server
   - No configuration needed

2. **Multiple Claude Instances**: Project isolation
   - Each Claude instance runs in different directory
   - Bridge detects working directory as project context
   - Attempts to connect to project-specific KM instance
   - Falls back to shared instance if needed

## Usage

### Basic (Single Instance)
```bash
# Start KM normally
super-agents --wild

# Claude will automatically connect via MCP bridge
```

### Advanced (Multiple Projects)
```bash
# Option 1: Manual management
# Terminal 1 - Project A
cd /path/to/project-a
KM_PORT=5002 super-agents --wild

# Terminal 2 - Project B  
cd /path/to/project-b
KM_PORT=5003 super-agents --wild

# Option 2: Using project manager
./km_project_manager.py start --project /path/to/project-a
./km_project_manager.py start --project /path/to/project-b
./km_project_manager.py list  # See all running instances
```

## Configuration

### Claude Desktop Config
The MCP server should be configured to use the wrapper:
```json
{
  "km": {
    "command": "/path/to/km_bridge_wrapper.sh",
    "args": []
  }
}
```

### Environment Variables
- `KM_PORT`: Force connection to specific port
- `CLAUDE_PROJECT_PATH`: Override project detection
- `CLAUDE_PROJECT_ID`: Manually set project identifier

## Troubleshooting

### Check KM Status
```bash
# See all running KM servers
./check_km_status.py

# Check specific project
./km_project_manager.py status --project /path/to/project
```

### Multiple Servers Detected
If you see warnings about multiple servers:
1. Stop unnecessary instances: `super-agents --stop`
2. Or use project manager for isolation
3. Bridge will use first available (usually port 5002)

### Connection Failed
1. Ensure KM is running: `super-agents --wild`
2. Check Python has requests: `pip install requests`
3. Verify port isn't blocked by firewall

## Benefits
- **No manual port configuration** - Everything is automatic
- **Project isolation** - Each project can have its own KM instance
- **Backwards compatible** - Works with existing single-instance setups
- **Self-healing** - Automatically finds available servers
- **Multi-instance safe** - Prevents knowledge mixing between projects