"""
API Routes package
"""

from .ai_routes import router as ai_router
from .knowledge_routes import router as knowledge_router
from .system_routes import router as system_router
from .auth_routes import router as auth_router
from .optimization_routes import router as optimization_router
from .workflow_routes import router as workflow_router

__all__ = ["ai_router", "knowledge_router", "system_router", "auth_router", "optimization_router", "workflow_router"]
