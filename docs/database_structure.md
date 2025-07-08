# Database Consolidation Guide

This document describes the new centralized database structure implemented in the n8n Web Scraper project.

## Overview

The project has been updated to use a **centralized database directory structure** for better organization, easier backup management, and improved accountability.

## New Directory Structure

```
./data/databases/
├── sqlite/
│   ├── workflows.db
│   ├── workflows.db-shm
│   └── workflows.db-wal
├── vector/
│   └── chroma.sqlite3
└── postgresql/
    └── (connection configs and backups)
```

## Database Systems

### 1. SQLite Database (Workflow Metadata)
- **Location**: `./data/databases/sqlite/workflows.db`
- **Purpose**: Fast indexing and search of n8n workflow JSON files
- **Features**: 
  - FTS5 full-text search
  - WAL mode for performance
  - Workflow metadata and analysis
- **Configuration**: `WORKFLOW_DB_PATH` and `SQLITE_DB_PATH`

### 2. ChromaDB Vector Database
- **Location**: `./data/databases/vector/chroma.sqlite3`
- **Purpose**: Semantic search and embeddings for AI-powered content similarity
- **Features**:
  - Vector embeddings using SentenceTransformers
  - Cosine similarity search
  - Persistent storage
- **Configuration**: `CHROMA_PERSIST_DIRECTORY` and `VECTOR_DB_DIRECTORY`

### 3. PostgreSQL Database
- **Location**: External server (connection configs in `./data/databases/postgresql/`)
- **Purpose**: Primary database for scraped documentation and unified data model
- **Features**:
  - Unified schema for documents and workflows
  - Full ACID compliance
  - Advanced querying capabilities
- **Configuration**: `DATABASE_URL` and related PostgreSQL settings

## Migration from Old Structure

### Automatic Migration

Use the provided migration script:

```bash
python scripts/migrate_database_structure.py
```

This script will:
1. Create the new directory structure
2. Move existing database files to new locations
3. Clean up old directories
4. Verify the migration

### Manual Migration

If you prefer manual migration:

```bash
# Create new directory structure
mkdir -p ./data/databases/{sqlite,vector,postgresql}

# Move SQLite files
mv ./data/workflows.db* ./data/databases/sqlite/

# Move ChromaDB files
mv ./data/chroma_db/* ./data/databases/vector/
rmdir ./data/chroma_db
```

## Configuration Updates

### Environment Variables

Update your `.env` file with the new paths:

```env
# Database Base Directory
DATABASE_BASE_DIRECTORY=./data/databases

# SQLite Configuration
SQLITE_DB_PATH=./data/databases/sqlite/workflows.db
WORKFLOW_DB_PATH=./data/databases/sqlite/workflows.db
SQLITE_TIMEOUT=30
SQLITE_CHECK_SAME_THREAD=false

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./data/databases/vector
VECTOR_DB_DIRECTORY=./data/databases/vector
CHROMA_COLLECTION_NAME=n8n_docs
CHROMA_DISTANCE_FUNCTION=cosine
```

### Code Changes

The following files have been updated to use the new paths:

- `config/settings.py` - Configuration classes
- `src/n8n_scraper/database/vector_db.py` - Vector database implementation
- `src/n8n_scraper/cli/vector_commands.py` - CLI commands
- `src/n8n_scraper/cli/commands.py` - General CLI commands
- `src/n8n_scraper/automation/knowledge_vector_integration.py` - Automation integration
- `src/n8n_scraper/workflow_integration.py` - Workflow integration

## Benefits of Consolidation

### 1. **Easier Backup Management**
- Single directory to backup all databases
- Consistent backup strategies across all database types
- Simplified disaster recovery procedures

### 2. **Better Organization**
- Clear separation by database type
- Logical grouping of related files
- Easier to understand project structure

### 3. **Simplified Monitoring**
- All database files in one location
- Easier to monitor disk usage and performance
- Centralized logging and metrics collection

### 4. **Easier Deployment**
- Single database directory to mount/copy in containers
- Simplified Docker volume configurations
- Consistent paths across environments

### 5. **Better Accountability**
- Clear ownership and access patterns
- Easier to implement security policies
- Simplified permission management

## Backup Strategies

### Full Database Backup

```bash
# Backup entire database directory
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz ./data/databases/
```

### Individual Database Backups

```bash
# SQLite backup
sqlite3 ./data/databases/sqlite/workflows.db ".backup ./backups/workflows_$(date +%Y%m%d).db"

# ChromaDB backup (copy directory)
cp -r ./data/databases/vector ./backups/vector_$(date +%Y%m%d)/

# PostgreSQL backup
pg_dump $DATABASE_URL > ./backups/postgres_$(date +%Y%m%d).sql
```

## Monitoring and Maintenance

### Database Health Checks

```bash
# Check SQLite integrity
sqlite3 ./data/databases/sqlite/workflows.db "PRAGMA integrity_check;"

# Check ChromaDB collection stats
python -c "from src.n8n_scraper.database.vector_db import VectorDatabase; db = VectorDatabase(); print(db.get_collection_stats())"

# Check PostgreSQL connection
psql $DATABASE_URL -c "SELECT version();"
```

### Disk Usage Monitoring

```bash
# Check database directory size
du -sh ./data/databases/

# Check individual database sizes
du -sh ./data/databases/*/
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   chmod -R 755 ./data/databases/
   ```

2. **Missing Directories**
   ```bash
   mkdir -p ./data/databases/{sqlite,vector,postgresql}
   ```

3. **Old Path References**
   - Check your `.env` file for old paths
   - Restart the application after configuration changes
   - Clear any cached configurations

### Verification Commands

```bash
# Verify new structure
ls -la ./data/databases/*/

# Check configuration
python -c "from config.settings import Settings; s = Settings(); print(f'SQLite: {s.workflow_db_path}'); print(f'Vector: {s.vector_db_directory}')"

# Test database connections
python scripts/check_db_status.py
```

## Future Enhancements

- **Database Sharding**: Split large databases across multiple files
- **Automated Backup Scheduling**: Implement automated backup routines
- **Database Replication**: Set up read replicas for better performance
- **Monitoring Dashboard**: Create a web interface for database monitoring
- **Migration Tools**: Develop tools for schema migrations and data transformations

## Support

If you encounter issues with the database consolidation:

1. Check the migration logs for errors
2. Verify file permissions and ownership
3. Ensure all configuration files are updated
4. Test database connections individually
5. Consult the troubleshooting section above

For additional support, refer to the main project documentation or create an issue in the project repository.