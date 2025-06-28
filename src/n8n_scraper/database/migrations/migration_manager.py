"""Database Migration Manager

Manages database migrations for the n8n AI Knowledge System
"""

import os
import logging
import importlib.util
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from ..vector_db import VectorDatabase

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, db: VectorDatabase, migrations_dir: Optional[str] = None):
        """
        Initialize migration manager
        
        Args:
            db: Vector database instance
            migrations_dir: Directory containing migration files
        """
        self.db = db
        self.migrations_dir = migrations_dir or os.path.dirname(__file__)
        
    def discover_migrations(self) -> List[Dict[str, Any]]:
        """
        Discover all migration files
        
        Returns:
            List of migration information
        """
        migrations = []
        migrations_path = Path(self.migrations_dir)
        
        # Find all Python files that match migration pattern
        for file_path in migrations_path.glob("[0-9][0-9][0-9]_*.py"):
            if file_path.name == "migration_manager.py":
                continue
                
            try:
                # Load migration module
                spec = importlib.util.spec_from_file_location(
                    file_path.stem, file_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get migration info
                if hasattr(module, 'get_migration_info'):
                    migration_info = module.get_migration_info()
                    migration_info['file_path'] = str(file_path)
                    migration_info['module'] = module
                    migrations.append(migration_info)
                else:
                    logger.warning(f"Migration {file_path.name} missing get_migration_info function")
                    
            except Exception as e:
                logger.error(f"Error loading migration {file_path.name}: {e}")
        
        # Sort by migration ID
        migrations.sort(key=lambda x: x['id'])
        return migrations
    
    def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migrations
        
        Returns:
            List of applied migration IDs
        """
        try:
            # Search for migration records
            results = self.db.search(
                query="migration",
                where={"type": "migration"},
                n_results=100
            )
            
            applied = []
            if 'results' in results:
                for result in results['results']:
                    if 'metadata' in result and 'migration_id' in result['metadata']:
                        applied.append(result['metadata']['migration_id'])
            
            return sorted(applied)
            
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """
        Get list of pending migrations
        
        Returns:
            List of pending migration information
        """
        all_migrations = self.discover_migrations()
        applied_migrations = self.get_applied_migrations()
        
        pending = []
        for migration in all_migrations:
            if migration['id'] not in applied_migrations:
                pending.append(migration)
        
        return pending
    
    def apply_migration(self, migration: Dict[str, Any]) -> bool:
        """
        Apply a single migration
        
        Args:
            migration: Migration information
            
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Applying migration {migration['id']}: {migration['name']}")
            
            # Check if migration has upgrade function
            module = migration['module']
            if not hasattr(module, 'upgrade'):
                logger.error(f"Migration {migration['id']} missing upgrade function")
                return False
            
            # Apply migration
            success = module.upgrade(self.db)
            
            if success:
                logger.info(f"Migration {migration['id']} applied successfully")
            else:
                logger.error(f"Migration {migration['id']} failed to apply")
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying migration {migration['id']}: {e}")
            return False
    
    def rollback_migration(self, migration: Dict[str, Any]) -> bool:
        """
        Rollback a single migration
        
        Args:
            migration: Migration information
            
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Rolling back migration {migration['id']}: {migration['name']}")
            
            # Check if migration has downgrade function
            module = migration['module']
            if not hasattr(module, 'downgrade'):
                logger.error(f"Migration {migration['id']} missing downgrade function")
                return False
            
            # Check if migration is reversible
            if not migration.get('reversible', True):
                logger.error(f"Migration {migration['id']} is not reversible")
                return False
            
            # Rollback migration
            success = module.downgrade(self.db)
            
            if success:
                logger.info(f"Migration {migration['id']} rolled back successfully")
            else:
                logger.error(f"Migration {migration['id']} failed to rollback")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rolling back migration {migration['id']}: {e}")
            return False
    
    def migrate(self, target_migration: Optional[str] = None) -> bool:
        """
        Apply all pending migrations or migrate to specific version
        
        Args:
            target_migration: Target migration ID (optional)
            
        Returns:
            bool: Success status
        """
        try:
            pending_migrations = self.get_pending_migrations()
            
            if not pending_migrations:
                logger.info("No pending migrations")
                return True
            
            # Filter migrations if target specified
            if target_migration:
                pending_migrations = [
                    m for m in pending_migrations 
                    if m['id'] <= target_migration
                ]
            
            logger.info(f"Applying {len(pending_migrations)} migrations")
            
            # Apply migrations in order
            for migration in pending_migrations:
                success = self.apply_migration(migration)
                if not success:
                    logger.error(f"Migration failed at {migration['id']}")
                    return False
            
            logger.info("All migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False
    
    def rollback(self, target_migration: Optional[str] = None) -> bool:
        """
        Rollback migrations to specific version
        
        Args:
            target_migration: Target migration ID to rollback to
            
        Returns:
            bool: Success status
        """
        try:
            applied_migrations = self.get_applied_migrations()
            all_migrations = self.discover_migrations()
            
            # Find migrations to rollback
            migrations_to_rollback = []
            for migration in reversed(all_migrations):
                if migration['id'] in applied_migrations:
                    if target_migration and migration['id'] <= target_migration:
                        break
                    migrations_to_rollback.append(migration)
            
            if not migrations_to_rollback:
                logger.info("No migrations to rollback")
                return True
            
            logger.info(f"Rolling back {len(migrations_to_rollback)} migrations")
            
            # Rollback migrations in reverse order
            for migration in migrations_to_rollback:
                success = self.rollback_migration(migration)
                if not success:
                    logger.error(f"Rollback failed at {migration['id']}")
                    return False
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get migration status
        
        Returns:
            Dict containing migration status
        """
        try:
            all_migrations = self.discover_migrations()
            applied_migrations = self.get_applied_migrations()
            pending_migrations = self.get_pending_migrations()
            
            return {
                "total_migrations": len(all_migrations),
                "applied_migrations": len(applied_migrations),
                "pending_migrations": len(pending_migrations),
                "applied_list": applied_migrations,
                "pending_list": [m['id'] for m in pending_migrations],
                "last_migration": applied_migrations[-1] if applied_migrations else None,
                "status": "up_to_date" if not pending_migrations else "pending_migrations"
            }
            
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return {"error": str(e)}
    
    def create_migration_template(self, name: str) -> str:
        """
        Create a new migration template
        
        Args:
            name: Migration name
            
        Returns:
            str: Path to created migration file
        """
        try:
            # Get next migration number
            existing_migrations = self.discover_migrations()
            next_number = 1
            if existing_migrations:
                last_id = existing_migrations[-1]['id']
                next_number = int(last_id) + 1
            
            # Create migration file
            migration_id = f"{next_number:03d}"
            filename = f"{migration_id}_{name}.py"
            file_path = Path(self.migrations_dir) / filename
            
            template = f'''"""\n{name.replace('_', ' ').title()} Migration\n\nDescription of what this migration does\n"""\n\nimport logging\nfrom datetime import datetime\nfrom typing import Dict, Any\nfrom ..vector_db import VectorDatabase\n\nlogger = logging.getLogger(__name__)\n\nMIGRATION_ID = "{migration_id}"\nMIGRATION_NAME = "{name}"\nMIGRATION_DESCRIPTION = "Description of migration"\n\ndef upgrade(db: VectorDatabase) -> bool:\n    """\n    Apply the migration\n    \n    Args:\n        db: Vector database instance\n        \n    Returns:\n        bool: Success status\n    """\n    try:\n        logger.info(f"Applying migration {{MIGRATION_ID}}: {{MIGRATION_NAME}}")\n        \n        # TODO: Implement migration logic\n        \n        logger.info(f"Migration {{MIGRATION_ID}} applied successfully")\n        return True\n        \n    except Exception as e:\n        logger.error(f"Error applying migration {{MIGRATION_ID}}: {{e}}")\n        return False\n\ndef downgrade(db: VectorDatabase) -> bool:\n    """\n    Rollback the migration\n    \n    Args:\n        db: Vector database instance\n        \n    Returns:\n        bool: Success status\n    """\n    try:\n        logger.info(f"Rolling back migration {{MIGRATION_ID}}: {{MIGRATION_NAME}}")\n        \n        # TODO: Implement rollback logic\n        \n        logger.info(f"Migration {{MIGRATION_ID}} rolled back successfully")\n        return True\n        \n    except Exception as e:\n        logger.error(f"Error rolling back migration {{MIGRATION_ID}}: {{e}}")\n        return False\n\ndef get_migration_info() -> Dict[str, Any]:\n    """\n    Get migration information\n    \n    Returns:\n        Dict containing migration details\n    """\n    return {{\n        "id": MIGRATION_ID,\n        "name": MIGRATION_NAME,\n        "description": MIGRATION_DESCRIPTION,\n        "created_at": "{datetime.now().isoformat()}",\n        "dependencies": [],\n        "reversible": True\n    }}\n'''
            
            with open(file_path, 'w') as f:
                f.write(template)
            
            logger.info(f"Created migration template: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error creating migration template: {e}")
            raise