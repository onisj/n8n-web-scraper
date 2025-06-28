# Vector Database Integration for Fast Knowledge Retrieval

This document explains how the n8n Web Scraper integrates with a vector database to provide fast chunking, embedding generation, and semantic search capabilities for scraped n8n documentation.

## Overview

The vector database integration transforms raw scraped data into semantically searchable knowledge chunks that can be quickly retrieved by AI agents and applications. This system provides:

- **Fast Chunking**: Automatic text segmentation with configurable chunk sizes and overlap
- **Semantic Embeddings**: Vector representations for similarity-based search
- **Incremental Updates**: Only process new or modified content
- **Metadata Enrichment**: Enhanced categorization and tagging
- **High-Performance Retrieval**: Sub-second search across thousands of documents

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│  JSON Storage    │───▶│ Vector Database │
│                 │    │                  │    │                 │
│ • Extract HTML  │    │ • Raw scraped    │    │ • Embeddings    │
│ • Parse content │    │   data           │    │ • Metadata      │
│ • Structure     │    │ • Metadata       │    │ • Fast search   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Knowledge        │    │ AI Agent /      │
                       │ Processor        │    │ Search API      │
                       │                  │    │                 │
                       │ • Chunk text     │    │ • Semantic      │
                       │ • Extract tags   │    │   search        │
                       │ • Categorize     │    │ • Context       │
                       │ • Generate IDs   │    │   retrieval     │
                       └──────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Scrape and Process in One Command

```bash
# Scrape n8n docs and automatically process into vector database
n8n-scraper scrape --process-to-vector --max-pages 50

# Scrape specific URLs with custom vector storage location
n8n-scraper scrape https://docs.n8n.io/workflows/ \
  --process-to-vector \
  --vector-dir ./my_knowledge_base \
  --max-pages 100
```

### 2. Process Existing Scraped Data

```bash
# Process all scraped JSON files into vector database
n8n-scraper vector process --scraped-dir data/scraped_docs

# Force reprocessing of all files
n8n-scraper vector process --force-refresh

# Custom chunking configuration
n8n-scraper vector process \
  --chunk-size 1500 \
  --chunk-overlap 300 \
  --async-mode
```

### 3. Search the Knowledge Base

```bash
# Basic semantic search
n8n-scraper vector search "workflow automation"

# Advanced search with filters
n8n-scraper vector search "HTTP request node" \
  --top-k 10 \
  --score-threshold 0.8 \
  --category "nodes" \
  --output-format detailed

# Export search results
n8n-scraper vector search "data transformation" \
  --output-format json > search_results.json
```

### 4. Manage the Knowledge Base

```bash
# View knowledge base statistics
n8n-scraper vector stats

# Incremental update (only new/modified files)
n8n-scraper vector update

# Reset the entire knowledge base
n8n-scraper vector reset --confirm
```

## Configuration

### Environment Variables

```bash
# Vector database directory
export VECTOR_DB_DIRECTORY="./data/chroma_db"

# Scraped data directory
export SCRAPED_DATA_DIRECTORY="./data/scraped_docs"

# ChromaDB persistence directory
export CHROMA_PERSIST_DIRECTORY="./data/chroma_db"
```

### Chunking Configuration

```python
# Default settings
CHUNK_SIZE = 1000          # Maximum characters per chunk
CHUNK_OVERLAP = 200        # Overlap between chunks
COLLECTION_NAME = "n8n_knowledge"
```

### Custom Configuration

```python
from n8n_scraper.automation.knowledge_vector_integration import KnowledgeVectorIntegration

# Create custom integration
integration = KnowledgeVectorIntegration(
    scraped_data_dir="./custom/scraped",
    vector_db_dir="./custom/vector_db",
    collection_name="my_knowledge",
    chunk_size=1500,
    chunk_overlap=300
)

# Process data
stats = integration.process_and_store_all()
print(f"Processed {stats['total_chunks']} chunks")
```

## Data Flow

### 1. Scraping Phase

```json
{
  "url": "https://docs.n8n.io/workflows/",
  "title": "Workflows",
  "content": "Workflows are the core concept in n8n...",
  "headings": ["Introduction", "Creating Workflows"],
  "links": ["https://docs.n8n.io/nodes/"],
  "code_blocks": ["const workflow = {...}"],
  "images": ["workflow-diagram.png"],
  "scraped_at": "2024-01-15T10:30:00Z",
  "metadata": {
    "quality_score": 95,
    "word_count": 1250
  }
}
```

### 2. Processing Phase

```python
# Knowledge chunk structure
{
  "id": "chunk_workflows_abc123",
  "content": "Workflows are the core concept in n8n. They define...",
  "metadata": {
    "title": "Workflows",
    "url": "https://docs.n8n.io/workflows/",
    "category": "core_concepts",
    "subcategory": "workflows",
    "source_file": "workflows_20240115",
    "word_count": 245,
    "char_count": 1000,
    "has_code": true,
    "has_images": true,
    "processed_at": "2024-01-15T10:35:00Z"
  }
}
```

### 3. Vector Storage

- **Embeddings**: Generated using `all-MiniLM-L6-v2` model
- **Metadata**: Stored alongside vectors for filtering
- **IDs**: Unique identifiers for deduplication
- **Collections**: Organized by knowledge domain

## Search Capabilities

### Semantic Search

```python
from n8n_scraper.automation.knowledge_vector_integration import create_knowledge_integration

integration = create_knowledge_integration()

# Find relevant documentation
results = integration.search_knowledge(
    query="How to handle HTTP errors in workflows",
    top_k=5,
    score_threshold=0.7,
    category_filter="error_handling"
)

for result in results:
    print(f"Title: {result['metadata']['title']}")
    print(f"Score: {result['score']:.3f}")
    print(f"Content: {result['content'][:200]}...")
    print("---")
```

### Advanced Filtering

```python
# Search with multiple filters
results = integration.search_knowledge(
    query="data transformation",
    top_k=10,
    score_threshold=0.8
)

# Filter results by metadata
filtered_results = [
    r for r in results 
    if r['metadata'].get('has_code', False) and 
       r['metadata'].get('word_count', 0) > 100
]
```

## Performance Optimization

### Chunking Strategy

- **Optimal Chunk Size**: 800-1200 characters for balanced context and retrieval
- **Overlap**: 150-250 characters to maintain context continuity
- **Sentence Boundaries**: Chunks split at natural sentence endings
- **Code Preservation**: Code blocks kept intact when possible

### Indexing Performance

```bash
# Batch processing for large datasets
n8n-scraper vector process --async-mode

# Monitor processing progress
n8n-scraper vector stats --output-format json | jq '.file_processing'
```

### Search Performance

- **Sub-second retrieval** for collections up to 100K documents
- **Parallel processing** for batch operations
- **Incremental updates** to avoid full reprocessing
- **Caching** for frequently accessed chunks

## Integration with AI Agents

### N8n Expert Agent

```python
from n8n_scraper.agents.n8n_agent import N8nExpertAgent
from n8n_scraper.automation.knowledge_vector_integration import create_knowledge_integration

# Create agent with vector-powered knowledge base
integration = create_knowledge_integration()
agent = N8nExpertAgent()

# Load knowledge from vector database
agent.load_knowledge_base()

# Ask questions with semantic search
response = agent.answer_question(
    "How do I create a workflow that processes CSV files?"
)
print(response)
```

### Custom Applications

```python
# Build custom search API
from fastapi import FastAPI
from n8n_scraper.automation.knowledge_vector_integration import create_knowledge_integration

app = FastAPI()
integration = create_knowledge_integration()

@app.get("/search")
async def search_knowledge(query: str, limit: int = 5):
    results = integration.search_knowledge(
        query=query,
        top_k=limit,
        score_threshold=0.7
    )
    return {"results": results}
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check system status
n8n-scraper vector stats

# Verify data integrity
n8n-scraper doctor --check-deps
```

### Backup and Recovery

```python
from n8n_scraper.automation.knowledge_vector_integration import create_knowledge_integration

integration = create_knowledge_integration()

# Backup knowledge base
backup_data = integration.vector_db.backup_collection()
with open('knowledge_backup.json', 'w') as f:
    json.dump(backup_data, f)

# Restore from backup
with open('knowledge_backup.json', 'r') as f:
    backup_data = json.load(f)
integration.vector_db.restore_collection(backup_data)
```

### Performance Monitoring

```bash
# Monitor processing performance
time n8n-scraper vector process --scraped-dir large_dataset/

# Check memory usage during processing
/usr/bin/time -v n8n-scraper vector process --async-mode
```

## Troubleshooting

### Common Issues

1. **Out of Memory During Processing**
   ```bash
   # Process in smaller batches
   n8n-scraper vector process --chunk-size 800 --async-mode
   ```

2. **Slow Search Performance**
   ```bash
   # Check collection size
   n8n-scraper vector stats
   
   # Consider increasing score threshold
   n8n-scraper vector search "query" --score-threshold 0.8
   ```

3. **Missing Dependencies**
   ```bash
   # Install required packages
   pip install sentence-transformers chromadb
   
   # Verify installation
   n8n-scraper doctor --check-deps
   ```

### Debug Mode

```bash
# Enable verbose logging
n8n-scraper -vvv vector process

# Check processing logs
tail -f logs/n8n_scraper.log
```

## Best Practices

### Data Quality

1. **Filter Low-Quality Content**
   ```bash
   n8n-scraper scrape --filter-quality 70 --process-to-vector
   ```

2. **Regular Updates**
   ```bash
   # Daily incremental updates
   n8n-scraper vector update
   ```

3. **Validate Search Results**
   ```python
   results = integration.search_knowledge("test query")
   assert len(results) > 0, "No results found"
   assert all(r['score'] >= 0.7 for r in results), "Low quality results"
   ```

### Performance

1. **Optimize Chunk Size**
   - Test different chunk sizes for your use case
   - Monitor search relevance vs. performance

2. **Use Async Processing**
   ```bash
   n8n-scraper vector process --async-mode
   ```

3. **Regular Maintenance**
   ```bash
   # Monthly full refresh
   n8n-scraper vector process --force-refresh
   ```

## API Reference

### KnowledgeVectorIntegration

```python
class KnowledgeVectorIntegration:
    def __init__(self, scraped_data_dir, vector_db_dir, collection_name, chunk_size, chunk_overlap)
    def process_and_store_all(self, force_refresh=False) -> Dict[str, Any]
    def process_incremental_update(self) -> Dict[str, Any]
    def search_knowledge(self, query, top_k=10, score_threshold=0.7, category_filter=None) -> List[Dict]
    def get_knowledge_stats(self) -> Dict[str, Any]
```

### CLI Commands

```bash
# Vector database management
n8n-scraper vector process [OPTIONS]
n8n-scraper vector search QUERY [OPTIONS]
n8n-scraper vector stats [OPTIONS]
n8n-scraper vector update [OPTIONS]
n8n-scraper vector reset [OPTIONS]

# Enhanced scraping
n8n-scraper scrape [URLS] --process-to-vector [OPTIONS]
```

## Examples

### Complete Workflow

```bash
#!/bin/bash
# Complete n8n documentation processing workflow

# 1. Scrape n8n documentation
echo "Scraping n8n documentation..."
n8n-scraper scrape \
  --max-pages 200 \
  --max-depth 4 \
  --process-to-vector \
  --output ./data/scraped \
  --vector-dir ./data/knowledge_base

# 2. Verify processing
echo "Checking knowledge base stats..."
n8n-scraper vector stats --vector-dir ./data/knowledge_base

# 3. Test search functionality
echo "Testing search..."
n8n-scraper vector search "HTTP request node" \
  --vector-dir ./data/knowledge_base \
  --top-k 5 \
  --output-format detailed

echo "Setup complete! Knowledge base ready for use."
```

### Python Integration

```python
#!/usr/bin/env python3
"""Example: Building a knowledge-powered chatbot"""

from n8n_scraper.automation.knowledge_vector_integration import create_knowledge_integration
from n8n_scraper.agents.n8n_agent import N8nExpertAgent

def create_chatbot():
    # Initialize knowledge integration
    integration = create_knowledge_integration(
        vector_db_dir="./data/knowledge_base"
    )
    
    # Create expert agent
    agent = N8nExpertAgent()
    agent.load_knowledge_base()
    
    return integration, agent

def answer_question(integration, agent, question):
    # Search for relevant context
    context = integration.search_knowledge(
        query=question,
        top_k=3,
        score_threshold=0.7
    )
    
    # Generate answer using agent
    response = agent.answer_question(
        question=question,
        context=[c['content'] for c in context]
    )
    
    return response, context

if __name__ == "__main__":
    integration, agent = create_chatbot()
    
    while True:
        question = input("Ask about n8n: ")
        if question.lower() in ['quit', 'exit']:
            break
            
        answer, sources = answer_question(integration, agent, question)
        print(f"Answer: {answer}")
        print(f"Sources: {len(sources)} relevant documents found")
        print("---")
```

This vector database integration provides a powerful foundation for building AI-powered applications that can quickly access and reason about n8n documentation. The system is designed to scale from small personal projects to large enterprise knowledge bases.