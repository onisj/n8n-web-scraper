"""Knowledge Base Schema Definitions

Defines data structures for the knowledge base system
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class KnowledgeBaseStatus(str, Enum):
    """Knowledge base status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    UPDATING = "updating"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class UpdateStatus(str, Enum):
    """Update status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class KnowledgeBaseInfo(BaseModel):
    """Knowledge base information schema"""
    name: str = Field(..., description="Knowledge base name")
    version: str = Field(..., description="Knowledge base version")
    status: KnowledgeBaseStatus = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
    total_documents: int = Field(default=0, description="Total number of documents")
    total_chunks: int = Field(default=0, description="Total number of chunks")
    embedding_model: str = Field(..., description="Embedding model used")
    vector_dimensions: int = Field(..., description="Vector dimensions")
    supported_languages: List[str] = Field(default_factory=list, description="Supported languages")
    categories: List[str] = Field(default_factory=list, description="Available categories")
    tags: List[str] = Field(default_factory=list, description="Available tags")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UpdateJob(BaseModel):
    """Update job schema"""
    id: str = Field(..., description="Job identifier")
    status: UpdateStatus = Field(..., description="Job status")
    job_type: str = Field(..., description="Type of update job")
    started_at: datetime = Field(..., description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    progress: float = Field(default=0.0, description="Job progress (0-100)")
    total_items: int = Field(default=0, description="Total items to process")
    processed_items: int = Field(default=0, description="Items processed")
    failed_items: int = Field(default=0, description="Items that failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CategoryStats(BaseModel):
    """Category statistics schema"""
    name: str = Field(..., description="Category name")
    document_count: int = Field(..., description="Number of documents")
    last_updated: datetime = Field(..., description="Last update time")
    avg_quality_score: Optional[float] = Field(None, description="Average quality score")
    subcategories: List[str] = Field(default_factory=list, description="Subcategories")

class QualityMetrics(BaseModel):
    """Quality metrics schema"""
    completeness_score: float = Field(..., description="Completeness score (0-1)")
    freshness_score: float = Field(..., description="Freshness score (0-1)")
    accuracy_score: Optional[float] = Field(None, description="Accuracy score (0-1)")
    coverage_score: float = Field(..., description="Coverage score (0-1)")
    overall_score: float = Field(..., description="Overall quality score (0-1)")
    last_calculated: datetime = Field(..., description="Last calculation time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SearchAnalytics(BaseModel):
    """Search analytics schema"""
    total_searches: int = Field(default=0, description="Total number of searches")
    successful_searches: int = Field(default=0, description="Successful searches")
    failed_searches: int = Field(default=0, description="Failed searches")
    avg_response_time: float = Field(default=0.0, description="Average response time (ms)")
    popular_queries: List[str] = Field(default_factory=list, description="Popular search queries")
    popular_categories: List[str] = Field(default_factory=list, description="Popular categories")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SystemHealth(BaseModel):
    """System health schema"""
    status: str = Field(..., description="Overall system status")
    uptime: float = Field(..., description="System uptime in seconds")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    cpu_usage: float = Field(..., description="CPU usage percentage")
    vector_db_status: str = Field(..., description="Vector database status")
    api_status: str = Field(..., description="API status")
    last_backup: Optional[datetime] = Field(None, description="Last backup time")
    active_connections: int = Field(default=0, description="Active connections")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BackupInfo(BaseModel):
    """Backup information schema"""
    id: str = Field(..., description="Backup identifier")
    name: str = Field(..., description="Backup name")
    created_at: datetime = Field(..., description="Backup creation time")
    size_bytes: int = Field(..., description="Backup size in bytes")
    document_count: int = Field(..., description="Number of documents backed up")
    backup_type: str = Field(..., description="Type of backup (full, incremental)")
    file_path: str = Field(..., description="Backup file path")
    checksum: str = Field(..., description="Backup file checksum")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Backup metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConfigurationSchema(BaseModel):
    """System configuration schema"""
    embedding_model: str = Field(..., description="Embedding model name")
    vector_dimensions: int = Field(..., description="Vector dimensions")
    chunk_size: int = Field(default=1000, description="Document chunk size")
    chunk_overlap: int = Field(default=200, description="Chunk overlap size")
    max_documents: Optional[int] = Field(None, description="Maximum documents limit")
    update_frequency: str = Field(default="daily", description="Update frequency")
    quality_threshold: float = Field(default=0.7, description="Quality threshold")
    backup_retention_days: int = Field(default=30, description="Backup retention period")
    log_level: str = Field(default="INFO", description="Logging level")
    api_rate_limit: int = Field(default=100, description="API rate limit per minute")
    
# Utility functions

def create_knowledge_base_info(
    name: str,
    embedding_model: str,
    vector_dimensions: int
) -> KnowledgeBaseInfo:
    """Create knowledge base info with defaults"""
    return KnowledgeBaseInfo(
        name=name,
        version="1.0.0",
        status=KnowledgeBaseStatus.INITIALIZING,
        created_at=datetime.now(),
        last_updated=datetime.now(),
        embedding_model=embedding_model,
        vector_dimensions=vector_dimensions
    )

def create_update_job(job_type: str, total_items: int = 0) -> UpdateJob:
    """Create a new update job"""
    import uuid
    return UpdateJob(
        id=str(uuid.uuid4()),
        status=UpdateStatus.PENDING,
        job_type=job_type,
        started_at=datetime.now(),
        total_items=total_items
    )

def calculate_quality_score(
    completeness: float,
    freshness: float,
    coverage: float,
    accuracy: Optional[float] = None
) -> float:
    """Calculate overall quality score"""
    scores = [completeness, freshness, coverage]
    if accuracy is not None:
        scores.append(accuracy)
    
    return sum(scores) / len(scores)

def create_backup_info(
    name: str,
    file_path: str,
    size_bytes: int,
    document_count: int,
    backup_type: str = "full"
) -> BackupInfo:
    """Create backup information"""
    import uuid
    import hashlib
    
    # Generate checksum (simplified)
    checksum = hashlib.md5(f"{name}_{size_bytes}_{document_count}".encode()).hexdigest()
    
    return BackupInfo(
        id=str(uuid.uuid4()),
        name=name,
        created_at=datetime.now(),
        size_bytes=size_bytes,
        document_count=document_count,
        backup_type=backup_type,
        file_path=file_path,
        checksum=checksum
    )