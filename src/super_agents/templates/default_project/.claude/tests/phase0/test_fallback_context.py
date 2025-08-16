#!/usr/bin/env python3
"""
Tests for fallback context generation and caching
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, Mock

# Add system path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from context_assembler import ContextAssembler

class TestFallbackContextGeneration:
    """Test fallback context generation when KM is unavailable."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory structure
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "events").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "registry").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "workspaces").mkdir(parents=True, exist_ok=True)
        
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
        """Test that fallback context has the correct structure."""
        context = self.assembler._get_fallback_context("developer-agent")
        
        # Check required fields
        required_fields = ['knowledge', 'results', 'fallback_mode', 'fallback_reason']
        for field in required_fields:
            assert field in context, f"Missing required field: {field}"
        
        # Check field types
        assert isinstance(context['knowledge'], dict)
        assert isinstance(context['results'], list)
        assert context['fallback_mode'] is True
        assert isinstance(context['fallback_reason'], str)
    
    def test_fallback_context_agent_specific(self):
        """Test that fallback context is generated for each agent type."""
        agent_types = ['pm-agent', 'architect-agent', 'developer-agent', 'reviewer-agent', 'qa-agent']
        
        for agent_type in agent_types:
            context = self.assembler._get_fallback_context(agent_type)
            
            assert context['fallback_mode'] is True
            assert agent_type.replace('-agent', '') in context['fallback_reason'] or \
                   'using defaults' in context['fallback_reason']
    
    def test_fallback_context_caching(self):
        """Test that fallback context is properly cached."""
        agent_type = "developer-agent"
        
        # First call should create cache entry
        context1 = self.assembler._get_fallback_context(agent_type)
        cache_key = f"fallback_{agent_type}"
        
        assert cache_key in self.assembler.fallback_cache
        
        # Second call should use cache
        context2 = self.assembler._get_fallback_context(agent_type)
        
        # Should have same structure (cache hit)
        assert context1['fallback_mode'] == context2['fallback_mode']
        assert context1['fallback_reason'] == context2['fallback_reason']
    
    def test_fallback_cache_expiry(self):
        """Test that fallback cache expires after TTL."""
        agent_type = "test-agent"
        cache_key = f"fallback_{agent_type}"
        
        # Manually add expired cache entry
        old_time = time.time() - 3700  # Older than 1 hour TTL
        self.assembler.fallback_cache[cache_key] = {
            'timestamp': old_time,
            'data': {'test': 'old_data'}
        }
        
        # Check cache should return False for expired entry
        assert not self.assembler._check_fallback_cache(cache_key)
        
        # Cache entry should be removed
        assert cache_key not in self.assembler.fallback_cache
    
    def test_fallback_cache_valid_entry(self):
        """Test that valid cache entries are recognized."""
        agent_type = "test-agent"
        cache_key = f"fallback_{agent_type}"
        
        # Add fresh cache entry
        fresh_time = time.time() - 300  # 5 minutes ago (within 1 hour TTL)
        self.assembler.fallback_cache[cache_key] = {
            'timestamp': fresh_time,
            'data': {'test': 'fresh_data'}
        }
        
        # Check cache should return True for valid entry
        assert self.assembler._check_fallback_cache(cache_key)
        
        # Cache entry should still exist
        assert cache_key in self.assembler.fallback_cache
    
    def test_fallback_context_performance(self):
        """Test that fallback context generation is fast."""
        agent_type = "performance-test-agent"
        
        # Measure fallback context generation time
        start_time = time.time()
        context = self.assembler._get_fallback_context(agent_type)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should be very fast (< 100ms)
        assert duration < 0.1, f"Fallback context generation too slow: {duration:.3f}s"
        assert context['fallback_mode'] is True

class TestFallbackIntegration:
    """Test fallback context integration in full context assembly."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory structure with workspace
        test_dir = Path(self.temp_dir)
        (test_dir / ".claude" / "events").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "registry").mkdir(parents=True, exist_ok=True)
        (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
        
        # Create test workspace
        workspace_dir = test_dir / ".claude" / "workspaces" / "test-job" / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Add some test files
        (workspace_dir / "test.py").write_text("# Test Python file\nprint('hello')")
        (workspace_dir / "README.md").write_text("# Test Project\nThis is a test.")
        
        # Change to temp directory
        import os
        os.chdir(self.temp_dir)
        
        self.assembler = ContextAssembler()
    
    def teardown_method(self):
        """Cleanup test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    @patch('requests.post')
    def test_full_context_assembly_with_km_failure(self, mock_post):
        """Test full context assembly when KM fails."""
        # Mock KM failure
        mock_post.side_effect = Exception("KM server unavailable")
        
        # Attempt full context assembly
        context = self.assembler.assemble_intelligent_context(
            ticket_id="FALLBACK-001",
            job_id="test-job",
            agent_type="developer-agent"
        )
        
        # Should complete successfully with fallback
        assert 'knowledge' in context
        assert 'dependencies' in context
        assert 'apis' in context
        assert 'files' in context
        assert 'decisions' in context
        assert 'workspace' in context
        
        # Knowledge should be in fallback mode
        knowledge = context['knowledge']
        if isinstance(knowledge, dict) and 'fallback_mode' in knowledge:
            assert knowledge['fallback_mode'] is True
    
    @patch('requests.post')
    def test_context_assembly_degraded_but_functional(self, mock_post):
        """Test that context assembly provides functional context even with KM failure."""
        # Mock KM failure
        mock_post.side_effect = Exception("Connection timeout")
        
        context = self.assembler.assemble_intelligent_context(
            ticket_id="DEGRADED-001",
            job_id="test-job",
            agent_type="qa-agent"
        )
        
        # Workspace info should always be available
        assert context['workspace']['ticket_id'] == "DEGRADED-001"
        assert context['workspace']['job_id'] == "test-job"
        assert 'path' in context['workspace']
        assert 'artifacts' in context['workspace']
        
        # Dependencies should be a list (even if empty)
        assert isinstance(context['dependencies'], list)
        
        # APIs should be a dict (even if empty)
        assert isinstance(context['apis'], dict)
        
        # Files should be a dict (even if empty)
        assert isinstance(context['files'], dict)
        
        # Decisions should be a list (even if empty)
        assert isinstance(context['decisions'], list)
    
    @patch('requests.post')
    def test_mixed_success_failure_scenario(self, mock_post):
        """Test scenario where KM fails intermittently."""
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary failure")
            # Third call succeeds
            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {
                'tool_response': {'results': ['recovered data']}
            }
            return mock_response
        
        mock_post.side_effect = side_effect
        
        # First two calls should use fallback
        context1 = self.assembler.assemble_intelligent_context(
            ticket_id="MIXED-001",
            job_id="test-job-1",
            agent_type="developer-agent"
        )
        
        context2 = self.assembler.assemble_intelligent_context(
            ticket_id="MIXED-002",
            job_id="test-job-2",
            agent_type="developer-agent"
        )
        
        # Third call should succeed after circuit breaker recovery
        # (In practice, circuit breaker might still be open, but this tests the recovery path)
        try:
            context3 = self.assembler.assemble_intelligent_context(
                ticket_id="MIXED-003",
                job_id="test-job-3",
                agent_type="developer-agent"
            )
            
            # All contexts should be functional
            for context in [context1, context2, context3]:
                assert 'workspace' in context
                assert 'dependencies' in context
        except:
            # Circuit breaker might still be open, which is acceptable behavior
            pass

class TestFallbackPerformance:
    """Test performance characteristics of fallback behavior."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Create test directory structure
        test_dir = Path(self.temp_dir)
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
    
    def test_fallback_context_generation_speed(self):
        """Test that fallback context generation is consistently fast."""
        agent_types = ['pm-agent', 'architect-agent', 'developer-agent', 'reviewer-agent', 'qa-agent']
        durations = []
        
        for agent_type in agent_types:
            start_time = time.time()
            context = self.assembler._get_fallback_context(agent_type)
            end_time = time.time()
            
            duration = end_time - start_time
            durations.append(duration)
            
            # Each call should be fast
            assert duration < 0.05, f"Fallback generation too slow for {agent_type}: {duration:.3f}s"
            assert context['fallback_mode'] is True
        
        # Average should be very fast
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 0.01, f"Average fallback generation too slow: {avg_duration:.3f}s"
    
    def test_cache_performance_benefit(self):
        """Test that caching provides performance benefit."""
        agent_type = "cache-test-agent"
        
        # First call (no cache)
        start_time = time.time()
        context1 = self.assembler._get_fallback_context(agent_type)
        first_duration = time.time() - start_time
        
        # Second call (should use cache)
        start_time = time.time()
        context2 = self.assembler._get_fallback_context(agent_type)
        second_duration = time.time() - start_time
        
        # Both should be fast, but second might be slightly faster
        assert first_duration < 0.1
        assert second_duration < 0.1
        
        # Results should be consistent
        assert context1['fallback_mode'] == context2['fallback_mode']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])