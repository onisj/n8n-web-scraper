"""
Health check system for monitoring application components.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from config.settings import settings
from .exceptions import HealthCheckError
from .logging_config import get_logger
from .metrics import metrics

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }
    
    @property
    def is_healthy(self) -> bool:
        """Check if the component is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def is_unhealthy(self) -> bool:
        """Check if the component is unhealthy."""
        return self.status == HealthStatus.UNHEALTHY


class HealthCheck(ABC):
    """Abstract base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Perform the health check."""
        pass
    
    async def run_check(self) -> HealthCheckResult:
        """Run the health check with timeout and error handling."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(self.check(), timeout=self.timeout)
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check failed for {self.name}: {e}")
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
            )


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""
    
    def __init__(self, timeout: float = 5.0):
        super().__init__("database", timeout)
    
    async def check(self) -> HealthCheckResult:
        """Check database connectivity."""
        try:
            # Import here to avoid circular imports
            from ..database.connection import get_database_connection
            
            # Test database connection
            conn = await get_database_connection()
            if conn:
                await conn.execute("SELECT 1")
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Database connection is healthy",
                    details={"connection_pool_size": getattr(conn, "pool_size", "unknown")},
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Unable to establish database connection",
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class VectorDatabaseHealthCheck(HealthCheck):
    """Health check for vector database connectivity."""
    
    def __init__(self, timeout: float = 5.0):
        super().__init__("vector_database", timeout)
    
    async def check(self) -> HealthCheckResult:
        """Check vector database connectivity."""
        try:
            # Import here to avoid circular imports
            from ..database.vector_store import VectorStore
            
            vector_store = VectorStore()
            collection_count = await vector_store.get_collection_count()
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="Vector database is healthy",
                details={
                    "collection_count": collection_count,
                    "database_path": str(settings.vector_db_path),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Vector database health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class RedisHealthCheck(HealthCheck):
    """Health check for Redis connectivity."""
    
    def __init__(self, timeout: float = 5.0):
        super().__init__("redis", timeout)
    
    async def check(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        try:
            import redis.asyncio as redis
            
            client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                socket_timeout=self.timeout,
            )
            
            # Test connection with ping
            await client.ping()
            info = await client.info()
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="Redis connection is healthy",
                details={
                    "redis_version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class AIProviderHealthCheck(HealthCheck):
    """Health check for AI provider connectivity."""
    
    def __init__(self, provider: str = "openai", timeout: float = 10.0):
        super().__init__(f"ai_provider_{provider}", timeout)
        self.provider = provider
    
    async def check(self) -> HealthCheckResult:
        """Check AI provider connectivity."""
        try:
            if self.provider == "openai":
                return await self._check_openai()
            elif self.provider == "anthropic":
                return await self._check_anthropic()
            else:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Unknown AI provider: {self.provider}",
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"AI provider health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )
    
    async def _check_openai(self) -> HealthCheckResult:
        """Check OpenAI connectivity."""
        if not settings.openai_api_key:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message="OpenAI API key not configured",
            )
        
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Test with a minimal request
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="OpenAI API is accessible",
                details={
                    "model": response.model,
                    "usage": response.usage.dict() if response.usage else {},
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"OpenAI API check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )
    
    async def _check_anthropic(self) -> HealthCheckResult:
        """Check Anthropic connectivity."""
        if not settings.anthropic_api_key:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Anthropic API key not configured",
            )
        
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            
            # Test with a minimal request
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}],
            )
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                message="Anthropic API is accessible",
                details={
                    "model": response.model,
                    "usage": response.usage.dict() if hasattr(response, "usage") else {},
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Anthropic API check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class FileSystemHealthCheck(HealthCheck):
    """Health check for file system access."""
    
    def __init__(self, timeout: float = 5.0):
        super().__init__("filesystem", timeout)
    
    async def check(self) -> HealthCheckResult:
        """Check file system access."""
        try:
            import os
            import tempfile
            from pathlib import Path
            
            # Check critical directories
            critical_dirs = [
                settings.data_dir,
                settings.logs_dir,
                settings.backups_dir,
            ]
            
            issues = []
            for directory in critical_dirs:
                if not directory.exists():
                    issues.append(f"Directory does not exist: {directory}")
                elif not os.access(directory, os.R_OK | os.W_OK):
                    issues.append(f"No read/write access to: {directory}")
            
            # Test write access with temporary file
            try:
                with tempfile.NamedTemporaryFile(dir=settings.data_dir, delete=True) as f:
                    f.write(b"health check test")
                    f.flush()
            except Exception as e:
                issues.append(f"Cannot write to data directory: {str(e)}")
            
            if issues:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="File system access issues detected",
                    details={"issues": issues},
                )
            
            # Get disk usage information
            disk_usage = os.statvfs(settings.data_dir)
            free_space_gb = (disk_usage.f_bavail * disk_usage.f_frsize) / (1024**3)
            total_space_gb = (disk_usage.f_blocks * disk_usage.f_frsize) / (1024**3)
            usage_percent = ((total_space_gb - free_space_gb) / total_space_gb) * 100
            
            status = HealthStatus.HEALTHY
            message = "File system is healthy"
            
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Disk usage is critically high"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = "Disk usage is high"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "free_space_gb": round(free_space_gb, 2),
                    "total_space_gb": round(total_space_gb, 2),
                    "usage_percent": round(usage_percent, 2),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"File system health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage."""
    
    def __init__(self, timeout: float = 5.0):
        super().__init__("memory", timeout)
    
    async def check(self) -> HealthCheckResult:
        """Check memory usage."""
        try:
            import psutil
            
            # Get system memory info
            memory = psutil.virtual_memory()
            
            # Get process memory info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            status = HealthStatus.HEALTHY
            message = "Memory usage is normal"
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "System memory usage is critically high"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = "System memory usage is high"
            
            # Check if process memory exceeds configured limit
            process_memory_mb = process_memory.rss / (1024 * 1024)
            if process_memory_mb > settings.memory_limit_mb:
                status = HealthStatus.UNHEALTHY
                message = f"Process memory usage exceeds limit ({settings.memory_limit_mb}MB)"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "system_memory_percent": round(memory.percent, 2),
                    "system_memory_available_gb": round(memory.available / (1024**3), 2),
                    "system_memory_total_gb": round(memory.total / (1024**3), 2),
                    "process_memory_mb": round(process_memory_mb, 2),
                    "process_memory_limit_mb": settings.memory_limit_mb,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Memory health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class HealthChecker:
    """Main health checker that orchestrates all health checks."""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.enabled = settings.enable_health_checks
        self._last_results: Dict[str, HealthCheckResult] = {}
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self) -> None:
        """Register default health checks."""
        if not self.enabled:
            return
        
        # Core system checks
        self.register_check(FileSystemHealthCheck())
        self.register_check(MemoryHealthCheck())
        
        # Database checks
        self.register_check(DatabaseHealthCheck())
        self.register_check(VectorDatabaseHealthCheck())
        self.register_check(RedisHealthCheck())
        
        # AI provider checks
        if settings.openai_api_key:
            self.register_check(AIProviderHealthCheck("openai"))
        if settings.anthropic_api_key:
            self.register_check(AIProviderHealthCheck("anthropic"))
    
    def register_check(self, health_check: HealthCheck) -> None:
        """Register a health check."""
        self.checks.append(health_check)
        logger.debug(f"Registered health check: {health_check.name}")
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Health checks are disabled",
                "timestamp": time.time(),
            }
        
        start_time = time.time()
        results = []
        
        # Run all checks concurrently
        tasks = [check.run_check() for check in self.checks]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        overall_status = HealthStatus.HEALTHY
        unhealthy_components = []
        degraded_components = []
        
        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                # Handle exceptions from health checks
                check_name = self.checks[i].name
                result = HealthCheckResult(
                    component=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(result)}",
                    details={"error_type": type(result).__name__},
                )
            
            results.append(result)
            self._last_results[result.component] = result
            
            # Update overall status
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                unhealthy_components.append(result.component)
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
                degraded_components.append(result.component)
        
        duration = time.time() - start_time
        
        # Update metrics
        metrics.set_gauge("health_check_duration_seconds", duration)
        metrics.set_gauge("health_check_components_total", len(results))
        metrics.set_gauge("health_check_unhealthy_components", len(unhealthy_components))
        metrics.set_gauge("health_check_degraded_components", len(degraded_components))
        
        # Create summary
        summary = {
            "status": overall_status.value,
            "message": self._get_summary_message(overall_status, unhealthy_components, degraded_components),
            "timestamp": time.time(),
            "duration_seconds": round(duration, 3),
            "components": {result.component: result.to_dict() for result in results},
            "summary": {
                "total_components": len(results),
                "healthy_components": len([r for r in results if r.status == HealthStatus.HEALTHY]),
                "degraded_components": len(degraded_components),
                "unhealthy_components": len(unhealthy_components),
            },
        }
        
        logger.info(
            f"Health check completed: {overall_status.value}",
            extra={
                "duration_seconds": duration,
                "total_components": len(results),
                "unhealthy_components": unhealthy_components,
                "degraded_components": degraded_components,
            },
        )
        
        return summary
    
    def _get_summary_message(
        self,
        status: HealthStatus,
        unhealthy: List[str],
        degraded: List[str],
    ) -> str:
        """Get a summary message based on health status."""
        if status == HealthStatus.HEALTHY:
            return "All components are healthy"
        elif status == HealthStatus.DEGRADED:
            return f"Some components are degraded: {', '.join(degraded)}"
        else:
            return f"Some components are unhealthy: {', '.join(unhealthy)}"
    
    async def run_check(self, component_name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check by component name."""
        for check in self.checks:
            if check.name == component_name:
                result = await check.run_check()
                self._last_results[component_name] = result
                return result
        return None
    
    def get_last_results(self) -> Dict[str, HealthCheckResult]:
        """Get the last health check results."""
        return self._last_results.copy()
    
    def get_component_status(self, component_name: str) -> Optional[HealthStatus]:
        """Get the status of a specific component."""
        result = self._last_results.get(component_name)
        return result.status if result else None


# Global health checker instance
health_checker = HealthChecker()


# Convenience functions
async def run_health_checks() -> Dict[str, Any]:
    """Run all health checks."""
    return await health_checker.run_all_checks()


async def check_component_health(component_name: str) -> Optional[HealthCheckResult]:
    """Check the health of a specific component."""
    return await health_checker.run_check(component_name)


def get_health_status() -> Dict[str, Any]:
    """Get the current health status without running checks."""
    last_results = health_checker.get_last_results()
    
    if not last_results:
        return {
            "status": "unknown",
            "message": "No health checks have been run yet",
            "timestamp": time.time(),
        }
    
    # Determine overall status from last results
    statuses = [result.status for result in last_results.values()]
    
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY
    
    return {
        "status": overall_status.value,
        "components": {name: result.to_dict() for name, result in last_results.items()},
        "timestamp": time.time(),
    }