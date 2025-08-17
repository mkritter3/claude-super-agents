#!/bin/bash
set -euo pipefail

log_event() {
    local ticket_id="$1"
    local event_type="$2"
    local payload="$3"
    
    python3 .claude/system/event_logger.py "$ticket_id" "$event_type" "$payload"
}

# Example usage:
# log_event "TICKET-123" "TASK_CREATED" '{"title": "Implement feature X"}'