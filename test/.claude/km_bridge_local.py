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
                
                # Test connection before declaring success
                try:
                    response = self.session.get(f"{self.base_url}/health", timeout=5)
                    if response.status_code == 200:
                        logging.info(f"Successfully connected to local KM on port {port}")
                        self.connection_status = "ready"
                    else:
                        logging.error(f"KM health check failed with status {response.status_code}")
                        self.connection_status = "failed"
                        self.base_url = None
                        self.session = None
                except Exception as e:
                    logging.error(f"Failed to connect to KM on port {port}: {e}")
                    self.connection_status = "failed"
                    self.base_url = None
                    self.session = None
        else:
            logging.error("Config file NOT found. This is likely the cause of the failure.")
            self.connection_status = "no_config"
            self.base_url = None
            self.session = None
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not self.base_url:
            return {"error": {"code": -32000, "message": "No local KM server"}}
        
        try:
            method = request.get("method", "")
            
            if method == "initialize":
                # Report connection status in server info
                status_info = f"KM Bridge ({self.connection_status})"
                if self.connection_status == "ready":
                    status_info += f" - Connected to {self.base_url}"
                
                return {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True} if self.base_url else {}
                    },
                    "serverInfo": {
                        "name": "knowledge-manager-local",
                        "version": "1.0.0",
                        "status": status_info
                    }
                }
            
            elif method == "tools/list":
                response = self.session.get(f"{self.base_url}/mcp/spec")
                response.raise_for_status()
                spec = response.json()
                
                tools = []
                for tool in spec.get("tools", []):
                    # Convert array-based parameters to JSON Schema format
                    parameters_array = tool.get("parameters", [])
                    properties = {}
                    required = []
                    
                    for param in parameters_array:
                        param_name = param.get("name")
                        param_type = param.get("type", "string")
                        param_desc = param.get("description", "")
                        is_optional = param.get("optional", False)
                        
                        if param_name:
                            properties[param_name] = {
                                "type": param_type,
                                "description": param_desc
                            }
                            if not is_optional:
                                required.append(param_name)
                    
                    input_schema = {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                    
                    tools.append({
                        "name": f"km__{tool.get('tool_name', tool.get('name'))}",
                        "description": tool.get("description", ""),
                        "inputSchema": input_schema
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
