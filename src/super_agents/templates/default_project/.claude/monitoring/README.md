# AET Observability and Monitoring

This directory contains the complete observability stack for the Autonomous Engineering Team (AET) system, providing production-ready monitoring, alerting, and performance insights.

## 🎯 Overview

Phase 4 implements comprehensive observability with:
- **Prometheus-compatible metrics** for monitoring system health
- **OpenTelemetry distributed tracing** for request flow analysis
- **Health endpoints** for service discovery and health checks
- **Grafana dashboards** for visual monitoring
- **Performance impact monitoring** with <5% overhead

## 📊 Components

### 1. Metrics Collection (`metrics_collector.py`)
- **Prometheus-compatible** metrics with fallback support
- **Thread-safe** operation with minimal performance impact
- **Business metrics**: task success rates, agent performance, system health
- **Technical metrics**: response times, resource usage, error rates
- **Custom metrics**: orchestration cycles, context assembly time

#### Key Metrics:
```
aet_tasks_total                    # Total tasks processed
aet_task_duration_seconds          # Task processing time
aet_active_tasks                   # Currently active tasks
aet_agent_requests_total           # Agent operation requests
aet_agent_response_seconds         # Agent response times
aet_cpu_usage_percent             # System CPU usage
aet_memory_usage_bytes            # Memory consumption
aet_events_total                  # Event log entries
```

### 2. Distributed Tracing (`tracing_config.py`)
- **OpenTelemetry integration** with OTLP export support
- **Context propagation** across service boundaries
- **Fallback tracing** when OpenTelemetry unavailable
- **Automatic instrumentation** for common libraries
- **Performance tracking** with span timing

#### Trace Operations:
- Agent execution flows
- File operations and registry updates
- Database transactions
- Orchestration cycles
- Knowledge manager operations

### 3. Health Endpoints (`km_server.py` enhancements)
- `/health` - Basic health check with database connectivity
- `/ready` - Comprehensive readiness probe
- `/metrics` - Prometheus metrics endpoint
- `/status` - Detailed system status and statistics

### 4. Grafana Dashboards (`dashboards/`)
- **System Overview**: High-level system health and performance
- **Agent Performance**: Per-agent metrics and comparisons
- **Error Tracking**: Error rates, types, and recovery times
- **Resource Usage**: CPU, memory, disk, and efficiency metrics

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Core observability
pip install prometheus_client psutil

# Optional: Full OpenTelemetry support
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

# Optional: Auto-instrumentation
pip install opentelemetry-instrumentation-requests opentelemetry-instrumentation-sqlite3
```

### 2. Enable Observability
```python
from metrics_collector import get_metrics, record_task_duration
from tracing_config import trace_operation

# Record metrics
metrics = get_metrics()
metrics.increment_counter('my_counter', {'label': 'value'})

# Trace operations
with trace_operation('my_operation', {'operation_id': '123'}):
    # Your code here
    pass
```

### 3. Start Knowledge Manager with Health Endpoints
```bash
cd .claude/system
python km_server.py
```

Access endpoints:
- Health: http://localhost:5001/health
- Ready: http://localhost:5001/ready
- Metrics: http://localhost:5001/metrics
- Status: http://localhost:5001/status

### 4. Import Grafana Dashboards
Import JSON files from `dashboards/` into your Grafana instance:
1. System Overview (`system-overview.json`)
2. Agent Performance (`agent-performance.json`)
3. Error Tracking (`error-tracking.json`)
4. Resource Usage (`resource-usage.json`)

## 📈 Performance Impact

The observability layer is designed for minimal overhead:

| Component | Average Overhead | Target |
|-----------|------------------|---------|
| Metrics Collection | <1ms per operation | <5ms |
| Distributed Tracing | <2ms per span | <10ms |
| Health Endpoints | <10ms response | <100ms |
| Combined Impact | <5% total overhead | <5% |

### Performance Monitoring
Monitor observability overhead with:
```python
from metrics_collector import get_metrics

metrics = get_metrics()
impact = metrics.get_performance_impact()
print(f"Average overhead: {impact['avg_overhead_ms']}ms")
```

## 🛠️ Configuration

### Environment Variables
```bash
# OpenTelemetry Configuration
export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:14250
export OTEL_EXPORTER_CONSOLE=true  # Development only
export ENVIRONMENT=production

# Service Configuration
export AET_METRICS_ENABLED=true
export AET_TRACING_ENABLED=true
```

### Metrics Configuration
```python
from metrics_collector import MetricsCollector

# Create with custom settings
collector = MetricsCollector(enable_prometheus=True)

# Disable for emergency situations
collector.disable_metrics()

# Re-enable
collector.enable_metrics()
```

### Tracing Configuration
```python
from tracing_config import TracingConfig

# Custom service name
tracer = TracingConfig(service_name='my-aet-service')

# Disable tracing
tracer = TracingConfig(enable_tracing=False)
```

## 🔍 Monitoring Best Practices

### 1. Metrics Strategy
- **RED Method**: Rate, Errors, Duration for requests
- **USE Method**: Utilization, Saturation, Errors for resources
- **Business Metrics**: Task completion rates, agent efficiency
- **SLI/SLO Tracking**: Service level indicators and objectives

### 2. Alerting Rules
Create alerts for:
- High error rates (>5% task failures)
- Long response times (>95th percentile thresholds)
- Resource exhaustion (CPU >80%, Memory >80%)
- Service unavailability (health check failures)

### 3. Dashboard Design
- **At-a-glance overview** with key health indicators
- **Drill-down capability** from high-level to detailed views
- **Time-based analysis** with appropriate time ranges
- **Comparative analysis** across agents and modes

### 4. Trace Analysis
- **Request flow visualization** across system components
- **Performance bottleneck identification** in critical paths
- **Error propagation tracking** through the system
- **Dependency mapping** between services

## 🧪 Testing

Run comprehensive observability tests:
```bash
cd .claude/tests/phase4
python run_all_tests.py
```

Test categories:
- **Metrics Collection**: Counter, gauge, histogram functionality
- **Tracing Configuration**: Span creation, context propagation
- **Health Endpoints**: Connectivity, response format validation
- **Performance Impact**: Overhead measurement and validation

## 📝 Troubleshooting

### Common Issues

1. **High Observability Overhead**
   ```python
   # Check performance impact
   from metrics_collector import get_metrics
   impact = get_metrics().get_performance_impact()
   
   # Disable if necessary
   get_metrics().disable_metrics()
   ```

2. **Missing Dependencies**
   ```bash
   # Install optional components
   pip install prometheus_client
   pip install opentelemetry-api
   pip install psutil
   ```

3. **Health Endpoint Failures**
   - Check database connectivity
   - Verify file system permissions
   - Ensure sufficient resources

4. **Metrics Not Appearing**
   - Verify Prometheus scraping configuration
   - Check metrics endpoint accessibility
   - Validate metric naming conventions

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔧 Integration Examples

### Kubernetes Deployment
```yaml
# Service Monitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: aet-metrics
spec:
  selector:
    matchLabels:
      app: aet-system
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### Docker Compose
```yaml
version: '3.8'
services:
  aet-system:
    build: .
    ports:
      - "5001:5001"
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:14250
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=5001"
      - "prometheus.io/path=/metrics"
```

### Prometheus Configuration
```yaml
scrape_configs:
  - job_name: 'aet-system'
    static_configs:
      - targets: ['localhost:5001']
    scrape_interval: 30s
    metrics_path: /metrics
```

## 📚 Additional Resources

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/best-practices/)
- [SRE Monitoring Principles](https://sre.google/sre-book/monitoring-distributed-systems/)

## 🎯 Future Enhancements

Planned improvements:
- **Anomaly detection** with machine learning
- **Automated alerting** with intelligent thresholds
- **Cost optimization** metrics and recommendations
- **Security monitoring** with audit trails
- **Custom metrics SDK** for agent-specific monitoring