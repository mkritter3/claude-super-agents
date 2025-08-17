#!/bin/bash
echo "=== AET System Status ==="
CLAUDE_DIR="$(dirname "$0")"

# Check agents
if [ -d "$CLAUDE_DIR/agents" ]; then
    AGENT_COUNT=$(ls -1 "$CLAUDE_DIR/agents"/*.md 2>/dev/null | wc -l)
    echo "✓ $AGENT_COUNT agents configured"
else
    echo "✗ No agents found"
fi

# Check KM server port
if [ -f "$CLAUDE_DIR/km_server/port" ]; then
    PORT=$(cat "$CLAUDE_DIR/km_server/port")
    echo "✓ Knowledge Manager configured for port $PORT"
else
    echo "✗ Knowledge Manager not configured"
fi

# Check events
if [ -f "$CLAUDE_DIR/events/log.ndjson" ]; then
    EVENT_COUNT=$(wc -l < "$CLAUDE_DIR/events/log.ndjson")
    echo "✓ Event system ($EVENT_COUNT events)"
else
    echo "✗ Event system not initialized"
fi

echo ""
echo "Project: $(pwd)"
