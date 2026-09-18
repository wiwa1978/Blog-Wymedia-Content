"""Add a privacy-conscious custom span around application work."""
from importlib import import_module

from opentelemetry import trace

configure_tracing = import_module("01_configure_tracing").configure_tracing


def retrieve_customer_context(customer_id: str) -> dict:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("retrieve_customer_context") as span:
        span.set_attribute("customer.id_hash", str(hash(customer_id)))
        result = {"record_count": 1}
        span.set_attribute("result.record_count", result["record_count"])
        return result


if __name__ == "__main__":
    configure_tracing()
    print(retrieve_customer_context("demo-customer"))
