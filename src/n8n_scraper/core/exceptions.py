"""
Custom exceptions for the n8n scraper system.
"""

from typing import Any, Dict, Optional


class N8nScraperError(Exception):
    """Base exception for all n8n scraper errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class ConfigurationError(N8nScraperError):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(N8nScraperError):
    """Raised when data validation fails."""
    pass


# Scraping-related exceptions
class ScrapingError(N8nScraperError):
    """Base exception for scraping-related errors."""
    pass


class ScrapingTimeoutError(ScrapingError):
    """Raised when scraping operations timeout."""
    pass


class ScrapingRateLimitError(ScrapingError):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ScrapingAuthenticationError(ScrapingError):
    """Raised when authentication fails during scraping."""
    pass


class ScrapingParseError(ScrapingError):
    """Raised when content parsing fails."""
    pass


class ContentExtractionError(ScrapingError):
    """Raised when content extraction fails."""
    pass


class ScrapingNetworkError(ScrapingError):
    """Raised when network issues occur during scraping."""
    pass


# Database-related exceptions
class DatabaseError(N8nScraperError):
    """Base exception for database-related errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class DatabaseQueryError(DatabaseError):
    """Raised when database queries fail."""
    pass


class DatabaseMigrationError(DatabaseError):
    """Raised when database migrations fail."""
    pass


# Vector database exceptions
class VectorDatabaseError(DatabaseError):
    """Base exception for vector database errors."""
    pass


class VectorDatabaseConnectionError(VectorDatabaseError):
    """Raised when vector database connection fails."""
    pass


class VectorDatabaseIndexError(VectorDatabaseError):
    """Raised when vector indexing fails."""
    pass


class VectorDatabaseSearchError(VectorDatabaseError):
    """Raised when vector search fails."""
    pass


# AI/LLM-related exceptions
class AIError(N8nScraperError):
    """Base exception for AI/LLM-related errors."""
    pass


class AIProviderError(AIError):
    """Raised when AI provider operations fail."""
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.model = model


class AIRateLimitError(AIError):
    """Raised when AI provider rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AIAuthenticationError(AIError):
    """Raised when AI provider authentication fails."""
    pass


class AITokenLimitError(AIError):
    """Raised when AI token limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        token_count: Optional[int] = None,
        token_limit: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.token_count = token_count
        self.token_limit = token_limit


class AIResponseError(AIError):
    """Raised when AI response is invalid or unexpected."""
    pass


# API-related exceptions
class APIError(N8nScraperError):
    """Base exception for API-related errors."""
    pass


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass


class APIAuthorizationError(APIError):
    """Raised when API authorization fails."""
    pass


class APIRateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIValidationError(APIError):
    """Raised when API request validation fails."""
    pass


class APINotFoundError(APIError):
    """Raised when API resource is not found."""
    pass


class APIServerError(APIError):
    """Raised when API server errors occur."""
    pass


# Processing-related exceptions
class ProcessingError(N8nScraperError):
    """Base exception for data processing errors."""
    pass


class ProcessingTimeoutError(ProcessingError):
    """Raised when processing operations timeout."""
    pass


class ProcessingMemoryError(ProcessingError):
    """Raised when processing runs out of memory."""
    pass


class ProcessingValidationError(ProcessingError):
    """Raised when processing validation fails."""
    pass


class ContentProcessingError(ProcessingError):
    """Raised when content processing fails."""
    pass


# Cache-related exceptions
class CacheError(N8nScraperError):
    """Base exception for cache-related errors."""
    pass


class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""
    pass


class CacheKeyError(CacheError):
    """Raised when cache key operations fail."""
    pass


class CacheSerializationError(CacheError):
    """Raised when cache serialization/deserialization fails."""
    pass


# File system exceptions
class FileSystemError(N8nScraperError):
    """Base exception for file system errors."""
    pass


class FileNotFoundError(FileSystemError):
    """Raised when required files are not found."""
    pass


class FilePermissionError(FileSystemError):
    """Raised when file permission errors occur."""
    pass


class FileCorruptionError(FileSystemError):
    """Raised when file corruption is detected."""
    pass


# Automation exceptions
class AutomationError(N8nScraperError):
    """Base exception for automation-related errors."""
    pass


class SchedulerError(AutomationError):
    """Raised when scheduler operations fail."""
    pass


class TaskExecutionError(AutomationError):
    """Raised when automated task execution fails."""
    
    def __init__(
        self,
        message: str,
        task_name: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.task_name = task_name
        self.task_id = task_id


class TaskTimeoutError(AutomationError):
    """Raised when automated tasks timeout."""
    pass


# Monitoring exceptions
class MonitoringError(N8nScraperError):
    """Base exception for monitoring-related errors."""
    pass


class MetricsError(MonitoringError):
    """Raised when metrics collection fails."""
    pass


class HealthCheckError(MonitoringError):
    """Raised when health checks fail."""
    
    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.component = component


# Utility functions for exception handling
def handle_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True,
) -> Optional[N8nScraperError]:
    """Handle and optionally convert exceptions to N8nScraperError."""
    if isinstance(exception, N8nScraperError):
        if context:
            exception.context.update(context)
        if reraise:
            raise exception
        return exception
    
    # Convert common exceptions to N8nScraperError
    error_mappings = {
        ConnectionError: DatabaseConnectionError,
        TimeoutError: ProcessingTimeoutError,
        MemoryError: ProcessingMemoryError,
        PermissionError: FilePermissionError,
        FileNotFoundError: FileNotFoundError,
    }
    
    error_class = error_mappings.get(type(exception), N8nScraperError)
    wrapped_error = error_class(
        message=str(exception),
        context=context,
        original_error=exception,
    )
    
    if reraise:
        raise wrapped_error
    return wrapped_error


def create_error_response(
    exception: Exception,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """Create a standardized error response dictionary."""
    if isinstance(exception, N8nScraperError):
        response = exception.to_dict()
    else:
        response = {
            "error_type": type(exception).__name__,
            "message": str(exception),
            "error_code": None,
            "context": {},
            "original_error": None,
        }
    
    if include_traceback:
        import traceback
        response["traceback"] = traceback.format_exc()
    
    return response