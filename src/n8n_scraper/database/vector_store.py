"""
Vector store implementation for semantic search.
"""

import asyncio
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from config.settings import settings
from ..core.exceptions import VectorDatabaseError, AIProviderError
from ..core.logging_config import get_logger
from ..core.metrics import metrics

logger = get_logger(__name__)


class VectorStore:
    """Vector store for semantic search using embeddings."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.embedding_model
        self.vector_db_path = settings.vector_db_path
        self.dimension = settings.embedding_dimension
        self._model: Optional[SentenceTransformer] = None
        self._index = None
        self._metadata: Dict[str, Any] = {}
        self._is_initialized = False
        
        # Ensure vector database directory exists
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize the vector store."""
        if self._is_initialized:
            return
        
        try:
            # Load embedding model
            await self._load_embedding_model()
            
            # Initialize vector index
            await self._initialize_index()
            
            # Load metadata
            await self._load_metadata()
            
            self._is_initialized = True
            logger.info(f"Vector store initialized with model: {self.model_name}")
            
            # Update metrics
            metrics.increment_counter("vector_store_initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            metrics.increment_counter("vector_store_initialization_errors")
            raise VectorDatabaseError(f"Failed to initialize vector store: {str(e)}") from e
    
    async def _load_embedding_model(self) -> None:
        """Load the sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence_transformers not available, vector operations will be disabled")
            self._model = None
            return
            
        try:
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(self.model_name)
            )
            
            # Update dimension based on model
            if hasattr(self._model, 'get_sentence_embedding_dimension'):
                self.dimension = self._model.get_sentence_embedding_dimension()
            
            logger.info(f"Loaded embedding model: {self.model_name} (dimension: {self.dimension})")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise AIProviderError(f"Failed to load embedding model: {str(e)}") from e
    
    async def _initialize_index(self) -> None:
        """Initialize the vector index."""
        try:
            # Try to import faiss for efficient similarity search
            try:
                import faiss
                
                index_path = self.vector_db_path / "faiss_index.bin"
                
                if index_path.exists():
                    # Load existing index
                    self._index = faiss.read_index(str(index_path))
                    logger.info(f"Loaded existing FAISS index with {self._index.ntotal} vectors")
                else:
                    # Create new index
                    self._index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                    logger.info("Created new FAISS index")
                
            except ImportError:
                logger.warning("FAISS not available, using simple numpy-based search")
                # Fallback to simple numpy-based storage
                self._index = {
                    "vectors": [],
                    "ids": [],
                    "metadata": []
                }
                
                # Try to load existing vectors
                vectors_path = self.vector_db_path / "vectors.npy"
                ids_path = self.vector_db_path / "ids.json"
                metadata_path = self.vector_db_path / "vector_metadata.json"
                
                if vectors_path.exists() and ids_path.exists():
                    self._index["vectors"] = np.load(vectors_path).tolist()
                    
                    with open(ids_path, 'r') as f:
                        self._index["ids"] = json.load(f)
                    
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            self._index["metadata"] = json.load(f)
                    
                    logger.info(f"Loaded {len(self._index['vectors'])} vectors from numpy files")
        
        except Exception as e:
            logger.error(f"Failed to initialize vector index: {e}")
            raise VectorDatabaseError(f"Failed to initialize vector index: {str(e)}") from e
    
    async def _load_metadata(self) -> None:
        """Load vector store metadata."""
        metadata_path = self.vector_db_path / "store_metadata.json"
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")
                self._metadata = {}
        else:
            self._metadata = {
                "model_name": self.model_name,
                "dimension": self.dimension,
                "created_at": None,
                "last_updated": None,
                "total_vectors": 0,
            }
    
    async def _save_metadata(self) -> None:
        """Save vector store metadata."""
        metadata_path = self.vector_db_path / "store_metadata.json"
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(self._metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    async def add_documents(
        self,
        documents: List[str],
        document_ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Add documents to the vector store.
        
        Args:
            documents: List of document texts
            document_ids: List of unique document IDs
            metadata: Optional list of metadata dictionaries
        """
        if not self._is_initialized:
            await self.initialize()
        
        if len(documents) != len(document_ids):
            raise ValueError("Number of documents must match number of document IDs")
        
        if metadata and len(metadata) != len(documents):
            raise ValueError("Number of metadata entries must match number of documents")
        
        try:
            # Generate embeddings
            embeddings = await self._generate_embeddings(documents)
            
            # Add to index
            await self._add_to_index(embeddings, document_ids, metadata or [])
            
            # Update metadata
            self._metadata["total_vectors"] = await self.get_vector_count()
            self._metadata["last_updated"] = str(asyncio.get_event_loop().time())
            await self._save_metadata()
            
            logger.info(f"Added {len(documents)} documents to vector store")
            metrics.increment_counter("vector_store_documents_added", len(documents))
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}")
            metrics.increment_counter("vector_store_add_errors")
            raise VectorDatabaseError(f"Failed to add documents: {str(e)}") from e
    
    async def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise VectorDatabaseError("sentence_transformers not available - cannot generate embeddings")
            
        if not self._model:
            raise VectorDatabaseError("Embedding model not loaded")
        
        try:
            # Generate embeddings in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise AIProviderError(f"Failed to generate embeddings: {str(e)}") from e
    
    async def _add_to_index(
        self,
        embeddings: np.ndarray,
        document_ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        """Add embeddings to the index."""
        try:
            if hasattr(self._index, 'add'):  # FAISS index
                # Add vectors to FAISS index
                self._index.add(embeddings.astype(np.float32))
                
                # Save FAISS index
                index_path = self.vector_db_path / "faiss_index.bin"
                import faiss
                faiss.write_index(self._index, str(index_path))
                
                # Save document IDs and metadata separately
                ids_path = self.vector_db_path / "document_ids.json"
                metadata_path = self.vector_db_path / "document_metadata.json"
                
                # Load existing data
                existing_ids = []
                existing_metadata = []
                
                if ids_path.exists():
                    with open(ids_path, 'r') as f:
                        existing_ids = json.load(f)
                
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        existing_metadata = json.load(f)
                
                # Append new data
                existing_ids.extend(document_ids)
                existing_metadata.extend(metadata)
                
                # Save updated data
                with open(ids_path, 'w') as f:
                    json.dump(existing_ids, f)
                
                with open(metadata_path, 'w') as f:
                    json.dump(existing_metadata, f, default=str)
                
            else:  # Numpy-based index
                # Add to numpy arrays
                self._index["vectors"].extend(embeddings.tolist())
                self._index["ids"].extend(document_ids)
                self._index["metadata"].extend(metadata)
                
                # Save to files
                vectors_path = self.vector_db_path / "vectors.npy"
                ids_path = self.vector_db_path / "ids.json"
                metadata_path = self.vector_db_path / "vector_metadata.json"
                
                np.save(vectors_path, np.array(self._index["vectors"]))
                
                with open(ids_path, 'w') as f:
                    json.dump(self._index["ids"], f)
                
                with open(metadata_path, 'w') as f:
                    json.dump(self._index["metadata"], f, default=str)
        
        except Exception as e:
            logger.error(f"Failed to add to index: {e}")
            raise VectorDatabaseError(f"Failed to add to index: {str(e)}") from e
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            threshold: Minimum similarity threshold
        
        Returns:
            List of search results with scores and metadata
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            query_vector = query_embedding[0]
            
            # Search index
            results = await self._search_index(query_vector, limit, threshold)
            
            logger.info(f"Vector search returned {len(results)} results for query")
            metrics.increment_counter("vector_store_searches")
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            metrics.increment_counter("vector_store_search_errors")
            raise VectorDatabaseError(f"Vector search failed: {str(e)}") from e
    
    async def _search_index(
        self,
        query_vector: np.ndarray,
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search the vector index."""
        try:
            if hasattr(self._index, 'search'):  # FAISS index
                # Search FAISS index
                scores, indices = self._index.search(
                    query_vector.reshape(1, -1).astype(np.float32),
                    limit
                )
                
                # Load document IDs and metadata
                ids_path = self.vector_db_path / "document_ids.json"
                metadata_path = self.vector_db_path / "document_metadata.json"
                
                document_ids = []
                document_metadata = []
                
                if ids_path.exists():
                    with open(ids_path, 'r') as f:
                        document_ids = json.load(f)
                
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        document_metadata = json.load(f)
                
                # Build results
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if score >= threshold and idx < len(document_ids):
                        result = {
                            "document_id": document_ids[idx],
                            "score": float(score),
                            "rank": i + 1,
                            "metadata": document_metadata[idx] if idx < len(document_metadata) else {}
                        }
                        results.append(result)
                
                return results
            
            else:  # Numpy-based index
                if not self._index["vectors"]:
                    return []
                
                # Calculate similarities
                vectors = np.array(self._index["vectors"])
                similarities = np.dot(vectors, query_vector)
                
                # Get top results
                top_indices = np.argsort(similarities)[::-1][:limit]
                
                results = []
                for i, idx in enumerate(top_indices):
                    score = similarities[idx]
                    if score >= threshold:
                        result = {
                            "document_id": self._index["ids"][idx],
                            "score": float(score),
                            "rank": i + 1,
                            "metadata": self._index["metadata"][idx] if idx < len(self._index["metadata"]) else {}
                        }
                        results.append(result)
                
                return results
        
        except Exception as e:
            logger.error(f"Index search failed: {e}")
            raise VectorDatabaseError(f"Index search failed: {str(e)}") from e
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store.
        
        Args:
            document_id: ID of the document to delete
        
        Returns:
            True if document was deleted, False if not found
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            if hasattr(self._index, 'remove_ids'):  # FAISS index with ID mapping
                # This would require a more complex implementation with ID mapping
                logger.warning("Document deletion not fully implemented for FAISS index")
                return False
            
            else:  # Numpy-based index
                if document_id in self._index["ids"]:
                    idx = self._index["ids"].index(document_id)
                    
                    # Remove from all arrays
                    del self._index["vectors"][idx]
                    del self._index["ids"][idx]
                    if idx < len(self._index["metadata"]):
                        del self._index["metadata"][idx]
                    
                    # Save updated data
                    await self._save_numpy_index()
                    
                    logger.info(f"Deleted document {document_id} from vector store")
                    metrics.increment_counter("vector_store_documents_deleted")
                    return True
                
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            metrics.increment_counter("vector_store_delete_errors")
            raise VectorDatabaseError(f"Failed to delete document: {str(e)}") from e
    
    async def _save_numpy_index(self) -> None:
        """Save numpy-based index to files."""
        try:
            vectors_path = self.vector_db_path / "vectors.npy"
            ids_path = self.vector_db_path / "ids.json"
            metadata_path = self.vector_db_path / "vector_metadata.json"
            
            if self._index["vectors"]:
                np.save(vectors_path, np.array(self._index["vectors"]))
            
            with open(ids_path, 'w') as f:
                json.dump(self._index["ids"], f)
            
            with open(metadata_path, 'w') as f:
                json.dump(self._index["metadata"], f, default=str)
        
        except Exception as e:
            logger.error(f"Failed to save numpy index: {e}")
            raise VectorDatabaseError(f"Failed to save numpy index: {str(e)}") from e
    
    async def get_vector_count(self) -> int:
        """Get the total number of vectors in the store."""
        if not self._is_initialized:
            await self.initialize()
        
        try:
            if hasattr(self._index, 'ntotal'):  # FAISS index
                return self._index.ntotal
            else:  # Numpy-based index
                return len(self._index["vectors"])
        
        except Exception as e:
            logger.error(f"Failed to get vector count: {e}")
            return 0
    
    async def get_collection_count(self) -> int:
        """Get the number of collections (for compatibility)."""
        # For this implementation, we have one collection
        return 1 if await self.get_vector_count() > 0 else 0
    
    async def clear(self) -> None:
        """Clear all vectors from the store."""
        if not self._is_initialized:
            await self.initialize()
        
        try:
            if hasattr(self._index, 'reset'):  # FAISS index
                self._index.reset()
                
                # Clear associated files
                for file_path in [
                    self.vector_db_path / "faiss_index.bin",
                    self.vector_db_path / "document_ids.json",
                    self.vector_db_path / "document_metadata.json"
                ]:
                    if file_path.exists():
                        file_path.unlink()
            
            else:  # Numpy-based index
                self._index = {
                    "vectors": [],
                    "ids": [],
                    "metadata": []
                }
                
                # Clear files
                for file_path in [
                    self.vector_db_path / "vectors.npy",
                    self.vector_db_path / "ids.json",
                    self.vector_db_path / "vector_metadata.json"
                ]:
                    if file_path.exists():
                        file_path.unlink()
            
            # Update metadata
            self._metadata["total_vectors"] = 0
            self._metadata["last_updated"] = str(asyncio.get_event_loop().time())
            await self._save_metadata()
            
            logger.info("Cleared all vectors from vector store")
            metrics.increment_counter("vector_store_cleared")
        
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            raise VectorDatabaseError(f"Failed to clear vector store: {str(e)}") from e
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        try:
            vector_count = await self.get_vector_count()
            
            stats = {
                "model_name": self.model_name,
                "dimension": self.dimension,
                "total_vectors": vector_count,
                "index_type": "faiss" if hasattr(self._index, 'ntotal') else "numpy",
                "is_initialized": self._is_initialized,
                "metadata": self._metadata,
            }
            
            # Add index-specific stats
            if hasattr(self._index, 'ntotal'):  # FAISS
                stats["faiss_stats"] = {
                    "ntotal": self._index.ntotal,
                    "d": self._index.d,
                    "is_trained": self._index.is_trained,
                }
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {"error": str(e)}
    
    async def close(self) -> None:
        """Close the vector store and cleanup resources."""
        try:
            # Save any pending changes
            if self._metadata:
                await self._save_metadata()
            
            # Clear references
            self._model = None
            self._index = None
            self._is_initialized = False
            
            logger.info("Vector store closed")
        
        except Exception as e:
            logger.error(f"Error closing vector store: {e}")