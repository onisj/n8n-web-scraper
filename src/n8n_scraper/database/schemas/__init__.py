"""Database Schemas Package

Provides data models and schemas for the n8n AI Knowledge System
"""

from .document import (
    DocumentType,
    DocumentStatus,
    DocumentMetadata,
    Document,
    DocumentChunk,
    SearchResult,
    SearchQuery,
    validate_document_metadata,
    document_to_dict,
    dict_to_document,
    create_document_id,
    extract_metadata_from_url
)

from .knowledge_base import (
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
    create_knowledge_base_info,
    create_update_job,
    calculate_quality_score,
    create_backup_info
)

__all__ = [
    # Document schemas
    "DocumentType",
    "DocumentStatus",
    "DocumentMetadata",
    "Document",
    "DocumentChunk",
    "SearchResult",
    "SearchQuery",
    "validate_document_metadata",
    "document_to_dict",
    "dict_to_document",
    "create_document_id",
    "extract_metadata_from_url",
    
    # Knowledge base schemas
    "KnowledgeBaseStatus",
    "UpdateStatus",
    "KnowledgeBaseInfo",
    "UpdateJob",
    "CategoryStats",
    "QualityMetrics",
    "SearchAnalytics",
    "SystemHealth",
    "BackupInfo",
    "ConfigurationSchema",
    "create_knowledge_base_info",
    "create_update_job",
    "calculate_quality_score",
    "create_backup_info"
]