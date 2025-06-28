#!/usr/bin/env python3
"""
Optimization Module

Provides performance optimizations for the n8n scraper including:
- Knowledge base caching
- Singleton agent management
- Parallel processing
"""

from .agent_manager import (
    AgentManager,
    get_agent_manager,
    get_expert_agent,
    get_knowledge_processor,
    get_knowledge_cache
)
from .knowledge_cache import KnowledgeCache, CacheMetadata

__all__ = [
    'AgentManager',
    'get_agent_manager',
    'get_expert_agent', 
    'get_knowledge_processor',
    'get_knowledge_cache',
    'KnowledgeCache',
    'CacheMetadata'
]