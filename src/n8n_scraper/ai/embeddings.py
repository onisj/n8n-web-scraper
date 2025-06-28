"""Embedding service for generating vector embeddings from text.

This module provides functionality to generate embeddings using various models
for semantic search and similarity matching.
"""

import os
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import numpy as np
from sentence_transformers import SentenceTransformer

from ..core.logging_config import get_logger
# from ..database.connection import get_redis_client  # Redis not available yet

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_ttl: int = 86400):
        """Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence transformer model to use
            cache_ttl: Cache TTL in seconds (default: 24 hours)
        """
        self.model_name = model_name
        self.cache_ttl = cache_ttl
        self._model = None
        self._redis_client = None
        
        # Initialize model
        self._load_model()
        
        # Initialize cache
        try:
            # self._redis_client = get_redis_client()  # Redis not available yet
            self._redis_client = None
            logger.info("Redis cache disabled for embeddings (not implemented yet)")
        except Exception as e:
            logger.warning(f"Redis cache not available for embeddings: {e}")
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text.
        
        Args:
            text: Input text
            
        Returns:
            Cache key
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"embedding:{self.model_name}:{text_hash}"
    
    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if available.
        
        Args:
            text: Input text
            
        Returns:
            Cached embedding or None
        """
        if not self._redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(text)
            cached_data = self._redis_client.get(cache_key)
            
            if cached_data:
                # Deserialize numpy array
                embedding_bytes = cached_data
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                return embedding.tolist()
                
        except Exception as e:
            logger.warning(f"Error retrieving cached embedding: {e}")
        
        return None
    
    def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding.
        
        Args:
            text: Input text
            embedding: Generated embedding
        """
        if not self._redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(text)
            
            # Serialize numpy array
            embedding_array = np.array(embedding, dtype=np.float32)
            embedding_bytes = embedding_array.tobytes()
            
            self._redis_client.setex(
                cache_key,
                self.cache_ttl,
                embedding_bytes
            )
            
        except Exception as e:
            logger.warning(f"Error caching embedding: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Check cache first
        cached_embedding = self._get_cached_embedding(text)
        if cached_embedding is not None:
            return cached_embedding
        
        # Generate new embedding
        try:
            # Truncate text if too long (model limit is usually 512 tokens)
            if len(text) > 2000:  # Rough token estimate
                text = text[:2000] + "..."
            
            embedding = self._model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            # Cache the result
            self._cache_embedding(text, embedding_list)
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Check cache for each text
            batch_embeddings = []
            uncached_indices = []
            uncached_texts = []
            
            for j, text in enumerate(batch_texts):
                cached_embedding = self._get_cached_embedding(text)
                if cached_embedding is not None:
                    batch_embeddings.append(cached_embedding)
                else:
                    batch_embeddings.append(None)
                    uncached_indices.append(j)
                    uncached_texts.append(text)
            
            # Generate embeddings for uncached texts
            if uncached_texts:
                try:
                    # Truncate long texts
                    processed_texts = []
                    for text in uncached_texts:
                        if len(text) > 2000:
                            text = text[:2000] + "..."
                        processed_texts.append(text)
                    
                    new_embeddings = self._model.encode(processed_texts, convert_to_tensor=False)
                    
                    # Insert new embeddings and cache them
                    for idx, embedding in zip(uncached_indices, new_embeddings):
                        embedding_list = embedding.tolist()
                        batch_embeddings[idx] = embedding_list
                        
                        # Cache the result
                        self._cache_embedding(uncached_texts[uncached_indices.index(idx)], embedding_list)
                        
                except Exception as e:
                    logger.error(f"Error generating batch embeddings: {e}")
                    # Fill with empty embeddings for failed texts
                    for idx in uncached_indices:
                        if batch_embeddings[idx] is None:
                            batch_embeddings[idx] = [0.0] * self.get_embedding_dimension()
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        if not self._model:
            self._load_model()
        
        return self._model.get_sentence_embedding_dimension()
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score (-1 to 1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Compute cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]], 
                         top_k: int = 5) -> List[tuple]:
        """Find most similar embeddings to query.
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: List of candidate embeddings
            top_k: Number of top results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(query_embedding, candidate)
            similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def clear_cache(self):
        """Clear embedding cache."""
        if not self._redis_client:
            logger.warning("No Redis client available for cache clearing")
            return
        
        try:
            # Find all embedding cache keys
            pattern = f"embedding:{self.model_name}:*"
            keys = self._redis_client.keys(pattern)
            
            if keys:
                self._redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} embedding cache entries")
            else:
                logger.info("No embedding cache entries to clear")
                
        except Exception as e:
            logger.error(f"Error clearing embedding cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        if not self._redis_client:
            return {"cache_available": False}
        
        try:
            pattern = f"embedding:{self.model_name}:*"
            keys = self._redis_client.keys(pattern)
            
            return {
                "cache_available": True,
                "cached_embeddings": len(keys),
                "model_name": self.model_name,
                "cache_ttl": self.cache_ttl
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"cache_available": False, "error": str(e)}


# Global embedding service instance
_embedding_service = None


def get_embedding_service(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingService:
    """Get global embedding service instance.
    
    Args:
        model_name: Model name to use
        
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    
    if _embedding_service is None or _embedding_service.model_name != model_name:
        _embedding_service = EmbeddingService(model_name)
    
    return _embedding_service