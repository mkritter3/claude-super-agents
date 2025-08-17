#!/usr/bin/env python3
"""
Production-ready metrics collector with Prometheus compatibility.
Provides low-overhead observability for the AET system.
"""
import time
import threading
import json
import psutil
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
from contextlib import contextmanager

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    print("Warning: prometheus_client not available, using fallback metrics")

class MetricsCollector:
    """Production metrics collector with Prometheus integration."""
    
    def __init__(self, enable_prometheus: bool = True):
        self.enabled = True
        self.start_time = time.time()
        self.prometheus_enabled = enable_prometheus and HAS_PROMETHEUS
        
        # Thread-safe storage for fallback metrics
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._gauges = defaultdict(float)
        self._histograms = defaultdict(lambda: deque(maxlen=1000))
        
        # Initialize Prometheus metrics if available
        if self.prometheus_enabled:
            self._init_prometheus_metrics()
        
        # Performance tracking
        self._operation_times = deque(maxlen=100)
        
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        # Task metrics
        self.task_counter = Counter(
            'aet_tasks_total',
            'Total tasks processed by the AET system',
            ['status', 'mode', 'agent']
        )
        
        self.task_duration = Histogram(
            'aet_task_duration_seconds',
            'Time spent processing tasks',
            ['agent', 'mode'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0, float('inf')]
        )
        
        self.active_tasks = Gauge(
            'aet_active_tasks',
            'Currently active tasks',
            ['mode']
        )
        
        # Agent performance metrics
        self.agent_requests = Counter(
            'aet_agent_requests_total',
            'Total requests to agents',
            ['agent', 'operation']
        )
        
        self.agent_response_time = Histogram(
            'aet_agent_response_seconds',
            'Agent response time',
            ['agent', 'operation'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        )
        
        self.agent_errors = Counter(
            'aet_agent_errors_total',
            'Agent errors by type',
            ['agent', 'error_type']
        )
        
        # System resource metrics
        self.cpu_usage = Gauge(
            'aet_cpu_usage_percent',
            'System CPU usage percentage'
        )
        
        self.memory_usage = Gauge(
            'aet_memory_usage_bytes',
            'System memory usage in bytes'
        )
        
        self.disk_usage = Gauge(
            'aet_disk_usage_bytes',
            'Disk usage in bytes',
            ['path']
        )
        
        # File registry metrics
        self.registered_files = Gauge(
            'aet_registered_files_total',
            'Total number of registered files'
        )
        
        self.file_operations = Counter(
            'aet_file_operations_total',
            'File operations performed',
            ['operation', 'status']
        )
        
        # Event log metrics
        self.events_written = Counter(
            'aet_events_total',
            'Total events written to log',
            ['event_type']
        )
        
        self.event_log_size = Gauge(
            'aet_event_log_size_bytes',
            'Size of the event log in bytes'
        )
        
        # Knowledge manager metrics
        self.km_requests = Counter(
            'aet_km_requests_total',
            'Knowledge manager requests',
            ['operation', 'status']
        )
        
        self.km_response_time = Histogram(
            'aet_km_response_seconds',
            'Knowledge manager response time',
            ['operation']
        )
        
        # Business metrics
        self.orchestration_cycles = Counter(
            'aet_orchestration_cycles_total',
            'Total orchestration cycles completed',
            ['result']
        )
        
        self.context_assembly_time = Histogram(
            'aet_context_assembly_seconds',
            'Time spent assembling context'
        )
        
        # System info
        self.system_info = Info(
            'aet_system_info',
            'System information'
        )
        
        # Set system info
        self.system_info.info({
            'version': '1.0.0',
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        })
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1):
        """Increment a counter metric."""
        if not self.enabled:
            return
            
        start = time.time()
        
        try:
            if self.prometheus_enabled and hasattr(self, name):
                metric = getattr(self, name)
                if labels:
                    metric.labels(**labels).inc(value)
                else:
                    metric.inc(value)
            else:
                # Fallback storage
                key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
                with self._lock:
                    self._counters[key] += value
        
        finally:
            self._record_operation_time(time.time() - start)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value."""
        if not self.enabled:
            return
            
        start = time.time()
        
        try:
            if self.prometheus_enabled and hasattr(self, name):
                metric = getattr(self, name)
                if labels:
                    metric.labels(**labels).set(value)
                else:
                    metric.set(value)
            else:
                # Fallback storage
                key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
                with self._lock:
                    self._gauges[key] = value
        
        finally:
            self._record_operation_time(time.time() - start)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation."""
        if not self.enabled:
            return
            
        start = time.time()
        
        try:
            if self.prometheus_enabled and hasattr(self, name):
                metric = getattr(self, name)
                if labels:
                    metric.labels(**labels).observe(value)
                else:
                    metric.observe(value)
            else:
                # Fallback storage
                key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
                with self._lock:
                    self._histograms[key].append(value)
        
        finally:
            self._record_operation_time(time.time() - start)
    
    @contextmanager
    def time_operation(self, operation_name: str, labels: Dict[str, str] = None):
        """Context manager to time operations."""
        start = time.time()
        success = True
        
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start
            
            # Record timing
            if operation_name.endswith('_duration') or operation_name.endswith('_time'):
                self.record_histogram(operation_name, duration, labels)
            
            # Record success/failure
            status_labels = dict(labels or {})
            status_labels['status'] = 'success' if success else 'error'
            
            counter_name = operation_name.replace('_duration', '').replace('_time', '') + '_total'
            if hasattr(self, counter_name):
                self.increment_counter(counter_name, status_labels)
    
    def record_task_metrics(self, agent: str, mode: str, duration: float, success: bool):
        """Record task completion metrics."""
        status = 'success' if success else 'failure'
        
        self.increment_counter('task_counter', {
            'status': status,
            'mode': mode,
            'agent': agent
        })
        
        self.record_histogram('task_duration', duration, {
            'agent': agent,
            'mode': mode
        })
    
    def record_agent_metrics(self, agent: str, operation: str, duration: float, 
                           success: bool, error_type: str = None):
        """Record agent performance metrics."""
        self.increment_counter('agent_requests', {
            'agent': agent,
            'operation': operation
        })
        
        self.record_histogram('agent_response_time', duration, {
            'agent': agent,
            'operation': operation
        })
        
        if not success and error_type:
            self.increment_counter('agent_errors', {
                'agent': agent,
                'error_type': error_type
            })
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.set_gauge('cpu_usage', cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.set_gauge('memory_usage', memory.used)
            
            # Disk usage for workspace
            workspace_path = Path('.claude/workspaces')
            if workspace_path.exists():
                disk_usage = psutil.disk_usage(str(workspace_path))
                self.set_gauge('disk_usage', disk_usage.used, {'path': 'workspaces'})
            
            # Event log size
            event_log_path = Path('.claude/events/event_log.jsonl')
            if event_log_path.exists():
                self.set_gauge('event_log_size', event_log_path.stat().st_size)
                
        except Exception as e:
            # Don't fail if system metrics can't be collected
            pass
    
    def get_performance_impact(self) -> Dict[str, float]:
        """Calculate performance impact of metrics collection."""
        if not self._operation_times:
            return {'avg_overhead_ms': 0.0, 'max_overhead_ms': 0.0}
        
        times_ms = [t * 1000 for t in self._operation_times]
        return {
            'avg_overhead_ms': sum(times_ms) / len(times_ms),
            'max_overhead_ms': max(times_ms),
            'p95_overhead_ms': sorted(times_ms)[int(len(times_ms) * 0.95)]
        }
    
    def _record_operation_time(self, duration: float):
        """Record metrics operation timing for overhead analysis."""
        self._operation_times.append(duration)
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics."""
        if self.prometheus_enabled:
            return generate_latest(REGISTRY)
        else:
            return self._generate_fallback_metrics()
    
    def _generate_fallback_metrics(self) -> str:
        """Generate Prometheus-format metrics from fallback storage."""
        lines = []
        
        with self._lock:
            # Counters
            for key, value in self._counters.items():
                lines.append(f"{key} {value}")
            
            # Gauges
            for key, value in self._gauges.items():
                lines.append(f"{key} {value}")
            
            # Simple histogram summaries
            for key, values in self._histograms.items():
                if values:
                    lines.append(f"{key}_count {len(values)}")
                    lines.append(f"{key}_sum {sum(values)}")
        
        return '\n'.join(lines) + '\n'
    
    def get_health_summary(self) -> Dict:
        """Get a summary for health checks."""
        impact = self.get_performance_impact()
        
        return {
            'metrics_enabled': self.enabled,
            'prometheus_available': self.prometheus_enabled,
            'uptime_seconds': time.time() - self.start_time,
            'performance_impact': impact,
            'healthy': impact['avg_overhead_ms'] < 5.0  # Less than 5ms average overhead
        }
    
    def disable_metrics(self):
        """Disable metrics collection (for emergency situations)."""
        self.enabled = False
    
    def enable_metrics(self):
        """Re-enable metrics collection."""
        self.enabled = True

# Global metrics instance
_metrics_instance = None

def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance

# Convenience functions for common operations
def increment_task_counter(status: str, mode: str, agent: str):
    """Increment task counter."""
    get_metrics().increment_counter('task_counter', {
        'status': status,
        'mode': mode,
        'agent': agent
    })

def record_task_duration(duration: float, agent: str, mode: str):
    """Record task duration."""
    get_metrics().record_histogram('task_duration', duration, {
        'agent': agent,
        'mode': mode
    })

def set_active_tasks(count: int, mode: str):
    """Set active task count."""
    get_metrics().set_gauge('active_tasks', count, {'mode': mode})

def record_agent_call(agent: str, operation: str, duration: float, success: bool, error_type: str = None):
    """Record agent operation metrics."""
    get_metrics().record_agent_metrics(agent, operation, duration, success, error_type)

def record_event(event_type: str):
    """Record event log entry."""
    get_metrics().increment_counter('events_written', {'event_type': event_type})

def record_file_operation(operation: str, success: bool):
    """Record file operation."""
    status = 'success' if success else 'error'
    get_metrics().increment_counter('file_operations', {
        'operation': operation,
        'status': status
    })

if __name__ == "__main__":
    # Test metrics collection
    import sys
    
    collector = MetricsCollector()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Test basic operations
        print("Testing metrics collection...")
        
        # Test counters
        collector.increment_counter('task_counter', {'status': 'success', 'mode': 'simple', 'agent': 'test'})
        
        # Test histograms
        collector.record_histogram('task_duration', 1.5, {'agent': 'test', 'mode': 'simple'})
        
        # Test gauges
        collector.set_gauge('active_tasks', 3, {'mode': 'simple'})
        
        # Test system metrics
        collector.update_system_metrics()
        
        # Show performance impact
        impact = collector.get_performance_impact()
        print(f"Performance impact: {impact}")
        
        # Show health summary
        health = collector.get_health_summary()
        print(f"Health summary: {health}")
        
        print("Metrics test completed successfully!")
    
    else:
        # Output current metrics
        print(collector.get_prometheus_metrics())