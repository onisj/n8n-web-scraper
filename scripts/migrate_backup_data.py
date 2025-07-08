#!/usr/bin/env python3
"""
Corrected data migration script to move data from backup tables to unified schema.
"""

import asyncio
import asyncpg
import json
import hashlib
import logging
from datetime import datetime
from uuid import uuid4
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupDataMigrator:
    """Migrates data from backup tables to unified schema."""
    
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
    
    def generate_content_hash(self, content: str) -> str:
        """Generate MD5 hash for content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def migrate_workflow_documents(self) -> int:
        """Migrate workflow documents from backup table."""
        logger.info("Migrating workflow documents...")
        
        migrated_count = 0
        
        async with self.connection_pool.acquire() as conn:
            # Get all workflow documents from backup
            try:
                workflows = await conn.fetch("SELECT * FROM workflow_documents_backup LIMIT 500")
                logger.info(f"Found {len(workflows)} workflow documents to migrate")
                
                for workflow in workflows:
                    try:
                        # Generate UUID for new record
                        new_id = str(uuid4())
                        
                        # Prepare content from workflow data
                        title = workflow['workflow_name'] or 'Untitled Workflow'
                        description = workflow['workflow_description'] or ''
                        
                        # Create content from workflow information
                        content_parts = [f"Workflow: {title}"]
                        if description:
                            content_parts.append(f"Description: {description}")
                        if workflow['node_count']:
                            content_parts.append(f"Node Count: {workflow['node_count']}")
                        if workflow['trigger_type']:
                            content_parts.append(f"Trigger Type: {workflow['trigger_type']}")
                        
                        content = "\n".join(content_parts)
                        content_hash = self.generate_content_hash(content)
                        
                        # Check if document already exists
                        existing = await conn.fetchval(
                            "SELECT id FROM unified_documents WHERE content_hash = $1",
                            content_hash
                        )
                        
                        if existing:
                            logger.debug(f"Document with hash {content_hash} already exists, skipping")
                            continue
                        
                        # Prepare metadata
                        metadata = {
                            'file_path': workflow['file_path'],
                            'file_name': workflow['file_name'],
                            'file_size': workflow['file_size'],
                            'node_count': workflow['node_count'],
                            'trigger_type': workflow['trigger_type'],
                            'original_complexity_score': workflow['complexity_score'],
                            'original_quality_score': workflow['quality_score'],
                            'processing_status': workflow['processing_status'],
                            'is_processed': workflow['is_processed']
                        }
                        
                        # Handle integrations array
                        integrations = workflow['integrations'] or []
                        tags = workflow['workflow_tags'] or []
                        
                        # Normalize scores to be between 0 and 1
                        complexity_score = None
                        quality_score = None
                        
                        if workflow['complexity_score'] is not None:
                            # If score is > 1, assume it's on a 0-100 scale and normalize
                            raw_complexity = float(workflow['complexity_score'])
                            if raw_complexity > 1:
                                complexity_score = min(raw_complexity / 100.0, 1.0)
                            else:
                                complexity_score = raw_complexity
                        
                        if workflow['quality_score'] is not None:
                            # If score is > 1, assume it's on a 0-100 scale and normalize
                            raw_quality = float(workflow['quality_score'])
                            if raw_quality > 1:
                                quality_score = min(raw_quality / 100.0, 1.0)
                            else:
                                quality_score = raw_quality
                        
                        # Insert into unified_documents table using correct column names
                        await conn.execute("""
                            INSERT INTO unified_documents (
                                id, document_type, source_type, file_path, title, content, 
                                content_hash, word_count, content_length, 
                                category, tags, node_count, integrations,
                                quality_score, complexity_score, is_processed,
                                metadata, created_at, updated_at
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, 
                                $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
                            )
                        """, 
                            new_id,
                            'workflow',
                            'file_import',
                            workflow['file_path'],
                            title,
                            content,
                            content_hash,
                            len(content.split()) if content else 0,
                            len(content) if content else 0,
                            'workflow',
                            json.dumps(tags),
                            workflow['node_count'],
                            json.dumps(integrations),
                            quality_score,
                            complexity_score,
                            workflow['is_processed'],
                            json.dumps(metadata),
                            workflow['created_at'] or datetime.utcnow(),
                            workflow['updated_at'] or datetime.utcnow()
                        )
                        
                        migrated_count += 1
                        
                        if migrated_count % 10 == 0:
                            logger.info(f"Migrated {migrated_count} workflow documents...")
                            
                    except Exception as e:
                        logger.error(f"Failed to migrate workflow document {workflow.get('id')}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to fetch workflow documents: {e}")
                return 0
        
        logger.info(f"Successfully migrated {migrated_count} workflow documents")
        return migrated_count
    
    async def migrate_docs_backup_tables(self) -> int:
        """Migrate documents from docs backup tables."""
        logger.info("Migrating documents from backup tables...")
        
        migrated_count = 0
        
        async with self.connection_pool.acquire() as conn:
            # Get all docs backup tables
            backup_tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'docs_%_backup' 
                AND table_name NOT LIKE '%_backup_backup%'
                AND table_schema = 'public'
                ORDER BY table_name
            """)
            
            logger.info(f"Found {len(backup_tables)} backup tables to migrate")
            
            for table_row in backup_tables:
                table_name = table_row['table_name']
                # Extract category from table name
                category = table_name.replace('docs_', '').replace('_backup', '').replace('_', ' ').title()
                
                logger.info(f"Migrating documents from {table_name} (category: {category})...")
                
                try:
                    # Get documents from this table
                    documents = await conn.fetch(f"SELECT * FROM {table_name} LIMIT 50")
                    
                    for doc in documents:
                        try:
                            # Generate UUID for new record
                            new_id = str(uuid4())
                            
                            title = doc['title'] or 'Untitled Document'
                            content = doc['content'] or ''
                            content_hash = self.generate_content_hash(content)
                            
                            # Check if document already exists
                            existing = await conn.fetchval(
                                "SELECT id FROM unified_documents WHERE content_hash = $1",
                                content_hash
                            )
                            
                            if existing:
                                logger.debug(f"Document with hash {content_hash} already exists, skipping")
                                continue
                            
                            # Prepare metadata
                            metadata = doc.get('metadata', {}) or {}
                            if isinstance(metadata, str):
                                try:
                                    metadata = json.loads(metadata)
                                except json.JSONDecodeError:
                                    metadata = {}
                            
                            # Insert into unified_documents table using correct column names
                            await conn.execute("""
                                INSERT INTO unified_documents (
                                    id, document_type, source_type, url, title, content, 
                                    content_hash, word_count, content_length, category,
                                    headings_count, links_count, code_blocks_count, images_count,
                                    metadata, created_at, updated_at
                                ) VALUES (
                                    $1, 'documentation', 'web_scrape', $2, $3, $4, $5, $6, $7, $8,
                                    $9, $10, $11, $12, $13, $14, $15
                                )
                            """, 
                                new_id,
                                doc['url'],
                                title,
                                content,
                                content_hash,
                                doc['word_count'] or len(content.split()) if content else 0,
                                len(content) if content else 0,
                                category,
                                doc['headings_count'] or 0,
                                doc['links_count'] or 0,
                                doc['code_blocks_count'] or 0,
                                doc['images_count'] or 0,
                                json.dumps(metadata),
                                doc['created_at'] or datetime.utcnow(),
                                datetime.utcnow()
                            )
                            
                            migrated_count += 1
                            
                            if migrated_count % 10 == 0:
                                logger.info(f"Migrated {migrated_count} documents so far...")
                            
                        except Exception as e:
                            logger.error(f"Failed to migrate document {doc.get('id')} from {table_name}: {e}")
                            continue
                    
                    logger.info(f"Processed {len(documents)} documents from {table_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to migrate table {table_name}: {e}")
                    continue
        
        logger.info(f"Successfully migrated {migrated_count} documents from backup tables")
        return migrated_count
    
    async def verify_migration(self) -> dict:
        """Verify the migration results."""
        logger.info("Verifying migration...")
        
        async with self.connection_pool.acquire() as conn:
            # Count total documents
            total_count = await conn.fetchval("SELECT COUNT(*) FROM unified_documents")
            
            # Count by document type
            doc_count = await conn.fetchval(
                "SELECT COUNT(*) FROM unified_documents WHERE document_type = 'documentation'"
            )
            workflow_count = await conn.fetchval(
                "SELECT COUNT(*) FROM unified_documents WHERE document_type = 'workflow'"
            )
            
            # Count by category
            categories = await conn.fetch(
                "SELECT category, COUNT(*) as count FROM unified_documents GROUP BY category ORDER BY count DESC LIMIT 10"
            )
            
            results = {
                'total_documents': total_count,
                'documentation_documents': doc_count,
                'workflow_documents': workflow_count,
                'categories': [(cat['category'], cat['count']) for cat in categories]
            }
            
            logger.info("Migration verification results:")
            for key, value in results.items():
                if key != 'categories':
                    logger.info(f"  {key}: {value}")
            
            logger.info("Top categories:")
            for category, count in results['categories']:
                logger.info(f"  {category or 'None'}: {count}")
            
            return results


async def main():
    """Main migration function."""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        database_url = "postgresql://root:root@localhost:5432/n8n_scraper"
    
    # Initialize migrator
    migrator = BackupDataMigrator(database_url)
    
    try:
        await migrator.initialize()
        
        # Step 1: Migrate workflow documents
        workflow_migrated = await migrator.migrate_workflow_documents()
        
        # Step 2: Migrate documentation from backup tables
        docs_migrated = await migrator.migrate_docs_backup_tables()
        
        # Step 3: Verify migration
        verification_results = await migrator.verify_migration()
        
        logger.info("\n=== MIGRATION SUMMARY ===")
        logger.info(f"Workflow documents migrated: {workflow_migrated}")
        logger.info(f"Documentation documents migrated: {docs_migrated}")
        logger.info(f"Total documents in unified schema: {verification_results['total_documents']}")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())