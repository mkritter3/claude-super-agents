#!/usr/bin/env python3
"""
AET Process Management System
Implements graceful shutdown, zombie cleanup, and process monitoring
Part of Phase 1.4: Process Management
"""

import os
import sys
import signal
import psutil
import json
import time
import atexit
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

class ProcessManager:
    """Manages AET system processes with graceful shutdown and cleanup"""
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.state_dir = self.claude_dir / "state"
        self.logs_dir = self.claude_dir / "logs"
        
        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Process registry
        self.process_registry_file = self.state_dir / "process_registry.json"
        self.processes = self._load_registry()
        
        # Setup logging
        self.logger = self._setup_logger()
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup process manager logger"""
        logger = logging.getLogger("AET_ProcessManager")
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.logs_dir / "process_manager.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.graceful_shutdown()
        sys.exit(0)
        
    def _load_registry(self) -> Dict[str, Dict]:
        """Load process registry from file"""
        if self.process_registry_file.exists():
            try:
                with open(self.process_registry_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                self.logger.warning("Failed to load process registry, starting fresh")
        return {}
        
    def _save_registry(self):
        """Save process registry to file atomically"""
        temp_file = self.process_registry_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(self.processes, f, indent=2)
            temp_file.replace(self.process_registry_file)
        except Exception as e:
            self.logger.error(f"Failed to save process registry: {e}")
            temp_file.unlink(missing_ok=True)
            
    def register_process(self, name: str, pid: int, metadata: Dict = None) -> bool:
        """Register a new managed process"""
        try:
            # Verify process exists
            process = psutil.Process(pid)
            
            self.processes[name] = {
                "pid": pid,
                "started_at": datetime.now().isoformat(),
                "command": ' '.join(process.cmdline()),
                "metadata": metadata or {}
            }
            
            self._save_registry()
            self.logger.info(f"Registered process {name} (PID: {pid})")
            return True
            
        except psutil.NoSuchProcess:
            self.logger.error(f"Failed to register {name}: process {pid} not found")
            return False
            
    def unregister_process(self, name: str):
        """Unregister a process"""
        if name in self.processes:
            del self.processes[name]
            self._save_registry()
            self.logger.info(f"Unregistered process {name}")
            
    def is_process_running(self, name: str) -> bool:
        """Check if a registered process is running"""
        if name not in self.processes:
            return False
            
        try:
            pid = self.processes[name]["pid"]
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, KeyError):
            return False
            
    def graceful_shutdown(self, timeout: int = 30):
        """Gracefully shutdown all managed processes"""
        self.logger.info("Starting graceful shutdown of all processes...")
        
        # Send SIGTERM to all processes
        for name, info in self.processes.items():
            try:
                pid = info["pid"]
                process = psutil.Process(pid)
                
                self.logger.info(f"Sending SIGTERM to {name} (PID: {pid})")
                process.terminate()
                
            except psutil.NoSuchProcess:
                self.logger.warning(f"Process {name} (PID: {pid}) already terminated")
                
        # Wait for processes to terminate
        start_time = time.time()
        while time.time() - start_time < timeout:
            all_terminated = True
            
            for name in list(self.processes.keys()):
                if self.is_process_running(name):
                    all_terminated = False
                else:
                    self.unregister_process(name)
                    
            if all_terminated:
                self.logger.info("All processes terminated gracefully")
                return
                
            time.sleep(0.5)
            
        # Force kill remaining processes
        for name, info in list(self.processes.items()):
            try:
                pid = info["pid"]
                process = psutil.Process(pid)
                
                self.logger.warning(f"Force killing {name} (PID: {pid})")
                process.kill()
                self.unregister_process(name)
                
            except psutil.NoSuchProcess:
                self.unregister_process(name)
                
    def cleanup_zombies(self) -> int:
        """Clean up zombie processes"""
        self.logger.info("Scanning for zombie processes...")
        
        zombies_cleaned = 0
        
        # Find all zombie processes
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    # Try to reap the zombie
                    try:
                        os.waitpid(proc.info['pid'], os.WNOHANG)
                        zombies_cleaned += 1
                        self.logger.info(f"Reaped zombie process {proc.info['pid']}")
                    except:
                        # If we can't reap it, try to kill its parent
                        try:
                            parent = psutil.Process(proc.info['ppid'])
                            if parent.name() in ['km_server.py', 'aet.py']:
                                parent.terminate()
                                self.logger.warning(f"Terminated parent {parent.pid} of zombie {proc.info['pid']}")
                                zombies_cleaned += 1
                        except:
                            pass
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # Clean up our own zombie children
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                zombies_cleaned += 1
                self.logger.info(f"Reaped zombie child {pid}")
            except ChildProcessError:
                break
                
        if zombies_cleaned > 0:
            self.logger.info(f"Cleaned up {zombies_cleaned} zombie processes")
        
        return zombies_cleaned
        
    def cleanup_stale_processes(self) -> int:
        """Clean up stale process entries"""
        cleaned = 0
        
        for name in list(self.processes.keys()):
            if not self.is_process_running(name):
                self.unregister_process(name)
                cleaned += 1
                
                # Also clean up PID files
                pid_file = self.state_dir / f"{name}.pid"
                if pid_file.exists():
                    pid_file.unlink()
                    
        if cleaned > 0:
            self.logger.info(f"Cleaned up {cleaned} stale process entries")
            
        return cleaned
        
    def cleanup_all(self):
        """Comprehensive cleanup of all process-related issues"""
        self.logger.info("Running comprehensive process cleanup...")
        
        # Clean up zombies
        self.cleanup_zombies()
        
        # Clean up stale processes
        self.cleanup_stale_processes()
        
        # Clean up orphaned PID files
        for pid_file in self.state_dir.glob("*.pid"):
            try:
                pid = int(pid_file.read_text().strip())
                # Check if process exists
                os.kill(pid, 0)
            except (OSError, ValueError):
                # Process doesn't exist, clean up
                pid_file.unlink()
                self.logger.info(f"Removed orphaned PID file: {pid_file.name}")
                
    def monitor_processes(self) -> Dict[str, Dict]:
        """Monitor health of all registered processes"""
        status = {}
        
        for name, info in self.processes.items():
            try:
                pid = info["pid"]
                process = psutil.Process(pid)
                
                status[name] = {
                    "running": process.is_running(),
                    "status": process.status(),
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "num_threads": process.num_threads(),
                    "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
                }
                
            except psutil.NoSuchProcess:
                status[name] = {"running": False, "status": "terminated"}
                
        return status
        
    def restart_process(self, name: str) -> bool:
        """Restart a managed process"""
        if name not in self.processes:
            self.logger.error(f"Process {name} not registered")
            return False
            
        info = self.processes[name]
        
        # Stop if running
        if self.is_process_running(name):
            try:
                process = psutil.Process(info["pid"])
                process.terminate()
                process.wait(timeout=10)
            except:
                pass
                
        # Extract command from metadata or use default
        if name == "km_server":
            return self._start_km_server()
        else:
            self.logger.error(f"Don't know how to restart {name}")
            return False
            
    def _start_km_server(self) -> bool:
        """Start the Knowledge Manager server"""
        try:
            # Get port from state
            port_file = self.state_dir / "km.port"
            if port_file.exists():
                port = port_file.read_text().strip()
            else:
                port = "5001"
                
            # Prepare environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.claude_dir / "system")
            env['KM_PORT'] = port
            
            # Start process
            process = subprocess.Popen(
                [sys.executable, str(self.claude_dir / "system" / "km_server.py")],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Register the process
            self.register_process("km_server", process.pid, {"port": port})
            
            # Save PID file
            pid_file = self.state_dir / "km.pid"
            pid_file.write_text(str(process.pid))
            
            self.logger.info(f"Started KM server on port {port} (PID: {process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start KM server: {e}")
            return False


def main():
    """CLI interface for process management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AET Process Manager")
    parser.add_argument('--cleanup', action='store_true', help='Clean up zombies and stale processes')
    parser.add_argument('--monitor', action='store_true', help='Monitor all processes')
    parser.add_argument('--shutdown', action='store_true', help='Gracefully shutdown all processes')
    parser.add_argument('--restart', metavar='NAME', help='Restart a specific process')
    
    args = parser.parse_args()
    
    manager = ProcessManager()
    
    if args.cleanup:
        manager.cleanup_all()
        print("Process cleanup complete")
        
    elif args.monitor:
        status = manager.monitor_processes()
        for name, info in status.items():
            running = "✓" if info.get("running") else "✗"
            print(f"{running} {name}: {info}")
            
    elif args.shutdown:
        manager.graceful_shutdown()
        print("Graceful shutdown complete")
        
    elif args.restart:
        success = manager.restart_process(args.restart)
        print(f"Restart {'succeeded' if success else 'failed'}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()