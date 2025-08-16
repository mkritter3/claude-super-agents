# Complete MCP Setup Guide: Connecting Custom Tools to Claude Code

This is a comprehensive, step-by-step guide for setting up Model Context Protocol (MCP) integration with Claude Code. Whether you're connecting existing tools or building new ones, this guide teaches you the fundamentals.

## What is MCP?

Model Context Protocol (MCP) is an open standard that allows AI assistants like Claude to securely connect to external tools, data sources, and services. Think of it as a bridge that lets Claude access your local tools, databases, APIs, or custom services.

### Key Concepts

- **MCP Server**: Your application that provides tools/resources to Claude
- **MCP Client**: Claude Code acts as the client consuming your tools  
- **JSON-RPC Protocol**: The communication standard MCP uses
- **Tools**: Functions Claude can call (like "search_database" or "get_weather")
- **Resources**: Data Claude can read (like files or API responses)

### Architecture

```
Claude Code  ←→  MCP Server  ←→  Your Tools/Services
 (Client)        (Bridge)        (Backend)
```

## Prerequisites

- **Claude Code**: Downloaded and installed ([get it here](https://claude.ai/download))
- **Python 3.8+**: For building MCP servers
- **Basic JSON knowledge**: MCP uses JSON for configuration
- **Terminal/Command Line**: For setup and testing

## Phase 1: Understanding MCP Structure

Every MCP setup involves three components:

### 1. MCP Server (Your Code)
A program that implements the MCP protocol and provides tools to Claude. This can be:
- A Python script using the MCP SDK
- A Node.js application 
- Any program that speaks JSON-RPC over stdin/stdout

### 2. Configuration File (.mcp.json)
Tells Claude Code how to start your MCP server:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["path/to/my_server.py"]
    }
  }
}
```

### 3. MCP Protocol Implementation
Your server must handle these core messages:
- `initialize` - Capability negotiation
- `tools/list` - Return available tools
- `tools/call` - Execute a specific tool

## Phase 2: Choose Your Approach

### Option A: Quick Start with Existing Tools
If you want to connect existing tools (databases, APIs, scripts), you need a bridge server.

### Option B: Build From Scratch  
If you're creating new functionality, build a dedicated MCP server.

### Option C: Use Pre-built Solutions
Many MCP servers already exist for common needs (databases, file systems, etc.).

## Phase 3: Step-by-Step Implementation

### Step 1: Create Your MCP Server

**Minimal Python MCP Server Example:**

```python
#!/usr/bin/env python3
import sys
import json
import logging

# Setup logging to file (NEVER to stdout - it breaks MCP)
logging.basicConfig(
    filename='mcp_server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MyMCPServer:
    def handle_request(self, request):
        method = request.get("method", "")
        
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "my-custom-server",
                    "version": "1.0.0"
                }
            }
        
        elif method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "hello_world",
                        "description": "Says hello to someone",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name to greet"
                                }
                            },
                            "required": ["name"]
                        }
                    }
                ]
            }
        
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            if tool_name == "hello_world":
                name = arguments.get("name", "World")
                return {
                    "content": [{
                        "type": "text", 
                        "text": f"Hello, {name}!"
                    }]
                }
        
        return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}
    
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
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except Exception as e:
                logging.error(f"Error: {e}")

if __name__ == "__main__":
    server = MyMCPServer()
    server.run()
```

### Step 2: Create Configuration File

In your project root, create `.mcp.json`:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["/absolute/path/to/my_server.py"]
    }
  }
}
```

**Critical Notes:**
- Use **absolute paths** - relative paths often fail
- The command must be accessible from Claude Code's environment
- Multiple servers can be configured in the same file

### Step 3: Test Your Server Manually

Before connecting to Claude Code, test your server:

```bash
# Test initialization
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python my_server.py

# Test tools list  
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python my_server.py

# Test tool call
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hello_world","arguments":{"name":"Alice"}}}' | python my_server.py
```

Expected outputs:
```json
// Initialize response
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", ...}}

// Tools list response  
{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "hello_world", ...}]}}

// Tool call response
{"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "Hello, Alice!"}]}}
```

### Step 4: Connect to Claude Code

Place your `.mcp.json` file in your project directory, then start Claude Code:

```bash
# Navigate to your project directory
cd /path/to/your/project

# Start Claude Code (it will auto-detect .mcp.json)
claude
```

### Step 5: Verify Connection

In Claude Code, look for the MCP indicators:
1. **Connection Status**: Check the MCP server panel for your server status
2. **Tools Available**: You should see your tools listed in the tools panel
3. **Test Usage**: Try asking Claude to use your tool: "Can you say hello to Bob?"

## Phase 4: Common Patterns & Advanced Usage

### Pattern 1: Database Bridge Server

```python
import sqlite3

class DatabaseMCPServer:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def handle_request(self, request):
        method = request.get("method", "")
        
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "query_database",
                        "description": "Execute SQL query on database",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "SQL query to execute"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        
        elif method == "tools/call":
            params = request.get("params", {})
            if params.get("name") == "query_database":
                query = params.get("arguments", {}).get("query", "")
                
                # Execute query safely
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(query)
                    results = cursor.fetchall()
                
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Query results: {results}"
                    }]
                }
```

### Pattern 2: API Wrapper Server

```python
import requests

class APIWrapperServer:
    def __init__(self, api_key):
        self.api_key = api_key
    
    def handle_request(self, request):
        # ... handle initialize, tools/list as before ...
        
        elif method == "tools/call":
            if params.get("name") == "fetch_weather":
                city = params.get("arguments", {}).get("city", "")
                
                response = requests.get(
                    f"https://api.weather.com/v1/current?city={city}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Weather data: {response.json()}"
                    }]
                }
```

### Pattern 3: File System Tools

```python
import os
import json

def handle_file_operations(request):
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path to file"}
                        },
                        "required": ["filepath"]
                    }
                },
                {
                    "name": "list_directory",
                    "description": "List files in directory",
                    "inputSchema": {
                        "type": "object", 
                        "properties": {
                            "dirpath": {"type": "string", "description": "Directory path"}
                        },
                        "required": ["dirpath"]
                    }
                }
            ]
        }
```

## Phase 5: Debugging & Troubleshooting

### Essential Debugging Steps

#### 1. Check Your Server Logs
Always log to files, never to stdout:

```python
# Good - logs to file
logging.basicConfig(filename='my_server.log', level=logging.INFO)

# Bad - breaks MCP protocol  
print("Server started")  # NEVER do this
```

#### 2. Test Each Component Separately

```bash
# Test 1: Can you run your server?
python my_server.py

# Test 2: Does it respond to initialize?
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | python my_server.py

# Test 3: Does Claude Code find your config?
ls .mcp.json

# Test 4: Can Claude Code start your server?
# Check Claude Code MCP panel for connection status
```

### Common Issues & Solutions

#### Issue 1: "MCP Server Failed to Start"
**Symptoms:** Claude Code shows server as failed
**Solutions:**
1. **Check absolute paths** in `.mcp.json`
2. **Verify command accessibility**: Can you run the command from terminal?
3. **Check file permissions**: Is your server script executable?
4. **Look for Python environment issues**: Is Python in PATH?

#### Issue 2: "No Tools Available" 
**Symptoms:** Server connects but no tools show up
**Root Cause:** Wrong parameter format
**Solution:** Use proper JSON Schema in `inputSchema`:

```python
# Wrong - this won't work
"parameters": ["name", "type"]

# Right - proper JSON Schema
"inputSchema": {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Parameter description"}
    },
    "required": ["name"]
}
```

#### Issue 3: "JSON Parse Errors"
**Symptoms:** Server crashes on requests
**Solutions:**
1. **Validate JSON output**: Use `json.dumps()` for all responses
2. **Handle exceptions**: Wrap everything in try/catch
3. **Check stdin handling**: Make sure you're reading line by line

#### Issue 4: "Server Stops Responding"
**Symptoms:** Tools work once then fail
**Root Cause:** Server exits instead of staying alive
**Solution:** Implement proper event loop:

```python
def run(self):
    # Keep reading from stdin indefinitely
    for line in sys.stdin:
        try:
            # Process request
            request = json.loads(line.strip())
            response = self.handle_request(request)
            
            # Send response
            print(json.dumps(response))
            sys.stdout.flush()  # Important!
            
        except Exception as e:
            logging.error(f"Error: {e}")
            # Continue running despite errors
```

### Advanced Configuration

#### Multiple Servers
```json
{
  "mcpServers": {
    "database-tools": {
      "command": "python",
      "args": ["database_server.py"]
    },
    "api-tools": {
      "command": "node", 
      "args": ["api_server.js"]
    },
    "file-tools": {
      "command": "python",
      "args": ["file_server.py"]
    }
  }
}
```

#### Environment Variables
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "API_KEY": "your-api-key",
        "DATABASE_URL": "sqlite:///data.db"
      }
    }
  }
}
```

## Phase 6: Production Considerations

### Security Best Practices
1. **Input validation**: Always validate tool parameters
2. **Authentication**: Add API key validation if needed
3. **Rate limiting**: Prevent abuse of expensive operations
4. **Sandboxing**: Limit file system access appropriately

### Performance Optimization  
1. **Connection pooling**: Reuse database connections
2. **Caching**: Cache expensive API calls
3. **Async operations**: Use async/await for I/O bound operations
4. **Resource cleanup**: Properly close files and connections

### Error Handling
```python
def safe_tool_call(self, tool_name, arguments):
    try:
        # Your tool logic here
        result = self.execute_tool(tool_name, arguments)
        return {"content": [{"type": "text", "text": str(result)}]}
    
    except ValueError as e:
        return {"error": {"code": -32602, "message": f"Invalid parameters: {e}"}}
    
    except Exception as e:
        logging.error(f"Tool execution failed: {e}")
        return {"error": {"code": -32603, "message": "Internal server error"}}
```

## Complete Working Example

Here's a complete, production-ready MCP server template:

```python
#!/usr/bin/env python3
"""
Complete MCP Server Template
A fully functional example with proper error handling, logging, and structure.
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
log_file = Path(__file__).parent / "mcp_server.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ProductionMCPServer:
    def __init__(self):
        self.tools = {
            "get_time": self.get_current_time,
            "echo": self.echo_message,
            "calculate": self.calculate
        }
        logging.info("MCP Server initialized")
    
    def get_current_time(self, arguments):
        """Return current time"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Current time: {now}"
    
    def echo_message(self, arguments):
        """Echo back a message"""
        message = arguments.get("message", "")
        return f"Echo: {message}"
    
    def calculate(self, arguments):
        """Simple calculator"""
        try:
            expression = arguments.get("expression", "")
            # WARNING: In production, use a safe math evaluator
            result = eval(expression)  # UNSAFE - demo only
            return f"Result: {result}"
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")
    
    def handle_request(self, request):
        """Handle incoming MCP requests"""
        method = request.get("method", "")
        
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05", 
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "production-mcp-server",
                    "version": "1.0.0"
                }
            }
        
        elif method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "get_time",
                        "description": "Get current system time",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "echo",
                        "description": "Echo back a message",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string", "description": "Message to echo"}
                            },
                            "required": ["message"]
                        }
                    },
                    {
                        "name": "calculate", 
                        "description": "Calculate mathematical expressions",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "expression": {"type": "string", "description": "Math expression"}
                            },
                            "required": ["expression"]
                        }
                    }
                ]
            }
        
        elif method == "tools/call":
            return self.handle_tool_call(request)
        
        else:
            return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}
    
    def handle_tool_call(self, request):
        """Handle tool execution with proper error handling"""
        try:
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                return {"error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}
            
            # Execute tool
            result = self.tools[tool_name](arguments)
            
            return {
                "content": [{
                    "type": "text",
                    "text": result
                }]
            }
            
        except ValueError as e:
            return {"error": {"code": -32602, "message": str(e)}}
        except Exception as e:
            logging.error(f"Tool execution error: {e}")
            return {"error": {"code": -32603, "message": "Internal server error"}}
    
    def run(self):
        """Main server loop"""
        logging.info("Server starting...")
        
        try:
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
                    
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error: {e}")
                    error_response = {
                        "jsonrpc": "2.0", 
                        "error": {"code": -32700, "message": "Parse error"}
                    }
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                    
                except Exception as e:
                    logging.error(f"Request handling error: {e}")
                    
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
        except Exception as e:
            logging.error(f"Server error: {e}")

if __name__ == "__main__":
    server = ProductionMCPServer()
    server.run()
```

## Summary

You now have everything needed to create robust MCP integrations:

1. **Understanding**: MCP protocol, JSON-RPC, and architecture
2. **Implementation**: Complete server templates and patterns
3. **Integration**: Proper Claude Code configuration  
4. **Debugging**: Systematic troubleshooting approach
5. **Production**: Security, performance, and error handling

The key to success with MCP is methodical testing at each step. Start simple, test thoroughly, then add complexity.

---

**Last Updated:** August 16, 2025  
**Status:** Complete Universal Guide