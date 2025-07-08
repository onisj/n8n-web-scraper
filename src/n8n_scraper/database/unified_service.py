#!/usr/bin/env python3
"""
Unified database service for consolidated schema operations.

This service provides high-level operations for the unified schema,
handling both documentation and workflow data through a single interface.
"""

import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from uuid import uuid4
from pathlib import Path

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .unified_models import (
    UnifiedDocument,
    UnifiedChunk,
    ConversationHistory,
    SystemMetrics,
    CacheEntry,
    SearchQuery
)
from .connection import get_async_session
from ..core.logging_config import get_logger
from ..core.exceptions import DatabaseError

logger = get_logger(__name__)


class UnifiedDatabaseService:
    """Service for unified database operations."""
    
    def __init__(self):
        self.logger = logger
    
    async def create_document(
        self,
        document_type: str,
        source_type: str,
        title: str,
        content: str,
        **kwargs
    ) -> UnifiedDocument:
        """Create a new document in the unified schema.
        
        Args:
            document_type: 'documentation' or 'workflow'
            source_type: 'web_scrape', 'file_import', etc.
            title: Document title
            content: Document content
            **kwargs: Additional document fields
        
        Returns:
            Created UnifiedDocument instance
        """
        async with get_async_session() as session:
            try:
                # Generate content hash
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                # Create document
                document = UnifiedDocument(
                    id=str(uuid4()),
                    document_type=document_type,
                    source_type=source_type,
                    title=title,
                    content=content,
                    content_hash=content_hash,
                    word_count=len(content.split()),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    **kwargs
                )
                
                session.add(document)
                await session.commit()
                await session.refresh(document)
                
                self.logger.info(f"Created {document_type} document: {document.id}")
                return document
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to create document: {e}")
                raise DatabaseError(f"Failed to create document: {str(e)}")
    
    async def get_document_by_id(self, document_id: str) -> Optional[UnifiedDocument]:
        """Get a document by its ID."""
        async with get_async_session() as session:
            try:
                result = await session.execute(
                    select(UnifiedDocument)
                    .options(selectinload(UnifiedDocument.chunks))
                    .where(UnifiedDocument.id == document_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                self.logger.error(f"Failed to get document {document_id}: {e}")
                raise DatabaseError(f"Failed to get document: {str(e)}")
    
    async def search_documents(
        self,
        query: str,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UnifiedDocument]:
        """Search documents using full-text search.
        
        Args:
            query: Search query
            document_type: Filter by document type
            category: Filter by category
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of matching documents
        """
        async with get_async_session() as session:
            try:
                # Build search query
                stmt = select(UnifiedDocument)
                
                # Add filters
                conditions = []
                
                if query:
                    # Use PostgreSQL full-text search
                    conditions.append(
                        or_(
                            UnifiedDocument.title.ilike(f"%{query}%"),
                            UnifiedDocument.content.ilike(f"%{query}%"),
                            UnifiedDocument.description.ilike(f"%{query}%")
                        )
                    )
                
                if document_type:
                    conditions.append(UnifiedDocument.document_type == document_type)
                
                if category:
                    conditions.append(UnifiedDocument.category == category)
                
                if conditions:
                    stmt = stmt.where(and_(*conditions))
                
                # Add ordering and pagination
                stmt = stmt.order_by(UnifiedDocument.updated_at.desc())
                stmt = stmt.offset(offset).limit(limit)
                
                result = await session.execute(stmt)
                documents = result.scalars().all()
                
                # Log search query
                await self._log_search_query(session, query, len(documents))
                
                return list(documents)
                
            except Exception as e:
                self.logger.error(f"Failed to search documents: {e}")
                raise DatabaseError(f"Failed to search documents: {str(e)}")
    
    async def get_documents_by_type(
        self,
        document_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[UnifiedDocument]:
        """Get documents by type with pagination."""
        async with get_async_session() as session:
            try:
                stmt = (
                    select(UnifiedDocument)
                    .where(UnifiedDocument.document_type == document_type)
                    .order_by(UnifiedDocument.updated_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                return list(result.scalars().all())
                
            except Exception as e:
                self.logger.error(f"Failed to get documents by type {document_type}: {e}")
                raise DatabaseError(f"Failed to get documents by type: {str(e)}")
    
    async def get_workflow_by_file_path(self, file_path: str) -> Optional[UnifiedDocument]:
        """Get a workflow document by its file path."""
        async with get_async_session() as session:
            try:
                result = await session.execute(
                    select(UnifiedDocument)
                    .where(
                        and_(
                            UnifiedDocument.document_type == 'workflow',
                            UnifiedDocument.file_path == file_path
                        )
                    )
                )
                return result.scalar_one_or_none()
            except Exception as e:
                self.logger.error(f"Failed to get workflow by file path {file_path}: {e}")
                raise DatabaseError(f"Failed to get workflow: {str(e)}")
    
    async def update_document(
        self,
        document_id: str,
        **updates
    ) -> Optional[UnifiedDocument]:
        """Update a document with new data."""
        async with get_async_session() as session:
            try:
                # Get existing document
                result = await session.execute(
                    select(UnifiedDocument).where(UnifiedDocument.id == document_id)
                )
                document = result.scalar_one_or_none()
                
                if not document:
                    return None
                
                # Update fields
                for key, value in updates.items():
                    if hasattr(document, key):
                        setattr(document, key, value)
                
                # Update content hash if content changed
                if 'content' in updates:
                    document.content_hash = hashlib.md5(
                        updates['content'].encode('utf-8')
                    ).hexdigest()
                    document.word_count = len(updates['content'].split())
                    document.content_length = len(updates['content'])
                
                document.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(document)
                
                self.logger.info(f"Updated document: {document_id}")
                return document
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to update document {document_id}: {e}")
                raise DatabaseError(f"Failed to update document: {str(e)}")
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its associated chunks."""
        async with get_async_session() as session:
            try:
                # Get document
                result = await session.execute(
                    select(UnifiedDocument).where(UnifiedDocument.id == document_id)
                )
                document = result.scalar_one_or_none()
                
                if not document:
                    return False
                
                # Delete associated chunks first
                await session.execute(
                    text("DELETE FROM unified_chunks WHERE document_id = :doc_id"),
                    {"doc_id": document_id}
                )
                
                # Delete document
                await session.delete(document)
                await session.commit()
                
                self.logger.info(f"Deleted document: {document_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to delete document {document_id}: {e}")
                raise DatabaseError(f"Failed to delete document: {str(e)}")
    
    async def create_chunk(
        self,
        document_id: str,
        content: str,
        chunk_index: int,
        embedding: Optional[List[float]] = None,
        **kwargs
    ) -> UnifiedChunk:
        """Create a chunk for a document."""
        async with get_async_session() as session:
            try:
                # Generate content hash
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                chunk = UnifiedChunk(
                    id=str(uuid4()),
                    document_id=document_id,
                    content=content,
                    chunk_index=chunk_index,
                    chunk_type=kwargs.get('chunk_type', 'text'),
                    content_hash=content_hash,
                    word_count=len(content.split()),
                    embedding=embedding,
                    created_at=datetime.utcnow(),
                    **{k: v for k, v in kwargs.items() if k != 'chunk_type'}
                )
                
                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)
                
                return chunk
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to create chunk for document {document_id}: {e}")
                raise DatabaseError(f"Failed to create chunk: {str(e)}")
    
    async def get_document_chunks(self, document_id: str) -> List[UnifiedChunk]:
        """Get all chunks for a document."""
        async with get_async_session() as session:
            try:
                result = await session.execute(
                    select(UnifiedChunk)
                    .where(UnifiedChunk.document_id == document_id)
                    .order_by(UnifiedChunk.chunk_index)
                )
                return list(result.scalars().all())
            except Exception as e:
                self.logger.error(f"Failed to get chunks for document {document_id}: {e}")
                raise DatabaseError(f"Failed to get chunks: {str(e)}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        async with get_async_session() as session:
            try:
                # Total documents
                total_docs = await session.execute(
                    select(func.count(UnifiedDocument.id))
                )
                total_count = total_docs.scalar()
                
                # Documents by type
                type_stats = await session.execute(
                    select(
                        UnifiedDocument.document_type,
                        func.count(UnifiedDocument.id)
                    ).group_by(UnifiedDocument.document_type)
                )
                
                # Documents by category
                category_stats = await session.execute(
                    select(
                        UnifiedDocument.category,
                        func.count(UnifiedDocument.id)
                    ).group_by(UnifiedDocument.category)
                )
                
                # Total chunks
                total_chunks = await session.execute(
                    select(func.count(UnifiedChunk.id))
                )
                chunks_count = total_chunks.scalar()
                
                return {
                    "total_documents": total_count,
                    "total_chunks": chunks_count,
                    "documents_by_type": dict(type_stats.all()),
                    "documents_by_category": dict(category_stats.all()),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Failed to get statistics: {e}")
                raise DatabaseError(f"Failed to get statistics: {str(e)}")
    
    async def import_workflow_file(self, file_path: Path) -> Optional[UnifiedDocument]:
        """Import a workflow JSON file into the unified schema."""
        try:
            if not file_path.exists():
                self.logger.error(f"Workflow file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Extract workflow information
            workflow_name = workflow_data.get('name', file_path.stem)
            workflow_id = workflow_data.get('id')
            description = workflow_data.get('description', '')
            
            # Create content from workflow data
            content_parts = []
            if workflow_name:
                content_parts.append(f"Workflow: {workflow_name}")
            if description:
                content_parts.append(f"Description: {description}")
            
            # Add node information
            nodes = workflow_data.get('nodes', [])
            if nodes:
                content_parts.append(f"Nodes ({len(nodes)}):")
                for node in nodes:
                    node_name = node.get('name', 'Unnamed Node')
                    node_type = node.get('type', 'Unknown')
                    content_parts.append(f"- {node_name} ({node_type})")
            
            content = "\n".join(content_parts)
            
            # Analyze workflow
            node_count = len(nodes)
            node_types = list(set(node.get('type', 'Unknown') for node in nodes))
            
            # Extract integrations (node types that aren't built-in)
            builtin_types = {'Start', 'Set', 'IF', 'Switch', 'Merge', 'NoOp', 'Function', 'FunctionItem'}
            integrations = [nt for nt in node_types if nt not in builtin_types]
            
            # Count connections
            connections = workflow_data.get('connections', {})
            connection_count = sum(len(conns) for conns in connections.values()) if connections else 0
            
            # Determine trigger types
            trigger_types = []
            for node in nodes:
                if node.get('type') in ['Trigger', 'Webhook', 'Cron', 'Manual Trigger']:
                    trigger_types.append(node.get('type'))
            
            # Calculate complexity score (simple heuristic)
            complexity_score = min(1.0, (node_count + connection_count) / 100.0)
            
            # Check if workflow already exists
            existing = await self.get_workflow_by_file_path(str(file_path))
            
            if existing:
                # Update existing workflow
                return await self.update_document(
                    existing.id,
                    title=workflow_name,
                    description=description,
                    content=content,
                    workflow_data=workflow_data,
                    node_count=node_count,
                    connection_count=connection_count,
                    trigger_types=trigger_types,
                    node_types=node_types,
                    integrations=integrations,
                    complexity_score=complexity_score,
                    metadata={
                        'file_size': file_path.stat().st_size,
                        'file_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                )
            else:
                # Create new workflow document
                return await self.create_document(
                    document_type='workflow',
                    source_type='file_import',
                    title=workflow_name,
                    content=content,
                    description=description,
                    file_path=str(file_path),
                    file_name=file_path.name,
                    category='workflow',
                    workflow_id=workflow_id,
                    workflow_data=workflow_data,
                    node_count=node_count,
                    connection_count=connection_count,
                    trigger_types=trigger_types,
                    node_types=node_types,
                    integrations=integrations,
                    complexity_score=complexity_score,
                    metadata={
                        'file_size': file_path.stat().st_size,
                        'file_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Failed to import workflow file {file_path}: {e}")
            raise DatabaseError(f"Failed to import workflow: {str(e)}")
    
    async def _log_search_query(
        self,
        session: AsyncSession,
        query: str,
        results_count: int
    ) -> None:
        """Log a search query for analytics."""
        try:
            search_log = SearchQuery(
                id=str(uuid4()),
                query=query,
                results_count=results_count,
                created_at=datetime.utcnow()
            )
            session.add(search_log)
            # Don't commit here, let the parent transaction handle it
        except Exception as e:
            self.logger.warning(f"Failed to log search query: {e}")


# Global service instance
unified_db_service = UnifiedDatabaseService()