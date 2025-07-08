#!/usr/bin/env python3
"""
Knowledge Vector Integration

Integrates scraped n8n documentation with vector database for fast chunking,
embedding generation, and semantic retrieval. This module provides the bridge
between raw scraped data and the AI-powered knowledge system.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib

from ..agents.knowledge_processor import N8nKnowledgeProcessor, KnowledgeChunk
from ..database.vector_db import VectorDatabase
from ..core.exceptions import VectorDatabaseError, ProcessingError
from ..core.config import load_config

logger = logging.getLogger(__name__)

class KnowledgeVectorIntegration:
    """
    Manages the integration between scraped knowledge and vector database.
    
    This class handles:
    - Processing scraped JSON files into knowledge chunks
    - Generating embeddings for semantic search
    - Storing chunks in vector database with metadata
    - Incremental updates and deduplication
    - Fast retrieval and chunking strategies
    """
    
    def __init__(
        self,
        scraped_data_dir: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs",
        vector_db_dir: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector",
        collection_name: str = "n8n_knowledge",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize the knowledge vector integration.
        
        Args:
            scraped_data_dir: Directory containing scraped JSON files
            vector_db_dir: Directory for vector database storage
            collection_name: Name of the vector database collection
            chunk_size: Maximum size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.scraped_data_dir = Path(scraped_data_dir)
        self.vector_db_dir = Path(vector_db_dir)
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize components
        self.knowledge_processor = N8nKnowledgeProcessor(str(self.scraped_data_dir))
        self.vector_db = VectorDatabase(
            persist_directory=str(self.vector_db_dir),
            collection_name=collection_name
        )
        
        # Track processed files for incremental updates
        self.processed_files_cache = self._load_processed_files_cache()
        
        logger.info(f"Knowledge vector integration initialized")
        logger.info(f"Scraped data: {self.scraped_data_dir}")
        logger.info(f"Vector DB: {self.vector_db_dir}")
    
    def process_and_store_all(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Process all scraped files and store in vector database.
        
        Args:
            force_refresh: If True, reprocess all files regardless of cache
            
        Returns:
            Dict containing processing statistics
        """
        start_time = datetime.now()
        logger.info("Starting full knowledge processing and vector storage")
        
        try:
            # Get list of files to process
            files_to_process = self._get_files_to_process(force_refresh)
            
            if not files_to_process:
                logger.info("No new files to process")
                return self._get_processing_stats(start_time, 0, 0)
            
            logger.info(f"Processing {len(files_to_process)} files")
            
            total_chunks = 0
            processed_files = 0
            
            # Process files in batches for memory efficiency
            batch_size = 10
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i + batch_size]
                batch_chunks = self._process_file_batch(batch)
                
                if batch_chunks:
                    # Store chunks in vector database
                    success = self._store_chunks_in_vector_db(batch_chunks)
                    if success:
                        total_chunks += len(batch_chunks)
                        processed_files += len(batch)
                        
                        # Update cache
                        for file_path in batch:
                            self._update_processed_file_cache(file_path)
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(files_to_process) + batch_size - 1)//batch_size}")
            
            # Save updated cache
            self._save_processed_files_cache()
            
            stats = self._get_processing_stats(start_time, processed_files, total_chunks)
            logger.info(f"Processing complete: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            raise ProcessingError(f"Failed to process and store knowledge: {e}")
    
    def process_incremental_update(self) -> Dict[str, Any]:
        """
        Process only new or modified files since last update.
        
        Returns:
            Dict containing processing statistics
        """
        return self.process_and_store_all(force_refresh=False)
    
    def search_knowledge(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.7,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            category_filter: Optional category to filter by
            
        Returns:
            List of relevant knowledge chunks with metadata
        """
        try:
            # Build metadata filter
            where_filter = {}
            if category_filter:
                where_filter["category"] = category_filter
            
            # Search vector database
            results = self.vector_db.search(
                query=query,
                n_results=top_k,
                where=where_filter if where_filter else None
            )
            
            # Filter by score threshold and format results
            filtered_results = []
            if "results" in results:
                for result in results["results"]:
                    if result.get("score", 0) >= score_threshold:
                        filtered_results.append({
                            "content": result.get("content", ""),
                            "metadata": result.get("metadata", {}),
                            "score": result.get("score", 0),
                            "chunk_id": result.get("id", "")
                        })
            
            logger.info(f"Search returned {len(filtered_results)} results for query: {query[:50]}...")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the knowledge base.
        
        Returns:
            Dict containing various statistics
        """
        try:
            # Vector database stats
            vector_stats = self.vector_db.get_collection_stats()
            
            # File processing stats
            total_files = len(list(self.scraped_data_dir.glob("*.json")))
            processed_files = len(self.processed_files_cache)
            
            return {
                "vector_database": vector_stats,
                "file_processing": {
                    "total_scraped_files": total_files,
                    "processed_files": processed_files,
                    "pending_files": total_files - processed_files,
                    "last_update": self._get_last_update_time()
                },
                "chunking": {
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge stats: {e}")
            return {"error": str(e)}
    
    def _get_files_to_process(self, force_refresh: bool) -> List[Path]:
        """
        Get list of files that need processing.
        
        Args:
            force_refresh: If True, return all files
            
        Returns:
            List of file paths to process
        """
        all_files = list(self.scraped_data_dir.glob("*.json"))
        
        if force_refresh:
            return all_files
        
        # Return only new or modified files
        files_to_process = []
        for file_path in all_files:
            file_key = str(file_path.relative_to(self.scraped_data_dir))
            file_mtime = file_path.stat().st_mtime
            
            if (file_key not in self.processed_files_cache or 
                self.processed_files_cache[file_key]["mtime"] < file_mtime):
                files_to_process.append(file_path)
        
        return files_to_process
    
    def _process_file_batch(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Process a batch of files into knowledge chunks.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of processed chunks ready for vector storage
        """
        chunks = []
        
        for file_path in file_paths:
            try:
                # Load and process file
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Create knowledge chunk
                chunk = self._create_enhanced_chunk(data, file_path)
                if chunk:
                    # Split into smaller chunks if needed
                    sub_chunks = self._split_chunk_if_needed(chunk)
                    chunks.extend(sub_chunks)
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
        
        return chunks
    
    def _create_enhanced_chunk(self, data: Dict, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Create an enhanced knowledge chunk with additional metadata.
        
        Args:
            data: Raw scraped data
            file_path: Path to the source file
            
        Returns:
            Enhanced chunk dictionary or None if invalid
        """
        try:
            # Extract basic information
            title = data.get('title', 'Untitled')
            content = data.get('content', '')
            url = data.get('url', '')
            
            # Skip if no meaningful content
            if not content or len(content.strip()) < 50:
                return None
            
            # Extract category from filename
            filename = file_path.stem
            category, subcategory = self.knowledge_processor._extract_categories(filename)
            
            # Generate unique ID
            chunk_id = self._generate_chunk_id(url, title, content, filename)
            
            # Enhanced metadata
            metadata = {
                "title": title,
                "url": url,
                "category": category,
                "subcategory": subcategory,
                "source_file": filename,
                "word_count": len(content.split()),
                "char_count": len(content),
                "scraped_at": data.get('scraped_at', ''),
                "processed_at": datetime.now().isoformat(),
                "has_code": bool(data.get('code_blocks')),
                "has_images": bool(data.get('images')),
                "headings_count": len(data.get('headings', [])),
                "links_count": len(data.get('links', []))
            }
            
            return {
                "id": chunk_id,
                "content": self._clean_content(content),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error creating chunk for {file_path}: {e}")
            return None
    
    def _split_chunk_if_needed(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split large chunks into smaller ones for better retrieval.
        
        Args:
            chunk: Original chunk
            
        Returns:
            List of chunks (original or split)
        """
        content = chunk["content"]
        
        if len(content) <= self.chunk_size:
            return [chunk]
        
        # Split content into smaller chunks
        chunks = []
        start = 0
        chunk_num = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence endings near the split point
                for i in range(end, max(start + self.chunk_size - 100, start), -1):
                    if content[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk_content = content[start:end].strip()
            
            if chunk_content:
                # Create sub-chunk
                sub_chunk = {
                    "id": f"{chunk['id']}_part_{chunk_num}",
                    "content": chunk_content,
                    "metadata": chunk["metadata"].copy()
                }
                
                # Add chunk-specific metadata
                sub_chunk["metadata"]["is_split_chunk"] = True
                sub_chunk["metadata"]["parent_chunk_id"] = chunk["id"]
                sub_chunk["metadata"]["chunk_part"] = chunk_num
                sub_chunk["metadata"]["chunk_char_count"] = len(chunk_content)
                
                chunks.append(sub_chunk)
                chunk_num += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(content):
                break
        
        logger.debug(f"Split chunk {chunk['id']} into {len(chunks)} parts")
        return chunks
    
    def _store_chunks_in_vector_db(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Store processed chunks in the vector database.
        
        Args:
            chunks: List of chunks to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not chunks:
                return True
            
            # Prepare data for vector database
            documents = [chunk["content"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            ids = [chunk["id"] for chunk in chunks]
            
            # Store in vector database
            success = self.vector_db.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            if success:
                logger.info(f"Successfully stored {len(chunks)} chunks in vector database")
            else:
                logger.error(f"Failed to store {len(chunks)} chunks in vector database")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing chunks in vector database: {e}")
            return False
    
    def _clean_content(self, content: str) -> str:
        """
        Clean and normalize content text.
        
        Args:
            content: Raw content text
            
        Returns:
            Cleaned content
        """
        # Use the knowledge processor's cleaning method
        return self.knowledge_processor._clean_content(content)
    
    def _generate_chunk_id(self, url: str, title: str, content: str, filename: str) -> str:
        """
        Generate a unique ID for a chunk.
        
        Args:
            url: Source URL
            title: Content title
            content: Content text
            filename: Source filename
            
        Returns:
            Unique chunk ID
        """
        # Create hash from multiple components for uniqueness
        hash_input = f"{url}:{title}:{filename}:{content[:100]}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"chunk_{filename}_{hash_value}"
    
    def _load_processed_files_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cache of processed files.
        
        Returns:
            Dictionary mapping file paths to processing metadata
        """
        cache_file = self.vector_db_dir / "processed_files_cache.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading processed files cache: {e}")
        
        return {}
    
    def _save_processed_files_cache(self):
        """
        Save cache of processed files.
        """
        cache_file = self.vector_db_dir / "processed_files_cache.json"
        
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(self.processed_files_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed files cache: {e}")
    
    def _update_processed_file_cache(self, file_path: Path):
        """
        Update cache entry for a processed file.
        
        Args:
            file_path: Path to the processed file
        """
        file_key = str(file_path.relative_to(self.scraped_data_dir))
        self.processed_files_cache[file_key] = {
            "mtime": file_path.stat().st_mtime,
            "processed_at": datetime.now().isoformat()
        }
    
    def _get_last_update_time(self) -> str:
        """
        Get the timestamp of the last processing update.
        
        Returns:
            ISO format timestamp or 'Never'
        """
        if not self.processed_files_cache:
            return "Never"
        
        latest_time = max(
            entry["processed_at"] 
            for entry in self.processed_files_cache.values()
            if "processed_at" in entry
        )
        
        return latest_time
    
    def _get_processing_stats(self, start_time: datetime, processed_files: int, total_chunks: int) -> Dict[str, Any]:
        """
        Generate processing statistics.
        
        Args:
            start_time: Processing start time
            processed_files: Number of files processed
            total_chunks: Number of chunks created
            
        Returns:
            Statistics dictionary
        """
        duration = datetime.now() - start_time
        
        return {
            "processed_files": processed_files,
            "total_chunks": total_chunks,
            "duration_seconds": duration.total_seconds(),
            "chunks_per_file": total_chunks / max(processed_files, 1),
            "processing_rate": processed_files / max(duration.total_seconds(), 1),
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }


# Convenience functions for easy integration

def create_knowledge_integration(
    scraped_data_dir: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs",
    vector_db_dir: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector"
) -> KnowledgeVectorIntegration:
    """
    Create a knowledge vector integration instance.
    
    Args:
        scraped_data_dir: Directory containing scraped data
        vector_db_dir: Directory for vector database
        
    Returns:
        KnowledgeVectorIntegration instance
    """
    return KnowledgeVectorIntegration(
        scraped_data_dir=scraped_data_dir,
        vector_db_dir=vector_db_dir
    )


async def process_knowledge_async(
    integration: KnowledgeVectorIntegration,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Asynchronously process knowledge and store in vector database.
    
    Args:
        integration: KnowledgeVectorIntegration instance
        force_refresh: Whether to force refresh all data
        
    Returns:
        Processing statistics
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        integration.process_and_store_all,
        force_refresh
    )


if __name__ == "__main__":
    # Example usage
    integration = create_knowledge_integration()
    
    # Process all scraped data
    stats = integration.process_and_store_all(force_refresh=True)
    print(f"Processing complete: {stats}")
    
    # Search example
    results = integration.search_knowledge("workflow automation", top_k=5)
    print(f"Found {len(results)} relevant chunks")
    
    # Get statistics
    knowledge_stats = integration.get_knowledge_stats()
    print(f"Knowledge base stats: {knowledge_stats}")