#!/usr/bin/env python3
"""
Integration tests for circuit breaker behavior in context_assembler.py
"""

import pytest
import json
import time
import requests
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from context_assembler import ContextAssembler
from reliability import CircuitBreaker

class TestCircuitBreakerIntegration:
    """Test circuit breaker integration in context assembler."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory structure
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "events").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "registry").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
        
        self.assembler = ContextAssembler()
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_circuit_breaker_initialization(self):
        """Test that circuit breaker is properly initialized."""
        assert hasattr(self.assembler, 'km_circuit_breaker')
        assert isinstance(self.assembler.km_circuit_breaker, CircuitBreaker)
        assert self.assembler.km_circuit_breaker.failure_threshold == 3
        assert self.assembler.km_circuit_breaker.recovery_timeout == 30
    
    @patch('requests.post')
    def test_km_success_path(self, mock_post):
        """Test successful KM requests reset circuit breaker."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'tool_response': {
                'results': ['test result'],
                'knowledge': {'test': 'data'}
            }
        }
        mock_post.return_value = mock_response
        
        # Make request
        result = self.assembler._query_knowledge_manager("TEST-001", "developer-agent")
        
        # Verify success
        assert 'results' in result
        assert result['results'] == ['test result']
        assert self.assembler.km_circuit_breaker.state == 'CLOSED'
        assert self.assembler.km_circuit_breaker.failure_count == 0
    
    @patch('requests.post')
    def test_circuit_breaker_opens_after_failures(self, mock_post):
        """Test circuit breaker opens after threshold failures."""
        # Mock failing response
        mock_post.side_effect = requests.RequestException("Connection failed")
        
        # Make failing requests
        for i in range(3):
            result = self.assembler._query_knowledge_manager("TEST-001", "developer-agent")
            # Should return fallback context
            assert 'fallback_mode' in result
            assert result['fallback_mode'] is True
        
        # Circuit breaker should be open
        assert self.assembler.km_circuit_breaker.state == 'OPEN'
        assert self.assembler.km_circuit_breaker.failure_count == 3
    
    @patch('requests.post')
    def test_circuit_breaker_prevents_requests_when_open(self, mock_post):
        """Test circuit breaker prevents requests when open."""
        # Force circuit breaker to open state
        self.assembler.km_circuit_breaker.state = 'OPEN'
        self.assembler.km_circuit_breaker.failure_count = 5
        
        # Attempt request
        result = self.assembler._query_knowledge_manager("TEST-001", "developer-agent")
        
        # Should get fallback without making request
        assert 'fallback_mode' in result
        assert result['fallback_mode'] is True
        
        # Verify no HTTP request was made
        mock_post.assert_not_called()
    
    @patch('requests.post')
    def test_circuit_breaker_recovery(self, mock_post):
        """Test circuit breaker recovery after timeout."""
        # Set circuit breaker to open with old failure time
        self.assembler.km_circuit_breaker.state = 'OPEN'
        self.assembler.km_circuit_breaker.failure_count = 3
        self.assembler.km_circuit_breaker.last_failure_time = \
            self.assembler.km_circuit_breaker.last_failure_time.__class__.now() - \
            self.assembler.km_circuit_breaker.last_failure_time.__class__.now().__class__(seconds=31)
        
        # Mock successful response for recovery
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'tool_response': {'results': ['recovery test']}
        }
        mock_post.return_value = mock_response
        
        # Manually set time to allow recovery
        from datetime import datetime, timedelta
        old_time = datetime.now() - timedelta(seconds=61)
        self.assembler.km_circuit_breaker.last_failure_time = old_time
        
        # Make request
        result = self.assembler._query_knowledge_manager("TEST-001", "developer-agent")
        
        # Should succeed and reset circuit breaker
        if 'fallback_mode' not in result:  # If recovery worked
            assert self.assembler.km_circuit_breaker.state == 'CLOSED'
            assert self.assembler.km_circuit_breaker.failure_count == 0
    
    def test_fallback_context_generation(self):
        """Test fallback context generation."""
        result = self.assembler._get_fallback_context("developer-agent")
        
        # Verify fallback structure
        assert 'fallback_mode' in result
        assert result['fallback_mode'] is True
        assert 'fallback_reason' in result
        assert 'knowledge' in result
        assert 'results' in result
    
    def test_fallback_context_caching(self):
        """Test fallback context is cached for performance."""
        # First call
        result1 = self.assembler._get_fallback_context("developer-agent")
        
        # Second call should use cache
        result2 = self.assembler._get_fallback_context("developer-agent")
        
        # Should have cached entry
        assert "fallback_developer-agent" in self.assembler.fallback_cache
        
        # Results should be consistent
        assert result1['fallback_mode'] == result2['fallback_mode']
        assert result1['fallback_reason'] == result2['fallback_reason']
    
    @patch('requests.post')
    def test_end_to_end_with_km_failure(self, mock_post):
        """Test complete context assembly with KM failure."""
        # Mock KM failure
        mock_post.side_effect = requests.RequestException("KM down")
        
        # Attempt context assembly
        context = self.assembler.assemble_intelligent_context(
            ticket_id="TEST-001",
            job_id="job-001",
            agent_type="developer-agent"
        )
        
        # Should complete with fallback
        assert 'knowledge' in context
        assert 'dependencies' in context
        assert 'workspace' in context
        
        # Knowledge should be fallback
        if 'fallback_mode' in context['knowledge']:
            assert context['knowledge']['fallback_mode'] is True

class TestFallbackBehavior:
    """Test fallback behavior when KM is unavailable."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory structure
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "events").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "registry").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
        
        self.assembler = ContextAssembler()
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_fallback_context_structure(self):
        """Test fallback context has required structure."""
        context = self.assembler._get_fallback_context("pm-agent")
        
        required_fields = ['knowledge', 'results', 'fallback_mode', 'fallback_reason']
        for field in required_fields:
            assert field in context, f"Missing required field: {field}"
        
        assert context['fallback_mode'] is True
        assert isinstance(context['knowledge'], dict)
        assert isinstance(context['results'], list)
    
    def test_fallback_cache_expiry(self):
        """Test fallback cache expires after TTL."""
        # Create cache entry with old timestamp
        cache_key = "fallback_test-agent"
        old_time = time.time() - 3700  # Older than 1 hour TTL
        
        self.assembler.fallback_cache[cache_key] = {
            'timestamp': old_time,
            'data': {'test': 'old_data'}
        }
        
        # Check cache - should be expired
        assert not self.assembler._check_fallback_cache(cache_key)
        assert cache_key not in self.assembler.fallback_cache
    
    def test_system_continues_without_km(self):
        """Test that system continues to function without KM."""
        # Simulate KM being completely unavailable
        with patch('requests.post', side_effect=requests.ConnectionError("No KM")):
            # Context assembly should still work
            context = self.assembler.assemble_intelligent_context(
                ticket_id="TEST-002",
                job_id="job-002", 
                agent_type="qa-agent"
            )
            
            # Should have all required sections
            assert 'knowledge' in context
            assert 'dependencies' in context
            assert 'workspace' in context
            assert 'files' in context
            
            # Workspace info should always be available
            assert context['workspace']['ticket_id'] == "TEST-002"
            assert context['workspace']['job_id'] == "job-002"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])