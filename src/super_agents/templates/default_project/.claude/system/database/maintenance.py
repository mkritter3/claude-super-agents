#!/usr/bin/env python3
"""
Automatic SQLite maintenance system for CLI reliability improvements.

Implements zero-maintenance database optimization as specified in the roadmap.
"""

import sqlite3
import atexit
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DatabaseMaintenance:
    """Automatic SQLite maintenance with background operations."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.maintenance_interval_days = 7
        self.cleanup_threshold_days = 90
        self.maintenance_running = False
        self._lock = threading.Lock()
        
    def check_and_schedule_maintenance(self):
        """Check if maintenance is needed and schedule it."""
        if not self.db_path.exists():
            return
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
                
                # Ensure meta table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS _meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check last maintenance
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM _meta WHERE key = 'last_vacuum_at'")
                result = cursor.fetchone()
                
                last_maintenance = None
                if result:
                    try:
                        last_maintenance = datetime.fromisoformat(result[0])
                    except (ValueError, TypeError):
                        logger.warning("Invalid last_vacuum_at timestamp, forcing maintenance")
                
                # Check if maintenance is needed
                if (last_maintenance is None or 
                    datetime.now() - last_maintenance >= timedelta(days=self.maintenance_interval_days)):
                    
                    logger.info("Scheduling database maintenance")
                    # Schedule maintenance to run after main command completes
                    atexit.register(self._run_maintenance_worker)
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to check maintenance schedule: {e}")
    
    def _run_maintenance_worker(self):
        """Background maintenance worker."""
        if self.maintenance_running:
            return
            
        with self._lock:
            if self.maintenance_running:
                return
            self.maintenance_running = True
        
        try:
            self._perform_maintenance()
        finally:
            self.maintenance_running = False
    
    def _perform_maintenance(self):
        """Perform database maintenance operations."""
        if not self.db_path.exists():
            return
        
        start_time = time.time()
        logger.info(f"Starting database maintenance for {self.db_path}")
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Get initial database size
                initial_size = self.db_path.stat().st_size
                
                # 1. Clean up old knowledge items
                cleanup_date = datetime.now() - timedelta(days=self.cleanup_threshold_days)
                
                if self._table_exists(conn, 'knowledge_items'):
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM knowledge_items 
                        WHERE created_at < ?
                    """, (cleanup_date.isoformat(),))
                    deleted_knowledge = cursor.rowcount
                    logger.info(f"Cleaned up {deleted_knowledge} old knowledge items")
                
                # 2. Clean up old file summaries
                if self._table_exists(conn, 'file_summaries'):
                    cursor.execute("""
                        DELETE FROM file_summaries 
                        WHERE updated_at < ?
                    """, (cleanup_date.isoformat(),))
                    deleted_summaries = cursor.rowcount
                    logger.info(f"Cleaned up {deleted_summaries} old file summaries")
                
                # 3. Clean up old events (keep last 30 days)
                event_cleanup_date = datetime.now() - timedelta(days=30)
                if self._table_exists(conn, 'events'):
                    cursor.execute("""
                        DELETE FROM events 
                        WHERE timestamp < ?
                    """, (event_cleanup_date.isoformat(),))
                    deleted_events = cursor.rowcount
                    logger.info(f"Cleaned up {deleted_events} old events")
                
                # 4. Update statistics (analyze tables)
                logger.info("Updating database statistics")
                conn.execute("ANALYZE")
                
                # 5. Vacuum database
                logger.info("Vacuuming database")
                conn.execute("VACUUM")
                
                # 6. Update maintenance timestamp
                conn.execute("""
                    INSERT OR REPLACE INTO _meta (key, value, updated_at)
                    VALUES ('last_vacuum_at', ?, ?)
                """, (datetime.now().isoformat(), datetime.now().isoformat()))
                
                # Log results
                final_size = self.db_path.stat().st_size
                size_reduction = initial_size - final_size
                duration = time.time() - start_time
                
                logger.info(f"Database maintenance completed in {duration:.2f}s")
                logger.info(f"Size reduction: {size_reduction:,} bytes ({size_reduction/1024:.1f} KB)")
                
                # Store maintenance metrics
                self._record_maintenance_metrics(conn, {
                    "duration": duration,
                    "size_before": initial_size,
                    "size_after": final_size,
                    "size_reduction": size_reduction,
                    "deleted_knowledge": deleted_knowledge if 'deleted_knowledge' in locals() else 0,
                    "deleted_summaries": deleted_summaries if 'deleted_summaries' in locals() else 0,
                    "deleted_events": deleted_events if 'deleted_events' in locals() else 0
                })
                
        except sqlite3.Error as e:
            logger.error(f"Database maintenance failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during maintenance: {e}")
    
    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if a table exists in the database."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone()[0] > 0
    
    def _record_maintenance_metrics(self, conn: sqlite3.Connection, metrics: Dict[str, Any]):
        """Record maintenance metrics for monitoring."""
        try:
            # Create metrics table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _maintenance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration REAL NOT NULL,
                    size_before INTEGER NOT NULL,
                    size_after INTEGER NOT NULL,
                    size_reduction INTEGER NOT NULL,
                    deleted_knowledge INTEGER DEFAULT 0,
                    deleted_summaries INTEGER DEFAULT 0,
                    deleted_events INTEGER DEFAULT 0
                )
            """)
            
            # Insert metrics
            conn.execute("""
                INSERT INTO _maintenance_metrics 
                (duration, size_before, size_after, size_reduction, 
                 deleted_knowledge, deleted_summaries, deleted_events)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics["duration"],
                metrics["size_before"],
                metrics["size_after"],
                metrics["size_reduction"],
                metrics["deleted_knowledge"],
                metrics["deleted_summaries"],
                metrics["deleted_events"]
            ))
            
            # Keep only last 50 maintenance records
            conn.execute("""
                DELETE FROM _maintenance_metrics 
                WHERE id NOT IN (
                    SELECT id FROM _maintenance_metrics 
                    ORDER BY timestamp DESC LIMIT 50
                )
            """)
            
        except sqlite3.Error as e:
            logger.error(f"Failed to record maintenance metrics: {e}")
    
    def get_maintenance_status(self) -> Dict[str, Any]:
        """Get current maintenance status."""
        if not self.db_path.exists():
            return {"status": "no_database"}
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Get last maintenance time
                cursor.execute("SELECT value FROM _meta WHERE key = 'last_vacuum_at'")
                result = cursor.fetchone()
                
                last_maintenance = None
                if result:
                    try:
                        last_maintenance = datetime.fromisoformat(result[0])
                    except (ValueError, TypeError):
                        pass
                
                # Get database size
                db_size = self.db_path.stat().st_size
                
                # Get recent maintenance metrics
                cursor.execute("""
                    SELECT * FROM _maintenance_metrics 
                    ORDER BY timestamp DESC LIMIT 1
                """)
                last_metrics = cursor.fetchone()
                
                return {
                    "status": "healthy",
                    "database_size": db_size,
                    "last_maintenance": last_maintenance.isoformat() if last_maintenance else None,
                    "days_since_maintenance": (datetime.now() - last_maintenance).days if last_maintenance else None,
                    "maintenance_due": (
                        last_maintenance is None or 
                        datetime.now() - last_maintenance >= timedelta(days=self.maintenance_interval_days)
                    ),
                    "last_metrics": dict(zip([
                        "id", "timestamp", "duration", "size_before", "size_after", 
                        "size_reduction", "deleted_knowledge", "deleted_summaries", "deleted_events"
                    ], last_metrics)) if last_metrics else None
                }
                
        except sqlite3.Error as e:
            return {"status": "error", "error": str(e)}
    
    def force_maintenance(self) -> bool:
        """Force immediate maintenance (for testing/admin purposes)."""
        try:
            self._perform_maintenance()
            return True
        except Exception as e:
            logger.error(f"Forced maintenance failed: {e}")
            return False

# Global maintenance managers for common databases
_maintenance_managers = {}

def get_maintenance_manager(db_path: str) -> DatabaseMaintenance:
    """Get or create maintenance manager for a database."""
    db_path = str(Path(db_path).resolve())
    
    if db_path not in _maintenance_managers:
        _maintenance_managers[db_path] = DatabaseMaintenance(db_path)
    
    return _maintenance_managers[db_path]

def check_maintenance_for_db(db_path: str):
    """Check and schedule maintenance for a specific database."""
    manager = get_maintenance_manager(db_path)
    manager.check_and_schedule_maintenance()

def check_all_maintenance():
    """Check maintenance for all common database files."""
    # Common database locations in AET system
    common_dbs = [
        ".claude/registry/files.db",
        ".claude/registry/knowledge.db",
        ".claude/registry/metrics.db",
        ".claude/registry/registry.db",
        ".claude/state/task_queue.db"
    ]
    
    for db_path in common_dbs:
        if Path(db_path).exists():
            check_maintenance_for_db(db_path)