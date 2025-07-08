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
    
    # Data storage paths
    data_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data", env="DATA_DIRECTORY")
    database_base_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases", env="DATABASE_BASE_DIRECTORY")
    scraped_docs_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/scraped_docs", env="SCRAPED_DOCS_DIRECTORY")
    vector_db_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector", env="VECTOR_DB_DIRECTORY")
    backups_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/backups", env="BACKUPS_DIRECTORY")
    logs_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/logs", env="LOGS_DIRECTORY")
    exports_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/exports", env="EXPORTS_DIRECTORY")
    config_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/config", env="CONFIG_DIRECTORY")
    
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
    
    # FastAPI Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    api_debug: bool = Field(default=False, env="API_DEBUG")
    api_workers: int = Field(default=1, env="API_WORKERS")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    
    # API Security
    api_secret_key: str = Field(default="your_secret_key_here_change_this_in_production", env="API_SECRET_KEY")
    api_access_token_expire_minutes: int = Field(default=30, env="API_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # CORS Settings
    cors_allow_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8501"], env="CORS_ALLOW_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Legacy CORS setting for backward compatibility
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("cors_allow_origins", pre=True)
    def parse_cors_allow_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("cors_allow_methods", pre=True)
    def parse_cors_allow_methods(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @validator("cors_allow_headers", pre=True)
    def parse_cors_allow_headers(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
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
    openai_max_tokens: int = Field(default=2000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=2000, env="ANTHROPIC_MAX_TOKENS")
    anthropic_temperature: float = Field(default=0.1, env="ANTHROPIC_TEMPERATURE")
    
    # General AI Configuration
    default_ai_provider: str = Field(default="openai", env="DEFAULT_AI_PROVIDER")
    ai_timeout: int = Field(default=30, env="AI_TIMEOUT")
    ai_retry_attempts: int = Field(default=3, env="AI_RETRY_ATTEMPTS")
    
    # Vector Search Settings
    vector_search_top_k: int = Field(default=5, env="VECTOR_SEARCH_TOP_K")
    vector_search_score_threshold: float = Field(default=0.7, env="VECTOR_SEARCH_SCORE_THRESHOLD")
    
    # Conversation Settings
    conversation_memory_limit: int = Field(default=10, env="CONVERSATION_MEMORY_LIMIT")
    conversation_timeout_minutes: int = Field(default=30, env="CONVERSATION_TIMEOUT_MINUTES")
    
    @validator("default_ai_provider")
    def validate_ai_provider(cls, v: str) -> str:
        allowed_providers = ["openai", "anthropic"]
        if v not in allowed_providers:
            raise ValueError(f"AI provider must be one of {allowed_providers}")
        return v


class N8nConfig(BaseConfig):
    """n8n Configuration."""
    
    # n8n API Key (if accessing n8n instance)
    n8n_api_key: Optional[str] = Field(default=None, env="N8N_API_KEY")
    
    # n8n Instance URL (if using external n8n instance)
    n8n_base_url: Optional[str] = Field(default=None, env="N8N_BASE_URL")


class DatabaseConfig(BaseConfig):
    """Database configuration."""
    
    # PostgreSQL Database Configuration
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="n8n_scraper", env="DATABASE_NAME")
    database_user: str = Field(default="root", env="DATABASE_USER")
    database_password: str = Field(default="root", env="DATABASE_PASSWORD")
    database_url: str = Field(default="postgresql://root:root@localhost:5432/n8n_scraper", env="DATABASE_URL")
    database_url_async: str = Field(default="postgresql+asyncpg://user:password@localhost:5432/n8n_scraper", env="DATABASE_URL_ASYNC")
    
    # Database Pool Settings
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # Legacy pool settings for backward compatibility
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    # ChromaDB Configuration
    chroma_host: str = Field(default="localhost", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    chroma_persist_directory: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/vector", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="n8n_docs", env="CHROMA_COLLECTION_NAME")
    chroma_distance_function: str = Field(default="cosine", env="CHROMA_DISTANCE_FUNCTION")
    
    # Vector Database
    vector_db_path: Optional[Path] = Field(default=None, env="VECTOR_DB_PATH")
    vector_db_collection: str = Field(default="n8n_docs", env="VECTOR_DB_COLLECTION")
    
    # Knowledge Database
    knowledge_db_path: Optional[Path] = Field(default=None, env="KNOWLEDGE_DB_PATH")
    
    # SQLite Configuration (for workflows)
    sqlite_db_path: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/sqlite/workflows.db", env="SQLITE_DB_PATH")
    workflow_db_path: str = Field(default="/Users/user/Projects/n8n-projects/n8n-web-scrapper/data/databases/sqlite/workflows.db", env="WORKFLOW_DB_PATH")
    sqlite_timeout: int = Field(default=30, env="SQLITE_TIMEOUT")
    sqlite_check_same_thread: bool = Field(default=False, env="SQLITE_CHECK_SAME_THREAD")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")


class ScrapingConfig(BaseConfig):
    """Web scraping configuration."""
    
    # Scraping Settings
    scraper_base_url: str = Field(default="https://docs.n8n.io", env="SCRAPER_BASE_URL")
    scraper_max_pages: int = Field(default=500, env="SCRAPER_MAX_PAGES")
    scraper_delay_between_requests: float = Field(default=1.0, env="SCRAPER_DELAY_BETWEEN_REQUESTS")
    scraper_timeout: int = Field(default=30, env="SCRAPER_TIMEOUT")
    scraper_max_retries: int = Field(default=3, env="SCRAPER_MAX_RETRIES")
    scraper_concurrent_requests: int = Field(default=5, env="SCRAPER_CONCURRENT_REQUESTS")
    
    # Legacy settings for backward compatibility
    scraper_delay: float = Field(default=1.0, env="SCRAPER_DELAY")
    
    # User Agent for scraping
    scraper_user_agent: str = Field(
        default="n8n-knowledge-system/1.0",
        env="SCRAPER_USER_AGENT"
    )
    
    # Automated Scraping Configuration
    scrape_interval_days: int = Field(default=2, env="SCRAPE_INTERVAL_DAYS")
    scrape_interval_hours: int = Field(default=0, env="SCRAPE_INTERVAL_HOURS")
    scrape_schedule_time: str = Field(default="02:00", env="SCRAPE_SCHEDULE_TIME")
    scrape_enabled: bool = Field(default=True, env="SCRAPE_ENABLED")
    
    # Data Processing
    auto_import_to_database: bool = Field(default=True, env="AUTO_IMPORT_TO_DATABASE")
    auto_export_formats: bool = Field(default=True, env="AUTO_EXPORT_FORMATS")
    auto_backup_enabled: bool = Field(default=True, env="AUTO_BACKUP_ENABLED")


class UpdateConfig(BaseConfig):
    """Update and automation configuration."""
    
    update_frequency: UpdateFrequency = Field(default=UpdateFrequency.DAILY, env="UPDATE_FREQUENCY")
    full_scrape_frequency: UpdateFrequency = Field(default=UpdateFrequency.WEEKLY, env="FULL_SCRAPE_FREQUENCY")
    backup_retention_days: int = Field(default=7, env="BACKUP_RETENTION_DAYS")
    enable_auto_updates: bool = Field(default=True, env="ENABLE_AUTO_UPDATES")
    update_check_interval: int = Field(default=3600, env="UPDATE_CHECK_INTERVAL")  # seconds
    
    # Update Scheduler
    update_schedule_time: str = Field(default="02:00", env="UPDATE_SCHEDULE_TIME")
    update_schedule_enabled: bool = Field(default=True, env="UPDATE_SCHEDULE_ENABLED")
    
    # Notifications
    notifications_enabled: bool = Field(default=True, env="NOTIFICATIONS_ENABLED")
    webhook_url: Optional[str] = Field(default=None, env="WEBHOOK_URL")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    discord_webhook_url: Optional[str] = Field(default=None, env="DISCORD_WEBHOOK_URL")


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
    
    # Cache Settings
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    
    # Threading and Concurrency
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    thread_pool_size: int = Field(default=10, env="THREAD_POOL_SIZE")
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Memory Management
    memory_limit_mb: int = Field(default=1024, env="MEMORY_LIMIT_MB")
    max_memory_usage_percent: int = Field(default=80, env="MAX_MEMORY_USAGE_PERCENT")
    garbage_collection_threshold: int = Field(default=1000, env="GARBAGE_COLLECTION_THRESHOLD")


class SecurityConfig(BaseConfig):
    """Security configuration."""
    
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # Authentication
    auth_enabled: bool = Field(default=False, env="AUTH_ENABLED")
    auth_secret_key: str = Field(default="your_auth_secret_key_here", env="AUTH_SECRET_KEY")
    auth_algorithm: str = Field(default="HS256", env="AUTH_ALGORITHM")


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
    N8nConfig,
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
ANTHROPIC_API_KEY = settings.anthropic_api_key
N8N_API_KEY = settings.n8n_api_key
N8N_BASE_URL = settings.n8n_base_url
DATABASE_URL = settings.database_url
VECTOR_DB_PATH = settings.vector_db_path
KNOWLEDGE_DB_PATH = settings.knowledge_db_path
LOG_LEVEL = settings.log_level
LOG_FILE = settings.log_file
SCRAPER_USER_AGENT = settings.scraper_user_agent
DEFAULT_AI_PROVIDER = settings.default_ai_provider
