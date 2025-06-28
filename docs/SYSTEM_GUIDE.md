# n8n AI Knowledge System - Complete System Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [AI Components](#ai-components)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Usage Guide](#usage-guide)
7. [API Reference](#api-reference)
8. [Development](#development)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

## System Overview

The n8n AI Knowledge System is a comprehensive, AI-powered platform designed to scrape, process, and serve n8n documentation with advanced knowledge management capabilities. The system combines web scraping, vector databases, and AI agents to provide intelligent assistance with n8n workflows, documentation, and best practices.

### Key Features

- **Automated Documentation Scraping**: Continuously scrapes and updates n8n documentation
- **Vector-Based Knowledge Storage**: Uses ChromaDB for efficient semantic search
- **AI-Powered Query System**: Natural language queries with context-aware responses
- **Multi-Interface Access**: Web UI, REST API, and command-line interfaces
- **Real-Time Monitoring**: System health, performance metrics, and automated alerts
- **Automated Updates**: Scheduled scraping and knowledge base updates
- **Export Capabilities**: Multiple data export formats (JSON, CSV, etc.)

### System Components

1. **Web Scraper**: Automated n8n documentation collection
2. **Vector Database**: ChromaDB-powered knowledge storage
3. **AI Agents**: OpenAI/Anthropic-powered assistance
4. **FastAPI Backend**: RESTful API services
5. **Next.js Frontend**: Modern interactive web interface
6. **Automation Engine**: Scheduled tasks and monitoring

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│  Vector Database │───▶│   AI Agents     │
│   (Automated)   │    │   (ChromaDB)    │    │ (OpenAI/Claude) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  FastAPI Server │    │   Next.js Web   │    │ Command Line    │
│   (Port 8000)   │    │   Interface     │    │    Tools        │
│                 │    │  (Port 8501)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Scraping Phase**: Automated scraper collects n8n documentation
2. **Processing Phase**: Content is cleaned, chunked, and vectorized
3. **Storage Phase**: Vectors and metadata stored in ChromaDB
4. **Query Phase**: User queries processed through AI agents
5. **Response Phase**: Context-aware responses delivered via API/UI

### Package Structure

```
src/n8n_scraper/
├── agents/              # AI agents and knowledge processing
│   ├── n8n_agent.py     # Main AI assistant
│   └── knowledge_processor.py
├── api/                 # FastAPI application
│   ├── main.py          # API entry point
│   ├── routes/          # API endpoints
│   └── middleware/      # Request/response middleware
├── automation/          # Automated processes
│   ├── change_detector.py
│   ├── knowledge_updater.py
│   └── update_scheduler.py
├── database/            # Database management
│   ├── vector_db.py     # ChromaDB integration
│   ├── schemas/         # Data schemas
│   └── migrations/      # Database migrations
└── web_interface/       # Legacy Streamlit application (deprecated)
├── streamlit_app.py.deprecated
    ├── components/      # UI components
    └── static/          # Static assets
```

## AI Components

### n8n Expert AI Agent

The core AI agent (`src/n8n_scraper/agents/n8n_agent.py`) provides:

- **Contextual Understanding**: Deep knowledge of n8n workflows and concepts
- **Multi-Modal Responses**: Text, code examples, and workflow suggestions
- **Learning Capabilities**: Continuous improvement from user interactions
- **Integration Support**: Help with API integrations and custom nodes

### Knowledge Processor

The knowledge processor (`src/n8n_scraper/agents/knowledge_processor.py`) handles:

- **Content Chunking**: Intelligent document segmentation
- **Vector Generation**: Embedding creation for semantic search
- **Metadata Extraction**: Structured data extraction from documentation
- **Quality Assurance**: Content validation and deduplication

### Supported AI Providers

- **OpenAI**: GPT-4, GPT-3.5-turbo for general assistance
- **Anthropic**: Claude for advanced reasoning and analysis
- **Local Models**: Support for self-hosted models (future)

## Installation & Setup

### Prerequisites

- Python 3.7+ (tested with Python 3.13)
- Git
- 4GB+ RAM (for vector database)
- OpenAI API key
- Anthropic API key (optional)

### Installation Steps

1. **Clone Repository**:
   ```bash
   git clone https://github.com/your-org/n8n-web-scraper.git
   cd n8n-web-scraper
   ```

2. **Setup Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   # Or for development:
   pip install -e .
   ```

4. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize System**:
   ```bash
   python start_system.py
   ```

### Environment Configuration

Create a `.env` file with the following variables:

```env
# API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Database
CHROMA_PERSIST_DIRECTORY=./data/vector_db
CHROMA_COLLECTION_NAME=n8n_docs

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Next.js Frontend Configuration
# Frontend runs on port 3000 during development
# No additional configuration needed

# Scraping Configuration
SCRAPE_DELAY=1
MAX_CONCURRENT_REQUESTS=5
USER_AGENT=n8n-knowledge-scraper/1.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=./data/logs/n8n_scraper.log
```

## Configuration

### Main Configuration (`config/settings.py`)

The main configuration file contains:

- **API Settings**: Host, port, CORS configuration
- **Database Settings**: ChromaDB configuration
- **AI Settings**: Model selection and parameters
- **Scraping Settings**: Rate limiting and user agents
- **Logging Settings**: Log levels and file locations

### Database Configuration (`config/database.yaml`)

```yaml
chroma:
  persist_directory: "./data/vector_db"
  collection_name: "n8n_docs"
  embedding_function: "openai"
  distance_metric: "cosine"

embeddings:
  openai:
    model: "text-embedding-ada-002"
    chunk_size: 1000
    chunk_overlap: 200
```

### Scheduler Configuration (`config/scheduler.yaml`)

```yaml
scheduler:
  timezone: "UTC"
  max_workers: 4

jobs:
  scrape_docs:
    schedule: "0 2 * * *"  # Daily at 2 AM
    enabled: true
  
  update_vectors:
    schedule: "0 3 * * *"  # Daily at 3 AM
    enabled: true
  
  health_check:
    schedule: "*/15 * * * *"  # Every 15 minutes
    enabled: true
```

## Usage Guide

### Web Interface

Access the Next.js interface at `http://localhost:3000`:

```bash
cd frontend
npm install
npm run dev
```

1. **Knowledge Search**: Enter natural language queries
2. **Document Browser**: Browse scraped documentation
3. **System Monitor**: View system health and metrics
4. **Export Tools**: Download data in various formats

### API Usage

The FastAPI server at `http://localhost:8000` provides:

#### Query Knowledge Base
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I create a webhook in n8n?", "max_results": 5}'
```

#### Health Check
```bash
curl "http://localhost:8000/api/health"
```

#### Trigger Scraping
```bash
curl -X POST "http://localhost:8000/api/scrape" \
  -H "Content-Type: application/json" \
  -d '{"force_update": true}'
```

### Command Line Tools

```bash
# System management
n8n-start          # Start complete system
n8n-check          # System diagnostics
n8n-scraper        # Run scraper only
n8n-test           # Run test suite

# Development tools
python src/tools/system_check.py
python tests/run_import_tests.py
```

## API Reference

### Authentication

Currently, the API uses simple API key authentication. Include your API key in the header:

```
X-API-Key: your_api_key_here
```

### Endpoints

#### GET /api/health
Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": "healthy",
    "ai_service": "healthy",
    "scraper": "healthy"
  }
}
```

#### POST /api/query
Query the knowledge base.

**Request:**
```json
{
  "query": "How do I create a webhook?",
  "max_results": 5,
  "include_metadata": true
}
```

**Response:**
```json
{
  "results": [
    {
      "content": "To create a webhook in n8n...",
      "score": 0.95,
      "metadata": {
        "source": "webhooks.md",
        "section": "Creating Webhooks"
      }
    }
  ],
  "query_time": 0.234
}
```

#### POST /api/scrape
Trigger documentation scraping.

**Request:**
```json
{
  "force_update": true,
  "target_urls": ["https://docs.n8n.io/webhooks/"]
}
```

#### GET /api/stats
Get system statistics.

**Response:**
```json
{
  "documents": 1247,
  "vectors": 15623,
  "last_update": "2024-01-15T02:00:00Z",
  "storage_size": "245MB"
}
```

## Development

### Development Setup

1. **Install Development Dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Pre-commit Hooks**:
   ```bash
   pre-commit install
   ```

3. **Run Tests**:
   ```bash
   pytest tests/
   # Or use make
   make test
   ```

### Code Quality

```bash
# Linting
ruff check src/
flake8 src/

# Formatting
black src/

# Type checking
mypy src/
```

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_api.py
pytest tests/test_scraper.py

# Run with coverage
pytest --cov=src/n8n_scraper
```

### Adding New Features

1. **Create Feature Branch**: `git checkout -b feature/new-feature`
2. **Implement Changes**: Follow existing code patterns
3. **Add Tests**: Ensure good test coverage
4. **Update Documentation**: Update relevant docs
5. **Submit PR**: Create pull request for review

## Deployment

### Docker Deployment

1. **Build Image**:
   ```bash
   docker build -t n8n-knowledge-system .
   ```

2. **Run Container**:
   ```bash
   docker run -p 8000:8000 -p 8501:8501 \
     -e OPENAI_API_KEY=your_key \
     -v $(pwd)/data:/app/data \
     n8n-knowledge-system
   ```

3. **Docker Compose**:
   ```bash
   docker-compose up -d
   ```

### Production Deployment

1. **Environment Setup**:
   - Use production-grade database
   - Configure load balancing
   - Set up monitoring and logging
   - Implement backup strategies

2. **Security Considerations**:
   - Use HTTPS in production
   - Implement proper authentication
   - Secure API keys and secrets
   - Regular security updates

3. **Scaling**:
   - Horizontal scaling for API servers
   - Database clustering for high availability
   - CDN for static assets
   - Caching layers for performance

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Run import diagnostics
python tests/run_import_tests.py
python tests/test_accurate_imports.py

# Check Python path
python src/tools/system_check.py
```

#### Database Connection Issues
```bash
# Check ChromaDB status
python -c "from src.n8n_scraper.database.vector_db import VectorDB; VectorDB().health_check()"

# Reset database
rm -rf data/vector_db/
python src/scripts/run_scraper.py --reset-db
```

#### API Server Issues
```bash
# Check port availability
lsof -i :8000
lsof -i :8501

# Run in debug mode
uvicorn src.n8n_scraper.api.main:app --reload --log-level debug
```

#### Memory Issues
```bash
# Monitor memory usage
python src/tools/system_check.py --memory

# Reduce batch size in config
# Edit config/settings.py: BATCH_SIZE = 50
```

### Logging

Logs are stored in `data/logs/n8n_scraper.log`. Key log locations:

- **API Logs**: FastAPI request/response logs
- **Scraper Logs**: Web scraping activity and errors
- **Database Logs**: ChromaDB operations
- **AI Logs**: AI model interactions and responses

### Performance Optimization

1. **Database Optimization**:
   - Regular vector database maintenance
   - Optimize chunk sizes for your use case
   - Monitor query performance

2. **API Optimization**:
   - Implement caching for frequent queries
   - Use async operations where possible
   - Monitor response times

3. **Scraping Optimization**:
   - Adjust concurrent request limits
   - Implement intelligent retry logic
   - Monitor rate limiting

### Getting Help

- **Documentation**: Check this guide and API docs
- **Logs**: Review application logs for errors
- **System Check**: Run `python src/tools/system_check.py`
- **Community**: Join our Discord/Slack for support
- **Issues**: Report bugs on GitHub

---

*This guide covers the complete n8n AI Knowledge System. For specific deployment scenarios or advanced configurations, please refer to the additional documentation files or contact the development team.*