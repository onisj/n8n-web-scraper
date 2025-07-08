"""
Knowledge Base API Routes

Routes for searching and exploring the n8n knowledge base
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import json

from n8n_scraper.optimization.agent_manager import get_knowledge_processor, get_expert_agent
from n8n_scraper.database.workflow_db import WorkflowDatabase

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

# Request/Response models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Category filter")
    limit: Optional[int] = Field(10, description="Maximum results")

class APIResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Use agent manager for singleton instances

def get_knowledge_processor_dep():
    """Dependency to get the knowledge processor instance"""
    return get_knowledge_processor()

def get_ai_agent_dep():
    """Dependency to get the AI agent instance"""
    return get_expert_agent()

@router.post("/search", response_model=APIResponse)
async def search_knowledge(
    request: SearchRequest,
    agent = Depends(get_ai_agent_dep)
):
    """Search the knowledge base"""
    try:
        agent_response = agent.search_knowledge(
            query=request.query
        )
        
        # Format the response for API consumption
        results = [{
            "content": agent_response.response,
            "confidence": agent_response.confidence,
            "sources": agent_response.sources,
            "suggestions": agent_response.suggestions,
            "timestamp": agent_response.timestamp.isoformat()
        }]
        
        return APIResponse(
            success=True,
            data={
                "results": results,
                "query": request.query,
                "total_results": len(results),
                "confidence": agent_response.confidence
            },
            message="Search completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/categories", response_model=APIResponse)
async def get_categories(
    processor = Depends(get_knowledge_processor_dep)
):
    """Get available knowledge categories"""
    try:
        # Get categories from processed knowledge
        data_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs")
        categories = set()
        
        if data_dir.exists():
            for json_file in data_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'category' in data:
                            categories.add(data['category'])
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and 'category' in item:
                                    categories.add(item['category'])
                except Exception:
                    continue
        
        return APIResponse(
            success=True,
            data={
                "categories": sorted(list(categories)),
                "total_categories": len(categories)
            },
            message="Categories retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.get("/stats", response_model=APIResponse)
async def get_knowledge_stats(
    agent = Depends(get_ai_agent_dep)
):
    """Get knowledge base statistics"""
    try:
        # Check both documentation and workflow directories
        docs_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs")
        workflows_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/workflows/files")
        
        total_files = 0
        total_pages = 0
        categories = set()
        workflow_files = 0
        documentation_files = 0
        
        # Count documentation files
        if docs_dir.exists():
            doc_json_files = list(docs_dir.glob("*.json"))
            documentation_files = len(doc_json_files)
            total_files += documentation_files
            
            for json_file in doc_json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            total_pages += 1
                            if 'category' in data:
                                categories.add(data['category'])
                        elif isinstance(data, list):
                            total_pages += len(data)
                            for item in data:
                                if isinstance(item, dict) and 'category' in item:
                                    categories.add(item['category'])
                except Exception:
                    continue
        
        # Count workflow files from SQLite database
        try:
            workflow_db = WorkflowDatabase("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/sqlite/workflows.db")
            workflow_stats = workflow_db.get_stats()
            workflow_files = workflow_stats.get('total', 0)
            total_files += workflow_files
            total_pages += workflow_files  # Each workflow is considered a page
            categories.add("workflows")
        except Exception as e:
            print(f"Warning: Could not get workflow stats from database: {e}")
            # Fallback to file counting if database is not available
            if workflows_dir.exists():
                workflow_json_files = list(workflows_dir.glob("*.json"))
                workflow_files = len(workflow_json_files)
                total_files += workflow_files
                
                for json_file in workflow_json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                total_pages += 1
                                # Add workflow category
                                categories.add("workflows")
                                if 'category' in data:
                                    categories.add(data['category'])
                            elif isinstance(data, list):
                                total_pages += len(data)
                                categories.add("workflows")
                                for item in data:
                                    if isinstance(item, dict) and 'category' in item:
                                        categories.add(item['category'])
                    except Exception:
                        continue
        
        # Get last update from analysis report
        analysis_file = Path("n8n_docs_analysis_report.json")
        last_update = None
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    analysis = json.load(f)
                    last_update = analysis.get('timestamp')
            except Exception:
                pass
        
        # Get additional workflow statistics if database is available
        workflow_details = {}
        try:
            workflow_db = WorkflowDatabase("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/sqlite/workflows.db")
            workflow_stats = workflow_db.get_stats()
            workflow_details = {
                "total_workflows": workflow_stats.get('total', workflow_files),
                "active_workflows": workflow_stats.get('active', 0),
                "total_nodes": workflow_stats.get('total_nodes', 0),
                "unique_integrations": workflow_stats.get('unique_integrations', 0)
            }
        except Exception:
            workflow_details = {
                "total_workflows": workflow_files,
                "active_workflows": 0,
                "total_nodes": 0,
                "unique_integrations": 0
            }

        return APIResponse(
            success=True,
            data={
                "total_files": total_files,
                "total_pages": total_pages,
                "documentation_files": documentation_files,
                "workflow_files": workflow_files,
                "categories": sorted(list(categories)),
                "total_categories": len(categories),
                "last_update": last_update,
                **workflow_details
            },
            message="Statistics retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.get("/document/{doc_id}", response_model=APIResponse)
async def get_document(doc_id: str):
    """Get a specific document by ID"""
    try:
        data_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs")
        doc_file = data_dir / f"{doc_id}.json"
        
        if not doc_file.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        
        with open(doc_file, 'r', encoding='utf-8') as f:
            document = json.load(f)
        
        return APIResponse(
            success=True,
            data={
                "document": document,
                "doc_id": doc_id
            },
            message="Document retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@router.get("/recent", response_model=APIResponse)
async def get_recent_documents(limit: int = 10):
    """Get recently updated documents"""
    try:
        data_dir = Path("data/scraped_docs")
        
        if not data_dir.exists():
            return APIResponse(
                success=True,
                data={"documents": []},
                message="No documents found"
            )
        
        # Get files sorted by modification time
        json_files = sorted(
            data_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:limit]
        
        documents = []
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract basic info
                    doc_info = {
                        "id": json_file.stem,
                        "title": data.get('title', 'Unknown') if isinstance(data, dict) else 'Unknown',
                        "category": data.get('category', 'Unknown') if isinstance(data, dict) else 'Unknown',
                        "modified": json_file.stat().st_mtime
                    }
                    documents.append(doc_info)
            except Exception:
                continue
        
        return APIResponse(
            success=True,
            data={
                "documents": documents,
                "total": len(documents)
            },
            message="Recent documents retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent documents: {str(e)}")

@router.post("/reload", response_model=APIResponse)
async def reload_knowledge_base():
    """Reload the knowledge base from scratch"""
    try:
        global ai_agent, knowledge_processor
        
        # Reset global instances
        ai_agent = None
        knowledge_processor = None
        
        # Create new agent instance which will reload the knowledge base
        agent = get_expert_agent()
        
        # Get stats to verify reload
        stats = agent.get_knowledge_stats()
        
        return APIResponse(
            success=True,
            data={
                "message": "Knowledge base reloaded successfully",
                "stats": stats
            },
            message="Knowledge base reloaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload knowledge base: {str(e)}")