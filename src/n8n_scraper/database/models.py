"""
SQLAlchemy models for n8n scraper.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

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


class ScrapedDocument(Base, TimestampMixin):
    """Model for scraped documents."""
    
    __tablename__ = "scraped_documents"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Document identification
    url = Column(String(2048), nullable=False, index=True)
    title = Column(String(1024), nullable=True)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Metadata
    meta_data = Column(JSONB, nullable=True, default=dict)
    
    # Document properties
    word_count = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True, default="en")
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_error = Column(Text, nullable=True)
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)
    readability_score = Column(Float, nullable=True)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_scraped_documents_url_hash", "url", "content_hash"),
        Index("idx_scraped_documents_created_at", "created_at"),
        Index("idx_scraped_documents_processed", "is_processed", "created_at"),
        UniqueConstraint("url", "content_hash", name="uq_scraped_documents_url_hash"),
        CheckConstraint("word_count >= 0", name="ck_scraped_documents_word_count"),
        CheckConstraint("quality_score >= 0 AND quality_score <= 1", name="ck_scraped_documents_quality_score"),
    )
    
    @validates("url")
    def validate_url(self, key, url):
        """Validate URL format."""
        if not url or len(url.strip()) == 0:
            raise ValueError("URL cannot be empty")
        if len(url) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return url.strip()
    
    @validates("content")
    def validate_content(self, key, content):
        """Validate content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "url": self.url,
            "title": self.title,
            "content_hash": self.content_hash,
            "content": self.content,
            "summary": self.summary,
            "metadata": self.meta_data,
            "word_count": self.word_count,
            "language": self.language,
            "is_processed": self.is_processed,
            "processing_error": self.processing_error,
            "quality_score": self.quality_score,
            "readability_score": self.readability_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowDocument(Base, TimestampMixin):
    """Model for n8n workflow documents."""
    
    __tablename__ = "workflow_documents"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Workflow identification
    workflow_id = Column(String(128), nullable=True, index=True)  # n8n workflow ID if available
    name = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # File information
    file_path = Column(String(1024), nullable=False)
    file_name = Column(String(256), nullable=False, index=True)
    file_hash = Column(String(64), nullable=False, index=True)
    
    # Workflow content
    workflow_data = Column(JSONB, nullable=False)  # Full workflow JSON
    
    # Workflow metadata
    version = Column(String(32), nullable=True)
    tags = Column(JSONB, nullable=True, default=list)
    category = Column(String(128), nullable=True, index=True)
    
    # Workflow analysis
    node_count = Column(Integer, nullable=True)
    connection_count = Column(Integer, nullable=True)
    trigger_types = Column(JSONB, nullable=True, default=list)
    node_types = Column(JSONB, nullable=True, default=list)
    integrations = Column(JSONB, nullable=True, default=list)
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_error = Column(Text, nullable=True)
    
    # Quality metrics
    complexity_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    
    # Relationships
    chunks = relationship("WorkflowChunk", back_populates="workflow", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_workflow_documents_name", "name"),
        Index("idx_workflow_documents_category", "category"),
        Index("idx_workflow_documents_file_hash", "file_hash"),
        Index("idx_workflow_documents_processed", "is_processed", "created_at"),
        UniqueConstraint("file_path", name="uq_workflow_documents_file_path"),
        CheckConstraint("node_count >= 0", name="ck_workflow_documents_node_count"),
        CheckConstraint("connection_count >= 0", name="ck_workflow_documents_connection_count"),
        CheckConstraint("complexity_score >= 0 AND complexity_score <= 1", name="ck_workflow_documents_complexity_score"),
        CheckConstraint("completeness_score >= 0 AND completeness_score <= 1", name="ck_workflow_documents_completeness_score"),
    )
    
    @validates("name")
    def validate_name(self, key, name):
        """Validate workflow name."""
        if not name or len(name.strip()) == 0:
            raise ValueError("Workflow name cannot be empty")
        if len(name) > 512:
            raise ValueError("Workflow name too long (max 512 characters)")
        return name.strip()
    
    @validates("file_path")
    def validate_file_path(self, key, file_path):
        """Validate file path."""
        if not file_path or len(file_path.strip()) == 0:
            raise ValueError("File path cannot be empty")
        return file_path.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_hash": self.file_hash,
            "workflow_data": self.workflow_data,
            "version": self.version,
            "tags": self.tags,
            "category": self.category,
            "node_count": self.node_count,
            "connection_count": self.connection_count,
            "trigger_types": self.trigger_types,
            "node_types": self.node_types,
            "integrations": self.integrations,
            "is_processed": self.is_processed,
            "processing_error": self.processing_error,
            "complexity_score": self.complexity_score,
            "completeness_score": self.completeness_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowChunk(Base, TimestampMixin):
    """Model for workflow chunks used in vector search."""
    
    __tablename__ = "workflow_chunks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to workflow
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_documents.id"), nullable=False, index=True)
    
    # Chunk properties
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(64), nullable=False, index=True)  # description, nodes, connections, etc.
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Chunk metadata
    node_names = Column(JSONB, nullable=True, default=list)
    node_types = Column(JSONB, nullable=True, default=list)
    integrations = Column(JSONB, nullable=True, default=list)
    
    # Vector embedding (stored as JSON for compatibility)
    embedding = Column(JSONB, nullable=True)
    embedding_model = Column(String(128), nullable=True)
    
    # Relationships
    workflow = relationship("WorkflowDocument", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index("idx_workflow_chunks_workflow_id", "workflow_id"),
        Index("idx_workflow_chunks_workflow_chunk", "workflow_id", "chunk_index"),
        Index("idx_workflow_chunks_type", "chunk_type"),
        UniqueConstraint("workflow_id", "chunk_index", name="uq_workflow_chunks_workflow_chunk"),
        CheckConstraint("chunk_index >= 0", name="ck_workflow_chunks_chunk_index"),
    )
    
    @validates("content")
    def validate_content(self, key, content):
        """Validate chunk content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Chunk content cannot be empty")
        return content
    
    @validates("chunk_type")
    def validate_chunk_type(self, key, chunk_type):
        """Validate chunk type."""
        valid_types = ["description", "nodes", "connections", "settings", "variables", "credentials"]
        if chunk_type not in valid_types:
            raise ValueError(f"Invalid chunk type. Must be one of: {valid_types}")
        return chunk_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "content": self.content,
            "content_hash": self.content_hash,
            "node_names": self.node_names,
            "node_types": self.node_types,
            "integrations": self.integrations,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentChunk(Base, TimestampMixin):
    """Model for document chunks used in vector search."""
    
    __tablename__ = "document_chunks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to document
    document_id = Column(UUID(as_uuid=True), ForeignKey("scraped_documents.id"), nullable=False, index=True)
    
    # Chunk properties
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Chunk metadata
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    # Vector embedding (stored as JSON for compatibility)
    embedding = Column(JSONB, nullable=True)
    embedding_model = Column(String(128), nullable=True)
    
    # Relationships
    document = relationship("ScrapedDocument", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index("idx_document_chunks_document_id", "document_id"),
        Index("idx_document_chunks_document_chunk", "document_id", "chunk_index"),
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk"),
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
        CheckConstraint("word_count >= 0", name="ck_document_chunks_word_count"),
    )
    
    @validates("content")
    def validate_content(self, key, content):
        """Validate chunk content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Chunk content cannot be empty")
        return content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "content": self.content,
            "content_hash": self.content_hash,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "word_count": self.word_count,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationHistory(Base, TimestampMixin):
    """Model for storing conversation history."""
    
    __tablename__ = "conversation_history"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Session identification
    session_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    
    # Message content
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    
    # Context and metadata
    context_documents = Column(JSONB, nullable=True, default=list)
    meta_data = Column(JSONB, nullable=True, default=dict)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # Quality metrics
    user_feedback = Column(String(20), nullable=True)  # positive, negative, neutral
    relevance_score = Column(Float, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_conversation_history_session", "session_id", "created_at"),
        Index("idx_conversation_history_user", "user_id", "created_at"),
        Index("idx_conversation_history_feedback", "user_feedback"),
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
    )
    
    @validates("user_message", "assistant_response")
    def validate_messages(self, key, message):
        """Validate message content."""
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
            "metadata": self.meta_data,
            "response_time_ms": self.response_time_ms,
            "token_count": self.token_count,
            "user_feedback": self.user_feedback,
            "relevance_score": self.relevance_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SystemMetrics(Base, TimestampMixin):
    """Model for storing system performance metrics."""
    
    __tablename__ = "system_metrics"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Metric identification
    metric_name = Column(String(128), nullable=False, index=True)
    metric_type = Column(String(32), nullable=False, index=True)  # counter, gauge, histogram
    
    # Metric value
    value = Column(Float, nullable=False)
    
    # Labels and metadata
    labels = Column(JSONB, nullable=True, default=dict)
    meta_data = Column(JSONB, nullable=True, default=dict)
    
    # Timestamp (for time-series data)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_system_metrics_name_timestamp", "metric_name", "timestamp"),
        Index("idx_system_metrics_type_timestamp", "metric_type", "timestamp"),
        Index("idx_system_metrics_timestamp", "timestamp"),
        CheckConstraint(
            "metric_type IN ('counter', 'gauge', 'histogram')",
            name="ck_system_metrics_type"
        ),
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
            "metadata": self.meta_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CacheEntry(Base, TimestampMixin):
    """Model for caching frequently accessed data."""
    
    __tablename__ = "cache_entries"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Cache key and namespace
    cache_key = Column(String(512), nullable=False, index=True)
    namespace = Column(String(128), nullable=False, index=True, default="default")
    
    # Cached data
    data = Column(JSONB, nullable=False)
    
    # Cache metadata
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Data properties
    data_size_bytes = Column(Integer, nullable=True)
    compression_type = Column(String(32), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_cache_entries_key_namespace", "cache_key", "namespace"),
        Index("idx_cache_entries_expires_at", "expires_at"),
        Index("idx_cache_entries_namespace", "namespace"),
        UniqueConstraint("cache_key", "namespace", name="uq_cache_entries_key_namespace"),
        CheckConstraint("access_count >= 0", name="ck_cache_entries_access_count"),
        CheckConstraint("data_size_bytes >= 0", name="ck_cache_entries_data_size"),
    )
    
    @validates("cache_key")
    def validate_cache_key(self, key, cache_key):
        """Validate cache key."""
        if not cache_key or len(cache_key.strip()) == 0:
            raise ValueError("Cache key cannot be empty")
        if len(cache_key) > 512:
            raise ValueError("Cache key too long (max 512 characters)")
        return cache_key.strip()
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
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
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SearchQuery(Base, TimestampMixin):
    """Model for tracking search queries and analytics."""
    
    __tablename__ = "search_queries"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Query identification
    session_id = Column(String(128), nullable=True, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    
    # Query content
    query_text = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False, index=True)
    
    # Search parameters
    search_type = Column(String(32), nullable=False, default="semantic")  # semantic, keyword, hybrid
    limit_results = Column(Integer, nullable=False, default=10)
    
    # Results and performance
    results_count = Column(Integer, nullable=False, default=0)
    response_time_ms = Column(Integer, nullable=True)
    
    # Quality metrics
    relevance_scores = Column(JSONB, nullable=True, default=list)
    user_clicked_results = Column(JSONB, nullable=True, default=list)
    user_satisfaction = Column(String(20), nullable=True)  # satisfied, neutral, unsatisfied
    
    # Metadata
    meta_data = Column(JSONB, nullable=True, default=dict)
    
    # Indexes
    __table_args__ = (
        Index("idx_search_queries_hash", "query_hash"),
        Index("idx_search_queries_session", "session_id", "created_at"),
        Index("idx_search_queries_user", "user_id", "created_at"),
        Index("idx_search_queries_type", "search_type"),
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
    )
    
    @validates("query_text")
    def validate_query_text(self, key, query_text):
        """Validate query text."""
        if not query_text or len(query_text.strip()) == 0:
            raise ValueError("Query text cannot be empty")
        return query_text.strip()
    
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
            "metadata": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }