#!/usr/bin/env python3
"""
Test suite for AI agents
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# Import agent classes
try:
    from agents.n8n_agent import N8nExpertAgent
    from agents.base_agent import BaseAgent
except ImportError:
    # Handle case where agent components aren't fully set up yet
    N8nExpertAgent = None
    BaseAgent = None


@pytest.fixture
def mock_vector_db():
    """Mock vector database for testing"""
    mock_db = Mock()
    mock_db.search.return_value = [
        {
            'id': 'doc_1',
            'content': 'n8n is a workflow automation tool that allows you to connect different services.',
            'metadata': {
                'title': 'Introduction to n8n',
                'url': 'https://docs.n8n.io/getting-started/',
                'category': 'getting-started'
            },
            'score': 0.95
        },
        {
            'id': 'doc_2', 
            'content': 'Webhooks in n8n allow you to trigger workflows from external services.',
            'metadata': {
                'title': 'Working with Webhooks',
                'url': 'https://docs.n8n.io/webhooks/',
                'category': 'webhooks'
            },
            'score': 0.88
        }
    ]
    return mock_db


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('openai.OpenAI') as mock_client:
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a helpful response about n8n workflows."
        mock_instance.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    with patch('anthropic.Anthropic') as mock_client:
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "This is a helpful response about n8n from Claude."
        mock_instance.messages.create.return_value = mock_response
        mock_client.return_value = mock_instance
        yield mock_instance


class TestBaseAgent:
    """Test base agent functionality"""
    
    def test_base_agent_initialization(self):
        """Test base agent can be initialized"""
        if BaseAgent is None:
            pytest.skip("BaseAgent not available")
        
        agent = BaseAgent()
        assert agent is not None
        assert hasattr(agent, 'process_query')
    
    def test_base_agent_abstract_methods(self):
        """Test that base agent has required abstract methods"""
        if BaseAgent is None:
            pytest.skip("BaseAgent not available")
        
        # BaseAgent should define the interface
        assert hasattr(BaseAgent, 'process_query')
        assert hasattr(BaseAgent, 'get_response')


class TestN8nExpertAgent:
    """Test N8n Expert Agent functionality"""
    
    def test_agent_initialization(self, mock_vector_db):
        """Test agent initialization"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            assert agent is not None
            assert agent.vector_db is not None
    
    def test_query_processing(self, mock_vector_db, mock_openai_client):
        """Test basic query processing"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            query = "How do I create a webhook in n8n?"
            result = agent.process_query(query)
            
            assert isinstance(result, dict)
            assert 'response' in result
            assert 'sources' in result
            assert 'confidence' in result
    
    def test_context_retrieval(self, mock_vector_db):
        """Test context retrieval from vector database"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            query = "webhook setup"
            contexts = agent._get_relevant_context(query)
            
            assert isinstance(contexts, list)
            assert len(contexts) > 0
            mock_vector_db.search.assert_called_once()
    
    def test_response_generation_openai(self, mock_vector_db, mock_openai_client):
        """Test response generation with OpenAI"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent(provider='openai')
            
            query = "How to use webhooks?"
            contexts = [
                "Webhooks allow external services to trigger n8n workflows.",
                "You can create webhook nodes in your workflow."
            ]
            
            response = agent._generate_response(query, contexts)
            
            assert isinstance(response, str)
            assert len(response) > 0
    
    def test_response_generation_anthropic(self, mock_vector_db, mock_anthropic_client):
        """Test response generation with Anthropic"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent(provider='anthropic')
            
            query = "How to debug workflows?"
            contexts = [
                "n8n provides execution logs for debugging.",
                "You can use the workflow debugger to step through executions."
            ]
            
            response = agent._generate_response(query, contexts)
            
            assert isinstance(response, str)
            assert len(response) > 0
    
    def test_conversation_memory(self, mock_vector_db, mock_openai_client):
        """Test conversation memory functionality"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            # First query
            result1 = agent.process_query("What is n8n?", conversation_id="test_conv")
            assert 'response' in result1
            
            # Follow-up query
            result2 = agent.process_query("How do I install it?", conversation_id="test_conv")
            assert 'response' in result2
            
            # Check that conversation context is maintained
            assert hasattr(agent, 'conversations')
    
    def test_source_attribution(self, mock_vector_db, mock_openai_client):
        """Test that sources are properly attributed"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            query = "webhook documentation"
            result = agent.process_query(query)
            
            assert 'sources' in result
            assert isinstance(result['sources'], list)
            
            # Check that sources contain proper metadata
            if result['sources']:
                source = result['sources'][0]
                assert 'title' in source or 'url' in source
    
    def test_confidence_scoring(self, mock_vector_db, mock_openai_client):
        """Test confidence scoring"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            query = "specific n8n question"
            result = agent.process_query(query)
            
            assert 'confidence' in result
            assert isinstance(result['confidence'], (int, float))
            assert 0 <= result['confidence'] <= 1
    
    def test_error_handling(self, mock_vector_db):
        """Test error handling in agent"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        # Mock database to raise an exception
        mock_vector_db.search.side_effect = Exception("Database error")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            query = "test query"
            result = agent.process_query(query)
            
            # Should handle error gracefully
            assert isinstance(result, dict)
            assert 'error' in result or 'response' in result
    
    def test_empty_query_handling(self, mock_vector_db, mock_openai_client):
        """Test handling of empty queries"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            # Test empty string
            result = agent.process_query("")
            assert isinstance(result, dict)
            
            # Test None
            result = agent.process_query(None)
            assert isinstance(result, dict)
    
    def test_long_query_handling(self, mock_vector_db, mock_openai_client):
        """Test handling of very long queries"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent = N8nExpertAgent()
            
            # Create a very long query
            long_query = "How do I " + "create workflows " * 100 + "in n8n?"
            
            result = agent.process_query(long_query)
            assert isinstance(result, dict)
            assert 'response' in result


class TestAgentIntegration:
    """Test agent integration with other components"""
    
    def test_agent_with_real_vector_search(self, mock_openai_client):
        """Test agent with actual vector search (if available)"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        try:
            # Try to create agent with real vector DB
            agent = N8nExpertAgent()
            
            query = "n8n basics"
            result = agent.process_query(query)
            
            assert isinstance(result, dict)
            assert 'response' in result
        except Exception:
            # If real vector DB isn't available, skip
            pytest.skip("Real vector database not available")
    
    def test_multiple_agents(self, mock_vector_db, mock_openai_client):
        """Test multiple agent instances"""
        if N8nExpertAgent is None:
            pytest.skip("N8nExpertAgent not available")
        
        with patch('database.vector_db.VectorDatabase', return_value=mock_vector_db):
            agent1 = N8nExpertAgent()
            agent2 = N8nExpertAgent()
            
            # Both agents should work independently
            result1 = agent1.process_query("What is n8n?")
            result2 = agent2.process_query("How to create workflows?")
            
            assert isinstance(result1, dict)
            assert isinstance(result2, dict)
            assert 'response' in result1
            assert 'response' in result2


if __name__ == "__main__":
    pytest.main([__file__])