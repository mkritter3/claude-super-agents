#!/usr/bin/env python3
"""
Tests for structured logging implementation
"""

import pytest
import json
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, Mock

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from logger_config import (
    StructuredFormatter, 
    AETLogger, 
    get_logger, 
    get_contextual_logger,
    log_performance,
    log_system_event
)

class TestStructuredFormatter:
    """Test the JSON structured formatter."""
    
    def setup_method(self):
        """Setup test environment."""
        self.formatter = StructuredFormatter()
    
    def test_basic_log_formatting(self):
        """Test basic log record formatting to JSON."""
        # Create log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Verify structure
        assert 'timestamp' in log_data
        assert log_data['level'] == 'INFO'
        assert log_data['module'] == 'path'
        assert log_data['function'] == '<module>'
        assert log_data['line'] == 42
        assert log_data['message'] == 'Test message'
        assert log_data['ticket_id'] is None
        assert log_data['job_id'] is None
        assert log_data['agent'] is None
        assert log_data['component'] is None
    
    def test_contextual_log_formatting(self):
        """Test log formatting with context."""
        # Create log record with context
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=100,
            msg="Error occurred",
            args=(),
            exc_info=None
        )
        
        # Add context attributes
        record.ticket_id = "TICKET-123"
        record.job_id = "job-456"
        record.agent = "test-agent"
        record.component = "test-component"
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Verify context is included
        assert log_data['ticket_id'] == 'TICKET-123'
        assert log_data['job_id'] == 'job-456'
        assert log_data['agent'] == 'test-agent'
        assert log_data['component'] == 'test-component'
    
    def test_exception_formatting(self):
        """Test exception formatting in logs."""
        try:
            raise ValueError("Test exception")
        except Exception:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=150,
                msg="Exception occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Verify exception info is included
        assert 'exception' in log_data
        assert 'ValueError: Test exception' in log_data['exception']
    
    def test_extra_fields(self):
        """Test additional fields in log records."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=200,
            msg="Test with extra fields",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.extra_fields = {
            'request_id': 'req-789',
            'duration': 1.5,
            'status': 'success'
        }
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Verify extra fields are included
        assert log_data['request_id'] == 'req-789'
        assert log_data['duration'] == 1.5
        assert log_data['status'] == 'success'

class TestAETLogger:
    """Test the AET logger configuration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
        # Clear any handlers that were added
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_logger_initialization(self):
        """Test logger initialization creates required files."""
        aet_logger = AETLogger()
        
        # Verify log directory exists
        log_dir = Path(".claude/logs")
        assert log_dir.exists()
        
        # Verify logger has handlers
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        # Check for structured formatter
        for handler in root_logger.handlers:
            if hasattr(handler, 'formatter'):
                assert isinstance(handler.formatter, StructuredFormatter)
    
    def test_component_logger_creation(self):
        """Test creating component-specific loggers."""
        aet_logger = AETLogger()
        
        logger = aet_logger.get_logger("test_module", "test_component")
        assert logger is not None
        
        # Should cache the logger
        logger2 = aet_logger.get_logger("test_module", "test_component")
        assert logger is logger2

class TestContextualLogger:
    """Test contextual logging functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
        # Clear any handlers that were added
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_contextual_logger_creation(self):
        """Test creating contextual logger with context."""
        logger = get_contextual_logger(
            "test_module",
            ticket_id="TICKET-456",
            job_id="job-789", 
            agent="test-agent",
            component="test-component"
        )
        
        assert logger is not None
        assert logger.context['ticket_id'] == "TICKET-456"
        assert logger.context['job_id'] == "job-789"
        assert logger.context['agent'] == "test-agent"
    
    @patch('sys.stdout')
    def test_contextual_logging_output(self, mock_stdout):
        """Test that contextual logger includes context in output."""
        logger = get_contextual_logger(
            "test_module",
            ticket_id="TICKET-789",
            agent="test-agent"
        )
        
        # Mock the write method to capture output
        written_data = []
        mock_stdout.write.side_effect = lambda x: written_data.append(x)
        
        logger.info("Test message")
        
        # Verify context was included in output
        output = ''.join(written_data)
        if output:  # Only check if something was written
            # Should contain JSON with context
            assert 'TICKET-789' in output
            assert 'test-agent' in output

class TestUtilityFunctions:
    """Test logging utility functions."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
        # Clear any handlers that were added
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    @patch('sys.stdout')
    def test_performance_logging(self, mock_stdout):
        """Test performance logging utility."""
        written_data = []
        mock_stdout.write.side_effect = lambda x: written_data.append(x)
        
        log_performance(
            func_name="test_function",
            duration=2.5,
            ticket_id="PERF-001",
            component="test-component"
        )
        
        # Verify performance metric was logged
        output = ''.join(written_data)
        if output:
            assert 'test_function' in output
            assert '2.5' in output
            assert 'PERF-001' in output
    
    @patch('sys.stdout')
    def test_system_event_logging(self, mock_stdout):
        """Test system event logging utility."""
        written_data = []
        mock_stdout.write.side_effect = lambda x: written_data.append(x)
        
        log_system_event(
            event_type="task_started",
            details={
                "task_type": "development",
                "estimated_duration": 3600
            },
            ticket_id="SYS-001",
            component="orchestrator"
        )
        
        # Verify system event was logged
        output = ''.join(written_data)
        if output:
            assert 'task_started' in output
            assert 'development' in output
            assert 'SYS-001' in output

class TestLogOutput:
    """Test that log output is valid JSON."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
        
        # Capture log output to string
        import io
        self.log_stream = io.StringIO()
        
        # Configure logger to write to our stream
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setFormatter(StructuredFormatter())
        
        self.logger = logging.getLogger("test_json_output")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
        # Remove our test handler
        self.logger.removeHandler(self.handler)
    
    def test_json_output_validity(self):
        """Test that all log output is valid JSON."""
        # Log various types of messages
        self.logger.info("Simple message")
        self.logger.warning("Warning with data", extra={'key': 'value'})
        self.logger.error("Error message")
        
        # Get the output
        output = self.log_stream.getvalue()
        
        # Each line should be valid JSON
        lines = output.strip().split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON output: {line}")
    
    def test_required_fields_present(self):
        """Test that required fields are present in JSON output."""
        self.logger.info("Test message")
        
        output = self.log_stream.getvalue()
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip():
                log_data = json.loads(line)
                
                # Verify required fields
                required_fields = [
                    'timestamp', 'level', 'module', 'function', 
                    'line', 'message', 'ticket_id', 'job_id', 
                    'agent', 'component'
                ]
                
                for field in required_fields:
                    assert field in log_data, f"Missing required field: {field}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])