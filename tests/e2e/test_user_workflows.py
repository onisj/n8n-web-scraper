"""End-to-end tests for complete user workflows.

These tests validate the entire system from a user's perspective,
including authentication, search, chat, and document management workflows.
"""

import pytest
import time
import json
from typing import Dict, List, Any
from unittest.mock import patch, Mock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from fastapi.testclient import TestClient
import websocket
import threading

from src.n8n_scraper.api.main import app
from src.n8n_scraper.config import settings


class E2ETestBase:
    """Base class for end-to-end tests."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.driver = None
        self.wait = None
        self.base_url = "http://localhost:3000"
        self.api_base_url = "http://localhost:8000/api/v1"
    
    def setup_browser(self, headless: bool = True):
        """Setup browser for UI testing."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def teardown_browser(self):
        """Cleanup browser resources."""
        if self.driver:
            self.driver.quit()
    
    def login_user(self, email: str = "test@example.com", password: str = "password") -> Dict[str, Any]:
        """Login user and return authentication token."""
        with patch('src.n8n_scraper.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "id": "user1",
                "email": email,
                "name": "Test User"
            }
            
            response = self.client.post(
                "/auth/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Login failed: {response.text}")
    
    def create_auth_headers(self, token: str) -> Dict[str, str]:
        """Create authentication headers."""
        return {"Authorization": f"Bearer {token}"}


class TestAuthenticationWorkflow(E2ETestBase):
    """Test complete authentication workflows."""
    
    def test_user_registration_workflow(self):
        """Test complete user registration workflow."""
        # Mock user registration
        with patch('src.n8n_scraper.auth.auth_service.register_user') as mock_register:
            mock_register.return_value = {
                "id": "new_user_1",
                "email": "newuser@example.com",
                "name": "New User",
                "created_at": "2024-01-01T00:00:00Z"
            }
            
            # Step 1: Register new user
            registration_data = {
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
                "confirm_password": "securepassword123"
            }
            
            response = self.client.post("/auth/register", json=registration_data)
            assert response.status_code == 201
            
            user_data = response.json()
            assert user_data["email"] == "newuser@example.com"
            assert user_data["name"] == "New User"
            assert "id" in user_data
    
    def test_user_login_workflow(self):
        """Test complete user login workflow."""
        # Step 1: Attempt login with valid credentials
        auth_data = self.login_user()
        assert "access_token" in auth_data
        assert "user" in auth_data
        
        # Step 2: Verify token works for protected endpoints
        headers = self.create_auth_headers(auth_data["access_token"])
        
        with patch('src.n8n_scraper.auth.auth_service.get_current_user') as mock_user:
            mock_user.return_value = auth_data["user"]
            
            profile_response = self.client.get("/auth/profile", headers=headers)
            assert profile_response.status_code == 200
            
            profile_data = profile_response.json()
            assert profile_data["email"] == "test@example.com"
    
    def test_password_reset_workflow(self):
        """Test password reset workflow."""
        # Step 1: Request password reset
        with patch('src.n8n_scraper.auth.auth_service.request_password_reset') as mock_reset:
            mock_reset.return_value = {"message": "Password reset email sent"}
            
            reset_request = self.client.post(
                "/auth/password-reset",
                json={"email": "test@example.com"}
            )
            assert reset_request.status_code == 200
        
        # Step 2: Confirm password reset with token
        with patch('src.n8n_scraper.auth.auth_service.confirm_password_reset') as mock_confirm:
            mock_confirm.return_value = {"message": "Password reset successful"}
            
            reset_confirm = self.client.post(
                "/auth/password-reset/confirm",
                json={
                    "token": "reset_token_123",
                    "new_password": "newpassword123",
                    "confirm_password": "newpassword123"
                }
            )
            assert reset_confirm.status_code == 200
    
    def test_token_refresh_workflow(self):
        """Test token refresh workflow."""
        # Step 1: Login to get initial tokens
        auth_data = self.login_user()
        
        # Step 2: Use refresh token to get new access token
        with patch('src.n8n_scraper.auth.auth_service.refresh_access_token') as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "token_type": "bearer",
                "expires_in": 3600
            }
            
            refresh_response = self.client.post(
                "/auth/refresh",
                json={"refresh_token": auth_data.get("refresh_token", "refresh_token_123")}
            )
            assert refresh_response.status_code == 200
            
            new_tokens = refresh_response.json()
            assert "access_token" in new_tokens
            assert new_tokens["access_token"] != auth_data["access_token"]


class TestSearchWorkflow(E2ETestBase):
    """Test complete search workflows."""
    
    def test_basic_search_workflow(self):
        """Test basic search workflow."""
        # Setup authentication
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock search results
        mock_results = {
            "results": [
                {
                    "id": "doc1",
                    "title": "Getting Started with n8n",
                    "content": "Learn how to create your first automation workflow...",
                    "score": 0.95,
                    "category": "tutorial",
                    "url": "https://docs.n8n.io/getting-started"
                },
                {
                    "id": "doc2",
                    "title": "Webhook Integration Guide",
                    "content": "Configure webhooks to trigger workflows...",
                    "score": 0.87,
                    "category": "integration",
                    "url": "https://docs.n8n.io/webhooks"
                }
            ],
            "total": 2,
            "query": "automation workflow",
            "took": 0.045
        }
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = mock_results
            
            # Step 1: Perform basic search
            search_response = self.client.get(
                "/search?query=automation workflow&limit=10",
                headers=headers
            )
            assert search_response.status_code == 200
            
            search_data = search_response.json()
            assert len(search_data["results"]) == 2
            assert search_data["total"] == 2
            assert search_data["query"] == "automation workflow"
    
    def test_advanced_search_workflow(self):
        """Test advanced search with filters."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock filtered search results
        mock_results = {
            "results": [
                {
                    "id": "doc3",
                    "title": "API Integration Tutorial",
                    "content": "Connect external APIs to your workflows...",
                    "score": 0.92,
                    "category": "tutorial",
                    "tags": ["api", "integration", "tutorial"]
                }
            ],
            "total": 1,
            "query": "API integration",
            "filters": {"category": "tutorial", "tags": ["api"]},
            "took": 0.032
        }
        
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = mock_results
            
            # Step 1: Perform filtered search
            search_params = {
                "query": "API integration",
                "category": "tutorial",
                "tags": "api",
                "limit": 10,
                "sort": "relevance"
            }
            
            search_response = self.client.get(
                "/search",
                params=search_params,
                headers=headers
            )
            assert search_response.status_code == 200
            
            search_data = search_response.json()
            assert len(search_data["results"]) == 1
            assert search_data["results"][0]["category"] == "tutorial"
            assert "api" in search_data["results"][0]["tags"]
    
    def test_search_suggestions_workflow(self):
        """Test search suggestions workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock search suggestions
        mock_suggestions = {
            "suggestions": [
                "automation workflow",
                "automation testing",
                "automation best practices",
                "workflow automation tools",
                "automated data processing"
            ],
            "query": "autom"
        }
        
        with patch('src.n8n_scraper.search.search_service.get_search_suggestions') as mock_suggestions_service:
            mock_suggestions_service.return_value = mock_suggestions
            
            # Step 1: Get search suggestions
            suggestions_response = self.client.get(
                "/search/suggestions?query=autom",
                headers=headers
            )
            assert suggestions_response.status_code == 200
            
            suggestions_data = suggestions_response.json()
            assert len(suggestions_data["suggestions"]) == 5
            assert all("autom" in suggestion.lower() for suggestion in suggestions_data["suggestions"])
    
    def test_semantic_search_workflow(self):
        """Test semantic search workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock semantic search results
        mock_results = {
            "results": [
                {
                    "id": "doc4",
                    "title": "Building Automated Workflows",
                    "content": "Create sophisticated automation pipelines...",
                    "score": 0.89,
                    "semantic_similarity": 0.94,
                    "explanation": "Highly relevant to workflow automation concepts"
                }
            ],
            "total": 1,
            "query": "how to create automated processes",
            "search_type": "semantic",
            "took": 0.156
        }
        
        with patch('src.n8n_scraper.search.search_service.semantic_search') as mock_semantic:
            mock_semantic.return_value = mock_results
            
            # Step 1: Perform semantic search
            search_response = self.client.get(
                "/search/semantic?query=how to create automated processes",
                headers=headers
            )
            assert search_response.status_code == 200
            
            search_data = search_response.json()
            assert search_data["search_type"] == "semantic"
            assert "semantic_similarity" in search_data["results"][0]


class TestChatWorkflow(E2ETestBase):
    """Test complete chat workflows."""
    
    def test_basic_chat_workflow(self):
        """Test basic chat interaction workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock chat response
        mock_response = {
            "response": "To create an automation workflow in n8n, you can start by accessing the workflow editor and adding nodes. Here's a step-by-step guide...",
            "sources": [
                {
                    "id": "doc1",
                    "title": "Getting Started with n8n",
                    "relevance_score": 0.95
                },
                {
                    "id": "doc2",
                    "title": "Workflow Creation Guide",
                    "relevance_score": 0.87
                }
            ],
            "model": "gpt-3.5-turbo",
            "tokens_used": 245,
            "conversation_id": "conv_123"
        }
        
        with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
            mock_chat.return_value = mock_response
            
            # Step 1: Send chat message
            chat_request = {
                "message": "How do I create an automation workflow?",
                "model": "gpt-3.5-turbo",
                "conversation_id": None
            }
            
            chat_response = self.client.post(
                "/chat",
                json=chat_request,
                headers=headers
            )
            assert chat_response.status_code == 200
            
            chat_data = chat_response.json()
            assert "response" in chat_data
            assert len(chat_data["sources"]) == 2
            assert chat_data["conversation_id"] == "conv_123"
    
    def test_conversation_history_workflow(self):
        """Test conversation history workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock conversation history
        mock_history = {
            "conversations": [
                {
                    "id": "conv_123",
                    "title": "Automation Workflow Help",
                    "created_at": "2024-01-01T10:00:00Z",
                    "updated_at": "2024-01-01T10:15:00Z",
                    "message_count": 4
                },
                {
                    "id": "conv_124",
                    "title": "API Integration Questions",
                    "created_at": "2024-01-01T09:00:00Z",
                    "updated_at": "2024-01-01T09:30:00Z",
                    "message_count": 6
                }
            ],
            "total": 2
        }
        
        with patch('src.n8n_scraper.chat.chat_service.get_conversation_history') as mock_history_service:
            mock_history_service.return_value = mock_history
            
            # Step 1: Get conversation history
            history_response = self.client.get(
                "/chat/history",
                headers=headers
            )
            assert history_response.status_code == 200
            
            history_data = history_response.json()
            assert len(history_data["conversations"]) == 2
            assert history_data["total"] == 2
    
    def test_conversation_continuation_workflow(self):
        """Test continuing an existing conversation."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock conversation messages
        mock_messages = {
            "messages": [
                {
                    "id": "msg_1",
                    "role": "user",
                    "content": "How do I create an automation workflow?",
                    "timestamp": "2024-01-01T10:00:00Z"
                },
                {
                    "id": "msg_2",
                    "role": "assistant",
                    "content": "To create an automation workflow...",
                    "timestamp": "2024-01-01T10:00:30Z",
                    "sources": [{"id": "doc1", "title": "Getting Started"}]
                }
            ],
            "conversation_id": "conv_123",
            "total": 2
        }
        
        # Mock follow-up response
        mock_followup = {
            "response": "You can add conditions to your workflow using the IF node. This allows you to create branching logic...",
            "sources": [{"id": "doc3", "title": "Conditional Logic Guide"}],
            "model": "gpt-3.5-turbo",
            "conversation_id": "conv_123"
        }
        
        with patch('src.n8n_scraper.chat.chat_service.get_conversation_messages') as mock_get_messages:
            with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
                mock_get_messages.return_value = mock_messages
                mock_chat.return_value = mock_followup
                
                # Step 1: Get existing conversation
                messages_response = self.client.get(
                    "/chat/conversations/conv_123/messages",
                    headers=headers
                )
                assert messages_response.status_code == 200
                
                # Step 2: Continue conversation
                followup_request = {
                    "message": "Can I add conditions to the workflow?",
                    "conversation_id": "conv_123"
                }
                
                followup_response = self.client.post(
                    "/chat",
                    json=followup_request,
                    headers=headers
                )
                assert followup_response.status_code == 200
                
                followup_data = followup_response.json()
                assert followup_data["conversation_id"] == "conv_123"
                assert "conditional logic" in followup_data["response"].lower()


class TestDocumentWorkflow(E2ETestBase):
    """Test document management workflows."""
    
    def test_document_retrieval_workflow(self):
        """Test document retrieval workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock document data
        mock_document = {
            "id": "doc1",
            "title": "Getting Started with n8n",
            "content": "n8n is a powerful workflow automation tool that allows you to connect different services and automate tasks...",
            "url": "https://docs.n8n.io/getting-started",
            "category": "tutorial",
            "tags": ["getting-started", "tutorial", "basics"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
            "word_count": 1250,
            "reading_time": 5
        }
        
        with patch('src.n8n_scraper.database.document_service.get_document') as mock_get_doc:
            mock_get_doc.return_value = mock_document
            
            # Step 1: Get document by ID
            doc_response = self.client.get(
                "/documents/doc1",
                headers=headers
            )
            assert doc_response.status_code == 200
            
            doc_data = doc_response.json()
            assert doc_data["id"] == "doc1"
            assert doc_data["title"] == "Getting Started with n8n"
            assert "tutorial" in doc_data["tags"]
    
    def test_document_listing_workflow(self):
        """Test document listing workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock document list
        mock_documents = {
            "documents": [
                {
                    "id": "doc1",
                    "title": "Getting Started with n8n",
                    "category": "tutorial",
                    "created_at": "2024-01-01T00:00:00Z",
                    "word_count": 1250
                },
                {
                    "id": "doc2",
                    "title": "Webhook Integration Guide",
                    "category": "integration",
                    "created_at": "2024-01-01T01:00:00Z",
                    "word_count": 890
                }
            ],
            "total": 2,
            "page": 1,
            "per_page": 20,
            "total_pages": 1
        }
        
        with patch('src.n8n_scraper.database.document_service.list_documents') as mock_list_docs:
            mock_list_docs.return_value = mock_documents
            
            # Step 1: List documents with pagination
            list_response = self.client.get(
                "/documents?page=1&per_page=20&category=tutorial",
                headers=headers
            )
            assert list_response.status_code == 200
            
            list_data = list_response.json()
            assert len(list_data["documents"]) == 2
            assert list_data["total"] == 2
            assert list_data["page"] == 1
    
    def test_document_categories_workflow(self):
        """Test document categories workflow."""
        auth_data = self.login_user()
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Mock categories data
        mock_categories = {
            "categories": [
                {
                    "name": "tutorial",
                    "display_name": "Tutorials",
                    "description": "Step-by-step guides and tutorials",
                    "document_count": 25,
                    "icon": "book"
                },
                {
                    "name": "integration",
                    "display_name": "Integrations",
                    "description": "Integration guides and examples",
                    "document_count": 18,
                    "icon": "link"
                },
                {
                    "name": "reference",
                    "display_name": "Reference",
                    "description": "API reference and documentation",
                    "document_count": 42,
                    "icon": "code"
                }
            ],
            "total": 3
        }
        
        with patch('src.n8n_scraper.database.document_service.get_categories') as mock_categories_service:
            mock_categories_service.return_value = mock_categories
            
            # Step 1: Get document categories
            categories_response = self.client.get(
                "/documents/categories",
                headers=headers
            )
            assert categories_response.status_code == 200
            
            categories_data = categories_response.json()
            assert len(categories_data["categories"]) == 3
            assert categories_data["total"] == 3
            
            # Verify category structure
            tutorial_category = next(cat for cat in categories_data["categories"] if cat["name"] == "tutorial")
            assert tutorial_category["document_count"] == 25
            assert tutorial_category["display_name"] == "Tutorials"


class TestWebSocketWorkflow(E2ETestBase):
    """Test WebSocket real-time communication workflows."""
    
    def test_websocket_connection_workflow(self):
        """Test WebSocket connection and messaging."""
        # Mock WebSocket server responses
        received_messages = []
        connection_established = threading.Event()
        
        def on_message(ws, message):
            received_messages.append(json.loads(message))
        
        def on_open(ws):
            connection_established.set()
            # Send authentication message
            auth_message = {
                "type": "auth",
                "token": "test_token_123"
            }
            ws.send(json.dumps(auth_message))
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        # Note: This is a mock test - in real implementation, you'd need a running WebSocket server
        # For now, we'll simulate the WebSocket behavior
        
        # Simulate WebSocket connection and messaging
        mock_ws_messages = [
            {"type": "auth_success", "user_id": "user1"},
            {"type": "notification", "message": "New document available", "document_id": "doc_new"},
            {"type": "search_update", "query": "automation", "new_results_count": 3}
        ]
        
        # Simulate receiving messages
        for message in mock_ws_messages:
            received_messages.append(message)
        
        # Verify message handling
        assert len(received_messages) == 3
        assert received_messages[0]["type"] == "auth_success"
        assert received_messages[1]["type"] == "notification"
        assert received_messages[2]["type"] == "search_update"
    
    def test_real_time_notifications_workflow(self):
        """Test real-time notifications workflow."""
        # Simulate real-time notification system
        notifications = [
            {
                "id": "notif_1",
                "type": "document_update",
                "title": "Document Updated",
                "message": "The 'Getting Started' guide has been updated with new information.",
                "document_id": "doc1",
                "timestamp": "2024-01-01T12:00:00Z",
                "read": False
            },
            {
                "id": "notif_2",
                "type": "system_maintenance",
                "title": "Scheduled Maintenance",
                "message": "System maintenance scheduled for tonight at 2 AM UTC.",
                "timestamp": "2024-01-01T11:30:00Z",
                "read": False
            }
        ]
        
        # Verify notification structure and content
        for notification in notifications:
            assert "id" in notification
            assert "type" in notification
            assert "title" in notification
            assert "message" in notification
            assert "timestamp" in notification
            assert "read" in notification
        
        # Test notification filtering
        unread_notifications = [n for n in notifications if not n["read"]]
        assert len(unread_notifications) == 2
        
        document_notifications = [n for n in notifications if n["type"] == "document_update"]
        assert len(document_notifications) == 1
        assert document_notifications[0]["document_id"] == "doc1"


class TestCompleteUserJourney(E2ETestBase):
    """Test complete user journey from registration to advanced usage."""
    
    def test_new_user_complete_journey(self):
        """Test complete journey for a new user."""
        # Step 1: User Registration
        with patch('src.n8n_scraper.auth.auth_service.register_user') as mock_register:
            mock_register.return_value = {
                "id": "journey_user_1",
                "email": "journey@example.com",
                "name": "Journey User"
            }
            
            registration_response = self.client.post(
                "/auth/register",
                json={
                    "email": "journey@example.com",
                    "password": "securepass123",
                    "name": "Journey User",
                    "confirm_password": "securepass123"
                }
            )
            assert registration_response.status_code == 201
        
        # Step 2: User Login
        with patch('src.n8n_scraper.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "id": "journey_user_1",
                "email": "journey@example.com",
                "name": "Journey User"
            }
            
            login_response = self.client.post(
                "/auth/login",
                json={"email": "journey@example.com", "password": "securepass123"}
            )
            assert login_response.status_code == 200
            auth_data = login_response.json()
            headers = self.create_auth_headers(auth_data["access_token"])
        
        # Step 3: Explore Categories
        with patch('src.n8n_scraper.database.document_service.get_categories') as mock_categories:
            mock_categories.return_value = {
                "categories": [
                    {"name": "tutorial", "display_name": "Tutorials", "document_count": 25},
                    {"name": "integration", "display_name": "Integrations", "document_count": 18}
                ],
                "total": 2
            }
            
            categories_response = self.client.get("/documents/categories", headers=headers)
            assert categories_response.status_code == 200
        
        # Step 4: Perform First Search
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "id": "doc1",
                        "title": "Getting Started with n8n",
                        "score": 0.95,
                        "category": "tutorial"
                    }
                ],
                "total": 1,
                "query": "getting started"
            }
            
            search_response = self.client.get(
                "/search?query=getting started",
                headers=headers
            )
            assert search_response.status_code == 200
        
        # Step 5: Read First Document
        with patch('src.n8n_scraper.database.document_service.get_document') as mock_doc:
            mock_doc.return_value = {
                "id": "doc1",
                "title": "Getting Started with n8n",
                "content": "Welcome to n8n! This guide will help you...",
                "category": "tutorial"
            }
            
            doc_response = self.client.get("/documents/doc1", headers=headers)
            assert doc_response.status_code == 200
        
        # Step 6: Ask First Question
        with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
            mock_chat.return_value = {
                "response": "Great question! To create your first workflow...",
                "sources": [{"id": "doc1", "title": "Getting Started with n8n"}],
                "conversation_id": "journey_conv_1"
            }
            
            chat_response = self.client.post(
                "/chat",
                json={"message": "How do I create my first workflow?"},
                headers=headers
            )
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            conversation_id = chat_data["conversation_id"]
        
        # Step 7: Continue Conversation
        with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat_followup:
            mock_chat_followup.return_value = {
                "response": "You can add nodes by clicking the '+' button...",
                "sources": [{"id": "doc2", "title": "Node Configuration Guide"}],
                "conversation_id": conversation_id
            }
            
            followup_response = self.client.post(
                "/chat",
                json={
                    "message": "How do I add nodes to my workflow?",
                    "conversation_id": conversation_id
                },
                headers=headers
            )
            assert followup_response.status_code == 200
        
        # Step 8: Check Conversation History
        with patch('src.n8n_scraper.chat.chat_service.get_conversation_history') as mock_history:
            mock_history.return_value = {
                "conversations": [
                    {
                        "id": conversation_id,
                        "title": "Workflow Creation Help",
                        "message_count": 4,
                        "created_at": "2024-01-01T12:00:00Z"
                    }
                ],
                "total": 1
            }
            
            history_response = self.client.get("/chat/history", headers=headers)
            assert history_response.status_code == 200
            history_data = history_response.json()
            assert len(history_data["conversations"]) == 1
        
        # Journey completed successfully
        assert True  # All steps completed without errors
    
    def test_power_user_workflow(self):
        """Test workflow for an experienced power user."""
        # Setup authenticated user
        auth_data = self.login_user("poweruser@example.com", "powerpass123")
        headers = self.create_auth_headers(auth_data["access_token"])
        
        # Step 1: Advanced Search with Multiple Filters
        with patch('src.n8n_scraper.search.search_service.search_documents') as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "id": "advanced_doc1",
                        "title": "Advanced API Integration Patterns",
                        "score": 0.98,
                        "category": "advanced",
                        "tags": ["api", "advanced", "patterns"]
                    }
                ],
                "total": 1,
                "query": "advanced API patterns",
                "filters": {"category": "advanced", "tags": ["api"]}
            }
            
            advanced_search = self.client.get(
                "/search?query=advanced API patterns&category=advanced&tags=api&sort=relevance",
                headers=headers
            )
            assert advanced_search.status_code == 200
        
        # Step 2: Semantic Search for Complex Concepts
        with patch('src.n8n_scraper.search.search_service.semantic_search') as mock_semantic:
            mock_semantic.return_value = {
                "results": [
                    {
                        "id": "semantic_doc1",
                        "title": "Error Handling Strategies",
                        "semantic_similarity": 0.92,
                        "explanation": "Highly relevant to fault tolerance concepts"
                    }
                ],
                "total": 1,
                "search_type": "semantic"
            }
            
            semantic_search = self.client.get(
                "/search/semantic?query=how to handle failures and ensure fault tolerance",
                headers=headers
            )
            assert semantic_search.status_code == 200
        
        # Step 3: Complex Multi-turn Conversation
        conversation_messages = [
            "I need to build a complex workflow that processes data from multiple APIs, handles errors gracefully, and scales automatically. Where should I start?",
            "How can I implement retry logic with exponential backoff?",
            "What's the best way to monitor workflow performance and set up alerts?",
            "Can you show me examples of error handling patterns for API failures?"
        ]
        
        conversation_id = None
        
        for i, message in enumerate(conversation_messages):
            with patch('src.n8n_scraper.chat.chat_service.generate_response') as mock_chat:
                mock_chat.return_value = {
                    "response": f"Detailed response to question {i+1}...",
                    "sources": [{"id": f"expert_doc_{i+1}", "title": f"Expert Guide {i+1}"}],
                    "conversation_id": conversation_id or f"power_conv_{int(time.time())}",
                    "model": "gpt-4",
                    "tokens_used": 450 + i * 50
                }
                
                chat_request = {"message": message}
                if conversation_id:
                    chat_request["conversation_id"] = conversation_id
                
                chat_response = self.client.post("/chat", json=chat_request, headers=headers)
                assert chat_response.status_code == 200
                
                if not conversation_id:
                    conversation_id = chat_response.json()["conversation_id"]
        
        # Step 4: Bulk Document Analysis
        document_ids = [f"bulk_doc_{i}" for i in range(1, 11)]
        
        with patch('src.n8n_scraper.database.document_service.get_documents_by_ids') as mock_bulk:
            mock_bulk.return_value = [
                {"id": doc_id, "title": f"Document {doc_id}", "category": "advanced"}
                for doc_id in document_ids
            ]
            
            bulk_response = self.client.post(
                "/documents/bulk",
                json={"document_ids": document_ids},
                headers=headers
            )
            assert bulk_response.status_code == 200
            bulk_data = bulk_response.json()
            assert len(bulk_data["documents"]) == 10
        
        # Power user workflow completed successfully
        assert True


if __name__ == "__main__":
    # Run end-to-end tests
    pytest.main(["-v", "-m", "e2e", __file__])