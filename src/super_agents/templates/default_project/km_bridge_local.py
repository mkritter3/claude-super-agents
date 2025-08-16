#!/usr/bin/env python3
import sys
import json
import os
import requests
import logging
from typing import Dict, Any

# Set up logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'km_bridge_local.log')
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Clear the log on each start for clean debugging
with open(log_file_path, 'w'):
    pass

logging.info("Bridge script started.")
logging.info(f"CWD: {os.getcwd()}")
logging.info(f"Absolute path of script: {os.path.abspath(__file__)}")
logging.info(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")

class LocalKMBridge:
    def __init__(self):
        config_file = os.path.join(os.path.dirname(__file__), "mcp_config.json")
        logging.info(f"Attempting to read config from: {os.path.abspath(config_file)}")
        if os.path.exists(config_file):
            logging.info("Config file found.")
            with open(config_file) as f:
                config = json.load(f)
                port = config.get("local_km_port", 5002)
                self.base_url = f"http://localhost:{port}"
                self.session = requests.Session()
                logging.info(f"Successfully connected to local KM on port {port}")
                sys.stderr.write(f"✓ Connected to local KM on port {port}\n")
                sys.stderr.flush()
        else:
            logging.error("Config file NOT found. This is likely the cause of the failure.")
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
                logging.exception(f"Unhandled exception in run loop: {e}")
                sys.stderr.write(f"Bridge error: {str(e)}\n")
                sys.stderr.flush()

if __name__ == "__main__":
    bridge = LocalKMBridge()
    bridge.run()
