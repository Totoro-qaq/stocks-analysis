from __future__ import annotations

import logging
import os
from contextlib import nullcontext
from typing import Any

logger = logging.getLogger(__name__)

_tracing_configured = False
_metrics_configured = False
_common_instrumented = False
_celery_instrumented = False
_pipeline_step_duration: Any | None = None
_pipeline_step_counter: Any | None = None


class _NoopSpan:
    def set_attribute(self, name: str, value: Any) -> None:
        return None

    def record_exception(self, exception: BaseException) -> None:
        return None

    def set_status(self, status: Any) -> None:
        return None


class _NoopTracer:
    def start_as_current_span(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return nullcontext(_NoopSpan())


def _is_otel_enabled() -> bool:
    return os.getenv("OTEL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _service_name() -> str:
    return os.getenv("OTEL_SERVICE_NAME", "stocks-backend").strip() or "stocks-backend"


def _otlp_endpoint() -> str:
    return os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317").strip()


def _resource() -> Any:
    from opentelemetry.sdk.resources import Resource

    return Resource.create(
        {
            "service.name": _service_name(),
            "deployment.environment": os.getenv("APP_ENV", "local"),
        }
    )


def _configure_tracing() -> None:
    global _tracing_configured
    if _tracing_configured or not _is_otel_enabled():
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        logger.warning("OpenTelemetry tracing is disabled: %s", exc)
        return

    provider = TracerProvider(resource=_resource())
    exporter = OTLPSpanExporter(endpoint=_otlp_endpoint(), insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracing_configured = True


def _configure_metrics() -> None:
    global _metrics_configured, _pipeline_step_counter, _pipeline_step_duration
    if _metrics_configured or not _is_otel_enabled():
        return

    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    except ImportError as exc:
        logger.warning("OpenTelemetry metrics are disabled: %s", exc)
        return

    exporter = OTLPMetricExporter(endpoint=_otlp_endpoint(), insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15_000)
    provider = MeterProvider(resource=_resource(), metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter("stocks.pipeline")
    _pipeline_step_duration = meter.create_histogram(
        name="pipeline_step_duration_seconds",
        unit="s",
        description="Duration of each pipeline step.",
    )
    _pipeline_step_counter = meter.create_counter(
        name="pipeline_step_runs",
        unit="1",
        description="Number of pipeline step executions.",
    )
    _metrics_configured = True


def _instrument_common_clients() -> None:
    global _common_instrumented
    if _common_instrumented or not _is_otel_enabled():
        return

    instrumentors = [
        ("requests", "opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
        ("redis", "opentelemetry.instrumentation.redis", "RedisInstrumentor"),
        ("pymysql", "opentelemetry.instrumentation.pymysql", "PyMySQLInstrumentor"),
    ]
    for label, module_name, class_name in instrumentors:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)().instrument()
        except ImportError as exc:
            logger.debug("OpenTelemetry %s instrumentation is unavailable: %s", label, exc)
        except Exception as exc:
            logger.debug("OpenTelemetry %s instrumentation skipped: %s", label, exc)

    _common_instrumented = True


def configure_fastapi_observability(app: Any) -> None:
    if not _is_otel_enabled():
        return

    _configure_tracing()
    _configure_metrics()
    _instrument_common_clients()

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except ImportError as exc:
        logger.warning("FastAPI OpenTelemetry instrumentation is disabled: %s", exc)
    except Exception as exc:
        logger.debug("FastAPI OpenTelemetry instrumentation skipped: %s", exc)


def configure_celery_observability(celery_app: Any) -> None:
    global _celery_instrumented
    if not _is_otel_enabled():
        return

    _configure_tracing()
    _configure_metrics()
    _instrument_common_clients()

    if _celery_instrumented:
        return

    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
        _celery_instrumented = True
    except ImportError as exc:
        logger.warning("Celery OpenTelemetry instrumentation is disabled: %s", exc)
    except Exception as exc:
        logger.debug("Celery OpenTelemetry instrumentation skipped: %s", exc)


def get_tracer(name: str) -> Any:
    if not _is_otel_enabled():
        return _NoopTracer()

    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return _NoopTracer()


def set_span_error(span: Any, exception: BaseException) -> None:
    try:
        from opentelemetry.trace import Status, StatusCode

        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))
    except Exception:
        return


def record_pipeline_step(step_name: str, duration_seconds: float, status: str) -> None:
    if not _is_otel_enabled():
        return

    _configure_metrics()
    attributes = {"step": step_name, "status": status}

    try:
        if _pipeline_step_duration is not None:
            _pipeline_step_duration.record(max(duration_seconds, 0.0), attributes=attributes)
        if _pipeline_step_counter is not None:
            _pipeline_step_counter.add(1, attributes=attributes)
    except Exception as exc:
        logger.debug("Pipeline metric recording skipped: %s", exc)
