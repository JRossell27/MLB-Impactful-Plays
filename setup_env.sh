#!/bin/bash

# Mets Home Run Tracker Environment Setup
echo "🏠⚾ Setting up Mets Home Run Tracker environment..."

# Set Discord webhook URL
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB"

# Set other default environment variables
export AUTO_START_MONITORING="true"
export PORT="5000"
export SITE_URL="http://localhost:5000"

echo "✅ Environment variables set:"
echo "   - Discord webhook configured"
echo "   - Auto-start monitoring enabled"
echo "   - Port set to 5000"
echo ""
echo "🚀 Ready to start Mets HR tracking!"
echo "   Run: ./startup.sh" 