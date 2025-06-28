#!/usr/bin/env python3
"""
Singleton Agent Manager

Manages global instances of N8nExpertAgent and N8nKnowledgeProcessor
to prevent duplicate initialization and improve performance.
"""

import threading
import logging
from typing import Optional

from n8n_scraper.agents.n8n_agent import N8nExpertAgent
from n8n_scraper.agents.knowledge_processor import N8nKnowledgeProcessor
from n8n_scraper.optimization.knowledge_cache import KnowledgeCache

logger = logging.getLogger(__name__)

class AgentManager:
    """Singleton manager for AI agents with optimized initialization"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._expert_agent: Optional[N8nExpertAgent] = None
        self._knowledge_processor: Optional[N8nKnowledgeProcessor] = None
        self._knowledge_cache: Optional[KnowledgeCache] = None
        self._initialization_lock = threading.Lock()
        self._initialized = True
        
        logger.info("Agent manager initialized")
    
    def get_expert_agent(self, data_directory: str = "data/scraped_docs") -> N8nExpertAgent:
        """Get or create the expert agent instance"""
        if self._expert_agent is None:
            with self._initialization_lock:
                if self._expert_agent is None:
                    logger.info("Creating optimized N8nExpertAgent instance")
                    
                    # Initialize cache first
                    self._knowledge_cache = KnowledgeCache(data_directory)
                    
                    # Create agent with optimized loading
                    self._expert_agent = OptimizedN8nExpertAgent(
                        data_directory=data_directory
                    )
                    
                    logger.info("N8nExpertAgent instance created")
        
        return self._expert_agent
    
    def get_knowledge_processor(self, data_directory: str = "data/scraped_docs") -> N8nKnowledgeProcessor:
        """Get or create the knowledge processor instance"""
        if self._knowledge_processor is None:
            with self._initialization_lock:
                if self._knowledge_processor is None:
                    logger.info("Creating N8nKnowledgeProcessor instance")
                    self._knowledge_processor = N8nKnowledgeProcessor(data_directory)
                    logger.info("N8nKnowledgeProcessor instance created")
        
        return self._knowledge_processor
    
    def get_knowledge_cache(self, data_directory: str = "data/scraped_docs") -> KnowledgeCache:
        """Get or create the knowledge cache instance"""
        if self._knowledge_cache is None:
            with self._initialization_lock:
                if self._knowledge_cache is None:
                    logger.info("Creating KnowledgeCache instance")
                    self._knowledge_cache = KnowledgeCache(data_directory)
                    logger.info("KnowledgeCache instance created")
        
        return self._knowledge_cache
    
    def invalidate_cache(self):
        """Invalidate all cached data"""
        if self._knowledge_cache:
            self._knowledge_cache.invalidate_cache()
        
        # Reset agents to force reload
        with self._initialization_lock:
            self._expert_agent = None
            self._knowledge_processor = None
        
        logger.info("All caches invalidated")
    
    def get_status(self) -> dict:
        """Get status of all managed components"""
        status = {
            'expert_agent_loaded': self._expert_agent is not None,
            'knowledge_processor_loaded': self._knowledge_processor is not None,
            'knowledge_cache_loaded': self._knowledge_cache is not None
        }
        
        if self._knowledge_cache:
            status['cache_stats'] = self._knowledge_cache.get_cache_stats()
        
        return status

class OptimizedN8nExpertAgent(N8nExpertAgent):
    """Optimized version of N8nExpertAgent with caching and performance improvements"""
    
    def __init__(self, data_directory: str = "data/scraped_docs"):
        # Initialize parent class first to set knowledge_base attribute
        super().__init__(data_directory)
        
        # Add optimization-specific attributes
        self.knowledge_cache = KnowledgeCache()
        
        # Override with optimized loading
        self._load_knowledge_base_optimized()
    
    def _load_knowledge_base_optimized(self):
        """Load knowledge base with caching optimization"""
        logger.info(f"Loading n8n knowledge base from {self.data_directory}...")
        
        # Use cached knowledge base
        processed_knowledge = self.knowledge_cache.get_knowledge_base()
        
        if processed_knowledge:
            # Set the knowledge_base attribute that the parent class expects
            self.knowledge_base = processed_knowledge
            
            logger.info(f"Successfully loaded {len(processed_knowledge.chunks)} knowledge chunks from cache")
        else:
            logger.error("Failed to load knowledge base from cache")
            # Fall back to parent class loading method
            super()._load_knowledge_base()
    
    def reload_knowledge_base(self, force_refresh: bool = False):
        """Reload knowledge base with option to force refresh"""
        if force_refresh:
            self.knowledge_cache.invalidate_cache()
        
        self._load_knowledge_base_optimized()

# Global instance
_agent_manager = AgentManager()

def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance"""
    return _agent_manager

def get_expert_agent(data_directory: str = "data/scraped_docs") -> N8nExpertAgent:
    """Get the expert agent instance (convenience function)"""
    return _agent_manager.get_expert_agent(data_directory)

def get_knowledge_processor(data_directory: str = "data/scraped_docs") -> N8nKnowledgeProcessor:
    """Get the knowledge processor instance (convenience function)"""
    return _agent_manager.get_knowledge_processor(data_directory)

def get_knowledge_cache(data_directory: str = "data/scraped_docs") -> KnowledgeCache:
    """Get the knowledge cache instance (convenience function)"""
    return _agent_manager.get_knowledge_cache(data_directory)