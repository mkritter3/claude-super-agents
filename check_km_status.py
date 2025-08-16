#!/usr/bin/env python3
"""Check status of all running Knowledge Manager instances"""

import requests
import json
import sys

def check_km_servers():
    """Find all running KM servers"""
    ports_to_check = list(range(5000, 5020)) + list(range(8000, 8010))
    running_servers = []
    
    for port in ports_to_check:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=0.2)
            if response.status_code == 200:
                data = response.json()
                if data.get("service") == "knowledge-manager":
                    running_servers.append({
                        "port": port,
                        "version": data.get("version", "unknown"),
                        "status": data.get("status", "unknown")
                    })
        except:
            pass
    
    return running_servers

if __name__ == "__main__":
    servers = check_km_servers()
    
    if not servers:
        print("❌ No Knowledge Manager servers found")
        print("\nTo start one: super-agents --wild")
        sys.exit(1)
    
    print(f"✅ Found {len(servers)} Knowledge Manager server(s):\n")
    for server in servers:
        print(f"  • Port {server['port']}: v{server['version']} ({server['status']})")
    
    if len(servers) > 1:
        print("\n⚠️  Multiple servers detected. The MCP bridge will connect to the first available.")
        print("Consider stopping extra instances with: super-agents --stop")