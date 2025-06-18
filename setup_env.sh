#!/bin/bash

# Enhanced Impact Tracker Environment Setup
echo "🚀 Setting up Enhanced Impact Tracker environment..."

# IMPORTANT: Set your Discord webhook URL as an environment variable for security
# DO NOT commit webhook URLs to version control!
# 
# To set your Discord webhook URL:
# export DISCORD_WEBHOOK_URL="your_webhook_url_here"
#
# Or create a .env file with:
# DISCORD_WEBHOOK_URL=your_webhook_url_here

if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    echo "⚠️  Warning: DISCORD_WEBHOOK_URL not set!"
    echo "📋 Please set your Discord webhook URL:"
    echo "   export DISCORD_WEBHOOK_URL='your_webhook_url_here'"
    echo ""
    echo "🔗 To get a Discord webhook URL:"
    echo "   1. Go to your Discord server settings"
    echo "   2. Click 'Integrations' → 'Webhooks'"
    echo "   3. Create a new webhook and copy the URL"
    echo ""
else
    echo "✅ Discord webhook URL configured"
fi

# Set other environment variables as needed
export PYTHONPATH="${PYTHONPATH}:."

echo "✅ Environment setup complete!"
echo "🏃 Run: python enhanced_dashboard.py" 