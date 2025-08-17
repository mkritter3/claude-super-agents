#!/usr/bin/env python3
"""
OpenTelemetry tracing configuration for the AET system.
Provides distributed tracing with minimal performance impact.
"""
import os
import time
import threading
from contextlib import contextmanager
from typing import Dict, Optional, Any
from functools import wraps

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.console import ConsoleSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
    from opentelemetry.trace import Status, StatusCode
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    print("Warning: OpenTelemetry not available, using fallback tracing")

class TracingConfig:
    """Configuration and management for OpenTelemetry tracing."""
    
    def __init__(self, service_name: str = 'aet-system', enable_tracing: bool = True):
        self.service_name = service_name
        self.enabled = enable_tracing and HAS_OPENTELEMETRY
        self.tracer = None
        
        # Fallback span storage for when OpenTelemetry is not available
        self._fallback_spans = []
        self._fallback_lock = threading.Lock()
        
        if self.enabled:
            self._setup_tracing()
        else:
            self._setup_fallback_tracer()
    
    def _setup_tracing(self):
        """Set up OpenTelemetry tracing."""
        # Create resource with service information
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development")
        })
        
        # Set up tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Configure exporters
        self._setup_exporters(provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(self.service_name)
        
        # Auto-instrument common libraries
        self._setup_auto_instrumentation()
    
    def _setup_exporters(self, provider):
        """Set up trace exporters."""
        # OTLP exporter for production (e.g., Jaeger, Zipkin)
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter, max_queue_size=2048, max_export_batch_size=512)
            )
        
        # Console exporter for development
        if os.getenv("OTEL_EXPORTER_CONSOLE", "false").lower() == "true":
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(SimpleSpanProcessor(console_exporter))
        
        # If no exporters configured, use a minimal batch processor to avoid memory leaks
        if not otlp_endpoint and os.getenv("OTEL_EXPORTER_CONSOLE", "false").lower() != "true":
            # No-op exporter that discards spans
            from opentelemetry.sdk.trace.export import SpanExporter
            
            class NoOpExporter(SpanExporter):
                def export(self, spans):
                    return trace.SpanExportResult.SUCCESS
                
                def shutdown(self):
                    return True
            
            provider.add_span_processor(BatchSpanProcessor(NoOpExporter()))
    
    def _setup_auto_instrumentation(self):
        """Set up automatic instrumentation for common libraries."""
        try:
            # Instrument requests library if available
            RequestsInstrumentor().instrument()
        except Exception:
            pass
        
        try:
            # Instrument SQLite if available
            SQLite3Instrumentor().instrument()
        except Exception:
            pass
    
    def _setup_fallback_tracer(self):
        """Set up fallback tracer when OpenTelemetry is not available."""
        self.tracer = FallbackTracer(self._fallback_spans, self._fallback_lock)
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Dict[str, Any] = None):
        """Context manager for tracing operations."""
        if not self.enabled or not self.tracer:
            # No-op if tracing disabled
            yield None
            return
        
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                if hasattr(span, 'set_status'):
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                if hasattr(span, 'record_exception'):
                    span.record_exception(e)
                raise
    
    def trace_function(self, operation_name: str = None, attributes: Dict[str, Any] = None):
        """Decorator for tracing functions."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or f"{func.__module__}.{func.__name__}"
                attrs = dict(attributes or {})
                attrs.update({
                    'function.name': func.__name__,
                    'function.module': func.__module__
                })
                
                with self.trace_operation(name, attrs) as span:
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def add_event(self, span, event_name: str, attributes: Dict[str, Any] = None):
        """Add an event to the current span."""
        if span and hasattr(span, 'add_event'):
            span.add_event(event_name, attributes or {})
    
    def set_attribute(self, span, key: str, value: Any):
        """Set an attribute on the current span."""
        if span and hasattr(span, 'set_attribute'):
            span.set_attribute(key, str(value))
    
    def get_trace_id(self, span) -> Optional[str]:
        """Get the trace ID from a span."""
        if span and hasattr(span, 'get_span_context'):
            context = span.get_span_context()
            if hasattr(context, 'trace_id'):
                return f"{context.trace_id:032x}"
        return None
    
    def get_span_id(self, span) -> Optional[str]:
        """Get the span ID from a span."""
        if span and hasattr(span, 'get_span_context'):
            context = span.get_span_context()
            if hasattr(context, 'span_id'):
                return f"{context.span_id:016x}"
        return None
    
    def get_tracing_headers(self) -> Dict[str, str]:
        """Get headers for trace context propagation."""
        if not self.enabled:
            return {}
        
        try:
            from opentelemetry.propagate import inject
            headers = {}
            inject(headers)
            return headers
        except Exception:
            return {}
    
    def extract_trace_context(self, headers: Dict[str, str]):
        """Extract trace context from headers."""
        if not self.enabled:
            return
        
        try:
            from opentelemetry.propagate import extract
            return extract(headers)
        except Exception:
            return None
    
    def get_health_info(self) -> Dict[str, Any]:
        """Get tracing health information."""
        return {
            'tracing_enabled': self.enabled,
            'opentelemetry_available': HAS_OPENTELEMETRY,
            'service_name': self.service_name,
            'fallback_spans_count': len(self._fallback_spans) if not self.enabled else 0
        }
    
    def shutdown(self):
        """Shutdown tracing and flush remaining spans."""
        if self.enabled:
            try:
                provider = trace.get_tracer_provider()
                if hasattr(provider, 'shutdown'):
                    provider.shutdown()
            except Exception:
                pass

class FallbackTracer:
    """Fallback tracer implementation when OpenTelemetry is not available."""
    
    def __init__(self, spans_storage, lock):
        self.spans_storage = spans_storage
        self.lock = lock
    
    @contextmanager
    def start_as_current_span(self, name: str):
        """Create a fallback span context."""
        span = FallbackSpan(name, self.spans_storage, self.lock)
        try:
            yield span
        finally:
            span.end()

class FallbackSpan:
    """Fallback span implementation."""
    
    def __init__(self, name: str, storage, lock):
        self.name = name
        self.storage = storage
        self.lock = lock
        self.start_time = time.time()
        self.attributes = {}
        self.events = []
        self.status = "OK"
    
    def set_attribute(self, key: str, value: str):
        """Set span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        """Add span event."""
        self.events.append({
            'name': name,
            'timestamp': time.time(),
            'attributes': attributes or {}
        })
    
    def set_status(self, status):
        """Set span status."""
        if hasattr(status, 'status_code'):
            self.status = "ERROR" if status.status_code == StatusCode.ERROR else "OK"
        else:
            self.status = str(status)
    
    def record_exception(self, exception):
        """Record an exception."""
        self.add_event("exception", {
            'exception.type': type(exception).__name__,
            'exception.message': str(exception)
        })
    
    def end(self):
        """End the span."""
        end_time = time.time()
        duration = end_time - self.start_time
        
        span_data = {
            'name': self.name,
            'start_time': self.start_time,
            'end_time': end_time,
            'duration': duration,
            'attributes': self.attributes,
            'events': self.events,
            'status': self.status
        }
        
        with self.lock:
            self.storage.append(span_data)
            # Keep only recent spans to avoid memory growth
            if len(self.storage) > 1000:
                self.storage.pop(0)

# Global tracing instance
_tracing_instance = None

def get_tracer(service_name: str = None) -> TracingConfig:
    """Get the global tracing configuration."""
    global _tracing_instance
    if _tracing_instance is None:
        _tracing_instance = TracingConfig(service_name or 'aet-system')
    return _tracing_instance

def trace_operation(operation_name: str, attributes: Dict[str, Any] = None):
    """Convenience function for tracing operations."""
    return get_tracer().trace_operation(operation_name, attributes)

def trace_function(operation_name: str = None, attributes: Dict[str, Any] = None):
    """Convenience decorator for tracing functions."""
    return get_tracer().trace_function(operation_name, attributes)

# Common operation tracers
def trace_agent_operation(agent_name: str, operation: str):
    """Trace agent operations."""
    return trace_operation(f"agent.{operation}", {
        'agent.name': agent_name,
        'agent.operation': operation
    })

def trace_file_operation(operation: str, file_path: str = None):
    """Trace file operations."""
    attributes = {'file.operation': operation}
    if file_path:
        attributes['file.path'] = file_path
    return trace_operation(f"file.{operation}", attributes)

def trace_db_operation(operation: str, table: str = None):
    """Trace database operations."""
    attributes = {'db.operation': operation}
    if table:
        attributes['db.table'] = table
    return trace_operation(f"db.{operation}", attributes)

def trace_orchestration_cycle(mode: str, ticket_id: str = None):
    """Trace orchestration cycles."""
    attributes = {'orchestration.mode': mode}
    if ticket_id:
        attributes['orchestration.ticket_id'] = ticket_id
    return trace_operation("orchestration.cycle", attributes)

if __name__ == "__main__":
    # Test tracing setup
    import sys
    
    tracer = TracingConfig()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Testing tracing configuration...")
        
        # Test basic tracing
        with tracer.trace_operation("test_operation", {"test": "true"}) as span:
            time.sleep(0.1)  # Simulate work
            tracer.add_event(span, "test_event", {"event_data": "test"})
        
        # Test function decorator
        @tracer.trace_function("test_function", {"function": "test"})
        def test_function():
            time.sleep(0.05)
            return "test_result"
        
        result = test_function()
        
        # Test health info
        health = tracer.get_health_info()
        print(f"Tracing health: {health}")
        
        print("Tracing test completed successfully!")
        tracer.shutdown()
    
    else:
        health = tracer.get_health_info()
        print(f"Tracing configuration: {health}")