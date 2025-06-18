#!/bin/bash
echo "🚀 Starting Enhanced MLB Impact Tracker..."

# Set Discord webhook URL if not already set
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    echo "⚠️  DISCORD_WEBHOOK_URL environment variable not set!"
    echo "📋 Please set your Discord webhook URL as an environment variable for security"
    echo "🔧 Example: export DISCORD_WEBHOOK_URL='your_webhook_url_here'"
    echo "🚫 System will continue but Discord notifications will be disabled"
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