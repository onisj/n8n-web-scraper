#!/usr/bin/env python3
"""
N8n Expert AI Agent

This module implements an AI agent that understands n8n workflows, nodes, and best practices.
Designed for integration with TRAE to help users build better n8n systems.
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

# Import the knowledge processor
from n8n_scraper.agents.knowledge_processor import N8nKnowledgeProcessor, ProcessedKnowledge

@dataclass
class AgentResponse:
    """Structure for AI agent responses"""
    response: str
    confidence: float
    sources: List[str]
    suggestions: List[str]
    timestamp: datetime
    
    @property
    def content(self) -> str:
        """Alias for response to match API expectations"""
        return self.response

class N8nExpertAgent:
    """
    AI Agent that provides expert guidance on n8n workflows and integrations.
    
    This agent processes the scraped n8n documentation to provide intelligent
    responses about n8n concepts, best practices, and implementation guidance.
    """
    
    def __init__(self, data_directory: str = "data/scraped_docs"):
        """
        Initialize the N8n Expert Agent.
        
        Args:
            data_directory: Directory containing scraped n8n documentation
        """
        self.data_directory = Path(data_directory)
        self.knowledge_processor = N8nKnowledgeProcessor(data_directory=str(data_directory))
        self.knowledge_base: Optional[ProcessedKnowledge] = None
        self.logger = self._setup_logging()
        
        # Load and process knowledge base
        self._load_knowledge_base()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the agent"""
        logger = logging.getLogger('n8n_expert_agent')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_knowledge_base(self):
        """Load and process the n8n documentation knowledge base"""
        try:
            self.logger.info(f"Loading n8n knowledge base from {self.data_directory}...")
            
            if not self.data_directory.exists():
                self.logger.error(f"Data directory {self.data_directory} not found")
                return
            
            # Process all JSON files in the data directory
            json_files = list(self.data_directory.glob("*.json"))
            self.logger.info(f"Found {len(json_files)} JSON files in data directory")
            
            if not json_files:
                self.logger.warning("No JSON files found in data directory")
                return
            
            self.logger.info("Processing knowledge files...")
            self.knowledge_base = self.knowledge_processor.process_all_files()
            
            if self.knowledge_base and self.knowledge_base.chunks:
                self.logger.info(
                    f"Successfully loaded {len(self.knowledge_base.chunks)} knowledge chunks "
                    f"from {len(json_files)} files"
                )
                # Ensure all chunks have tags attribute for backward compatibility
                self._ensure_chunks_have_tags()
            else:
                self.logger.error("Knowledge base processing returned empty or None")
                self.knowledge_base = None
            
        except Exception as e:
            self.logger.error(f"Error loading knowledge base: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _ensure_chunks_have_tags(self):
        """Ensure all chunks have tags attribute for backward compatibility"""
        for chunk in self.knowledge_base.chunks:
            if not hasattr(chunk, 'tags') or chunk.tags is None:
                chunk.tags = []
    
    def reload_knowledge_base(self):
        """Reload the knowledge base from scratch"""
        self.logger.info("Reloading knowledge base...")
        self.knowledge_base = None
        self._load_knowledge_base()
    
    def get_node_information(self, node_name: str) -> AgentResponse:
        """
        Get detailed information about a specific n8n node.
        
        Args:
            node_name: Name of the n8n node to get information about
            
        Returns:
            AgentResponse with node information and usage examples
        """
        if not self.knowledge_base:
            return AgentResponse(
                response="Knowledge base not loaded. Please ensure data is available.",
                confidence=0.0,
                sources=[],
                suggestions=["Run the scraper to collect n8n documentation"],
                timestamp=datetime.now()
            )
        
        # Search for node-related chunks
        relevant_chunks = []
        node_name_lower = node_name.lower()
        
        for chunk in self.knowledge_base.chunks:
            if (
                node_name_lower in chunk.title.lower() or
                node_name_lower in chunk.content.lower() or
                any(node_name_lower in tag.lower() for tag in chunk.tags)
            ):
                relevant_chunks.append(chunk)
        
        if not relevant_chunks:
            return AgentResponse(
                response=f"No information found for node '{node_name}'. This might be a custom node or the name might be incorrect.",
                confidence=0.1,
                sources=[],
                suggestions=[
                    "Check the node name spelling",
                    "Look for similar node names",
                    "Check if it's a community node"
                ],
                timestamp=datetime.now()
            )
        
        # Compile response from relevant chunks
        response_parts = []
        sources = []
        
        for chunk in relevant_chunks[:3]:  # Limit to top 3 most relevant
            response_parts.append(f"**{chunk.title}**\n{chunk.content[:500]}...")
            sources.append(chunk.url)
        
        response = f"Information about {node_name}:\n\n" + "\n\n".join(response_parts)
        
        suggestions = [
            f"Explore related nodes in the {relevant_chunks[0].category} category",
            "Check the official documentation for the latest updates",
            "Look for workflow examples using this node"
        ]
        
        return AgentResponse(
            response=response,
            confidence=0.8,
            sources=sources,
            suggestions=suggestions,
            timestamp=datetime.now()
        )
    
    def get_workflow_suggestions(self, use_case: str) -> AgentResponse:
        """
        Get workflow suggestions for a specific use case.
        
        Args:
            use_case: Description of what the user wants to achieve
            
        Returns:
            AgentResponse with workflow suggestions and relevant nodes
        """
        if not self.knowledge_base:
            return AgentResponse(
                response="Knowledge base not loaded.",
                confidence=0.0,
                sources=[],
                suggestions=[],
                timestamp=datetime.now()
            )
        
        use_case_lower = use_case.lower()
        relevant_chunks = []
        
        # Search for relevant workflow examples and tutorials
        for chunk in self.knowledge_base.chunks:
            if (
                'workflow' in chunk.content.lower() or
                'example' in chunk.content.lower() or
                'tutorial' in chunk.content.lower() or
                any(keyword in chunk.content.lower() for keyword in use_case_lower.split())
            ):
                relevant_chunks.append(chunk)
        
        if not relevant_chunks:
            return AgentResponse(
                response=f"No specific workflow examples found for '{use_case}'. However, I can provide general guidance.",
                confidence=0.3,
                sources=[],
                suggestions=[
                    "Break down your use case into smaller steps",
                    "Identify the data sources and destinations",
                    "Look for relevant nodes in the integrations section"
                ],
                timestamp=datetime.now()
            )
        
        # Compile workflow suggestions
        response_parts = []
        sources = []
        
        for chunk in relevant_chunks[:5]:  # Top 5 relevant chunks
            if 'example' in chunk.title.lower() or 'tutorial' in chunk.title.lower():
                response_parts.append(f"**{chunk.title}**\n{chunk.content[:400]}...")
                sources.append(chunk.url)
        
        response = f"Workflow suggestions for '{use_case}':\n\n" + "\n\n".join(response_parts)
        
        suggestions = [
            "Start with a simple workflow and iterate",
            "Test each node individually before connecting them",
            "Use the n8n community forum for additional examples",
            "Consider error handling and data validation"
        ]
        
        return AgentResponse(
            response=response,
            confidence=0.7,
            sources=sources,
            suggestions=suggestions,
            timestamp=datetime.now()
        )
    
    def get_best_practices(self, topic: str = "general") -> AgentResponse:
        """
        Get best practices for n8n development.
        
        Args:
            topic: Specific topic for best practices (e.g., 'security', 'performance')
            
        Returns:
            AgentResponse with best practices and recommendations
        """
        if not self.knowledge_base:
            return AgentResponse(
                response="Knowledge base not loaded.",
                confidence=0.0,
                sources=[],
                suggestions=[],
                timestamp=datetime.now()
            )
        
        topic_lower = topic.lower()
        relevant_chunks = []
        
        # Search for best practices, tips, and recommendations
        for chunk in self.knowledge_base.chunks:
            content_lower = chunk.content.lower()
            if (
                'best practice' in content_lower or
                'recommendation' in content_lower or
                'tip' in content_lower or
                'should' in content_lower or
                'avoid' in content_lower or
                topic_lower in content_lower
            ):
                relevant_chunks.append(chunk)
        
        if not relevant_chunks:
            return AgentResponse(
                response=f"No specific best practices found for '{topic}'.",
                confidence=0.2,
                sources=[],
                suggestions=[
                    "Check the general documentation for guidelines",
                    "Look for community discussions on best practices",
                    "Review official n8n examples"
                ],
                timestamp=datetime.now()
            )
        
        # Compile best practices
        response_parts = []
        sources = []
        
        for chunk in relevant_chunks[:4]:  # Top 4 relevant chunks
            response_parts.append(f"**{chunk.title}**\n{chunk.content[:300]}...")
            sources.append(chunk.url)
        
        response = f"Best practices for {topic}:\n\n" + "\n\n".join(response_parts)
        
        suggestions = [
            "Always test workflows in a development environment",
            "Use meaningful names for nodes and workflows",
            "Implement proper error handling",
            "Document your workflows for team collaboration"
        ]
        
        return AgentResponse(
            response=response,
            confidence=0.8,
            sources=sources,
            suggestions=suggestions,
            timestamp=datetime.now()
        )
    
    def search_knowledge(self, query: str) -> AgentResponse:
        """
        Search the knowledge base for specific information.
        
        Args:
            query: Search query
            
        Returns:
            AgentResponse with search results
        """
        if not self.knowledge_base:
            return AgentResponse(
                response="Knowledge base not loaded.",
                confidence=0.0,
                sources=[],
                suggestions=[],
                timestamp=datetime.now()
            )
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        # Score chunks based on query relevance
        scored_chunks = []
        
        for chunk in self.knowledge_base.chunks:
            score = 0
            content_lower = chunk.content.lower()
            title_lower = chunk.title.lower()
            
            # Title matches get higher score
            for term in query_terms:
                if term in title_lower:
                    score += 3
                if term in content_lower:
                    score += 1
                if term in chunk.tags:
                    score += 2
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by score and take top results
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for score, chunk in scored_chunks[:5]]
        
        if not top_chunks:
            return AgentResponse(
                response=f"No results found for '{query}'. Try different keywords or check spelling.",
                confidence=0.1,
                sources=[],
                suggestions=[
                    "Try broader search terms",
                    "Check for typos in your query",
                    "Use specific n8n terminology"
                ],
                timestamp=datetime.now()
            )
        
        # Compile search results
        response_parts = []
        sources = []
        
        for chunk in top_chunks:
            response_parts.append(f"**{chunk.title}**\n{chunk.content[:400]}...")
            sources.append(chunk.url)
        
        response = f"Search results for '{query}':\n\n" + "\n\n".join(response_parts)
        
        confidence = min(0.9, len(top_chunks) * 0.15 + 0.25)
        
        return AgentResponse(
            response=response,
            confidence=confidence,
            sources=sources,
            suggestions=[
                "Refine your search with more specific terms",
                "Check the source documentation for complete details",
                "Look for related topics in the same category"
            ],
            timestamp=datetime.now()
        )
    
    def answer_question(self, question: str, context: Optional[str] = None, max_length: int = 500) -> str:
        """
        Answer a general question about n8n using the knowledge base.
        
        Args:
            question: The question to answer
            context: Optional additional context
            max_length: Maximum length of the response
            
        Returns:
            String response to the question
        """
        if not self.knowledge_base:
            return "I'm sorry, but my knowledge base is not currently loaded. Please ensure the n8n documentation has been scraped and processed."
        
        # Use the search_knowledge method to find relevant information
        search_response = self.search_knowledge(question)
        
        if search_response.confidence < 0.3:
            return f"I couldn't find specific information about '{question}'. You might want to check the official n8n documentation or try rephrasing your question with more specific terms."
        
        # Format the response for better readability
        response = search_response.response
        
        # Truncate if necessary
        if len(response) > max_length:
            response = response[:max_length] + "..."
        
        return response
    
    def get_node_info(self, node_name: str, include_examples: bool = True) -> str:
        """
        Get information about a specific n8n node.
        
        Args:
            node_name: Name of the node
            include_examples: Whether to include usage examples
            
        Returns:
            String with node information
        """
        response = self.get_node_information(node_name)
        return response.response
    
    def suggest_workflow(self, description: str, complexity: str = "medium", include_nodes: Optional[List[str]] = None) -> str:
        """
        Suggest a workflow based on the description.
        
        Args:
            description: Description of the desired workflow
            complexity: Complexity level (simple, medium, complex)
            include_nodes: Preferred nodes to include
            
        Returns:
            String with workflow suggestions
        """
        response = self.get_workflow_suggestions(description)
        return response.response
    
    def get_best_practices_list(self, category: Optional[str] = None) -> List[str]:
        """
        Get best practices for n8n as a list.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of best practice strings
        """
        topic = category or "general"
        response = self.get_best_practices(topic)
        
        # Extract practices from the response
        practices = []
        lines = response.response.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('**'):
                practices.append(line.strip())
        
        return practices[:10]  # Return top 10 practices

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded knowledge base.
        
        Returns:
            Dictionary with knowledge base statistics
        """
        if not self.knowledge_base:
            return {"status": "Knowledge base not loaded"}
        
        categories = {}
        total_content_length = 0
        
        for chunk in self.knowledge_base.chunks:
            category = chunk.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
            total_content_length += len(chunk.content)
        
        return {
            "total_chunks": len(self.knowledge_base.chunks),
            "categories": categories,
            "total_content_length": total_content_length,
            "average_chunk_size": total_content_length // len(self.knowledge_base.chunks) if self.knowledge_base.chunks else 0,
            "last_updated": self.knowledge_base.metadata.get("processed_at", "Unknown")
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize the agent using agent manager to prevent duplicates
    from n8n_scraper.optimization.agent_manager import get_expert_agent
    
    agent = get_expert_agent()
    
    # Test the agent with some queries
    print("=== N8n Expert Agent Test ===")
    
    # Test node information
    print("\n1. Testing node information:")
    response = agent.get_node_information("HTTP Request")
    print(f"Response: {response.response[:200]}...")
    print(f"Confidence: {response.confidence}")
    
    # Test workflow suggestions
    print("\n2. Testing workflow suggestions:")
    response = agent.get_workflow_suggestions("send email notifications")
    print(f"Response: {response.response[:200]}...")
    print(f"Confidence: {response.confidence}")
    
    # Test knowledge search
    print("\n3. Testing knowledge search:")
    response = agent.search_knowledge("API authentication")
    print(f"Response: {response.response[:200]}...")
    print(f"Confidence: {response.confidence}")
    
    # Show knowledge stats
    print("\n4. Knowledge base statistics:")
    stats = agent.get_knowledge_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")