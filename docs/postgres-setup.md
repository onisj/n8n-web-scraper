# PostgreSQL Setup Guide

## Development Environment

### 1. Install PostgreSQL

**macOS (using Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create Database and User

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Or on macOS:
psql postgres
```

Then run these SQL commands:

```sql
-- Create database
CREATE DATABASE n8n_scraper;

-- Create user with password
CREATE USER scraper_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE n8n_scraper TO scraper_user;

-- Exit
\q
```

### 3. Update Configuration

Update your `.env` file or environment variables:

```env
# Database Configuration
DATABASE_URL=postgresql://scraper_user:your_secure_password@localhost:5432/n8n_scraper
DATABASE_URL_ASYNC=postgresql+asyncpg://scraper_user:your_secure_password@localhost:5432/n8n_scraper
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
```

### 4. Run Database Migrations

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## Production Environment

### Using Docker Compose

Create a `docker-compose.yml` for PostgreSQL:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: n8n_scraper
      POSTGRES_USER: scraper_user
      POSTGRES_PASSWORD: your_secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

Start with:
```bash
docker-compose up -d postgres
```

### Cloud Providers

- **AWS RDS**: Use PostgreSQL RDS instance
- **Google Cloud SQL**: PostgreSQL instance
- **Azure Database**: PostgreSQL service
- **Heroku**: Heroku Postgres add-on

Update the connection strings accordingly for your cloud provider.

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure PostgreSQL is running
2. **Authentication failed**: Check username/password
3. **Database does not exist**: Create the database first
4. **Permission denied**: Grant proper privileges to user

### Useful Commands

```bash
# Check PostgreSQL status
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Connect to database
psql -h localhost -U scraper_user -d n8n_scraper

# List databases
\l

# List tables
\dt

# Describe table
\d table_name
```