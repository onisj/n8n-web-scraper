#!/usr/bin/env python3
"""
Test inserting a single record into a category table.
"""

import asyncio
import json
from sqlalchemy import text
from src.n8n_scraper.database.connection import DatabaseManager
from src.n8n_scraper.core.logging_config import get_logger

logger = get_logger(__name__)

async def test_insert():
    """Test inserting a single record."""
    logger.info("🧪 Testing category table insert...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.get_async_session() as session:
            # Get one document from documentation_pages
            result = await session.execute(
                text("""
                    SELECT id, url, title, content, category, word_count, 
                           headings, links, code_blocks, images, metadata
                    FROM documentation_pages 
                    WHERE category = 'integrations_builtin'
                    LIMIT 1
                """)
            )
            
            doc = result.fetchone()
            if not doc:
                logger.error("No document found")
                return
                
            doc_id, url, title, content, category, word_count, headings, links, code_blocks, images, metadata = doc
            
            logger.info(f"Found document: {doc_id} - {title[:50]}...")
            logger.info(f"Metadata type: {type(metadata)}")
            logger.info(f"Metadata value: {metadata}")
            
            # Parse JSON fields to get counts
            try:
                headings_list = json.loads(headings) if headings else []
                links_list = json.loads(links) if links else []
                code_blocks_list = json.loads(code_blocks) if code_blocks else []
                images_list = json.loads(images) if images else []
            except Exception as e:
                logger.error(f"Error parsing JSON fields: {e}")
                headings_list = []
                links_list = []
                code_blocks_list = []
                images_list = []
            
            # Handle metadata
            if isinstance(metadata, dict):
                metadata_str = json.dumps(metadata)
            elif isinstance(metadata, str):
                metadata_str = metadata
            else:
                metadata_str = '{}'
            
            logger.info(f"Processed metadata: {metadata_str[:100]}...")
            
            # Check if already exists
            check_result = await session.execute(
                text("SELECT id FROM docs_integrations WHERE document_id = :document_id"),
                {"document_id": doc_id}
            )
            existing = check_result.fetchone()
            
            if existing:
                logger.info(f"Document {doc_id} already exists in docs_integrations")
                return
            
            # Insert into docs_integrations
            insert_query = text("""
                INSERT INTO docs_integrations (
                    document_id, url, title, content, word_count,
                    headings_count, links_count, code_blocks_count, images_count, metadata
                ) VALUES (
                    :document_id, :url, :title, :content, :word_count,
                    :headings_count, :links_count, :code_blocks_count, :images_count, :metadata
                )
            """)
            
            params = {
                "document_id": doc_id,
                "url": url,
                "title": title,
                "content": content,
                "word_count": word_count or 0,
                "headings_count": len(headings_list),
                "links_count": len(links_list),
                "code_blocks_count": len(code_blocks_list),
                "images_count": len(images_list),
                "metadata": metadata_str
            }
            
            logger.info(f"Parameters: {list(params.keys())}")
            logger.info(f"Parameter count: {len(params)}")
            
            await session.execute(insert_query, params)
            await session.commit()
            
            logger.info("✅ Successfully inserted test record!")
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_insert())