#!/usr/bin/env python3
"""
PostgreSQL Connection Test Script

This script tests the PostgreSQL connection using the configuration
from the project's settings.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
    import asyncpg
    import asyncio
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Install with: pip install psycopg2-binary asyncpg")
    sys.exit(1)

try:
    from config.settings import settings
except ImportError as e:
    print(f"❌ Could not import settings: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)


def test_sync_connection():
    """Test synchronous PostgreSQL connection using psycopg2."""
    print("\n🔍 Testing synchronous PostgreSQL connection...")
    
    try:
        # Create connection
        conn = psycopg2.connect(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password
        )
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Test database operations
        cursor.execute("""
            SELECT 
                current_database() as database,
                current_user as user,
                inet_server_addr() as server_ip,
                inet_server_port() as server_port,
                pg_postmaster_start_time() as start_time
        """)
        
        db_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print("✅ Synchronous connection successful!")
        print(f"   📊 Version: {version.split(',')[0]}")
        print(f"   🗄️  Database: {db_info[0]}")
        print(f"   👤 User: {db_info[1]}")
        print(f"   🌐 Server: {db_info[2] or 'localhost'}:{db_info[3]}")
        print(f"   ⏰ Started: {db_info[4]}")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Synchronous connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_async_connection():
    """Test asynchronous PostgreSQL connection using asyncpg."""
    print("\n🔍 Testing asynchronous PostgreSQL connection...")
    
    try:
        # Create async connection
        conn = await asyncpg.connect(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password
        )
        
        # Test query
        version = await conn.fetchval("SELECT version();")
        
        # Test database operations
        db_info = await conn.fetchrow("""
            SELECT 
                current_database() as database,
                current_user as user,
                inet_server_addr() as server_ip,
                inet_server_port() as server_port,
                pg_postmaster_start_time() as start_time
        """)
        
        await conn.close()
        
        print("✅ Asynchronous connection successful!")
        print(f"   📊 Version: {version.split(',')[0]}")
        print(f"   🗄️  Database: {db_info['database']}")
        print(f"   👤 User: {db_info['user']}")
        print(f"   🌐 Server: {db_info['server_ip'] or 'localhost'}:{db_info['server_port']}")
        print(f"   ⏰ Started: {db_info['start_time']}")
        
        return True
        
    except asyncpg.PostgresError as e:
        print(f"❌ Asynchronous connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_database_operations():
    """Test basic database operations."""
    print("\n🔍 Testing database operations...")
    
    try:
        conn = psycopg2.connect(
            host=settings.database_host,
            port=settings.database_port,
            database=settings.database_name,
            user=settings.database_user,
            password=settings.database_password
        )
        
        cursor = conn.cursor()
        
        # Test table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Test insert
        cursor.execute(
            "INSERT INTO test_table (name) VALUES (%s) RETURNING id",
            ("test_connection",)
        )
        test_id = cursor.fetchone()[0]
        
        # Test select
        cursor.execute(
            "SELECT id, name, created_at FROM test_table WHERE id = %s",
            (test_id,)
        )
        result = cursor.fetchone()
        
        # Test delete
        cursor.execute("DELETE FROM test_table WHERE id = %s", (test_id,))
        
        # Drop test table
        cursor.execute("DROP TABLE test_table")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Database operations successful!")
        print(f"   📝 Created record with ID: {result[0]}")
        print(f"   📛 Name: {result[1]}")
        print(f"   📅 Created at: {result[2]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database operations failed: {e}")
        return False


def print_configuration():
    """Print current PostgreSQL configuration."""
    print("\n📋 Current PostgreSQL Configuration:")
    print(f"   🌐 Host: {settings.database_host}")
    print(f"   🔌 Port: {settings.database_port}")
    print(f"   🗄️  Database: {settings.database_name}")
    print(f"   👤 User: {settings.database_user}")
    print(f"   🔒 Password: {'*' * len(settings.database_password)}")
    print(f"   🔗 URL: {settings.database_url.replace(settings.database_password, '*' * len(settings.database_password))}")
    print(f"   ⚡ Async URL: {settings.database_url_async.replace(settings.database_password, '*' * len(settings.database_password))}")
    print(f"   🏊 Pool Size: {settings.database_pool_size}")
    print(f"   📈 Max Overflow: {settings.database_max_overflow}")
    print(f"   ⏱️  Pool Timeout: {settings.database_pool_timeout}s")


def main():
    """Main test function."""
    print("🐘 PostgreSQL Connection Test")
    print("=" * 50)
    
    # Print configuration
    print_configuration()
    
    # Test connections
    sync_success = test_sync_connection()
    async_success = asyncio.run(test_async_connection())
    ops_success = test_database_operations()
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"   Synchronous Connection: {'✅ PASS' if sync_success else '❌ FAIL'}")
    print(f"   Asynchronous Connection: {'✅ PASS' if async_success else '❌ FAIL'}")
    print(f"   Database Operations: {'✅ PASS' if ops_success else '❌ FAIL'}")
    
    if all([sync_success, async_success, ops_success]):
        print("\n🎉 All tests passed! PostgreSQL is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check your PostgreSQL configuration.")
        print("\n💡 Troubleshooting tips:")
        print("   1. Ensure PostgreSQL is running")
        print("   2. Check connection parameters in .env file")
        print("   3. Verify database and user exist")
        print("   4. Check firewall and network settings")
        print("   5. Review PostgreSQL logs for errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())