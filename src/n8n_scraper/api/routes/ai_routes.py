"""
AI Agent API Routes

Routes for interacting with the n8n AI Expert Agent
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from n8n_scraper.optimization.agent_manager import get_expert_agent

router = APIRouter(prefix="/ai", tags=["AI Agent"])

# Request/Response models
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

class APIResponse(BaseModel):
    success: bool
    data: dict
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Use agent manager for singleton instances

def get_ai_agent():
    """Dependency to get the AI agent instance"""
    return get_expert_agent()

@router.post("/question", response_model=APIResponse)
async def ask_question(
    request: QuestionRequest,
    agent = Depends(get_ai_agent)
):
    """Ask the AI agent a question about n8n"""
    try:
        response = agent.answer_question(
            question=request.question,
            context=request.context,
            max_length=request.max_length
        )
        
        return APIResponse(
            success=True,
            data={
                "answer": response,
                "question": request.question
            },
            message="Question answered successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")

@router.post("/node-info", response_model=APIResponse)
async def get_node_info(
    request: NodeInfoRequest,
    agent = Depends(get_ai_agent)
):
    """Get information about a specific n8n node"""
    try:
        info = agent.get_node_info(
            node_name=request.node_name,
            include_examples=request.include_examples
        )
        
        return APIResponse(
            success=True,
            data={
                "node_info": info,
                "node_name": request.node_name
            },
            message="Node information retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node info: {str(e)}")

@router.post("/workflow-suggestion", response_model=APIResponse)
async def suggest_workflow(
    request: WorkflowSuggestionRequest,
    agent = Depends(get_ai_agent)
):
    """Get workflow suggestions from the AI agent"""
    try:
        suggestion = agent.suggest_workflow(
            description=request.description,
            complexity=request.complexity,
            include_nodes=request.include_nodes
        )
        
        return APIResponse(
            success=True,
            data={
                "workflow_suggestion": suggestion,
                "description": request.description
            },
            message="Workflow suggestion generated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest workflow: {str(e)}")

@router.get("/best-practices", response_model=APIResponse)
async def get_best_practices(
    category: Optional[str] = None,
    agent = Depends(get_ai_agent)
):
    """Get n8n best practices"""
    try:
        practices = agent.get_best_practices(topic=category)
        
        return APIResponse(
            success=True,
            data={
                "best_practices": practices,
                "category": category
            },
            message="Best practices retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get best practices: {str(e)}")