"""Initial Database Setup Migration.

Sets up the initial vector database structure and collections for the n8n AI Knowledge System.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from ..vector_db import VectorDatabase
from ..schemas import KnowledgeBaseInfo, KnowledgeBaseStatus

logger = logging.getLogger(__name__)

MIGRATION_ID = "001"
MIGRATION_NAME = "initial_setup"
MIGRATION_DESCRIPTION = "Initial database setup with collections and indexes"


def upgrade(db: VectorDatabase) -> bool:
    """Apply the migration.
    
    Args:
        db: Vector database instance
        
    Returns:
        bool: Success status
    """
    try:
        logger.info(f"Applying migration {MIGRATION_ID}: {MIGRATION_NAME}")
        
        # Ensure the main collection exists
        if not hasattr(db, 'collection') or db.collection is None:
            logger.error("Database collection not initialized")
            return False
        
        # Add initial metadata to track migration
        migration_doc = {
            "id": f"migration_{MIGRATION_ID}",
            "content": f"Migration {MIGRATION_ID}: {MIGRATION_DESCRIPTION}",
            "metadata": {
                "type": "migration",
                "migration_id": MIGRATION_ID,
                "migration_name": MIGRATION_NAME,
                "applied_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }
        
        # Add migration record
        success = db.add_documents(
            documents=[migration_doc["content"]],
            metadatas=[migration_doc["metadata"]],
            ids=[migration_doc["id"]]
        )
        
        if not success:
            logger.error("Failed to add migration record")
            return False
        
        # Create knowledge base info document
        kb_info = {
            "id": "kb_info",
            "content": "n8n AI Knowledge System - Knowledge Base Information",
            "metadata": {
                "type": "system_info",
                "name": "n8n_ai_knowledge_system",
                "version": "1.0.0",
                "status": KnowledgeBaseStatus.READY.value,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "embedding_model": db.embedding_model,
                "collection_name": db.collection_name
            }
        }
        
        success = db.add_documents(
            documents=[kb_info["content"]],
            metadatas=[kb_info["metadata"]],
            ids=[kb_info["id"]]
        )
        
        if not success:
            logger.error("Failed to add knowledge base info")
            return False
        
        logger.info(f"Migration {MIGRATION_ID} applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error applying migration {MIGRATION_ID}: {e}")
        return False


def downgrade(db: VectorDatabase) -> bool:
    """Rollback the migration.
    
    Args:
        db: Vector database instance
        
    Returns:
        bool: Success status
    """
    try:
        logger.info(f"Rolling back migration {MIGRATION_ID}: {MIGRATION_NAME}")
        
        # Remove migration record
        success1 = db.delete_document(f"migration_{MIGRATION_ID}")
        success2 = db.delete_document("kb_info")
        
        if success1 and success2:
            logger.info(f"Migration {MIGRATION_ID} rolled back successfully")
            return True
        else:
            logger.warning(f"Partial rollback of migration {MIGRATION_ID}")
            return False
            
    except Exception as e:
        logger.error(f"Error rolling back migration {MIGRATION_ID}: {e}")
        return False


def get_migration_info() -> Dict[str, Any]:
    """Get migration information.
    
    Returns:
        Dict containing migration details
    """
    return {
        "id": MIGRATION_ID,
        "name": MIGRATION_NAME,
        "description": MIGRATION_DESCRIPTION,
        "created_at": "2024-01-01T00:00:00",
        "dependencies": [],
        "reversible": True
    }