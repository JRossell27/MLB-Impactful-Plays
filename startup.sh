#!/bin/bash
echo "🚀 Starting MLB Impact System..."
echo "RUN_TEST environment variable: $RUN_TEST"

if [ "$RUN_TEST" = "true" ]; then
    echo "🧪 Running test mode - processing last night's high-impact plays..."
    python test_last_night_plays.py
else
    echo "🏃 Running normal monitoring mode..."
    python enhanced_dashboard.py
fi 