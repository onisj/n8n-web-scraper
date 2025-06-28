#!/usr/bin/env python3
"""
Quick database status check to see current tables and data.
"""

import asyncio
from sqlalchemy import text
from src.n8n_scraper.database.connection import DatabaseManager

async def check_database():
    """Check current database status."""
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.get_async_session() as session:
            # Get all tables
            result = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]
            
            print(f"📊 Current database tables ({len(tables)}):")
            for table in sorted(tables):
                print(f"   - {table}")
            
            # Check main tables for data
            if 'workflow_documents' in tables:
                result = await session.execute(text("SELECT COUNT(*) FROM workflow_documents"))
                count = result.fetchone()[0]
                print(f"\n📄 workflow_documents: {count} records")
                
                if count > 0:
                    # Show categories
                    result = await session.execute(
                        text("SELECT category, COUNT(*) FROM workflow_documents GROUP BY category ORDER BY COUNT(*) DESC")
                    )
                    categories = result.fetchall()
                    print(f"   Categories:")
                    for cat, cnt in categories:
                        print(f"     {cat}: {cnt}")
            
            if 'workflow_chunks' in tables:
                result = await session.execute(text("SELECT COUNT(*) FROM workflow_chunks"))
                count = result.fetchone()[0]
                print(f"\n🧩 workflow_chunks: {count} records")
            
            # Check if category tables exist
            category_tables = [t for t in tables if t.startswith('docs_')]
            if category_tables:
                print(f"\n📂 Category tables ({len(category_tables)}):")
                for table in sorted(category_tables):
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"   {table}: {count} records")
            else:
                print(f"\n❌ No category tables found (docs_* pattern)")
                
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_database())