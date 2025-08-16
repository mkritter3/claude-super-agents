# Knowledge Manager MCP Bridge - Project Isolation by Default

## Overview
Each Claude Desktop instance automatically gets its own isolated Knowledge Manager (KM) server based on the project directory. This prevents knowledge contamination between projects and ensures data isolation.

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

1. **Automatic Project Isolation** (Default)
   - Each project directory gets its own KM instance
   - Bridge detects working directory as project context
   - Automatically starts project-specific KM if not running
   - No shared instances - complete isolation

2. **Multiple Claude Instances**: Full Isolation
   - Each Claude instance in different directory = different KM server
   - No knowledge mixing between projects
   - Automatic server management per project

## Usage

### Automatic Mode (Default)
```bash
# Just open Claude in your project directory
# KM server starts automatically for that project
# Each project gets its own isolated instance
```

### Manual Management (Optional)
```bash
# Check status of all projects
./check_km_status.py

# Manually start/stop specific projects
./km_project_manager.py start --project /path/to/project-a
./km_project_manager.py stop --project /path/to/project-a
./km_project_manager.py list  # See all running instances

# View project status
./km_project_manager.py status --project /path/to/project
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
- **Zero configuration** - Everything is automatic
- **Complete project isolation** - No knowledge contamination
- **Auto-start on demand** - KM servers start when needed
- **Self-healing** - Automatically restarts failed servers
- **Security by default** - Restrictive permissions, file locking
- **No manual port management** - Automatic port allocation