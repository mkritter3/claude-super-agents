#!/usr/bin/env python3
import sys, json, os, requests
from typing import Dict, Any

class LocalKMBridge:
    def __init__(self):
        port_file = os.path.join(os.path.dirname(__file__), "km_server/port")
        if os.path.exists(port_file):
            with open(port_file) as f:
                self.port = int(f.read().strip())
                self.base_url = f"http://localhost:{self.port}"
                self.session = requests.Session()
        else:
            self.base_url = None
            self.session = None
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not self.base_url:
            return {"error": {"code": -32000, "message": "No local KM server"}}
        
        method = request.get("method", "")
        
        if method == "initialize":
            return {"protocolVersion": "1.0.0", "serverName": "km-local", "capabilities": {"tools": True}}
        elif method == "tools/list":
            response = self.session.get(f"{self.base_url}/mcp/spec")
            spec = response.json()
            tools = [{"name": f"km__{t.get('tool_name', t.get('name'))}", 
                     "description": t.get("description", ""),
                     "parameters": t.get("parameters", [])} for t in spec.get("tools", [])]
            return {"tools": tools}
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "").replace("km__", "")
            response = self.session.post(f"{self.base_url}/mcp",
                json={"jsonrpc": "2.0", "method": tool_name, 
                      "params": params.get("arguments", {}), "id": request.get("id")})
            result = response.json()
            return {"content": [{"type": "text", "text": json.dumps(result.get("result", result))}]}
        else:
            return {"error": {"code": -32601, "message": f"Method not found: {method}"}}
    
    def run(self):
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                result = self.handle_request(request)
                response = {"jsonrpc": "2.0", "id": request.get("id")}
                if "error" in result:
                    response["error"] = result["error"]
                else:
                    response["result"] = result
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()

if __name__ == "__main__":
    LocalKMBridge().run()
