"""Configure local or Application Insights OpenTelemetry exporters."""
import os
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING", "true")

from azure.ai.projects.telemetry import AIProjectInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from azure.monitor.opentelemetry import configure_azure_monitor


def configure_tracing() -> None:
    provider = TracerProvider()
    connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection:
        configure_azure_monitor(connection_string=connection)
    else:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        print("Using console spans; configure Application Insights for cloud export")
    AIProjectInstrumentor().instrument()


if __name__ == "__main__":
    configure_tracing()
    print("Tracing configured")
