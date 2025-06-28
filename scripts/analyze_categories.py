#!/usr/bin/env python3
"""
Script to analyze the categories in the CSV export and create a categorized data import system.
"""

import csv
import json
import re
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlparse

def extract_category_from_url(url):
    """Extract the main category from a docs.n8n.io URL."""
    # Parse URL and get path
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if not path_parts:
        return 'root'
    
    # First part after domain is the main category
    main_category = path_parts[0]
    
    # Handle special cases
    if main_category == 'integrations' and len(path_parts) > 1:
        # For integrations, we might want subcategories
        if path_parts[1] in ['builtin', 'creating-nodes']:
            return f"integrations_{path_parts[1]}"
        return 'integrations'
    elif main_category == 'release-notes' and len(path_parts) > 1:
        # Separate current and legacy release notes
        if path_parts[1] == '0-x':
            return 'release_notes_legacy'
        return 'release_notes'
    elif main_category == 'hosting' and len(path_parts) > 1:
        # Subcategorize hosting docs
        if path_parts[1] in ['installation', 'configuration', 'architecture']:
            return f"hosting_{path_parts[1]}"
        return 'hosting'
    elif main_category == 'code' and len(path_parts) > 1:
        # Subcategorize code docs
        if path_parts[1] in ['cookbook', 'builtin']:
            return f"code_{path_parts[1]}"
        return 'code'
    
    # Clean category name (replace hyphens with underscores)
    return main_category.replace('-', '_')

def analyze_csv_categories():
    """Analyze the CSV file to understand all categories."""
    csv_path = Path("data/exports/n8n_docs_export.csv")
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return {}
    
    categories = Counter()
    category_examples = defaultdict(list)
    
    print("📊 Analyzing CSV categories...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['url']
            title = row['title']
            category = extract_category_from_url(url)
            
            categories[category] += 1
            if len(category_examples[category]) < 3:  # Keep first 3 examples
                category_examples[category].append({
                    'url': url,
                    'title': title,
                    'word_count': row['word_count']
                })
    
    print(f"\n📈 Found {len(categories)} categories:")
    for category, count in categories.most_common():
        print(f"   {category}: {count} documents")
        for example in category_examples[category][:2]:  # Show 2 examples
            print(f"     - {example['title'][:60]}...")
        print()
    
    return dict(categories), dict(category_examples)

def create_database_schema(categories):
    """Create database schema for categorized tables."""
    schema_sql = []
    
    # Base table for all documents
    schema_sql.append("""
-- Base workflow documents table (existing)
CREATE TABLE IF NOT EXISTS workflow_documents (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    headings JSONB,
    links JSONB,
    code_blocks JSONB,
    images JSONB,
    metadata JSONB,
    word_count INTEGER,
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for category-based queries
CREATE INDEX IF NOT EXISTS idx_workflow_documents_category ON workflow_documents(category);
CREATE INDEX IF NOT EXISTS idx_workflow_documents_subcategory ON workflow_documents(subcategory);
CREATE INDEX IF NOT EXISTS idx_workflow_documents_url ON workflow_documents(url);
""")
    
    # Create category-specific tables for better organization
    for category in sorted(categories.keys()):
        table_name = f"docs_{category}"
        schema_sql.append(f"""
-- {category.replace('_', ' ').title()} specific table
CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_{table_name}_document_id ON {table_name}(document_id);
CREATE INDEX IF NOT EXISTS idx_{table_name}_url ON {table_name}(url);
""")
    
    return "\n".join(schema_sql)

def create_import_script(categories):
    """Create a Python script to import categorized data."""
    
    script_content = f'''
#!/usr/bin/env python3
"""
Categorized data import script for n8n documentation.
Imports scraped JSON files into category-specific database tables.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import text
from src.n8n_scraper.database.connection import DatabaseManager
from src.n8n_scraper.core.logging_config import get_logger

logger = get_logger(__name__)

# Category mapping based on analysis
CATEGORIES = {categories}

def extract_category_from_url(url: str) -> str:
    """Extract category from URL using the same logic as analysis."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if not path_parts:
        return 'root'
    
    main_category = path_parts[0]
    
    # Handle special cases (same logic as analysis script)
    if main_category == 'integrations' and len(path_parts) > 1:
        if path_parts[1] in ['builtin', 'creating-nodes']:
            return f"integrations_{{path_parts[1]}}"
        return 'integrations'
    elif main_category == 'release-notes' and len(path_parts) > 1:
        if path_parts[1] == '0-x':
            return 'release_notes_legacy'
        return 'release_notes'
    elif main_category == 'hosting' and len(path_parts) > 1:
        if path_parts[1] in ['installation', 'configuration', 'architecture']:
            return f"hosting_{{path_parts[1]}}"
        return 'hosting'
    elif main_category == 'code' and len(path_parts) > 1:
        if path_parts[1] in ['cookbook', 'builtin']:
            return f"code_{{path_parts[1]}}"
        return 'code'
    
    return main_category.replace('-', '_')

def extract_subcategory_from_url(url: str) -> Optional[str]:
    """Extract subcategory from URL path."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if len(path_parts) >= 3:
        return path_parts[2].replace('-', '_')
    return None

async def load_json_files() -> List[Dict]:
    """Load all JSON files from scraped_docs directory."""
    scraped_docs_dir = Path("data/scraped_docs")
    
    if not scraped_docs_dir.exists():
        logger.error(f"Scraped docs directory not found: {{scraped_docs_dir}}")
        return []
    
    json_files = list(scraped_docs_dir.glob("*.json"))
    logger.info(f"Found {{len(json_files)}} JSON files to process")
    
    documents = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'url' in data:
                    documents.append(data)
                else:
                    logger.warning(f"Invalid JSON structure in {{json_file}}")
        except Exception as e:
            logger.error(f"Error reading {{json_file}}: {{e}}")
    
    logger.info(f"Successfully loaded {{len(documents)}} documents")
    return documents

async def insert_document(db_manager: DatabaseManager, doc: Dict) -> Optional[int]:
    """Insert a document into the main workflow_documents table."""
    try:
        category = extract_category_from_url(doc['url'])
        subcategory = extract_subcategory_from_url(doc['url'])
        
        async with db_manager.get_async_session() as session:
            # Check if document already exists
            result = await session.execute(
                text("SELECT id FROM workflow_documents WHERE url = :url"),
                {{"url": doc['url']}}
            )
            existing = result.fetchone()
            
            if existing:
                logger.debug(f"Document already exists: {{doc['url']}}")
                return existing[0]
            
            # Insert new document
            insert_query = text("""
                INSERT INTO workflow_documents (
                    url, title, content, content_length, category, subcategory,
                    headings, links, code_blocks, images, metadata, word_count, scraped_at
                ) VALUES (
                    :url, :title, :content, :content_length, :category, :subcategory,
                    :headings, :links, :code_blocks, :images, :metadata, :word_count, :scraped_at
                ) RETURNING id
            """)
            
            result = await session.execute(insert_query, {{
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
                "metadata": json.dumps(doc.get('metadata', {{}})),
                "word_count": doc.get('word_count', 0),
                "scraped_at": doc.get('scraped_at')
            }})
            
            document_id = result.fetchone()[0]
            await session.commit()
            
            logger.debug(f"Inserted document {{document_id}}: {{doc['title'][:50]}}...")
            return document_id
            
    except Exception as e:
        logger.error(f"Error inserting document {{doc['url']}}: {{e}}")
        return None

async def insert_category_document(db_manager: DatabaseManager, doc: Dict, document_id: int, category: str):
    """Insert document into category-specific table."""
    try:
        table_name = f"docs_{{category}}"
        
        async with db_manager.get_async_session() as session:
            # Check if already exists in category table
            result = await session.execute(
                text(f"SELECT id FROM {{table_name}} WHERE document_id = :document_id"),
                {{"document_id": document_id}}
            )
            existing = result.fetchone()
            
            if existing:
                logger.debug(f"Document already in {{table_name}}: {{document_id}}")
                return
            
            # Insert into category table
            insert_query = text(f"""
                INSERT INTO {{table_name}} (
                    document_id, url, title, content, word_count,
                    headings_count, links_count, code_blocks_count, images_count, metadata
                ) VALUES (
                    :document_id, :url, :title, :content, :word_count,
                    :headings_count, :links_count, :code_blocks_count, :images_count, :metadata
                )
            """)
            
            await session.execute(insert_query, {{
                "document_id": document_id,
                "url": doc['url'],
                "title": doc['title'],
                "content": doc['content'],
                "word_count": doc.get('word_count', 0),
                "headings_count": len(doc.get('headings', [])),
                "links_count": len(doc.get('links', [])),
                "code_blocks_count": len(doc.get('code_blocks', [])),
                "images_count": len(doc.get('images', [])),
                "metadata": json.dumps(doc.get('metadata', {{}}))
            }})
            
            await session.commit()
            logger.debug(f"Inserted into {{table_name}}: {{document_id}}")
            
    except Exception as e:
        logger.error(f"Error inserting into {{table_name}} for document {{document_id}}: {{e}}")

async def import_categorized_data():
    """Main function to import all data into categorized tables."""
    logger.info("🚀 Starting categorized data import...")
    
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
        categorized_docs = {{}}
        for doc in documents:
            category = extract_category_from_url(doc['url'])
            if category not in categorized_docs:
                categorized_docs[category] = []
            categorized_docs[category].append(doc)
        
        logger.info(f"📊 Documents by category:")
        for category, docs in categorized_docs.items():
            logger.info(f"   {{category}}: {{len(docs)}} documents")
        
        # Import documents
        total_imported = 0
        category_counts = {{}}
        
        for category, docs in categorized_docs.items():
            logger.info(f"\n📥 Importing {{category}} documents ({{len(docs)}} total)...")
            category_count = 0
            
            for i, doc in enumerate(docs, 1):
                # Insert into main table
                document_id = await insert_document(db_manager, doc)
                
                if document_id:
                    # Insert into category table
                    await insert_category_document(db_manager, doc, document_id, category)
                    category_count += 1
                    total_imported += 1
                
                if i % 100 == 0:
                    logger.info(f"   Processed {{i}}/{{len(docs)}} {{category}} documents")
            
            category_counts[category] = category_count
            logger.info(f"✅ Completed {{category}}: {{category_count}} documents imported")
        
        logger.info(f"\n🎉 Import completed!")
        logger.info(f"   Total documents imported: {{total_imported}}")
        logger.info(f"   Category breakdown:")
        for category, count in category_counts.items():
            logger.info(f"     {{category}}: {{count}}")
        
    except Exception as e:
        logger.error(f"Import failed: {{e}}")
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(import_categorized_data())
'''
    
    return script_content

if __name__ == "__main__":
    print("🔍 Analyzing n8n documentation categories...")
    
    # Analyze categories
    categories, examples = analyze_csv_categories()
    
    if not categories:
        print("❌ No categories found")
        exit(1)
    
    # Create database schema
    print("\n📝 Generating database schema...")
    schema = create_database_schema(categories)
    
    # Save schema
    schema_path = Path("migrations/categorized_schema.sql")
    schema_path.parent.mkdir(exist_ok=True)
    with open(schema_path, 'w') as f:
        f.write(schema)
    print(f"✅ Schema saved to: {schema_path}")
    
    # Create import script
    print("\n🐍 Generating import script...")
    import_script = create_import_script(categories)
    
    # Save import script
    import_path = Path("import_categorized_data.py")
    with open(import_path, 'w') as f:
        f.write(import_script)
    print(f"✅ Import script saved to: {import_path}")
    
    print(f"\n🎯 Summary:")
    print(f"   Categories found: {len(categories)}")
    print(f"   Total documents: {sum(categories.values())}")
    print(f"   Schema file: {schema_path}")
    print(f"   Import script: {import_path}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review the generated schema: {schema_path}")
    print(f"   2. Apply schema to database (if needed)")
    print(f"   3. Run import script: python {import_path}")