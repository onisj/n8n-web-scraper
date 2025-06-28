"""
Database connection management for n8n scraper.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any

import asyncpg
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from config.settings import settings
from ..core.exceptions import DatabaseConnectionError, DatabaseError
from ..core.logging_config import get_logger
from ..core.metrics import metrics

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_engine = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._sync_session_factory = None
        self._connection_pool: Optional[asyncpg.Pool] = None
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connections and engines."""
        if self._is_initialized:
            return
        
        try:
            # Create async engine for SQLAlchemy
            self._async_engine = create_async_engine(
                settings.database_url_async,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=3600,  # Recycle connections every hour
                echo=settings.is_development,
            )
            
            # Create sync engine for migrations and other sync operations
            self._sync_engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=3600,
                echo=settings.is_development,
            )
            
            # Create session factories
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                class_=Session,
                expire_on_commit=False,
            )
            
            # Create asyncpg connection pool for raw queries
            # Extract the connection string for asyncpg (remove the +asyncpg part)
            asyncpg_url = settings.database_url_async.replace('postgresql+asyncpg://', 'postgresql://')
            self._connection_pool = await asyncpg.create_pool(
                asyncpg_url,
                min_size=2,
                max_size=settings.db_pool_size,
                command_timeout=60,
                server_settings={
                    'jit': 'off',  # Disable JIT for better performance with short queries
                },
            )
            
            self._is_initialized = True
            logger.info("Database manager initialized successfully")
            
            # Update metrics
            metrics.increment_counter("database_connections_initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            metrics.increment_counter("database_connection_errors")
            raise DatabaseConnectionError(f"Failed to initialize database: {str(e)}") from e
    
    async def close(self) -> None:
        """Close all database connections."""
        if not self._is_initialized:
            return
        
        try:
            # Close asyncpg pool
            if self._connection_pool:
                await self._connection_pool.close()
                self._connection_pool = None
            
            # Close async engine
            if self._async_engine:
                await self._async_engine.dispose()
                self._async_engine = None
            
            # Close sync engine
            if self._sync_engine:
                self._sync_engine.dispose()
                self._sync_engine = None
            
            self._async_session_factory = None
            self._sync_session_factory = None
            self._is_initialized = False
            
            logger.info("Database manager closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing database manager: {e}")
            raise DatabaseError(f"Failed to close database connections: {str(e)}") from e
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async SQLAlchemy session."""
        if not self._is_initialized:
            await self.initialize()
        
        if not self._async_session_factory:
            raise DatabaseConnectionError("Async session factory not initialized")
        
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            metrics.increment_counter("database_session_errors")
            raise
        finally:
            await session.close()
    
    def get_sync_session(self) -> Session:
        """Get a sync SQLAlchemy session."""
        if not self._sync_session_factory:
            raise DatabaseConnectionError("Sync session factory not initialized")
        
        return self._sync_session_factory()
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a raw asyncpg connection."""
        if not self._is_initialized:
            await self.initialize()
        
        if not self._connection_pool:
            raise DatabaseConnectionError("Connection pool not initialized")
        
        async with self._connection_pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                metrics.increment_counter("database_connection_errors")
                raise
    
    async def execute_query(
        self,
        query: str,
        *args,
        fetch: str = "all",
        **kwargs
    ) -> Any:
        """Execute a raw SQL query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            fetch: 'all', 'one', 'val', or 'none'
            **kwargs: Additional query parameters
        
        Returns:
            Query results based on fetch type
        """
        async with self.get_connection() as conn:
            try:
                if fetch == "all":
                    return await conn.fetch(query, *args, **kwargs)
                elif fetch == "one":
                    return await conn.fetchrow(query, *args, **kwargs)
                elif fetch == "val":
                    return await conn.fetchval(query, *args, **kwargs)
                elif fetch == "none":
                    return await conn.execute(query, *args, **kwargs)
                else:
                    raise ValueError(f"Invalid fetch type: {fetch}")
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                metrics.increment_counter("database_query_errors")
                raise DatabaseError(f"Query execution failed: {str(e)}") from e
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on database connections."""
        if not self._is_initialized:
            return {
                "status": "unhealthy",
                "message": "Database manager not initialized",
            }
        
        try:
            # Test asyncpg connection
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            
            # Test SQLAlchemy async session
            async with self.get_async_session() as session:
                result = await session.execute("SELECT 1")
                result.scalar()
            
            # Get pool statistics
            pool_stats = {}
            if self._connection_pool:
                pool_stats = {
                    "pool_size": self._connection_pool.get_size(),
                    "pool_min_size": self._connection_pool.get_min_size(),
                    "pool_max_size": self._connection_pool.get_max_size(),
                    "pool_idle_size": self._connection_pool.get_idle_size(),
                }
            
            return {
                "status": "healthy",
                "message": "All database connections are working",
                "pool_stats": pool_stats,
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database health check failed: {str(e)}",
                "error": str(e),
            }
    
    @property
    def is_initialized(self) -> bool:
        """Check if the database manager is initialized."""
        return self._is_initialized
    
    @property
    def async_engine(self) -> Optional[AsyncEngine]:
        """Get the async SQLAlchemy engine."""
        return self._async_engine
    
    @property
    def sync_engine(self):
        """Get the sync SQLAlchemy engine."""
        return self._sync_engine


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
async def get_database_connection() -> asyncpg.Connection:
    """Get a database connection from the pool."""
    if not db_manager.is_initialized:
        await db_manager.initialize()
    
    async with db_manager.get_connection() as conn:
        return conn


async def close_database_connection() -> None:
    """Close all database connections."""
    await db_manager.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async SQLAlchemy session."""
    async with db_manager.get_async_session() as session:
        yield session


def get_sync_session() -> Session:
    """Get a sync SQLAlchemy session."""
    return db_manager.get_sync_session()


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a raw database connection."""
    async with db_manager.get_connection() as conn:
        yield conn


async def execute_query(
    query: str,
    *args,
    fetch: str = "all",
    **kwargs
) -> Any:
    """Execute a raw SQL query."""
    return await db_manager.execute_query(query, *args, fetch=fetch, **kwargs)


# Database initialization and cleanup
async def initialize_database() -> None:
    """Initialize the database manager."""
    await db_manager.initialize()


async def cleanup_database() -> None:
    """Cleanup database connections."""
    await db_manager.close()


# FastAPI dependency for getting database session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    if not db_manager.is_initialized:
        await db_manager.initialize()
    
    async with db_manager.get_async_session() as session:
        yield session


# Context manager for database lifecycle
@asynccontextmanager
async def database_lifespan():
    """Context manager for database lifecycle management."""
    try:
        await initialize_database()
        logger.info("Database initialized")
        yield
    finally:
        await cleanup_database()
        logger.info("Database cleanup completed")