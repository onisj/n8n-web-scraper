#!/usr/bin/env python3
import asyncio
from src.n8n_scraper.database.connection import db_manager
from sqlalchemy import inspect, text

async def check_database_status():
    try:
        # Initialize database connection
        await db_manager.initialize()
        
        print("=== Database Status Check ===")
        print(f"Database initialized: {db_manager.is_initialized}")
        
        if db_manager.sync_engine:
            print(f"Database URL: {str(db_manager.sync_engine.url).replace(db_manager.sync_engine.url.password or '', '***')}")
            
            # Check connection
            with db_manager.sync_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("Connection test: ✅ SUCCESS")
                
                # Get table information
                inspector = inspect(conn)
                tables = inspector.get_table_names()
                
                print(f"\n=== Tables ({len(tables)}) ===")
                for table in sorted(tables):
                    columns = inspector.get_columns(table)
                    indexes = inspector.get_indexes(table)
                    print(f"  📋 {table}:")
                    print(f"     - Columns: {len(columns)}")
                    print(f"     - Indexes: {len(indexes)}")
                    
                    # Show column details for workflow tables
                    if 'workflow' in table:
                        print(f"     - Column details:")
                        for col in columns[:5]:  # Show first 5 columns
                            print(f"       • {col['name']} ({col['type']})")
                        if len(columns) > 5:
                            print(f"       • ... and {len(columns) - 5} more columns")
                
                # Check migration status
                if 'alembic_version' in tables:
                    result = conn.execute(text("SELECT version_num FROM alembic_version"))
                    version = result.fetchone()
                    if version:
                        print(f"\n=== Migration Status ===")
                        print(f"Current migration version: {version[0]}")
                    else:
                        print(f"\n=== Migration Status ===")
                        print("No migrations applied yet")
                        
        else:
            print("❌ Database engine not available")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    asyncio.run(check_database_status())