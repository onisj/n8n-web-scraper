#!/usr/bin/env python3
"""
FastAPI Server for n8n AI Knowledge System

Provides REST API endpoints for TRAE integration and external access
to the n8n AI Expert Agent and knowledge base.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import our custom modules
from n8n_scraper.optimization.agent_manager import get_expert_agent, get_knowledge_processor, get_agent_manager
from n8n_scraper.automation.update_scheduler import AutomatedUpdater
from n8n_scraper.automation.change_detector import N8nDataAnalyzer as N8nDocsAnalyzer

# Import API routes
from .routes import ai_routes, knowledge_routes, system_routes, optimization_routes, workflow_routes, auth_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="n8n AI Knowledge System API",
    description="REST API for n8n AI Expert Agent and Knowledge Base",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ai_routes.router)
app.include_router(knowledge_routes.router)
app.include_router(system_routes.router)
app.include_router(optimization_routes.router)
app.include_router(workflow_routes.router)
app.include_router(auth_routes.router)

# Pydantic models for request/response
class QuestionRequest(BaseModel):
    question: str = Field(..., description="Question about n8n")
    context: Optional[str] = Field(None, description="Additional context")
    max_length: Optional[int] = Field(500, description="Maximum response length")

class NodeInfoRequest(BaseModel):
    node_name: str = Field(..., description="Name of the n8n node")
    include_examples: Optional[bool] = Field(True, description="Include usage examples")

class WorkflowSuggestionRequest(BaseModel):
    description: str = Field(..., description="Description of desired workflow")
    complexity: Optional[str] = Field("medium", description="Complexity level: simple, medium, complex")
    include_nodes: Optional[List[str]] = Field(None, description="Preferred nodes to include")

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Category filter")
    limit: Optional[int] = Field(10, description="Maximum results")

class UpdateRequest(BaseModel):
    force: Optional[bool] = Field(False, description="Force update even if recent")
    full_scrape: Optional[bool] = Field(False, description="Perform full scrape")

class APIResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class SystemStatus(BaseModel):
    status: str
    knowledge_base_size: int
    last_update: Optional[str]
    ai_agent_status: str
    uptime: str

# Global agent manager
agent_manager = get_agent_manager()
automated_updater = None
analyzer = None
start_time = datetime.now()

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global automated_updater, analyzer
    
    logger.info("Initializing n8n AI Knowledge System API...")
    
    try:
        # Initialize database
        from ..database.connection import initialize_database
        await initialize_database()
        logger.info("Database initialized")
        
        # Initialize Redis cache
        from ..cache.redis_cache import get_cache
        cache = await get_cache()
        await cache.connect()
        logger.info("Redis cache initialized")
        
        # Initialize agents through manager (prevents duplicate loading)
        agent_manager.get_expert_agent()
        agent_manager.get_knowledge_processor()
        automated_updater = AutomatedUpdater()
        analyzer = N8nDocsAnalyzer()
        
        logger.info("API server initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize API server: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down n8n AI Knowledge System API...")
    
    try:
        # Cleanup Redis cache
        from ..cache.redis_cache import get_cache
        cache = await get_cache()
        await cache.disconnect()
        logger.info("Redis cache disconnected")
        
        # Cleanup database
        from ..database.connection import cleanup_database
        await cleanup_database()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Dependency to get AI agent
def get_ai_agent():
    try:
        return agent_manager.get_expert_agent()
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")

# Note: Health check and system status endpoints are now handled by system_routes

# Note: AI Agent endpoints are now handled by ai_router

# Note: Knowledge base endpoints are now handled by knowledge_router

# Note: Update management endpoints are now handled by system_routes

# Background task for updates
async def run_update_task(force: bool = False, full_scrape: bool = False):
    """Background task to run knowledge base update"""
    try:
        logger.info("Starting background update task")
        
        if automated_updater:
            await automated_updater.run_update_cycle(force=force, full_scrape=full_scrape)
        
        logger.info("Background update task completed")
    except Exception as e:
        logger.error(f"Background update task failed: {str(e)}")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="n8n AI Knowledge System API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )