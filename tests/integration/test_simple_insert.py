#!/usr/bin/env python3
"""
Simple test to insert one document into documentation_pages table.
"""

import asyncio
import json
from datetime import datetime
from sqlalchemy import text
from src.n8n_scraper.database.connection import DatabaseManager
from src.n8n_scraper.core.logging_config import get_logger

logger = get_logger(__name__)

async def test_simple_insert():
    """Test inserting a simple document."""
    db_manager = DatabaseManager()
    
    try:
        await db_manager.initialize()
        
        # Simple test data
        test_data = {
            'url': 'https://test.example.com',
            'title': 'Test Document',
            'content': 'This is a test document content.',
            'content_length': 33,
            'category': 'test',
            'subcategory': None,
            'headings': json.dumps([]),
            'links': json.dumps([]),
            'code_blocks': json.dumps([]),
            'images': json.dumps([]),
            'metadata': json.dumps({}),
            'word_count': 6,
            'scraped_at': datetime.now()
        }
        
        async with db_manager.get_async_session() as session:
            # First check if table exists
            result = await session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'documentation_pages'")
            )
            table_exists = result.fetchone()[0] > 0
            print(f"documentation_pages table exists: {table_exists}")
            
            if not table_exists:
                print("❌ Table doesn't exist")
                return
            
            # Try to insert
            insert_query = text("""
                INSERT INTO documentation_pages (
                    url, title, content, content_length, category, subcategory,
                    headings, links, code_blocks, images, metadata, word_count, scraped_at
                ) VALUES (
                    :url, :title, :content, :content_length, :category, :subcategory,
                    :headings, :links, :code_blocks, :images, :metadata, :word_count, :scraped_at
                ) RETURNING id
            """)
            
            print("Attempting to insert test document...")
            result = await session.execute(insert_query, test_data)
            doc_id = result.fetchone()[0]
            await session.commit()
            
            print(f"✅ Successfully inserted document with ID: {doc_id}")
            
            # Verify the insert
            verify_query = text("SELECT COUNT(*) FROM documentation_pages")
            result = await session.execute(verify_query)
            count = result.fetchone()[0]
            print(f"Total documents in table: {count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_simple_insert())