import logging
import os

logger = logging.getLogger(__name__)


def configure_telemetry(app=None) -> None:
    """Instrumenta FastAPI con OpenTelemetry.

    Sin exporter OTLP configurado la app arranca normalmente.
    Activar con OTEL_EXPORTER_OTLP_ENDPOINT en el entorno.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()

        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )

        trace.set_tracer_provider(provider)

        if app is not None:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)

    except ImportError:
        logger.warning("opentelemetry packages not installed; skipping telemetry setup")
