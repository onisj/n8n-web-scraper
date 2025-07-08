#!/usr/bin/env python3
"""
Unified schema migration script.

This script migrates data from the old fragmented schema (categorized_schema.sql)
to the new unified schema, consolidating both documentation and workflow data
into a single, coherent structure.
"""

import asyncio
import asyncpg
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedSchemaMigrator:
    """Handles migration from old schema to unified schema."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection_pool = None
        
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.connection_pool = await asyncpg.create_pool(self.database_url)
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
    
    async def backup_existing_data(self) -> Dict[str, int]:
        """Create backup of existing data before migration."""
        logger.info("Creating backup of existing data...")
        
        backup_counts = {}
        
        async with self.connection_pool.acquire() as conn:
            # Check if old workflow_documents table exists
            old_table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'workflow_documents')"
            )
            
            if old_table_exists:
                # Count records in old workflow_documents table
                count = await conn.fetchval("SELECT COUNT(*) FROM workflow_documents")
                backup_counts['workflow_documents'] = count
                logger.info(f"Found {count} records in workflow_documents table")
                
                # Create backup table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_documents_backup AS 
                    SELECT * FROM workflow_documents
                """)
                logger.info("Created workflow_documents_backup table")
            
            # Check for category-specific tables and back them up
            category_tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'docs_%' AND table_schema = 'public'
            """)
            
            for table_row in category_tables:
                table_name = table_row['table_name']
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                backup_counts[table_name] = count
                
                if count > 0:
                    backup_table_name = f"{table_name}_backup"
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {backup_table_name} AS 
                        SELECT * FROM {table_name}
                    """)
                    logger.info(f"Created backup table {backup_table_name} with {count} records")
        
        logger.info(f"Backup completed. Total tables backed up: {len(backup_counts)}")
        return backup_counts
    
    async def apply_unified_schema(self):
        """Apply the unified schema to the database."""
        logger.info("Applying unified schema...")
        
        schema_file = Path(__file__).parent.parent / "migrations" / "unified_schema.sql"
        
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Execute the entire schema as one transaction
                await conn.execute(schema_sql)
            except Exception as e:
                # Log warnings for expected errors (like table already exists)
                if "already exists" in str(e).lower():
                    logger.warning(f"Some objects already exist, continuing: {e}")
                else:
                    logger.error(f"Failed to apply unified schema: {e}")
                    raise
        
        logger.info("Unified schema applied successfully")
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into statements, properly handling dollar-quoted strings."""
        statements = []
        current_statement = ""
        in_dollar_quote = False
        dollar_tag = ""
        i = 0
        
        while i < len(sql):
            char = sql[i]
            
            if not in_dollar_quote:
                # Check for start of dollar quote
                if char == '$':
                    # Find the end of the dollar tag
                    tag_start = i
                    i += 1
                    while i < len(sql) and sql[i] != '$':
                        i += 1
                    if i < len(sql):
                        dollar_tag = sql[tag_start:i+1]
                        in_dollar_quote = True
                        current_statement += dollar_tag
                        i += 1
                        continue
                elif char == ';':
                    # End of statement
                    current_statement += char
                    stmt = current_statement.strip()
                    if stmt:
                        statements.append(stmt)
                    current_statement = ""
                    i += 1
                    continue
            else:
                # Check for end of dollar quote
                if sql[i:i+len(dollar_tag)] == dollar_tag:
                    current_statement += dollar_tag
                    in_dollar_quote = False
                    dollar_tag = ""
                    i += len(dollar_tag)
                    continue
            
            current_statement += char
            i += 1
        
        # Add any remaining statement
        stmt = current_statement.strip()
        if stmt:
            statements.append(stmt)
        
        return statements
    
    def generate_content_hash(self, content: str) -> str:
        """Generate MD5 hash for content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def migrate_workflow_documents(self) -> int:
        """Migrate workflow documents from old schema to unified schema."""
        logger.info("Migrating workflow documents...")
        
        migrated_count = 0
        
        async with self.connection_pool.acquire() as conn:
            # Check if old workflow_documents table exists
            old_table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'workflow_documents_backup')"
            )
            
            if not old_table_exists:
                logger.warning("No workflow_documents_backup table found, skipping workflow migration")
                return 0
            
            # Get all workflow documents from backup
            old_workflows = await conn.fetch("SELECT * FROM workflow_documents_backup")
            
            for workflow in old_workflows:
                try:
                    # Generate UUID for new record
                    new_id = str(uuid4())
                    
                    # Prepare data for unified table
                    content = workflow.get('content', '')
                    if not content:
                        # If no content, use title + description
                        content = f"{workflow.get('title', '')}\n{workflow.get('description', '')}".strip()
                    
                    content_hash = self.generate_content_hash(content)
                    
                    # Extract metadata from old record
                    metadata = workflow.get('metadata', {}) or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            metadata = {}
                    
                    # Insert into unified_documents table
                    await conn.execute("""
                        INSERT INTO unified_documents (
                            id, document_type, source_type, title, description, content, 
                            content_hash, url, category, subcategory, word_count, 
                            content_length, headings, links, code_blocks, images,
                            headings_count, links_count, code_blocks_count, images_count,
                            metadata, scraped_at, created_at, updated_at
                        ) VALUES (
                            $1, 'documentation', 'web_scrape', $2, $3, $4, $5, $6, $7, $8, 
                            $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22
                        )
                    """, 
                        new_id,
                        workflow.get('title', 'Untitled'),
                        None,  # description
                        content,
                        content_hash,
                        workflow.get('url'),
                        workflow.get('category'),
                        workflow.get('subcategory'),
                        workflow.get('word_count'),
                        workflow.get('content_length'),
                        workflow.get('headings', []) or [],
                        workflow.get('links', []) or [],
                        workflow.get('code_blocks', []) or [],
                        workflow.get('images', []) or [],
                        workflow.get('headings_count'),
                        workflow.get('links_count'),
                        workflow.get('code_blocks_count'),
                        workflow.get('images_count'),
                        json.dumps(metadata),
                        workflow.get('scraped_at'),
                        workflow.get('created_at', datetime.utcnow()),
                        workflow.get('updated_at', datetime.utcnow())
                    )
                    
                    migrated_count += 1
                    
                    if migrated_count % 100 == 0:
                        logger.info(f"Migrated {migrated_count} workflow documents...")
                        
                except Exception as e:
                    logger.error(f"Failed to migrate workflow document {workflow.get('id')}: {e}")
                    continue
        
        logger.info(f"Successfully migrated {migrated_count} workflow documents")
        return migrated_count
    
    async def migrate_category_documents(self) -> int:
        """Migrate category-specific documents to unified schema."""
        logger.info("Migrating category-specific documents...")
        
        migrated_count = 0
        
        async with self.connection_pool.acquire() as conn:
            # Get all category backup tables
            category_tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'docs_%_backup' AND table_schema = 'public'
            """)
            
            for table_row in category_tables:
                table_name = table_row['table_name']
                original_table = table_name.replace('_backup', '')
                category = original_table.replace('docs_', '').replace('_', ' ').title()
                
                logger.info(f"Migrating documents from {table_name} (category: {category})...")
                
                try:
                    # Get all documents from this category table
                    documents = await conn.fetch(f"SELECT * FROM {table_name}")
                    
                    for doc in documents:
                        try:
                            # Generate UUID for new record
                            new_id = str(uuid4())
                            
                            content = doc.get('content', '')
                            if not content:
                                content = f"{doc.get('title', '')}\n{doc.get('description', '')}".strip()
                            
                            content_hash = self.generate_content_hash(content)
                            
                            # Extract metadata
                            metadata = doc.get('metadata', {}) or {}
                            if isinstance(metadata, str):
                                try:
                                    metadata = json.loads(metadata)
                                except json.JSONDecodeError:
                                    metadata = {}
                            
                            # Insert into unified_documents table
                            await conn.execute("""
                                INSERT INTO unified_documents (
                                    id, document_type, source_type, title, description, content, 
                                    content_hash, url, category, word_count, content_length,
                                    headings_count, links_count, code_blocks_count, images_count,
                                    metadata, created_at, updated_at
                                ) VALUES (
                                    $1, 'documentation', 'web_scrape', $2, $3, $4, $5, $6, $7, 
                                    $8, $9, $10, $11, $12, $13, $14, $15, $16
                                )
                                ON CONFLICT (url, content_hash) DO NOTHING
                            """, 
                                new_id,
                                doc.get('title', 'Untitled'),
                                None,  # description
                                content,
                                content_hash,
                                doc.get('url'),
                                category,
                                doc.get('word_count'),
                                doc.get('content_length'),
                                doc.get('headings_count'),
                                doc.get('links_count'),
                                doc.get('code_blocks_count'),
                                doc.get('images_count'),
                                json.dumps(metadata),
                                doc.get('created_at', datetime.utcnow()),
                                doc.get('updated_at', datetime.utcnow())
                            )
                            
                            migrated_count += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to migrate document {doc.get('id')} from {table_name}: {e}")
                            continue
                    
                    logger.info(f"Migrated {len(documents)} documents from {table_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to migrate table {table_name}: {e}")
                    continue
        
        logger.info(f"Successfully migrated {migrated_count} category documents")
        return migrated_count
    
    async def migrate_workflow_files(self, workflows_dir: Path) -> int:
        """Migrate workflow JSON files to unified schema."""
        logger.info(f"Migrating workflow files from {workflows_dir}...")
        
        if not workflows_dir.exists():
            logger.warning(f"Workflows directory not found: {workflows_dir}")
            return 0
        
        migrated_count = 0
        
        # Find all JSON files in the workflows directory
        json_files = list(workflows_dir.rglob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        async with self.connection_pool.acquire() as conn:
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                    
                    # Generate UUID for new record
                    new_id = str(uuid4())
                    
                    # Extract workflow information
                    workflow_name = workflow_data.get('name', json_file.stem)
                    workflow_id = workflow_data.get('id')
                    description = workflow_data.get('description', '')
                    
                    # Create content from workflow data
                    content_parts = []
                    if workflow_name:
                        content_parts.append(f"Workflow: {workflow_name}")
                    if description:
                        content_parts.append(f"Description: {description}")
                    
                    # Add node information
                    nodes = workflow_data.get('nodes', [])
                    if nodes:
                        content_parts.append(f"Nodes ({len(nodes)}):")
                        for node in nodes:
                            node_name = node.get('name', 'Unnamed Node')
                            node_type = node.get('type', 'Unknown')
                            content_parts.append(f"- {node_name} ({node_type})")
                    
                    content = "\n".join(content_parts)
                    content_hash = self.generate_content_hash(content)
                    
                    # Analyze workflow
                    node_count = len(nodes)
                    node_types = list(set(node.get('type', 'Unknown') for node in nodes))
                    
                    # Extract integrations (node types that aren't built-in)
                    builtin_types = {'Start', 'Set', 'IF', 'Switch', 'Merge', 'NoOp', 'Function', 'FunctionItem'}
                    integrations = [nt for nt in node_types if nt not in builtin_types]
                    
                    # Count connections
                    connections = workflow_data.get('connections', {})
                    connection_count = sum(len(conns) for conns in connections.values()) if connections else 0
                    
                    # Determine trigger types
                    trigger_types = []
                    for node in nodes:
                        if node.get('type') in ['Trigger', 'Webhook', 'Cron', 'Manual Trigger']:
                            trigger_types.append(node.get('type'))
                    
                    # Calculate complexity score (simple heuristic)
                    complexity_score = min(1.0, (node_count + connection_count) / 100.0)
                    
                    # Insert into unified_documents table
                    await conn.execute("""
                        INSERT INTO unified_documents (
                            id, document_type, source_type, title, description, content, 
                            content_hash, file_path, file_name, category, workflow_id,
                            workflow_data, node_count, connection_count, trigger_types,
                            node_types, integrations, complexity_score, word_count,
                            content_length, metadata, created_at, updated_at
                        ) VALUES (
                            $1, 'workflow', 'file_import', $2, $3, $4, $5, $6, $7, $8, $9,
                            $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                        )
                        ON CONFLICT (file_path) DO UPDATE SET
                            content = EXCLUDED.content,
                            content_hash = EXCLUDED.content_hash,
                            workflow_data = EXCLUDED.workflow_data,
                            node_count = EXCLUDED.node_count,
                            connection_count = EXCLUDED.connection_count,
                            updated_at = CURRENT_TIMESTAMP
                    """, 
                        new_id,
                        workflow_name,
                        description,
                        content,
                        content_hash,
                        str(json_file.relative_to(workflows_dir.parent)),
                        json_file.name,
                        'workflow',
                        workflow_id,
                        json.dumps(workflow_data),
                        node_count,
                        connection_count,
                        json.dumps(trigger_types),
                        json.dumps(node_types),
                        json.dumps(integrations),
                        complexity_score,
                        len(content.split()),
                        len(content),
                        json.dumps({
                            'file_size': json_file.stat().st_size,
                            'file_modified': datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                        }),
                        datetime.utcnow(),
                        datetime.utcnow()
                    )
                    
                    migrated_count += 1
                    
                    if migrated_count % 50 == 0:
                        logger.info(f"Migrated {migrated_count} workflow files...")
                        
                except Exception as e:
                    logger.error(f"Failed to migrate workflow file {json_file}: {e}")
                    continue
        
        logger.info(f"Successfully migrated {migrated_count} workflow files")
        return migrated_count
    
    async def verify_migration(self) -> Dict[str, int]:
        """Verify the migration by counting records in the new schema."""
        logger.info("Verifying migration...")
        
        counts = {}
        
        async with self.connection_pool.acquire() as conn:
            # Count total documents
            total_count = await conn.fetchval("SELECT COUNT(*) FROM unified_documents")
            counts['total_documents'] = total_count
            
            # Count by document type
            doc_count = await conn.fetchval(
                "SELECT COUNT(*) FROM unified_documents WHERE document_type = 'documentation'"
            )
            counts['documentation_documents'] = doc_count
            
            workflow_count = await conn.fetchval(
                "SELECT COUNT(*) FROM unified_documents WHERE document_type = 'workflow'"
            )
            counts['workflow_documents'] = workflow_count
            
            # Count chunks
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM unified_chunks")
            counts['total_chunks'] = chunk_count
            
            # Count by category
            categories = await conn.fetch(
                "SELECT category, COUNT(*) as count FROM unified_documents GROUP BY category ORDER BY count DESC"
            )
            
            logger.info("Migration verification results:")
            for key, value in counts.items():
                logger.info(f"  {key}: {value}")
            
            logger.info("Documents by category:")
            for cat in categories:
                logger.info(f"  {cat['category'] or 'None'}: {cat['count']}")
        
        return counts
    
    async def cleanup_old_tables(self, confirm: bool = False):
        """Clean up old tables after successful migration."""
        if not confirm:
            logger.warning("Cleanup not confirmed. Use confirm=True to actually remove old tables.")
            return
        
        logger.info("Cleaning up old tables...")
        
        async with self.connection_pool.acquire() as conn:
            # Get all old tables
            old_tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'docs_%' AND table_name NOT LIKE '%_backup'
                AND table_schema = 'public'
            """)
            
            for table_row in old_tables:
                table_name = table_row['table_name']
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                    logger.info(f"Dropped table {table_name}")
                except Exception as e:
                    logger.error(f"Failed to drop table {table_name}: {e}")
        
        logger.info("Cleanup completed")


async def main():
    """Main migration function."""
    import os
    from pathlib import Path
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    # Initialize migrator
    migrator = UnifiedSchemaMigrator(database_url)
    
    try:
        await migrator.initialize()
        
        # Step 1: Backup existing data
        backup_counts = await migrator.backup_existing_data()
        logger.info(f"Backup completed: {backup_counts}")
        
        # Step 2: Apply unified schema
        await migrator.apply_unified_schema()
        
        # Step 3: Migrate workflow documents
        workflow_migrated = await migrator.migrate_workflow_documents()
        
        # Step 4: Migrate category documents
        category_migrated = await migrator.migrate_category_documents()
        
        # Step 5: Migrate workflow files
        workflows_dir = Path("data/workflows/files")
        files_migrated = await migrator.migrate_workflow_files(workflows_dir)
        
        # Step 6: Verify migration
        verification_counts = await migrator.verify_migration()
        
        logger.info("\n=== MIGRATION SUMMARY ===")
        logger.info(f"Workflow documents migrated: {workflow_migrated}")
        logger.info(f"Category documents migrated: {category_migrated}")
        logger.info(f"Workflow files migrated: {files_migrated}")
        logger.info(f"Total documents in unified schema: {verification_counts.get('total_documents', 0)}")
        
        # Optional: Clean up old tables (commented out for safety)
        # await migrator.cleanup_old_tables(confirm=True)
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())