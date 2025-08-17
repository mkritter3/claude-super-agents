#!/bin/bash
CLAUDE_DIR="$(dirname "$0")"

echo "=== AET System Status ==="
echo ""

# Check agents
if [ -d "$CLAUDE_DIR/agents" ]; then
    AGENT_COUNT=$(ls -1 "$CLAUDE_DIR/agents"/*.md 2>/dev/null | wc -l)
    echo "✓ $AGENT_COUNT agents configured"
else
    echo "✗ No agents found"
fi

# Check KM server
if [ -f "$CLAUDE_DIR/km_server/port" ]; then
    PORT=$(cat "$CLAUDE_DIR/km_server/port")
    if curl -s "http://localhost:$PORT/health" >/dev/null 2>&1; then
        echo "✓ Knowledge Manager running on port $PORT"
    else
        echo "✗ Knowledge Manager not responding on port $PORT"
    fi
else
    echo "✗ Knowledge Manager not configured"
fi

# Check event system
if [ -f "$CLAUDE_DIR/events/log.ndjson" ]; then
    EVENT_COUNT=$(wc -l < "$CLAUDE_DIR/events/log.ndjson")
    echo "✓ Event system active ($EVENT_COUNT events)"
else
    echo "✗ Event system not initialized"
fi

# Check git hooks
if [ -d "$CLAUDE_DIR/hooks" ]; then
    HOOK_COUNT=$(ls -1 "$CLAUDE_DIR/hooks"/* 2>/dev/null | wc -l)
    echo "✓ $HOOK_COUNT git hooks installed"
else
    echo "✗ No git hooks found"
fi

echo ""
echo "Project: $(pwd)"
