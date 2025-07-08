# PostgreSQL Setup Guide

This guide will help you set up PostgreSQL for the n8n Web Scraper project. PostgreSQL is configured but requires external server setup.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Database Setup](#database-setup)
4. [Configuration](#configuration)
5. [Testing Connection](#testing-connection)
6. [Docker Setup (Recommended)](#docker-setup-recommended)
7. [Production Considerations](#production-considerations)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

- PostgreSQL 12 or higher
- Python 3.8+
- Administrative access to create databases and users

## Installation

### macOS (using Homebrew)

```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Create a database cluster (if needed)
initdb /usr/local/var/postgres
```

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### CentOS/RHEL

```bash
# Install PostgreSQL
sudo yum install postgresql-server postgresql-contrib

# Initialize database
sudo postgresql-setup initdb

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Windows

1. Download PostgreSQL installer from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the setup wizard
3. Remember the password you set for the `postgres` user

## Database Setup

### 1. Access PostgreSQL

```bash
# Switch to postgres user (Linux/macOS)
sudo -u postgres psql

# Or connect directly (if postgres user has password)
psql -U postgres -h localhost
```

### 2. Create Database and User

```sql
-- Create database
CREATE DATABASE n8n_scraper;

-- Create user
CREATE USER n8n_user WITH PASSWORD 'secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE n8n_scraper TO n8n_user;

-- Grant schema privileges
\c n8n_scraper
GRANT ALL ON SCHEMA public TO n8n_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO n8n_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO n8n_user;

-- Exit psql
\q
```

### 3. Test Connection

```bash
# Test connection with new user
psql -U n8n_user -d n8n_scraper -h localhost
```

## Configuration

### 1. Update Environment Variables

Create or update your `.env` file:

```bash
# Copy example environment file
cp .env.example .env
```

Update the PostgreSQL configuration in `.env`:

```env
# PostgreSQL Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=n8n_scraper
DATABASE_USER=n8n_user
DATABASE_PASSWORD=secure_password_here
DATABASE_URL=postgresql://n8n_user:secure_password_here@localhost:5432/n8n_scraper
DATABASE_URL_ASYNC=postgresql+asyncpg://n8n_user:secure_password_here@localhost:5432/n8n_scraper

# Database Pool Settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
```

### 2. Install Python Dependencies

```bash
# Install PostgreSQL adapter for Python
pip install psycopg2-binary asyncpg

# Or if using requirements.txt
pip install -r requirements.txt
```

## Testing Connection

### 1. Test with Python Script

Create a test script `test_postgres.py`:

```python
import psycopg2
from config.settings import settings

def test_connection():
    try:
        # Test connection
        conn = psycopg2.connect(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ PostgreSQL connection successful!")
        print(f"✓ Version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
```

Run the test:

```bash
python test_postgres.py
```

### 2. Test with CLI

```bash
# Test connection using psql
psql -U n8n_user -d n8n_scraper -h localhost -c "SELECT version();"
```

## Docker Setup (Recommended)

For development, using Docker is often easier:

### 1. Create Docker Compose File

Create `docker-compose.postgres.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: n8n_postgres
    environment:
      POSTGRES_DB: n8n_scraper
      POSTGRES_USER: n8n_user
      POSTGRES_PASSWORD: secure_password_here
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./data/databases/postgresql:/docker-entrypoint-initdb.d
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n_user -d n8n_scraper"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local
```

### 2. Start PostgreSQL with Docker

```bash
# Start PostgreSQL container
docker-compose -f docker-compose.postgres.yml up -d

# Check logs
docker-compose -f docker-compose.postgres.yml logs postgres

# Stop when done
docker-compose -f docker-compose.postgres.yml down
```

### 3. Connect to Docker PostgreSQL

```bash
# Connect to PostgreSQL in container
docker exec -it n8n_postgres psql -U n8n_user -d n8n_scraper
```

## Production Considerations

### 1. Security

- Use strong passwords
- Configure `pg_hba.conf` for proper authentication
- Enable SSL/TLS connections
- Restrict network access

### 2. Performance

```sql
-- Optimize PostgreSQL settings in postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 100
```

### 3. Backup Strategy

```bash
# Create backup
pg_dump -U n8n_user -h localhost n8n_scraper > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql -U n8n_user -h localhost n8n_scraper < backup_20231201_120000.sql
```

### 4. Monitoring

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('n8n_scraper'));

-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'n8n_scraper';

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if port is open
netstat -an | grep 5432

# Check PostgreSQL configuration
sudo nano /etc/postgresql/*/main/postgresql.conf
# Ensure: listen_addresses = '*' or 'localhost'
```

#### 2. Authentication Failed

```bash
# Check pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add line: local   all   n8n_user   md5

# Reload configuration
sudo systemctl reload postgresql
```

#### 3. Database Does Not Exist

```sql
-- List all databases
\l

-- Create database if missing
CREATE DATABASE n8n_scraper;
```

#### 4. Permission Denied

```sql
-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE n8n_scraper TO n8n_user;
GRANT ALL ON SCHEMA public TO n8n_user;
```

### Logs and Debugging

```bash
# View PostgreSQL logs (Ubuntu/Debian)
sudo tail -f /var/log/postgresql/postgresql-*-main.log

# View PostgreSQL logs (CentOS/RHEL)
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log

# View PostgreSQL logs (macOS with Homebrew)
tail -f /usr/local/var/log/postgres.log

# Docker logs
docker logs n8n_postgres
```

### Performance Issues

```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Next Steps

After setting up PostgreSQL:

1. **Run Database Migrations**: Use Alembic or your migration tool
2. **Test Application**: Ensure all features work with PostgreSQL
3. **Monitor Performance**: Set up monitoring and alerting
4. **Configure Backups**: Implement automated backup strategy
5. **Security Review**: Ensure production security measures

## Additional Resources

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [PostgreSQL Security Best Practices](https://www.postgresql.org/docs/current/security.html)
- [Docker PostgreSQL Image](https://hub.docker.com/_/postgres)

---

**Note**: This guide provides a comprehensive setup for PostgreSQL. Choose the installation method that best fits your environment and requirements.