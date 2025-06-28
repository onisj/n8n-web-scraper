"""
Centralized logging configuration for the n8n scraper system.
"""

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "getMessage"
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class LoggingConfig:
    """Centralized logging configuration manager."""
    
    def __init__(self):
        self._configured = False
        self._loggers: Dict[str, logging.Logger] = {}
    
    def setup_logging(
        self,
        log_level: Optional[str] = None,
        log_file: Optional[Path] = None,
        enable_json: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Setup comprehensive logging configuration."""
        if self._configured:
            return
        
        # Use settings defaults if not provided
        log_level = log_level or settings.log_level
        log_file = log_file or settings.log_file
        enable_json = enable_json if enable_json is not None else settings.enable_json_logging
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Setup formatters
        if enable_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt=settings.log_format,
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        
        # Add context filter if provided
        if context:
            console_handler.addFilter(ContextFilter(context))
        
        root_logger.addHandler(console_handler)
        
        # Setup file handler if log file is specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=settings.log_max_size,
                backupCount=settings.log_backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            
            if context:
                file_handler.addFilter(ContextFilter(context))
            
            root_logger.addHandler(file_handler)
        
        # Setup error file handler for ERROR and CRITICAL logs
        if log_file:
            error_file = log_file.parent / f"error_{log_file.name}"
            error_handler = logging.handlers.RotatingFileHandler(
                filename=error_file,
                maxBytes=settings.log_max_size,
                backupCount=settings.log_backup_count,
                encoding="utf-8"
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            
            if context:
                error_handler.addFilter(ContextFilter(context))
            
            root_logger.addHandler(error_handler)
        
        # Configure third-party loggers
        self._configure_third_party_loggers()
        
        self._configured = True
        
        # Log configuration completion
        logger = self.get_logger("logging_config")
        logger.info(
            "Logging configured",
            extra={
                "log_level": log_level,
                "log_file": str(log_file) if log_file else None,
                "json_logging": enable_json,
                "context": context,
            }
        )
    
    def _configure_third_party_loggers(self) -> None:
        """Configure logging levels for third-party libraries."""
        third_party_configs = {
            "urllib3": logging.WARNING,
            "requests": logging.WARNING,
            "httpx": logging.WARNING,
            "chromadb": logging.WARNING,
            "openai": logging.WARNING,
            "anthropic": logging.WARNING,
            # "streamlit": logging.WARNING,  # Removed - replaced by Next.js frontend
            "uvicorn": logging.INFO,
            "fastapi": logging.INFO,
        }
        
        for logger_name, level in third_party_configs.items():
            logging.getLogger(logger_name).setLevel(level)
    
    def get_logger(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> logging.Logger:
        """Get a configured logger instance."""
        if not self._configured:
            self.setup_logging()
        
        if name not in self._loggers:
            logger = logging.getLogger(name)
            
            # Add context filter if provided
            if context:
                logger.addFilter(ContextFilter(context))
            
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def add_context_to_logger(
        self,
        logger_name: str,
        context: Dict[str, Any],
    ) -> None:
        """Add context to an existing logger."""
        if logger_name in self._loggers:
            self._loggers[logger_name].addFilter(ContextFilter(context))
    
    def set_log_level(self, level: str) -> None:
        """Dynamically change log level for all loggers."""
        numeric_level = getattr(logging, level.upper())
        
        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
        
        logger = self.get_logger("logging_config")
        logger.info(f"Log level changed to {level.upper()}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        root_logger = logging.getLogger()
        
        return {
            "configured": self._configured,
            "root_level": logging.getLevelName(root_logger.level),
            "handlers_count": len(root_logger.handlers),
            "loggers_count": len(self._loggers),
            "handler_types": [type(h).__name__ for h in root_logger.handlers],
        }


# Global logging configuration instance
logging_config = LoggingConfig()


def get_logger(
    name: str,
    context: Optional[Dict[str, Any]] = None,
) -> logging.Logger:
    """Convenience function to get a configured logger."""
    return logging_config.get_logger(name, context)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_json: Optional[bool] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience function to setup logging."""
    logging_config.setup_logging(log_level, log_file, enable_json, context)


def log_function_call(func_name: str, **kwargs) -> Dict[str, Any]:
    """Create a standardized log entry for function calls."""
    return {
        "event_type": "function_call",
        "function": func_name,
        "parameters": kwargs,
    }


def log_performance(operation: str, duration: float, **kwargs) -> Dict[str, Any]:
    """Create a standardized log entry for performance metrics."""
    return {
        "event_type": "performance",
        "operation": operation,
        "duration_seconds": duration,
        **kwargs,
    }


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized log entry for errors."""
    return {
        "event_type": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
    }