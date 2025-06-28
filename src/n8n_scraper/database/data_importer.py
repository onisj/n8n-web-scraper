"""
Data Import Module for migrating scraped data and workflows to PostgreSQL.

This module provides functionality to import:
1. Scraped n8n documentation from JSON files
2. n8n workflow files from JSON format
3. Generate embeddings and chunks for vector search
"""

import json
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.logging_config import get_logger
from ..database.connection import get_sync_session
from ..database.models import (
    ScrapedDocument, DocumentChunk, WorkflowDocument, WorkflowChunk
)
from ..ai.embeddings import EmbeddingService
from ..utils.text_processing import TextProcessor

logger = get_logger(__name__)


class DataImporter:
    """Handles importing scraped data and workflows into PostgreSQL."""
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """Initialize the data importer.
        
        Args:
            embedding_service: Service for generating embeddings
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.text_processor = TextProcessor()
        self.session: Optional[Session] = None
        
    def __enter__(self):
        """Context manager entry."""
        self.session = get_sync_session()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()
    
    def import_scraped_documents(self, data_dir: str) -> Dict[str, Any]:
        """Import scraped documentation from JSON files.
        
        Args:
            data_dir: Directory containing scraped JSON files
            
        Returns:
            Dict with import statistics
        """
        logger.info(f"Starting import of scraped documents from {data_dir}")
        
        stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "error_files": 0,
            "total_documents": 0,
            "total_chunks": 0,
            "errors": []
        }
        
        data_path = Path(data_dir)
        if not data_path.exists():
            raise ValueError(f"Data directory does not exist: {data_dir}")
        
        # Find all JSON files
        json_files = list(data_path.glob("**/*.json"))
        stats["total_files"] = len(json_files)
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        for file_path in json_files:
            try:
                result = self._import_scraped_document_file(file_path)
                if result["success"]:
                    stats["processed_files"] += 1
                    stats["total_documents"] += result["documents"]
                    stats["total_chunks"] += result["chunks"]
                else:
                    if result["skipped"]:
                        stats["skipped_files"] += 1
                    else:
                        stats["error_files"] += 1
                        stats["errors"].append({
                            "file": str(file_path),
                            "error": result["error"]
                        })
                        
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                stats["error_files"] += 1
                stats["errors"].append({
                    "file": str(file_path),
                    "error": str(e)
                })
        
        logger.info(f"Scraped documents import completed: {stats}")
        return stats
    
    def _import_scraped_document_file(self, file_path: Path) -> Dict[str, Any]:
        """Import a single scraped document file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dict with import result
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract document information
            url = data.get('url', str(file_path))
            title = data.get('title', file_path.stem)
            content = data.get('content', '')
            metadata = data.get('metadata', {})
            
            if not content or len(content.strip()) == 0:
                return {"success": False, "skipped": True, "error": "Empty content"}
            
            # Generate content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Check if document already exists
            existing = self.session.query(ScrapedDocument).filter_by(
                url=url, content_hash=content_hash
            ).first()
            
            if existing:
                return {"success": False, "skipped": True, "error": "Document already exists"}
            
            # Create document
            document = ScrapedDocument(
                url=url,
                title=title,
                content=content,
                content_hash=content_hash,
                meta_data=metadata,
                word_count=len(content.split()),
                language=metadata.get('language', 'en')
            )
            
            self.session.add(document)
            self.session.flush()  # Get the ID
            
            # Generate chunks
            chunks = self._create_document_chunks(document, content)
            chunk_count = len(chunks)
            
            # Mark as processed
            document.is_processed = True
            
            return {
                "success": True,
                "skipped": False,
                "documents": 1,
                "chunks": chunk_count
            }
            
        except Exception as e:
            logger.error(f"Error importing document {file_path}: {e}")
            return {"success": False, "skipped": False, "error": str(e)}
    
    def import_workflows(self, workflows_dir: str) -> Dict[str, Any]:
        """Import n8n workflows from JSON files.
        
        Args:
            workflows_dir: Directory containing workflow JSON files
            
        Returns:
            Dict with import statistics
        """
        logger.info(f"Starting import of workflows from {workflows_dir}")
        
        stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "error_files": 0,
            "total_workflows": 0,
            "total_chunks": 0,
            "errors": []
        }
        
        workflows_path = Path(workflows_dir)
        if not workflows_path.exists():
            raise ValueError(f"Workflows directory does not exist: {workflows_dir}")
        
        # Find all JSON files
        json_files = list(workflows_path.glob("**/*.json"))
        stats["total_files"] = len(json_files)
        
        logger.info(f"Found {len(json_files)} workflow files to process")
        
        for file_path in json_files:
            try:
                result = self._import_workflow_file(file_path)
                if result["success"]:
                    stats["processed_files"] += 1
                    stats["total_workflows"] += result["workflows"]
                    stats["total_chunks"] += result["chunks"]
                else:
                    if result["skipped"]:
                        stats["skipped_files"] += 1
                    else:
                        stats["error_files"] += 1
                        stats["errors"].append({
                            "file": str(file_path),
                            "error": result["error"]
                        })
                        
            except Exception as e:
                logger.error(f"Error processing workflow file {file_path}: {e}")
                stats["error_files"] += 1
                stats["errors"].append({
                    "file": str(file_path),
                    "error": str(e)
                })
        
        logger.info(f"Workflows import completed: {stats}")
        return stats
    
    def _import_workflow_file(self, file_path: Path) -> Dict[str, Any]:
        """Import a single workflow file.
        
        Args:
            file_path: Path to the workflow JSON file
            
        Returns:
            Dict with import result
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Extract workflow information
            workflow_id = workflow_data.get('id')
            name = workflow_data.get('name', file_path.stem)
            description = workflow_data.get('description', '')
            
            # Generate file hash
            file_content = json.dumps(workflow_data, sort_keys=True)
            file_hash = hashlib.sha256(file_content.encode()).hexdigest()
            
            # Check if workflow already exists
            existing = self.session.query(WorkflowDocument).filter_by(
                file_path=str(file_path)
            ).first()
            
            if existing:
                return {"success": False, "skipped": True, "error": "Workflow already exists"}
            
            # Analyze workflow
            analysis = self._analyze_workflow(workflow_data)
            
            # Create workflow document
            workflow = WorkflowDocument(
                workflow_id=workflow_id,
                name=name,
                description=description,
                file_path=str(file_path),
                file_name=file_path.name,
                file_hash=file_hash,
                workflow_data=workflow_data,
                version=workflow_data.get('version'),
                tags=workflow_data.get('tags', []),
                category=self._categorize_workflow(workflow_data, analysis),
                node_count=analysis['node_count'],
                connection_count=analysis['connection_count'],
                trigger_types=analysis['trigger_types'],
                node_types=analysis['node_types'],
                integrations=analysis['integrations'],
                complexity_score=analysis['complexity_score'],
                completeness_score=analysis['completeness_score']
            )
            
            self.session.add(workflow)
            self.session.flush()  # Get the ID
            
            # Generate chunks
            chunks = self._create_workflow_chunks(workflow, workflow_data, analysis)
            chunk_count = len(chunks)
            
            # Mark as processed
            workflow.is_processed = True
            
            return {
                "success": True,
                "skipped": False,
                "workflows": 1,
                "chunks": chunk_count
            }
            
        except Exception as e:
            logger.error(f"Error importing workflow {file_path}: {e}")
            return {"success": False, "skipped": False, "error": str(e)}
    
    def _create_document_chunks(self, document: ScrapedDocument, content: str) -> List[DocumentChunk]:
        """Create chunks for a document.
        
        Args:
            document: The document to chunk
            content: Document content
            
        Returns:
            List of created chunks
        """
        chunks = []
        
        # Split content into chunks
        text_chunks = self.text_processor.split_text(content, chunk_size=1000, overlap=200)
        
        for i, chunk_text in enumerate(text_chunks):
            # Generate embedding
            embedding = None
            if self.embedding_service:
                try:
                    embedding = self.embedding_service.generate_embedding(chunk_text)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for chunk {i}: {e}")
            
            # Create chunk
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=i,
                content=chunk_text,
                content_hash=hashlib.sha256(chunk_text.encode()).hexdigest(),
                word_count=len(chunk_text.split()),
                embedding=embedding,
                embedding_model=self.embedding_service.model_name if self.embedding_service else None
            )
            
            self.session.add(chunk)
            chunks.append(chunk)
        
        return chunks
    
    def _create_workflow_chunks(self, workflow: WorkflowDocument, workflow_data: Dict, analysis: Dict) -> List[WorkflowChunk]:
        """Create chunks for a workflow.
        
        Args:
            workflow: The workflow to chunk
            workflow_data: Workflow JSON data
            analysis: Workflow analysis results
            
        Returns:
            List of created chunks
        """
        chunks = []
        chunk_index = 0
        
        # Description chunk
        if workflow.description:
            chunk = self._create_workflow_chunk(
                workflow, chunk_index, "description", workflow.description, analysis
            )
            chunks.append(chunk)
            chunk_index += 1
        
        # Nodes chunks
        nodes = workflow_data.get('nodes', [])
        for node in nodes:
            node_text = self._format_node_for_search(node)
            if node_text:
                chunk = self._create_workflow_chunk(
                    workflow, chunk_index, "nodes", node_text, analysis, node
                )
                chunks.append(chunk)
                chunk_index += 1
        
        # Connections chunk
        connections = workflow_data.get('connections', {})
        if connections:
            connections_text = self._format_connections_for_search(connections)
            chunk = self._create_workflow_chunk(
                workflow, chunk_index, "connections", connections_text, analysis
            )
            chunks.append(chunk)
            chunk_index += 1
        
        # Settings chunk
        settings = workflow_data.get('settings', {})
        if settings:
            settings_text = self._format_settings_for_search(settings)
            chunk = self._create_workflow_chunk(
                workflow, chunk_index, "settings", settings_text, analysis
            )
            chunks.append(chunk)
            chunk_index += 1
        
        return chunks
    
    def _create_workflow_chunk(self, workflow: WorkflowDocument, index: int, chunk_type: str, 
                              content: str, analysis: Dict, node_data: Optional[Dict] = None) -> WorkflowChunk:
        """Create a single workflow chunk.
        
        Args:
            workflow: Parent workflow
            index: Chunk index
            chunk_type: Type of chunk
            content: Chunk content
            analysis: Workflow analysis
            node_data: Node data if this is a node chunk
            
        Returns:
            Created workflow chunk
        """
        # Generate embedding
        embedding = None
        if self.embedding_service:
            try:
                embedding = self.embedding_service.generate_embedding(content)
            except Exception as e:
                logger.warning(f"Failed to generate embedding for workflow chunk {index}: {e}")
        
        # Extract metadata
        node_names = []
        node_types = []
        integrations = []
        
        if node_data:
            node_names = [node_data.get('name', '')]
            node_types = [node_data.get('type', '')]
            integrations = [node_data.get('type', '')] if node_data.get('type') else []
        else:
            node_names = analysis.get('node_names', [])
            node_types = analysis.get('node_types', [])
            integrations = analysis.get('integrations', [])
        
        chunk = WorkflowChunk(
            workflow_id=workflow.id,
            chunk_index=index,
            chunk_type=chunk_type,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            node_names=node_names,
            node_types=node_types,
            integrations=integrations,
            embedding=embedding,
            embedding_model=self.embedding_service.model_name if self.embedding_service else None
        )
        
        self.session.add(chunk)
        return chunk
    
    def _analyze_workflow(self, workflow_data: Dict) -> Dict[str, Any]:
        """Analyze workflow to extract metadata.
        
        Args:
            workflow_data: Workflow JSON data
            
        Returns:
            Analysis results
        """
        nodes = workflow_data.get('nodes', [])
        connections = workflow_data.get('connections', {})
        
        # Count nodes and connections
        node_count = len(nodes)
        connection_count = sum(len(conns) for conns in connections.values())
        
        # Extract node types and integrations
        node_types = []
        integrations = []
        trigger_types = []
        node_names = []
        
        for node in nodes:
            node_type = node.get('type', '')
            node_name = node.get('name', '')
            
            if node_type:
                node_types.append(node_type)
                node_names.append(node_name)
                
                # Check if it's a trigger
                if 'trigger' in node_type.lower() or node.get('typeVersion') == 1:
                    trigger_types.append(node_type)
                
                # Add to integrations (remove common prefixes)
                integration = node_type.replace('n8n-nodes-base.', '').replace('Trigger', '')
                if integration and integration not in integrations:
                    integrations.append(integration)
        
        # Calculate complexity score (0-1)
        complexity_score = min(1.0, (node_count + connection_count) / 50.0)
        
        # Calculate completeness score (0-1)
        completeness_score = 1.0
        if not workflow_data.get('name'):
            completeness_score -= 0.2
        if not workflow_data.get('description'):
            completeness_score -= 0.3
        if node_count == 0:
            completeness_score -= 0.5
        
        return {
            'node_count': node_count,
            'connection_count': connection_count,
            'node_types': list(set(node_types)),
            'integrations': list(set(integrations)),
            'trigger_types': list(set(trigger_types)),
            'node_names': node_names,
            'complexity_score': complexity_score,
            'completeness_score': max(0.0, completeness_score)
        }
    
    def _categorize_workflow(self, workflow_data: Dict, analysis: Dict) -> str:
        """Categorize workflow based on its content.
        
        Args:
            workflow_data: Workflow JSON data
            analysis: Workflow analysis
            
        Returns:
            Category string
        """
        integrations = analysis.get('integrations', [])
        trigger_types = analysis.get('trigger_types', [])
        
        # Check for common patterns
        if any('webhook' in t.lower() for t in trigger_types):
            return 'webhook'
        elif any('schedule' in t.lower() or 'cron' in t.lower() for t in trigger_types):
            return 'scheduled'
        elif any('manual' in t.lower() for t in trigger_types):
            return 'manual'
        elif any(integration.lower() in ['slack', 'discord', 'telegram'] for integration in integrations):
            return 'communication'
        elif any(integration.lower() in ['gmail', 'email', 'smtp'] for integration in integrations):
            return 'email'
        elif any(integration.lower() in ['github', 'gitlab', 'git'] for integration in integrations):
            return 'development'
        elif any(integration.lower() in ['airtable', 'googlesheets', 'notion'] for integration in integrations):
            return 'data'
        else:
            return 'automation'
    
    def _format_node_for_search(self, node: Dict) -> str:
        """Format node data for search indexing.
        
        Args:
            node: Node data
            
        Returns:
            Formatted text
        """
        parts = []
        
        # Node name and type
        name = node.get('name', '')
        node_type = node.get('type', '')
        
        if name:
            parts.append(f"Node: {name}")
        if node_type:
            parts.append(f"Type: {node_type}")
        
        # Parameters
        parameters = node.get('parameters', {})
        if parameters:
            for key, value in parameters.items():
                if isinstance(value, str) and value:
                    parts.append(f"{key}: {value}")
        
        # Notes
        notes = node.get('notes', '')
        if notes:
            parts.append(f"Notes: {notes}")
        
        return ' | '.join(parts)
    
    def _format_connections_for_search(self, connections: Dict) -> str:
        """Format connections for search indexing.
        
        Args:
            connections: Connections data
            
        Returns:
            Formatted text
        """
        parts = ["Workflow Connections:"]
        
        for source_node, targets in connections.items():
            if targets:
                target_nodes = []
                for target_list in targets.values():
                    for target in target_list:
                        target_nodes.append(target.get('node', ''))
                
                if target_nodes:
                    parts.append(f"{source_node} -> {', '.join(target_nodes)}")
        
        return ' | '.join(parts)
    
    def _format_settings_for_search(self, settings: Dict) -> str:
        """Format settings for search indexing.
        
        Args:
            settings: Settings data
            
        Returns:
            Formatted text
        """
        parts = ["Workflow Settings:"]
        
        for key, value in settings.items():
            if isinstance(value, (str, int, bool)):
                parts.append(f"{key}: {value}")
        
        return ' | '.join(parts)


def run_data_import(scraped_docs_dir: str, workflows_dir: str) -> Dict[str, Any]:
    """Run complete data import process.
    
    Args:
        scraped_docs_dir: Directory with scraped documentation
        workflows_dir: Directory with workflow files
        
    Returns:
        Combined import statistics
    """
    logger.info("Starting complete data import process")
    
    results = {
        "scraped_docs": {},
        "workflows": {},
        "total_time": 0,
        "success": False
    }
    
    start_time = datetime.now()
    
    try:
        with DataImporter() as importer:
            # Import scraped documents
            if os.path.exists(scraped_docs_dir):
                logger.info("Importing scraped documents...")
                results["scraped_docs"] = importer.import_scraped_documents(scraped_docs_dir)
            else:
                logger.warning(f"Scraped docs directory not found: {scraped_docs_dir}")
                results["scraped_docs"] = {"error": "Directory not found"}
            
            # Import workflows
            if os.path.exists(workflows_dir):
                logger.info("Importing workflows...")
                results["workflows"] = importer.import_workflows(workflows_dir)
            else:
                logger.warning(f"Workflows directory not found: {workflows_dir}")
                results["workflows"] = {"error": "Directory not found"}
        
        results["success"] = True
        
    except Exception as e:
        logger.error(f"Error during data import: {e}")
        results["error"] = str(e)
    
    end_time = datetime.now()
    results["total_time"] = (end_time - start_time).total_seconds()
    
    logger.info(f"Data import completed in {results['total_time']:.2f} seconds")
    logger.info(f"Results: {results}")
    
    return results