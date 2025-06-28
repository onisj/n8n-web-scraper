#!/usr/bin/env python3
"""
Import scraped documentation data into categorized database tables.
Uses the new documentation_pages table structure.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import text
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.n8n_scraper.database.connection import DatabaseManager
from src.n8n_scraper.core.logging_config import get_logger

logger = get_logger(__name__)

def extract_category_from_url(url: str) -> str:
    """Extract category from URL using the same logic as analysis."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if not path_parts:
        return 'root'
    
    main_category = path_parts[0]
    
    # Handle special cases
    if main_category == 'integrations' and len(path_parts) > 1:
        if path_parts[1] in ['builtin', 'creating-nodes']:
            return f"integrations_{path_parts[1]}"
        return 'integrations'
    elif main_category == 'release-notes' and len(path_parts) > 1:
        if path_parts[1] == '0-x':
            return 'release_notes_legacy'
        return 'release_notes'
    elif main_category == 'hosting' and len(path_parts) > 1:
        if path_parts[1] in ['installation', 'configuration', 'architecture']:
            return f"hosting_{path_parts[1]}"
        return 'hosting'
    elif main_category == 'code' and len(path_parts) > 1:
        if path_parts[1] in ['cookbook', 'builtin']:
            return f"code_{path_parts[1]}"
        return 'code'
    
    return main_category.replace('-', '_')

def extract_subcategory_from_url(url: str) -> Optional[str]:
    """Extract subcategory from URL path."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if len(path_parts) >= 3:
        return path_parts[2].replace('-', '_')
    return None

# Mapping of categories to their corresponding table names
CATEGORY_TABLE_MAP = {
    # Integrations - all integration subcategories go to docs_integrations
    'integrations': 'docs_integrations',
    'integrations_builtin': 'docs_integrations',
    'integrations_creating_nodes': 'docs_integrations',
    'integrations_creating-nodes': 'docs_integrations',
    
    # Workflows
    'workflows': 'docs_workflows',
    
    # Hosting - all hosting subcategories go to docs_hosting
    'hosting': 'docs_hosting',
    'hosting_installation': 'docs_hosting',
    'hosting_configuration': 'docs_hosting',
    
    # Release notes - all release note subcategories go to docs_release_notes
    'release_notes': 'docs_release_notes',
    'release_notes_legacy': 'docs_release_notes',
    
    # User management
    'user_management': 'docs_user_management',
    
    # API
    'api': 'docs_api',
    
    # Code - all code subcategories go to docs_code
    'code': 'docs_code',
    'code_builtin': 'docs_code',
    
    # Courses
    'courses': 'docs_courses',
    
    # Advanced AI
    'advanced_ai': 'docs_advanced_ai',
    
    # Glossary
    'glossary': 'docs_glossary'
}

async def load_json_files() -> List[Dict]:
    """Load all JSON files from scraped_docs directory."""
    scraped_docs_dir = Path("data/scraped_docs")
    
    if not scraped_docs_dir.exists():
        logger.error(f"Scraped docs directory not found: {scraped_docs_dir}")
        return []
    
    json_files = list(scraped_docs_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    documents = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'url' in data:
                    documents.append(data)
                else:
                    logger.warning(f"Invalid JSON structure in {json_file}")
        except Exception as e:
            logger.error(f"Error reading {json_file}: {e}")
    
    logger.info(f"Successfully loaded {len(documents)} documents")
    return documents

async def insert_document(db_manager: DatabaseManager, doc: Dict) -> Optional[int]:
    """Insert a document into the main documentation_pages table."""
    try:
        category = extract_category_from_url(doc['url'])
        subcategory = extract_subcategory_from_url(doc['url'])
        
        async with db_manager.get_async_session() as session:
            # Check if document already exists
            result = await session.execute(
                text("SELECT id FROM documentation_pages WHERE url = :url"),
                {"url": doc['url']}
            )
            existing = result.fetchone()
            
            if existing:
                logger.debug(f"Document already exists: {doc['url']}")
                return existing[0]
            
            # Insert new document
            insert_query = text("""
                INSERT INTO documentation_pages (
                    url, title, content, content_length, category, subcategory,
                    headings, links, code_blocks, images, metadata, word_count, scraped_at
                ) VALUES (
                    :url, :title, :content, :content_length, :category, :subcategory,
                    :headings, :links, :code_blocks, :images, :metadata, :word_count, :scraped_at
                ) RETURNING id
            """)
            
            # Parse scraped_at timestamp
            scraped_at = doc.get('scraped_at')
            if isinstance(scraped_at, str):
                try:
                    from datetime import datetime
                    if scraped_at.endswith('Z'):
                        scraped_at = scraped_at[:-1] + '+00:00'
                    scraped_at = datetime.fromisoformat(scraped_at)
                except:
                    scraped_at = None
            
            result = await session.execute(insert_query, {
                "url": doc['url'],
                "title": doc['title'],
                "content": doc['content'],
                "content_length": len(doc['content']),
                "category": category,
                "subcategory": subcategory,
                "headings": json.dumps(doc.get('headings', [])),
                "links": json.dumps(doc.get('links', [])),
                "code_blocks": json.dumps(doc.get('code_blocks', [])),
                "images": json.dumps(doc.get('images', [])),
                "metadata": json.dumps(doc.get('metadata', {})),
                "word_count": doc.get('word_count', 0),
                "scraped_at": scraped_at
            })
            
            document_id = result.fetchone()[0]
            await session.commit()
            
            logger.debug(f"Inserted document {document_id}: {doc['title'][:50]}...")
            return document_id
            
    except Exception as e:
        logger.error(f"Error inserting document {doc['url']}: {e}")
        return None

async def insert_category_document(db_manager: DatabaseManager, doc: Dict, document_id: int, category: str):
    """Insert document into category-specific table."""
    try:
        # Get the correct table name for this category
        table_name = CATEGORY_TABLE_MAP.get(category)
        
        if not table_name:
            logger.debug(f"No specific table for category: {category}")
            return
        
        async with db_manager.get_async_session() as session:
            # Check if already exists in category table
            result = await session.execute(
                text(f"SELECT id FROM {table_name} WHERE document_id = :document_id"),
                {"document_id": document_id}
            )
            existing = result.fetchone()
            
            if existing:
                logger.debug(f"Document already in {table_name}: {document_id}")
                return
            
            # Insert into category table
            insert_query = text(f"""
                INSERT INTO {table_name} (
                    document_id, url, title, content, word_count,
                    headings_count, links_count, code_blocks_count, images_count, metadata
                ) VALUES (
                    :document_id, :url, :title, :content, :word_count,
                    :headings_count, :links_count, :code_blocks_count, :images_count, :metadata
                )
            """)
            
            await session.execute(insert_query, {
                "document_id": document_id,
                "url": doc['url'],
                "title": doc['title'],
                "content": doc['content'],
                "word_count": doc.get('word_count', 0),
                "headings_count": len(doc.get('headings', [])),
                "links_count": len(doc.get('links', [])),
                "code_blocks_count": len(doc.get('code_blocks', [])),
                "images_count": len(doc.get('images', [])),
                "metadata": json.dumps(doc.get('metadata', {}))
            })
            
            await session.commit()
            logger.debug(f"Inserted into {table_name}: {document_id}")
            
    except Exception as e:
        logger.error(f"Error inserting into category table for document {document_id}: {e}")

async def import_categorized_data():
    """Main function to import all data into categorized tables."""
    logger.info("🚀 Starting categorized documentation import...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        # Load all documents
        documents = await load_json_files()
        
        if not documents:
            logger.error("No documents to import")
            return
        
        # Group documents by category
        categorized_docs = {}
        for doc in documents:
            category = extract_category_from_url(doc['url'])
            if category not in categorized_docs:
                categorized_docs[category] = []
            categorized_docs[category].append(doc)
        
        logger.info(f"📊 Documents by category:")
        for category, docs in categorized_docs.items():
            table_name = CATEGORY_TABLE_MAP.get(category, 'No specific table')
            logger.info(f"   {category}: {len(docs)} documents -> {table_name}")
        
        # Import documents
        total_imported = 0
        category_counts = {}
        
        for category, docs in categorized_docs.items():
            logger.info(f"\n📥 Importing {category} documents ({len(docs)} total)...")
            category_count = 0
            
            for i, doc in enumerate(docs, 1):
                # Insert into main table
                document_id = await insert_document(db_manager, doc)
                
                if document_id:
                    # Insert into category table (if applicable)
                    await insert_category_document(db_manager, doc, document_id, category)
                    category_count += 1
                    total_imported += 1
                
                if i % 100 == 0:
                    logger.info(f"   Processed {i}/{len(docs)} {category} documents")
            
            category_counts[category] = category_count
            logger.info(f"✅ Completed {category}: {category_count} documents imported")
        
        logger.info(f"\n🎉 Import completed!")
        logger.info(f"   Total documents imported: {total_imported}")
        logger.info(f"   Category breakdown:")
        for category, count in category_counts.items():
            logger.info(f"     {category}: {count}")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(import_categorized_data())