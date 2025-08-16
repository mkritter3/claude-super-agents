# Phase 0 Critical Fixes - Test Suite

This directory contains comprehensive tests for the Phase 0 critical fixes implemented in the AET system upgrade.

## Phase 0 Implementations

### 1. Circuit Breakers & Retry Strategy
- **File**: `context_assembler.py`
- **Purpose**: Prevent cascade failures when Knowledge Manager is unavailable
- **Features**:
  - Circuit breaker with 3 failure threshold, 30s recovery timeout
  - Retry strategy with exponential backoff
  - Graceful degradation to fallback context

### 2. Structured Logging
- **File**: `logger_config.py` (NEW)
- **Purpose**: Replace all print() statements with JSON structured logging
- **Features**:
  - JSON formatted log output
  - Contextual logging with ticket_id, job_id, agent, component
  - Performance and system event logging utilities
  - Multiple log handlers (console, file, error file)

### 3. Fallback Context Generation
- **File**: `context_assembler.py` (enhanced)
- **Purpose**: Provide functional context when KM is unavailable
- **Features**:
  - Cached fallback context with 1-hour TTL
  - Agent-specific fallback strategies
  - Fast generation (< 100ms)
  - System continues to function without KM

### 4. Production KM Deployment
- **File**: `.claude/scripts/deploy_km.sh` (NEW)
- **Purpose**: Deploy KM with Gunicorn for production load
- **Features**:
  - 4 workers for concurrent handling
  - Proper timeout and logging configuration
  - Health checks and performance testing
  - Start/stop/restart/status commands

## Test Files

### `test_circuit_breaker.py`
Tests the circuit breaker integration in context assembler:
- Circuit breaker initialization and state management
- Failure threshold triggering
- Recovery after timeout
- End-to-end context assembly with KM failures

### `test_structured_logging.py`
Tests the structured logging implementation:
- JSON formatter functionality
- Contextual logger with ticket/job/agent context
- Log output validation
- Performance and system event logging

### `test_fallback_context.py`
Tests fallback context generation:
- Fallback context structure and completeness
- Caching behavior and performance
- Integration with full context assembly
- Performance characteristics

### `test_km_load.py`
Load tests for Knowledge Manager server:
- Single request performance baseline
- Concurrent request handling (10 workers, 100 requests)
- Sustained load testing (30 seconds @ 20 RPS)
- POST request performance with realistic payloads
- Memory stability under load

### `run_phase0_tests.py`
Comprehensive test runner that:
- Checks prerequisites (KM server, dependencies)
- Runs all test suites
- Generates detailed JSON report
- Provides implementation checklist
- Returns appropriate exit codes

## Running Tests

### Prerequisites
```bash
# Install required packages
pip install pytest requests

# Start Knowledge Manager (for load tests)
cd .claude/scripts
./deploy_km.sh start
```

### Run All Tests
```bash
cd .claude/tests/phase0
python run_phase0_tests.py
```

### Run Individual Test Suites
```bash
# Circuit breaker tests
pytest test_circuit_breaker.py -v

# Structured logging tests
pytest test_structured_logging.py -v

# Fallback context tests
pytest test_fallback_context.py -v

# KM load tests (requires running KM server)
pytest test_km_load.py -v -s
```

## Expected Results

### Success Criteria
- **Circuit Breaker**: Prevents cascade failures, opens after 3 failures, recovers after 30s
- **Structured Logging**: All logs output as valid JSON with required fields
- **Fallback Context**: System continues functioning when KM unavailable, < 100ms generation
- **KM Load**: Handles 100+ req/s, < 1s average response time, 95%+ success rate
- **Deployment**: Script successfully starts/stops KM server

### Performance Targets
- Fallback context generation: < 100ms
- KM server throughput: > 100 req/s
- KM server response time: < 1s average, < 2s P95
- Circuit breaker overhead: negligible
- Log output: valid JSON for all messages

## Integration with Main System

The Phase 0 fixes are integrated into the existing AET system:

1. **Context Assembler**: Enhanced with circuit breakers and fallback
2. **Orchestrator**: Updated to use structured logging
3. **Event Logger**: Updated to use structured logging
4. **Reliability Module**: Updated to use structured logging
5. **KM Server**: Deployable with production configuration

## Troubleshooting

### Common Issues

1. **KM Server Not Starting**
   ```bash
   # Check if port is in use
   lsof -i :5001
   
   # Check deployment script logs
   tail -f logs/km_error.log
   ```

2. **Import Errors in Tests**
   ```bash
   # Ensure you're in the correct directory
   cd claude-super-agents/.claude/tests/phase0
   
   # Check Python path
   export PYTHONPATH="../../system:$PYTHONPATH"
   ```

3. **Circuit Breaker Not Working**
   - Verify KM server is actually down
   - Check circuit breaker state in logs
   - Confirm failure threshold is reached

4. **Log Format Issues**
   - Verify logger_config.py is importable
   - Check that StructuredFormatter is being used
   - Validate JSON output with `jq` tool

## Next Steps

After Phase 0 tests pass:
1. Deploy to staging environment
2. Monitor structured logs for issues
3. Verify KM server performance under real load
4. Proceed to Phase 1 implementation

## Files Modified

- `context_assembler.py`: Added circuit breakers, fallback context
- `orchestrator.py`: Replaced print() with structured logging
- `event_logger.py`: Added structured logging
- `reliability.py`: Replaced print() with structured logging
- `logger_config.py`: NEW - Structured logging implementation
- `deploy_km.sh`: NEW - Production KM deployment script