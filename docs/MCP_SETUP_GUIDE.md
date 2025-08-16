# MCP Configuration Guide for Super Agents Knowledge Manager

This document provides step-by-step instructions for setting up the Model Context Protocol (MCP) integration between Claude Code and the Super Agents Knowledge Manager system.

## Current Status: 🟡 Partially Working

✅ **Working Components:**
- Knowledge Manager server starts correctly (port 5001)
- MCP bridge script connects to KM when run manually
- Project-scoped MCP configuration files are properly generated
- All dependencies are installed correctly

🔄 **Known Issues:**
- Claude Code MCP server shows "Status: ✘ failed" despite successful manual testing
- Need to investigate why Claude Code can't start the MCP bridge (debugging logs added)

## Overview

The Super Agents system includes a Knowledge Manager (KM) that provides semantic search, file path resolution, and API registration capabilities through MCP. This allows Claude Code to access project-specific knowledge and utilities.

### Architecture

```
Claude Code  →  MCP Bridge  →  Knowledge Manager Server
              (.mcp.json)      (localhost:5001)
```

## Prerequisites

- Python 3.8+ with pipx installed
- Claude Code installed and accessible via `claude` command
- Super Agents installed via pipx (`pipx install -e .`)

## Step 1: Install Super Agents

```bash
# Clone the repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Install with pipx (includes all dependencies)
pipx install -e .

# Verify installation
super-agents --help
```

## Step 2: Initialize Project

```bash
# Navigate to your project directory
cd /path/to/your/project

# Initialize the AET system (creates all necessary files)
super-agents init

# Verify initialization
super-agents status
```

This creates the complete directory structure including:
- `.claude/` - AET system files and MCP bridge
- `.mcp.json` - Claude Code MCP configuration
- `CLAUDE.md` - Orchestration instructions

## Step 3: Verify Knowledge Manager

```bash
# Start the system
super-agents

# Check status in another terminal
super-agents status
```

You should see:
```
Component: Km - Healthy (port 5001)
Running on port 5001 (PID: xxxxx)
Status: Responding
URL: http://localhost:5001/health
```

## Step 4: MCP Configuration Files

The initialization creates two key MCP files:

### `.mcp.json` (Project Root)
```json
{
  "mcpServers": {
    "km": {
      "command": "/Users/[username]/.local/pipx/venvs/super-agents/bin/python",
      "args": [".claude/km_bridge_local.py"]
    }
  }
}
```

### `.claude/mcp_config.json` (Bridge Configuration)
```json
{
  "local_km_port": 5001,
  "project_dir": "/absolute/path/to/your/project"
}
```

## Step 5: Test MCP Bridge Manually

```bash
# Test the bridge script directly
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | \
  /Users/[username]/.local/pipx/venvs/super-agents/bin/python .claude/km_bridge_local.py
```

Expected output:
```json
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "1.0.0", "serverName": "knowledge-manager-local", "capabilities": {"tools": true}}}
```

## Step 6: Configure Claude Code

### Option A: Let Claude Code Auto-Discover

Claude Code should automatically detect the `.mcp.json` file in your project root. Check via:

```bash
claude mcp list
```

### Option B: Manual Configuration (if needed)

```bash
# Remove any old configurations
claude mcp remove km

# The .mcp.json file should be automatically discovered
# If not, you can manually add:
claude mcp add km --scope project \
  -- /Users/[username]/.local/pipx/venvs/super-agents/bin/python .claude/km_bridge_local.py
```

## Debugging

### Check MCP Bridge Logs

The bridge creates detailed logs at `.claude/km_bridge_local.log`:

```bash
cat .claude/km_bridge_local.log
```

Successful log should show:
```
INFO - Bridge script started.
INFO - CWD: /path/to/your/project
INFO - Config file found.
INFO - Successfully connected to local KM on port 5001
```

### Common Issues and Solutions

#### 1. "No local KM config found"
**Symptom:** Bridge can't find `mcp_config.json`
**Solution:** 
- Verify `.claude/mcp_config.json` exists
- Check file permissions
- Ensure absolute paths in config

#### 2. "Connection refused" on port 5001
**Symptom:** Can't connect to Knowledge Manager
**Solution:**
```bash
# Check if KM is running
super-agents status

# Restart if needed
super-agents --stop && super-agents
```

#### 3. "ModuleNotFoundError: No module named 'requests'"
**Symptom:** Missing dependencies
**Solution:**
```bash
# Reinstall with dependencies
pipx install -e . --force
```

#### 4. Claude Code shows "MCP Server failed"
**Symptom:** MCP server status shows failed in Claude Code
**Current Status:** Under investigation
**Debug Steps:**
1. Check `.claude/km_bridge_local.log` for errors
2. Verify manual bridge test works
3. Check Claude Code MCP configuration with `claude mcp list`

### Available MCP Tools

Once connected, Claude Code has access to these Knowledge Manager tools:

- `km__save` - Save knowledge with semantic embeddings
- `km__query` - Semantic search for relevant information
- `km__get_file_path` - Get canonical file paths for components
- `km__register_api` - Register component API definitions
- `km__get_api` - Retrieve component API information

## Files Created During Setup

```
your-project/
├── .mcp.json                          # Claude Code MCP config
├── CLAUDE.md                          # AET instructions
└── .claude/
    ├── mcp_config.json               # Bridge configuration
    ├── km_bridge_local.py            # MCP bridge script
    ├── km_bridge_local.log           # Debug logs
    ├── agents/                       # 23 AI agents
    ├── system/                       # Core AET system
    └── ...                          # Other AET files
```

## Environment Variables

The system uses these environment variables:

- `CLAUDE_PROJECT_DIR` - Set automatically by hooks
- `MCP_TIMEOUT` - MCP server startup timeout (default: 2 minutes)

## Next Steps (Planned)

1. **Resolve Claude Code Integration** - Debug why MCP server fails in Claude Code despite manual success
2. **Enhanced Error Handling** - Improve error messages and recovery
3. **Configuration Validation** - Add setup verification commands
4. **Multi-Project Support** - Handle multiple Knowledge Manager instances

## Getting Help

If you encounter issues:

1. Check `.claude/km_bridge_local.log` for detailed error information
2. Verify Knowledge Manager is running with `super-agents status`
3. Test manual MCP bridge connection
4. Review this guide for common solutions

## Contributing

This configuration is actively being refined. Current challenges and solutions are documented here as they're discovered and resolved.

---

**Last Updated:** August 16, 2025  
**Status:** Development - MCP bridge functional, Claude Code integration troubleshooting in progress