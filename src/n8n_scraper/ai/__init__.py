"""AI module for n8n scraper.

This module contains AI-related functionality including:
- Embedding generation for semantic search
- Text processing and analysis
- Vector similarity computations
"""

from .embeddings import EmbeddingService, get_embedding_service

__all__ = [
    'EmbeddingService',
    'get_embedding_service'
]