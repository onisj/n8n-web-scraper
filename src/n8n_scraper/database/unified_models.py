"""Unified SQLAlchemy models for n8n scraper.

This module provides a unified data model that consolidates both documentation
and workflow data into a single, coherent structure while maintaining backward
compatibility through views and properties.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    JSON,
    Index,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Create declarative base
Base = declarative_base()


class TimestampMixin:
    """Mixin for adding timestamp columns."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )


class UnifiedDocument(Base, TimestampMixin):
    """Unified model for both documentation and workflow documents.
    
    This model consolidates scraped documentation and workflow files into
    a single table with type-specific fields that are nullable based on
    the document type.
    """
    
    __tablename__ = "unified_documents"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Document Type and Source
    document_type = Column(
        String(32), 
        nullable=False, 
        index=True,
        comment="Type of document: 'documentation' or 'workflow'"
    )
    source_type = Column(
        String(32), 
        nullable=False, 
        index=True,
        comment="Source of document: 'web_scrape', 'file_import', or 'api'"
    )
    
    # Common Identification Fields
    title = Column(String(1024), nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # URL/Path Information (unified)
    url = Column(Text, nullable=True, index=True, comment="For documentation")
    file_path = Column(String(1024), nullable=True, index=True, comment="For workflows")
    file_name = Column(String(256), nullable=True, index=True)
    
    # Categorization
    category = Column(String(128), nullable=True, index=True)
    subcategory = Column(String(128), nullable=True, index=True)
    tags = Column(JSONB, nullable=True, default=list)
    
    # Content Analysis
    word_count = Column(Integer, nullable=True)
    content_length = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True, default="en")
    
    # Workflow-specific fields (NULL for documentation)
    workflow_id = Column(String(128), nullable=True, index=True, comment="n8n workflow ID")
    workflow_data = Column(JSONB, nullable=True, comment="Full workflow JSON")
    version = Column(String(32), nullable=True)
    node_count = Column(Integer, nullable=True)
    connection_count = Column(Integer, nullable=True)
    trigger_types = Column(JSONB, nullable=True, default=list)
    node_types = Column(JSONB, nullable=True, default=list)
    integrations = Column(JSONB, nullable=True, default=list)
    
    # Documentation-specific fields (NULL for workflows)
    headings = Column(JSONB, nullable=True, default=list)
    links = Column(JSONB, nullable=True, default=list)
    code_blocks = Column(JSONB, nullable=True, default=list)
    images = Column(JSONB, nullable=True, default=list)
    headings_count = Column(Integer, nullable=True)
    links_count = Column(Integer, nullable=True)
    code_blocks_count = Column(Integer, nullable=True)
    images_count = Column(Integer, nullable=True)
    
    # Processing Status
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_error = Column(Text, nullable=True)
    
    # Quality Metrics
    quality_score = Column(Float, nullable=True)
    complexity_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    readability_score = Column(Float, nullable=True)
    
    # Metadata
    cache_metadata = Column('metadata', JSONB, nullable=True, default=dict)
    
    # Timestamps
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chunks = relationship("UnifiedChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('documentation', 'workflow')",
            name="ck_unified_documents_document_type"
        ),
        CheckConstraint(
            "source_type IN ('web_scrape', 'file_import', 'api')",
            name="ck_unified_documents_source_type"
        ),
        CheckConstraint("word_count >= 0", name="ck_unified_documents_word_count"),
        CheckConstraint("node_count >= 0", name="ck_unified_documents_node_count"),
        CheckConstraint("connection_count >= 0", name="ck_unified_documents_connection_count"),
        CheckConstraint(
            "quality_score >= 0 AND quality_score <= 1",
            name="ck_unified_documents_quality_score"
        ),
        CheckConstraint(
            "complexity_score >= 0 AND complexity_score <= 1",
            name="ck_unified_documents_complexity_score"
        ),
        CheckConstraint(
            "completeness_score >= 0 AND completeness_score <= 1",
            name="ck_unified_documents_completeness_score"
        ),
        CheckConstraint(
            "readability_score >= 0 AND readability_score <= 1",
            name="ck_unified_documents_readability_score"
        ),
        # Conditional constraints
        CheckConstraint(
            "(document_type = 'documentation' AND url IS NOT NULL) OR document_type = 'workflow'",
            name="ck_unified_documents_documentation_url"
        ),
        CheckConstraint(
            "(document_type = 'workflow' AND file_path IS NOT NULL) OR document_type = 'documentation'",
            name="ck_unified_documents_workflow_file_path"
        ),
        Index("idx_unified_documents_type_category", "document_type", "category"),
        Index("idx_unified_documents_processed_created", "is_processed", "created_at"),
    )
    
    # Validation methods
    @validates("document_type")
    def validate_document_type(self, key, document_type):
        """Validate document type."""
        valid_types = {"documentation", "workflow"}
        if document_type not in valid_types:
            raise ValueError(f"Document type must be one of: {valid_types}")
        return document_type
    
    @validates("source_type")
    def validate_source_type(self, key, source_type):
        """Validate source type."""
        valid_sources = {"web_scrape", "file_import", "api"}
        if source_type not in valid_sources:
            raise ValueError(f"Source type must be one of: {valid_sources}")
        return source_type
    
    @validates("title")
    def validate_title(self, key, title):
        """Validate title."""
        if not title or len(title.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if len(title) > 1024:
            raise ValueError("Title too long (max 1024 characters)")
        return title.strip()
    
    @validates("content")
    def validate_content(self, key, content):
        """Validate content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return content
    
    # Hybrid properties for backward compatibility
    @hybrid_property
    def name(self):
        """Alias for title (workflow compatibility)."""
        return self.title
    
    @name.setter
    def name(self, value):
        """Set title via name property."""
        self.title = value
    
    @hybrid_property
    def file_hash(self):
        """Alias for content_hash (workflow compatibility)."""
        return self.content_hash
    
    @file_hash.setter
    def file_hash(self, value):
        """Set content_hash via file_hash property."""
        self.content_hash = value
    
    @hybrid_property
    def summary(self):
        """Alias for description (documentation compatibility)."""
        return self.description
    
    @summary.setter
    def summary(self, value):
        """Set description via summary property."""
        self.description = value
    
    @property
    def meta_data(self):
        """Alias for metadata (documentation compatibility)."""
        return self.cache_metadata
    
    @meta_data.setter
    def meta_data(self, value):
        """Set metadata via meta_data property."""
        self.cache_metadata = value
    
    # Helper methods
    def is_documentation(self) -> bool:
        """Check if this is a documentation document."""
        return self.document_type == "documentation"
    
    def is_workflow(self) -> bool:
        """Check if this is a workflow document."""
        return self.document_type == "workflow"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base_dict = {
            "id": str(self.id),
            "document_type": self.document_type,
            "source_type": self.source_type,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "content_hash": self.content_hash,
            "url": self.url,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "word_count": self.word_count,
            "content_length": self.content_length,
            "language": self.language,
            "is_processed": self.is_processed,
            "processing_error": self.processing_error,
            "quality_score": self.quality_score,
            "complexity_score": self.complexity_score,
            "completeness_score": self.completeness_score,
            "readability_score": self.readability_score,
            "metadata": self.cache_metadata,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Add workflow-specific fields if applicable
        if self.is_workflow():
            base_dict.update({
                "workflow_id": self.workflow_id,
                "workflow_data": self.workflow_data,
                "version": self.version,
                "node_count": self.node_count,
                "connection_count": self.connection_count,
                "trigger_types": self.trigger_types,
                "node_types": self.node_types,
                "integrations": self.integrations,
            })
        
        # Add documentation-specific fields if applicable
        if self.is_documentation():
            base_dict.update({
                "headings": self.headings,
                "links": self.links,
                "code_blocks": self.code_blocks,
                "images": self.images,
                "headings_count": self.headings_count,
                "links_count": self.links_count,
                "code_blocks_count": self.code_blocks_count,
                "images_count": self.images_count,
            })
        
        return base_dict


class UnifiedChunk(Base, TimestampMixin):
    """Unified model for both documentation and workflow chunks.
    
    This model handles chunks for both documentation and workflows,
    with type-specific fields that are nullable based on the parent
    document type.
    """
    
    __tablename__ = "unified_chunks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to parent document
    document_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("unified_documents.id"), 
        nullable=False, 
        index=True
    )
    
    # Chunk Properties
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Position Information (for documentation chunks)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    # Workflow-specific chunk metadata (NULL for documentation)
    node_names = Column(JSONB, nullable=True, default=list)
    node_types = Column(JSONB, nullable=True, default=list)
    integrations = Column(JSONB, nullable=True, default=list)
    
    # Vector Embeddings
    embedding = Column(JSONB, nullable=True)
    embedding_model = Column(String(128), nullable=True)
    
    # Relationships
    document = relationship("UnifiedDocument", back_populates="chunks")
    
    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_unified_chunks_chunk_index"),
        CheckConstraint("word_count >= 0", name="ck_unified_chunks_word_count"),
        UniqueConstraint("document_id", "chunk_index", name="uq_unified_chunks_document_chunk"),
        Index("idx_unified_chunks_document_type", "document_id", "chunk_type"),
    )
    
    @validates("content")
    def validate_content(self, key, content):
        """Validate content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Chunk content cannot be empty")
        return content
    
    @validates("chunk_type")
    def validate_chunk_type(self, key, chunk_type):
        """Validate chunk type."""
        if not chunk_type or len(chunk_type.strip()) == 0:
            raise ValueError("Chunk type cannot be empty")
        return chunk_type.strip()
    
    # Hybrid properties for backward compatibility
    @hybrid_property
    def workflow_id(self):
        """Alias for document_id (workflow compatibility)."""
        return self.document_id
    
    @workflow_id.setter
    def workflow_id(self, value):
        """Set document_id via workflow_id property."""
        self.document_id = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "content": self.content,
            "content_hash": self.content_hash,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "word_count": self.word_count,
            "node_names": self.node_names,
            "node_types": self.node_types,
            "integrations": self.integrations,
            "embedding": self.embedding,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Keep existing models for other functionality
class ConversationHistory(Base, TimestampMixin):
    """Model for conversation history."""
    
    __tablename__ = "conversation_history"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Session Information
    session_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    
    # Conversation Content
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    
    # Context and Metadata
    context_documents = Column(JSONB, nullable=True, default=list)
    chunk_metadata = Column('metadata', JSONB, nullable=True, default=dict)
    
    # Performance Metrics
    response_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # User Feedback
    user_feedback = Column(String(20), nullable=True)
    relevance_score = Column(Float, nullable=True)
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("response_time_ms >= 0", name="ck_conversation_history_response_time"),
        CheckConstraint("token_count >= 0", name="ck_conversation_history_token_count"),
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="ck_conversation_history_relevance_score"
        ),
        CheckConstraint(
            "user_feedback IN ('positive', 'negative', 'neutral')",
            name="ck_conversation_history_feedback"
        ),
        Index("idx_conversation_history_session_created", "session_id", "created_at"),
    )
    
    @validates("user_message", "assistant_response")
    def validate_messages(self, key, message):
        """Validate messages."""
        if not message or len(message.strip()) == 0:
            raise ValueError(f"{key} cannot be empty")
        return message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "context_documents": self.context_documents,
            "metadata": self.metadata,
            "response_time_ms": self.response_time_ms,
            "token_count": self.token_count,
            "user_feedback": self.user_feedback,
            "relevance_score": self.relevance_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SystemMetrics(Base, TimestampMixin):
    """Model for system metrics."""
    
    __tablename__ = "system_metrics"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Metric Information
    metric_name = Column(String(128), nullable=False, index=True)
    metric_type = Column(String(32), nullable=False, index=True)
    
    # Metric Value
    value = Column(Float, nullable=False)
    
    # Metadata
    labels = Column(JSONB, nullable=True, default=dict)
    cache_metadata = Column('metadata', JSONB, nullable=True, default=dict)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=func.now())
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "metric_type IN ('counter', 'gauge', 'histogram')",
            name="ck_system_metrics_type"
        ),
        Index("idx_system_metrics_name_timestamp", "metric_name", "timestamp"),
    )
    
    @validates("metric_name")
    def validate_metric_name(self, key, name):
        """Validate metric name."""
        if not name or len(name.strip()) == 0:
            raise ValueError("Metric name cannot be empty")
        return name.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "labels": self.labels,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CacheEntry(Base, TimestampMixin):
    """Model for cache entries."""
    
    __tablename__ = "cache_entries"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Cache Key Information
    cache_key = Column(String(512), nullable=False, index=True)
    namespace = Column(String(128), nullable=False, index=True, default="default")
    
    # Cache Data
    data = Column(JSONB, nullable=False)
    
    # Cache Management
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Storage Information
    data_size_bytes = Column(Integer, nullable=True)
    compression_type = Column(String(32), nullable=True)
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("access_count >= 0", name="ck_cache_entries_access_count"),
        CheckConstraint("data_size_bytes >= 0", name="ck_cache_entries_data_size"),
        UniqueConstraint("cache_key", "namespace", name="uq_cache_entries_key_namespace"),
        Index("idx_cache_entries_key_namespace", "cache_key", "namespace"),
    )
    
    @validates("cache_key")
    def validate_cache_key(self, key, cache_key):
        """Validate cache key."""
        if not cache_key or len(cache_key.strip()) == 0:
            raise ValueError("Cache key cannot be empty")
        return cache_key.strip()
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def increment_access(self) -> None:
        """Increment access count and update last accessed time."""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "cache_key": self.cache_key,
            "namespace": self.namespace,
            "data": self.data,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "data_size_bytes": self.data_size_bytes,
            "compression_type": self.compression_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SearchQuery(Base, TimestampMixin):
    """Model for search queries."""
    
    __tablename__ = "search_queries"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Session Information
    session_id = Column(String(128), nullable=True, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    
    # Query Information
    query_text = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False, index=True)
    
    # Search Configuration
    search_type = Column(String(32), nullable=False, default="semantic")
    limit_results = Column(Integer, nullable=False, default=10)
    
    # Results Information
    results_count = Column(Integer, nullable=False, default=0)
    response_time_ms = Column(Integer, nullable=True)
    
    # User Interaction
    relevance_scores = Column(JSONB, nullable=True, default=list)
    user_clicked_results = Column(JSONB, nullable=True, default=list)
    user_satisfaction = Column(String(20), nullable=True)
    
    # Metadata
    search_metadata = Column('metadata', JSONB, nullable=True, default=dict)
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("results_count >= 0", name="ck_search_queries_results_count"),
        CheckConstraint("response_time_ms >= 0", name="ck_search_queries_response_time"),
        CheckConstraint("limit_results > 0", name="ck_search_queries_limit_results"),
        CheckConstraint(
            "search_type IN ('semantic', 'keyword', 'hybrid')",
            name="ck_search_queries_search_type"
        ),
        CheckConstraint(
            "user_satisfaction IN ('satisfied', 'neutral', 'unsatisfied')",
            name="ck_search_queries_satisfaction"
        ),
        Index("idx_search_queries_hash", "query_hash"),
    )
    
    @validates("query_text")
    def validate_query_text(self, key, query_text):
        """Validate query text."""
        if not query_text or len(query_text.strip()) == 0:
            raise ValueError("Query text cannot be empty")
        return query_text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query_text": self.query_text,
            "query_hash": self.query_hash,
            "search_type": self.search_type,
            "limit_results": self.limit_results,
            "results_count": self.results_count,
            "response_time_ms": self.response_time_ms,
            "relevance_scores": self.relevance_scores,
            "user_clicked_results": self.user_clicked_results,
            "user_satisfaction": self.user_satisfaction,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Backward compatibility aliases
# These allow existing code to continue working with the old model names
ScrapedDocument = UnifiedDocument
WorkflowDocument = UnifiedDocument
DocumentChunk = UnifiedChunk
WorkflowChunk = UnifiedChunk

# Export all models
__all__ = [
    "Base",
    "TimestampMixin",
    "UnifiedDocument",
    "UnifiedChunk",
    "ConversationHistory",
    "SystemMetrics",
    "CacheEntry",
    "SearchQuery",
    # Backward compatibility
    "ScrapedDocument",
    "WorkflowDocument",
    "DocumentChunk",
    "WorkflowChunk",
]