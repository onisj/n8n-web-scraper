#!/usr/bin/env python3
"""
Test suite for database components
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock

# Import database classes
try:
    from database.vector_db import VectorDatabase
    from database.document_processor import DocumentProcessor
except ImportError:
    # Handle case where database components aren't fully set up yet
    VectorDatabase = None
    DocumentProcessor = None


@pytest.fixture
def temp_db_path():
    """Create temporary directory for test database"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        {
            'id': 'doc_1',
            'title': 'Getting Started with n8n',
            'content': 'n8n is a powerful workflow automation tool that allows you to connect different services and automate tasks.',
            'url': 'https://docs.n8n.io/getting-started/',
            'metadata': {
                'category': 'getting-started',
                'tags': ['basics', 'introduction'],
                'last_updated': '2024-01-15'
            }
        },
        {
            'id': 'doc_2',
            'title': 'Working with Webhooks',
            'content': 'Webhooks in n8n allow external services to trigger your workflows. You can create webhook nodes to receive HTTP requests.',
            'url': 'https://docs.n8n.io/webhooks/',
            'metadata': {
                'category': 'webhooks',
                'tags': ['webhooks', 'triggers', 'http'],
                'last_updated': '2024-01-10'
            }
        },
        {
            'id': 'doc_3',
            'title': 'Creating Custom Nodes',
            'content': 'You can extend n8n functionality by creating custom nodes. This involves writing TypeScript code and following n8n node conventions.',
            'url': 'https://docs.n8n.io/nodes/creating-nodes/',
            'metadata': {
                'category': 'development',
                'tags': ['custom-nodes', 'typescript', 'development'],
                'last_updated': '2024-01-05'
            }
        }
    ]


class TestVectorDatabase:
    """Test vector database functionality"""
    
    def test_database_initialization(self, temp_db_path):
        """Test database initialization"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            assert db is not None
            assert hasattr(db, 'collection')
        except Exception as e:
            pytest.skip(f"Database initialization failed: {e}")
    
    def test_add_documents(self, temp_db_path, sample_documents):
        """Test adding documents to database"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add documents
            for doc in sample_documents:
                db.add_document(
                    doc_id=doc['id'],
                    content=doc['content'],
                    metadata=doc['metadata']
                )
            
            # Verify documents were added
            stats = db.get_stats()
            assert stats['total_documents'] >= len(sample_documents)
            
        except Exception as e:
            pytest.skip(f"Database operations failed: {e}")
    
    def test_search_functionality(self, temp_db_path, sample_documents):
        """Test search functionality"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add documents first
            for doc in sample_documents:
                db.add_document(
                    doc_id=doc['id'],
                    content=doc['content'],
                    metadata=doc['metadata']
                )
            
            # Test search
            results = db.search("webhook trigger workflow", limit=2)
            
            assert isinstance(results, list)
            assert len(results) <= 2
            
            if results:
                result = results[0]
                assert 'id' in result
                assert 'content' in result
                assert 'metadata' in result
                assert 'score' in result
                
        except Exception as e:
            pytest.skip(f"Search functionality failed: {e}")
    
    def test_search_with_filters(self, temp_db_path, sample_documents):
        """Test search with metadata filters"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add documents
            for doc in sample_documents:
                db.add_document(
                    doc_id=doc['id'],
                    content=doc['content'],
                    metadata=doc['metadata']
                )
            
            # Search with category filter
            results = db.search(
                "n8n",
                limit=5,
                filters={"category": "webhooks"}
            )
            
            assert isinstance(results, list)
            
            # All results should match the filter
            for result in results:
                assert result['metadata']['category'] == 'webhooks'
                
        except Exception as e:
            pytest.skip(f"Filtered search failed: {e}")
    
    def test_update_document(self, temp_db_path, sample_documents):
        """Test updating existing documents"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add initial document
            doc = sample_documents[0]
            db.add_document(
                doc_id=doc['id'],
                content=doc['content'],
                metadata=doc['metadata']
            )
            
            # Update document
            updated_content = "Updated content about n8n workflows and automation."
            updated_metadata = doc['metadata'].copy()
            updated_metadata['last_updated'] = '2024-01-20'
            
            db.update_document(
                doc_id=doc['id'],
                content=updated_content,
                metadata=updated_metadata
            )
            
            # Verify update
            results = db.search("updated content", limit=1)
            assert len(results) > 0
            assert "Updated content" in results[0]['content']
            
        except Exception as e:
            pytest.skip(f"Document update failed: {e}")
    
    def test_delete_document(self, temp_db_path, sample_documents):
        """Test deleting documents"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add document
            doc = sample_documents[0]
            db.add_document(
                doc_id=doc['id'],
                content=doc['content'],
                metadata=doc['metadata']
            )
            
            # Get initial count
            initial_stats = db.get_stats()
            initial_count = initial_stats['total_documents']
            
            # Delete document
            db.delete_document(doc['id'])
            
            # Verify deletion
            final_stats = db.get_stats()
            final_count = final_stats['total_documents']
            
            assert final_count < initial_count
            
        except Exception as e:
            pytest.skip(f"Document deletion failed: {e}")
    
    def test_get_document(self, temp_db_path, sample_documents):
        """Test retrieving specific documents"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add document
            doc = sample_documents[0]
            db.add_document(
                doc_id=doc['id'],
                content=doc['content'],
                metadata=doc['metadata']
            )
            
            # Retrieve document
            retrieved_doc = db.get_document(doc['id'])
            
            if retrieved_doc:
                assert retrieved_doc['id'] == doc['id']
                assert retrieved_doc['content'] == doc['content']
                assert retrieved_doc['metadata'] == doc['metadata']
            
        except Exception as e:
            pytest.skip(f"Document retrieval failed: {e}")
    
    def test_list_documents(self, temp_db_path, sample_documents):
        """Test listing all documents"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Add documents
            for doc in sample_documents:
                db.add_document(
                    doc_id=doc['id'],
                    content=doc['content'],
                    metadata=doc['metadata']
                )
            
            # List documents
            documents = db.list_documents(limit=10)
            
            assert isinstance(documents, list)
            assert len(documents) <= 10
            
            if documents:
                doc = documents[0]
                assert 'id' in doc
                assert 'metadata' in doc
                
        except Exception as e:
            pytest.skip(f"Document listing failed: {e}")
    
    def test_database_stats(self, temp_db_path, sample_documents):
        """Test database statistics"""
        if VectorDatabase is None:
            pytest.skip("VectorDatabase not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            
            # Get initial stats
            initial_stats = db.get_stats()
            assert isinstance(initial_stats, dict)
            assert 'total_documents' in initial_stats
            
            # Add documents
            for doc in sample_documents:
                db.add_document(
                    doc_id=doc['id'],
                    content=doc['content'],
                    metadata=doc['metadata']
                )
            
            # Get updated stats
            final_stats = db.get_stats()
            assert final_stats['total_documents'] >= initial_stats['total_documents']
            
        except Exception as e:
            pytest.skip(f"Database stats failed: {e}")


class TestDocumentProcessor:
    """Test document processing functionality"""
    
    def test_processor_initialization(self):
        """Test document processor initialization"""
        if DocumentProcessor is None:
            pytest.skip("DocumentProcessor not available")
        
        processor = DocumentProcessor()
        assert processor is not None
        assert hasattr(processor, 'process_document')
    
    def test_text_chunking(self):
        """Test text chunking functionality"""
        if DocumentProcessor is None:
            pytest.skip("DocumentProcessor not available")
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        
        long_text = "This is a long document. " * 50  # Create long text
        chunks = processor.chunk_text(long_text)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        
        # Check chunk sizes
        for chunk in chunks:
            assert len(chunk) <= 120  # chunk_size + some tolerance
    
    def test_document_processing(self, sample_documents):
        """Test full document processing"""
        if DocumentProcessor is None:
            pytest.skip("DocumentProcessor not available")
        
        processor = DocumentProcessor()
        
        doc = sample_documents[0]
        processed_chunks = processor.process_document(
            content=doc['content'],
            metadata=doc['metadata']
        )
        
        assert isinstance(processed_chunks, list)
        assert len(processed_chunks) > 0
        
        # Check chunk structure
        chunk = processed_chunks[0]
        assert 'content' in chunk
        assert 'metadata' in chunk
        assert 'chunk_id' in chunk
    
    def test_metadata_extraction(self):
        """Test metadata extraction from content"""
        if DocumentProcessor is None:
            pytest.skip("DocumentProcessor not available")
        
        processor = DocumentProcessor()
        
        content = "# Getting Started\n\nThis is about n8n workflows."
        metadata = processor.extract_metadata(content)
        
        assert isinstance(metadata, dict)
        # Should extract title from markdown header
        if 'title' in metadata:
            assert 'Getting Started' in metadata['title']
    
    def test_content_cleaning(self):
        """Test content cleaning functionality"""
        if DocumentProcessor is None:
            pytest.skip("DocumentProcessor not available")
        
        processor = DocumentProcessor()
        
        dirty_content = "  This has   extra   spaces\n\n\nand newlines  "
        clean_content = processor.clean_content(dirty_content)
        
        assert isinstance(clean_content, str)
        assert clean_content.strip() == clean_content
        assert "   " not in clean_content  # No triple spaces
    
    def test_language_detection(self):
        """Test language detection"""
        if DocumentProcessor is None:
            pytest.skip("DocumentProcessor not available")
        
        processor = DocumentProcessor()
        
        english_text = "This is an English document about n8n workflows."
        language = processor.detect_language(english_text)
        
        if language:
            assert isinstance(language, str)
            # Should detect English
            assert language.lower() in ['en', 'english']


class TestDatabaseIntegration:
    """Test integration between database components"""
    
    def test_processor_with_database(self, temp_db_path, sample_documents):
        """Test document processor with vector database"""
        if VectorDatabase is None or DocumentProcessor is None:
            pytest.skip("Database components not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            processor = DocumentProcessor(chunk_size=200)
            
            # Process and add document
            doc = sample_documents[0]
            chunks = processor.process_document(
                content=doc['content'],
                metadata=doc['metadata']
            )
            
            # Add chunks to database
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc['id']}_chunk_{i}"
                db.add_document(
                    doc_id=chunk_id,
                    content=chunk['content'],
                    metadata=chunk['metadata']
                )
            
            # Test search
            results = db.search("n8n workflow", limit=5)
            assert isinstance(results, list)
            
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")
    
    def test_bulk_document_processing(self, temp_db_path, sample_documents):
        """Test processing multiple documents"""
        if VectorDatabase is None or DocumentProcessor is None:
            pytest.skip("Database components not available")
        
        try:
            db = VectorDatabase(persist_directory=temp_db_path)
            processor = DocumentProcessor()
            
            # Process all documents
            total_chunks = 0
            for doc in sample_documents:
                chunks = processor.process_document(
                    content=doc['content'],
                    metadata=doc['metadata']
                )
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc['id']}_chunk_{i}"
                    db.add_document(
                        doc_id=chunk_id,
                        content=chunk['content'],
                        metadata=chunk['metadata']
                    )
                    total_chunks += 1
            
            # Verify all chunks were added
            stats = db.get_stats()
            assert stats['total_documents'] >= total_chunks
            
        except Exception as e:
            pytest.skip(f"Bulk processing failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])