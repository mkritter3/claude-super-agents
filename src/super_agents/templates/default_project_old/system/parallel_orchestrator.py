#!/usr/bin/env python3
import json
import threading
import queue
import time
import subprocess
import shutil
import psutil
import os
import signal
from pathlib import Path
from typing import Dict, List, Set, Generator, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from orchestrator import TaskOrchestrator
from file_registry import FileRegistry
from datetime import datetime
from logger_config import get_contextual_logger

class ResourceManager:
    """
    Phase 1 Resource Manager with Enforcement
    - Actually enforces limits, not just warns
    - Implements throttling when CPU exceeds limits  
    - Queues tasks when memory exceeds limits
    - Uses psutil for monitoring
    """
    
    def __init__(self, 
                 max_cpu_percent: float = 70.0,
                 max_memory_percent: float = 80.0,
                 max_concurrent_tasks: int = 4):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_concurrent_tasks = max_concurrent_tasks
        self.current_tasks = 0
        self.task_queue = queue.Queue()
        self.lock = threading.Lock()
        self.logger = get_contextual_logger("resource_manager", component="orchestrator")
        
        # Resource monitoring state
        self._cpu_readings = []
        self._memory_readings = []
        self._monitoring = True
        
        # Start resource monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_resources(self):
        """Background thread to monitor system resources."""
        while self._monitoring:
            try:
                # Get CPU usage (averaged over short period)
                cpu_percent = psutil.cpu_percent(interval=1.0)
                memory_info = psutil.virtual_memory()
                
                # Keep rolling window of readings
                self._cpu_readings.append(cpu_percent)
                self._memory_readings.append(memory_info.percent)
                
                # Keep only last 10 readings
                if len(self._cpu_readings) > 10:
                    self._cpu_readings.pop(0)
                if len(self._memory_readings) > 10:
                    self._memory_readings.pop(0)
                    
            except Exception as e:
                self.logger.error("Resource monitoring error", extra={'error': str(e)})
                time.sleep(5)  # Wait before retrying
    
    def get_resource_status(self) -> Dict:
        """Get current resource usage status."""
        try:
            avg_cpu = sum(self._cpu_readings) / len(self._cpu_readings) if self._cpu_readings else 0
            avg_memory = sum(self._memory_readings) / len(self._memory_readings) if self._memory_readings else 0
            
            return {
                'cpu_percent': avg_cpu,
                'memory_percent': avg_memory,
                'active_tasks': self.current_tasks,
                'queued_tasks': self.task_queue.qsize(),
                'cpu_limit_exceeded': avg_cpu > self.max_cpu_percent,
                'memory_limit_exceeded': avg_memory > self.max_memory_percent,
                'task_limit_exceeded': self.current_tasks >= self.max_concurrent_tasks
            }
        except Exception as e:
            self.logger.error("Error getting resource status", extra={'error': str(e)})
            return {
                'cpu_percent': 0, 'memory_percent': 0, 'active_tasks': 0,
                'queued_tasks': 0, 'cpu_limit_exceeded': False,
                'memory_limit_exceeded': False, 'task_limit_exceeded': False
            }
    
    def acquire_resource_permit(self, ticket_id: str, timeout: int = 300) -> bool:
        """
        Acquire permission to run a task based on resource limits.
        Returns True if task can run now, False if should be queued/rejected.
        """
        with self.lock:
            status = self.get_resource_status()
            
            # Check if we can run immediately
            if (not status['cpu_limit_exceeded'] and 
                not status['memory_limit_exceeded'] and 
                not status['task_limit_exceeded']):
                
                self.current_tasks += 1
                self.logger.info("Resource permit granted", extra={
                    'ticket_id': ticket_id,
                    'cpu_percent': status['cpu_percent'],
                    'memory_percent': status['memory_percent'],
                    'active_tasks': self.current_tasks
                })
                return True
            
            # Queue the task if limits exceeded
            self.logger.warning("Resource limits exceeded, queuing task", extra={
                'ticket_id': ticket_id,
                'cpu_exceeded': status['cpu_limit_exceeded'],
                'memory_exceeded': status['memory_limit_exceeded'],
                'task_limit_exceeded': status['task_limit_exceeded'],
                'queue_size': status['queued_tasks']
            })
            
            try:
                self.task_queue.put(ticket_id, timeout=timeout)
                return False  # Task was queued, not granted
            except queue.Full:
                self.logger.error("Resource queue full, rejecting task", extra={
                    'ticket_id': ticket_id,
                    'queue_size': status['queued_tasks']
                })
                return False
    
    def release_resource_permit(self, ticket_id: str):
        """Release resource permit when task completes."""
        with self.lock:
            if self.current_tasks > 0:
                self.current_tasks -= 1
                
            self.logger.info("Resource permit released", extra={
                'ticket_id': ticket_id,
                'active_tasks': self.current_tasks
            })
            
            # Process queued tasks if resources are available
            self._process_queued_tasks()
    
    def _process_queued_tasks(self):
        """Process queued tasks if resources become available."""
        status = self.get_resource_status()
        
        while (not status['cpu_limit_exceeded'] and 
               not status['memory_limit_exceeded'] and 
               not status['task_limit_exceeded'] and
               not self.task_queue.empty()):
            
            try:
                ticket_id = self.task_queue.get_nowait()
                self.current_tasks += 1
                
                self.logger.info("Processing queued task", extra={
                    'ticket_id': ticket_id,
                    'queue_remaining': self.task_queue.qsize()
                })
                
                # Yield control back to allow task to start
                return ticket_id
                
            except queue.Empty:
                break
            
            # Refresh status for next iteration
            status = self.get_resource_status()
        
        return None
    
    def process_queued_tasks(self) -> Generator[str, None, None]:
        """Generator that yields queued tasks when resources are available."""
        while True:
            ticket_id = self._process_queued_tasks()
            if ticket_id:
                yield ticket_id
            else:
                time.sleep(1)  # Wait before checking again
                if self.task_queue.empty():
                    break
    
    def emergency_throttle(self):
        """Emergency throttling when system is overloaded."""
        try:
            # Lower process priority
            current_process = psutil.Process()
            current_process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == 'nt' else 10)
            
            # Reduce concurrent tasks
            with self.lock:
                self.max_concurrent_tasks = max(1, self.max_concurrent_tasks // 2)
                
            self.logger.warning("Emergency throttling activated", extra={
                'new_max_tasks': self.max_concurrent_tasks
            })
            
        except Exception as e:
            self.logger.error("Emergency throttling failed", extra={'error': str(e)})
    
    def shutdown(self):
        """Shutdown resource manager."""
        self._monitoring = False
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join(timeout=5)

class ParallelOrchestrator(TaskOrchestrator):
    def __init__(self, max_workers: int = 3):
        super().__init__()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tickets: Set[str] = set()
        
        # Phase 1 Enhancement: Remove in-memory file_locks, use only registry
        # self.file_locks: Dict[str, str] = {}  # REMOVED - replaced with registry-only locking
        
        self.lock = threading.Lock()
        self.logger = get_contextual_logger("parallel_orchestrator", component="orchestrator")
        
        # Phase 1 Enhancement: Add ResourceManager
        self.resource_manager = ResourceManager(
            max_cpu_percent=70.0,
            max_memory_percent=80.0, 
            max_concurrent_tasks=max_workers
        )
    
    def can_process_parallel(self, ticket1: str, ticket2: str) -> bool:
        """Check if two tickets can be processed in parallel."""
        # Get file dependencies for both tickets
        deps1 = self.get_file_dependencies(ticket1)
        deps2 = self.get_file_dependencies(ticket2)
        
        # Check for overlap
        return len(deps1.intersection(deps2)) == 0
    
    def get_file_dependencies(self, ticket_id: str) -> Set[str]:
        """Get all files a ticket might touch."""
        deps = set()
        
        # Query registry for files associated with ticket
        cursor = self.registry.conn.cursor()
        cursor.execute("""
            SELECT path FROM files WHERE ticket_id = ?
        """, (ticket_id,))
        
        for row in cursor.fetchall():
            deps.add(row['path'])
        
        # Also check workspace for uncommitted changes
        snapshot = self.load_snapshots().get(ticket_id, {})
        if 'job_id' in snapshot:
            workspace_path = Path(f".claude/workspaces/{snapshot['job_id']}/workspace")
            if workspace_path.exists():
                # Get modified files from git
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line:
                        deps.add(line)
        
        return deps
    
    def acquire_file_locks(self, ticket_id: str, files: Set[str]) -> bool:
        """
        Phase 1 Enhanced Locking: Use only registry-backed locking with cleanup.
        Try to acquire locks on all files for a ticket with proper error handling.
        """
        acquired_locks = []
        
        try:
            # Phase 1 Enhancement: Use only registry locking, no in-memory tracking
            for file_path in files:
                success = self.registry.acquire_lock(file_path, ticket_id)
                if success:
                    acquired_locks.append(file_path)
                    self.logger.debug("Lock acquired", extra={
                        'file_path': file_path,
                        'ticket_id': ticket_id
                    })
                else:
                    # Failed to acquire lock - cleanup and return False
                    self.logger.warning("Failed to acquire lock", extra={
                        'file_path': file_path,
                        'ticket_id': ticket_id,
                        'acquired_so_far': len(acquired_locks)
                    })
                    
                    # Phase 1 Enhancement: Cleanup on partial failure
                    self._cleanup_partial_locks(acquired_locks, ticket_id)
                    return False
            
            self.logger.info("All file locks acquired", extra={
                'ticket_id': ticket_id,
                'file_count': len(acquired_locks)
            })
            return True
            
        except Exception as e:
            # Phase 1 Enhancement: Robust error handling with cleanup
            self.logger.error("Exception during lock acquisition", extra={
                'ticket_id': ticket_id,
                'error': str(e),
                'acquired_so_far': len(acquired_locks)
            })
            
            # Cleanup any locks we managed to acquire
            self._cleanup_partial_locks(acquired_locks, ticket_id)
            return False
    
    def _cleanup_partial_locks(self, acquired_locks: List[str], ticket_id: str):
        """Phase 1 Enhancement: Clean up partially acquired locks."""
        for file_path in acquired_locks:
            try:
                self.registry.release_lock(file_path, ticket_id)
                self.logger.debug("Lock released during cleanup", extra={
                    'file_path': file_path,
                    'ticket_id': ticket_id
                })
            except Exception as cleanup_error:
                self.logger.error("Failed to release lock during cleanup", extra={
                    'file_path': file_path,
                    'ticket_id': ticket_id,
                    'cleanup_error': str(cleanup_error)
                })
    
    def release_file_locks(self, ticket_id: str):
        """
        Phase 1 Enhanced: Release all file locks held by a ticket using registry.
        """
        try:
            # Get all files locked by this ticket from registry
            cursor = self.registry.conn.cursor()
            cursor.execute("""
                SELECT path FROM files 
                WHERE lock_owner = ? AND lock_status = 'locked'
            """, (ticket_id,))
            
            locked_files = [row['path'] for row in cursor.fetchall()]
            
            # Release each lock through registry
            released_count = 0
            for file_path in locked_files:
                if self.registry.release_lock(file_path, ticket_id):
                    released_count += 1
                    self.logger.debug("Lock released", extra={
                        'file_path': file_path,
                        'ticket_id': ticket_id
                    })
                else:
                    self.logger.warning("Failed to release lock", extra={
                        'file_path': file_path,
                        'ticket_id': ticket_id
                    })
            
            self.logger.info("File locks released", extra={
                'ticket_id': ticket_id,
                'total_files': len(locked_files),
                'released_count': released_count
            })
            
        except Exception as e:
            self.logger.error("Error releasing file locks", extra={
                'ticket_id': ticket_id,
                'error': str(e)
            })
    
    def process_ticket_safe(self, ticket_id: str) -> bool:
        """
        Phase 1 Enhanced: Process a ticket with resource management and proper locking.
        """
        resource_permit_acquired = False
        
        try:
            # Phase 1 Enhancement: Check resource limits first
            if not self.resource_manager.acquire_resource_permit(ticket_id):
                self.logger.info("Ticket queued due to resource limits", extra={
                    'ticket_id': ticket_id
                })
                return False  # Task was queued, not failed
            
            resource_permit_acquired = True
            
            # Get file dependencies
            deps = self.get_file_dependencies(ticket_id)
            
            # Try to acquire locks with exponential backoff
            max_retries = 10
            for retry in range(max_retries):
                if self.acquire_file_locks(ticket_id, deps):
                    break
                
                wait_time = min(2 ** retry, 60)  # Cap at 60 seconds
                self.logger.debug("Lock acquisition retry", extra={
                    'ticket_id': ticket_id,
                    'retry': retry + 1,
                    'wait_time': wait_time
                })
                time.sleep(wait_time)
            else:
                self.logger.error("Could not acquire locks after retries", extra={
                    'ticket_id': ticket_id,
                    'max_retries': max_retries
                })
                return False
            
            # Process the ticket
            self.active_tickets.add(ticket_id)
            
            # Call parent's process method for single ticket
            snapshot = self.load_snapshots()[ticket_id]
            if snapshot["status"] in self.transitions:
                agent, next_status = self.transitions[snapshot["status"]]
                
                if agent:
                    self.logger.info("Processing ticket with agent", extra={
                        'ticket_id': ticket_id,
                        'agent': agent,
                        'current_status': snapshot["status"]
                    })
                    
                    context = self.build_context_bundle(ticket_id, snapshot["job_id"])
                    success, output = self.invoke_agent(agent, context)
                    
                    if success:
                        self.workspace_manager.checkpoint_workspace(
                            snapshot["job_id"],
                            f"Completed: {agent}"
                        )
                        snapshot["status"] = next_status
                        self.save_snapshot(ticket_id, snapshot)
                        
                        self.logger.info("Ticket processing completed", extra={
                            'ticket_id': ticket_id,
                            'new_status': next_status
                        })
                        return True
                    else:
                        self.logger.warning("Agent processing failed", extra={
                            'ticket_id': ticket_id,
                            'agent': agent,
                            'output': str(output)[:200]  # Truncate long output
                        })
            
            return False
            
        except Exception as e:
            self.logger.error("Exception during ticket processing", extra={
                'ticket_id': ticket_id,
                'error': str(e)
            })
            return False
            
        finally:
            # Phase 1 Enhancement: Always release resources and locks
            try:
                self.release_file_locks(ticket_id)
                self.active_tickets.discard(ticket_id)
                
                if resource_permit_acquired:
                    self.resource_manager.release_resource_permit(ticket_id)
                    
            except Exception as cleanup_error:
                self.logger.error("Error during cleanup", extra={
                    'ticket_id': ticket_id,
                    'cleanup_error': str(cleanup_error)
                })
    
    def process_all_parallel(self) -> Dict[str, bool]:
        """Process all eligible tickets in parallel."""
        snapshots = self.load_snapshots()
        results = {}
        
        # Find tickets ready for processing
        ready_tickets = [
            ticket_id for ticket_id, snapshot in snapshots.items()
            if snapshot["status"] in self.transitions 
            and snapshot["status"] != "COMPLETED"
            and snapshot["status"] != "FAILED"
        ]
        
        if not ready_tickets:
            return results
        
        # Submit all tickets to executor
        futures = {
            self.executor.submit(self.process_ticket_safe, ticket_id): ticket_id
            for ticket_id in ready_tickets
        }
        
        # Wait for completion
        for future in as_completed(futures):
            ticket_id = futures[future]
            try:
                results[ticket_id] = future.result()
            except Exception as e:
                print(f"Error processing {ticket_id}: {e}")
                results[ticket_id] = False
        
        return results
    
    def get_status_report(self) -> Dict:
        """
        Phase 1 Enhanced: Get detailed status with resource information.
        """
        snapshots = self.load_snapshots()
        resource_status = self.resource_manager.get_resource_status()
        
        report = {
            "active": list(self.active_tickets),
            "blocked": [],
            "ready": [],
            "completed": [],
            "failed": [],
            "queued": [],
            "resource_status": resource_status
        }
        
        for ticket_id, snapshot in snapshots.items():
            status = snapshot["status"]
            
            if status == "COMPLETED":
                report["completed"].append(ticket_id)
            elif status == "FAILED":
                report["failed"].append(ticket_id)
            elif ticket_id in self.active_tickets:
                report["active"].append(ticket_id)
            else:
                # Phase 1 Enhancement: Check registry-based locks instead of in-memory
                deps = self.get_file_dependencies(ticket_id)
                blocked = False
                
                # Check registry for any locked files in dependencies
                cursor = self.registry.conn.cursor()
                for file_path in deps:
                    cursor.execute("""
                        SELECT lock_owner FROM files 
                        WHERE path = ? AND lock_status = 'locked' AND lock_owner != ?
                    """, (file_path, ticket_id))
                    
                    if cursor.fetchone():
                        blocked = True
                        break
                
                if blocked:
                    report["blocked"].append(ticket_id)
                elif (resource_status['cpu_limit_exceeded'] or 
                      resource_status['memory_limit_exceeded'] or 
                      resource_status['task_limit_exceeded']):
                    report["queued"].append(ticket_id)
                else:
                    report["ready"].append(ticket_id)
        
        return report
    
    def shutdown(self):
        """Phase 1 Enhancement: Proper shutdown with resource cleanup."""
        try:
            self.logger.info("Shutting down parallel orchestrator")
            
            # Shutdown resource manager
            self.resource_manager.shutdown()
            
            # Release any remaining locks
            for ticket_id in list(self.active_tickets):
                self.release_file_locks(ticket_id)
            
            # Shutdown executor
            self.executor.shutdown(wait=True, timeout=30)
            
            self.logger.info("Parallel orchestrator shutdown complete")
            
        except Exception as e:
            self.logger.error("Error during shutdown", extra={'error': str(e)})

if __name__ == "__main__":
    import sys
    
    orchestrator = ParallelOrchestrator()
    
    if len(sys.argv) < 2:
        print("Usage: parallel_orchestrator.py <command>")
        print("Commands: process, status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "process":
        results = orchestrator.process_all_parallel()
        print(f"Processed {len(results)} tickets")
        for ticket, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {ticket}: {status}")
    
    elif command == "status":
        report = orchestrator.get_status_report()
        print(json.dumps(report, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)