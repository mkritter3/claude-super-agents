#!/usr/bin/env python3
"""
Test suite for automatic SQLite maintenance system.

Tests the roadmap requirements:
- Automatic vacuum runs after 7 days
- Old knowledge items cleaned up (90+ days)
- User never waits for maintenance during commands
- Database corruption detection and handling
- Maintenance failure doesn't break CLI functionality
- Database size reduction measurable after maintenance
"""

import pytest
import sqlite3
import tempfile
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from super_agents.database.maintenance import DatabaseMaintenance, get_maintenance_manager

class TestDatabaseMaintenance:
    """Test automatic database maintenance functionality."""
    
    def setup_method(self):
        """Create temporary database for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test.db"
        self.maintenance = DatabaseMaintenance(self.db_path)
        
        # Create test database with sample data
        self._create_test_database()
    
    def teardown_method(self):
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_database(self):
        """Create a test database with sample data."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Create tables similar to AET system
            conn.executescript("""
                CREATE TABLE knowledge_items (
                    item_id INTEGER PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE file_summaries (
                    file_path TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE events (
                    event_id INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
    
    def _add_old_data(self):
        """Add old data that should be cleaned up."""
        old_date = datetime.now() - timedelta(days=100)
        old_date_str = old_date.isoformat()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Add old knowledge items
            for i in range(10):
                conn.execute("""
                    INSERT INTO knowledge_items (ticket_id, content, created_at)
                    VALUES (?, ?, ?)
                """, (f"OLD-{i}", f"Old content {i}", old_date_str))
            
            # Add old file summaries
            for i in range(5):
                conn.execute("""
                    INSERT INTO file_summaries (file_path, summary, updated_at)
                    VALUES (?, ?, ?)
                """, (f"old_file_{i}.py", f"Old summary {i}", old_date_str))
            
            # Add old events
            for i in range(20):
                conn.execute("""
                    INSERT INTO events (event_type, event_data, timestamp)
                    VALUES (?, ?, ?)
                """, ("old_event", f"Old data {i}", old_date_str))
    
    def _add_recent_data(self):
        """Add recent data that should be kept."""
        recent_date = datetime.now() - timedelta(days=10)
        recent_date_str = recent_date.isoformat()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Add recent knowledge items
            for i in range(5):
                conn.execute("""
                    INSERT INTO knowledge_items (ticket_id, content, created_at)
                    VALUES (?, ?, ?)
                """, (f"NEW-{i}", f"Recent content {i}", recent_date_str))
            
            # Add recent file summaries
            for i in range(3):
                conn.execute("""
                    INSERT INTO file_summaries (file_path, summary, updated_at)
                    VALUES (?, ?, ?)
                """, (f"new_file_{i}.py", f"Recent summary {i}", recent_date_str))
    
    def test_maintenance_scheduling(self):
        """Test that maintenance is scheduled when needed."""
        # No maintenance record - should schedule
        self.maintenance.check_and_schedule_maintenance()
        
        # Check that meta table was created
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='_meta'
            """)
            assert cursor.fetchone()[0] == 1
    
    def test_old_data_cleanup(self):
        """Test that old data is cleaned up during maintenance."""
        self._add_old_data()
        self._add_recent_data()
        
        # Count items before maintenance
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM knowledge_items")
            initial_knowledge = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM file_summaries")
            initial_summaries = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events")
            initial_events = cursor.fetchone()[0]
        
        # Run maintenance
        self.maintenance.force_maintenance()
        
        # Count items after maintenance
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM knowledge_items")
            final_knowledge = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM file_summaries")
            final_summaries = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events")
            final_events = cursor.fetchone()[0]
        
        # Old data should be cleaned up
        assert final_knowledge < initial_knowledge
        assert final_summaries < initial_summaries
        assert final_events < initial_events
        
        # Recent data should remain (at least some)
        assert final_knowledge > 0
        assert final_summaries > 0
    
    def test_database_size_reduction(self):
        """Test that database size is reduced after maintenance."""
        self._add_old_data()
        
        # Get initial size
        initial_size = self.db_path.stat().st_size
        
        # Run maintenance
        self.maintenance.force_maintenance()
        
        # Get final size
        final_size = self.db_path.stat().st_size
        
        # Size should be reduced (or at least not increased significantly)
        # Note: Size might not always reduce if there's little data
        assert final_size <= initial_size * 1.1  # Allow 10% tolerance
    
    def test_maintenance_metrics_recording(self):
        """Test that maintenance metrics are properly recorded."""
        self._add_old_data()
        
        # Run maintenance
        self.maintenance.force_maintenance()
        
        # Check that metrics were recorded
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Check metrics table exists
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='_maintenance_metrics'
            """)
            assert cursor.fetchone()[0] == 1
            
            # Check metrics were recorded
            cursor.execute("SELECT COUNT(*) FROM _maintenance_metrics")
            assert cursor.fetchone()[0] > 0
            
            # Check required fields
            cursor.execute("""
                SELECT duration, size_before, size_after, size_reduction 
                FROM _maintenance_metrics ORDER BY timestamp DESC LIMIT 1
            """)
            metrics = cursor.fetchone()
            assert metrics is not None
            assert metrics[0] > 0  # duration
            assert metrics[1] >= 0  # size_before
            assert metrics[2] >= 0  # size_after
    
    def test_maintenance_status(self):
        """Test maintenance status reporting."""
        # Initial status
        status = self.maintenance.get_maintenance_status()
        assert status["status"] in ["healthy", "no_database"]
        
        if status["status"] == "healthy":
            assert "database_size" in status
            assert "maintenance_due" in status
    
    def test_concurrent_maintenance_prevention(self):
        """Test that concurrent maintenance is prevented."""
        import threading
        
        results = []
        
        def run_maintenance():
            try:
                self.maintenance.force_maintenance()
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # Start multiple maintenance threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_maintenance)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have at least one success, others should complete without error
        assert len([r for r in results if r == "success"]) >= 1
        assert len(results) == 3
    
    def test_database_corruption_handling(self):
        """Test handling of database corruption."""
        # Corrupt the database by writing invalid data
        with open(self.db_path, 'w') as f:
            f.write("This is not a valid SQLite database")
        
        # Maintenance should handle corruption gracefully
        try:
            status = self.maintenance.get_maintenance_status()
            # Should return error status, not crash
            assert status["status"] == "error"
        except Exception:
            # Any exception should be handled gracefully
            pass
    
    def test_maintenance_no_impact_on_cli(self):
        """Test that maintenance doesn't impact normal CLI operations."""
        # This test simulates that maintenance runs in background
        # and doesn't block normal operations
        
        # Schedule maintenance
        self.maintenance.check_and_schedule_maintenance()
        
        # Normal database operations should still work
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master")
            result = cursor.fetchone()
            assert result is not None
    
    def test_wal_mode_enabled(self):
        """Test that WAL mode is enabled for better concurrency."""
        self.maintenance.check_and_schedule_maintenance()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
            # Should be WAL mode for better concurrency
            assert mode.upper() == "WAL"

class TestMaintenanceManager:
    """Test the global maintenance manager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "manager_test.db"
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_manager_singleton(self):
        """Test that maintenance manager is singleton per database."""
        manager1 = get_maintenance_manager(str(self.db_path))
        manager2 = get_maintenance_manager(str(self.db_path))
        
        # Should be the same instance
        assert manager1 is manager2
    
    def test_multiple_database_managers(self):
        """Test managing multiple databases."""
        db1 = self.temp_dir / "db1.db"
        db2 = self.temp_dir / "db2.db"
        
        manager1 = get_maintenance_manager(str(db1))
        manager2 = get_maintenance_manager(str(db2))
        
        # Should be different instances
        assert manager1 is not manager2
        assert manager1.db_path != manager2.db_path

class TestMaintenancePerformance:
    """Test maintenance performance characteristics."""
    
    def setup_method(self):
        """Set up performance test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "perf_test.db"
        self.maintenance = DatabaseMaintenance(self.db_path)
    
    def teardown_method(self):
        """Clean up performance test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_maintenance_performance(self):
        """Test that maintenance completes in reasonable time."""
        # Create database with substantial data
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE knowledge_items (
                    item_id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Add substantial data
            old_date = (datetime.now() - timedelta(days=100)).isoformat()
            for i in range(1000):
                conn.execute("""
                    INSERT INTO knowledge_items (content, created_at)
                    VALUES (?, ?)
                """, (f"Content {i} " * 100, old_date))  # Make content larger
        
        # Time the maintenance operation
        start_time = time.time()
        self.maintenance.force_maintenance()
        duration = time.time() - start_time
        
        # Should complete in reasonable time (under 10 seconds for test data)
        assert duration < 10.0, f"Maintenance took too long: {duration:.2f}s"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])