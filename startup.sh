#!/bin/bash
echo "🚀 Starting Enhanced MLB Impact Tracker..."

# Set Discord webhook URL if not already set
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB"
    echo "🔗 Discord webhook configured automatically"
fi

echo "RUN_TEST environment variable: $RUN_TEST"

if [ "$RUN_TEST" = "true" ]; then
    echo "🧪 Running test mode - checking Enhanced Impact Tracker system..."
    python -c "
from enhanced_impact_tracker import EnhancedImpactTracker
tracker = EnhancedImpactTracker()
games = tracker.get_live_games()
print(f'Found {len(games)} live games')
print('✅ Enhanced Impact Tracker test completed')
"
else
    echo "⚾🎯 Running Enhanced MLB Impact Tracker with GIF integration..."
    python enhanced_dashboard.py
fi 