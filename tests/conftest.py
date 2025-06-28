#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set testing environment
os.environ['TESTING'] = 'true'
os.environ['LOG_LEVEL'] = 'WARNING'


@pytest.fixture(scope="session")
def project_root_path():
    """Get project root path"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root_path):
    """Create test data directory"""
    test_dir = project_root_path / "tests" / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    test_env = {
        'OPENAI_API_KEY': 'test_openai_key',
        'ANTHROPIC_API_KEY': 'test_anthropic_key',
        'N8N_API_KEY': 'test_n8n_key',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        yield test_env


@pytest.fixture
def sample_n8n_docs():
    """Sample n8n documentation data for testing"""
    return [
        {
            'id': 'getting-started',
            'title': 'Getting Started with n8n',
            'content': '''
            n8n is a powerful workflow automation tool that helps you connect different services and automate repetitive tasks.
            
            ## Installation
            You can install n8n using npm:
            ```bash
            npm install n8n -g
            ```
            
            ## First Workflow
            Create your first workflow by adding nodes and connecting them.
            ''',
            'url': 'https://docs.n8n.io/getting-started/',
            'metadata': {
                'category': 'getting-started',
                'tags': ['basics', 'installation', 'workflow'],
                'last_updated': '2024-01-15',
                'difficulty': 'beginner'
            }
        },
        {
            'id': 'webhooks-guide',
            'title': 'Working with Webhooks',
            'content': '''
            Webhooks allow external services to trigger your n8n workflows.
            
            ## Creating a Webhook
            1. Add a Webhook node to your workflow
            2. Configure the HTTP method and path
            3. Set up authentication if needed
            
            ## Testing Webhooks
            Use the test webhook feature to verify your setup.
            ''',
            'url': 'https://docs.n8n.io/webhooks/',
            'metadata': {
                'category': 'webhooks',
                'tags': ['webhooks', 'triggers', 'http', 'api'],
                'last_updated': '2024-01-10',
                'difficulty': 'intermediate'
            }
        },
        {
            'id': 'custom-nodes',
            'title': 'Creating Custom Nodes',
            'content': '''
            Extend n8n functionality by creating custom nodes.
            
            ## Development Setup
            1. Clone the n8n repository
            2. Set up the development environment
            3. Create your node structure
            
            ## Node Implementation
            Implement the execute method and define node properties.
            ''',
            'url': 'https://docs.n8n.io/nodes/creating-nodes/',
            'metadata': {
                'category': 'development',
                'tags': ['custom-nodes', 'typescript', 'development', 'api'],
                'last_updated': '2024-01-05',
                'difficulty': 'advanced'
            }
        },
        {
            'id': 'error-handling',
            'title': 'Error Handling in Workflows',
            'content': '''
            Learn how to handle errors gracefully in your n8n workflows.
            
            ## Error Workflow
            Set up error workflows to handle failures.
            
            ## Retry Logic
            Configure retry settings for unreliable services.
            
            ## Monitoring
            Use execution logs to monitor workflow health.
            ''',
            'url': 'https://docs.n8n.io/error-handling/',
            'metadata': {
                'category': 'best-practices',
                'tags': ['error-handling', 'monitoring', 'reliability'],
                'last_updated': '2024-01-12',
                'difficulty': 'intermediate'
            }
        }
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        'choices': [{
            'message': {
                'content': 'This is a helpful response about n8n workflows and automation.'
            }
        }],
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response"""
    return {
        'content': [{
            'text': 'This is a helpful response about n8n from Claude.'
        }],
        'usage': {
            'input_tokens': 100,
            'output_tokens': 50
        }
    }


@pytest.fixture
def mock_vector_search_results():
    """Mock vector search results"""
    return [
        {
            'id': 'doc_1',
            'content': 'n8n is a workflow automation tool that connects different services.',
            'metadata': {
                'title': 'Introduction to n8n',
                'url': 'https://docs.n8n.io/getting-started/',
                'category': 'getting-started'
            },
            'score': 0.95
        },
        {
            'id': 'doc_2',
            'content': 'Webhooks in n8n allow external services to trigger workflows.',
            'metadata': {
                'title': 'Working with Webhooks',
                'url': 'https://docs.n8n.io/webhooks/',
                'category': 'webhooks'
            },
            'score': 0.88
        }
    ]


@pytest.fixture
def mock_database_stats():
    """Mock database statistics"""
    return {
        'total_documents': 150,
        'total_chunks': 750,
        'collections': ['n8n_docs'],
        'last_updated': '2024-01-15T10:30:00Z',
        'index_size': '25.6 MB'
    }


@pytest.fixture
def mock_system_status():
    """Mock system status"""
    return {
        'api': {'status': 'healthy', 'uptime': 3600},
        'database': {'status': 'healthy', 'connections': 5},
        'vector_db': {'status': 'healthy', 'documents': 150},
        'agents': {'status': 'healthy', 'active_conversations': 3},
        'memory_usage': '45%',
        'cpu_usage': '12%',
        'disk_usage': '67%'
    }


@pytest.fixture
def mock_conversation_history():
    """Mock conversation history"""
    return [
        {
            'id': 'msg_1',
            'role': 'user',
            'content': 'How do I create a webhook in n8n?',
            'timestamp': '2024-01-15T10:00:00Z'
        },
        {
            'id': 'msg_2',
            'role': 'assistant',
            'content': 'To create a webhook in n8n, follow these steps...',
            'timestamp': '2024-01-15T10:00:05Z',
            'sources': ['webhooks-guide']
        },
        {
            'id': 'msg_3',
            'role': 'user',
            'content': 'Can I secure the webhook?',
            'timestamp': '2024-01-15T10:01:00Z'
        },
        {
            'id': 'msg_4',
            'role': 'assistant',
            'content': 'Yes, you can secure webhooks using authentication...',
            'timestamp': '2024-01-15T10:01:03Z',
            'sources': ['webhooks-guide', 'security-guide']
        }
    ]


# Pytest hooks
def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers based on test names/paths
    for item in items:
        # Mark slow tests
        if "slow" in item.name or "integration" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Mark external service tests
        if any(keyword in item.name.lower() for keyword in ['openai', 'anthropic', 'external']):
            item.add_marker(pytest.mark.external)
        
        # Mark database tests
        if "database" in str(item.fspath) or "db" in item.name:
            item.add_marker(pytest.mark.database)
        
        # Mark API tests
        if "api" in str(item.fspath) or "api" in item.name:
            item.add_marker(pytest.mark.api)
        
        # Mark agent tests
        if "agent" in str(item.fspath) or "agent" in item.name:
            item.add_marker(pytest.mark.agents)


def pytest_runtest_setup(item):
    """Setup for each test"""
    # Skip external tests if no API keys
    if item.get_closest_marker("external"):
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('ANTHROPIC_API_KEY'):
            pytest.skip("External API keys not available")


def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("\n🧪 Starting n8n AI Knowledge System test suite...")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    if exitstatus == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests finished with exit status: {exitstatus}")


# Skip tests if dependencies are not available
def pytest_runtest_setup(item):
    """Setup for individual tests"""
    # Skip tests that require specific modules
    test_file = str(item.fspath)
    
    if "test_api" in test_file:
        try:
            import fastapi
            import uvicorn
        except ImportError:
            pytest.skip("FastAPI dependencies not available")
    
    elif "test_database" in test_file:
        try:
            import chromadb
        except ImportError:
            pytest.skip("ChromaDB not available")
    
    elif "test_agents" in test_file:
        try:
            import openai
        except ImportError:
            try:
                import anthropic
            except ImportError:
                pytest.skip("No AI provider libraries available")


# Custom assertions
class CustomAssertions:
    """Custom assertion helpers"""
    
    @staticmethod
    def assert_valid_response(response_data):
        """Assert that API response has valid structure"""
        assert isinstance(response_data, dict)
        assert 'response' in response_data or 'results' in response_data
    
    @staticmethod
    def assert_valid_search_result(result):
        """Assert that search result has valid structure"""
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'content' in result
        assert 'metadata' in result
        assert 'score' in result
        assert 0 <= result['score'] <= 1
    
    @staticmethod
    def assert_valid_document(document):
        """Assert that document has valid structure"""
        assert isinstance(document, dict)
        assert 'id' in document
        assert 'content' in document
        assert 'metadata' in document
        assert isinstance(document['metadata'], dict)


@pytest.fixture
def assertions():
    """Provide custom assertions"""
    return CustomAssertions()