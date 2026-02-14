#!/bin/bash

cd "$(dirname "$0")"

STOPPED=false

# Kill from PID file
if [ -f stock_monitor.pid ]; then
    PID=$(cat stock_monitor.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 Stopping Stock Monitor (PID: $PID)..."
        kill $PID
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
        fi
        STOPPED=true
    fi
    rm -f stock_monitor.pid
fi

# Also kill any orphaned processes
ORPHANS=$(pgrep -f "python.*main\.py" 2>/dev/null)
if [ -n "$ORPHANS" ]; then
    echo "Killing orphaned processes: $ORPHANS"
    echo "$ORPHANS" | xargs kill 2>/dev/null
    STOPPED=true
fi

if [ "$STOPPED" = true ]; then
    echo "✅ Stock Monitor stopped"
else
    echo "⚠️  Stock Monitor is not running."
fi
