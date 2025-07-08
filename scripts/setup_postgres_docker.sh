#!/bin/bash

# PostgreSQL Docker Setup Script for n8n Web Scraper
# This script sets up PostgreSQL using Docker for development

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="n8n_postgres"
DB_NAME="n8n_scraper"
DB_USER="n8n_user"
DB_PASSWORD="secure_password_123"
DB_PORT="5432"
POSTGRES_VERSION="15"

echo -e "${BLUE}=== PostgreSQL Docker Setup for n8n Web Scraper ===${NC}"
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed and running${NC}"

# Check if container already exists
if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}⚠ Container '${CONTAINER_NAME}' already exists${NC}"
    read -p "Do you want to remove it and create a new one? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing existing container...${NC}"
        docker stop "${CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${CONTAINER_NAME}" 2>/dev/null || true
        echo -e "${GREEN}✓ Existing container removed${NC}"
    else
        echo -e "${BLUE}Using existing container. Checking if it's running...${NC}"
        if ! docker ps --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${YELLOW}Starting existing container...${NC}"
            docker start "${CONTAINER_NAME}"
        fi
        echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
        echo -e "${BLUE}Connection details:${NC}"
        echo "  Host: localhost"
        echo "  Port: ${DB_PORT}"
        echo "  Database: ${DB_NAME}"
        echo "  User: ${DB_USER}"
        echo "  Password: ${DB_PASSWORD}"
        exit 0
    fi
fi

# Create data directory
echo -e "${BLUE}Creating data directory...${NC}"
mkdir -p "./data/databases/postgresql"
echo -e "${GREEN}✓ Data directory created${NC}"

# Pull PostgreSQL image
echo -e "${BLUE}Pulling PostgreSQL ${POSTGRES_VERSION} image...${NC}"
docker pull "postgres:${POSTGRES_VERSION}"
echo -e "${GREEN}✓ PostgreSQL image pulled${NC}"

# Create and start PostgreSQL container
echo -e "${BLUE}Creating PostgreSQL container...${NC}"
docker run -d \
    --name "${CONTAINER_NAME}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
    -e POSTGRES_INITDB_ARGS="--encoding=UTF-8" \
    -p "${DB_PORT}:5432" \
    -v "$(pwd)/data/databases/postgresql:/var/lib/postgresql/data" \
    --restart unless-stopped \
    "postgres:${POSTGRES_VERSION}"

echo -e "${GREEN}✓ PostgreSQL container created and started${NC}"

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ PostgreSQL failed to start within 30 seconds${NC}"
        echo "Check logs with: docker logs ${CONTAINER_NAME}"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo

# Test connection
echo -e "${BLUE}Testing database connection...${NC}"
if docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT version();" &> /dev/null; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file from template...${NC}"
    cp ".env.example" ".env"
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Update .env file with PostgreSQL settings
echo -e "${BLUE}Updating .env file with PostgreSQL settings...${NC}"

# Function to update or add environment variable
update_env_var() {
    local var_name="$1"
    local var_value="$2"
    local env_file=".env"
    
    if grep -q "^${var_name}=" "$env_file"; then
        # Variable exists, update it
        sed -i.bak "s|^${var_name}=.*|${var_name}=${var_value}|" "$env_file"
    else
        # Variable doesn't exist, add it
        echo "${var_name}=${var_value}" >> "$env_file"
    fi
}

# Update PostgreSQL configuration
update_env_var "DATABASE_HOST" "localhost"
update_env_var "DATABASE_PORT" "${DB_PORT}"
update_env_var "DATABASE_NAME" "${DB_NAME}"
update_env_var "DATABASE_USER" "${DB_USER}"
update_env_var "DATABASE_PASSWORD" "${DB_PASSWORD}"
update_env_var "DATABASE_URL" "postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"
update_env_var "DATABASE_URL_ASYNC" "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"

# Clean up backup file
rm -f ".env.bak"

echo -e "${GREEN}✓ .env file updated with PostgreSQL settings${NC}"

# Display connection information
echo
echo -e "${GREEN}=== PostgreSQL Setup Complete! ===${NC}"
echo
echo -e "${BLUE}Connection Details:${NC}"
echo "  Host: localhost"
echo "  Port: ${DB_PORT}"
echo "  Database: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo "  Password: ${DB_PASSWORD}"
echo
echo -e "${BLUE}Container Management:${NC}"
echo "  Start:   docker start ${CONTAINER_NAME}"
echo "  Stop:    docker stop ${CONTAINER_NAME}"
echo "  Logs:    docker logs ${CONTAINER_NAME}"
echo "  Connect: docker exec -it ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME}"
echo
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Install Python dependencies: pip install psycopg2-binary asyncpg"
echo "2. Test the connection with your application"
echo "3. Run database migrations if needed"
echo
echo -e "${YELLOW}Note: The database data is persisted in ./data/databases/postgresql${NC}"
echo -e "${YELLOW}To completely remove: docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}${NC}"
echo