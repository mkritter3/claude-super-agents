#!/usr/bin/env python3
"""
MCP Bridge for Knowledge Manager
Provides MCP interface to the Knowledge Manager HTTP server
"""

import json
import sys
import requests
from typing import Dict, Any, List

class KnowledgeManagerMCP:
    def __init__(self, km_port: int = 5001):
        self.km_url = f"http://localhost:{km_port}"
        self.tools = [
            {
                "name": "km_search",
                "description": "Search the Knowledge Manager for information about the codebase",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "km_get_dependencies",
                "description": "Get dependencies for a file or function",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path or function name"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "km_is_valid_path",
                "description": "Check if a file path is valid and safe",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to validate"}
                    },
                    "required": ["path"]
                }
            }
        ]
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol requests"""
        method = request.get("method")
        
        if method == "initialize":
            return {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": True
                }
            }
        
        elif method == "tools/list":
            return {"tools": self.tools}
        
        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            arguments = request.get("params", {}).get("arguments", {})
            
            try:
                if tool_name == "km_search":
                    response = requests.post(
                        f"{self.km_url}/search",
                        json={"query": arguments.get("query")},
                        timeout=10
                    )
                    return {"content": [{"type": "text", "text": json.dumps(response.json())}]}
                
                elif tool_name == "km_get_dependencies":
                    response = requests.post(
                        f"{self.km_url}/dependencies",
                        json={"path": arguments.get("path")},
                        timeout=10
                    )
                    return {"content": [{"type": "text", "text": json.dumps(response.json())}]}
                
                elif tool_name == "km_is_valid_path":
                    response = requests.post(
                        f"{self.km_url}/validate_path",
                        json={"path": arguments.get("path")},
                        timeout=10
                    )
                    return {"content": [{"type": "text", "text": json.dumps(response.json())}]}
                
                else:
                    return {"error": f"Unknown tool: {tool_name}"}
                    
            except requests.exceptions.RequestException as e:
                return {"error": f"Knowledge Manager error: {str(e)}"}
        
        else:
            return {"error": f"Unknown method: {method}"}
    
    def run(self):
        """Run the MCP server, reading from stdin and writing to stdout"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line)
                response = self.handle_request(request)
                
                # MCP protocol expects JSON-RPC format
                output = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": response
                }
                
                sys.stdout.write(json.dumps(output) + "\n")
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                error = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"}
                }
                sys.stdout.write(json.dumps(error) + "\n")
                sys.stdout.flush()
            except Exception as e:
                error = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)}
                }
                sys.stdout.write(json.dumps(error) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    # Get port from environment or command line
    import os
    port = int(os.environ.get("KM_PORT", sys.argv[1] if len(sys.argv) > 1 else 5001))
    
    mcp = KnowledgeManagerMCP(port)
    mcp.run()