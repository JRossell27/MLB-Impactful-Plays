#!/bin/bash
echo "🚀 Starting Mets Home Run Tracker..."

# Set Discord webhook URL if not already set
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB"
    echo "🔗 Discord webhook configured automatically"
fi

echo "RUN_TEST environment variable: $RUN_TEST"

if [ "$RUN_TEST" = "true" ]; then
    echo "🧪 Running test mode - checking Mets HR system..."
    python -c "
from mets_homerun_tracker import MetsHomeRunTracker
tracker = MetsHomeRunTracker()
games = tracker.get_live_mets_games()
print(f'Found {len(games)} Mets games')
print('✅ Mets HR Tracker test completed')
"
else
    echo "🏠⚾ Running Mets Home Run monitoring..."
    python mets_dashboard.py
fi 