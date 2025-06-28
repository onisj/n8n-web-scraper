#!/bin/bash

# N8N Web Scraper Development Setup Script
# This script sets up the local development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="n8n-scraper"
DOCKER_COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env.dev"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    local tools=("docker" "docker-compose" "python3" "node" "npm")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed. Please install it first."
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    # Check Python version
    local python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [[ "$(echo "$python_version >= 3.9" | bc)" -eq 0 ]]; then
        log_error "Python 3.9+ is required. Current version: $python_version"
        exit 1
    fi
    
    # Check Node version
    local node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ "$node_version" -lt 18 ]]; then
        log_error "Node.js 18+ is required. Current version: $node_version"
        exit 1
    fi
    
    log_success "All prerequisites met!"
}

setup_python_environment() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    if [[ -f "requirements.txt" ]]; then
        log_info "Installing Python dependencies..."
        pip install -r requirements.txt
    fi
    
    if [[ -f "requirements-dev.txt" ]]; then
        log_info "Installing development dependencies..."
        pip install -r requirements-dev.txt
    fi
    
    log_success "Python environment set up!"
}

setup_node_environment() {
    log_info "Setting up Node.js environment..."
    
    # Check if frontend directory exists
    if [[ -d "frontend" ]]; then
        cd frontend
        
        # Install dependencies
        if [[ -f "package.json" ]]; then
            log_info "Installing Node.js dependencies..."
            npm install
        fi
        
        cd ..
    fi
    
    log_success "Node.js environment set up!"
}

create_env_file() {
    log_info "Creating environment file..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        cat > "$ENV_FILE" << 'EOF'
# Development Environment Configuration

# Application
APP_NAME=n8n-scraper
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=1
RELOAD=true

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/n8n_scraper_dev
DATABASE_ECHO=true
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_SSL=false

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8001
CHROMADB_SSL=false

# AI/ML Configuration
OPENAI_API_KEY=your_openai_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-3.5-turbo
MAX_TOKENS=2048
TEMPERATURE=0.7

# Scraping Configuration
SCRAPING_DELAY=1
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3
USER_AGENT=N8N-Scraper/1.0.0
RESPECT_ROBOTS_TXT=true

# Security
SECRET_KEY=your_secret_key_here_change_in_production
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
SESSION_SECRET_KEY=your_session_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Monitoring
MONITORING_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Logging
LOG_FORMAT=json
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=7

# Real-time Features
REALTIME_ENABLED=true
WEBSOCKET_PORT=8001
SOCKETIO_CORS_ORIGINS=["http://localhost:3000"]

# Automation
N8N_WEBHOOK_URL=http://localhost:5678/webhook
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here

# Backup
BACKUP_ENABLED=true
BACKUP_INTERVAL=daily
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_ENABLED=false

# Performance
CACHE_TTL=3600
CACHE_MAX_SIZE=1000
WORKER_CONCURRENCY=4
QUEUE_MAX_SIZE=1000

# Feature Flags
AI_FEATURES_ENABLED=true
REALTIME_FEATURES_ENABLED=true
ANALYTICS_ENABLED=true
BACKUP_AUTOMATION_ENABLED=true

# External Services
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true

# Cloud Storage (for development, use local storage)
CLOUD_STORAGE_PROVIDER=local
CLOUD_STORAGE_BUCKET=n8n-scraper-dev
CLOUD_STORAGE_REGION=us-west-2

# API Configuration
API_V1_PREFIX=/api/v1
API_DOCS_ENABLED=true
API_DOCS_URL=/docs
API_REDOC_URL=/redoc

# Data Processing
DATA_PROCESSING_BATCH_SIZE=100
DATA_PROCESSING_TIMEOUT=300
DATA_VALIDATION_ENABLED=true
DATA_SANITIZATION_ENABLED=true
EOF
        
        log_success "Environment file created: $ENV_FILE"
        log_warning "Please update the API keys and other sensitive values in $ENV_FILE"
    else
        log_info "Environment file already exists: $ENV_FILE"
    fi
}

create_docker_compose() {
    log_info "Creating Docker Compose file for development..."
    
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        cat > "$DOCKER_COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: n8n-scraper-postgres-dev
    environment:
      POSTGRES_DB: n8n_scraper_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - n8n-scraper-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: n8n-scraper-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - n8n-scraper-network

  # ChromaDB Vector Database
  chromadb:
    image: chromadb/chroma:latest
    container_name: n8n-scraper-chromadb-dev
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_HTTP_PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - n8n-scraper-network

  # Prometheus (Monitoring)
  prometheus:
    image: prom/prometheus:latest
    container_name: n8n-scraper-prometheus-dev
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - n8n-scraper-network

  # Grafana (Dashboards)
  grafana:
    image: grafana/grafana:latest
    container_name: n8n-scraper-grafana-dev
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - n8n-scraper-network

  # n8n Workflow Automation
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n-scraper-n8n-dev
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=UTC
    networks:
      - n8n-scraper-network

  # Mailhog (Email Testing)
  mailhog:
    image: mailhog/mailhog:latest
    container_name: n8n-scraper-mailhog-dev
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI
    networks:
      - n8n-scraper-network

volumes:
  postgres_data:
  redis_data:
  chromadb_data:
  prometheus_data:
  grafana_data:
  n8n_data:

networks:
  n8n-scraper-network:
    driver: bridge
EOF
        
        log_success "Docker Compose file created: $DOCKER_COMPOSE_FILE"
    else
        log_info "Docker Compose file already exists: $DOCKER_COMPOSE_FILE"
    fi
}

create_monitoring_config() {
    log_info "Creating monitoring configuration..."
    
    # Create monitoring directory
    mkdir -p monitoring/grafana/{provisioning/datasources,provisioning/dashboards,dashboards}
    
    # Prometheus configuration
    if [[ ! -f "monitoring/prometheus.yml" ]]; then
        cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'n8n-scraper-api'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'n8n-scraper-worker'
    static_configs:
      - targets: ['host.docker.internal:8001']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
EOF
    fi
    
    # Grafana datasource configuration
    if [[ ! -f "monitoring/grafana/provisioning/datasources/prometheus.yml" ]]; then
        cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
    fi
    
    # Grafana dashboard configuration
    if [[ ! -f "monitoring/grafana/provisioning/dashboards/dashboard.yml" ]]; then
        cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF
    fi
    
    log_success "Monitoring configuration created!"
}

create_database_init_script() {
    log_info "Creating database initialization script..."
    
    mkdir -p scripts
    
    if [[ ! -f "scripts/init-db.sql" ]]; then
        cat > scripts/init-db.sql << 'EOF'
-- Database initialization script for development

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create development user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'n8n_scraper_dev') THEN
        CREATE ROLE n8n_scraper_dev WITH LOGIN PASSWORD 'dev_password';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE n8n_scraper_dev TO n8n_scraper_dev;
GRANT ALL ON SCHEMA public TO n8n_scraper_dev;

-- Create development schemas
CREATE SCHEMA IF NOT EXISTS scraping;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Grant schema permissions
GRANT ALL ON SCHEMA scraping TO n8n_scraper_dev;
GRANT ALL ON SCHEMA analytics TO n8n_scraper_dev;
GRANT ALL ON SCHEMA monitoring TO n8n_scraper_dev;
EOF
    fi
    
    log_success "Database initialization script created!"
}

setup_pre_commit_hooks() {
    log_info "Setting up pre-commit hooks..."
    
    if command -v pre-commit &> /dev/null; then
        # Create .pre-commit-config.yaml if it doesn't exist
        if [[ ! -f ".pre-commit-config.yaml" ]]; then
            cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-redis]

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-r", "src/"]
        exclude: tests/
EOF
        fi
        
        # Install pre-commit hooks
        source venv/bin/activate
        pip install pre-commit
        pre-commit install
        
        log_success "Pre-commit hooks installed!"
    else
        log_warning "pre-commit not found. Skipping pre-commit setup."
    fi
}

start_services() {
    log_info "Starting development services..."
    
    # Start Docker services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    log_success "Development services started!"
}

show_development_info() {
    log_info "Development Environment Information:"
    echo ""
    echo "Services:"
    echo "  PostgreSQL:  localhost:5432 (postgres/password)"
    echo "  Redis:       localhost:6379"
    echo "  ChromaDB:    localhost:8001"
    echo "  Prometheus:  http://localhost:9090"
    echo "  Grafana:     http://localhost:3001 (admin/admin)"
    echo "  n8n:         http://localhost:5678 (admin/admin)"
    echo "  MailHog:     http://localhost:8025"
    echo ""
    echo "Development Commands:"
    echo "  Start API:     python -m uvicorn src.n8n_scraper.main:app --reload --host 0.0.0.0 --port 8000"
    echo "  Start Worker:  python -m celery -A src.n8n_scraper.worker.celery_app worker --loglevel=info"
    echo "  Start Frontend: cd frontend && npm run dev"
    echo "  Run Tests:     python -m pytest"
    echo "  Format Code:   black src/ && isort src/"
    echo "  Lint Code:     flake8 src/"
    echo "  Type Check:    mypy src/"
    echo ""
    echo "Database Commands:"
    echo "  Connect:       psql -h localhost -U postgres -d n8n_scraper_dev"
    echo "  Migrations:    alembic upgrade head"
    echo "  Create Migration: alembic revision --autogenerate -m 'description'"
    echo ""
    echo "Docker Commands:"
    echo "  View Logs:     docker-compose -f $DOCKER_COMPOSE_FILE logs -f [service]"
    echo "  Stop Services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  Restart:       docker-compose -f $DOCKER_COMPOSE_FILE restart [service]"
    echo ""
}

stop_services() {
    log_info "Stopping development services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    log_success "Development services stopped!"
}

clean_environment() {
    log_warning "Cleaning development environment..."
    
    read -p "This will remove all containers, volumes, and virtual environment. Continue? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "Clean cancelled."
        return
    fi
    
    # Stop and remove containers
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans
    
    # Remove virtual environment
    if [[ -d "venv" ]]; then
        rm -rf venv
    fi
    
    # Remove node_modules
    if [[ -d "frontend/node_modules" ]]; then
        rm -rf frontend/node_modules
    fi
    
    log_success "Development environment cleaned!"
}

# Main execution
main() {
    local action="${1:-setup}"
    
    case "$action" in
        "setup")
            check_prerequisites
            setup_python_environment
            setup_node_environment
            create_env_file
            create_docker_compose
            create_monitoring_config
            create_database_init_script
            setup_pre_commit_hooks
            start_services
            show_development_info
            ;;
        "start")
            start_services
            show_development_info
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            start_services
            ;;
        "clean")
            clean_environment
            ;;
        "info")
            show_development_info
            ;;
        "help")
            echo "Usage: $0 [setup|start|stop|restart|clean|info|help]"
            echo ""
            echo "Commands:"
            echo "  setup    - Full development environment setup (default)"
            echo "  start    - Start development services"
            echo "  stop     - Stop development services"
            echo "  restart  - Restart development services"
            echo "  clean    - Clean development environment"
            echo "  info     - Show development information"
            echo "  help     - Show this help"
            ;;
        *)
            log_error "Unknown action: $action"
            echo "Run '$0 help' for usage information."
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"