#!/usr/bin/env python3
"""
Knowledge Manager stdio→HTTP Bridge for Claude Desktop
Proxies stdio communication from Claude to HTTP Knowledge Manager
"""

import sys
import json
import requests
import socket
from typing import Dict, Any, Optional, List

class KMBridge:
    def __init__(self, port: Optional[int] = None):
        if port is None:
            port = self.find_km_server()
        self.base_url = f"http://localhost:{port}"
        self.session = requests.Session()
    
    def find_km_server(self) -> int:
        """Find an available Knowledge Manager server by checking ports in priority order"""
        import hashlib
        
        # Try to determine project context
        project_id = os.environ.get("CLAUDE_PROJECT_ID", "")
        project_path = os.environ.get("CLAUDE_PROJECT_PATH", os.getcwd())
        
        # Canonicalize the project path
        if project_path:
            project_path = os.path.realpath(project_path)
        
        if not project_id and project_path:
            # Generate a project ID from the canonicalized path
            project_id = hashlib.md5(project_path.encode()).hexdigest()[:8]
            sys.stderr.write(f"Project context: {project_path} (ID: {project_id})\n")
            sys.stderr.flush()
        
        # If we have a project context, ONLY connect to that project's server
        if project_id:
            port_file = os.path.expanduser(f"~/.claude/km_ports/{project_id}.port")
            if os.path.exists(port_file):
                try:
                    with open(port_file, 'r') as f:
                        port = int(f.read().strip())
                        if self.check_km_server(port):
                            sys.stderr.write(f"✓ Connected to project-specific KM on port {port} (project: {project_id})\n")
                            sys.stderr.flush()
                            return port
                        else:
                            sys.stderr.write(f"✗ KM server for project {project_id} is not running on port {port}\n")
                            sys.stderr.flush()
                except (ValueError, IOError) as e:
                    sys.stderr.write(f"✗ Error reading port file for project {project_id}: {e}\n")
                    sys.stderr.flush()
            
            # FAIL-FAST: Don't fall back to other servers when project context is set
            sys.stderr.write(f"✗ ERROR: Could not connect to KM server for project {project_id}\n")
            sys.stderr.write(f"Please start the project's KM instance:\n")
            sys.stderr.write(f"  cd {project_path}\n")
            sys.stderr.write(f"  super-agents --wild\n")
            sys.stderr.flush()
            return 0  # Signal failure
        
        # Priority order: less common ports first, then common ones
        priority_ports = [
            # Less common ports (preferred)
            5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009,
            8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009,
            9002, 9003, 9004, 9005, 9006, 9007, 9008, 9009,
            # More common ports (fallback)
            5000, 5001, 8000, 8001, 9000, 9001,
            3000, 3001, 3002, 3003,
            4000, 4001, 4002, 4003,
            # Extended range if needed
            *range(5010, 5100),
            *range(8010, 8100),
        ]
        
        # No project context should never happen in Claude Desktop
        # But if it does, fail safely rather than risk data contamination
        sys.stderr.write("✗ ERROR: No project context detected\n")
        sys.stderr.write("This should not happen when running from Claude Desktop.\n")
        sys.stderr.write("Please ensure you're running Claude from a project directory.\n")
        sys.stderr.flush()
        return 0  # Signal failure - don't risk connecting to wrong server
    
    def check_km_server(self, port: int) -> bool:
        """Check if a Knowledge Manager server is running on the given port"""
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=0.5)
            if response.status_code == 200:
                data = response.json()
                # Verify it's actually a Knowledge Manager server
                if data.get("service") == "knowledge-manager":
                    return True
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            pass
        return False
        
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON-RPC request and return response"""
        try:
            # Forward to appropriate endpoint based on method
            method = request.get("method", "")
            
            if method == "initialize":
                # Initialize connection
                return {
                    "protocolVersion": "1.0.0",
                    "serverName": "knowledge-manager",
                    "capabilities": {
                        "tools": True
                    }
                }
            
            elif method == "tools/list":
                # Get tools from /mcp/spec
                response = self.session.get(f"{self.base_url}/mcp/spec")
                response.raise_for_status()
                spec = response.json()
                
                # Convert spec format to MCP tools format
                tools = []
                for tool in spec.get("tools", []):
                    tools.append({
                        "name": f"km__{tool.get('tool_name', tool.get('name'))}",
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", [])
                    })
                
                return {"tools": tools}
            
            elif method == "tools/call":
                # Execute tool call
                params = request.get("params", {})
                tool_name = params.get("name", "").replace("km__", "")
                arguments = params.get("arguments", {})
                
                # Post to MCP endpoint
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
                # Unknown method
                return {
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "error": {
                    "code": -32000,
                    "message": f"HTTP error: {str(e)}"
                }
            }
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def run(self):
        """Main loop: read stdin, process, write stdout"""
        sys.stderr.write("KM Bridge started\n")
        sys.stderr.flush()
        
        # Test connection (already validated in __init__ if auto-detected)
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            sys.stderr.write(f"✓ Connected to Knowledge Manager v{data.get('version', 'unknown')} at {self.base_url}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"✗ Failed to connect to Knowledge Manager at {self.base_url}: {e}\n")
            sys.stderr.write("Attempting to find Knowledge Manager on other ports...\n")
            sys.stderr.flush()
            # Try to find it again
            port = self.find_km_server()
            if port:
                self.base_url = f"http://localhost:{port}"
                sys.stderr.write(f"✓ Found Knowledge Manager at {self.base_url}\n")
                sys.stderr.flush()
            else:
                sys.stderr.write("Make sure Knowledge Manager is running (super-agents)\n")
                sys.stderr.flush()
        
        # Process requests
        for line in sys.stdin:
            try:
                # Parse JSON-RPC request
                request = json.loads(line.strip())
                
                # Handle request
                result = self.handle_request(request)
                
                # Build JSON-RPC response
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id")
                }
                
                if "error" in result:
                    response["error"] = result["error"]
                else:
                    response["result"] = result
                
                # Write response
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                # Invalid JSON
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                # Unexpected error
                sys.stderr.write(f"Bridge error: {str(e)}\n")
                sys.stderr.flush()

if __name__ == "__main__":
    import os
    
    # Check if user specified a port via environment
    port = None
    if "KM_PORT" in os.environ:
        try:
            port = int(os.environ.get("KM_PORT"))
            sys.stderr.write(f"Using port {port} from KM_PORT environment variable\n")
            sys.stderr.flush()
        except (TypeError, ValueError):
            sys.stderr.write("Invalid KM_PORT value, will auto-detect\n")
            sys.stderr.flush()
    
    # Run bridge with dynamic port discovery
    bridge = KMBridge(port)
    bridge.run()