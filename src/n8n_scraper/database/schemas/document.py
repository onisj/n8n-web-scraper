from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class DocumentType(str, Enum):
    """Document type enumeration"""
    NODE_DOCS = "node_docs"
    WORKFLOW = "workflow"
    TUTORIAL = "tutorial"
    FAQ = "faq"
    COMMUNITY = "community"
    CHANGELOG = "changelog"
    API_DOCS = "api_docs"
    INTEGRATION = "integration"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICE = "best_practice"

class DocumentStatus(str, Enum):
    """Document status enumeration"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    DEPRECATED = "deprecated"

class DocumentMetadata(BaseModel):
    """Document metadata schema"""
    title: str = Field(..., description="Document title")
    url: str = Field(..., description="Source URL")
    doc_type: DocumentType = Field(..., description="Type of document")
    status: DocumentStatus = Field(default=DocumentStatus.ACTIVE, description="Document status")
    category: Optional[str] = Field(None, description="Document category")
    subcategory: Optional[str] = Field(None, description="Document subcategory")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    language: str = Field(default="en", description="Document language")
    version: Optional[str] = Field(None, description="Document version")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Scraping timestamp")
    content_hash: Optional[str] = Field(None, description="Content hash for change detection")
    word_count: Optional[int] = Field(None, description="Word count")
    reading_time: Optional[int] = Field(None, description="Estimated reading time in minutes")
    difficulty_level: Optional[str] = Field(None, description="Difficulty level (beginner, intermediate, advanced)")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")
    related_nodes: List[str] = Field(default_factory=list, description="Related n8n nodes")
    author: Optional[str] = Field(None, description="Document author")
    source: str = Field(default="n8n_docs", description="Source system")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Document(BaseModel):
    """Complete document schema"""
    id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document content")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    embedding: Optional[List[float]] = Field(None, description="Document embedding vector")
    chunks: Optional[List[str]] = Field(None, description="Document chunks for processing")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DocumentChunk(BaseModel):
    """Document chunk schema for processing large documents"""
    id: str = Field(..., description="Chunk identifier")
    document_id: str = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Chunk position in document")
    start_char: int = Field(..., description="Start character position")
    end_char: int = Field(..., description="End character position")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk-specific metadata")
    embedding: Optional[List[float]] = Field(None, description="Chunk embedding vector")

class SearchResult(BaseModel):
    """Search result schema"""
    document: Document = Field(..., description="Found document")
    score: float = Field(..., description="Relevance score")
    distance: float = Field(..., description="Vector distance")
    highlights: List[str] = Field(default_factory=list, description="Content highlights")

class SearchQuery(BaseModel):
    """Search query schema"""
    query: str = Field(..., description="Search query text")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    limit: int = Field(default=10, description="Maximum results")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    doc_types: Optional[List[DocumentType]] = Field(None, description="Filter by document types")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    min_score: Optional[float] = Field(None, description="Minimum relevance score")

# Utility functions for schema validation and conversion

def validate_document_metadata(metadata: Dict[str, Any]) -> DocumentMetadata:
    """Validate and convert dictionary to DocumentMetadata"""
    return DocumentMetadata(**metadata)

def document_to_dict(document: Document) -> Dict[str, Any]:
    """Convert Document to dictionary for storage"""
    return document.dict()

def dict_to_document(data: Dict[str, Any]) -> Document:
    """Convert dictionary to Document"""
    return Document(**data)

def create_document_id(url: str, doc_type: DocumentType) -> str:
    """Create a unique document ID"""
    import hashlib
    content = f"{url}_{doc_type.value}"
    return hashlib.md5(content.encode()).hexdigest()

def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    """Extract metadata from URL patterns"""
    metadata = {
        "url": url,
        "source": "n8n_docs"
    }
    
    # Extract category from URL patterns
    if "/nodes/" in url:
        metadata["doc_type"] = DocumentType.NODE_DOCS
        metadata["category"] = "nodes"
    elif "/workflows/" in url:
        metadata["doc_type"] = DocumentType.WORKFLOW
        metadata["category"] = "workflows"
    elif "/tutorials/" in url:
        metadata["doc_type"] = DocumentType.TUTORIAL
        metadata["category"] = "tutorials"
    elif "/integrations/" in url:
        metadata["doc_type"] = DocumentType.INTEGRATION
        metadata["category"] = "integrations"
    elif "/api/" in url:
        metadata["doc_type"] = DocumentType.API_DOCS
        metadata["category"] = "api"
    else:
        metadata["doc_type"] = DocumentType.NODE_DOCS
        metadata["category"] = "general"
    
    return metadata