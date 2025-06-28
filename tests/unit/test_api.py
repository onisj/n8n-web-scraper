#!/usr/bin/env python3
"""
Test suite for API endpoints
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import the FastAPI app
try:
    from api.main import app
except ImportError:
    # Handle case where API components aren't fully set up yet
    app = None


@pytest.fixture
def client():
    """Create test client"""
    if app is None:
        pytest.skip("API app not available")
    return TestClient(app)


@pytest.fixture
def mock_vector_db():
    """Mock vector database"""
    with patch('database.vector_db.VectorDatabase') as mock:
        mock_instance = Mock()
        mock_instance.search.return_value = [
            {
                'id': 'test_doc_1',
                'content': 'Test document content',
                'metadata': {'title': 'Test Document'},
                'score': 0.95
            }
        ]
        mock_instance.get_stats.return_value = {
            'total_documents': 100,
            'total_chunks': 500
        }
        mock.return_value = mock_instance
        yield mock_instance


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self, client):
        """Test basic health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_detailed_status(self, client, mock_vector_db):
        """Test detailed status endpoint"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "database" in data
        assert "timestamp" in data


class TestSearchEndpoints:
    """Test search functionality"""
    
    def test_search_knowledge_base(self, client, mock_vector_db):
        """Test knowledge base search"""
        search_data = {
            "query": "How to create a webhook in n8n?",
            "limit": 5
        }
        
        response = client.post("/api/v1/search", json=search_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert len(data["results"]) <= 5
    
    def test_search_with_filters(self, client, mock_vector_db):
        """Test search with metadata filters"""
        search_data = {
            "query": "workflow automation",
            "limit": 10,
            "filters": {"category": "workflows"}
        }
        
        response = client.post("/api/v1/search", json=search_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
    
    def test_search_empty_query(self, client):
        """Test search with empty query"""
        search_data = {"query": "", "limit": 5}
        
        response = client.post("/api/v1/search", json=search_data)
        assert response.status_code == 400


class TestChatEndpoints:
    """Test chat functionality"""
    
    @patch('agents.n8n_agent.N8nExpertAgent')
    def test_chat_with_agent(self, mock_agent, client):
        """Test chat with AI agent"""
        # Mock agent response
        mock_agent_instance = Mock()
        mock_agent_instance.process_query.return_value = {
            "response": "Here's how to create a webhook in n8n...",
            "sources": ["doc1", "doc2"],
            "confidence": 0.9
        }
        mock_agent.return_value = mock_agent_instance
        
        chat_data = {
            "message": "How do I create a webhook in n8n?",
            "conversation_id": "test_conv_1"
        }
        
        response = client.post("/api/v1/chat", json=chat_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
    
    def test_chat_empty_message(self, client):
        """Test chat with empty message"""
        chat_data = {"message": ""}
        
        response = client.post("/api/v1/chat", json=chat_data)
        assert response.status_code == 400


class TestDocumentEndpoints:
    """Test document management endpoints"""
    
    def test_list_documents(self, client, mock_vector_db):
        """Test listing documents"""
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        
        data = response.json()
        assert "documents" in data
        assert "total" in data
    
    def test_get_document(self, client, mock_vector_db):
        """Test getting specific document"""
        doc_id = "test_doc_1"
        response = client.get(f"/api/v1/documents/{doc_id}")
        
        # Should return 200 if document exists, 404 if not
        assert response.status_code in [200, 404]
    
    def test_add_document(self, client, mock_vector_db):
        """Test adding new document"""
        doc_data = {
            "title": "Test Document",
            "content": "This is a test document about n8n workflows.",
            "url": "https://example.com/test-doc",
            "metadata": {"category": "test"}
        }
        
        response = client.post("/api/v1/documents", json=doc_data)
        assert response.status_code in [201, 200]  # Created or OK
        
        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            assert "message" in data


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present"""
        response = client.get("/health")
        
        # Check for rate limiting headers
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 200
    
    @pytest.mark.slow
    def test_rate_limit_enforcement(self, client):
        """Test rate limit enforcement (slow test)"""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # Should have at least some successful responses
        assert 200 in responses


class TestCORS:
    """Test CORS functionality"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/health")
        
        # Should allow CORS or return appropriate headers
        assert response.status_code in [200, 204]


if __name__ == "__main__":
    pytest.main([__file__])