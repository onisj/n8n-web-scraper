# Development & Testing Guide

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Testing Framework](#testing-framework)
5. [Code Quality & Standards](#code-quality--standards)
6. [Debugging & Troubleshooting](#debugging--troubleshooting)
7. [Performance Optimization](#performance-optimization)
8. [Contributing Guidelines](#contributing-guidelines)
9. [Release Management](#release-management)
10. [Project Restructuring Notes](#project-restructuring-notes)

## Development Environment Setup

### Prerequisites

- **Python**: 3.7+ (recommended: 3.11 or 3.13)
- **Node.js**: 16+ (for any frontend components)
- **Git**: Latest version
- **Docker**: For containerized development (optional)
- **API Keys**: OpenAI and/or Anthropic for AI functionality

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd n8n-web-scrapper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Initialize the system
python start_system.py

# Run tests to verify setup
python -m pytest tests/
```

### Development Dependencies

```bash
# Install development tools
pip install -e ".[dev]"

# Or install individually
pip install pytest ruff black mypy pre-commit

# Set up pre-commit hooks
pre-commit install
```

### IDE Configuration

#### VS Code Settings

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/.pytest_cache": true
    }
}
```

#### PyCharm Configuration

1. Set Python interpreter to `./venv/bin/python`
2. Configure code style to use Black formatter
3. Enable pytest as test runner
4. Set up Ruff for linting

## Project Structure

### Current Structure (Post-Restructuring)

```
n8n-web-scrapper/
├── src/                          # Source code
│   ├── n8n_scraper/             # Main package
│   │   ├── agents/              # AI agents
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py
│   │   │   ├── n8n_expert.py
│   │   │   └── query_processor.py
│   │   ├── api/                 # FastAPI application
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   └── middleware/
│   │   ├── automation/          # Automation scripts
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py
│   │   │   └── workflows/
│   │   ├── database/            # Database operations
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── operations.py
│   │   │   └── vector_store.py
│   │   └── web_interface/       # Legacy Streamlit interface (deprecated)
│   │       ├── __init__.py
│   │       ├── app.py
│   │       ├── components/
│   │       └── utils/
│   ├── scripts/                 # Utility scripts
│   │   ├── run_scraper.py
│   │   ├── start_system.py
│   │   └── system_check.py
│   └── tools/                   # Development tools
│       ├── restructure_project.py
│       └── migration_helpers.py
├── config/                      # Configuration files
│   ├── __init__.py
│   ├── settings.py
│   ├── logging_config.py
│   ├── api_config.yaml
│   └── scraper_config.json
├── data/                        # Data storage
│   ├── scraped_docs/           # Scraped documentation
│   ├── vector_db/              # Vector database
│   └── logs/                   # Application logs
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── test_accurate_imports.py
│   └── run_import_tests.py
├── docs/                        # Documentation
│   ├── SYSTEM_GUIDE.md
│   ├── TRAE_INTEGRATION_DEPLOYMENT.md
│   └── DEVELOPMENT_TESTING.md
├── backups/                     # Backup files
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose
├── Makefile                    # Development commands
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project overview
└── DEPLOYMENT.md               # Deployment guide
```

### Package Organization

#### Core Modules

- **`src/n8n_scraper/`**: Main application package
  - **`agents/`**: AI agent implementations
  - **`api/`**: REST API using FastAPI
  - **`automation/`**: Scheduled tasks and workflows
  - **`database/`**: Data persistence and vector operations
  - **`web_interface/`**: Legacy Streamlit web application (deprecated)

#### Supporting Modules

- **`src/scripts/`**: Standalone utility scripts
- **`src/tools/`**: Development and maintenance tools
- **`config/`**: Configuration management
- **`tests/`**: Comprehensive test suite

## Development Workflow

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create pull request
git push origin feature/new-feature
```

### Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(api): add knowledge query endpoint"
git commit -m "fix(scraper): handle timeout errors gracefully"
git commit -m "docs: update installation instructions"
```

### Development Commands

#### Using Make

```bash
# Development setup
make setup          # Install dependencies and set up environment
make install        # Install package in development mode

# Code quality
make lint           # Run linting with ruff
make format         # Format code with black
make type-check     # Run type checking with mypy
make quality        # Run all quality checks

# Testing
make test           # Run all tests
make test-unit      # Run unit tests only
make test-integration # Run integration tests only
make test-coverage  # Run tests with coverage report

# System operations
make start          # Start the system
make stop           # Stop the system
make restart        # Restart the system
make check          # Run system health check

# Documentation
make docs           # Generate documentation
make docs-serve     # Serve documentation locally

# Cleanup
make clean          # Clean build artifacts
make clean-all      # Clean everything including data
```

#### Using Scripts

```bash
# System management
python start_system.py          # Start all services
python src/scripts/system_check.py  # Health check
python src/scripts/run_scraper.py   # Run scraper manually

# Testing
python -m pytest tests/         # Run all tests
python tests/run_import_tests.py # Test imports
python tests/test_accurate_imports.py # Verify imports

# Package commands (after pip install -e .)
n8n-start                       # Start system
n8n-check                       # System check
n8n-scraper                     # Run scraper
n8n-test                        # Run tests
```

## Testing Framework

### Test Structure

```
tests/
├── unit/                       # Unit tests
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_database.py
│   └── test_scraper.py
├── integration/                # Integration tests
│   ├── test_api_integration.py
│   ├── test_end_to_end.py
│   └── test_system_integration.py
├── fixtures/                   # Test fixtures
│   ├── sample_data.json
│   └── mock_responses.py
├── conftest.py                 # Pytest configuration
├── test_accurate_imports.py    # Import verification
└── run_import_tests.py         # Import test runner
```

### Writing Tests

#### Unit Test Example

```python
# tests/unit/test_agents.py
import pytest
from unittest.mock import Mock, patch
from src.n8n_scraper.agents.n8n_expert import N8nExpertAgent

class TestN8nExpertAgent:
    """Test suite for N8nExpertAgent"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance for testing"""
        return N8nExpertAgent(api_key="test_key")
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.api_key == "test_key"
        assert agent.model is not None
    
    @patch('src.n8n_scraper.agents.n8n_expert.openai')
    def test_query_processing(self, mock_openai, agent):
        """Test query processing functionality"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.ChatCompletion.create.return_value = mock_response
        
        # Test query
        result = agent.process_query("How to create a workflow?")
        
        # Assertions
        assert result is not None
        assert "Test response" in result
        mock_openai.ChatCompletion.create.assert_called_once()
    
    def test_error_handling(self, agent):
        """Test error handling in agent"""
        with patch('src.n8n_scraper.agents.n8n_expert.openai') as mock_openai:
            mock_openai.ChatCompletion.create.side_effect = Exception("API Error")
            
            result = agent.process_query("Test query")
            
            assert "error" in result.lower()
```

#### Integration Test Example

```python
# tests/integration/test_api_integration.py
import pytest
import requests
from fastapi.testclient import TestClient
from src.n8n_scraper.api.main import app

class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"
    
    def test_query_endpoint(self, client):
        """Test knowledge query endpoint"""
        payload = {
            "query": "How to create a webhook in n8n?",
            "max_results": 5
        }
        
        response = client.post("/api/query", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
    
    def test_authentication(self, client):
        """Test API authentication"""
        # Test without API key
        response = client.post("/api/query", json={"query": "test"})
        assert response.status_code == 401
        
        # Test with valid API key
        headers = {"X-API-Key": "valid_key"}
        response = client.post(
            "/api/query", 
            json={"query": "test"}, 
            headers=headers
        )
        assert response.status_code == 200
```

### Test Configuration

#### pytest.ini

```ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra
    -q
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    api: marks tests as API tests
```

#### conftest.py

```python
# tests/conftest.py
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

@pytest.fixture(scope="session")
def temp_data_dir():
    """Create temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices[0].message.content = "Mock AI response"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client

@pytest.fixture
def sample_scraped_data():
    """Sample scraped data for testing"""
    return {
        "title": "Test Documentation",
        "content": "This is test content for n8n documentation.",
        "url": "https://docs.n8n.io/test",
        "metadata": {
            "category": "nodes",
            "last_updated": "2024-01-01"
        }
    }

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_data_dir):
    """Set up test environment variables"""
    monkeypatch.setenv("DATA_DIR", str(temp_data_dir))
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest -m "not slow"           # Exclude slow tests

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run specific test method
pytest tests/unit/test_agents.py::TestN8nExpertAgent::test_query_processing

# Run tests in parallel
pytest -n auto                 # Requires pytest-xdist

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

## Code Quality & Standards

### Linting with Ruff

```bash
# Run linting
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Check specific files
ruff check src/n8n_scraper/agents/
```

#### Ruff Configuration (pyproject.toml)

```toml
[tool.ruff]
target-version = "py37"
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long, handled by black
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*" = ["B011", "B018"]
```

### Code Formatting with Black

```bash
# Format code
black src/ tests/

# Check formatting without making changes
black --check src/ tests/

# Format specific files
black src/n8n_scraper/agents/n8n_expert.py
```

#### Black Configuration (pyproject.toml)

```toml
[tool.black]
line-length = 88
target-version = ['py37', 'py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### Type Checking with MyPy

```bash
# Run type checking
mypy src/

# Check specific module
mypy src/n8n_scraper/agents/

# Generate type checking report
mypy --html-report mypy-report src/
```

#### MyPy Configuration (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.7"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = [
    # "streamlit.*",  # Removed - replaced by Next.js frontend
    "chromadb.*",
    "langchain.*",
]
ignore_missing_imports = true
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.270
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
```

## Debugging & Troubleshooting

### Logging Configuration

```python
# config/logging_config.py
import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Configure logging for the application"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    
    return root_logger
```

### Debug Mode

```python
# Enable debug mode in environment
export DEBUG=true
export LOG_LEVEL=DEBUG

# Or in code
import os
os.environ['DEBUG'] = 'true'
os.environ['LOG_LEVEL'] = 'DEBUG'
```

### Common Issues and Solutions

#### Import Errors

```bash
# Run import tests
python tests/run_import_tests.py

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
pip show n8n-web-scraper
```

#### API Connection Issues

```python
# Test API connectivity
import requests

response = requests.get('http://localhost:8000/api/health')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

#### Database Issues

```python
# Check vector database
from src.n8n_scraper.database.vector_store import VectorStore

vector_store = VectorStore()
print(f"Collection count: {vector_store.get_collection_count()}")
print(f"Document count: {vector_store.get_document_count()}")
```

### Performance Profiling

```python
# Profile code execution
import cProfile
import pstats

def profile_function(func, *args, **kwargs):
    """Profile a function's execution"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
    
    return result

# Usage
from src.n8n_scraper.agents.n8n_expert import N8nExpertAgent

agent = N8nExpertAgent()
result = profile_function(agent.process_query, "How to create a workflow?")
```

## Performance Optimization

### Caching Strategies

```python
# Simple LRU cache
from functools import lru_cache

class CachedAgent:
    @lru_cache(maxsize=128)
    def process_query(self, query: str) -> str:
        """Cached query processing"""
        return self._actual_process_query(query)
```

### Async Operations

```python
# Async API endpoints
from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.post("/api/query")
async def async_query(request: QueryRequest):
    """Async query processing"""
    # Process multiple queries concurrently
    tasks = [
        process_query_async(query) 
        for query in request.queries
    ]
    
    results = await asyncio.gather(*tasks)
    return {"results": results}
```

### Database Optimization

```python
# Batch operations
class OptimizedVectorStore:
    def batch_add_documents(self, documents: List[Dict], batch_size: int = 100):
        """Add documents in batches for better performance"""
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            self._add_batch(batch)
    
    def _add_batch(self, batch: List[Dict]):
        """Add a batch of documents"""
        # Implement batch insertion
        pass
```

## Contributing Guidelines

### Code Style

1. **Follow PEP 8**: Use Black for formatting
2. **Type Hints**: Add type hints to all functions
3. **Docstrings**: Use Google-style docstrings
4. **Naming**: Use descriptive variable and function names
5. **Comments**: Explain complex logic, not obvious code

### Pull Request Process

1. **Create Feature Branch**: `git checkout -b feature/description`
2. **Write Tests**: Ensure new code has test coverage
3. **Run Quality Checks**: `make quality`
4. **Update Documentation**: Update relevant docs
5. **Create PR**: Use descriptive title and description
6. **Code Review**: Address reviewer feedback
7. **Merge**: Squash and merge when approved

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Error handling is appropriate

## Release Management

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Create release branch
git checkout -b release/v1.2.0

# 4. Run full test suite
make test
make quality

# 5. Create release commit
git add .
git commit -m "chore: release v1.2.0"

# 6. Create tag
git tag -a v1.2.0 -m "Release v1.2.0"

# 7. Push to main
git checkout main
git merge release/v1.2.0
git push origin main --tags

# 8. Create GitHub release
# Use GitHub UI or gh CLI
gh release create v1.2.0 --title "Release v1.2.0" --notes-file CHANGELOG.md
```

### Changelog Format

```markdown
# Changelog

## [1.2.0] - 2024-01-15

### Added
- New AI agent for advanced query processing
- Support for multiple vector databases
- Async API endpoints for better performance

### Changed
- Improved error handling in scraper
- Updated dependencies to latest versions

### Fixed
- Fixed memory leak in vector operations
- Resolved import path issues

### Deprecated
- Old query format (will be removed in v2.0.0)

### Removed
- Legacy configuration options

### Security
- Updated dependencies with security patches
```

## Project Restructuring Notes

### Restructuring Overview

The project underwent a major restructuring to improve organization, maintainability, and development experience. Here are the key changes:

### What Was Changed

#### 1. Package Structure
- **Before**: Flat structure with mixed concerns
- **After**: Hierarchical package structure with clear separation

```
# Old structure
n8n-web-scrapper/
├── scraper.py
├── api.py
├── agents.py
├── database.py
└── ...

# New structure
n8n-web-scrapper/
├── src/
│   ├── n8n_scraper/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── automation/
│   │   ├── database/
│   │   └── web_interface/
│   ├── scripts/
│   └── tools/
```

#### 2. Import Path Updates

**Updated Files:**
- `src/scripts/run_scraper.py`: Fixed config imports
- `tests/test_accurate_imports.py`: Updated Python path
- `tests/run_import_tests.py`: Added project root to path

**Import Changes:**
```python
# Old imports
from config.settings import SCRAPER_CONFIG

# New imports
from config.settings import SCRAPER_CONFIG  # Still works due to path fixes
```

#### 3. Configuration Management
- Centralized configuration in `config/` directory
- Environment-based configuration loading
- Separate configs for different components

#### 4. Testing Infrastructure
- Comprehensive test suite organization
- Import verification tests
- Integration and unit test separation

### Migration Benefits

1. **Better Organization**: Clear separation of concerns
2. **Improved Maintainability**: Easier to navigate and modify
3. **Enhanced Testing**: Comprehensive test coverage
4. **Modern Python Practices**: Follows current best practices
5. **Development Experience**: Better IDE support and tooling

### Post-Restructuring Verification

```bash
# Verify all imports work
python tests/run_import_tests.py

# Run comprehensive tests
python -m pytest tests/

# Check system health
python src/scripts/system_check.py

# Start system to verify everything works
python start_system.py
```

### Next Steps After Restructuring

1. **Documentation Updates**: ✅ Completed
2. **CI/CD Pipeline**: Update build scripts for new structure
3. **Deployment Scripts**: Update Docker and deployment configs
4. **IDE Configuration**: Update workspace settings
5. **Team Training**: Familiarize team with new structure

### Troubleshooting Restructuring Issues

#### Import Errors
```bash
# Check if package is properly installed
pip show n8n-web-scraper

# Reinstall in development mode
pip install -e .

# Verify Python path
python -c "import sys; print(sys.path)"
```

#### Path Issues
```python
# Add project root to Python path if needed
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

#### Configuration Issues
```bash
# Check configuration files
ls -la config/

# Verify environment variables
env | grep N8N

# Test configuration loading
python -c "from config.settings import *; print('Config loaded successfully')"
```

This restructuring provides a solid foundation for future development and ensures the project follows modern Python packaging and development practices.