#!/usr/bin/env python3
"""
Embeddings module with graceful degradation for sentence-transformers dependency.

This module implements the roadmap requirement for making sentence-transformers
truly optional while maintaining semantic search functionality through fallbacks.
"""

import sys
import logging
from typing import Optional, List
import numpy as np

# Global state for embedding model
_embedding_model = None
_import_failed = False
_warning_shown = False

logger = logging.getLogger(__name__)

def get_embedding_model():
    """
    Get the sentence transformer model with graceful degradation.
    
    Returns:
        SentenceTransformer model if available, None if not installed
    """
    global _embedding_model, _import_failed, _warning_shown
    
    if _import_failed:
        return None
        
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformers loaded successfully")
        except ImportError:
            if not _warning_shown:
                print("Warning: 'sentence-transformers' not found. Semantic search disabled.", file=sys.stderr)
                print("To enable enhanced search, run: pip install sentence-transformers", file=sys.stderr)
                _warning_shown = True
            _import_failed = True
            logger.warning("Sentence transformers not available, using keyword fallback")
            return None
        except Exception as e:
            if not _warning_shown:
                print(f"Warning: Failed to load sentence-transformers: {e}", file=sys.stderr)
                print("Falling back to keyword search.", file=sys.stderr)
                _warning_shown = True
            _import_failed = True
            logger.error(f"Failed to load sentence transformers: {e}")
            return None
            
    return _embedding_model

def encode_text(text: str) -> Optional[np.ndarray]:
    """
    Encode text to embedding vector.
    
    Args:
        text: Input text to encode
        
    Returns:
        Embedding vector if model available, None otherwise
    """
    model = get_embedding_model()
    if model is None:
        return None
        
    try:
        return model.encode(text)
    except Exception as e:
        logger.error(f"Failed to encode text: {e}")
        return None

def compute_similarity(query_embedding: np.ndarray, doc_embedding: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.
    
    Args:
        query_embedding: Query embedding vector
        doc_embedding: Document embedding vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    try:
        # Cosine similarity
        similarity = np.dot(query_embedding, doc_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
        )
        # Ensure result is in [0, 1] range
        return max(0.0, min(1.0, float(similarity)))
    except Exception as e:
        logger.error(f"Failed to compute similarity: {e}")
        return 0.0

def keyword_similarity(query: str, content: str) -> float:
    """
    Fallback keyword-based similarity calculation.
    
    This is used when sentence-transformers is not available.
    
    Args:
        query: Search query
        content: Content to match against
        
    Returns:
        Similarity score (0-1) based on keyword overlap
    """
    if not query or not content:
        return 0.0
        
    # Normalize and tokenize
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    
    if not query_words:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = query_words.intersection(content_words)
    union = query_words.union(content_words)
    
    if not union:
        return 0.0
        
    jaccard = len(intersection) / len(union)
    
    # Also consider simple word overlap ratio
    overlap_ratio = len(intersection) / len(query_words)
    
    # Combine both metrics for better results
    return (jaccard + overlap_ratio) / 2

def enhanced_keyword_similarity(query: str, content: str, title: str = "") -> float:
    """
    Enhanced keyword similarity with title boosting and phrase matching.
    
    Args:
        query: Search query
        content: Content to match against  
        title: Optional title for boosting
        
    Returns:
        Enhanced similarity score (0-1)
    """
    if not query:
        return 0.0
        
    # Combine title and content with title getting higher weight
    full_text = f"{title} {title} {content}".strip()
    
    # Basic keyword similarity
    base_score = keyword_similarity(query, full_text)
    
    # Phrase matching bonus
    query_lower = query.lower()
    content_lower = content.lower()
    title_lower = title.lower()
    
    phrase_bonus = 0.0
    
    # Exact phrase match in title (high bonus)
    if query_lower in title_lower:
        phrase_bonus += 0.3
        
    # Exact phrase match in content (medium bonus)
    elif query_lower in content_lower:
        phrase_bonus += 0.15
        
    # Partial phrase matches
    query_words = query_lower.split()
    if len(query_words) > 1:
        # Check for consecutive word matches
        for i in range(len(query_words) - 1):
            phrase = f"{query_words[i]} {query_words[i+1]}"
            if phrase in content_lower:
                phrase_bonus += 0.05
    
    # Ensure final score doesn't exceed 1.0
    final_score = min(1.0, base_score + phrase_bonus)
    return final_score

def is_semantic_search_available() -> bool:
    """
    Check if semantic search is available.
    
    Returns:
        True if sentence-transformers is loaded, False otherwise
    """
    return get_embedding_model() is not None

def get_search_mode() -> str:
    """
    Get current search mode for debugging/monitoring.
    
    Returns:
        "semantic" if embeddings available, "keyword" if fallback
    """
    return "semantic" if is_semantic_search_available() else "keyword"