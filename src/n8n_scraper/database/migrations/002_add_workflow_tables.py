"""Add Workflow Tables Migration.

Adds tables for storing n8n workflow documents and their chunks.
"""

import logging
from typing import Dict, Any
from sqlalchemy import text

from ..connection import get_database_session
from ..models import Base, WorkflowDocument, WorkflowChunk

logger = logging.getLogger(__name__)

MIGRATION_ID = "002"
MIGRATION_NAME = "add_workflow_tables"
MIGRATION_DESCRIPTION = "Add workflow_documents and workflow_chunks tables"


def upgrade() -> bool:
    """Apply the migration.
    
    Returns:
        bool: Success status
    """
    try:
        logger.info(f"Applying migration {MIGRATION_ID}: {MIGRATION_NAME}")
        
        # Get database session
        session = get_database_session()
        
        # Create workflow tables
        engine = session.get_bind()
        
        # Create workflow_documents table
        WorkflowDocument.__table__.create(engine, checkfirst=True)
        logger.info("Created workflow_documents table")
        
        # Create workflow_chunks table
        WorkflowChunk.__table__.create(engine, checkfirst=True)
        logger.info("Created workflow_chunks table")
        
        # Add migration record
        migration_record = text("""
            INSERT INTO system_metrics (id, metric_name, metric_type, value, labels, timestamp)
            VALUES (gen_random_uuid(), :metric_name, 'counter', 1, :labels, NOW())
        """)
        
        session.execute(migration_record, {
            "metric_name": f"migration_{MIGRATION_ID}_applied",
            "labels": {
                "migration_id": MIGRATION_ID,
                "migration_name": MIGRATION_NAME,
                "description": MIGRATION_DESCRIPTION
            }
        })
        
        session.commit()
        session.close()
        
        logger.info(f"Migration {MIGRATION_ID} applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error applying migration {MIGRATION_ID}: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False


def downgrade() -> bool:
    """Rollback the migration.
    
    Returns:
        bool: Success status
    """
    try:
        logger.info(f"Rolling back migration {MIGRATION_ID}: {MIGRATION_NAME}")
        
        # Get database session
        session = get_database_session()
        engine = session.get_bind()
        
        # Drop workflow tables
        WorkflowChunk.__table__.drop(engine, checkfirst=True)
        logger.info("Dropped workflow_chunks table")
        
        WorkflowDocument.__table__.drop(engine, checkfirst=True)
        logger.info("Dropped workflow_documents table")
        
        # Remove migration record
        delete_record = text("""
            DELETE FROM system_metrics 
            WHERE metric_name = :metric_name
        """)
        
        session.execute(delete_record, {
            "metric_name": f"migration_{MIGRATION_ID}_applied"
        })
        
        session.commit()
        session.close()
        
        logger.info(f"Migration {MIGRATION_ID} rolled back successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error rolling back migration {MIGRATION_ID}: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
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
        "created_at": "2024-01-02T00:00:00",
        "dependencies": ["001"],
        "reversible": True
    }