#!/usr/bin/env python3
"""
AET Parallel Executor - Phase 1.1 Implementation
Enables parallel agent execution using local process pools without Batch API dependency
"""

import os
import json
import time
import asyncio
import sqlite3
import hashlib
import multiprocessing
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from queue import PriorityQueue
import logging
from enum import Enum
import pickle
import tempfile
import subprocess
import signal
import psutil

# Task priority levels
class TaskPriority(Enum):
    CRITICAL = 1    # Pre-commit hooks, security checks
    HIGH = 2        # Contract guardian, incident response  
    NORMAL = 3      # Development, testing
    LOW = 4         # Documentation, optimization
    DEFERRED = 5    # Background tasks

# Task status
class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AgentTask:
    """Represents a task to be executed by an agent"""
    task_id: str
    agent: str
    priority: TaskPriority
    params: Dict[str, Any]
    dependencies: List[str] = None
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.dependencies is None:
            self.dependencies = []
            
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentTask':
        """Create from dictionary"""
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        return cls(**data)

class ParallelExecutor:
    """Manages parallel execution of agent tasks using local resources"""
    
    def __init__(self, project_dir: Path = None, max_workers: int = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.state_dir = self.claude_dir / "state"
        self.queue_db = self.state_dir / "task_queue.db"
        
        # Determine optimal worker count
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = max_workers or min(8, max(2, cpu_count - 1))
        
        # Executors for different task types
        self.process_pool = None  # For CPU-bound tasks
        self.thread_pool = None   # For I/O-bound tasks
        
        # Task tracking
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}
        self.task_dependencies: Dict[str, List[str]] = {}
        
        # Initialize components
        self._setup_logging()
        self._init_database()
        self._start_executors()
        
    def _setup_logging(self):
        """Setup parallel execution logger"""
        log_dir = self.claude_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("ParallelExecutor")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_dir / "parallel_executor.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        
    def _init_database(self):
        """Initialize SQLite database for persistent task queue"""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_queue (
                task_id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                priority INTEGER NOT NULL,
                params TEXT NOT NULL,
                dependencies TEXT,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                result TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status_priority 
            ON task_queue(status, priority, created_at)
        """)
        
        conn.commit()
        conn.close()
        
    def _start_executors(self):
        """Start process and thread pools"""
        self.process_pool = ProcessPoolExecutor(max_workers=self.max_workers)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers * 2)
        
        self.logger.info(f"Started executors with {self.max_workers} process workers")
        
    def submit_task(self, agent: str, params: Dict[str, Any], 
                   priority: TaskPriority = TaskPriority.NORMAL,
                   dependencies: List[str] = None) -> str:
        """Submit a task for parallel execution"""
        # Generate unique task ID
        task_data = f"{agent}:{json.dumps(params)}:{time.time()}"
        task_id = hashlib.sha256(task_data.encode()).hexdigest()[:16]
        
        # Create task
        task = AgentTask(
            task_id=task_id,
            agent=agent,
            priority=priority,
            params=params,
            dependencies=dependencies or []
        )
        
        # Store in database
        self._store_task(task)
        
        self.logger.info(f"Submitted task {task_id} for agent {agent} with priority {priority.name}")
        
        return task_id
        
    def submit_batch(self, tasks: List[Tuple[str, Dict, TaskPriority]]) -> List[str]:
        """Submit multiple tasks at once"""
        task_ids = []
        
        for agent, params, priority in tasks:
            task_id = self.submit_task(agent, params, priority)
            task_ids.append(task_id)
            
        self.logger.info(f"Submitted batch of {len(task_ids)} tasks")
        return task_ids
        
    def _store_task(self, task: AgentTask):
        """Store task in persistent queue"""
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO task_queue 
            (task_id, agent, priority, params, dependencies, status, 
             created_at, started_at, completed_at, result, error, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.agent,
            task.priority.value,
            json.dumps(task.params),
            json.dumps(task.dependencies),
            task.status.value,
            task.created_at,
            task.started_at,
            task.completed_at,
            json.dumps(task.result) if task.result else None,
            task.error,
            task.retry_count
        ))
        
        conn.commit()
        conn.close()
        
    def _get_next_task(self) -> Optional[AgentTask]:
        """Get next task from queue respecting priorities and dependencies"""
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        # Get pending tasks ordered by priority
        cursor.execute("""
            SELECT * FROM task_queue 
            WHERE status = ? 
            ORDER BY priority ASC, created_at ASC
            LIMIT 10
        """, (TaskStatus.PENDING.value,))
        
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            task = self._row_to_task(row)
            
            # Check dependencies
            if self._can_run_task(task):
                return task
                
        return None
        
    def _row_to_task(self, row) -> AgentTask:
        """Convert database row to AgentTask"""
        return AgentTask(
            task_id=row[0],
            agent=row[1],
            priority=TaskPriority(row[2]),
            params=json.loads(row[3]),
            dependencies=json.loads(row[4]) if row[4] else [],
            status=TaskStatus(row[5]),
            created_at=row[6],
            started_at=row[7],
            completed_at=row[8],
            result=json.loads(row[9]) if row[9] else None,
            error=row[10],
            retry_count=row[11]
        )
        
    def _can_run_task(self, task: AgentTask) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.dependencies:
            return True
            
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        # Check if all dependencies are completed
        placeholders = ','.join(['?'] * len(task.dependencies))
        cursor.execute(f"""
            SELECT COUNT(*) FROM task_queue 
            WHERE task_id IN ({placeholders}) 
            AND status = ?
        """, task.dependencies + [TaskStatus.COMPLETED.value])
        
        completed_count = cursor.fetchone()[0]
        conn.close()
        
        return completed_count == len(task.dependencies)
        
    async def process_queue(self):
        """Main processing loop for task queue"""
        self.logger.info("Starting queue processor")
        
        while True:
            try:
                # Get next available task
                task = self._get_next_task()
                
                if task:
                    # Mark as running
                    task.status = TaskStatus.RUNNING
                    task.started_at = time.time()
                    self._store_task(task)
                    
                    # Determine execution strategy
                    if self._is_cpu_bound(task.agent):
                        future = self.process_pool.submit(self._execute_agent, task)
                    else:
                        future = self.thread_pool.submit(self._execute_agent, task)
                        
                    # Track active task
                    self.active_tasks[task.task_id] = (task, future)
                    
                # Check completed tasks
                self._check_completed_tasks()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
                
    def _check_completed_tasks(self):
        """Check and handle completed tasks"""
        completed = []
        
        for task_id, (task, future) in self.active_tasks.items():
            if future.done():
                try:
                    result = future.result(timeout=0)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = time.time()
                    
                    self.logger.info(f"Task {task_id} completed successfully")
                    
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    task.completed_at = time.time()
                    
                    # Retry logic
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.status = TaskStatus.PENDING
                        self.logger.warning(f"Task {task_id} failed, retrying ({task.retry_count}/{task.max_retries})")
                    else:
                        self.logger.error(f"Task {task_id} failed after {task.max_retries} retries: {e}")
                        
                # Update database
                self._store_task(task)
                completed.append(task_id)
                
        # Remove from active tasks
        for task_id in completed:
            del self.active_tasks[task_id]
            
    def _is_cpu_bound(self, agent: str) -> bool:
        """Determine if agent task is CPU-bound"""
        cpu_bound_agents = [
            "architect-agent",
            "developer-agent", 
            "test-executor",
            "performance-optimizer-agent"
        ]
        return agent in cpu_bound_agents
        
    def _execute_agent(self, task: AgentTask) -> Dict[str, Any]:
        """Execute an agent task (runs in worker process/thread)"""
        try:
            # Import here to avoid pickling issues
            from operational_orchestrator import OperationalOrchestrator
            
            # Create orchestrator instance
            orchestrator = OperationalOrchestrator()
            
            # Execute agent
            result = orchestrator.execute_agent(
                agent=task.agent,
                task_type=task.params.get('task_type', 'general'),
                context=task.params.get('context', {}),
                prompt=task.params.get('prompt', '')
            )
            
            return result
            
        except Exception as e:
            raise Exception(f"Agent execution failed: {e}")
            
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            task = self._row_to_task(row)
            return task.to_dict()
        return None
        
    def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics about the task queue"""
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        stats = {}
        
        for status in TaskStatus:
            cursor.execute(
                "SELECT COUNT(*) FROM task_queue WHERE status = ?",
                (status.value,)
            )
            stats[status.name.lower()] = cursor.fetchone()[0]
            
        conn.close()
        
        stats['active_workers'] = len(self.active_tasks)
        stats['max_workers'] = self.max_workers
        
        return stats
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        conn = sqlite3.connect(str(self.queue_db))
        cursor = conn.cursor()
        
        # Check if task exists and is cancellable
        cursor.execute(
            "SELECT status FROM task_queue WHERE task_id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        
        if row and row[0] in [TaskStatus.PENDING.value, TaskStatus.QUEUED.value]:
            cursor.execute(
                "UPDATE task_queue SET status = ? WHERE task_id = ?",
                (TaskStatus.CANCELLED.value, task_id)
            )
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cancelled task {task_id}")
            return True
            
        conn.close()
        return False
        
    def shutdown(self, wait: bool = True):
        """Shutdown the executor gracefully"""
        self.logger.info("Shutting down parallel executor")
        
        if self.process_pool:
            self.process_pool.shutdown(wait=wait)
        if self.thread_pool:
            self.thread_pool.shutdown(wait=wait)
            
        self.logger.info("Parallel executor shutdown complete")


class TaskRouter:
    """Routes tasks to appropriate execution strategy"""
    
    def __init__(self, executor: ParallelExecutor):
        self.executor = executor
        
    def route_task(self, agent: str, task_data: Dict) -> str:
        """Route task based on criticality and type"""
        
        # Determine priority
        priority = self._determine_priority(agent, task_data)
        
        # Check for dependencies
        dependencies = self._identify_dependencies(agent, task_data)
        
        # Submit to executor
        task_id = self.executor.submit_task(
            agent=agent,
            params=task_data,
            priority=priority,
            dependencies=dependencies
        )
        
        return task_id
        
    def _determine_priority(self, agent: str, task_data: Dict) -> TaskPriority:
        """Determine task priority based on agent and context"""
        
        # Critical agents
        if agent in ["contract-guardian", "security-agent"]:
            return TaskPriority.CRITICAL
            
        # High priority agents
        if agent in ["incident-response-agent", "test-executor"]:
            return TaskPriority.HIGH
            
        # Check for blocking operations
        if task_data.get('blocking', False):
            return TaskPriority.HIGH
            
        # Background tasks
        if agent in ["documentation-agent", "performance-optimizer-agent"]:
            return TaskPriority.LOW
            
        return TaskPriority.NORMAL
        
    def _identify_dependencies(self, agent: str, task_data: Dict) -> List[str]:
        """Identify task dependencies"""
        dependencies = []
        
        # Explicit dependencies
        if 'depends_on' in task_data:
            dependencies.extend(task_data['depends_on'])
            
        # Agent-specific dependencies
        if agent == "integrator-agent":
            # Integrator depends on tests passing
            dependencies.append("test-executor")
            
        if agent == "documentation-agent":
            # Docs depend on code being complete
            dependencies.append("developer-agent")
            
        return dependencies


def main():
    """CLI interface for parallel executor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AET Parallel Executor")
    parser.add_argument('--start', action='store_true',
                       help='Start the parallel executor')
    parser.add_argument('--submit', metavar='AGENT:TASK',
                       help='Submit a task (e.g., developer-agent:implement_feature)')
    parser.add_argument('--status', metavar='TASK_ID',
                       help='Get status of a task')
    parser.add_argument('--stats', action='store_true',
                       help='Show queue statistics')
    parser.add_argument('--workers', type=int,
                       help='Number of worker processes')
    
    args = parser.parse_args()
    
    if args.start:
        # Start executor and process queue
        executor = ParallelExecutor(max_workers=args.workers)
        
        print(f"Started parallel executor with {executor.max_workers} workers")
        print("Processing queue... (Ctrl+C to stop)")
        
        try:
            asyncio.run(executor.process_queue())
        except KeyboardInterrupt:
            print("\nShutting down...")
            executor.shutdown()
            
    elif args.submit:
        # Submit a task
        parts = args.submit.split(':', 1)
        if len(parts) == 2:
            agent, task_type = parts
            
            executor = ParallelExecutor()
            router = TaskRouter(executor)
            
            task_id = router.route_task(agent, {
                'task_type': task_type,
                'prompt': f"Execute {task_type} task"
            })
            
            print(f"Submitted task: {task_id}")
            executor.shutdown(wait=False)
            
    elif args.status:
        # Get task status
        executor = ParallelExecutor()
        status = executor.get_task_status(args.status)
        
        if status:
            print(json.dumps(status, indent=2))
        else:
            print(f"Task {args.status} not found")
            
        executor.shutdown(wait=False)
        
    elif args.stats:
        # Show statistics
        executor = ParallelExecutor()
        stats = executor.get_queue_stats()
        
        print("=== Task Queue Statistics ===")
        for key, value in stats.items():
            print(f"{key:20}: {value}")
            
        executor.shutdown(wait=False)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()