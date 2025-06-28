"""
Metrics collection and monitoring for the n8n scraper system.
"""

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, Generator, List, Optional, Union

from config.settings import settings
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Represents a metric value with metadata."""
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


@dataclass
class Counter:
    """A counter metric that only increases."""
    name: str
    description: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the counter."""
        with self._lock:
            self.value += amount
            if labels:
                self.labels.update(labels)
    
    def get(self) -> MetricValue:
        """Get current counter value."""
        return MetricValue(value=self.value, labels=self.labels.copy())


@dataclass
class Gauge:
    """A gauge metric that can increase or decrease."""
    name: str
    description: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set the gauge value."""
        with self._lock:
            self.value = value
            if labels:
                self.labels.update(labels)
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the gauge."""
        with self._lock:
            self.value += amount
            if labels:
                self.labels.update(labels)
    
    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement the gauge."""
        with self._lock:
            self.value -= amount
            if labels:
                self.labels.update(labels)
    
    def get(self) -> MetricValue:
        """Get current gauge value."""
        return MetricValue(value=self.value, labels=self.labels.copy())


@dataclass
class Histogram:
    """A histogram metric for measuring distributions."""
    name: str
    description: str
    buckets: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0])
    counts: Dict[float, int] = field(default_factory=dict)
    sum_value: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    def __post_init__(self):
        """Initialize bucket counts."""
        for bucket in self.buckets:
            self.counts[bucket] = 0
        self.counts[float('inf')] = 0
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value."""
        with self._lock:
            self.sum_value += value
            self.count += 1
            
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self.counts[bucket] += 1
            self.counts[float('inf')] += 1
            
            if labels:
                self.labels.update(labels)
    
    def get(self) -> Dict[str, Any]:
        """Get histogram data."""
        return {
            "buckets": dict(self.counts),
            "sum": self.sum_value,
            "count": self.count,
            "labels": self.labels.copy(),
        }


class MetricsCollector:
    """Central metrics collector for the application."""
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = Lock()
        self._enabled = settings.enable_metrics
        
        # Initialize default metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self) -> None:
        """Initialize default application metrics."""
        # System metrics
        self.register_gauge(
            "system_memory_usage_bytes",
            "Current memory usage in bytes"
        )
        self.register_gauge(
            "system_cpu_usage_percent",
            "Current CPU usage percentage"
        )
        
        # Application metrics
        self.register_counter(
            "http_requests_total",
            "Total number of HTTP requests"
        )
        self.register_counter(
            "http_request_errors_total",
            "Total number of HTTP request errors"
        )
        self.register_histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds"
        )
        
        # Scraping metrics
        self.register_counter(
            "scraping_pages_total",
            "Total number of pages scraped"
        )
        self.register_counter(
            "scraping_errors_total",
            "Total number of scraping errors"
        )
        self.register_histogram(
            "scraping_duration_seconds",
            "Scraping operation duration in seconds"
        )
        
        # Database metrics
        self.register_counter(
            "database_queries_total",
            "Total number of database queries"
        )
        self.register_counter(
            "database_errors_total",
            "Total number of database errors"
        )
        self.register_histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds"
        )
        
        # AI metrics
        self.register_counter(
            "ai_requests_total",
            "Total number of AI requests"
        )
        self.register_counter(
            "ai_errors_total",
            "Total number of AI errors"
        )
        self.register_histogram(
            "ai_request_duration_seconds",
            "AI request duration in seconds"
        )
        self.register_counter(
            "ai_tokens_used_total",
            "Total number of AI tokens used"
        )
    
    def register_counter(
        self,
        name: str,
        description: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """Register a new counter metric."""
        if not self._enabled:
            return Counter(name, description)
        
        with self._lock:
            if name in self._counters:
                return self._counters[name]
            
            counter = Counter(name, description, labels=labels or {})
            self._counters[name] = counter
            logger.debug(f"Registered counter metric: {name}")
            return counter
    
    def register_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """Register a new gauge metric."""
        if not self._enabled:
            return Gauge(name, description)
        
        with self._lock:
            if name in self._gauges:
                return self._gauges[name]
            
            gauge = Gauge(name, description, labels=labels or {})
            self._gauges[name] = gauge
            logger.debug(f"Registered gauge metric: {name}")
            return gauge
    
    def register_histogram(
        self,
        name: str,
        description: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> Histogram:
        """Register a new histogram metric."""
        if not self._enabled:
            return Histogram(name, description)
        
        with self._lock:
            if name in self._histograms:
                return self._histograms[name]
            
            histogram = Histogram(
                name,
                description,
                buckets=buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
                labels=labels or {}
            )
            self._histograms[name] = histogram
            logger.debug(f"Registered histogram metric: {name}")
            return histogram
    
    def get_counter(self, name: str) -> Optional[Counter]:
        """Get a counter by name."""
        return self._counters.get(name)
    
    def get_gauge(self, name: str) -> Optional[Gauge]:
        """Get a gauge by name."""
        return self._gauges.get(name)
    
    def get_histogram(self, name: str) -> Optional[Histogram]:
        """Get a histogram by name."""
        return self._histograms.get(name)
    
    def increment_counter(
        self,
        name: str,
        amount: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric."""
        if not self._enabled:
            return
        
        counter = self.get_counter(name)
        if counter:
            counter.inc(amount, labels)
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set a gauge metric value."""
        if not self._enabled:
            return
        
        gauge = self.get_gauge(name)
        if gauge:
            gauge.set(value, labels)
    
    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Observe a value in a histogram metric."""
        if not self._enabled:
            return
        
        histogram = self.get_histogram(name)
        if histogram:
            histogram.observe(value, labels)
    
    @contextmanager
    def time_operation(
        self,
        histogram_name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Generator[None, None, None]:
        """Context manager to time an operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe_histogram(histogram_name, duration, labels)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics data."""
        if not self._enabled:
            return {}
        
        metrics = {
            "counters": {},
            "gauges": {},
            "histograms": {},
            "timestamp": time.time(),
        }
        
        for name, counter in self._counters.items():
            metrics["counters"][name] = counter.get().to_dict()
        
        for name, gauge in self._gauges.items():
            metrics["gauges"][name] = gauge.get().to_dict()
        
        for name, histogram in self._histograms.items():
            metrics["histograms"][name] = histogram.get()
        
        return metrics
    
    def get_prometheus_format(self) -> str:
        """Get metrics in Prometheus format."""
        if not self._enabled:
            return ""
        
        lines = []
        
        # Counters
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.description}")
            lines.append(f"# TYPE {name} counter")
            metric_value = counter.get()
            labels_str = ",".join([f'{k}="{v}"' for k, v in metric_value.labels.items()])
            if labels_str:
                lines.append(f"{name}{{{labels_str}}} {metric_value.value}")
            else:
                lines.append(f"{name} {metric_value.value}")
        
        # Gauges
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.description}")
            lines.append(f"# TYPE {name} gauge")
            metric_value = gauge.get()
            labels_str = ",".join([f'{k}="{v}"' for k, v in metric_value.labels.items()])
            if labels_str:
                lines.append(f"{name}{{{labels_str}}} {metric_value.value}")
            else:
                lines.append(f"{name} {metric_value.value}")
        
        # Histograms
        for name, histogram in self._histograms.items():
            lines.append(f"# HELP {name} {histogram.description}")
            lines.append(f"# TYPE {name} histogram")
            hist_data = histogram.get()
            labels_str = ",".join([f'{k}="{v}"' for k, v in hist_data["labels"].items()])
            
            # Bucket counts
            for bucket, count in hist_data["buckets"].items():
                bucket_label = f'le="{bucket}"'
                if labels_str:
                    bucket_labels = f"{labels_str},{bucket_label}"
                else:
                    bucket_labels = bucket_label
                lines.append(f"{name}_bucket{{{bucket_labels}}} {count}")
            
            # Sum and count
            if labels_str:
                lines.append(f"{name}_sum{{{labels_str}}} {hist_data['sum']}")
                lines.append(f"{name}_count{{{labels_str}}} {hist_data['count']}")
            else:
                lines.append(f"{name}_sum {hist_data['sum']}")
                lines.append(f"{name}_count {hist_data['count']}")
        
        return "\n".join(lines)
    
    def reset_all_metrics(self) -> None:
        """Reset all metrics to their initial state."""
        with self._lock:
            for counter in self._counters.values():
                counter.value = 0.0
            
            for gauge in self._gauges.values():
                gauge.value = 0.0
            
            for histogram in self._histograms.values():
                histogram.sum_value = 0.0
                histogram.count = 0
                for bucket in histogram.counts:
                    histogram.counts[bucket] = 0
        
        logger.info("All metrics have been reset")


# Global metrics collector instance
metrics = MetricsCollector()


# Convenience functions
def increment_counter(
    name: str,
    amount: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Increment a counter metric."""
    metrics.increment_counter(name, amount, labels)


def set_gauge(
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Set a gauge metric value."""
    metrics.set_gauge(name, value, labels)


def observe_histogram(
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Observe a value in a histogram metric."""
    metrics.observe_histogram(name, value, labels)


def time_operation(
    histogram_name: str,
    labels: Optional[Dict[str, str]] = None,
):
    """Context manager to time an operation."""
    return metrics.time_operation(histogram_name, labels)


# Decorators for automatic metrics collection
def track_requests(metric_name: str = "http_requests_total"):
    """Decorator to track HTTP requests."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            increment_counter(metric_name)
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                increment_counter(f"{metric_name.replace('_total', '_errors_total')}")
                raise
        return wrapper
    return decorator


def track_duration(metric_name: str):
    """Decorator to track function execution duration."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with time_operation(metric_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Alias for backward compatibility
timing_decorator = track_duration