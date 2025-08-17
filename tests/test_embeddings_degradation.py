#!/usr/bin/env python3
"""
Test suite for embeddings graceful degradation.

Tests the roadmap requirement that CLI starts successfully without 
sentence-transformers and provides functional fallback search.
"""

import pytest
import sys
import unittest.mock
import numpy as np
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from super_agents.features import embeddings

class TestEmbeddingsGracefulDegradation:
    """Test graceful degradation when sentence-transformers is not available."""
    
    def setup_method(self):
        """Reset global state before each test."""
        embeddings._embedding_model = None
        embeddings._import_failed = False
        embeddings._warning_shown = False
    
    def test_import_failure_graceful_handling(self, capsys):
        """Test that ImportError is handled gracefully."""
        # Mock import failure
        with unittest.mock.patch.dict('sys.modules', {'sentence_transformers': None}):
            with unittest.mock.patch('builtins.__import__', side_effect=ImportError("No module named 'sentence_transformers'")):
                model = embeddings.get_embedding_model()
                
        # Should return None and show warning
        assert model is None
        assert embeddings._import_failed is True
        
        # Check warning message
        captured = capsys.readouterr()
        assert "sentence-transformers' not found" in captured.err
        assert "pip install sentence-transformers" in captured.err
    
    def test_warning_shown_only_once(self, capsys):
        """Test that warning message is displayed exactly once per session."""
        # Mock import failure
        with unittest.mock.patch.dict('sys.modules', {'sentence_transformers': None}):
            with unittest.mock.patch('builtins.__import__', side_effect=ImportError()):
                # Call multiple times
                embeddings.get_embedding_model()
                embeddings.get_embedding_model()
                embeddings.get_embedding_model()
        
        # Warning should only appear once
        captured = capsys.readouterr()
        warning_count = captured.err.count("sentence-transformers' not found")
        assert warning_count == 1
    
    def test_keyword_similarity_functionality(self):
        """Test that keyword similarity provides functional search."""
        # Test basic keyword matching
        query = "python function error"
        content = "This Python function throws an error when called"
        
        similarity = embeddings.keyword_similarity(query, content)
        assert 0.0 < similarity <= 1.0
        assert similarity > 0.5  # Should have decent overlap
        
        # Test no match
        no_match = embeddings.keyword_similarity("cats dogs", "javascript react")
        assert no_match == 0.0
        
        # Test exact match
        exact_match = embeddings.keyword_similarity("test", "test")
        assert exact_match > 0.0
    
    def test_enhanced_keyword_similarity(self):
        """Test enhanced keyword similarity with title boosting."""
        query = "authentication error"
        title = "Authentication Error Handler"
        content = "This module handles user authentication failures"
        
        enhanced_score = embeddings.enhanced_keyword_similarity(query, content, title)
        basic_score = embeddings.keyword_similarity(query, content)
        
        # Enhanced should be better due to title match
        assert enhanced_score > basic_score
        assert enhanced_score <= 1.0
    
    def test_phrase_matching_bonus(self):
        """Test that phrase matching provides bonus scoring."""
        query = "user authentication"
        
        # Exact phrase in title
        title_match = embeddings.enhanced_keyword_similarity(
            query, "Some content here", "User Authentication Module"
        )
        
        # Exact phrase in content
        content_match = embeddings.enhanced_keyword_similarity(
            query, "Handle user authentication errors", "Different Title"
        )
        
        # Separate words only
        word_match = embeddings.enhanced_keyword_similarity(
            query, "User login and authentication system", "System Module"
        )
        
        # Title match should score highest
        assert title_match > content_match > word_match
    
    def test_encode_text_fallback(self):
        """Test that encode_text returns None when model unavailable."""
        # Mock import failure
        with unittest.mock.patch.dict('sys.modules', {'sentence_transformers': None}):
            with unittest.mock.patch('builtins.__import__', side_effect=ImportError()):
                result = embeddings.encode_text("test content")
                
        assert result is None
    
    def test_search_mode_detection(self):
        """Test search mode detection functions."""
        # Mock import failure
        with unittest.mock.patch.dict('sys.modules', {'sentence_transformers': None}):
            with unittest.mock.patch('builtins.__import__', side_effect=ImportError()):
                assert not embeddings.is_semantic_search_available()
                assert embeddings.get_search_mode() == "keyword"
    
    def test_compute_similarity_error_handling(self):
        """Test similarity computation error handling."""
        # Test with invalid embeddings
        query_emb = np.array([1, 2, 3])
        doc_emb = np.array([0, 0, 0])  # Zero vector
        
        # Should handle division by zero gracefully
        similarity = embeddings.compute_similarity(query_emb, doc_emb)
        assert similarity == 0.0
        
        # Test with valid embeddings
        query_emb = np.array([1, 0, 0])
        doc_emb = np.array([1, 0, 0])
        
        similarity = embeddings.compute_similarity(query_emb, doc_emb)
        assert similarity == 1.0

class TestEmbeddingsPerformance:
    """Test performance characteristics of fallback search."""
    
    def test_keyword_search_performance(self):
        """Test that keyword search performance is acceptable."""
        import time
        
        # Large content for performance testing
        large_content = " ".join(["performance test content"] * 1000)
        query = "performance test"
        
        start_time = time.time()
        for _ in range(100):
            embeddings.keyword_similarity(query, large_content)
        end_time = time.time()
        
        # Should complete 100 searches in under 1 second
        duration = end_time - start_time
        assert duration < 1.0, f"Keyword search too slow: {duration:.3f}s for 100 searches"
    
    def test_enhanced_search_performance(self):
        """Test enhanced keyword search performance."""
        import time
        
        content = "Authentication system with user login functionality"
        title = "Auth Module"
        query = "user authentication"
        
        start_time = time.time()
        for _ in range(1000):
            embeddings.enhanced_keyword_similarity(query, content, title)
        end_time = time.time()
        
        # Should be fast enough for real-time search
        duration = end_time - start_time
        assert duration < 0.5, f"Enhanced search too slow: {duration:.3f}s for 1000 searches"

class TestEmbeddingsFunctionality:
    """Test that all core functionality remains available."""
    
    def test_core_search_functionality_without_embeddings(self):
        """Test that core search works without embeddings."""
        # Mock import failure
        with unittest.mock.patch.dict('sys.modules', {'sentence_transformers': None}):
            with unittest.mock.patch('builtins.__import__', side_effect=ImportError()):
                # Should be able to perform searches
                results = []
                
                # Mock knowledge items
                items = [
                    {"title": "Authentication Module", "content": "User authentication system"},
                    {"title": "Database Helper", "content": "Database connection utilities"},
                    {"title": "Error Handler", "content": "Authentication error handling"},
                ]
                
                query = "authentication error"
                
                for item in items:
                    score = embeddings.enhanced_keyword_similarity(
                        query, item["content"], item["title"]
                    )
                    results.append((item, score))
                
                # Sort by score
                results.sort(key=lambda x: x[1], reverse=True)
                
                # Should find relevant items
                assert len(results) > 0
                assert results[0][1] > 0  # Best match should have positive score
                
                # Most relevant should be authentication-related
                best_match = results[0][0]
                assert "authentication" in best_match["title"].lower() or \
                       "authentication" in best_match["content"].lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])