#!/bin/bash
# Production deployment script for Knowledge Manager
# Target: Handle 100 req/s with proper logging and timeout settings

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
AET_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOGS_DIR="$AET_ROOT/logs"
SYSTEM_DIR="$AET_ROOT/.claude/system"
PID_FILE="$AET_ROOT/.claude/km.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check if gunicorn is installed
    if ! command -v gunicorn &> /dev/null; then
        log_info "Installing gunicorn..."
        pip install gunicorn
    fi
    
    # Check if km_server.py exists
    if [ ! -f "$SYSTEM_DIR/km_server.py" ]; then
        log_error "km_server.py not found at $SYSTEM_DIR/km_server.py"
        exit 1
    fi
    
    log_info "Dependencies check complete"
}

setup_directories() {
    log_info "Setting up directories..."
    
    # Create logs directory
    mkdir -p "$LOGS_DIR"
    
    # Create .claude directory if it doesn't exist
    mkdir -p "$AET_ROOT/.claude"
    
    log_info "Directories setup complete"
}

stop_existing_km() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        log_info "Stopping existing KM server (PID: $pid)..."
        
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid"
            sleep 5
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "Force killing KM server..."
                kill -KILL "$pid"
            fi
        fi
        
        rm -f "$PID_FILE"
    fi
}

start_km_server() {
    log_info "Starting Knowledge Manager server..."
    
    cd "$SYSTEM_DIR"
    
    # Start gunicorn with production settings
    gunicorn \
        --workers 4 \
        --bind 127.0.0.1:5001 \
        --timeout 120 \
        --keep-alive 10 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
        --worker-class sync \
        --worker-connections 1000 \
        --access-logfile "$LOGS_DIR/km_access.log" \
        --error-logfile "$LOGS_DIR/km_error.log" \
        --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s' \
        --log-level info \
        --capture-output \
        --enable-stdio-inheritance \
        --daemon \
        --pid "$PID_FILE" \
        km_server:app
    
    if [ $? -eq 0 ]; then
        log_info "Knowledge Manager started successfully"
        log_info "PID file: $PID_FILE"
        log_info "Access logs: $LOGS_DIR/km_access.log"
        log_info "Error logs: $LOGS_DIR/km_error.log"
    else
        log_error "Failed to start Knowledge Manager"
        exit 1
    fi
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if PID file exists and process is running
    if [ ! -f "$PID_FILE" ]; then
        log_error "PID file not found"
        exit 1
    fi
    
    local pid=$(cat "$PID_FILE")
    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "KM process not running (PID: $pid)"
        exit 1
    fi
    
    # Test HTTP endpoint
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Testing endpoint (attempt $attempt/$max_attempts)..."
        
        if curl -s -f http://127.0.0.1:5001/mcp/spec > /dev/null; then
            log_info "KM server is responding correctly"
            return 0
        fi
        
        sleep 2
        ((attempt++))
    done
    
    log_error "KM server not responding after $max_attempts attempts"
    exit 1
}

performance_test() {
    log_info "Running basic performance test..."
    
    # Simple load test using curl
    local test_endpoint="http://127.0.0.1:5001/mcp/spec"
    local concurrent_requests=10
    local total_requests=100
    
    log_info "Testing $total_requests requests with $concurrent_requests concurrent connections..."
    
    # Create temporary file for results
    local temp_file=$(mktemp)
    
    # Run concurrent requests
    for i in $(seq 1 $concurrent_requests); do
        {
            for j in $(seq 1 $((total_requests / concurrent_requests))); do
                curl -s -w "%{time_total}\n" -o /dev/null "$test_endpoint" >> "$temp_file"
            done
        } &
    done
    
    wait
    
    # Calculate basic statistics
    local avg_time=$(awk '{sum+=$1} END {print sum/NR}' "$temp_file")
    local max_time=$(awk 'BEGIN{max=0} {if($1>max) max=$1} END{print max}' "$temp_file")
    
    log_info "Performance test results:"
    log_info "  Average response time: ${avg_time}s"
    log_info "  Maximum response time: ${max_time}s"
    log_info "  Total requests: $total_requests"
    
    rm -f "$temp_file"
    
    # Check if performance is acceptable (< 1 second average)
    if (( $(echo "$avg_time < 1.0" | bc -l) )); then
        log_info "Performance test PASSED"
    else
        log_warn "Performance test FAILED - average response time too high"
    fi
}

show_status() {
    log_info "Knowledge Manager Status:"
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "  Status: RUNNING (PID: $pid)"
            log_info "  Endpoint: http://127.0.0.1:5001/mcp"
            log_info "  Logs: $LOGS_DIR/km_*.log"
        else
            log_warn "  Status: NOT RUNNING (stale PID file)"
        fi
    else
        log_warn "  Status: NOT RUNNING"
    fi
}

main() {
    local command="${1:-start}"
    
    case "$command" in
        "start")
            log_info "Deploying Knowledge Manager in production mode..."
            check_dependencies
            setup_directories
            stop_existing_km
            start_km_server
            verify_deployment
            performance_test
            show_status
            log_info "Deployment complete!"
            ;;
        "stop")
            log_info "Stopping Knowledge Manager..."
            stop_existing_km
            log_info "Knowledge Manager stopped"
            ;;
        "restart")
            log_info "Restarting Knowledge Manager..."
            stop_existing_km
            sleep 2
            start_km_server
            verify_deployment
            show_status
            ;;
        "status")
            show_status
            ;;
        "test")
            performance_test
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|test}"
            echo ""
            echo "Commands:"
            echo "  start   - Deploy and start KM server"
            echo "  stop    - Stop KM server"
            echo "  restart - Restart KM server"
            echo "  status  - Show KM server status"
            echo "  test    - Run performance test"
            exit 1
            ;;
    esac
}

# Check if bc is available for performance calculations
if ! command -v bc &> /dev/null; then
    log_warn "bc not available - performance calculations may be limited"
fi

main "$@"