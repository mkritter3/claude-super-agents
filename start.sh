#!/bin/bash

# AET System Start Script
# Starts all necessary services for the AET system

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Starting AET System Services                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if setup has been run
if [ ! -d ".claude/events" ]; then
    echo "❌ AET system not initialized. Running setup first..."
    ./setup.sh
    echo ""
fi

# Start Knowledge Manager in production mode
echo "🧠 Starting Knowledge Manager..."
if [ -f .claude/system/km_server.py ]; then
    # Check if already running
    if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✅ Knowledge Manager already running on port 5001"
    else
        # Start with gunicorn if available, otherwise use Flask dev server
        if command -v gunicorn &> /dev/null; then
            echo "Starting with Gunicorn (production mode)..."
            cd .claude/system
            gunicorn -w 4 -b 127.0.0.1:5001 --daemon --pid /tmp/km_server.pid --log-file .claude/logs/km_server.log km_server:app 2>/dev/null
            cd "$SCRIPT_DIR"
            sleep 2
            if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
                echo "✅ Knowledge Manager started (production mode)"
            else
                echo "⚠️  Failed to start with Gunicorn, trying Flask..."
                python3 .claude/system/km_server.py > .claude/logs/km_server.log 2>&1 &
                echo $! > /tmp/km_server.pid
                sleep 2
                echo "✅ Knowledge Manager started (development mode)"
            fi
        else
            echo "Starting with Flask (development mode)..."
            python3 .claude/system/km_server.py > .claude/logs/km_server.log 2>&1 &
            echo $! > /tmp/km_server.pid
            sleep 2
            echo "✅ Knowledge Manager started (development mode)"
        fi
    fi
else
    echo "⚠️  Knowledge Manager not found at .claude/system/km_server.py"
fi

# Check health of services
echo ""
echo "🔍 Checking service health..."
sleep 1

# Check KM health
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Knowledge Manager: Healthy"
else
    echo "⚠️  Knowledge Manager: Not responding (may still be starting)"
fi

# Check if metrics collector is available
if [ -f .claude/system/metrics_collector.py ]; then
    if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✅ Metrics Collector: Already running"
    else
        echo "📊 Starting Metrics Collector..."
        python3 .claude/system/metrics_collector.py > .claude/logs/metrics.log 2>&1 &
        echo $! > /tmp/metrics_collector.pid
        sleep 1
        echo "✅ Metrics Collector: Started"
    fi
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║            ✅ AET System Ready!                          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Available Commands:"
echo ""
echo "  Create a task:"
echo "    ./.claude/aet create \"Your task description\""
echo ""
echo "  Process tasks:"
echo "    ./.claude/aet process"
echo ""
echo "  Check status:"
echo "    ./.claude/aet status"
echo ""
echo "  Stop services:"
echo "    ./stop.sh"
echo ""
echo "📊 Monitoring:"
echo "  - Knowledge Manager: http://localhost:5001/health"
echo "  - Metrics: http://localhost:5000/metrics"
echo ""