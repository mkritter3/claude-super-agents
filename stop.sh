#!/bin/bash

# AET System Stop Script
# Stops all AET system services

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Stopping AET System Services                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Stop Knowledge Manager
echo "🛑 Stopping Knowledge Manager..."
if [ -f /tmp/km_server.pid ]; then
    PID=$(cat /tmp/km_server.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        rm /tmp/km_server.pid
        echo "✅ Knowledge Manager stopped"
    else
        echo "⚠️  Knowledge Manager not running (stale PID file)"
        rm /tmp/km_server.pid
    fi
else
    # Try to find by port
    KM_PID=$(lsof -ti:5001)
    if [ ! -z "$KM_PID" ]; then
        kill $KM_PID
        echo "✅ Knowledge Manager stopped"
    else
        echo "⚠️  Knowledge Manager not running"
    fi
fi

# Stop Metrics Collector
echo "🛑 Stopping Metrics Collector..."
if [ -f /tmp/metrics_collector.pid ]; then
    PID=$(cat /tmp/metrics_collector.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        rm /tmp/metrics_collector.pid
        echo "✅ Metrics Collector stopped"
    else
        echo "⚠️  Metrics Collector not running (stale PID file)"
        rm /tmp/metrics_collector.pid
    fi
else
    # Try to find by port
    METRICS_PID=$(lsof -ti:5000)
    if [ ! -z "$METRICS_PID" ]; then
        kill $METRICS_PID
        echo "✅ Metrics Collector stopped"
    else
        echo "⚠️  Metrics Collector not running"
    fi
fi

echo ""
echo "✅ All AET services stopped"
echo ""