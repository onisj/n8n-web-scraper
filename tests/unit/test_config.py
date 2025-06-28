"""Test configuration and settings for the n8n scraper test suite.

This module provides centralized configuration for all tests,
including test database settings, mock configurations, and test data.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class TestDatabaseConfig:
    """Configuration for test database."""
    url: str = "sqlite:///test_n8n_scraper.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    @property
    def async_url(self) -> str:
        """Get async database URL."""
        return self.url.replace("sqlite://", "sqlite+aiosqlite://")


@dataclass
class TestRedisConfig:
    """Configuration for test Redis."""
    host: str = "localhost"
    port: int = 6379
    db: int = 15  # Use different DB for tests
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class TestAPIConfig:
    """Configuration for test API settings."""
    base_url: str = "http://localhost:8000"
    api_version: str = "v1"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 0.5
    
    @property
    def api_base_url(self) -> str:
        """Get API base URL."""
        return f"{self.base_url}/api/{self.api_version}"


@dataclass
class TestAuthConfig:
    """Configuration for test authentication."""
    secret_key: str = "test_secret_key_for_testing_only"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Test user credentials
    test_users: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "test_user": {
            "id": "test_user_1",
            "email": "test@example.com",
            "password": "testpassword123",
            "name": "Test User",
            "is_active": True,
            "is_admin": False
        },
        "admin_user": {
            "id": "admin_user_1",
            "email": "admin@example.com",
            "password": "adminpassword123",
            "name": "Admin User",
            "is_active": True,
            "is_admin": True
        },
        "inactive_user": {
            "id": "inactive_user_1",
            "email": "inactive@example.com",
            "password": "inactivepassword123",
            "name": "Inactive User",
            "is_active": False,
            "is_admin": False
        }
    })


@dataclass
class TestSearchConfig:
    """Configuration for test search settings."""
    # Mock vector dimensions
    vector_dimension: int = 1536
    
    # Search limits
    max_results: int = 100
    default_limit: int = 10
    
    # Mock search results
    mock_documents: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "id": "doc_1",
            "title": "Getting Started with n8n",
            "content": "Learn how to create your first automation workflow with n8n. This comprehensive guide covers the basics of workflow creation, node configuration, and best practices for automation.",
            "url": "https://docs.n8n.io/getting-started",
            "category": "tutorial",
            "tags": ["getting-started", "tutorial", "basics", "workflow"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
            "word_count": 1250,
            "reading_time": 5,
            "difficulty": "beginner",
            "author": "n8n Team"
        },
        {
            "id": "doc_2",
            "title": "Webhook Integration Guide",
            "content": "Configure webhooks to trigger workflows automatically. Learn about webhook security, payload handling, and integration patterns with external services.",
            "url": "https://docs.n8n.io/webhooks",
            "category": "integration",
            "tags": ["webhooks", "integration", "triggers", "api"],
            "created_at": "2024-01-01T01:00:00Z",
            "updated_at": "2024-01-01T13:00:00Z",
            "word_count": 890,
            "reading_time": 4,
            "difficulty": "intermediate",
            "author": "Integration Team"
        },
        {
            "id": "doc_3",
            "title": "Advanced API Integration Patterns",
            "content": "Master advanced API integration techniques including authentication, rate limiting, error handling, and data transformation patterns for complex workflows.",
            "url": "https://docs.n8n.io/advanced-api",
            "category": "advanced",
            "tags": ["api", "advanced", "patterns", "authentication", "error-handling"],
            "created_at": "2024-01-01T02:00:00Z",
            "updated_at": "2024-01-01T14:00:00Z",
            "word_count": 2100,
            "reading_time": 8,
            "difficulty": "advanced",
            "author": "API Team"
        },
        {
            "id": "doc_4",
            "title": "Database Operations and Data Processing",
            "content": "Learn how to work with databases in n8n workflows. Covers SQL operations, data transformation, batch processing, and database best practices.",
            "url": "https://docs.n8n.io/database-operations",
            "category": "data",
            "tags": ["database", "sql", "data-processing", "batch", "transformation"],
            "created_at": "2024-01-01T03:00:00Z",
            "updated_at": "2024-01-01T15:00:00Z",
            "word_count": 1680,
            "reading_time": 7,
            "difficulty": "intermediate",
            "author": "Data Team"
        },
        {
            "id": "doc_5",
            "title": "Error Handling and Monitoring",
            "content": "Implement robust error handling and monitoring in your workflows. Learn about retry strategies, error notifications, and workflow debugging techniques.",
            "url": "https://docs.n8n.io/error-handling",
            "category": "monitoring",
            "tags": ["error-handling", "monitoring", "debugging", "retry", "notifications"],
            "created_at": "2024-01-01T04:00:00Z",
            "updated_at": "2024-01-01T16:00:00Z",
            "word_count": 1420,
            "reading_time": 6,
            "difficulty": "intermediate",
            "author": "DevOps Team"
        }
    ])
    
    # Mock search suggestions
    mock_suggestions: List[str] = field(default_factory=lambda: [
        "automation workflow",
        "webhook integration",
        "API documentation",
        "database operations",
        "error handling",
        "data transformation",
        "workflow triggers",
        "node configuration",
        "authentication setup",
        "monitoring and alerts"
    ])


@dataclass
class TestChatConfig:
    """Configuration for test chat settings."""
    # Mock AI responses
    mock_responses: Dict[str, str] = field(default_factory=lambda: {
        "getting_started": "To get started with n8n, you'll want to begin by creating your first workflow. Here's a step-by-step guide: 1) Access the workflow editor, 2) Add your first node, 3) Configure the node settings, 4) Test your workflow. Would you like me to explain any of these steps in more detail?",
        "webhook_setup": "Setting up webhooks in n8n is straightforward. First, add a Webhook node to your workflow, then configure the HTTP method and path. The webhook URL will be automatically generated. You can then use this URL to receive data from external services.",
        "api_integration": "For API integrations, you'll typically use the HTTP Request node. Configure the URL, method, headers, and body as needed. For authentication, you can use the credentials system to securely store API keys and tokens.",
        "error_handling": "Error handling in n8n can be implemented using the Error Trigger node and try-catch patterns. You can also configure retry settings on individual nodes and set up notification workflows for when errors occur.",
        "data_processing": "Data processing in n8n involves using nodes like Set, Function, and various transformation nodes. You can manipulate JSON data, perform calculations, and format data for different systems."
    })
    
    # Mock conversation history
    mock_conversations: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "id": "conv_1",
            "title": "Getting Started Help",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:30:00Z",
            "message_count": 6,
            "user_id": "test_user_1"
        },
        {
            "id": "conv_2",
            "title": "API Integration Questions",
            "created_at": "2024-01-01T11:00:00Z",
            "updated_at": "2024-01-01T11:45:00Z",
            "message_count": 8,
            "user_id": "test_user_1"
        },
        {
            "id": "conv_3",
            "title": "Error Handling Discussion",
            "created_at": "2024-01-01T14:00:00Z",
            "updated_at": "2024-01-01T14:20:00Z",
            "message_count": 4,
            "user_id": "test_user_1"
        }
    ])
    
    # AI model settings
    default_model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class TestPerformanceConfig:
    """Configuration for performance testing."""
    # Load testing parameters
    max_concurrent_users: int = 50
    test_duration_seconds: int = 60
    ramp_up_time_seconds: int = 10
    
    # Performance thresholds
    max_response_time_ms: int = 1000
    min_success_rate_percent: float = 95.0
    max_error_rate_percent: float = 5.0
    
    # Memory and CPU limits
    max_memory_usage_mb: int = 512
    max_cpu_usage_percent: float = 80.0
    
    # Database performance
    max_db_query_time_ms: int = 100
    max_db_connections: int = 20


@dataclass
class TestWebSocketConfig:
    """Configuration for WebSocket testing."""
    url: str = "ws://localhost:8000/ws"
    connection_timeout: int = 10
    message_timeout: int = 5
    max_message_size: int = 1024 * 1024  # 1MB
    
    # Mock WebSocket messages
    mock_messages: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "type": "auth_success",
            "user_id": "test_user_1",
            "timestamp": "2024-01-01T12:00:00Z"
        },
        {
            "type": "notification",
            "title": "New Document Available",
            "message": "A new tutorial has been added to the documentation.",
            "document_id": "doc_new",
            "timestamp": "2024-01-01T12:05:00Z"
        },
        {
            "type": "search_update",
            "query": "automation",
            "new_results_count": 3,
            "timestamp": "2024-01-01T12:10:00Z"
        },
        {
            "type": "system_status",
            "status": "healthy",
            "services": {
                "api": "healthy",
                "database": "healthy",
                "search": "healthy",
                "chat": "healthy"
            },
            "timestamp": "2024-01-01T12:15:00Z"
        }
    ])


@dataclass
class TestFileConfig:
    """Configuration for test file handling."""
    # Test data directories
    test_data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "fixtures")
    temp_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "n8n_scraper_tests")
    
    # Test file patterns
    test_file_patterns: List[str] = field(default_factory=lambda: [
        "test_*.py",
        "*_test.py",
        "test*.json",
        "mock_*.json",
        "fixture_*.yaml"
    ])
    
    # File size limits
    max_test_file_size_mb: int = 10
    max_temp_files: int = 100
    
    def ensure_directories(self):
        """Ensure test directories exist."""
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def cleanup_temp_files(self):
        """Clean up temporary test files."""
        if self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)


class TestConfig:
    """Main test configuration class."""
    
    def __init__(self):
        self.database = TestDatabaseConfig()
        self.redis = TestRedisConfig()
        self.api = TestAPIConfig()
        self.auth = TestAuthConfig()
        self.search = TestSearchConfig()
        self.chat = TestChatConfig()
        self.performance = TestPerformanceConfig()
        self.websocket = TestWebSocketConfig()
        self.files = TestFileConfig()
        
        # Environment-specific overrides
        self._apply_environment_overrides()
        
        # Ensure required directories exist
        self.files.ensure_directories()
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        # Database overrides
        if db_url := os.getenv("TEST_DATABASE_URL"):
            self.database.url = db_url
        
        # Redis overrides
        if redis_host := os.getenv("TEST_REDIS_HOST"):
            self.redis.host = redis_host
        if redis_port := os.getenv("TEST_REDIS_PORT"):
            self.redis.port = int(redis_port)
        if redis_db := os.getenv("TEST_REDIS_DB"):
            self.redis.db = int(redis_db)
        
        # API overrides
        if api_base_url := os.getenv("TEST_API_BASE_URL"):
            self.api.base_url = api_base_url
        
        # Performance overrides
        if max_concurrent := os.getenv("TEST_MAX_CONCURRENT_USERS"):
            self.performance.max_concurrent_users = int(max_concurrent)
        if test_duration := os.getenv("TEST_DURATION_SECONDS"):
            self.performance.test_duration_seconds = int(test_duration)
    
    def get_test_user(self, user_type: str = "test_user") -> Dict[str, Any]:
        """Get test user configuration."""
        return self.auth.test_users.get(user_type, self.auth.test_users["test_user"])
    
    def get_mock_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get mock document by ID."""
        return next(
            (doc for doc in self.search.mock_documents if doc["id"] == doc_id),
            None
        )
    
    def get_mock_documents_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get mock documents by category."""
        return [doc for doc in self.search.mock_documents if doc["category"] == category]
    
    def get_mock_chat_response(self, query_type: str) -> str:
        """Get mock chat response by query type."""
        return self.chat.mock_responses.get(query_type, "I'm here to help with your n8n questions!")
    
    def is_external_service_available(self, service: str) -> bool:
        """Check if external service is available for testing."""
        service_env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "redis": "REDIS_URL",
            "postgres": "DATABASE_URL"
        }
        
        env_var = service_env_vars.get(service.lower())
        if not env_var:
            return False
        
        return bool(os.getenv(env_var))
    
    def should_run_slow_tests(self) -> bool:
        """Check if slow tests should be run."""
        return os.getenv("RUN_SLOW_TESTS", "false").lower() in ("true", "1", "yes")
    
    def should_run_integration_tests(self) -> bool:
        """Check if integration tests should be run."""
        return os.getenv("RUN_INTEGRATION_TESTS", "false").lower() in ("true", "1", "yes")
    
    def should_run_e2e_tests(self) -> bool:
        """Check if end-to-end tests should be run."""
        return os.getenv("RUN_E2E_TESTS", "false").lower() in ("true", "1", "yes")
    
    def get_test_timeout(self, test_type: str = "unit") -> int:
        """Get timeout for different test types."""
        timeouts = {
            "unit": 10,
            "integration": 30,
            "e2e": 60,
            "performance": 300
        }
        return timeouts.get(test_type, 10)
    
    def cleanup(self):
        """Clean up test resources."""
        self.files.cleanup_temp_files()


# Global test configuration instance
test_config = TestConfig()


# Test markers for pytest
PYTEST_MARKERS = {
    "unit": "Unit tests that don't require external dependencies",
    "integration": "Integration tests that require external services",
    "e2e": "End-to-end tests that test complete user workflows",
    "performance": "Performance and load tests",
    "slow": "Tests that take a long time to run",
    "external": "Tests that require external API keys or services",
    "database": "Tests that require database access",
    "redis": "Tests that require Redis access",
    "websocket": "Tests that require WebSocket functionality",
    "auth": "Tests related to authentication and authorization",
    "search": "Tests related to search functionality",
    "chat": "Tests related to chat and AI functionality",
    "api": "Tests related to API endpoints",
    "frontend": "Tests related to frontend components",
    "security": "Security-related tests",
    "regression": "Regression tests for known issues"
}


# Test environment detection
def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    ci_indicators = [
        "CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS",
        "GITLAB_CI", "JENKINS_URL", "BUILDKITE", "CIRCLECI"
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)


def is_local_development() -> bool:
    """Check if running in local development environment."""
    return not is_ci_environment() and os.getenv("ENVIRONMENT", "development") == "development"


def get_test_environment() -> str:
    """Get current test environment."""
    if is_ci_environment():
        return "ci"
    elif is_local_development():
        return "local"
    else:
        return os.getenv("TEST_ENVIRONMENT", "unknown")


# Test data generators
def generate_test_user_data(user_type: str = "standard") -> Dict[str, Any]:
    """Generate test user data."""
    import uuid
    from datetime import datetime
    
    base_data = {
        "id": str(uuid.uuid4()),
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "name": f"Test User {uuid.uuid4().hex[:8]}",
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True
    }
    
    if user_type == "admin":
        base_data.update({
            "is_admin": True,
            "permissions": ["read", "write", "admin"]
        })
    elif user_type == "inactive":
        base_data.update({
            "is_active": False,
            "deactivated_at": datetime.utcnow().isoformat()
        })
    else:
        base_data.update({
            "is_admin": False,
            "permissions": ["read"]
        })
    
    return base_data


def generate_test_document_data(category: str = "tutorial") -> Dict[str, Any]:
    """Generate test document data."""
    import uuid
    from datetime import datetime
    
    categories_data = {
        "tutorial": {
            "tags": ["tutorial", "guide", "learning"],
            "difficulty": "beginner",
            "author": "Tutorial Team"
        },
        "integration": {
            "tags": ["integration", "api", "webhook"],
            "difficulty": "intermediate",
            "author": "Integration Team"
        },
        "advanced": {
            "tags": ["advanced", "expert", "patterns"],
            "difficulty": "advanced",
            "author": "Expert Team"
        }
    }
    
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    category_info = categories_data.get(category, categories_data["tutorial"])
    
    return {
        "id": doc_id,
        "title": f"Test Document {doc_id}",
        "content": f"This is test content for document {doc_id}. It contains information about {category} topics.",
        "url": f"https://docs.example.com/{doc_id}",
        "category": category,
        "tags": category_info["tags"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "word_count": 150,
        "reading_time": 2,
        "difficulty": category_info["difficulty"],
        "author": category_info["author"]
    }


def generate_test_conversation_data(user_id: str) -> Dict[str, Any]:
    """Generate test conversation data."""
    import uuid
    from datetime import datetime
    
    conv_id = f"conv_{uuid.uuid4().hex[:8]}"
    
    return {
        "id": conv_id,
        "title": f"Test Conversation {conv_id}",
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "message_count": 2,
        "status": "active"
    }


if __name__ == "__main__":
    # Print test configuration for debugging
    print("Test Configuration:")
    print(f"Environment: {get_test_environment()}")
    print(f"Database URL: {test_config.database.url}")
    print(f"Redis URL: {test_config.redis.url}")
    print(f"API Base URL: {test_config.api.api_base_url}")
    print(f"External services available:")
    for service in ["openai", "anthropic", "redis", "postgres"]:
        available = test_config.is_external_service_available(service)
        print(f"  {service}: {available}")