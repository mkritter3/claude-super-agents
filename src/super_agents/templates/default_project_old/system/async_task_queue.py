#!/usr/bin/env python3
"""
AET Async Task Queue - Non-blocking background operations
Part of Phase 1.1: Local Parallel Processing without Batch API
"""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import aiofiles
import aiosqlite
from asyncio import Queue, PriorityQueue as AsyncPriorityQueue

class AsyncTaskPriority(Enum):
    """Priority levels for async tasks"""
    REALTIME = 0     # Must complete immediately
    HIGH = 1         # Should complete soon
    NORMAL = 2       # Regular priority
    LOW = 3          # Can be deferred
    BACKGROUND = 4   # Run when idle

@dataclass(order=True)
class AsyncTask:
    """Represents an async task in the queue"""
    priority: int = field(compare=True)
    task_id: str = field(compare=False)
    agent: str = field(compare=False)
    operation: str = field(compare=False)
    params: Dict = field(default_factory=dict, compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    started_at: Optional[float] = field(default=None, compare=False)
    completed_at: Optional[float] = field(default=None, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    retries: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)

class AsyncTaskQueue:
    """Manages asynchronous task execution for non-blocking operations"""
    
    def __init__(self, project_dir: Path = None, max_concurrent: int = 10):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.state_dir = self.claude_dir / "state"
        self.queue_db = self.state_dir / "async_queue.db"
        
        # Async components
        self.task_queue = AsyncPriorityQueue()
        self.max_concurrent = max_concurrent
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: Dict[str, AsyncTask] = {}
        
        # Background workers
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup async queue logger"""
        log_dir = self.claude_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("AsyncTaskQueue")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_dir / "async_queue.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        
    async def initialize(self):
        """Initialize async components"""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        async with aiosqlite.connect(str(self.queue_db)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS async_tasks (
                    task_id TEXT PRIMARY KEY,
                    agent TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    params TEXT,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    result TEXT,
                    error TEXT,
                    retries INTEGER DEFAULT 0
                )
            """)
            await db.commit()
            
        self.logger.info("Async task queue initialized")
        
    async def start(self):
        """Start the async task queue workers"""
        self.running = True
        
        # Start worker coroutines
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
            
        # Start persistence worker
        persistence = asyncio.create_task(self._persistence_worker())
        self.workers.append(persistence)
        
        self.logger.info(f"Started {self.max_concurrent} async workers")
        
    async def stop(self):
        """Stop all workers gracefully"""
        self.running = False
        
        # Wait for workers to complete current tasks
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.logger.info("Async task queue stopped")
        
    async def submit(self, agent: str, operation: str, params: Dict = None,
                    priority: AsyncTaskPriority = AsyncTaskPriority.NORMAL,
                    callback: Optional[Callable] = None) -> str:
        """Submit an async task to the queue"""
        task_id = str(uuid.uuid4())[:8]
        
        task = AsyncTask(
            priority=priority.value,
            task_id=task_id,
            agent=agent,
            operation=operation,
            params=params or {},
            callback=callback
        )
        
        # Add to queue
        await self.task_queue.put(task)
        
        # Persist to database
        await self._persist_task(task)
        
        self.logger.info(f"Submitted async task {task_id}: {agent}.{operation}")
        
        return task_id
        
    async def _worker(self, worker_id: str):
        """Worker coroutine that processes tasks from the queue"""
        self.logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get task with timeout to allow checking running flag
                task = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
                
                # Mark as active
                self.active_tasks[task.task_id] = asyncio.current_task()
                
                # Execute task
                self.logger.info(f"Worker {worker_id} executing {task.task_id}")
                task.started_at = time.time()
                
                try:
                    result = await self._execute_task(task)
                    task.result = result
                    task.completed_at = time.time()
                    
                    # Run callback if provided
                    if task.callback:
                        await self._run_callback(task.callback, result)
                        
                    self.logger.info(f"Task {task.task_id} completed successfully")
                    
                except Exception as e:
                    task.error = str(e)
                    task.completed_at = time.time()
                    
                    # Retry logic
                    if task.retries < task.max_retries:
                        task.retries += 1
                        task.error = None
                        task.started_at = None
                        task.completed_at = None
                        
                        # Re-queue with exponential backoff
                        await asyncio.sleep(2 ** task.retries)
                        await self.task_queue.put(task)
                        
                        self.logger.warning(
                            f"Task {task.task_id} failed, retrying "
                            f"({task.retries}/{task.max_retries}): {e}"
                        )
                    else:
                        self.logger.error(f"Task {task.task_id} failed permanently: {e}")
                        
                # Update database
                await self._update_task_status(task)
                
                # Move to completed
                self.completed_tasks[task.task_id] = task
                del self.active_tasks[task.task_id]
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                
        self.logger.info(f"Worker {worker_id} stopped")
        
    async def _execute_task(self, task: AsyncTask) -> Any:
        """Execute a specific async task"""
        
        # Map operations to handlers
        handlers = {
            "update_documentation": self._update_documentation,
            "generate_metrics": self._generate_metrics,
            "optimize_performance": self._optimize_performance,
            "cleanup_logs": self._cleanup_logs,
            "validate_contracts": self._validate_contracts,
            "index_codebase": self._index_codebase,
            "generate_report": self._generate_report,
            "sync_state": self._sync_state
        }
        
        handler = handlers.get(task.operation)
        if handler:
            return await handler(task.agent, task.params)
        else:
            # Fallback to generic agent execution
            return await self._execute_agent_async(task.agent, task.params)
            
    async def _execute_agent_async(self, agent: str, params: Dict) -> Dict:
        """Execute an agent asynchronously"""
        # This would integrate with the actual agent execution
        # For now, simulate async work
        await asyncio.sleep(1)
        
        return {
            "status": "completed",
            "agent": agent,
            "params": params,
            "timestamp": time.time()
        }
        
    async def _update_documentation(self, agent: str, params: Dict) -> Dict:
        """Async documentation update"""
        self.logger.info(f"Updating documentation for {params.get('file', 'unknown')}")
        
        # Simulate documentation generation
        await asyncio.sleep(2)
        
        return {
            "status": "documentation_updated",
            "files": params.get('files', []),
            "timestamp": time.time()
        }
        
    async def _generate_metrics(self, agent: str, params: Dict) -> Dict:
        """Generate performance metrics asynchronously"""
        self.logger.info("Generating performance metrics")
        
        # Simulate metric collection
        await asyncio.sleep(1.5)
        
        return {
            "cpu_usage": 45.2,
            "memory_usage": 62.8,
            "task_throughput": 125,
            "timestamp": time.time()
        }
        
    async def _optimize_performance(self, agent: str, params: Dict) -> Dict:
        """Run performance optimization in background"""
        self.logger.info("Running performance optimization")
        
        # Simulate optimization
        await asyncio.sleep(3)
        
        return {
            "optimizations_applied": 5,
            "performance_gain": "12%",
            "timestamp": time.time()
        }
        
    async def _cleanup_logs(self, agent: str, params: Dict) -> Dict:
        """Clean up old log files"""
        log_dir = self.claude_dir / "logs"
        cleaned = 0
        
        # Find old logs
        cutoff = datetime.now() - timedelta(days=params.get('days', 7))
        
        for log_file in log_dir.glob("*.log"):
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                log_file.unlink()
                cleaned += 1
                
        return {
            "logs_cleaned": cleaned,
            "timestamp": time.time()
        }
        
    async def _validate_contracts(self, agent: str, params: Dict) -> Dict:
        """Validate API contracts asynchronously"""
        self.logger.info("Validating API contracts")
        
        # Simulate validation
        await asyncio.sleep(2)
        
        return {
            "contracts_validated": 15,
            "violations": 0,
            "timestamp": time.time()
        }
        
    async def _index_codebase(self, agent: str, params: Dict) -> Dict:
        """Index codebase for search"""
        self.logger.info("Indexing codebase")
        
        # Simulate indexing
        await asyncio.sleep(4)
        
        return {
            "files_indexed": 247,
            "index_size": "12.4MB",
            "timestamp": time.time()
        }
        
    async def _generate_report(self, agent: str, params: Dict) -> Dict:
        """Generate async report"""
        report_type = params.get('type', 'summary')
        self.logger.info(f"Generating {report_type} report")
        
        # Simulate report generation
        await asyncio.sleep(2.5)
        
        return {
            "report_type": report_type,
            "status": "generated",
            "timestamp": time.time()
        }
        
    async def _sync_state(self, agent: str, params: Dict) -> Dict:
        """Sync state across components"""
        self.logger.info("Syncing state")
        
        # Simulate state sync
        await asyncio.sleep(1)
        
        return {
            "components_synced": 8,
            "timestamp": time.time()
        }
        
    async def _run_callback(self, callback: Callable, result: Any):
        """Run callback with result"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(result)
            else:
                callback(result)
        except Exception as e:
            self.logger.error(f"Callback error: {e}")
            
    async def _persist_task(self, task: AsyncTask):
        """Persist task to database"""
        async with aiosqlite.connect(str(self.queue_db)) as db:
            await db.execute("""
                INSERT OR REPLACE INTO async_tasks
                (task_id, agent, operation, priority, params, status,
                 created_at, started_at, completed_at, result, error, retries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.agent,
                task.operation,
                task.priority,
                json.dumps(task.params),
                "pending",
                task.created_at,
                task.started_at,
                task.completed_at,
                json.dumps(task.result) if task.result else None,
                task.error,
                task.retries
            ))
            await db.commit()
            
    async def _update_task_status(self, task: AsyncTask):
        """Update task status in database"""
        status = "completed" if task.completed_at and not task.error else "failed"
        if not task.started_at:
            status = "pending"
        elif task.started_at and not task.completed_at:
            status = "running"
            
        async with aiosqlite.connect(str(self.queue_db)) as db:
            await db.execute("""
                UPDATE async_tasks SET
                status = ?, started_at = ?, completed_at = ?,
                result = ?, error = ?, retries = ?
                WHERE task_id = ?
            """, (
                status,
                task.started_at,
                task.completed_at,
                json.dumps(task.result) if task.result else None,
                task.error,
                task.retries,
                task.task_id
            ))
            await db.commit()
            
    async def _persistence_worker(self):
        """Periodically save queue state to disk"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Save every 30 seconds
                
                # Save active tasks
                for task_id in list(self.active_tasks.keys()):
                    if task_id in self.active_tasks:
                        # Task still active, update heartbeat
                        async with aiosqlite.connect(str(self.queue_db)) as db:
                            await db.execute(
                                "UPDATE async_tasks SET status = 'running' WHERE task_id = ?",
                                (task_id,)
                            )
                            await db.commit()
                            
            except Exception as e:
                self.logger.error(f"Persistence worker error: {e}")
                
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        # Check active tasks
        if task_id in self.active_tasks:
            return {"status": "running", "task_id": task_id}
            
        # Check completed tasks
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "status": "completed" if not task.error else "failed",
                "task_id": task_id,
                "result": task.result,
                "error": task.error
            }
            
        # Check database
        async with aiosqlite.connect(str(self.queue_db)) as db:
            async with db.execute(
                "SELECT * FROM async_tasks WHERE task_id = ?",
                (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return {
                        "task_id": row[0],
                        "agent": row[1],
                        "operation": row[2],
                        "status": row[5],
                        "result": json.loads(row[9]) if row[9] else None,
                        "error": row[10]
                    }
                    
        return None
        
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        stats = {
            "queued": self.task_queue.qsize(),
            "active": len(self.active_tasks),
            "completed": len(self.completed_tasks)
        }
        
        # Get database stats
        async with aiosqlite.connect(str(self.queue_db)) as db:
            async with db.execute(
                "SELECT status, COUNT(*) FROM async_tasks GROUP BY status"
            ) as cursor:
                async for row in cursor:
                    stats[f"db_{row[0]}"] = row[1]
                    
        return stats


async def main():
    """Example usage of async task queue"""
    queue = AsyncTaskQueue(max_concurrent=5)
    await queue.initialize()
    await queue.start()
    
    # Submit various async tasks
    tasks = []
    
    # High priority task
    task_id = await queue.submit(
        agent="documentation-agent",
        operation="update_documentation",
        params={"files": ["main.py", "utils.py"]},
        priority=AsyncTaskPriority.HIGH
    )
    tasks.append(task_id)
    
    # Normal priority tasks
    task_id = await queue.submit(
        agent="performance-optimizer",
        operation="generate_metrics",
        priority=AsyncTaskPriority.NORMAL
    )
    tasks.append(task_id)
    
    # Background task
    task_id = await queue.submit(
        agent="maintenance-agent",
        operation="cleanup_logs",
        params={"days": 7},
        priority=AsyncTaskPriority.BACKGROUND
    )
    tasks.append(task_id)
    
    print(f"Submitted {len(tasks)} async tasks")
    
    # Wait a bit for processing
    await asyncio.sleep(5)
    
    # Check status
    for task_id in tasks:
        status = await queue.get_task_status(task_id)
        print(f"Task {task_id}: {status}")
        
    # Get stats
    stats = await queue.get_queue_stats()
    print(f"Queue stats: {stats}")
    
    # Shutdown
    await queue.stop()


if __name__ == "__main__":
    asyncio.run(main())