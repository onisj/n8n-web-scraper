#!/usr/bin/env python3
"""
Knowledge Base Cache and Optimization

Provides caching, parallel processing, and singleton management
for the n8n knowledge base to dramatically improve startup performance.
"""

import json
import os
import pickle
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

from n8n_scraper.agents.knowledge_processor import KnowledgeChunk, ProcessedKnowledge

logger = logging.getLogger(__name__)

@dataclass
class CacheMetadata:
    """Metadata for cache validation"""
    created_at: datetime
    file_count: int
    total_size: int
    checksum: str
    version: str = "1.0"

class KnowledgeCache:
    """High-performance knowledge base cache with parallel processing"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to prevent multiple instances"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, data_directory: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs", cache_dir: str = "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/cache"):
        if hasattr(self, '_initialized'):
            return
            
        self.data_directory = Path(data_directory)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.cache_file = self.cache_dir / "knowledge_cache.pkl"
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        
        self._knowledge_base = None
        self._cache_valid = False
        self._initialized = True
        
        logger.info(f"Knowledge cache initialized: {self.cache_dir}")
    
    def get_knowledge_base(self, force_refresh: bool = False) -> Optional[ProcessedKnowledge]:
        """Get knowledge base with intelligent caching"""
        if not force_refresh and self._knowledge_base and self._cache_valid:
            logger.info("Returning cached knowledge base")
            return self._knowledge_base
        
        # Check if we can load from cache
        if not force_refresh and self._should_use_cache():
            logger.info("Loading knowledge base from cache")
            cached_kb = self._load_from_cache()
            if cached_kb:
                self._knowledge_base = cached_kb
                self._cache_valid = True
                return cached_kb
        
        # Process files with optimization
        logger.info("Processing knowledge base with optimizations")
        processed_kb = self._process_with_optimization()
        
        if processed_kb:
            # Save to cache
            self._save_to_cache(processed_kb)
            self._knowledge_base = processed_kb
            self._cache_valid = True
        
        return processed_kb
    
    def _should_use_cache(self) -> bool:
        """Check if cache is valid and should be used"""
        if not self.cache_file.exists() or not self.metadata_file.exists():
            return False
        
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            cache_meta = CacheMetadata(
                created_at=datetime.fromisoformat(metadata['created_at']),
                file_count=metadata['file_count'],
                total_size=metadata['total_size'],
                checksum=metadata['checksum']
            )
            
            # Check if cache is too old (24 hours)
            if datetime.now() - cache_meta.created_at > timedelta(hours=24):
                logger.info("Cache expired (>24 hours old)")
                return False
            
            # Check if file count or checksum changed
            current_meta = self._get_current_metadata()
            if (cache_meta.file_count != current_meta.file_count or 
                cache_meta.checksum != current_meta.checksum):
                logger.info("Cache invalid (files changed)")
                return False
            
            logger.info("Cache is valid")
            return True
            
        except Exception as e:
            logger.warning(f"Error validating cache: {e}")
            return False
    
    def _get_current_metadata(self) -> CacheMetadata:
        """Get current metadata for cache validation"""
        if not self.data_directory.exists():
            return CacheMetadata(
                created_at=datetime.now(),
                file_count=0,
                total_size=0,
                checksum=""
            )
        
        json_files = list(self.data_directory.glob("*.json"))
        total_size = sum(f.stat().st_size for f in json_files)
        
        # Create checksum from file count, total size, and modification times
        checksum_data = f"{len(json_files)}:{total_size}:"
        checksum_data += ":".join(str(f.stat().st_mtime) for f in sorted(json_files)[:10])  # Sample first 10
        checksum = hashlib.md5(checksum_data.encode()).hexdigest()
        
        return CacheMetadata(
            created_at=datetime.now(),
            file_count=len(json_files),
            total_size=total_size,
            checksum=checksum
        )
    
    def _load_from_cache(self) -> Optional[ProcessedKnowledge]:
        """Load knowledge base from cache"""
        try:
            with open(self.cache_file, 'rb') as f:
                knowledge_base = pickle.load(f)
            logger.info(f"Loaded {len(knowledge_base.chunks)} chunks from cache")
            return knowledge_base
        except Exception as e:
            logger.error(f"Error loading from cache: {e}")
            return None
    
    def _save_to_cache(self, knowledge_base: ProcessedKnowledge):
        """Save knowledge base to cache"""
        try:
            # Save knowledge base
            with open(self.cache_file, 'wb') as f:
                pickle.dump(knowledge_base, f)
            
            # Save metadata
            metadata = self._get_current_metadata()
            with open(self.metadata_file, 'w') as f:
                json.dump({
                    'created_at': metadata.created_at.isoformat(),
                    'file_count': metadata.file_count,
                    'total_size': metadata.total_size,
                    'checksum': metadata.checksum,
                    'version': metadata.version
                }, f)
            
            logger.info(f"Cached {len(knowledge_base.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def _process_with_optimization(self) -> Optional[ProcessedKnowledge]:
        """Process files with parallel processing and optimizations"""
        if not self.data_directory.exists():
            logger.error(f"Data directory not found: {self.data_directory}")
            return None
        
        json_files = list(self.data_directory.glob("*.json"))
        if not json_files:
            logger.warning("No JSON files found")
            return None
        
        logger.info(f"Processing {len(json_files)} files with parallel processing")
        
        processed_chunks = []
        categories = {}
        
        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(32, (os.cpu_count() or 1) + 4)  # Optimal thread count
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file processing tasks
            future_to_file = {
                executor.submit(self._process_single_file, file_path): file_path 
                for file_path in json_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    chunk = future.result()
                    if chunk:
                        processed_chunks.append(chunk)
                        category = chunk.category
                        categories[category] = categories.get(category, 0) + 1
                except Exception as e:
                    logger.warning(f"Error processing {file_path}: {e}")
        
        logger.info(f"Successfully processed {len(processed_chunks)} chunks from {len(json_files)} files")
        
        return ProcessedKnowledge(
            chunks=processed_chunks,
            categories=categories,
            total_chunks=len(processed_chunks),
            processing_date=datetime.now().isoformat()
        )
    
    def _process_single_file(self, file_path: Path) -> Optional[KnowledgeChunk]:
        """Process a single JSON file (optimized for parallel execution)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract category and subcategory from filename
            filename = file_path.stem
            category, subcategory = self._extract_categories(filename)
            
            # Create knowledge chunk
            return self._create_knowledge_chunk(data, category, subcategory, filename)
            
        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
            return None
    
    def _extract_categories(self, filename: str) -> tuple[str, str]:
        """Extract category and subcategory from filename"""
        category_mappings = {
            'advanced-ai': 'AI & Machine Learning',
            'api': 'API & Integration',
            'code': 'Code & Development',
            'hosting': 'Hosting & Deployment',
            'integrations': 'Node Integrations',
            'data': 'Data Management',
            'flow-logic': 'Workflow Logic',
            'credentials': 'Authentication',
            'embed': 'Embedding',
            'courses': 'Learning Resources',
            'glossary': 'Reference',
            'help-community': 'Community & Support'
        }
        
        parts = filename.split('_')
        
        if len(parts) >= 2:
            main_category = parts[0]
            subcategory = '_'.join(parts[1:]) if len(parts) > 2 else parts[1]
        else:
            main_category = parts[0]
            subcategory = 'general'
        
        friendly_category = category_mappings.get(main_category, main_category.title())
        return friendly_category, subcategory
    
    def _create_knowledge_chunk(self, data: Dict, category: str, subcategory: str, filename: str) -> Optional[KnowledgeChunk]:
        """Create a knowledge chunk from scraped data"""
        try:
            title = data.get('title', 'Untitled')
            content = data.get('content', '')
            url = data.get('url', '')
            
            # Skip if no meaningful content
            if not content or len(content.strip()) < 50:
                return None
            
            # Clean content (simplified for performance)
            processed_content = ' '.join(content.split())  # Fast whitespace normalization
            
            # Extract basic metadata
            metadata = {
                'scraped_at': data.get('scraped_at', ''),
                'word_count': len(content.split()),
                'has_code_examples': '```' in content or '<code>' in content,
            }
            
            # Extract basic tags
            tags = [category.lower(), subcategory.lower()]
            if 'node' in title.lower():
                tags.append('node')
            if 'workflow' in title.lower():
                tags.append('workflow')
            
            # Generate unique ID
            chunk_id = hashlib.md5(f"{url}:{title}:{len(content)}".encode()).hexdigest()[:16]
            
            return KnowledgeChunk(
                id=chunk_id,
                title=title,
                content=processed_content,
                category=category,
                subcategory=subcategory,
                url=url,
                metadata=metadata,
                tags=tags
            )
            
        except Exception as e:
            logger.warning(f"Error creating chunk for {filename}: {e}")
            return None
    
    def invalidate_cache(self):
        """Invalidate and clear cache"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            
            self._knowledge_base = None
            self._cache_valid = False
            logger.info("Cache invalidated")
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'cache_exists': self.cache_file.exists(),
            'cache_valid': self._cache_valid,
            'knowledge_loaded': self._knowledge_base is not None
        }
        
        if self.cache_file.exists():
            stats['cache_size'] = self.cache_file.stat().st_size
            stats['cache_modified'] = datetime.fromtimestamp(self.cache_file.stat().st_mtime).isoformat()
        
        if self._knowledge_base:
            stats['chunks_count'] = len(self._knowledge_base.chunks)
            stats['categories_count'] = len(self._knowledge_base.categories)
        
        return stats