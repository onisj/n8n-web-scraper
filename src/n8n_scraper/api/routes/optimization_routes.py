#!/usr/bin/env python3
"""
Optimization API Routes

Provides endpoints for cache management and performance optimization.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from n8n_scraper.optimization.agent_manager import get_agent_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimization", tags=["Performance Optimization"])

class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class CacheRefreshRequest(BaseModel):
    """Request to refresh cache"""
    force_refresh: bool = Field(default=False, description="Force complete cache refresh")

@router.get("/status", response_model=APIResponse)
async def get_optimization_status():
    """Get current optimization and cache status"""
    try:
        agent_manager = get_agent_manager()
        status = agent_manager.get_status()
        
        return APIResponse(
            success=True,
            message="Optimization status retrieved successfully",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Error getting optimization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats", response_model=APIResponse)
async def get_cache_stats():
    """Get detailed cache statistics"""
    try:
        agent_manager = get_agent_manager()
        cache = agent_manager.get_knowledge_cache()
        stats = cache.get_cache_stats()
        
        return APIResponse(
            success=True,
            message="Cache statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/refresh", response_model=APIResponse)
async def refresh_cache(request: CacheRefreshRequest):
    """Refresh the knowledge base cache"""
    try:
        agent_manager = get_agent_manager()
        
        if request.force_refresh:
            # Invalidate cache and force reload
            agent_manager.invalidate_cache()
            logger.info("Cache invalidated, forcing complete refresh")
        
        # Get fresh knowledge base (will use cache if valid, or rebuild if needed)
        cache = agent_manager.get_knowledge_cache()
        knowledge_base = cache.get_knowledge_base(force_refresh=request.force_refresh)
        
        if knowledge_base:
            stats = {
                'chunks_loaded': len(knowledge_base.chunks),
                'categories': len(knowledge_base.categories),
                'processing_date': knowledge_base.processing_date,
                'force_refresh': request.force_refresh
            }
            
            return APIResponse(
                success=True,
                message="Cache refreshed successfully",
                data=stats
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh cache")
            
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache", response_model=APIResponse)
async def clear_cache():
    """Clear all cached data"""
    try:
        agent_manager = get_agent_manager()
        agent_manager.invalidate_cache()
        
        return APIResponse(
            success=True,
            message="Cache cleared successfully",
            data={'cache_cleared': True}
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/tips", response_model=APIResponse)
async def get_performance_tips():
    """Get performance optimization tips and recommendations"""
    try:
        agent_manager = get_agent_manager()
        status = agent_manager.get_status()
        
        tips = []
        
        # Analyze current state and provide tips
        if not status.get('cache_stats', {}).get('cache_exists', False):
            tips.append({
                'category': 'Caching',
                'tip': 'No cache found. First startup will be slower but subsequent starts will be much faster.',
                'action': 'Wait for initial processing to complete'
            })
        
        cache_stats = status.get('cache_stats', {})
        if cache_stats.get('cache_exists') and not cache_stats.get('cache_valid'):
            tips.append({
                'category': 'Caching',
                'tip': 'Cache exists but may be invalid. Consider refreshing.',
                'action': 'Use POST /optimization/cache/refresh to refresh cache'
            })
        
        if cache_stats.get('chunks_count', 0) > 0:
            tips.append({
                'category': 'Performance',
                'tip': f"Knowledge base loaded with {cache_stats['chunks_count']} chunks. Using singleton pattern to prevent duplicate loading.",
                'action': 'No action needed - optimization active'
            })
        
        # General performance tips
        tips.extend([
            {
                'category': 'Startup',
                'tip': 'Use parallel processing for file loading (automatically enabled)',
                'action': 'No action needed - optimization active'
            },
            {
                'category': 'Memory',
                'tip': 'Singleton pattern prevents duplicate agent initialization',
                'action': 'No action needed - optimization active'
            },
            {
                'category': 'Caching',
                'tip': 'Cache is automatically validated based on file changes and age',
                'action': 'Monitor cache stats regularly'
            }
        ])
        
        return APIResponse(
            success=True,
            message="Performance tips retrieved successfully",
            data={
                'tips': tips,
                'current_status': status
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting performance tips: {e}")
        raise HTTPException(status_code=500, detail=str(e))