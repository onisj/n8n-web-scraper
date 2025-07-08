#!/usr/bin/env python3
"""
Workflow API Routes for n8n Web Scraper

Provides REST API endpoints for workflow management, search, and visualization.
Integrates the standalone workflows system from data/workflows/ into the main API.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from ...workflow_integration import get_workflow_integration

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/workflows", tags=["workflows"])

# Get workflow integration instance
workflow_integration = get_workflow_integration()

# Pydantic models for requests/responses
class WorkflowSearchQuery(BaseModel):
    query: str = Field(..., description="Search query for workflows")
    category: Optional[str] = Field(None, description="Filter by category")
    integration: Optional[str] = Field(None, description="Filter by integration")
    limit: Optional[int] = Field(20, description="Maximum number of results")
    offset: Optional[int] = Field(0, description="Offset for pagination")

class WorkflowFilter(BaseModel):
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    integrations: Optional[List[str]] = Field(None, description="Filter by integrations")
    complexity: Optional[str] = Field(None, description="Filter by complexity level")
    has_webhook: Optional[bool] = Field(None, description="Filter workflows with webhooks")
    has_schedule: Optional[bool] = Field(None, description="Filter workflows with schedules")

class WorkflowAnalytics(BaseModel):
    total_workflows: int
    categories_count: int
    integrations_count: int
    avg_nodes_per_workflow: float
    most_used_integrations: List[Dict[str, Any]]
    complexity_distribution: Dict[str, int]
    last_updated: str

class MermaidRequest(BaseModel):
    workflow_id: str = Field(..., description="Workflow ID to generate diagram for")
    theme: Optional[str] = Field("default", description="Mermaid theme")
    direction: Optional[str] = Field("TD", description="Diagram direction (TD, LR, etc.)")



@router.get("/health", response_model=None)
async def workflow_health():
    """Health check for workflow system"""
    try:
        stats_result = workflow_integration.get_workflow_stats()
        if stats_result.get("success"):
            stats = stats_result.get("data", {})
            return {
                "status": "healthy",
                "workflows_count": stats.get("total_workflows", 0),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"status": "error", "message": stats_result.get("error", "Unknown error")}
    except Exception as e:
        logger.error(f"Workflow health check failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/stats", response_model=WorkflowAnalytics)
async def get_workflow_stats():
    """Get comprehensive workflow statistics"""
    try:
        result = workflow_integration.get_workflow_stats()
        if result.get("success"):
            stats = result.get("data", {})
            
            # Get all workflows for analytics
            search_result = workflow_integration.search_workflows("", limit=1000)
            workflows = search_result.get("data", {}).get("workflows", []) if search_result.get("success") else []
            
            total_nodes = sum(len(w.get("nodes", [])) for w in workflows)
            avg_nodes = total_nodes / len(workflows) if workflows else 0
            
            # Count integrations
            integration_counts = {}
            complexity_dist = {"simple": 0, "medium": 0, "complex": 0}
            
            for workflow in workflows:
                # Count integrations
                for node in workflow.get("nodes", []):
                    node_type = node.get("type", "unknown")
                    integration_counts[node_type] = integration_counts.get(node_type, 0) + 1
                
                # Classify complexity
                node_count = len(workflow.get("nodes", []))
                if node_count <= 3:
                    complexity_dist["simple"] += 1
                elif node_count <= 8:
                    complexity_dist["medium"] += 1
                else:
                    complexity_dist["complex"] += 1
            
            # Get top integrations
            top_integrations = sorted(
                integration_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return {
                "total_workflows": stats.get("total", 0),
                "categories_count": len(stats.get("triggers", {})),
                "integrations_count": stats.get("unique_integrations", 0),
                "avg_nodes_per_workflow": round(stats.get("total_nodes", 0) / max(stats.get("total", 1), 1), 2),
                "most_used_integrations": [
                    {"name": name, "count": count} for name, count in top_integrations
                ],
                "complexity_distribution": {
                    "simple": stats.get("complexity", {}).get("low", 0),
                    "medium": stats.get("complexity", {}).get("medium", 0),
                    "complex": stats.get("complexity", {}).get("high", 0)
                },
                "last_updated": stats.get("last_indexed", datetime.now().isoformat())
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except Exception as e:
        logger.error(f"Failed to get workflow stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=None)
async def search_workflows(search_query: WorkflowSearchQuery):
    """Search workflows with advanced filtering"""
    try:
        result = workflow_integration.search_workflows(
            query=search_query.query,
            category=search_query.category,
            integration=search_query.integration,
            limit=search_query.limit,
            offset=search_query.offset
        )
        
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "data": {
                    "workflows": data.get("workflows", []),
                    "total": data.get("total", 0),
                    "query": search_query.query,
                    "filters": {
                        "category": search_query.category,
                        "integration": search_query.integration
                    }
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except Exception as e:
        logger.error(f"Workflow search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories", response_model=None)
async def get_categories():
    """Get all available workflow categories"""
    try:
        result = workflow_integration.get_categories()
        if result.get("success"):
            return {
                "success": True,
                "data": result.get("data", [])
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/integrations", response_model=None)
async def get_integrations():
    """Get all available workflow integrations"""
    try:
        result = workflow_integration.get_integrations()
        if result.get("success"):
            return {
                "success": True,
                "data": result.get("data", [])
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except Exception as e:
        logger.error(f"Failed to get integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=None)
async def get_workflow_details(workflow_id: str):
    """Get detailed information about a specific workflow"""
    try:
        result = workflow_integration.get_workflow_by_id(workflow_id)
        if result.get("success"):
            return {
                "success": True,
                "data": result.get("data", {})
            }
        else:
            error = result.get("error", "Unknown error")
            if "not found" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=500, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/download", response_model=None)
async def download_workflow(workflow_id: str):
    """Download workflow JSON file"""
    try:
        result = workflow_integration.download_workflow(workflow_id)
        if result.get("success"):
            data = result.get("data", {})
            
            # Create temporary file for download
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(data.get("content", {}), f, indent=2)
                temp_path = f.name
            
            filename = data.get("filename", f"{workflow_id}.json")
            return FileResponse(
                path=temp_path,
                filename=filename,
                media_type='application/json'
            )
        else:
            error = result.get("error", "Unknown error")
            if "not found" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=500, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/mermaid", response_model=None)
async def generate_mermaid_diagram(workflow_id: str, request: MermaidRequest):
    """Generate Mermaid diagram for workflow visualization"""
    try:
        result = workflow_integration.generate_mermaid_diagram(workflow_id)
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "data": {
                    "mermaid_code": data.get("mermaid_code", ""),
                    "workflow_id": workflow_id,
                    "theme": request.theme,
                    "direction": request.direction
                }
            }
        else:
            error = result.get("error", "Unknown error")
            if "not found" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=500, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Mermaid diagram: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reindex", response_model=None)
async def reindex_workflows(background_tasks: BackgroundTasks):
    """Trigger workflow database reindexing"""
    try:
        result = workflow_integration.import_workflows_to_db()
        if result.get("success"):
            return {
                "success": True,
                "message": "Workflow reindexing completed",
                "timestamp": datetime.now().isoformat(),
                "data": result.get("data", {})
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start reindexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/filter", response_model=None)
async def filter_workflows(filter_request: WorkflowFilter):
    """Advanced workflow filtering"""
    try:
        # Use search with filters as a fallback for filtering
        result = workflow_integration.search_workflows(
            query="",
            category=filter_request.categories[0] if filter_request.categories else None,
            integration=filter_request.integrations[0] if filter_request.integrations else None,
            limit=1000
        )
        
        if result.get("success"):
            workflows = result.get("data", {}).get("workflows", [])
            
            # Apply additional filtering logic here if needed
            filtered_workflows = workflows
            
            return {
                "success": True,
                "data": {
                    "workflows": filtered_workflows,
                    "total": len(filtered_workflows),
                    "filters_applied": filter_request.dict(exclude_none=True)
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except Exception as e:
        logger.error(f"Workflow filtering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/similar", response_model=None)
async def get_similar_workflows(workflow_id: str, limit: int = Query(5, ge=1, le=20)):
    """Find workflows similar to the given workflow"""
    try:
        result = workflow_integration.get_similar_workflows(workflow_id, limit)
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "data": {
                    "similar_workflows": data.get("similar_workflows", []),
                    "base_workflow_id": workflow_id,
                    "total": len(data.get("similar_workflows", []))
                }
            }
        else:
            error = result.get("error", "Unknown error")
            if "not found" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=500, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find similar workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))