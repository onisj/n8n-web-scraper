"""
Vector Database Implementation

Provides vector database functionality using ChromaDB for the n8n AI Knowledge System
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import numpy as np
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorDatabase:
    """Vector database implementation using ChromaDB"""
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "n8n_knowledge",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize vector database
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
            embedding_model: Embedding model to use
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Vector database initialized with {self.collection.count()} documents")
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            return self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
        except Exception:
            return self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
    
    def initialize(self):
        """Initialize the vector database (for backward compatibility)"""
        # Already initialized in __init__, but keeping for compatibility
        pass
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add documents to the vector database
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: Optional list of document IDs
            
        Returns:
            bool: Success status
        """
        try:
            if not documents:
                logger.warning("No documents provided to add")
                return False
            
            # Generate IDs if not provided
            if ids is None:
                ids = [f"doc_{i}_{datetime.now().timestamp()}" for i in range(len(documents))]
            
            # Ensure all metadata has required fields
            processed_metadatas = []
            for metadata in metadatas:
                processed_metadata = metadata.copy()
                processed_metadata.setdefault("timestamp", datetime.now().isoformat())
                processed_metadata.setdefault("source", "unknown")
                processed_metadatas.append(processed_metadata)
            
            # Add documents to collection
            self.collection.add(
                documents=documents,
                metadatas=processed_metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            return False
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: List[str] = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            n_results: Number of results to return
            where: Metadata filter conditions
            include: Fields to include in results
            
        Returns:
            Dict containing search results
        """
        try:
            if include is None:
                include = ["documents", "metadatas", "distances"]
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=include
            )
            
            # Format results for backward compatibility and enhanced functionality
            if hasattr(results, 'get') and 'ids' in results:
                # New format
                formatted_results = {
                    "query": query,
                    "total_results": len(results["ids"][0]) if results["ids"] else 0,
                    "results": []
                }
                
                if results["ids"] and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        result = {
                            "id": results["ids"][0][i],
                            "score": 1 - results["distances"][0][i] if "distances" in results else None,
                            "distance": results["distances"][0][i] if "distances" in results else None
                        }
                        
                        if "documents" in include and "documents" in results:
                            result["content"] = results["documents"][0][i]
                        
                        if "metadatas" in include and "metadatas" in results:
                            result["metadata"] = results["metadatas"][0][i]
                        
                        formatted_results["results"].append(result)
                
                return formatted_results
            else:
                # Return raw results for backward compatibility
                return results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return {"query": query, "total_results": 0, "results": [], "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics (backward compatibility)"""
        return self.get_collection_stats()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics
        
        Returns:
            Dict containing collection stats
        """
        try:
            count = self.collection.count()
            
            # Get sample of metadata to analyze
            sample_results = self.collection.get(
                limit=min(100, count),
                include=["metadatas"]
            )
            
            # Analyze metadata
            sources = set()
            categories = set()
            
            if sample_results["metadatas"]:
                for metadata in sample_results["metadatas"]:
                    if "source" in metadata:
                        sources.add(metadata["source"])
                    if "category" in metadata:
                        categories.add(metadata["category"])
            
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
                "unique_sources": len(sources),
                "unique_categories": len(categories),
                "sources": list(sources),
                "categories": list(categories)
            }
            
        except Exception as e:
             logger.error(f"Error getting collection stats: {e}")
             return {"error": str(e)}
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results["ids"] and results["ids"][0]:
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0] if results["documents"] else None,
                    "metadata": results["metadatas"][0] if results["metadatas"] else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    def update_document(
        self,
        doc_id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing document
        
        Args:
            doc_id: Document ID
            document: New document content
            metadata: New metadata
            
        Returns:
            bool: Success status
        """
        try:
            update_data = {"ids": [doc_id]}
            
            if document is not None:
                update_data["documents"] = [document]
            
            if metadata is not None:
                metadata["updated_at"] = datetime.now().isoformat()
                update_data["metadatas"] = [metadata]
            
            self.collection.update(**update_data)
            logger.info(f"Updated document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document
        
        Args:
            doc_id: Document ID
            
        Returns:
            bool: Success status
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def delete_documents(self, where: Dict[str, Any]) -> bool:
        """
        Delete documents matching criteria
        
        Args:
            where: Metadata filter conditions
            
        Returns:
            bool: Success status
        """
        try:
            self.collection.delete(where=where)
            logger.info(f"Deleted documents matching criteria: {where}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False
    
    def reset_collection(self) -> bool:
        """
        Reset the collection (delete all documents)
        
        Returns:
            bool: Success status
        """
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Collection reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return False
    
    def backup_collection(self, backup_path: str) -> bool:
        """
        Backup collection data
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            bool: Success status
        """
        try:
            # Get all documents
            all_docs = self.collection.get(
                include=["documents", "metadatas"]
            )
            
            backup_data = {
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
                "timestamp": datetime.now().isoformat(),
                "documents": all_docs
            }
            
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Collection backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up collection: {e}")
            return False
    
    def restore_collection(self, backup_path: str) -> bool:
        """
        Restore collection from backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            bool: Success status
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Reset collection
            self.reset_collection()
            
            # Restore documents
            docs_data = backup_data["documents"]
            if docs_data["ids"]:
                self.collection.add(
                    ids=docs_data["ids"],
                    documents=docs_data["documents"],
                    metadatas=docs_data["metadatas"]
                )
            
            logger.info(f"Collection restored from {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring collection: {e}")
            return False
