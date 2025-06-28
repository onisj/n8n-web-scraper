"""
Database migration utilities for n8n scraper.

This module provides utilities for managing database migrations using Alembic.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from .connection import db_manager
from .models import Base
from ..core.exceptions import DatabaseError, DatabaseMigrationError
from ..core.logging_config import get_logger
from ..core.metrics import metrics

logger = get_logger(__name__)


class MigrationManager:
    """Manages database migrations using Alembic."""
    
    def __init__(self):
        self.alembic_cfg_path = settings.base_dir / "alembic.ini"
        self.migrations_dir = settings.base_dir / "migrations"
        self.alembic_cfg: Optional[Config] = None
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(exist_ok=True)
    
    def _get_alembic_config(self) -> Config:
        """Get Alembic configuration."""
        if self.alembic_cfg is None:
            if self.alembic_cfg_path.exists():
                self.alembic_cfg = Config(str(self.alembic_cfg_path))
            else:
                # Create a basic alembic config
                self.alembic_cfg = Config()
                self.alembic_cfg.set_main_option("script_location", str(self.migrations_dir))
                self.alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        # Always update the database URL in case it changed
        self.alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        return self.alembic_cfg
    
    async def initialize_alembic(self) -> None:
        """Initialize Alembic for the project."""
        try:
            # Check if migrations directory has the necessary files
            env_py_exists = (self.migrations_dir / "env.py").exists()
            script_mako_exists = (self.migrations_dir / "script.py.mako").exists()
            versions_dir_exists = (self.migrations_dir / "versions").exists()
            
            if not self.migrations_dir.exists() or not (env_py_exists and script_mako_exists and versions_dir_exists):
                logger.info("Initializing Alembic...")
                
                # Create alembic configuration
                alembic_cfg = self._get_alembic_config()
                
                # Initialize alembic only if directory doesn't exist or is missing key files
                if not self.migrations_dir.exists():
                    command.init(alembic_cfg, str(self.migrations_dir))
                else:
                    # Directory exists but missing files, create them manually
                    if not versions_dir_exists:
                        (self.migrations_dir / "versions").mkdir(exist_ok=True)
                
                logger.info("Alembic initialized successfully")
            else:
                logger.info("Alembic already initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Alembic: {e}")
            raise DatabaseMigrationError(f"Failed to initialize Alembic: {str(e)}") from e
    
    async def create_migration(
        self,
        message: str,
        auto_generate: bool = True
    ) -> str:
        """Create a new migration.
        
        Args:
            message: Migration message/description
            auto_generate: Whether to auto-generate migration from model changes
        
        Returns:
            Migration revision ID
        """
        try:
            await self.initialize_alembic()
            
            alembic_cfg = self._get_alembic_config()
            
            if auto_generate:
                # Auto-generate migration from model changes
                revision = command.revision(
                    alembic_cfg,
                    message=message,
                    autogenerate=True
                )
            else:
                # Create empty migration
                revision = command.revision(
                    alembic_cfg,
                    message=message
                )
            
            logger.info(f"Created migration: {revision} - {message}")
            metrics.increment_counter("database_migrations_created")
            
            return revision
            
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            metrics.increment_counter("database_migration_errors")
            raise DatabaseMigrationError(f"Failed to create migration: {str(e)}") from e
    
    async def run_migrations(self, target_revision: str = "head") -> None:
        """Run database migrations.
        
        Args:
            target_revision: Target revision to migrate to (default: "head")
        """
        try:
            await self.initialize_alembic()
            
            # Ensure database manager is initialized
            if not db_manager.is_initialized:
                await db_manager.initialize()
            
            alembic_cfg = self._get_alembic_config()
            
            # Run migrations
            command.upgrade(alembic_cfg, target_revision)
            
            logger.info(f"Migrations completed successfully to revision: {target_revision}")
            metrics.increment_counter("database_migrations_applied")
            
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            metrics.increment_counter("database_migration_errors")
            raise DatabaseMigrationError(f"Failed to run migrations: {str(e)}") from e
    
    async def rollback_migration(self, target_revision: str) -> None:
        """Rollback to a specific migration.
        
        Args:
            target_revision: Target revision to rollback to
        """
        try:
            await self.initialize_alembic()
            
            alembic_cfg = self._get_alembic_config()
            
            # Rollback to target revision
            command.downgrade(alembic_cfg, target_revision)
            
            logger.info(f"Rollback completed to revision: {target_revision}")
            metrics.increment_counter("database_migrations_rolled_back")
            
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            metrics.increment_counter("database_migration_errors")
            raise DatabaseMigrationError(f"Failed to rollback migration: {str(e)}") from e
    
    async def get_current_revision(self) -> Optional[str]:
        """Get the current database revision.
        
        Returns:
            Current revision ID or None if no migrations have been applied
        """
        try:
            if not db_manager.is_initialized:
                await db_manager.initialize()
            
            engine = db_manager.sync_engine
            if not engine:
                raise DatabaseError("Database engine not available")
            
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                return current_rev
            
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    async def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history.
        
        Returns:
            List of migration information
        """
        try:
            await self.initialize_alembic()
            
            alembic_cfg = self._get_alembic_config()
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            
            history = []
            for revision in script_dir.walk_revisions():
                history.append({
                    "revision": revision.revision,
                    "down_revision": revision.down_revision,
                    "branch_labels": revision.branch_labels,
                    "depends_on": revision.depends_on,
                    "doc": revision.doc,
                    "create_date": revision.create_date.isoformat() if revision.create_date else None,
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    async def check_migration_status(self) -> Dict[str, Any]:
        """Check the current migration status.
        
        Returns:
            Migration status information
        """
        try:
            current_revision = await self.get_current_revision()
            history = await self.get_migration_history()
            
            # Find the latest available revision
            latest_revision = None
            if history:
                latest_revision = history[0]["revision"]
            
            is_up_to_date = current_revision == latest_revision
            
            status = {
                "current_revision": current_revision,
                "latest_revision": latest_revision,
                "is_up_to_date": is_up_to_date,
                "total_migrations": len(history),
                "pending_migrations": [],
            }
            
            # Find pending migrations
            if not is_up_to_date and history:
                current_found = False
                for migration in history:
                    if migration["revision"] == current_revision:
                        current_found = True
                        continue
                    
                    if not current_found:
                        status["pending_migrations"].append(migration)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check migration status: {e}")
            return {
                "error": str(e),
                "current_revision": None,
                "latest_revision": None,
                "is_up_to_date": False,
                "total_migrations": 0,
                "pending_migrations": [],
            }


class DatabaseInitializer:
    """Handles database initialization and schema creation."""
    
    def __init__(self):
        self.migration_manager = MigrationManager()
    
    async def create_database_if_not_exists(self) -> None:
        """Create the database if it doesn't exist."""
        try:
            # This would typically be handled by the database administrator
            # or deployment scripts, but we can add basic logic here
            logger.info("Checking database existence...")
            
            # For PostgreSQL, we might need to create the database
            # This is a simplified implementation
            if not db_manager.is_initialized:
                await db_manager.initialize()
            
            # Test connection
            async with db_manager.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info("Database is accessible")
            
        except Exception as e:
            logger.error(f"Database accessibility check failed: {e}")
            raise DatabaseError(f"Database not accessible: {str(e)}") from e
    
    async def create_tables(self) -> None:
        """Create all tables defined in models."""
        try:
            if not db_manager.is_initialized:
                await db_manager.initialize()
            
            engine = db_manager.sync_engine
            if not engine:
                raise DatabaseError("Database engine not available")
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            
            logger.info("Database tables created successfully")
            metrics.increment_counter("database_tables_created")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            metrics.increment_counter("database_table_creation_errors")
            raise DatabaseError(f"Failed to create tables: {str(e)}") from e
    
    async def drop_tables(self) -> None:
        """Drop all tables (use with caution!)."""
        try:
            if not db_manager.is_initialized:
                await db_manager.initialize()
            
            engine = db_manager.sync_engine
            if not engine:
                raise DatabaseError("Database engine not available")
            
            # Drop all tables
            Base.metadata.drop_all(bind=engine)
            
            logger.warning("All database tables dropped")
            metrics.increment_counter("database_tables_dropped")
            
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise DatabaseError(f"Failed to drop tables: {str(e)}") from e
    
    async def initialize_database(self, force_recreate: bool = False) -> None:
        """Initialize the database with tables and initial data.
        
        Args:
            force_recreate: Whether to drop and recreate all tables
        """
        try:
            logger.info("Initializing database...")
            
            # Check database accessibility
            await self.create_database_if_not_exists()
            
            if force_recreate:
                logger.warning("Force recreating database tables")
                await self.drop_tables()
            
            # Create tables
            await self.create_tables()
            
            # Run any pending migrations
            await self.migration_manager.run_migrations()
            
            logger.info("Database initialization completed")
            metrics.increment_counter("database_initialized")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            metrics.increment_counter("database_initialization_errors")
            raise DatabaseError(f"Database initialization failed: {str(e)}") from e
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics.
        
        Returns:
            Database information dictionary
        """
        try:
            if not db_manager.is_initialized:
                await db_manager.initialize()
            
            engine = db_manager.sync_engine
            if not engine:
                raise DatabaseError("Database engine not available")
            
            info = {
                "database_url": settings.database_url.replace(settings.db_password, "***") if settings.db_password else settings.database_url,
                "engine_info": str(engine.url),
                "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
                "tables": [],
                "migration_status": await self.migration_manager.check_migration_status(),
            }
            
            # Get table information
            with engine.connect() as connection:
                inspector = inspect(connection)
                table_names = inspector.get_table_names()
                
                for table_name in table_names:
                    columns = inspector.get_columns(table_name)
                    indexes = inspector.get_indexes(table_name)
                    
                    info["tables"].append({
                        "name": table_name,
                        "columns": len(columns),
                        "indexes": len(indexes),
                    })
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}


# Global instances
migration_manager = MigrationManager()
database_initializer = DatabaseInitializer()


# Convenience functions
async def run_migrations(target_revision: str = "head") -> None:
    """Run database migrations."""
    await migration_manager.run_migrations(target_revision)


async def create_migration(message: str, auto_generate: bool = True) -> str:
    """Create a new migration."""
    return await migration_manager.create_migration(message, auto_generate)


async def rollback_migration(target_revision: str) -> None:
    """Rollback to a specific migration."""
    await migration_manager.rollback_migration(target_revision)


async def get_migration_status() -> Dict[str, Any]:
    """Get current migration status."""
    return await migration_manager.check_migration_status()


async def initialize_database(force_recreate: bool = False) -> None:
    """Initialize the database."""
    await database_initializer.initialize_database(force_recreate)


async def get_database_info() -> Dict[str, Any]:
    """Get database information."""
    return await database_initializer.get_database_info()