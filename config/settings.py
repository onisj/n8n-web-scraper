"""
Configuration settings for n8n AI Knowledge System using Pydantic.
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UpdateFrequency(str, Enum):
    """Update frequency options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BaseConfig(BaseSettings):
    """Base configuration with common settings."""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "use_enum_values": True,
        "extra": "ignore"
    }


class PathConfig(BaseConfig):
    """Path-related configuration."""
    
    # Base paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default=None)
    logs_dir: Path = Field(default=None)
    backups_dir: Path = Field(default=None)
    
    @validator("data_dir", pre=True, always=True)
    def set_data_dir(cls, v: Optional[Path], values: Dict[str, Any]) -> Path:
        return v or values["base_dir"] / "data"
    
    @validator("logs_dir", pre=True, always=True)
    def set_logs_dir(cls, v: Optional[Path], values: Dict[str, Any]) -> Path:
        return v or values["base_dir"] / "data" / "logs"
    
    @validator("backups_dir", pre=True, always=True)
    def set_backups_dir(cls, v: Optional[Path], values: Dict[str, Any]) -> Path:
        return v or values["base_dir"] / "backups"


class APIConfig(BaseConfig):
    """API server configuration."""
    
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


# class StreamlitConfig(BaseConfig):
#     """Streamlit configuration - REMOVED."""
#
#     streamlit_host: str = Field(default="0.0.0.0", env="STREAMLIT_HOST")
#     streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")


class AIConfig(BaseConfig):
    """AI and LLM configuration."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=500, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=500, env="ANTHROPIC_MAX_TOKENS")
    
    # General AI Configuration
    default_ai_provider: str = Field(default="openai", env="DEFAULT_AI_PROVIDER")
    ai_timeout: int = Field(default=30, env="AI_TIMEOUT")
    ai_retry_attempts: int = Field(default=3, env="AI_RETRY_ATTEMPTS")
    
    @validator("default_ai_provider")
    def validate_ai_provider(cls, v: str) -> str:
        allowed_providers = ["openai", "anthropic"]
        if v not in allowed_providers:
            raise ValueError(f"AI provider must be one of {allowed_providers}")
        return v


class DatabaseConfig(BaseConfig):
    """Database configuration."""
    
    # PostgreSQL Database Configuration
    database_url: str = Field(default="postgresql://user:password@localhost:5432/n8n_scraper", env="DATABASE_URL")
    database_url_async: str = Field(default="postgresql+asyncpg://user:password@localhost:5432/n8n_scraper", env="DATABASE_URL_ASYNC")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    # Vector Database
    vector_db_path: Optional[Path] = Field(default=None, env="VECTOR_DB_PATH")
    vector_db_collection: str = Field(default="n8n_docs", env="VECTOR_DB_COLLECTION")
    
    # Knowledge Database
    knowledge_db_path: Optional[Path] = Field(default=None, env="KNOWLEDGE_DB_PATH")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")


class ScrapingConfig(BaseConfig):
    """Web scraping configuration."""
    
    scraper_base_url: str = Field(default="https://docs.n8n.io", env="SCRAPER_BASE_URL")
    scraper_max_pages: int = Field(default=1000, env="SCRAPER_MAX_PAGES")
    scraper_delay: float = Field(default=1.0, env="SCRAPER_DELAY")
    scraper_timeout: int = Field(default=30, env="SCRAPER_TIMEOUT")
    scraper_user_agent: str = Field(
        default="n8n-scraper/1.0 (+https://github.com/user/n8n-scraper)",
        env="SCRAPER_USER_AGENT"
    )
    scraper_max_retries: int = Field(default=3, env="SCRAPER_MAX_RETRIES")
    scraper_concurrent_requests: int = Field(default=5, env="SCRAPER_CONCURRENT_REQUESTS")


class UpdateConfig(BaseConfig):
    """Update and automation configuration."""
    
    update_frequency: UpdateFrequency = Field(default=UpdateFrequency.DAILY, env="UPDATE_FREQUENCY")
    full_scrape_frequency: UpdateFrequency = Field(default=UpdateFrequency.WEEKLY, env="FULL_SCRAPE_FREQUENCY")
    backup_retention_days: int = Field(default=30, env="BACKUP_RETENTION_DAYS")
    enable_auto_updates: bool = Field(default=True, env="ENABLE_AUTO_UPDATES")
    update_check_interval: int = Field(default=3600, env="UPDATE_CHECK_INTERVAL")  # seconds


class LoggingConfig(BaseConfig):
    """Logging configuration."""
    
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: Optional[Path] = Field(default=None, env="LOG_FILE")
    log_max_size: int = Field(default=10485760, env="LOG_MAX_SIZE")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    enable_json_logging: bool = Field(default=False, env="ENABLE_JSON_LOGGING")


class PerformanceConfig(BaseConfig):
    """Performance and caching configuration."""
    
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    memory_limit_mb: int = Field(default=1024, env="MEMORY_LIMIT_MB")


class SecurityConfig(BaseConfig):
    """Security configuration."""
    
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour


class MonitoringConfig(BaseConfig):
    """Monitoring and observability configuration."""
    
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    enable_health_checks: bool = Field(default=True, env="ENABLE_HEALTH_CHECKS")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    enable_tracing: bool = Field(default=False, env="ENABLE_TRACING")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")


class Settings(
    PathConfig,
    APIConfig,
    # StreamlitConfig,  # Removed - replaced by Next.js frontend
    AIConfig,
    DatabaseConfig,
    ScrapingConfig,
    UpdateConfig,
    LoggingConfig,
    PerformanceConfig,
    SecurityConfig,
    MonitoringConfig,
):
    """Main application settings combining all configuration sections."""
    
    # Application metadata
    app_name: str = Field(default="n8n AI Knowledge System", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
        self._setup_derived_paths()
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.logs_dir,
            self.backups_dir,
            self.data_dir / "scraped_docs",
            self.data_dir / "exports",
            self.data_dir / "analysis",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _setup_derived_paths(self) -> None:
        """Setup derived paths based on base configuration."""
        if not self.vector_db_path:
            self.vector_db_path = self.data_dir / "vector_db"
        
        if not self.knowledge_db_path:
            self.knowledge_db_path = self.data_dir / "knowledge.db"
        
        if not self.log_file:
            self.log_file = self.logs_dir / "system.log"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING
    
    def get_log_level(self) -> int:
        """Get numeric log level for Python logging."""
        return getattr(logging, self.log_level.value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return self.dict()
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "use_enum_values": True,
        "validate_assignment": True,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()

# Backward compatibility exports
BASE_DIR = settings.base_dir
DATA_DIR = settings.data_dir
LOGS_DIR = settings.logs_dir
BACKUPS_DIR = settings.backups_dir
API_HOST = settings.api_host
API_PORT = settings.api_port
# STREAMLIT_HOST = settings.streamlit_host  # Removed - replaced by Next.js frontend
# STREAMLIT_PORT = settings.streamlit_port  # Removed - replaced by Next.js frontend
OPENAI_API_KEY = settings.openai_api_key
VECTOR_DB_PATH = settings.vector_db_path
KNOWLEDGE_DB_PATH = settings.knowledge_db_path
LOG_LEVEL = settings.log_level
LOG_FILE = settings.log_file
