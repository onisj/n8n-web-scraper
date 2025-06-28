# TRAE Integration & Deployment Guide

## Table of Contents

1. [TRAE Integration Overview](#trae-integration-overview)
2. [Integration Setup](#integration-setup)
3. [TRAE Agent Implementation](#trae-agent-implementation)
4. [API Integration Patterns](#api-integration-patterns)
5. [Deployment Strategies](#deployment-strategies)
6. [Configuration Management](#configuration-management)
7. [Monitoring & Logging](#monitoring--logging)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Configurations](#advanced-configurations)

## TRAE Integration Overview

This guide explains how to integrate the n8n AI Expert Agent with TRAE (Trae AI), enabling seamless access to n8n knowledge and assistance within the TRAE environment.

### Integration Benefits

- **Seamless Knowledge Access**: Direct access to n8n documentation and expertise
- **Context-Aware Responses**: AI responses tailored to n8n workflows and concepts
- **Real-Time Updates**: Always current with latest n8n documentation
- **Multi-Modal Support**: Text, code examples, and workflow suggestions
- **Scalable Architecture**: Handles multiple concurrent TRAE sessions

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TRAE Agent    │───▶│  n8n API Server │───▶│ Vector Database │
│   (Frontend)    │    │  (Port 8000)    │    │   (ChromaDB)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   AI Agents     │    │  Knowledge Base │
         │              │ (OpenAI/Claude) │    │ (1000+ docs)    │
         │              └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ TRAE Interface  │
│   (User UI)     │
└─────────────────┘
```

## Integration Setup

### Prerequisites

- Running n8n AI Knowledge System
- TRAE development environment
- API access credentials
- Network connectivity between TRAE and n8n system

### Quick Setup

1. **Ensure n8n System is Running**:
   ```bash
   # Start the n8n AI system
   python start_system.py
   
   # Verify API is accessible
   curl http://localhost:8000/api/health
   ```

2. **Configure TRAE Environment**:
   ```bash
   # Set environment variables in TRAE
   export N8N_API_BASE_URL="http://localhost:8000"
   export N8N_API_KEY="your_api_key_here"
   ```

3. **Test Connection**:
   ```bash
   # Test API connectivity
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8000/api/health"
   ```

## TRAE Agent Implementation

### Basic TRAE Agent

Here's a complete TRAE agent implementation for n8n assistance:

```python
# trae_n8n_agent.py
import requests
import json
from typing import Dict, List, Optional

class N8nTraeAgent:
    """TRAE Agent for n8n AI Knowledge System Integration"""
    
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def query_knowledge(self, query: str, max_results: int = 5) -> Dict:
        """Query the n8n knowledge base"""
        endpoint = f"{self.api_base_url}/api/query"
        payload = {
            "query": query,
            "max_results": max_results,
            "include_metadata": True
        }
        
        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
    
    def get_workflow_help(self, workflow_type: str) -> Dict:
        """Get help for specific workflow types"""
        query = f"How to create {workflow_type} workflow in n8n"
        return self.query_knowledge(query)
    
    def get_node_documentation(self, node_name: str) -> Dict:
        """Get documentation for specific n8n nodes"""
        query = f"{node_name} node documentation configuration examples"
        return self.query_knowledge(query)
    
    def troubleshoot_issue(self, issue_description: str) -> Dict:
        """Get troubleshooting help for n8n issues"""
        query = f"n8n troubleshooting: {issue_description}"
        return self.query_knowledge(query)
    
    def get_best_practices(self, topic: str) -> Dict:
        """Get n8n best practices for specific topics"""
        query = f"n8n best practices {topic}"
        return self.query_knowledge(query)
    
    def health_check(self) -> Dict:
        """Check if the n8n API is healthy"""
        endpoint = f"{self.api_base_url}/api/health"
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Health check failed: {str(e)}"}

# TRAE Integration Functions
def create_n8n_agent() -> N8nTraeAgent:
    """Factory function to create n8n TRAE agent"""
    import os
    
    api_base_url = os.getenv('N8N_API_BASE_URL', 'http://localhost:8000')
    api_key = os.getenv('N8N_API_KEY', 'default_key')
    
    return N8nTraeAgent(api_base_url, api_key)

def handle_n8n_query(user_input: str) -> str:
    """Main handler for n8n-related queries in TRAE"""
    agent = create_n8n_agent()
    
    # Check if system is healthy
    health = agent.health_check()
    if 'error' in health:
        return f"n8n AI system is not available: {health['error']}"
    
    # Process the query
    result = agent.query_knowledge(user_input)
    
    if 'error' in result:
        return f"Error querying n8n knowledge: {result['error']}"
    
    # Format response for TRAE
    if result.get('results'):
        response = "Based on n8n documentation:\n\n"
        for i, item in enumerate(result['results'][:3], 1):
            response += f"{i}. {item['content'][:200]}...\n"
            if item.get('metadata', {}).get('source'):
                response += f"   Source: {item['metadata']['source']}\n"
            response += "\n"
        return response
    else:
        return "No relevant information found in n8n documentation."

# TRAE Command Handlers
def handle_workflow_command(workflow_type: str) -> str:
    """Handle workflow creation commands"""
    agent = create_n8n_agent()
    result = agent.get_workflow_help(workflow_type)
    
    if 'error' in result:
        return f"Error: {result['error']}"
    
    if result.get('results'):
        return f"Here's how to create a {workflow_type} workflow in n8n:\n\n{result['results'][0]['content']}"
    else:
        return f"No specific information found for {workflow_type} workflows."

def handle_node_command(node_name: str) -> str:
    """Handle node documentation commands"""
    agent = create_n8n_agent()
    result = agent.get_node_documentation(node_name)
    
    if 'error' in result:
        return f"Error: {result['error']}"
    
    if result.get('results'):
        return f"Documentation for {node_name} node:\n\n{result['results'][0]['content']}"
    else:
        return f"No documentation found for {node_name} node."

def handle_troubleshoot_command(issue: str) -> str:
    """Handle troubleshooting commands"""
    agent = create_n8n_agent()
    result = agent.troubleshoot_issue(issue)
    
    if 'error' in result:
        return f"Error: {result['error']}"
    
    if result.get('results'):
        return f"Troubleshooting help for '{issue}':\n\n{result['results'][0]['content']}"
    else:
        return f"No troubleshooting information found for '{issue}'."
```

### Advanced TRAE Agent with Context

```python
# advanced_trae_n8n_agent.py
class AdvancedN8nTraeAgent(N8nTraeAgent):
    """Advanced TRAE agent with conversation context"""
    
    def __init__(self, api_base_url: str, api_key: str):
        super().__init__(api_base_url, api_key)
        self.conversation_context = []
        self.user_preferences = {}
    
    def add_context(self, user_input: str, response: str):
        """Add conversation context"""
        self.conversation_context.append({
            'user_input': user_input,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 10 interactions
        if len(self.conversation_context) > 10:
            self.conversation_context = self.conversation_context[-10:]
    
    def get_contextual_response(self, user_input: str) -> str:
        """Get response with conversation context"""
        # Build context-aware query
        context_query = user_input
        if self.conversation_context:
            recent_topics = [ctx['user_input'] for ctx in self.conversation_context[-3:]]
            context_query = f"Context: {' '.join(recent_topics)}. Current question: {user_input}"
        
        result = self.query_knowledge(context_query)
        response = self._format_response(result)
        
        # Add to context
        self.add_context(user_input, response)
        
        return response
    
    def _format_response(self, result: Dict) -> str:
        """Format API response for TRAE display"""
        if 'error' in result:
            return f"❌ Error: {result['error']}"
        
        if not result.get('results'):
            return "ℹ️ No relevant information found in n8n documentation."
        
        response = "📚 **n8n Documentation:**\n\n"
        
        for i, item in enumerate(result['results'][:2], 1):
            content = item['content'][:300]
            if len(item['content']) > 300:
                content += "..."
            
            response += f"**{i}.** {content}\n"
            
            if item.get('metadata', {}).get('source'):
                response += f"   📄 *Source: {item['metadata']['source']}*\n"
            response += "\n"
        
        return response
```

## API Integration Patterns

### Synchronous Integration

```python
# sync_integration.py
def sync_n8n_query(query: str) -> Dict:
    """Synchronous query to n8n API"""
    agent = create_n8n_agent()
    return agent.query_knowledge(query)

# Usage in TRAE
def trae_sync_handler(user_input: str) -> str:
    result = sync_n8n_query(user_input)
    return format_response(result)
```

### Asynchronous Integration

```python
# async_integration.py
import asyncio
import aiohttp

class AsyncN8nAgent:
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
    
    async def query_knowledge_async(self, query: str) -> Dict:
        """Async query to n8n knowledge base"""
        endpoint = f"{self.api_base_url}/api/query"
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            "query": query,
            "max_results": 5,
            "include_metadata": True
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                return {"error": f"API request failed: {str(e)}"}

# Usage in TRAE
async def trae_async_handler(user_input: str) -> str:
    agent = AsyncN8nAgent(
        os.getenv('N8N_API_BASE_URL', 'http://localhost:8000'),
        os.getenv('N8N_API_KEY', 'default_key')
    )
    result = await agent.query_knowledge_async(user_input)
    return format_response(result)
```

### Batch Processing Integration

```python
# batch_integration.py
def batch_n8n_queries(queries: List[str]) -> List[Dict]:
    """Process multiple queries in batch"""
    agent = create_n8n_agent()
    results = []
    
    for query in queries:
        result = agent.query_knowledge(query)
        results.append(result)
    
    return results

# Usage for complex TRAE workflows
def trae_batch_handler(user_inputs: List[str]) -> List[str]:
    results = batch_n8n_queries(user_inputs)
    return [format_response(result) for result in results]
```

## Deployment Strategies

### Local Development Deployment

```bash
# Start n8n system locally
python start_system.py

# Configure TRAE environment
export N8N_API_BASE_URL="http://localhost:8000"
export N8N_API_KEY="dev_key"

# Test integration
python test_trae_integration.py
```

### Docker Deployment

```yaml
# docker-compose.trae.yml
version: '3.8'

services:
  n8n-knowledge-system:
    build: .
    ports:
      - "8000:8000"
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - API_KEY=${N8N_API_KEY}
    volumes:
      - ./data:/app/data
    networks:
      - trae-network
  
  trae-agent:
    build: ./trae-integration
    environment:
      - N8N_API_BASE_URL=http://n8n-knowledge-system:8000
      - N8N_API_KEY=${N8N_API_KEY}
    depends_on:
      - n8n-knowledge-system
    networks:
      - trae-network

networks:
  trae-network:
    driver: bridge
```

### Production Deployment

```bash
# Production deployment script
#!/bin/bash

# Deploy n8n system
docker-compose -f docker-compose.prod.yml up -d

# Wait for system to be ready
while ! curl -f http://localhost:8000/api/health; do
  echo "Waiting for n8n system..."
  sleep 5
done

# Deploy TRAE integration
kubectl apply -f k8s/trae-n8n-integration.yaml

# Verify deployment
kubectl get pods -l app=trae-n8n
```

### Kubernetes Deployment

```yaml
# k8s/trae-n8n-integration.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: n8n-knowledge-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: n8n-knowledge
  template:
    metadata:
      labels:
        app: n8n-knowledge
    spec:
      containers:
      - name: n8n-api
        image: n8n-knowledge-system:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: openai-key
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: n8n-api-key
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: n8n-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: n8n-knowledge-service
spec:
  selector:
    app: n8n-knowledge
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

## Configuration Management

### Environment Configuration

```python
# trae_config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class TraeN8nConfig:
    """Configuration for TRAE-n8n integration"""
    api_base_url: str
    api_key: str
    timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 300  # 5 minutes
    max_results: int = 5
    enable_context: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> 'TraeN8nConfig':
        """Create config from environment variables"""
        return cls(
            api_base_url=os.getenv('N8N_API_BASE_URL', 'http://localhost:8000'),
            api_key=os.getenv('N8N_API_KEY', 'default_key'),
            timeout=int(os.getenv('N8N_TIMEOUT', '30')),
            max_retries=int(os.getenv('N8N_MAX_RETRIES', '3')),
            cache_ttl=int(os.getenv('N8N_CACHE_TTL', '300')),
            max_results=int(os.getenv('N8N_MAX_RESULTS', '5')),
            enable_context=os.getenv('N8N_ENABLE_CONTEXT', 'true').lower() == 'true',
            log_level=os.getenv('N8N_LOG_LEVEL', 'INFO')
        )

# Usage
config = TraeN8nConfig.from_env()
agent = N8nTraeAgent(config.api_base_url, config.api_key)
```

### Dynamic Configuration

```python
# dynamic_config.py
class DynamicConfig:
    """Dynamic configuration management"""
    
    def __init__(self):
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from multiple sources"""
        # Environment variables
        self.config.update(self._load_from_env())
        
        # Configuration file
        self.config.update(self._load_from_file())
        
        # Remote configuration (if available)
        self.config.update(self._load_from_remote())
    
    def _load_from_env(self) -> dict:
        """Load from environment variables"""
        return {
            'api_base_url': os.getenv('N8N_API_BASE_URL', 'http://localhost:8000'),
            'api_key': os.getenv('N8N_API_KEY', 'default_key'),
            'timeout': int(os.getenv('N8N_TIMEOUT', '30'))
        }
    
    def _load_from_file(self) -> dict:
        """Load from configuration file"""
        try:
            with open('trae_n8n_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _load_from_remote(self) -> dict:
        """Load from remote configuration service"""
        # Implement remote config loading if needed
        return {}
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def update(self, key: str, value):
        """Update configuration value"""
        self.config[key] = value
```

## Monitoring & Logging

### Logging Configuration

```python
# logging_config.py
import logging
import sys
from datetime import datetime

def setup_trae_logging(log_level: str = "INFO"):
    """Setup logging for TRAE integration"""
    
    # Create logger
    logger = logging.getLogger('trae_n8n')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler('trae_n8n_integration.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Usage
logger = setup_trae_logging()

class LoggedN8nAgent(N8nTraeAgent):
    """N8n agent with comprehensive logging"""
    
    def __init__(self, api_base_url: str, api_key: str):
        super().__init__(api_base_url, api_key)
        self.logger = logging.getLogger('trae_n8n')
    
    def query_knowledge(self, query: str, max_results: int = 5) -> Dict:
        """Query with logging"""
        self.logger.info(f"Querying n8n knowledge: {query[:100]}...")
        start_time = datetime.now()
        
        try:
            result = super().query_knowledge(query, max_results)
            duration = (datetime.now() - start_time).total_seconds()
            
            if 'error' in result:
                self.logger.error(f"Query failed: {result['error']}")
            else:
                self.logger.info(f"Query successful in {duration:.2f}s, {len(result.get('results', []))} results")
            
            return result
            
        except Exception as e:
            self.logger.exception(f"Unexpected error during query: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
```

### Metrics Collection

```python
# metrics.py
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import threading

class TraeMetrics:
    """Metrics collection for TRAE integration"""
    
    def __init__(self):
        self.query_count = Counter()
        self.response_times = []
        self.error_count = Counter()
        self.last_reset = datetime.now()
        self._lock = threading.Lock()
    
    def record_query(self, query_type: str, response_time: float, success: bool):
        """Record query metrics"""
        with self._lock:
            self.query_count[query_type] += 1
            self.response_times.append(response_time)
            
            if not success:
                self.error_count[query_type] += 1
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        with self._lock:
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            return {
                'total_queries': sum(self.query_count.values()),
                'query_types': dict(self.query_count),
                'avg_response_time': avg_response_time,
                'error_rate': sum(self.error_count.values()) / sum(self.query_count.values()) if self.query_count else 0,
                'errors_by_type': dict(self.error_count),
                'uptime': (datetime.now() - self.last_reset).total_seconds()
            }
    
    def reset(self):
        """Reset metrics"""
        with self._lock:
            self.query_count.clear()
            self.response_times.clear()
            self.error_count.clear()
            self.last_reset = datetime.now()

# Global metrics instance
metrics = TraeMetrics()

class MetricsN8nAgent(LoggedN8nAgent):
    """N8n agent with metrics collection"""
    
    def query_knowledge(self, query: str, max_results: int = 5) -> Dict:
        """Query with metrics collection"""
        start_time = datetime.now()
        
        result = super().query_knowledge(query, max_results)
        
        duration = (datetime.now() - start_time).total_seconds()
        success = 'error' not in result
        
        metrics.record_query('knowledge_query', duration, success)
        
        return result
```

## Best Practices

### Error Handling

```python
# error_handling.py
from functools import wraps
import time

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying failed API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        continue
                    break
            
            # All retries failed
            raise last_exception
        return wrapper
    return decorator

class RobustN8nAgent(MetricsN8nAgent):
    """Robust n8n agent with error handling"""
    
    @retry_on_failure(max_retries=3)
    def query_knowledge(self, query: str, max_results: int = 5) -> Dict:
        """Query with retry logic"""
        return super().query_knowledge(query, max_results)
    
    def safe_query(self, query: str, fallback_response: str = None) -> str:
        """Safe query with fallback"""
        try:
            result = self.query_knowledge(query)
            
            if 'error' in result:
                self.logger.warning(f"API error: {result['error']}")
                return fallback_response or "I'm having trouble accessing the n8n documentation right now. Please try again later."
            
            return self._format_response(result)
            
        except Exception as e:
            self.logger.exception(f"Unexpected error: {str(e)}")
            return fallback_response or "An unexpected error occurred. Please try again later."
```

### Caching

```python
# caching.py
from functools import lru_cache
import hashlib
import json
import time
from typing import Dict, Optional

class QueryCache:
    """Simple query cache for TRAE integration"""
    
    def __init__(self, ttl: int = 300):  # 5 minutes default TTL
        self.cache = {}
        self.ttl = ttl
    
    def _hash_query(self, query: str) -> str:
        """Create hash for query"""
        return hashlib.md5(query.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[Dict]:
        """Get cached result"""
        key = self._hash_query(query)
        
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[key]
        
        return None
    
    def set(self, query: str, result: Dict):
        """Cache result"""
        key = self._hash_query(query)
        self.cache[key] = (result, time.time())
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()

class CachedN8nAgent(RobustN8nAgent):
    """N8n agent with caching"""
    
    def __init__(self, api_base_url: str, api_key: str, cache_ttl: int = 300):
        super().__init__(api_base_url, api_key)
        self.cache = QueryCache(cache_ttl)
    
    def query_knowledge(self, query: str, max_results: int = 5) -> Dict:
        """Query with caching"""
        # Check cache first
        cached_result = self.cache.get(query)
        if cached_result:
            self.logger.debug(f"Cache hit for query: {query[:50]}...")
            return cached_result
        
        # Query API
        result = super().query_knowledge(query, max_results)
        
        # Cache successful results
        if 'error' not in result:
            self.cache.set(query, result)
        
        return result
```

### Performance Optimization

```python
# performance.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

class OptimizedN8nAgent(CachedN8nAgent):
    """Performance-optimized n8n agent"""
    
    def __init__(self, api_base_url: str, api_key: str, max_workers: int = 4):
        super().__init__(api_base_url, api_key)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def batch_query(self, queries: List[str]) -> List[Dict]:
        """Process multiple queries in parallel"""
        futures = []
        
        for query in queries:
            future = self.executor.submit(self.query_knowledge, query)
            futures.append(future)
        
        results = []
        for future in futures:
            try:
                result = future.result(timeout=30)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        return results
    
    async def async_batch_query(self, queries: List[str]) -> List[Dict]:
        """Async batch processing"""
        loop = asyncio.get_event_loop()
        
        tasks = []
        for query in queries:
            task = loop.run_in_executor(self.executor, self.query_knowledge, query)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error dicts
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({"error": str(result)})
            else:
                processed_results.append(result)
        
        return processed_results
```

## Troubleshooting

### Common Issues

#### Connection Issues

```python
# troubleshooting.py
def diagnose_connection(api_base_url: str, api_key: str) -> Dict:
    """Diagnose connection issues"""
    import requests
    import socket
    from urllib.parse import urlparse
    
    results = {
        "url_reachable": False,
        "api_responding": False,
        "authentication_valid": False,
        "errors": []
    }
    
    try:
        # Check if URL is reachable
        parsed_url = urlparse(api_base_url)
        socket.create_connection((parsed_url.hostname, parsed_url.port or 80), timeout=5)
        results["url_reachable"] = True
    except Exception as e:
        results["errors"].append(f"URL not reachable: {str(e)}")
    
    try:
        # Check if API is responding
        response = requests.get(f"{api_base_url}/api/health", timeout=10)
        if response.status_code == 200:
            results["api_responding"] = True
        else:
            results["errors"].append(f"API returned status {response.status_code}")
    except Exception as e:
        results["errors"].append(f"API not responding: {str(e)}")
    
    try:
        # Check authentication
        headers = {'X-API-Key': api_key}
        response = requests.get(f"{api_base_url}/api/health", headers=headers, timeout=10)
        if response.status_code == 200:
            results["authentication_valid"] = True
        elif response.status_code == 401:
            results["errors"].append("Invalid API key")
        else:
            results["errors"].append(f"Authentication check failed: {response.status_code}")
    except Exception as e:
        results["errors"].append(f"Authentication check error: {str(e)}")
    
    return results

def run_diagnostics() -> str:
    """Run comprehensive diagnostics"""
    import os
    
    api_base_url = os.getenv('N8N_API_BASE_URL', 'http://localhost:8000')
    api_key = os.getenv('N8N_API_KEY', 'default_key')
    
    print("🔍 Running TRAE-n8n Integration Diagnostics...\n")
    
    # Environment check
    print("📋 Environment Configuration:")
    print(f"   API Base URL: {api_base_url}")
    print(f"   API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'}")
    print()
    
    # Connection diagnostics
    print("🔗 Connection Diagnostics:")
    diag_results = diagnose_connection(api_base_url, api_key)
    
    for check, status in diag_results.items():
        if check != "errors":
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {check.replace('_', ' ').title()}: {status}")
    
    if diag_results["errors"]:
        print("\n❌ Errors Found:")
        for error in diag_results["errors"]:
            print(f"   • {error}")
    
    # Test query
    if all([diag_results["url_reachable"], diag_results["api_responding"], diag_results["authentication_valid"]]):
        print("\n🧪 Testing Query Functionality:")
        try:
            agent = N8nTraeAgent(api_base_url, api_key)
            result = agent.query_knowledge("test query")
            if 'error' not in result:
                print("   ✅ Query test successful")
            else:
                print(f"   ❌ Query test failed: {result['error']}")
        except Exception as e:
            print(f"   ❌ Query test error: {str(e)}")
    
    print("\n🏁 Diagnostics Complete")
    
    return "Diagnostics completed. Check output above for results."

if __name__ == "__main__":
    run_diagnostics()
```

### Debug Mode

```python
# debug_mode.py
class DebugN8nAgent(OptimizedN8nAgent):
    """Debug version of n8n agent"""
    
    def __init__(self, api_base_url: str, api_key: str, debug: bool = True):
        super().__init__(api_base_url, api_key)
        self.debug = debug
        
        if debug:
            # Enable detailed logging
            import logging
            logging.getLogger('trae_n8n').setLevel(logging.DEBUG)
    
    def query_knowledge(self, query: str, max_results: int = 5) -> Dict:
        """Query with debug information"""
        if self.debug:
            print(f"🔍 DEBUG: Querying '{query[:50]}...'")
            print(f"🔍 DEBUG: Max results: {max_results}")
            print(f"🔍 DEBUG: API URL: {self.api_base_url}")
        
        result = super().query_knowledge(query, max_results)
        
        if self.debug:
            if 'error' in result:
                print(f"❌ DEBUG: Query failed - {result['error']}")
            else:
                print(f"✅ DEBUG: Query successful - {len(result.get('results', []))} results")
                if result.get('results'):
                    print(f"🔍 DEBUG: First result preview: {result['results'][0]['content'][:100]}...")
        
        return result
```

## Advanced Configurations

### Custom Response Formatting

```python
# custom_formatting.py
class CustomFormattedAgent(DebugN8nAgent):
    """Agent with custom response formatting for TRAE"""
    
    def __init__(self, api_base_url: str, api_key: str, format_style: str = "markdown"):
        super().__init__(api_base_url, api_key)
        self.format_style = format_style
    
    def format_for_trae(self, result: Dict) -> str:
        """Format result specifically for TRAE display"""
        if 'error' in result:
            return self._format_error(result['error'])
        
        if not result.get('results'):
            return self._format_no_results()
        
        if self.format_style == "markdown":
            return self._format_markdown(result['results'])
        elif self.format_style == "html":
            return self._format_html(result['results'])
        elif self.format_style == "plain":
            return self._format_plain(result['results'])
        else:
            return self._format_markdown(result['results'])
    
    def _format_error(self, error: str) -> str:
        """Format error message"""
        return f"🚨 **Error**: {error}\n\nPlease check your connection and try again."
    
    def _format_no_results(self) -> str:
        """Format no results message"""
        return "🔍 **No Results Found**\n\nI couldn't find relevant information in the n8n documentation. Try rephrasing your question or asking about a different topic."
    
    def _format_markdown(self, results: List[Dict]) -> str:
        """Format results as markdown"""
        response = "📚 **n8n Documentation Results:**\n\n"
        
        for i, item in enumerate(results[:3], 1):
            content = item['content'][:400]
            if len(item['content']) > 400:
                content += "..."
            
            response += f"### {i}. Result\n\n"
            response += f"{content}\n\n"
            
            if item.get('metadata', {}).get('source'):
                response += f"*📄 Source: {item['metadata']['source']}*\n\n"
            
            response += "---\n\n"
        
        return response.rstrip("---\n\n")
    
    def _format_html(self, results: List[Dict]) -> str:
        """Format results as HTML"""
        response = "<div class='n8n-results'>\n"
        response += "<h3>📚 n8n Documentation Results:</h3>\n"
        
        for i, item in enumerate(results[:3], 1):
            content = item['content'][:400]
            if len(item['content']) > 400:
                content += "..."
            
            response += f"<div class='result-item'>\n"
            response += f"<h4>{i}. Result</h4>\n"
            response += f"<p>{content}</p>\n"
            
            if item.get('metadata', {}).get('source'):
                response += f"<small>📄 Source: {item['metadata']['source']}</small>\n"
            
            response += "</div>\n"
        
        response += "</div>"
        return response
    
    def _format_plain(self, results: List[Dict]) -> str:
        """Format results as plain text"""
        response = "n8n Documentation Results:\n\n"
        
        for i, item in enumerate(results[:3], 1):
            content = item['content'][:400]
            if len(item['content']) > 400:
                content += "..."
            
            response += f"{i}. {content}\n"
            
            if item.get('metadata', {}).get('source'):
                response += f"   Source: {item['metadata']['source']}\n"
            
            response += "\n"
        
        return response
```

### Multi-Language Support

```python
# multilingual.py
class MultilingualN8nAgent(CustomFormattedAgent):
    """Multilingual support for TRAE integration"""
    
    def __init__(self, api_base_url: str, api_key: str, language: str = "en"):
        super().__init__(api_base_url, api_key)
        self.language = language
        self.translations = self._load_translations()
    
    def _load_translations(self) -> Dict:
        """Load translation strings"""
        translations = {
            "en": {
                "error": "Error",
                "no_results": "No Results Found",
                "results_title": "n8n Documentation Results",
                "source": "Source",
                "try_again": "Please check your connection and try again.",
                "no_info": "I couldn't find relevant information in the n8n documentation."
            },
            "es": {
                "error": "Error",
                "no_results": "No se encontraron resultados",
                "results_title": "Resultados de la documentación de n8n",
                "source": "Fuente",
                "try_again": "Por favor, verifica tu conexión e inténtalo de nuevo.",
                "no_info": "No pude encontrar información relevante en la documentación de n8n."
            },
            "fr": {
                "error": "Erreur",
                "no_results": "Aucun résultat trouvé",
                "results_title": "Résultats de la documentation n8n",
                "source": "Source",
                "try_again": "Veuillez vérifier votre connexion et réessayer.",
                "no_info": "Je n'ai pas pu trouver d'informations pertinentes dans la documentation n8n."
            }
        }
        
        return translations.get(self.language, translations["en"])
    
    def _format_error(self, error: str) -> str:
        """Format error message in selected language"""
        return f"🚨 **{self.translations['error']}**: {error}\n\n{self.translations['try_again']}"
    
    def _format_no_results(self) -> str:
        """Format no results message in selected language"""
        return f"🔍 **{self.translations['no_results']}**\n\n{self.translations['no_info']}"
    
    def _format_markdown(self, results: List[Dict]) -> str:
        """Format results as markdown in selected language"""
        response = f"📚 **{self.translations['results_title']}:**\n\n"
        
        for i, item in enumerate(results[:3], 1):
            content = item['content'][:400]
            if len(item['content']) > 400:
                content += "..."
            
            response += f"### {i}. Result\n\n"
            response += f"{content}\n\n"
            
            if item.get('metadata', {}).get('source'):
                response += f"*📄 {self.translations['source']}: {item['metadata']['source']}*\n\n"
            
            response += "---\n\n"
        
        return response.rstrip("---\n\n")
```

This comprehensive guide provides everything needed to successfully integrate the n8n AI Knowledge System with TRAE, from basic setup to advanced configurations and troubleshooting. The modular approach allows for customization based on specific requirements and use cases.