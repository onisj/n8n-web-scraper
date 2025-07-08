#!/usr/bin/env python3
"""
Database Structure Migration Script

Migrates existing database files from old locations to the new centralized structure.
This script helps users transition to the new consolidated database directory layout.
"""

import os
import shutil
import sys
from pathlib import Path

def create_directory_structure():
    """Create the new centralized database directory structure."""
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases")
    
    directories = [
        base_dir / "sqlite",
        base_dir / "vector", 
        base_dir / "postgresql"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def migrate_sqlite_files():
    """Migrate SQLite workflow database files."""
    old_files = [
        "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/workflows.db",
        "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/workflows.db-shm",
        "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/workflows.db-wal"
    ]
    
    new_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/sqlite")
    
    for old_file in old_files:
        old_path = Path(old_file)
        if old_path.exists():
            new_path = new_dir / old_path.name
            shutil.move(str(old_path), str(new_path))
            print(f"✓ Moved {old_path} → {new_path}")
        else:
            print(f"ℹ File not found: {old_path}")

def migrate_vector_files():
    """Migrate ChromaDB vector database files."""
    old_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/chroma_db")
    new_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector")
    
    if old_dir.exists():
        # Move all files from old directory to new directory
        for item in old_dir.iterdir():
            if item.is_file():
                new_path = new_dir / item.name
                shutil.move(str(item), str(new_path))
                print(f"✓ Moved {item} → {new_path}")
            elif item.is_dir():
                new_subdir = new_dir / item.name
                shutil.move(str(item), str(new_subdir))
                print(f"✓ Moved directory {item} → {new_subdir}")
        
        # Remove empty old directory
        if not any(old_dir.iterdir()):
            old_dir.rmdir()
            print(f"✓ Removed empty directory: {old_dir}")
    else:
        print(f"ℹ Directory not found: {old_dir}")

def verify_migration():
    """Verify that the migration was successful."""
    print("\n=== Migration Verification ===")
    
    # Check new structure
    base_dir = Path("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases")
    if base_dir.exists():
        print(f"✓ Base directory exists: {base_dir}")
        
        for subdir in ["sqlite", "vector", "postgresql"]:
            subdir_path = base_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.iterdir())
                print(f"✓ {subdir}/ directory: {len(files)} files")
                for file in files:
                    print(f"  - {file.name}")
            else:
                print(f"⚠ Missing directory: {subdir_path}")
    else:
        print(f"❌ Base directory missing: {base_dir}")
    
    # Check for old files
    old_locations = [
        "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/workflows.db",
        "/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/chroma_db"
    ]
    
    print("\n=== Old Location Check ===")
    for old_location in old_locations:
        old_path = Path(old_location)
        if old_path.exists():
            print(f"⚠ Old file/directory still exists: {old_path}")
        else:
            print(f"✓ Old location cleaned up: {old_path}")

def main():
    """Main migration function."""
    print("Database Structure Migration Tool")
    print("=" * 40)
    print("This script will migrate your database files to the new centralized structure.")
    print("\nNew structure:")
    print("/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/")
    print("├── sqlite/     (SQLite workflow databases)")
    print("├── vector/     (ChromaDB vector databases)")
    print("└── postgresql/ (PostgreSQL connection configs)")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed with the migration? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Migration cancelled.")
        sys.exit(0)
    
    try:
        print("\n=== Creating Directory Structure ===")
        create_directory_structure()
        
        print("\n=== Migrating SQLite Files ===")
        migrate_sqlite_files()
        
        print("\n=== Migrating Vector Database Files ===")
        migrate_vector_files()
        
        verify_migration()
        
        print("\n=== Migration Complete ===")
        print("✓ Database migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your .env file with the new paths (if needed)")
        print("2. Restart your application to use the new database locations")
        print("3. Verify that all functionality works as expected")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check the error and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()