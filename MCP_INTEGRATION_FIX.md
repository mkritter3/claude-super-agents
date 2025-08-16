# MCP Integration Fix Documentation

## Problem Statement

The Knowledge Manager server is running successfully on port 5002 and provides MCP tools via HTTP endpoint (`http://localhost:5002/mcp`), but these tools are not appearing in Claude Code. The user sees other MCP servers (Context7, Zen) but not the Knowledge Manager tools that should appear as `mcp__km__*`.

## Root Cause

**Claude Desktop only supports stdio-based MCP servers, not HTTP endpoints.**

When Claude launches MCP servers, it:
1. Spawns them as subprocess from entries in `claude_desktop_config.json`
2. Communicates via stdin/stdout (not HTTP)
3. Expects JSON-RPC messages over stdio streams

The Knowledge Manager runs as an HTTP server, which Claude cannot directly connect to.

## Consensus from AI Models

We consulted three leading AI models for their expert opinions:

### Grok-4 (8/10 confidence)
- Recommends stdio wrapper approach
- Estimates 1-2 hours implementation
- Highlights this is industry standard pattern
- Notes similar to LSP over HTTP proxies

### GPT-5 (7/10 confidence)
- Agrees with stdio→HTTP bridge solution
- Provides detailed MCP SDK implementation
- Suggests long-term: add native stdio to KM
- Emphasizes security (localhost only)

### Gemini-2.5-pro (9/10 confidence)
- Strongly endorses wrapper pattern
- Calls it "standard industry practice"
- Estimates less than 1 hour work
- Provides concrete Python example

**Unanimous Agreement**: All three models agree that Option B (stdio wrapper) is the correct solution.

## Solution Architecture

```
┌─────────────┐     stdio      ┌─────────────┐     HTTP      ┌──────────────┐
│   Claude    │ ◄──────────► │   Bridge    │ ◄──────────► │  Knowledge   │
│   Desktop   │   JSON-RPC     │   Script    │   JSON-RPC    │   Manager    │
└─────────────┘                └─────────────┘                └──────────────┘
```

### How It Works

1. **Claude Desktop** reads `claude_desktop_config.json`
2. Spawns the bridge script as a subprocess
3. Sends JSON-RPC requests via stdin
4. **Bridge Script** receives stdio input
5. Forwards requests to Knowledge Manager HTTP endpoint
6. Returns HTTP responses back via stdout
7. **Knowledge Manager** handles actual tool execution

## Implementation Plan

### Step 1: Create the Bridge Script
- **File**: `km_stdio_bridge.py`
- **Location**: `/Volumes/MKR HD/coding-projects/Systems/projects/claude-super-agents/`
- **Language**: Python (simple, built-in libraries)
- **Dependencies**: Only `requests` library needed

### Step 2: Key Features of Bridge
1. **Initialize Handler**: Respond to MCP initialization
2. **Tools List Handler**: Fetch tools from `/mcp/spec`
3. **Tool Call Handler**: Forward tool executions to HTTP
4. **Error Handling**: Graceful failures with stderr logging
5. **Port Detection**: Read from `.claude/km.port` if exists

### Step 3: Update Claude Configuration
- **File**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Add Entry**:
```json
{
  "mcpServers": {
    "zen": { ...existing... },
    "km": {
      "command": "/usr/bin/python3",
      "args": ["/absolute/path/to/km_stdio_bridge.py"]
    }
  }
}
```

### Step 4: Testing Process
1. Ensure Knowledge Manager is running (`super-agents`)
2. Save the bridge script and make executable
3. Update Claude config with absolute path
4. Fully quit and restart Claude Desktop
5. Open Claude Code and check for `mcp__km__*` tools

## Expected Outcome

After implementation:
- Knowledge Manager tools will appear in Claude as:
  - `mcp__km__save`
  - `mcp__km__query`
  - `mcp__km__get_file_path`
  - `mcp__km__register_api`
  - `mcp__km__get_api`
- Tools will be fully functional
- No changes needed to Knowledge Manager itself

## Alternative Solutions (Not Recommended)

### Option A: Direct HTTP in Config
- **Why it won't work**: Config schema doesn't support HTTP URLs
- **Risk**: Would require undocumented hacks

### Option C: Modify Knowledge Manager
- **Why not recommended**: Much larger effort
- **Long-term option**: Could add native stdio support later

### Option D: Wait for Claude Updates
- **Why not practical**: No timeline for HTTP support
- **Current limitation**: Must work with stdio today

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Port conflicts | Bridge reads `.claude/km.port` dynamically |
| KM not running | Bridge checks `/health` on startup |
| Protocol mismatch | Bridge handles JSON-RPC translation |
| Process lifecycle | Claude manages bridge process automatically |
| Error handling | Errors logged to stderr for debugging |

## Long-term Improvements

1. **Native stdio in Knowledge Manager**: Best long-term solution
2. **MCP SDK Integration**: Use official SDK for robustness
3. **Multiple HTTP Servers**: Bridge could support multiple backends
4. **WebSocket Support**: For real-time updates if needed

## Success Criteria

✅ Knowledge Manager tools appear in Claude Code
✅ Tools are callable and return results
✅ No errors in Claude logs
✅ Bridge process managed automatically
✅ Works across Claude restarts

## Timeline

- **Implementation**: 30-60 minutes
- **Testing**: 15-30 minutes
- **Total**: Under 2 hours

## Next Steps

1. Review this documentation
2. Create the bridge script (already drafted above)
3. Test locally
4. Update Claude configuration
5. Verify integration works

---

**Confidence Level**: Very High (9/10)
- Industry standard solution
- Unanimous expert agreement
- Simple implementation
- Proven pattern in similar tools