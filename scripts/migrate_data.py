#!/usr/bin/env python3
"""CLI script for migrating scraped data and workflows to PostgreSQL.

This script provides a command-line interface to import:
1. Scraped n8n documentation from JSON files
2. n8n workflow files from JSON format
3. Run database migrations if needed

Usage:
    python scripts/migrate_data.py --scraped-docs data/scraped_docs --workflows data/workflows/files
    python scripts/migrate_data.py --workflows-only data/workflows/files
    python scripts/migrate_data.py --docs-only data/scraped_docs
    python scripts/migrate_data.py --run-migrations
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.n8n_scraper.core.logging_config import get_logger
from src.n8n_scraper.database.data_importer import run_data_import
from src.n8n_scraper.database.migrations import MigrationManager
from src.n8n_scraper.database.connection import get_sync_session

logger = get_logger(__name__)


async def check_database_connection():
    """Check if database connection is working."""
    logger.info("Checking database connection...")
    try:
        from src.n8n_scraper.database.connection import db_manager
        from sqlalchemy import text
        await db_manager.initialize()
        session = get_sync_session()
        session.execute(text("SELECT 1"))
        session.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False


async def run_migrations():
    """Run database migrations."""
    logger.info("Running database migrations...")
    try:
        migration_manager = MigrationManager()
        
        # Check current migration status
        current_revision = await migration_manager.get_current_revision()
        logger.info(f"Current migration revision: {current_revision}")
        
        # Run migrations
        await migration_manager.run_migrations()
        
        logger.info("✅ Migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def validate_directories(scraped_docs_dir, workflows_dir):
    """Validate that directories exist and contain files."""
    issues = []
    
    if scraped_docs_dir:
        if not os.path.exists(scraped_docs_dir):
            issues.append(f"Scraped docs directory does not exist: {scraped_docs_dir}")
        else:
            json_files = list(Path(scraped_docs_dir).glob("**/*.json"))
            if not json_files:
                issues.append(f"No JSON files found in scraped docs directory: {scraped_docs_dir}")
            else:
                logger.info(f"Found {len(json_files)} JSON files in scraped docs directory")
    
    if workflows_dir:
        if not os.path.exists(workflows_dir):
            issues.append(f"Workflows directory does not exist: {workflows_dir}")
        else:
            json_files = list(Path(workflows_dir).glob("**/*.json"))
            if not json_files:
                issues.append(f"No JSON files found in workflows directory: {workflows_dir}")
            else:
                logger.info(f"Found {len(json_files)} JSON files in workflows directory")
    
    return issues


def print_import_summary(results):
    """Print a summary of the import results."""
    print("\n" + "="*60)
    print("📊 DATA IMPORT SUMMARY")
    print("="*60)
    
    # Overall status
    if results.get("success"):
        print("✅ Import Status: SUCCESS")
    else:
        print("❌ Import Status: FAILED")
        if "error" in results:
            print(f"   Error: {results['error']}")
    
    print(f"⏱️  Total Time: {results.get('total_time', 0):.2f} seconds")
    
    # Scraped documents summary
    scraped_stats = results.get("scraped_docs", {})
    if scraped_stats and "error" not in scraped_stats:
        print("\n📄 SCRAPED DOCUMENTS:")
        print(f"   Total Files: {scraped_stats.get('total_files', 0)}")
        print(f"   Processed: {scraped_stats.get('processed_files', 0)}")
        print(f"   Skipped: {scraped_stats.get('skipped_files', 0)}")
        print(f"   Errors: {scraped_stats.get('error_files', 0)}")
        print(f"   Documents Created: {scraped_stats.get('total_documents', 0)}")
        print(f"   Chunks Created: {scraped_stats.get('total_chunks', 0)}")
        
        if scraped_stats.get('errors'):
            print("   ⚠️  Errors:")
            for error in scraped_stats['errors'][:5]:  # Show first 5 errors
                print(f"      {error['file']}: {error['error']}")
            if len(scraped_stats['errors']) > 5:
                print(f"      ... and {len(scraped_stats['errors']) - 5} more")
    elif "error" in scraped_stats:
        print(f"\n📄 SCRAPED DOCUMENTS: ❌ {scraped_stats['error']}")
    
    # Workflows summary
    workflow_stats = results.get("workflows", {})
    if workflow_stats and "error" not in workflow_stats:
        print("\n🔄 WORKFLOWS:")
        print(f"   Total Files: {workflow_stats.get('total_files', 0)}")
        print(f"   Processed: {workflow_stats.get('processed_files', 0)}")
        print(f"   Skipped: {workflow_stats.get('skipped_files', 0)}")
        print(f"   Errors: {workflow_stats.get('error_files', 0)}")
        print(f"   Workflows Created: {workflow_stats.get('total_workflows', 0)}")
        print(f"   Chunks Created: {workflow_stats.get('total_chunks', 0)}")
        
        if workflow_stats.get('errors'):
            print("   ⚠️  Errors:")
            for error in workflow_stats['errors'][:5]:  # Show first 5 errors
                print(f"      {error['file']}: {error['error']}")
            if len(workflow_stats['errors']) > 5:
                print(f"      ... and {len(workflow_stats['errors']) - 5} more")
    elif "error" in workflow_stats:
        print(f"\n🔄 WORKFLOWS: ❌ {workflow_stats['error']}")
    
    print("\n" + "="*60)


async def main():
    """Main function to run migrations and data import."""
    parser = argparse.ArgumentParser(description="N8N Data Migration Tool")
    parser.add_argument(
        "--run-migrations",
        action="store_true",
        help="Run database migrations before importing data"
    )
    parser.add_argument(
        "--import-data",
        action="store_true",
        help="Import scraped data to database"
    )
    parser.add_argument(
        "--scraped-docs-dir",
        default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs",
        help="Directory containing scraped documents"
    )
    parser.add_argument(
        "--workflows-dir",
        default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/workflows",
        help="Directory containing workflow files"
    )
    
    args = parser.parse_args()
    
    print("🚀 N8N Data Migration Tool")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check database connection first
    if not await check_database_connection():
        print("❌ Cannot proceed without database connection")
        return 1
    
    success = True
    
    if args.run_migrations:
        logger.info("Running database migrations...")
        success = await run_migrations()
        if not success:
            print("❌ Migration failed")
            return 1
        print("✅ Migrations completed successfully")
    
    if args.import_data:
        if not validate_directories(args.scraped_docs_dir, args.workflows_dir):
            return 1
        
        logger.info("Starting data import...")
        success = import_data(args.scraped_docs_dir, args.workflows_dir)
        if not success:
            print("❌ Data import failed")
            return 1
        print("✅ Data import completed successfully")
    
    if not args.run_migrations and not args.import_data:
        print("ℹ️  No action specified. Use --run-migrations or --import-data")
        print_import_summary(args.scraped_docs_dir, args.workflows_dir)
    
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0 if success else 1


if __name__ == "__main__":
    asyncio.run(main())