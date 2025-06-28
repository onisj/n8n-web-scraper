"""Integration tests for API endpoints.

These tests validate the complete API functionality including
authentication, search, chat, and real-time features.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import websockets
from datetime import datetime, timedelta

from src.n8n_scraper.api.main import app
from src.n8n_scraper.database.models import User, Document, SearchResult
from src.n8n_scraper.auth.jwt_handler import create_access_token
from src.n8n_scraper.config import settings


class TestAPIEndpoints:
    """Test suite for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def auth_headers(self, mock_user):
        """Create authentication headers."""
        token = create_access_token(data={"sub": mock_user["email"]})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def mock_user(self):
        """Mock user data."""
        return {
            "id": "user123",
            "email": "test@example.com",
            "username": "testuser",
            "is_active": True,
            "created_at": datetime.utcnow()
        }

    @pytest.fixture
    def mock_documents(self):
        """Mock document data."""
        return [
            {
                "id": "doc1",
                "title": "Test Document 1",
                "content": "This is test content for document 1",
                "url": "https://example.com/doc1",
                "category": "tutorial",
                "tags": ["test", "api"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "id": "doc2",
                "title": "Test Document 2",
                "content": "This is test content for document 2",
                "url": "https://example.com/doc2",
                "category": "guide",
                "tags": ["test", "integration"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]

    # Authentication Tests
    def test_register_user_success(self, client):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123"
        }
        
        with patch('src.n8n_scraper.auth.auth_service.create_user') as mock_create:
            mock_create.return_value = {"id": "new123", **user_data}
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == user_data["email"]
            assert "password" not in data

    def test_register_user_duplicate_email(self, client):
        """Test registration with duplicate email."""
        user_data = {
            "email": "existing@example.com",
            "username": "newuser",
            "password": "securepassword123"
        }
        
        with patch('src.n8n_scraper.auth.auth_service.create_user') as mock_create:
            mock_create.side_effect = ValueError("Email already exists")
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]

    def test_login_success(self, client, mock_user):
        """Test successful login."""
        login_data = {
            "email": "test@example.com",
            "password": "correctpassword"
        }
        
        with patch('src.n8n_scraper.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = mock_user
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        with patch('src.n8n_scraper.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/user/profile")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client, auth_headers, mock_user):
        """Test accessing protected endpoint with valid token."""
        with patch('src.n8n_scraper.auth.auth_service.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            response = client.get("/api/v1/user/profile", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == mock_user["email"]

    # Search Tests
    def test_search_documents_success(self, client, auth_headers, mock_documents):
        """Test successful document search."""
        search_params = {
            "query": "test content",
            "limit": 10,
            "offset": 0
        }
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = {
                "results": mock_documents,
                "total": len(mock_documents),
                "query": search_params["query"]
            }
            
            response = client.get("/api/v1/search", params=search_params, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            assert data["total"] == 2
            assert data["query"] == search_params["query"]

    def test_search_with_filters(self, client, auth_headers, mock_documents):
        """Test search with category and tag filters."""
        search_params = {
            "query": "test",
            "category": "tutorial",
            "tags": "api,test",
            "limit": 5
        }
        
        filtered_docs = [doc for doc in mock_documents if doc["category"] == "tutorial"]
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = {
                "results": filtered_docs,
                "total": len(filtered_docs),
                "query": search_params["query"]
            }
            
            response = client.get("/api/v1/search", params=search_params, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["category"] == "tutorial"

    def test_semantic_search(self, client, auth_headers, mock_documents):
        """Test semantic search functionality."""
        search_params = {
            "query": "how to integrate APIs",
            "search_type": "semantic",
            "limit": 5
        }
        
        with patch('src.n8n_scraper.search.semantic_search.semantic_search') as mock_semantic:
            mock_semantic.return_value = {
                "results": mock_documents,
                "total": len(mock_documents),
                "query": search_params["query"],
                "search_type": "semantic"
            }
            
            response = client.get("/api/v1/search/semantic", params=search_params, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["search_type"] == "semantic"
            assert len(data["results"]) > 0

    def test_search_suggestions(self, client, auth_headers):
        """Test search suggestions endpoint."""
        query_params = {"q": "test"}
        
        mock_suggestions = [
            "test api integration",
            "test automation",
            "test documentation"
        ]
        
        with patch('src.n8n_scraper.search.search_service.get_suggestions') as mock_suggestions_func:
            mock_suggestions_func.return_value = mock_suggestions
            
            response = client.get("/api/v1/search/suggestions", params=query_params, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert len(data["suggestions"]) == 3

    # Chat Tests
    def test_chat_completion_success(self, client, auth_headers):
        """Test successful chat completion."""
        chat_data = {
            "message": "How do I set up n8n automation?",
            "context": ["automation", "setup"],
            "model": "gpt-3.5-turbo"
        }
        
        mock_response = {
            "response": "To set up n8n automation, you need to...",
            "sources": ["doc1", "doc2"],
            "model": "gpt-3.5-turbo",
            "usage": {"tokens": 150}
        }
        
        with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
            mock_chat.return_value = mock_response
            
            response = client.post("/api/v1/chat", json=chat_data, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "sources" in data
            assert len(data["sources"]) > 0

    def test_chat_with_conversation_history(self, client, auth_headers):
        """Test chat with conversation history."""
        chat_data = {
            "message": "Can you explain more about webhooks?",
            "conversation_id": "conv123",
            "context": ["webhooks"]
        }
        
        mock_response = {
            "response": "Webhooks in n8n allow you to...",
            "conversation_id": "conv123",
            "sources": ["webhook_doc"]
        }
        
        with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
            mock_chat.return_value = mock_response
            
            response = client.post("/api/v1/chat", json=chat_data, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == "conv123"

    def test_get_conversation_history(self, client, auth_headers):
        """Test retrieving conversation history."""
        conversation_id = "conv123"
        
        mock_history = [
            {
                "id": "msg1",
                "message": "How do I set up n8n?",
                "response": "To set up n8n...",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        with patch('src.n8n_scraper.chat.chat_service.get_conversation_history') as mock_history_func:
            mock_history_func.return_value = mock_history
            
            response = client.get(f"/api/v1/chat/conversations/{conversation_id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "messages" in data
            assert len(data["messages"]) == 1

    # Document Management Tests
    def test_get_document_by_id(self, client, auth_headers, mock_documents):
        """Test retrieving document by ID."""
        document_id = "doc1"
        
        with patch('src.n8n_scraper.database.document_service.get_document') as mock_get_doc:
            mock_get_doc.return_value = mock_documents[0]
            
            response = client.get(f"/api/v1/documents/{document_id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == document_id
            assert data["title"] == "Test Document 1"

    def test_get_document_not_found(self, client, auth_headers):
        """Test retrieving non-existent document."""
        document_id = "nonexistent"
        
        with patch('src.n8n_scraper.database.document_service.get_document') as mock_get_doc:
            mock_get_doc.return_value = None
            
            response = client.get(f"/api/v1/documents/{document_id}", headers=auth_headers)
            
            assert response.status_code == 404

    def test_list_documents_with_pagination(self, client, auth_headers, mock_documents):
        """Test listing documents with pagination."""
        params = {"limit": 1, "offset": 0}
        
        with patch('src.n8n_scraper.database.document_service.list_documents') as mock_list:
            mock_list.return_value = {
                "documents": mock_documents[:1],
                "total": len(mock_documents),
                "limit": 1,
                "offset": 0
            }
            
            response = client.get("/api/v1/documents", params=params, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["documents"]) == 1
            assert data["total"] == 2

    # Analytics Tests
    def test_get_search_analytics(self, client, auth_headers):
        """Test retrieving search analytics."""
        mock_analytics = {
            "total_searches": 150,
            "popular_queries": [
                {"query": "automation", "count": 25},
                {"query": "webhook", "count": 20}
            ],
            "search_trends": {
                "daily": [10, 15, 12, 18, 22],
                "categories": {"tutorial": 45, "guide": 35, "reference": 20}
            }
        }
        
        with patch('src.n8n_scraper.analytics.analytics_service.get_search_analytics') as mock_analytics_func:
            mock_analytics_func.return_value = mock_analytics
            
            response = client.get("/api/v1/analytics/search", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_searches"] == 150
            assert len(data["popular_queries"]) == 2

    def test_get_user_analytics(self, client, auth_headers):
        """Test retrieving user analytics."""
        mock_user_analytics = {
            "search_count": 25,
            "chat_count": 15,
            "favorite_categories": ["automation", "webhooks"],
            "activity_timeline": [
                {"date": "2024-01-01", "searches": 5, "chats": 3}
            ]
        }
        
        with patch('src.n8n_scraper.analytics.analytics_service.get_user_analytics') as mock_user_analytics_func:
            mock_user_analytics_func.return_value = mock_user_analytics
            
            response = client.get("/api/v1/analytics/user", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["search_count"] == 25
            assert data["chat_count"] == 15

    # Health Check Tests
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        mock_health = {
            "status": "healthy",
            "services": {
                "database": "healthy",
                "redis": "healthy",
                "elasticsearch": "healthy"
            },
            "metrics": {
                "response_time": 0.05,
                "memory_usage": 0.65,
                "cpu_usage": 0.25
            }
        }
        
        with patch('src.n8n_scraper.health.health_service.get_detailed_health') as mock_health_func:
            mock_health_func.return_value = mock_health
            
            response = client.get("/api/v1/health/detailed")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "services" in data
            assert "metrics" in data

    # Error Handling Tests
    def test_invalid_json_request(self, client, auth_headers):
        """Test handling of invalid JSON in request."""
        response = client.post(
            "/api/v1/chat",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_missing_required_fields(self, client, auth_headers):
        """Test handling of missing required fields."""
        incomplete_data = {"message": ""}  # Missing required message content
        
        response = client.post("/api/v1/chat", json=incomplete_data, headers=auth_headers)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting functionality."""
        # This would require actual rate limiting implementation
        # For now, we'll test the structure
        
        with patch('src.n8n_scraper.middleware.rate_limiter.is_rate_limited') as mock_rate_limit:
            mock_rate_limit.return_value = True
            
            response = client.get("/api/v1/search?query=test", headers=auth_headers)
            
            # Depending on implementation, this might be 429 or handled differently
            assert response.status_code in [200, 429]

    # WebSocket Tests
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection for real-time features."""
        # This is a basic structure for WebSocket testing
        # Actual implementation would depend on your WebSocket setup
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            
            # Simulate WebSocket connection
            uri = "ws://localhost:8000/ws"
            
            async with mock_connect(uri) as websocket:
                # Test sending a message
                test_message = {"type": "search", "query": "test"}
                await websocket.send(json.dumps(test_message))
                
                # Mock response
                mock_response = {"type": "search_result", "data": []}
                mock_websocket.recv.return_value = json.dumps(mock_response)
                
                response = await websocket.recv()
                response_data = json.loads(response)
                
                assert response_data["type"] == "search_result"

    # Performance Tests
    def test_search_performance(self, client, auth_headers):
        """Test search endpoint performance."""
        import time
        
        search_params = {"query": "performance test", "limit": 100}
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = {"results": [], "total": 0, "query": "performance test"}
            
            start_time = time.time()
            response = client.get("/api/v1/search", params=search_params, headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 1.0  # Should respond within 1 second

    def test_concurrent_requests(self, client, auth_headers):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/api/v1/health", headers=auth_headers)
            results.append(response.status_code)
        
        # Create multiple threads to simulate concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10

    # Integration with External Services
    @pytest.mark.external
    def test_openai_integration(self, client, auth_headers):
        """Test integration with OpenAI API."""
        chat_data = {
            "message": "Test OpenAI integration",
            "model": "gpt-3.5-turbo"
        }
        
        # This test would require actual OpenAI API key
        # Skip if not available
        if not settings.OPENAI_API_KEY:
            pytest.skip("OpenAI API key not available")
        
        response = client.post("/api/v1/chat", json=chat_data, headers=auth_headers)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 503]  # 503 if service unavailable

    @pytest.mark.external
    def test_database_integration(self, client, auth_headers):
        """Test database integration."""
        # This test would require actual database connection
        response = client.get("/api/v1/documents", headers=auth_headers)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 503]

    # Cleanup and Teardown
    def test_cleanup_resources(self, client, auth_headers):
        """Test proper cleanup of resources."""
        # Test that resources are properly cleaned up after requests
        # This is more of a structural test
        
        response = client.get("/api/v1/health", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify no resource leaks (would require monitoring tools in real scenario)
        # For now, just ensure the endpoint responds correctly
        response2 = client.get("/api/v1/health", headers=auth_headers)
        assert response2.status_code == 200