"""
Database Package

Provides database functionality for the n8n AI Knowledge System
"""

from .vector_db import VectorDatabase
from .migrations import MigrationManager
from .connection import (
    get_database_connection,
    close_database_connection,
    DatabaseManager,
)
from .models import (
    Base,
    ScrapedDocument,
    ConversationHistory,
    SystemMetrics,
    CacheEntry,
)
from .vector_store import VectorStore
from .migrations import run_migrations

# Import schemas
from .schemas import (
    # Document schemas
    DocumentType,
    DocumentStatus,
    DocumentMetadata,
    Document,
    DocumentChunk,
    SearchResult,
    SearchQuery,
    
    # Knowledge base schemas
    KnowledgeBaseStatus,
    UpdateStatus,
    KnowledgeBaseInfo,
    UpdateJob,
    CategoryStats,
    QualityMetrics,
    SearchAnalytics,
    SystemHealth,
    BackupInfo,
    ConfigurationSchema,
    
    # Utility functions
    create_document_id,
    extract_metadata_from_url,
    create_knowledge_base_info,
    create_update_job,
    calculate_quality_score,
    create_backup_info
)

__all__ = [
    # Core database classes
    'VectorDatabase',
    'MigrationManager',
    'get_database_connection',
    'close_database_connection',
    'DatabaseManager',
    'Base',
    'ScrapedDocument',
    'ConversationHistory',
    'SystemMetrics',
    'CacheEntry',
    'VectorStore',
    'run_migrations',
    
    # Document schemas
    'DocumentType',
    'DocumentStatus',
    'DocumentMetadata',
    'Document',
    'DocumentChunk',
    'SearchResult',
    'SearchQuery',
    
    # Knowledge base schemas
    'KnowledgeBaseStatus',
    'UpdateStatus',
    'KnowledgeBaseInfo',
    'UpdateJob',
    'CategoryStats',
    'QualityMetrics',
    'SearchAnalytics',
    'SystemHealth',
    'BackupInfo',
    'ConfigurationSchema',
    
    # Utility functions
    'create_document_id',
    'extract_metadata_from_url',
    'create_knowledge_base_info',
    'create_update_job',
    'calculate_quality_score',
    'create_backup_info'
]
