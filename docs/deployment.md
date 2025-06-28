# Deployment Guide for n8n AI Knowledge System

This guide covers different deployment options for the n8n AI Knowledge System, from local development to production deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Configuration](#configuration)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB minimum, 50GB recommended
- **Network**: Internet access for AI APIs and documentation scraping

### Software Requirements

- **Python**: 3.11 or higher
- **Docker**: 20.10+ (for containerized deployment)
- **Docker Compose**: 2.0+ (for multi-container deployment)
- **Git**: For cloning the repository

### API Keys Required

At least one AI provider API key is required:

- **OpenAI API Key**: For GPT models
- **Anthropic API Key**: For Claude models

Optional:
- **n8n API Key**: If connecting to an existing n8n instance

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd n8n-web-scrapper
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys and configuration
nano .env
```

### 4. Initialize the System

```bash
# Run setup script
python setup.py

# Start the system
python start_system.py --mode full
```

### 5. Access the Application

- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Docker Deployment

### Single Container Deployment

```bash
# Build the image
docker build -t n8n-knowledge-system .

# Run the container
docker run -d \
  --name n8n-knowledge-system \
  -p 8000:8000 \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  n8n-knowledge-system
```

### Multi-Container Deployment with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Compose Services

The `docker-compose.yml` includes:

- **n8n-knowledge-app**: Main application (API + Next.js frontend)
- **n8n-knowledge-updater**: Automated update scheduler
- **chromadb**: Vector database
- **redis**: Caching layer
- **nginx**: Reverse proxy

## Production Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application user
sudo useradd -m -s /bin/bash n8n-app
sudo usermod -aG docker n8n-app
```

### 2. Application Setup

```bash
# Switch to application user
sudo su - n8n-app

# Clone repository
git clone <repository-url> n8n-knowledge-system
cd n8n-knowledge-system

# Set up environment
cp .env.example .env
# Edit .env with production values
```

### 3. Production Configuration

Update `.env` for production:

```bash
# Security
API_DEBUG=false
DEVELOPMENT_MODE=false
API_SECRET_KEY=<strong-random-key>

# Performance
MAX_WORKERS=8
THREAD_POOL_SIZE=20

# Logging
LOG_LEVEL=INFO

# CORS (adjust for your domain)
CORS_ALLOW_ORIGINS=["https://yourdomain.com"]
```

### 4. SSL/TLS Setup

For HTTPS, update `nginx.conf` or use a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. Start Production Services

```bash
# Start with production compose file
docker-compose -f docker-compose.prod.yml up -d

# Enable auto-restart
docker update --restart=unless-stopped $(docker ps -q)
```

### 6. Set Up Systemd Service (Alternative)

```bash
# Create systemd service
sudo tee /etc/systemd/system/n8n-knowledge.service > /dev/null <<EOF
[Unit]
Description=n8n AI Knowledge System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/n8n-app/n8n-knowledge-system
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=n8n-app

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable n8n-knowledge.service
sudo systemctl start n8n-knowledge.service
```

## Cloud Deployment

### AWS Deployment

#### Using EC2

1. **Launch EC2 Instance**:
   - Instance type: t3.medium or larger
   - OS: Ubuntu 22.04 LTS
   - Security groups: Allow ports 80, 443, 22

2. **Set up Application**:
   ```bash
   # Connect to instance
   ssh -i your-key.pem ubuntu@your-instance-ip
   
   # Follow production deployment steps
   ```

3. **Configure Load Balancer** (optional):
   - Create Application Load Balancer
   - Configure target groups for ports 8000 and 8501
   - Set up health checks

#### Using ECS (Elastic Container Service)

1. **Create ECS Cluster**
2. **Build and push Docker image to ECR**
3. **Create task definitions**
4. **Deploy services**

### Google Cloud Platform

#### Using Compute Engine

```bash
# Create VM instance
gcloud compute instances create n8n-knowledge-system \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-medium \
  --tags=http-server,https-server

# SSH and deploy
gcloud compute ssh n8n-knowledge-system
```

#### Using Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/n8n-knowledge-system
gcloud run deploy --image gcr.io/PROJECT-ID/n8n-knowledge-system --platform managed
```

### Azure Deployment

#### Using Container Instances

```bash
# Create resource group
az group create --name n8n-knowledge-rg --location eastus

# Deploy container
az container create \
  --resource-group n8n-knowledge-rg \
  --name n8n-knowledge-system \
  --image your-registry/n8n-knowledge-system \
  --ports 8000 8501 \
  --environment-variables OPENAI_API_KEY=your-key
```

## Configuration

### Environment Variables

Key configuration options:

```bash
# AI Provider
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
DEFAULT_AI_PROVIDER=openai

# Database
CHROMA_PERSIST_DIRECTORY=./data/vector_db

# API
API_HOST=0.0.0.0
API_PORT=8000

# Security
API_SECRET_KEY=your_secret_key
CORS_ALLOW_ORIGINS=["https://yourdomain.com"]

# Performance
MAX_WORKERS=4
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### Database Configuration

Edit `config/database.yaml`:

```yaml
vector_database:
  provider: "chromadb"
  host: "localhost"
  port: 8001
  persist_directory: "./data/vector_db"
  collection_name: "n8n_docs"
  
cache:
  provider: "redis"
  url: "redis://localhost:6379"
  ttl: 3600
```

### Scheduler Configuration

Edit `config/scheduler.yaml`:

```yaml
scheduler:
  enabled: true
  update_time: "02:00"
  timezone: "UTC"
  max_pages: 500
  backup_retention_days: 7
  
notifications:
  enabled: true
  webhook_url: "https://your-webhook-url"
```

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check system health
curl http://localhost:8000/health

# Check detailed status
curl http://localhost:8000/api/v1/status

# View logs
docker-compose logs -f
```

### Backup Strategy

```bash
# Manual backup
python automation/update_scheduler.py --backup

# Automated backups are created before each update
# Location: ./backups/
```

### Log Management

```bash
# View application logs
tail -f logs/app.log

# View update logs
tail -f logs/automated_updater.log

# Rotate logs (add to crontab)
0 0 * * * find /path/to/logs -name "*.log" -mtime +7 -delete
```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats

# Check database size
du -sh data/vector_db/

# Monitor API performance
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/health
```

### Updates

```bash
# Update application
git pull origin main
docker-compose build
docker-compose up -d

# Update dependencies
pip install -r requirements.txt --upgrade
```

## Troubleshooting

### Common Issues

#### 1. API Key Issues

```bash
# Check environment variables
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Verify API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### 2. Database Connection Issues

```bash
# Check ChromaDB status
docker-compose logs chromadb

# Test connection
curl http://localhost:8001/api/v1/heartbeat
```

#### 3. Memory Issues

```bash
# Check memory usage
free -h
docker stats

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Port Conflicts

```bash
# Check port usage
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :8501

# Change ports in .env file if needed
```

### Debug Mode

```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with verbose logging
python start_system.py --mode full --debug
```

### Getting Help

1. **Check logs**: Always start by checking application logs
2. **Verify configuration**: Ensure all required environment variables are set
3. **Test components**: Use the health check endpoints
4. **Resource monitoring**: Check CPU, memory, and disk usage
5. **Network connectivity**: Verify API access and database connections

### Performance Tuning

```bash
# Optimize for production
export MAX_WORKERS=8
export THREAD_POOL_SIZE=20
export VECTOR_SEARCH_TOP_K=3

# Enable caching
export CACHE_TTL_SECONDS=3600
export CACHE_MAX_SIZE=1000
```

## Security Considerations

1. **API Keys**: Store securely, never commit to version control
2. **HTTPS**: Always use HTTPS in production
3. **Firewall**: Restrict access to necessary ports only
4. **Updates**: Keep system and dependencies updated
5. **Monitoring**: Set up alerts for unusual activity
6. **Backups**: Regular backups with encryption
7. **Access Control**: Implement authentication if needed

## Scaling

### Horizontal Scaling

- Deploy multiple instances behind a load balancer
- Use shared storage for data persistence
- Implement session affinity for chat conversations

### Vertical Scaling

- Increase CPU and memory allocation
- Optimize database configuration
- Tune worker processes and thread pools

### Database Scaling

- Use external ChromaDB cluster
- Implement read replicas
- Consider database sharding for large datasets

This deployment guide should help you get the n8n AI Knowledge System running in various environments. Choose the deployment method that best fits your needs and infrastructure.