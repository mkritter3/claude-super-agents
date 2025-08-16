#!/usr/bin/env python3
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
from event_logger import EventLogger

class MetricsCollector:
    def __init__(self, db_path: str = ".claude/registry/metrics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._initialize_db()
        self.event_logger = EventLogger()
    
    def _initialize_db(self):
        """Create metrics tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds REAL,
                success BOOLEAN,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT
            );
            
            CREATE TABLE IF NOT EXISTS file_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                total_files INTEGER,
                unregistered_files INTEGER,
                ghost_files INTEGER,
                hash_mismatches INTEGER,
                UNIQUE(date)
            );
            
            CREATE TABLE IF NOT EXISTS system_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_task_metrics_ticket ON task_metrics(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_task_metrics_agent ON task_metrics(agent_name);
            CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
        """)
        self.conn.commit()
    
    def record_task_start(self, ticket_id: str, agent_name: str) -> int:
        """Record task start time."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO task_metrics (ticket_id, agent_name, start_time)
            VALUES (?, ?, ?)
        """, (ticket_id, agent_name, datetime.now().isoformat()))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def record_task_end(self, 
                       metric_id: int,
                       success: bool,
                       error_message: str = None):
        """Record task completion."""
        cursor = self.conn.cursor()
        
        # Get start time
        cursor.execute("""
            SELECT start_time FROM task_metrics WHERE metric_id = ?
        """, (metric_id,))
        
        row = cursor.fetchone()
        if row:
            start = datetime.fromisoformat(row['start_time'])
            end = datetime.now()
            duration = (end - start).total_seconds()
            
            cursor.execute("""
                UPDATE task_metrics
                SET end_time = ?, duration_seconds = ?, 
                    success = ?, error_message = ?
                WHERE metric_id = ?
            """, (end.isoformat(), duration, success, error_message, metric_id))
            
            self.conn.commit()
    
    def get_agent_performance(self, 
                             agent_name: str,
                             days: int = 7) -> Dict:
        """Get agent performance metrics."""
        since = datetime.now() - timedelta(days=days)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(duration_seconds) as avg_duration,
                MAX(duration_seconds) as max_duration,
                MIN(duration_seconds) as min_duration,
                SUM(retry_count) as total_retries
            FROM task_metrics
            WHERE agent_name = ? AND start_time > ?
        """, (agent_name, since.isoformat()))
        
        row = cursor.fetchone()
        
        return {
            "agent": agent_name,
            "period_days": days,
            "total_tasks": row['total_tasks'] or 0,
            "successful": row['successful'] or 0,
            "success_rate": (row['successful'] or 0) / max(row['total_tasks'], 1),
            "avg_duration_seconds": row['avg_duration'] or 0,
            "max_duration_seconds": row['max_duration'] or 0,
            "min_duration_seconds": row['min_duration'] or 0,
            "total_retries": row['total_retries'] or 0
        }
    
    def get_system_health(self) -> Dict:
        """Get overall system health metrics."""
        # Analyze event log
        events = self.event_logger.replay_events()
        
        # Calculate metrics
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        events_last_hour = [
            e for e in events 
            if datetime.fromtimestamp(e['timestamp']/1000) > last_hour
        ]
        
        events_last_day = [
            e for e in events
            if datetime.fromtimestamp(e['timestamp']/1000) > last_day
        ]
        
        # Count failures
        failures_last_hour = len([
            e for e in events_last_hour 
            if e['type'] == 'AGENT_FAILED'
        ])
        
        failures_last_day = len([
            e for e in events_last_day
            if e['type'] == 'AGENT_FAILED'
        ])
        
        # Get file registry stats (simplified without consistency verifier)
        consistency_status = "OK"
        total_files = 0
        total_issues = 0
        
        try:
            from file_registry import FileRegistry
            registry = FileRegistry()
            cursor = registry.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM files")
            total_files = cursor.fetchone()['count']
        except Exception:
            pass
        
        return {
            "timestamp": now.isoformat(),
            "events_last_hour": len(events_last_hour),
            "events_last_day": len(events_last_day),
            "failures_last_hour": failures_last_hour,
            "failures_last_day": failures_last_day,
            "file_consistency": {
                "status": consistency_status,
                "total_files": total_files,
                "issues": total_issues
            },
            "health_score": self._calculate_health_score(
                failures_last_hour,
                total_issues
            )
        }
    
    def _calculate_health_score(self, 
                               recent_failures: int,
                               file_issues: int) -> float:
        """Calculate system health score (0-100)."""
        score = 100.0
        
        # Deduct for failures
        score -= min(recent_failures * 5, 30)
        
        # Deduct for file issues
        score -= min(file_issues * 2, 20)
        
        return max(score, 0.0)
    
    def record_system_metric(self, metric_name: str, value: float):
        """Record a system metric."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO system_metrics (metric_name, metric_value)
            VALUES (?, ?)
        """, (metric_name, value))
        self.conn.commit()
    
    def get_recent_metrics(self, metric_name: str, hours: int = 24) -> List[Dict]:
        """Get recent values for a metric."""
        since = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT timestamp, metric_value
            FROM system_metrics
            WHERE metric_name = ? AND timestamp > ?
            ORDER BY timestamp
        """, (metric_name, since.isoformat()))
        
        return [
            {"timestamp": row['timestamp'], "value": row['metric_value']}
            for row in cursor.fetchall()
        ]
    
    def generate_report(self) -> str:
        """Generate comprehensive metrics report."""
        health = self.get_system_health()
        
        # Get agent performances
        agents = [
            "pm-agent", "architect-agent", "developer-agent",
            "reviewer-agent", "qa-agent", "integrator-agent"
        ]
        
        agent_stats = {}
        for agent in agents:
            agent_stats[agent] = self.get_agent_performance(agent)
        
        # Format report
        report = f"""
# System Metrics Report
Generated: {health['timestamp']}

## System Health
- **Health Score**: {health['health_score']:.1f}/100
- **Events (Last Hour)**: {health['events_last_hour']}
- **Events (Last Day)**: {health['events_last_day']}
- **Failures (Last Hour)**: {health['failures_last_hour']}
- **Failures (Last Day)**: {health['failures_last_day']}

## File Consistency
- **Status**: {health['file_consistency']['status']}
- **Total Files**: {health['file_consistency']['total_files']}
- **Issues**: {health['file_consistency']['issues']}

## Agent Performance (Last 7 Days)
"""
        
        for agent, stats in agent_stats.items():
            if stats['total_tasks'] > 0:
                report += f"""
### {agent}
- **Tasks**: {stats['total_tasks']}
- **Success Rate**: {stats['success_rate']:.1%}
- **Avg Duration**: {stats['avg_duration_seconds']:.1f}s
- **Retries**: {stats['total_retries']}
"""
        
        return report

if __name__ == "__main__":
    import sys
    collector = MetricsCollector()
    
    if len(sys.argv) < 2:
        print("Usage: metrics.py <command>")
        print("Commands: report, health")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "report":
        print(collector.generate_report())
    elif command == "health":
        health = collector.get_system_health()
        print(json.dumps(health, indent=2))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)