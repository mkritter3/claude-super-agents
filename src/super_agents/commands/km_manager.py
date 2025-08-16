"""
Knowledge Manager Controller - Manages KM instances with dynamic port allocation
"""

import os
import sys
import time
import json
import socket
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
from rich.console import Console
from rich.table import Table

console = Console()


class KnowledgeManagerController:
    """Controls Knowledge Manager lifecycle with dynamic port allocation"""
    
    BASE_PORT = 5001
    MAX_PORT = 5100
    
    def __init__(self):
        self.port_file = Path(".claude/km.port")
        self.pid_file = Path(".claude/km.pid")
        self.lock_file = Path(".claude/km.port.lock")
        self.log_file = Path(".claude/logs/km_server.log")
    
    def find_available_port(self) -> Optional[int]:
        """Find an available port in the range"""
        for port in range(self.BASE_PORT, self.MAX_PORT + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', port))
                    return port
                except OSError:
                    continue
        return None
    
    def get_project_port(self) -> int:
        """Get or assign port for current project"""
        # Create lock file if needed
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.touch()
        
        # Check if we have a saved port
        if self.port_file.exists():
            try:
                saved_port = int(self.port_file.read_text().strip())
                
                # Check if our process is still running on that port
                if self.pid_file.exists():
                    saved_pid = int(self.pid_file.read_text().strip())
                    
                    # Check if process is alive
                    try:
                        os.kill(saved_pid, 0)
                        # Process exists, use the saved port
                        return saved_port
                    except OSError:
                        # Process doesn't exist
                        pass
                
                # Check if the port is free
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(('127.0.0.1', saved_port))
                        # Port is free, we can reuse it
                        return saved_port
                    except OSError:
                        # Port is taken by someone else
                        pass
            except (ValueError, OSError):
                pass
        
        # Need to find a new port
        new_port = self.find_available_port()
        if new_port:
            self.port_file.write_text(str(new_port))
            return new_port
        
        raise RuntimeError("No available ports found (5001-5100)")
    
    def check_dependencies(self) -> bool:
        """Check if required Python packages are installed"""
        missing_deps = []
        
        required_packages = ['flask', 'numpy']
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_deps.append(package)
        
        if missing_deps:
            console.print("[red]Missing Python dependencies for Knowledge Manager:[/red]")
            for dep in missing_deps:
                console.print(f"  • {dep}")
            console.print("\n[yellow]Install with:[/yellow] pip3 install " + " ".join(missing_deps))
            return False
        
        return True
    
    def is_running(self) -> bool:
        """Check if KM is currently running"""
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                os.kill(pid, 0)
                return True
            except (ValueError, OSError):
                # Clean up stale PID file
                self.pid_file.unlink(missing_ok=True)
        return False
    
    def start(self) -> Optional[int]:
        """
        Start the Knowledge Manager
        Returns the port number on success, None on failure
        """
        # Get port for this project
        try:
            km_port = self.get_project_port()
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            return None
        
        # Check if already running
        if self.is_running():
            console.print(f"[green]✓[/green] Knowledge Manager already running on port {km_port}")
            return km_port
        
        # Check dependencies
        if not self.check_dependencies():
            console.print("[yellow]⚠[/yellow] Knowledge Manager will not start due to missing dependencies")
            return None
        
        console.print(f"[cyan]Starting Knowledge Manager on port {km_port}...[/cyan]")
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create wrapper script with dynamic port
        wrapper_path = Path(".claude/km_server_wrapper.py")
        wrapper_content = f"""#!/usr/bin/env python3
import sys
import os

# Add the port as an environment variable
os.environ['KM_PORT'] = '{km_port}'

# Import and run the original server
sys.path.insert(0, '.claude/system')
try:
    from km_server import app
    app.run(port={km_port}, debug=False, host='127.0.0.1')
except ImportError as e:
    print(f"Error: Could not import km_server: {{e}}")
    print("Make sure km_server.py exists in .claude/system/")
    sys.exit(1)
"""
        
        wrapper_path.write_text(wrapper_content)
        os.chmod(wrapper_path, 0o755)
        
        # Check if km_server.py exists
        km_server_path = Path(".claude/system/km_server.py")
        if not km_server_path.exists():
            console.print(f"[red]Knowledge Manager not found at {km_server_path}[/red]")
            console.print("[dim]Run 'super-agents init' to set up the project first[/dim]")
            return None
        
        # Start KM in background
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{os.getcwd()}/.claude/system:{env.get('PYTHONPATH', '')}"
        
        with open(self.log_file, 'w') as log:
            process = subprocess.Popen(
                [sys.executable, str(wrapper_path)],
                stdout=log,
                stderr=log,
                env=env,
                start_new_session=True
            )
        
        # Save PID
        self.pid_file.write_text(str(process.pid))
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if it started successfully
        if self.is_running():
            console.print(f"[green]✓[/green] Knowledge Manager started on port {km_port} (PID: {process.pid})")
            
            # Test if it's responding
            try:
                import urllib.request
                response = urllib.request.urlopen(f"http://localhost:{km_port}/health", timeout=2)
                if response.status == 200:
                    console.print(f"[green]✓[/green] Knowledge Manager is responding at http://localhost:{km_port}")
            except:
                console.print("[yellow]⚠[/yellow] Knowledge Manager started but not yet responding")
            
            return km_port
        else:
            console.print("[red]Failed to start Knowledge Manager[/red]")
            console.print(f"[dim]Check {self.log_file} for errors[/dim]")
            
            # Show last few lines of error log
            if self.log_file.exists():
                console.print("\n[dim]Recent error output:[/dim]")
                log_lines = self.log_file.read_text().splitlines()
                for line in log_lines[-5:]:
                    console.print(f"[dim]{line}[/dim]")
            
            return None
    
    def stop(self) -> bool:
        """
        Stop the Knowledge Manager
        Returns True on success, False on failure
        """
        stopped = False
        
        # Try using PID file first
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                os.kill(pid, 15)  # SIGTERM
                self.pid_file.unlink()
                self.port_file.unlink(missing_ok=True)
                console.print("[green]✓[/green] Knowledge Manager stopped")
                stopped = True
            except (ValueError, OSError):
                # Process doesn't exist or can't be killed
                self.pid_file.unlink(missing_ok=True)
        
        # If we have a port file but no PID, try to find process by port
        if not stopped and self.port_file.exists():
            try:
                km_port = int(self.port_file.read_text().strip())
                
                # Use lsof to find process on port (macOS/Linux)
                result = subprocess.run(
                    ['lsof', '-ti', f':{km_port}'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    pid = int(result.stdout.strip())
                    os.kill(pid, 15)
                    console.print("[green]✓[/green] Knowledge Manager stopped")
                    stopped = True
                
                self.port_file.unlink(missing_ok=True)
            except (ValueError, OSError, subprocess.SubprocessError):
                pass
        
        if not stopped:
            console.print("[yellow]⚠[/yellow] Knowledge Manager not running")
        
        return stopped
    
    def list_all_instances(self) -> List[Tuple[int, str]]:
        """
        List all projects with running KM instances
        Returns list of (port, project_path) tuples
        """
        instances = []
        
        console.print("[bold cyan]All AET Projects with Running KM Instances[/bold cyan]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Port", style="cyan")
        table.add_column("Project Directory")
        table.add_column("Status", style="green")
        
        # Check all ports in range
        for port in range(self.BASE_PORT, self.MAX_PORT + 1):
            # Check if port is in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect(('127.0.0.1', port))
                    # Port is in use, try to find project
                    
                    # Search for project directories with this port
                    # This is a simple implementation - could be improved
                    home = Path.home()
                    for port_file in home.rglob(".claude/km.port"):
                        try:
                            if int(port_file.read_text().strip()) == port:
                                project_dir = port_file.parent.parent
                                instances.append((port, str(project_dir)))
                                
                                # Test if responding
                                status = "Running"
                                try:
                                    import urllib.request
                                    response = urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1)
                                    if response.status == 200:
                                        status = "Healthy"
                                except:
                                    status = "Not Responding"
                                
                                table.add_row(str(port), str(project_dir), status)
                                break
                        except (ValueError, OSError):
                            continue
                    else:
                        # Port in use but project unknown
                        table.add_row(str(port), "[dim]Unknown project[/dim]", "Running")
                        
                except OSError:
                    # Port not in use
                    continue
        
        if table.row_count > 0:
            console.print(table)
            console.print(f"\n[dim]Found {table.row_count} running instance(s)[/dim]")
        else:
            console.print("[yellow]No running Knowledge Manager instances found[/yellow]")
        
        console.print("\n[dim]To stop a specific project's KM:[/dim]")
        console.print("[dim]  cd <project-dir> && super-agents --stop[/dim]")
        
        return instances