"""
Advanced observability and monitoring system for OPERA Cloud MCP.

Provides structured logging, metrics collection, distributed tracing,
and comprehensive monitoring for production hotel operations.
"""

import json
import logging
import operator
import sys
import time
from collections import defaultdict, deque
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Enhanced log levels for hotel operations."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    BUSINESS = "BUSINESS"  # Hotel business events
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"  # Audit trail events


class MetricType(Enum):
    """Types of metrics collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class TraceContext:
    """Distributed tracing context."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    operation_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    error: str | None = None


@dataclass
class Metric:
    """Metric data structure."""

    name: str
    metric_type: MetricType
    value: int | float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)
    hotel_id: str | None = None


@dataclass
class BusinessEvent:
    """Hotel business event for auditing and analytics."""

    event_type: str
    event_name: str
    hotel_id: str
    timestamp: float = field(default_factory=time.time)
    user_id: str | None = None
    reservation_id: str | None = None
    room_number: str | None = None
    guest_id: str | None = None
    amount: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None


class StructuredLogger:
    """
    Production-grade structured logger for OPERA Cloud operations.

    Features:
    - Structured JSON logging
    - Context propagation
    - Business event tracking
    - Performance monitoring
    - PII masking
    """

    def __init__(
        self,
        name: str,
        hotel_id: str | None = None,
        enable_console_output: bool = True,
        log_file_path: str | None = None,
        enable_pii_masking: bool = True,
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            hotel_id: Hotel identifier
            enable_console_output: Output to console
            log_file_path: Optional log file path
            enable_pii_masking: Mask PII data
        """
        self.name = name
        self.hotel_id = hotel_id
        self.enable_pii_masking = enable_pii_masking

        # Context storage for request correlation
        self._context_stack: list[dict[str, Any]] = []

        # PII patterns for masking
        self._pii_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"(\+\d{1,3}\s?)?(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
            "cc_number": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
        }

        # Setup logger
        self.logger = logging.getLogger(name)
        self._setup_handlers(enable_console_output, log_file_path)

    def _create_structured_formatter(self, enable_masking: bool) -> logging.Formatter:
        """Create structured formatter for logging."""

        class StructuredFormatter(logging.Formatter):
            def __init__(
                self,
                hotel_id: str | None,
                enable_masking: bool,
                pii_patterns: dict[str, str],
            ):
                super().__init__()
                self.hotel_id = hotel_id
                self.enable_masking = enable_masking
                self._pii_patterns = pii_patterns

            def format(self, record: logging.LogRecord) -> str:
                # Base log entry
                log_entry = {
                    "timestamp": datetime.now(tz=UTC).isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                    "thread_id": record.thread,
                    "process_id": record.process,
                }

                # Add hotel context
                if self.hotel_id:
                    log_entry["hotel_id"] = self.hotel_id

                # Add trace context if available
                if hasattr(record, "trace_id"):
                    log_entry["trace_id"] = record.trace_id
                if hasattr(record, "span_id"):
                    log_entry["span_id"] = record.span_id

                # Add extra fields
                if hasattr(record, "extra") and record.extra:
                    log_entry.update(record.extra)

                # Add exception info
                if record.exc_info:
                    log_entry["exception"] = {
                        "type": record.exc_info[0].__name__
                        if record.exc_info[0] is not None
                        else "Unknown",
                        "message": str(record.exc_info[1]),
                        "traceback": self.formatException(record.exc_info),
                    }

                # Mask PII if enabled
                if self.enable_masking:
                    log_entry = self._mask_pii(log_entry)

                return json.dumps(log_entry, default=str)

            def _mask_pii(self, data: dict[str, Any]) -> dict[str, Any]:
                """Recursively mask PII in log data."""
                import re

                def mask_string(text: str) -> str:
                    if not isinstance(text, str):
                        return text

                    masked = text
                    # Mask email addresses
                    masked = re.sub(
                        self._pii_patterns["email"], "***@***.***", masked
                    )  # REGEX OK: Standard email pattern for PII masking
                    # Mask phone numbers
                    masked = re.sub(
                        self._pii_patterns["phone"], "***-***-****", masked
                    )  # REGEX OK: Standard phone pattern for PII masking
                    # Mask credit card numbers
                    masked = re.sub(
                        self._pii_patterns["cc_number"], "****-****-****-****", masked
                    )  # REGEX OK: Standard credit card pattern for PII masking
                    # Mask SSN
                    masked = re.sub(
                        self._pii_patterns["ssn"], "***-**-****", masked
                    )  # REGEX OK: Standard SSN pattern for PII masking

                    return masked

                def mask_recursive(obj: Any) -> Any:
                    if isinstance(obj, dict):
                        return {k: mask_recursive(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [mask_recursive(item) for item in obj]
                    elif isinstance(obj, str):
                        return mask_string(obj)
                    return obj

                return mask_recursive(data)  # type: ignore

        return StructuredFormatter(self.hotel_id, enable_masking, self._pii_patterns)

    def _setup_console_handler(self, enable_masking: bool) -> logging.Handler:
        """Setup console handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._create_structured_formatter(enable_masking))
        return console_handler

    def _setup_file_handler(
        self, log_file: str, enable_masking: bool
    ) -> logging.Handler:
        """Setup file handler."""
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(self._create_structured_formatter(enable_masking))
        return file_handler

    def _setup_handlers(self, console: bool, log_file: str | None) -> None:
        """Setup log handlers with structured formatting."""
        # Remove existing handlers
        self.logger.handlers.clear()

        enable_masking = self.enable_pii_masking

        # Console handler
        if console:
            console_handler = self._setup_console_handler(enable_masking)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            file_handler = self._setup_file_handler(log_file, enable_masking)
            self.logger.addHandler(file_handler)

        self.logger.setLevel(logging.DEBUG)

    @contextmanager
    def context(self, **context_data: Any) -> Generator[None]:
        """Add context data to all log entries in this block."""
        self._context_stack.append(context_data)
        try:
            yield
        finally:
            if self._context_stack:
                self._context_stack.pop()

    def _get_current_context(self) -> dict[str, Any]:
        """Get merged context from stack."""
        merged_context = {}
        for context in self._context_stack:
            merged_context.update(context)
        return merged_context

    def log(
        self,
        level: LogLevel,
        message: str,
        trace_context: TraceContext | None = None,
        **extra_data: Any,
    ) -> None:
        """
        Log a structured message.

        Args:
            level: Log level
            message: Log message
            trace_context: Optional trace context
            **extra_data: Additional structured data
        """
        # Merge context
        log_data = self._get_current_context() | extra_data

        # Add trace information
        if trace_context:
            log_data.update(
                {
                    "trace_id": trace_context.trace_id,
                    "span_id": trace_context.span_id,
                    "operation": trace_context.operation_name,
                }
            )

        # Create log record with extra data
        log_record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level.value),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Add extra data as attributes
        log_record.extra = log_data
        if trace_context:
            log_record.trace_id = trace_context.trace_id
            log_record.span_id = trace_context.span_id

        self.logger.handle(log_record)

    def business_event(self, event: BusinessEvent) -> None:
        """Log a business event for auditing and analytics."""
        self.log(
            LogLevel.BUSINESS,
            f"Business Event: {event.event_type}.{event.event_name}",
            event_type=event.event_type,
            event_name=event.event_name,
            hotel_id=event.hotel_id,
            user_id=event.user_id,
            reservation_id=event.reservation_id,
            room_number=event.room_number,
            guest_id=event.guest_id,
            amount=event.amount,
            metadata=event.metadata,
        )


class MetricsCollector:
    """
    High-performance metrics collection for OPERA Cloud operations.

    Features:
    - In-memory aggregation
    - Hotel-specific metrics
    - Time-series data
    - Automatic cleanup
    """

    def __init__(self, hotel_id: str | None = None):
        """
        Initialize metrics collector.

        Args:
            hotel_id: Hotel identifier
        """
        self.hotel_id = hotel_id

        # Metric storage
        self.counters: dict[str, int] = defaultdict(int)
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.timers: dict[str, deque[Any]] = defaultdict(lambda: deque(maxlen=1000))

        # Time series data (last 24 hours)
        self.time_series: dict[str, deque[Any]] = defaultdict(
            lambda: deque(maxlen=1440)
        )  # 1 minute intervals

        # Last cleanup time
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # 1 hour

    def increment(
        self, name: str, value: int = 1, tags: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, tags)
        self.counters[key] += value
        self._record_time_series(key, self.counters[key])

    def set_gauge(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """Set a gauge metric value."""
        key = self._make_key(name, tags)
        self.gauges[key] = value
        self._record_time_series(key, value)

    def record_histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a histogram value."""
        key = self._make_key(name, tags)
        self.histograms[key].append(value)

        # Keep only last 1000 values
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]

    def record_timer(
        self, name: str, duration: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a timer duration."""
        key = self._make_key(name, tags)
        self.timers[key].append({"duration": duration, "timestamp": time.time()})

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None) -> Generator[None]:
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_timer(name, duration, tags)

    def _make_key(self, name: str, tags: dict[str, str] | None) -> str:
        """Create a unique key for metric with tags."""
        key_parts = [name]
        if self.hotel_id:
            key_parts.append(f"hotel:{self.hotel_id}")
        if tags:
            tag_parts = [f"{k}:{v}" for k, v in sorted(tags.items())]
            key_parts.extend(tag_parts)
        return "|".join(key_parts)

    def _record_time_series(self, key: str, value: float) -> None:
        """Record value in time series."""
        now = time.time()
        self.time_series[key].append({"timestamp": now, "value": value})

        # Cleanup if needed
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_data()

    def _cleanup_old_data(self) -> None:
        """Clean up old time series data."""
        cutoff_time = time.time() - 86400  # 24 hours ago

        for key in list(self.time_series.keys()):
            self.time_series[key] = deque(
                [
                    entry
                    for entry in self.time_series[key]
                    if entry["timestamp"] > cutoff_time
                ],
                maxlen=1440,
            )

            # Remove empty series
            if not self.time_series[key]:
                del self.time_series[key]

        self._last_cleanup = time.time()

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all metrics."""
        summary: dict[str, Any] = {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {},
            "timers": {},
            "hotel_id": self.hotel_id,
            "timestamp": time.time(),
        }

        # Summarize histograms
        histograms_summary: dict[str, Any] = summary["histograms"]
        for key, values in self.histograms.items():
            if values:
                histograms_summary[key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": self._percentile(values, 50),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                }
        summary["histograms"] = histograms_summary

        # Summarize timers
        timers_summary: dict[str, Any] = summary["timers"]
        for key, entries in self.timers.items():
            if entries:
                durations = [entry["duration"] for entry in entries]
                timers_summary[key] = {
                    "count": len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "avg": sum(durations) / len(durations),
                    "p50": self._percentile(durations, 50),
                    "p95": self._percentile(durations, 95),
                    "p99": self._percentile(durations, 99),
                }
        summary["timers"] = timers_summary

        return summary

    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


class DistributedTracer:
    """
    Distributed tracing for OPERA Cloud operations.

    Provides request correlation, performance analysis,
    and error tracking across service boundaries.
    """

    def __init__(self, service_name: str, hotel_id: str | None = None):
        """
        Initialize tracer.

        Args:
            service_name: Name of the service
            hotel_id: Hotel identifier
        """
        self.service_name = service_name
        self.hotel_id = hotel_id

        # Active spans storage
        self.active_spans: dict[str, TraceContext] = {}

        # Completed spans for analysis
        self.completed_spans: deque[TraceContext] = deque(maxlen=10000)

        logger.info(
            "Distributed tracer initialized",
            extra={"service_name": service_name, "hotel_id": hotel_id},
        )

    def start_span(
        self,
        operation_name: str,
        parent_span: TraceContext | None = None,
        tags: dict[str, Any] | None = None,
    ) -> TraceContext:
        """
        Start a new trace span.

        Args:
            operation_name: Name of the operation
            parent_span: Parent span context
            tags: Initial tags

        Returns:
            New trace context
        """
        span = TraceContext(
            trace_id=parent_span.trace_id if parent_span else str(uuid4()),
            span_id=str(uuid4()),
            parent_span_id=parent_span.span_id if parent_span else None,
            operation_name=operation_name,
            tags=tags or {},
        )

        # Add service context
        span.tags.update({"service.name": self.service_name, "hotel.id": self.hotel_id})

        self.active_spans[span.span_id] = span
        return span

    def finish_span(self, span: TraceContext, error: Exception | None = None) -> None:
        """
        Finish a trace span.

        Args:
            span: Span to finish
            error: Optional error that occurred
        """
        span.end_time = time.time()
        span.duration = span.end_time - span.start_time

        if error:
            span.status = "error"
            span.error = str(error)
            span.tags["error"] = True
            span.tags["error.type"] = type(error).__name__

        # Move to completed spans
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

        self.completed_spans.append(span)

        logger.debug(
            "Span finished",
            extra={
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "operation": span.operation_name,
                "duration": span.duration,
                "status": span.status,
            },
        )

    @asynccontextmanager
    async def trace(
        self,
        operation_name: str,
        parent_span: TraceContext | None = None,
        tags: dict[str, Any] | None = None,
    ) -> AsyncGenerator[TraceContext]:
        """Async context manager for tracing operations."""
        span = self.start_span(operation_name, parent_span, tags)
        try:
            yield span
        except Exception as e:
            self.finish_span(span, error=e)
            raise
        else:
            self.finish_span(span)

    def get_trace_analysis(self, trace_id: str) -> dict[str, Any] | None:
        """Get analysis of a complete trace."""
        trace_spans = [
            span for span in self.completed_spans if span.trace_id == trace_id
        ]

        if not trace_spans:
            return None

        # Build trace tree and calculate metrics
        root_spans = [span for span in trace_spans if span.parent_span_id is None]
        end_times = [span.end_time for span in trace_spans if span.end_time is not None]
        start_times = [
            span.start_time for span in trace_spans if span.start_time is not None
        ]
        total_duration = (max(end_times) if end_times else 0.0) - (
            min(start_times) if start_times else 0.0
        )

        errors = [span for span in trace_spans if span.status == "error"]

        return {
            "trace_id": trace_id,
            "total_spans": len(trace_spans),
            "total_duration": total_duration,
            "root_spans": len(root_spans),
            "error_count": len(errors),
            "service_breakdown": self._analyze_service_breakdown(trace_spans),
            "critical_path": self._find_critical_path(trace_spans),
            "errors": [
                {
                    "span_id": span.span_id,
                    "operation": span.operation_name,
                    "error": span.error,
                }
                for span in errors
            ],
        }

    def _analyze_service_breakdown(self, spans: list[TraceContext]) -> dict[str, Any]:
        """Analyze service time breakdown."""
        service_times: dict[str, float] = defaultdict(float)
        service_counts: dict[str, int] = defaultdict(int)

        for span in spans:
            service = span.tags.get("service.name", "unknown")
            if span.duration:
                service_times[service] += span.duration
                service_counts[service] += 1

        return {
            service: {
                "total_time": total_time,
                "span_count": service_counts[service],
                "avg_time": total_time / service_counts[service],
            }
            for service, total_time in service_times.items()
        }

    def _find_critical_path(self, spans: list[TraceContext]) -> list[dict[str, Any]]:
        """Find the critical path through the trace."""
        # Simplified critical path - longest sequential path
        spans_by_time = sorted(spans, key=lambda s: s.start_time)

        critical_path = [
            {
                "span_id": span.span_id,
                "operation": span.operation_name,
                "duration": span.duration,
                "service": span.tags.get("service.name"),
            }
            for span in spans_by_time[:10]  # Limit to top 10 spans
        ]

        return critical_path


class ObservabilityManager:
    """
    Comprehensive observability manager for OPERA Cloud MCP.

    Combines structured logging, metrics collection, and distributed tracing
    into a unified observability solution for production hotel operations.
    """

    def __init__(
        self,
        service_name: str = "opera-cloud-mcp",
        hotel_id: str | None = None,
        enable_console_logging: bool = True,
        log_file_path: str | None = None,
    ):
        """
        Initialize observability manager.

        Args:
            service_name: Service name for tracing
            hotel_id: Hotel identifier
            enable_console_logging: Enable console output
            log_file_path: Log file path
        """
        self.service_name = service_name
        self.hotel_id = hotel_id

        # Initialize components
        self.logger = StructuredLogger(
            name=service_name,
            hotel_id=hotel_id,
            enable_console_output=enable_console_logging,
            log_file_path=log_file_path,
        )

        self.metrics = MetricsCollector(hotel_id=hotel_id)
        self.tracer = DistributedTracer(service_name=service_name, hotel_id=hotel_id)

        logger.info(
            "Observability manager initialized",
            extra={
                "service_name": service_name,
                "hotel_id": hotel_id,
                "console_logging": enable_console_logging,
                "log_file": log_file_path,
            },
        )

    def get_health_dashboard(self) -> dict[str, Any]:
        """Get comprehensive health dashboard."""
        metrics_summary = self.metrics.get_metrics_summary()

        # Recent errors from completed spans
        recent_errors = [
            span
            for span in self.tracer.completed_spans
            if span.status == "error"
            and span.end_time is not None
            and (time.time() - span.end_time) < 300
        ]

        # Performance summary
        recent_spans = [
            span
            for span in self.tracer.completed_spans
            if span.end_time is not None and (time.time() - span.end_time) < 3600
        ]

        avg_response_time = 0.0
        if recent_spans:
            total_time = sum(span.duration for span in recent_spans if span.duration)
            avg_response_time = total_time / len(recent_spans)

        return {
            "service": self.service_name,
            "hotel_id": self.hotel_id,
            "timestamp": time.time(),
            "health_status": self._calculate_health_status(recent_errors, recent_spans),
            "metrics": {
                "counters": len(metrics_summary["counters"]),
                "gauges": len(metrics_summary["gauges"]),
                "histograms": len(metrics_summary["histograms"]),
                "timers": len(metrics_summary["timers"]),
            },
            "tracing": {
                "active_spans": len(self.tracer.active_spans),
                "completed_spans": len(self.tracer.completed_spans),
                "recent_errors": len(recent_errors),
                "avg_response_time": avg_response_time,
            },
            "top_operations": self._get_top_operations(),
            "error_summary": self._get_error_summary(recent_errors),
        }

    def _calculate_health_status(
        self, recent_errors: list[TraceContext], recent_spans: list[TraceContext]
    ) -> str:
        """Calculate overall health status."""
        if not recent_spans:
            return "healthy"

        error_rate = len(recent_errors) / len(recent_spans)

        if error_rate < 0.01:  # Less than 1% errors
            return "healthy"
        elif error_rate < 0.05:  # Less than 5% errors
            return "warning"
        return "unhealthy"

    def _get_top_operations(self) -> list[dict[str, Any]]:
        """Get top operations by frequency."""
        operation_counts: dict[str, int] = defaultdict(int)
        operation_durations: dict[str, list[float]] = defaultdict(list)

        for span in self.tracer.completed_spans:
            operation_counts[span.operation_name] += 1
            if span.duration:
                operation_durations[span.operation_name].append(span.duration)

        top_ops = []
        for operation, count in sorted(
            operation_counts.items(), key=operator.itemgetter(1), reverse=True
        )[:10]:
            durations = operation_durations[operation]
            avg_duration = sum(durations) / len(durations) if durations else 0

            top_ops.append(
                {"operation": operation, "count": count, "avg_duration": avg_duration}
            )

        return top_ops

    def _get_error_summary(self, recent_errors: list[TraceContext]) -> dict[str, Any]:
        """Get summary of recent errors."""
        error_types: dict[str, int] = defaultdict(int)
        error_operations: dict[str, int] = defaultdict(int)

        for error_span in recent_errors:
            error_type = error_span.tags.get("error.type", "unknown")
            error_types[error_type] += 1
            error_operations[error_span.operation_name] += 1

        return {
            "total_errors": len(recent_errors),
            "by_type": error_types.copy(),
            "by_operation": error_operations.copy(),
        }


# Global observability instance
_observability: ObservabilityManager | None = None


def get_observability() -> ObservabilityManager:
    """Get the global observability manager."""
    if _observability is None:
        raise RuntimeError(
            "Observability not initialized. Call initialize_observability() first."
        )
    return _observability


def initialize_observability(
    service_name: str = "opera-cloud-mcp",
    hotel_id: str | None = None,
    enable_console_logging: bool = True,
    log_file_path: str | None = None,
) -> ObservabilityManager:
    """Initialize the global observability manager."""
    global _observability

    if _observability is not None:
        logger.warning("Observability already initialized, replacing existing instance")

    _observability = ObservabilityManager(
        service_name=service_name,
        hotel_id=hotel_id,
        enable_console_logging=enable_console_logging,
        log_file_path=log_file_path,
    )

    return _observability
