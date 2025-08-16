#!/usr/bin/env python3
"""
Knowledge Manager Project Manager
Manages separate KM instances for different projects to prevent conflicts
"""

import os
import sys
import json
import hashlib
import subprocess
import time
import signal
import fcntl
import errno
from pathlib import Path
from typing import Optional, Dict, List

class KMProjectManager:
    def __init__(self):
        self.base_dir = Path.home() / ".claude" / "km_projects"
        self.port_dir = Path.home() / ".claude" / "km_ports"
        self.lock_dir = Path.home() / ".claude" / "km_locks"
        
        # Create directories with restrictive permissions
        for dir_path in [self.base_dir, self.port_dir, self.lock_dir]:
            dir_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        
    def get_project_id(self, project_path: str) -> str:
        """Generate unique project ID from canonicalized path"""
        canonical_path = os.path.realpath(project_path)
        return hashlib.md5(canonical_path.encode()).hexdigest()[:8]
    
    def acquire_lock(self, project_id: str, timeout: int = 5) -> Optional:
        """Acquire a lock for the project to prevent race conditions"""
        lock_file = self.lock_dir / f"{project_id}.lock"
        lock_fd = None
        
        try:
            lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY, 0o600)
            
            # Try to acquire lock with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return lock_fd  # Lock acquired
                except IOError as e:
                    if e.errno != errno.EAGAIN:
                        raise
                    time.sleep(0.1)  # Wait and retry
            
            # Timeout reached
            os.close(lock_fd)
            return None
            
        except Exception as e:
            if lock_fd is not None:
                os.close(lock_fd)
            raise
    
    def release_lock(self, lock_fd):
        """Release a project lock"""
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except:
                pass
    
    def get_project_info(self, project_path: str) -> Dict:
        """Get info about a project's KM instance"""
        project_id = self.get_project_id(project_path)
        info_file = self.base_dir / f"{project_id}.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_project_info(self, project_path: str, info: Dict):
        """Save project KM instance info"""
        project_id = self.get_project_id(project_path)
        info_file = self.base_dir / f"{project_id}.json"
        
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
    
    def find_free_port(self, start=5002) -> int:
        """Find a free port starting from given port"""
        import socket
        port = start
        while port < 10000:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except:
                port += 1
        raise RuntimeError("No free ports available")
    
    def start_km_for_project(self, project_path: str) -> Dict:
        """Start a KM instance for specific project with proper locking"""
        canonical_path = os.path.realpath(project_path)
        project_id = self.get_project_id(canonical_path)
        
        # Acquire lock to prevent race conditions
        lock_fd = self.acquire_lock(project_id)
        if lock_fd is None:
            print(f"⚠️  Could not acquire lock for project {project_id}. Another process may be starting.")
            return {}
        
        try:
            info = self.get_project_info(canonical_path)
            
            # Check if already running
            if info.get("pid"):
                try:
                    os.kill(info["pid"], 0)  # Check if process exists
                    print(f"✅ KM already running for project {project_id} on port {info['port']}")
                    return info
                except OSError:
                    pass  # Process doesn't exist
        
        # Find a free port
        port = self.find_free_port()
        
        # Start KM with specific port
        env = os.environ.copy()
        env["KM_PORT"] = str(port)
        
        # Start super-agents in background
        proc = subprocess.Popen(
            ["super-agents", "--wild"],
            cwd=project_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        # Wait for it to start
        time.sleep(3)
        
            # Save project info
            info = {
                "project_path": canonical_path,
                "project_id": project_id,
                "port": port,
                "pid": proc.pid,
                "started_at": time.time()
            }
            self.save_project_info(canonical_path, info)
            
            # Save port file for bridge with restrictive permissions
            port_file = self.port_dir / f"{project_id}.port"
            port_file.write_text(str(port))
            port_file.chmod(0o600)
            
            print(f"✅ Started KM for project {project_id} on port {port}")
            return info
            
        finally:
            # Always release the lock
            self.release_lock(lock_fd)
    
    def stop_km_for_project(self, project_path: str):
        """Stop KM instance for specific project"""
        project_id = self.get_project_id(project_path)
        info = self.get_project_info(project_path)
        
        if info.get("pid"):
            try:
                os.kill(info["pid"], signal.SIGTERM)
                print(f"✅ Stopped KM for project {project_id}")
            except OSError:
                print(f"⚠️  KM process {info['pid']} not found")
        
        # Clean up files
        info_file = self.base_dir / f"{project_id}.json"
        port_file = Path.home() / ".claude" / "km_ports" / f"{project_id}.port"
        
        info_file.unlink(missing_ok=True)
        port_file.unlink(missing_ok=True)
    
    def list_projects(self):
        """List all projects with KM instances"""
        projects = []
        for info_file in self.base_dir.glob("*.json"):
            with open(info_file, 'r') as f:
                info = json.load(f)
                # Check if still running
                try:
                    os.kill(info["pid"], 0)
                    status = "running"
                except OSError:
                    status = "stopped"
                
                projects.append({
                    **info,
                    "status": status
                })
        
        return projects

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage KM instances per project")
    parser.add_argument("command", choices=["start", "stop", "status", "list"])
    parser.add_argument("--project", default=os.getcwd(), help="Project path")
    
    args = parser.parse_args()
    manager = KMProjectManager()
    
    if args.command == "start":
        info = manager.start_km_for_project(args.project)
        print(f"Project: {info['project_path']}")
        print(f"Port: {info['port']}")
        print(f"PID: {info['pid']}")
        
    elif args.command == "stop":
        manager.stop_km_for_project(args.project)
        
    elif args.command == "status":
        info = manager.get_project_info(args.project)
        if info:
            print(f"Project: {info['project_path']}")
            print(f"Port: {info['port']}")
            print(f"PID: {info['pid']}")
            try:
                os.kill(info["pid"], 0)
                print("Status: ✅ Running")
            except OSError:
                print("Status: ❌ Stopped")
        else:
            print("No KM instance for this project")
            
    elif args.command == "list":
        projects = manager.list_projects()
        if projects:
            print("Active KM instances:")
            for p in projects:
                print(f"  • {p['project_id']}: {p['project_path']}")
                print(f"    Port: {p['port']}, PID: {p['pid']}, Status: {p['status']}")
        else:
            print("No active KM instances")

if __name__ == "__main__":
    main()