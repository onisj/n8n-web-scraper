# n8n Documentation Automation System

🚀 **Complete automation system for scraping, processing, and managing n8n documentation with real-time monitoring and intelligent scheduling.**

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Contributing](#contributing)

## 🎯 Overview

This automation system provides a complete solution for maintaining an up-to-date knowledge base of n8n documentation. It automatically scrapes documentation, processes content, stores it in a PostgreSQL database, and provides comprehensive monitoring and health checks.

### Key Components

- **Automated Scraper** (`automated_scraper.py`) - Core automation engine
- **Monitoring Dashboard** (`monitoring_dashboard.py`) - Real-time system monitoring
- **Service Wrapper** (`automation_service.py`) - Service management and error recovery
- **Installation Script** (`install_automation.py`) - Complete system setup
- **Setup Script** (`setup_automation.py`) - Database and configuration setup

## ✨ Features

### 🤖 Automation
- **Scheduled Scraping** - Configurable intervals (days/hours)
- **Intelligent Processing** - Content extraction and categorization
- **Database Integration** - PostgreSQL storage with duplicate handling
- **Export Generation** - Multiple formats (JSON, CSV, XML)
- **Backup Management** - Automated backups with retention policies
- **Error Recovery** - Comprehensive error handling and retry logic

### 📊 Monitoring
- **Real-time Dashboard** - System health and performance metrics
- **Health Checks** - Automated system status monitoring
- **Performance Tracking** - CPU, memory, disk usage monitoring
- **Data Freshness** - Track data age and update frequency
- **Alert System** - Configurable notifications for issues

### 🔧 Management
- **Service Integration** - systemd (Linux) and launchd (macOS) support
- **Configuration Management** - Environment-based configuration
- **Log Management** - Structured logging with rotation
- **Backup & Recovery** - Automated data protection

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **PostgreSQL 12+**
- **Git**
- **pip**

### One-Command Installation

```bash
# Clone and install everything
git clone <your-repo-url>
cd n8n-web-scrapper
python3 install_automation.py
```

### Quick Test

```bash
# Test the monitoring dashboard
python3 monitoring_dashboard.py

# Run a test scrape
python3 automated_scraper.py --test
```

## 📦 Installation

### Method 1: Automated Installation (Recommended)

```bash
# Run the complete installer
python3 install_automation.py

# Follow the prompts for database setup
# Update .env file with your database credentials
# Start the service
```

### Method 2: Manual Installation

#### 1. Install System Dependencies

**macOS:**
```bash
# Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14
```

**Linux (Ubuntu/Debian):**
```bash
# Install PostgreSQL and development tools
sudo apt update
sudo apt install postgresql postgresql-contrib python3-dev libpq-dev
sudo systemctl start postgresql
```

#### 2. Install Python Dependencies

```bash
# Install requirements
pip3 install -r requirements.txt
pip3 install -r requirements_automation.txt

# Or install individual packages
pip3 install psycopg2-binary schedule requests python-dotenv psutil
```

#### 3. Setup Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE n8n_scraper;
CREATE USER n8n_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE n8n_scraper TO n8n_user;
\q

# Setup database schema
python3 setup_automation.py --setup-db
```

#### 4. Configure Environment

```bash
# Copy and edit configuration
cp .env.example .env
# Edit .env with your database credentials and preferences
```

#### 5. Setup Service (Optional)

**macOS:**
```bash
# Copy launchd plist
cp com.n8n.automation.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.n8n.automation.plist
```

**Linux:**
```bash
# Install systemd service
sudo cp n8n-automation.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable n8n-automation.service
sudo systemctl start n8n-automation.service
```

## ⚙️ Configuration

### Environment Variables (.env)

#### Database Configuration
```env
# PostgreSQL Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=n8n_scraper
DATABASE_USER=n8n_user
DATABASE_PASSWORD=your_secure_password
DATABASE_URL=postgresql://n8n_user:password@localhost:5432/n8n_scraper

# Database Pool Settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
```

#### Automation Configuration
```env
# Scraping Schedule
SCRAPE_ENABLED=true
SCRAPE_INTERVAL_DAYS=2
SCRAPE_INTERVAL_HOURS=0
SCRAPE_SCHEDULE_TIME=02:00

# Processing Options
AUTO_IMPORT_TO_DATABASE=true
AUTO_EXPORT_FORMATS=json,csv
AUTO_BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
```

#### Scraping Configuration
```env
# Scraping Limits
SCRAPE_MAX_PAGES=1000
SCRAPE_DELAY_SECONDS=1
SCRAPE_MAX_RETRIES=3
SCRAPE_TIMEOUT_SECONDS=30
SCRAPE_USER_AGENT=n8n-docs-scraper/1.0
```

#### Notification Configuration
```env
# Email Notifications (Optional)
NOTIFICATION_EMAIL_ENABLED=false
NOTIFICATION_EMAIL_SMTP_HOST=smtp.gmail.com
NOTIFICATION_EMAIL_SMTP_PORT=587
NOTIFICATION_EMAIL_USERNAME=your_email@gmail.com
NOTIFICATION_EMAIL_PASSWORD=your_app_password
NOTIFICATION_EMAIL_TO=admin@yourcompany.com

# Slack Notifications (Optional)
NOTIFICATION_SLACK_ENABLED=false
NOTIFICATION_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## 🎮 Usage

### Command Line Interface

#### Automated Scraper
```bash
# Run full automation cycle
python3 automated_scraper.py

# Test mode (limited scraping)
python3 automated_scraper.py --test

# Force run (ignore schedule)
python3 automated_scraper.py --force

# Dry run (no database changes)
python3 automated_scraper.py --dry-run

# Custom configuration
python3 automated_scraper.py --max-pages 100 --delay 2
```

#### Monitoring Dashboard
```bash
# Show current status
python3 monitoring_dashboard.py

# Watch mode (refresh every 30 seconds)
python3 monitoring_dashboard.py --watch 30

# JSON output
python3 monitoring_dashboard.py --format json

# Save report to file
python3 monitoring_dashboard.py --save
```

#### Service Management
```bash
# Start automation service
python3 automation_service.py

# Check service status
python3 automation_service.py --status

# Stop service
python3 automation_service.py --stop
```

### Service Control

**macOS (launchd):**
```bash
# Start service
launchctl start com.n8n.automation

# Stop service
launchctl stop com.n8n.automation

# Check status
launchctl list | grep n8n
```

**Linux (systemd):**
```bash
# Start service
sudo systemctl start n8n-automation.service

# Stop service
sudo systemctl stop n8n-automation.service

# Check status
sudo systemctl status n8n-automation.service

# View logs
sudo journalctl -u n8n-automation.service -f
```

## 📊 Monitoring

### Dashboard Features

- **System Health** - Overall system status with color-coded indicators
- **Performance Metrics** - CPU, memory, disk usage
- **Database Statistics** - Document counts, data freshness, size metrics
- **Automation Status** - Last run time, success rate, next scheduled run
- **Recent Logs** - Latest log entries from all components

### Health Status Indicators

- 🟢 **Healthy** - All systems operating normally
- 🟡 **Warning** - Minor issues detected, system functional
- 🔴 **Unhealthy** - Critical issues requiring attention

### Monitoring Commands

```bash
# Real-time dashboard
python3 monitoring_dashboard.py --watch 30

# Health check only
python3 monitoring_dashboard.py --format json | jq '.health_status'

# Generate report
python3 monitoring_dashboard.py --save
```

### Log Files

- `logs/automation.log` - Main automation events
- `logs/system.log` - System-level events
- `logs/error_system.log` - Error messages and stack traces
- `logs/scraper.log` - Detailed scraping activities

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Test database connection
psql -h localhost -U n8n_user -d n8n_scraper

# Check PostgreSQL status
pg_isready

# Restart PostgreSQL (macOS)
brew services restart postgresql@14

# Restart PostgreSQL (Linux)
sudo systemctl restart postgresql
```

#### Permission Issues
```bash
# Fix file permissions
chmod +x automated_scraper.py
chmod +x monitoring_dashboard.py
chmod +x automation_service.py

# Fix directory permissions
chmod -R 755 data/ logs/
```

#### Service Issues
```bash
# Check service logs (macOS)
log show --predicate 'process == "python3"' --last 1h

# Check service logs (Linux)
sudo journalctl -u n8n-automation.service --since "1 hour ago"

# Restart service
# macOS: launchctl unload/load
# Linux: sudo systemctl restart n8n-automation.service
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 automated_scraper.py --test

# Verbose monitoring
python3 monitoring_dashboard.py --format json | jq .
```

### Performance Issues

```bash
# Check system resources
python3 monitoring_dashboard.py | grep -A 10 "SYSTEM METRICS"

# Reduce scraping load
# Edit .env: SCRAPE_DELAY_SECONDS=3
# Edit .env: SCRAPE_MAX_PAGES=500
```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    n8n Automation System                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Web Scraper    │  │   Data Processor │  │  Database   │ │
│  │                 │  │                 │  │             │ │
│  │ • HTTP Requests │  │ • Content Parse │  │ • PostgreSQL│ │
│  │ • Rate Limiting │  │ • Categorization│  │ • Indexing  │ │
│  │ • Error Retry   │  │ • Deduplication │  │ • Backup    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Scheduler     │  │    Monitor      │  │   Service   │ │
│  │                 │  │                 │  │             │ │
│  │ • Cron Jobs     │  │ • Health Checks │  │ • Auto Start│ │
│  │ • Intervals     │  │ • Metrics       │  │ • Recovery  │ │
│  │ • Triggers      │  │ • Alerts        │  │ • Logging   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Scheduler** triggers scraping based on configuration
2. **Web Scraper** fetches documentation pages
3. **Data Processor** extracts and categorizes content
4. **Database** stores processed data with deduplication
5. **Export Generator** creates output files
6. **Backup Manager** creates data backups
7. **Monitor** tracks system health and performance
8. **Notification System** alerts on issues

### File Structure

```
n8n-web-scrapper/
├── automated_scraper.py          # Main automation engine
├── monitoring_dashboard.py       # Real-time monitoring
├── automation_service.py         # Service wrapper
├── install_automation.py         # Complete installer
├── setup_automation.py           # Database setup
├── requirements_automation.txt   # Python dependencies
├── n8n-automation.service        # systemd service file
├── com.n8n.automation.plist      # launchd service file
├── .env                          # Configuration file
├── data/                         # Data directory
│   ├── scraped_docs/            # Raw scraped content
│   ├── exports/                 # Generated exports
│   ├── backups/                 # Database backups
│   └── reports/                 # Monitoring reports
├── logs/                         # Log files
│   ├── automation.log           # Main automation log
│   ├── system.log              # System events
│   └── error_system.log        # Error log
└── vector_db/                   # Vector database (if used)
```

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd n8n-web-scrapper

# Install development dependencies
pip3 install -r requirements.txt
pip3 install -r requirements_automation.txt

# Setup development environment
cp .env.example .env
# Edit .env for development

# Run tests
python3 -m pytest tests/
```

### Adding Features

1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** your changes
4. **Add** tests for new functionality
5. **Update** documentation
6. **Submit** a pull request

### Code Style

- Follow **PEP 8** Python style guide
- Use **type hints** for function parameters
- Add **docstrings** for all functions and classes
- Include **error handling** for external dependencies
- Write **unit tests** for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. **Check** the troubleshooting section
2. **Review** log files for error details
3. **Run** the monitoring dashboard for system status
4. **Create** an issue with detailed information

---

**Made with ❤️ for the n8n community**