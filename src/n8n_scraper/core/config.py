"""
Configuration management for the n8n scraper.

This module provides configuration classes and utilities for managing
scraper settings, database connections, and other system parameters.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, Union
from urllib.parse import urlparse

from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    def __post_init__(self):
        """Validate database configuration."""
        if self.url:
            try:
                parsed = urlparse(self.url)
                if not parsed.scheme:
                    raise ValueError("Database URL must include a scheme")
            except Exception as e:
                raise ConfigurationError(f"Invalid database URL: {e}")


@dataclass
class VectorStoreConfig:
    """Vector store configuration settings."""
    enabled: bool = True
    backend: str = "numpy"  # numpy, faiss, chroma
    dimension: int = 384
    index_type: str = "flat"  # flat, ivf, hnsw
    metric: str = "cosine"  # cosine, euclidean, dot_product
    storage_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate vector store configuration."""
        valid_backends = ["numpy", "faiss", "chroma"]
        if self.backend not in valid_backends:
            raise ConfigurationError(f"Invalid vector store backend: {self.backend}. Must be one of {valid_backends}")
        
        valid_metrics = ["cosine", "euclidean", "dot_product"]
        if self.metric not in valid_metrics:
            raise ConfigurationError(f"Invalid metric: {self.metric}. Must be one of {valid_metrics}")


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    enabled: bool = True
    backend: str = "memory"  # memory, redis, file
    ttl: int = 3600  # Time to live in seconds
    max_size: int = 1000  # Maximum number of items
    redis_url: Optional[str] = None
    file_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate cache configuration."""
        valid_backends = ["memory", "redis", "file"]
        if self.backend not in valid_backends:
            raise ConfigurationError(f"Invalid cache backend: {self.backend}. Must be one of {valid_backends}")
        
        if self.backend == "redis" and not self.redis_url:
            raise ConfigurationError("Redis URL is required when using redis backend")


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ConfigurationError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")
        self.level = self.level.upper()


@dataclass
class ScrapingConfig:
    """Scraping configuration settings."""
    max_pages: int = 100
    max_depth: int = 3
    delay_range: tuple = (1.0, 2.0)
    max_concurrent: int = 5
    timeout: int = 30
    retries: int = 3
    user_agent: str = "n8n-scraper/1.0"
    respect_robots_txt: bool = True
    
    def __post_init__(self):
        """Validate scraping configuration."""
        if self.max_pages <= 0:
            raise ConfigurationError("max_pages must be positive")
        if self.max_depth <= 0:
            raise ConfigurationError("max_depth must be positive")
        if self.max_concurrent <= 0:
            raise ConfigurationError("max_concurrent must be positive")
        if len(self.delay_range) != 2 or self.delay_range[0] > self.delay_range[1]:
            raise ConfigurationError("delay_range must be a tuple of (min, max) where min <= max")


@dataclass
class ProcessingConfig:
    """Content processing configuration settings."""
    min_content_length: int = 100
    max_content_length: int = 1000000
    quality_threshold: float = 0.5
    enable_chunking: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200
    enable_embeddings: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    def __post_init__(self):
        """Validate processing configuration."""
        if self.min_content_length < 0:
            raise ConfigurationError("min_content_length must be non-negative")
        if self.max_content_length <= self.min_content_length:
            raise ConfigurationError("max_content_length must be greater than min_content_length")
        if not 0 <= self.quality_threshold <= 1:
            raise ConfigurationError("quality_threshold must be between 0 and 1")
        if self.chunk_size <= 0:
            raise ConfigurationError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ConfigurationError("chunk_overlap must be non-negative")


@dataclass
class Config:
    """Main configuration class."""
    database: DatabaseConfig = None
    vector_store: VectorStoreConfig = None
    cache: CacheConfig = None
    logging: LoggingConfig = None
    scraping: ScrapingConfig = None
    processing: ProcessingConfig = None
    
    def __post_init__(self):
        """Initialize default configurations if not provided."""
        if self.database is None:
            self.database = DatabaseConfig()
        if self.vector_store is None:
            self.vector_store = VectorStoreConfig()
        if self.cache is None:
            self.cache = CacheConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.scraping is None:
            self.scraping = ScrapingConfig()
        if self.processing is None:
            self.processing = ProcessingConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        try:
            return cls(
                database=DatabaseConfig(**data.get('database', {})),
                vector_store=VectorStoreConfig(**data.get('vector_store', {})),
                cache=CacheConfig(**data.get('cache', {})),
                logging=LoggingConfig(**data.get('logging', {})),
                scraping=ScrapingConfig(**data.get('scraping', {})),
                processing=ProcessingConfig(**data.get('processing', {}))
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to create configuration from dict: {e}")
    
    def validate(self) -> None:
        """Validate the entire configuration."""
        # Individual dataclass validation happens in __post_init__
        # Add any cross-configuration validation here
        pass
    
    def update_from_env(self) -> None:
        """Update configuration from environment variables."""
        # Database
        if db_url := os.getenv('DATABASE_URL'):
            self.database.url = db_url
        
        # Vector store
        if vs_backend := os.getenv('VECTOR_STORE_BACKEND'):
            self.vector_store.backend = vs_backend
        
        # Cache
        if cache_backend := os.getenv('CACHE_BACKEND'):
            self.cache.backend = cache_backend
        if redis_url := os.getenv('REDIS_URL'):
            self.cache.redis_url = redis_url
        
        # Logging
        if log_level := os.getenv('LOG_LEVEL'):
            self.logging.level = log_level
        if log_file := os.getenv('LOG_FILE'):
            self.logging.file = log_file
        
        # Scraping
        if max_pages := os.getenv('MAX_PAGES'):
            try:
                self.scraping.max_pages = int(max_pages)
            except ValueError:
                logger.warning(f"Invalid MAX_PAGES value: {max_pages}")
        
        if max_concurrent := os.getenv('MAX_CONCURRENT'):
            try:
                self.scraping.max_concurrent = int(max_concurrent)
            except ValueError:
                logger.warning(f"Invalid MAX_CONCURRENT value: {max_concurrent}")


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from file or create default.
    
    Args:
        config_path: Path to configuration file. If None, looks for default locations.
    
    Returns:
        Config: Loaded configuration object.
    
    Raises:
        ConfigurationError: If configuration file is invalid.
    """
    if config_path is None:
        # Look for config in default locations
        possible_paths = [
            Path.cwd() / 'config' / 'scraper.json',
            Path.cwd() / 'scraper.json',
            Path.home() / '.n8n-scraper' / 'config.json',
        ]
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
    
    if config_path is None:
        logger.info("No configuration file found, using defaults")
        config = Config()
    else:
        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            config = Config.from_dict(data)
            logger.info(f"Configuration loaded from {config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    # Update from environment variables
    config.update_from_env()
    
    # Validate configuration
    config.validate()
    
    return config


def save_config(config: Config, config_path: Union[str, Path]) -> None:
    """Save configuration to file.
    
    Args:
        config: Configuration object to save.
        config_path: Path where to save the configuration.
    
    Raises:
        ConfigurationError: If saving fails.
    """
    config_path = Path(config_path)
    
    try:
        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
    
    except Exception as e:
        raise ConfigurationError(f"Failed to save configuration: {e}")


def get_default_config() -> Config:
    """Get default configuration.
    
    Returns:
        Config: Default configuration object.
    """
    return Config()


def merge_configs(base: Config, override: Config) -> Config:
    """Merge two configurations, with override taking precedence.
    
    Args:
        base: Base configuration.
        override: Override configuration.
    
    Returns:
        Config: Merged configuration.
    """
    base_dict = base.to_dict()
    override_dict = override.to_dict()
    
    # Deep merge dictionaries
    def deep_merge(base_dict: dict, override_dict: dict) -> dict:
        result = base_dict.copy()
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    merged_dict = deep_merge(base_dict, override_dict)
    return Config.from_dict(merged_dict)