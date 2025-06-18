#!/usr/bin/env python3
"""
Discord Integration for MLB Impact Tracker
Posts high-impact plays to Discord for easy copy/paste to Twitter
"""

import requests
import logging
from typing import Optional, Dict
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordIntegration:
    def __init__(self):
        # Get webhook URL from environment variable only - no hardcoded fallback for security
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        
        if not self.webhook_url:
            logger.warning("⚠️  DISCORD_WEBHOOK_URL environment variable not set - Discord notifications disabled")
            logger.info("🔧 To enable Discord notifications, set DISCORD_WEBHOOK_URL environment variable")
        else:
            logger.info("✅ Discord webhook configured from environment variable")
    
    def is_configured(self) -> bool:
        """Check if Discord integration is properly configured"""
        return bool(self.webhook_url)
    
    def send_impact_notification(self, play_data: Dict, gif_path: Optional[str] = None) -> bool:
        """
        Send a high-impact play notification to Discord
        
        Args:
            play_data: Dictionary containing play information
            gif_path: Optional path to GIF file to attach
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.debug("Discord not configured - skipping notification")
            return False
            
        try:
            # Create Discord embed
            embed = {
                "title": f"🎯 {play_data.get('event', 'High-Impact Play')}",
                "description": play_data.get('description', ''),
                "color": 0xFF6B35,  # Orange color
                "fields": [
                    {
                        "name": "⚾ Game",
                        "value": f"{play_data.get('away_team', 'Away')} @ {play_data.get('home_team', 'Home')}",
                        "inline": True
                    },
                    {
                        "name": "📊 Impact",
                        "value": f"{play_data.get('impact_score', 0):.1%} WP Change",
                        "inline": True
                    },
                    {
                        "name": "⏰ Inning",
                        "value": f"{play_data.get('inning', '?')}{play_data.get('half_inning', '')}",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Enhanced MLB Impact Tracker"
                },
                "timestamp": play_data.get('timestamp', '')
            }
            
            # Add player info if available
            if play_data.get('batter'):
                embed["fields"].append({
                    "name": "🏏 Batter",
                    "value": play_data['batter'],
                    "inline": True
                })
            
            if play_data.get('pitcher'):
                embed["fields"].append({
                    "name": "⚾ Pitcher", 
                    "value": play_data['pitcher'],
                    "inline": True
                })
            
            payload = {
                "embeds": [embed],
                "username": "MLB Impact Tracker",
                "avatar_url": "https://raw.githubusercontent.com/JRossell27/MLB-Impactful-Plays/main/assets/baseball-icon.png"
            }
            
            # Handle GIF upload if provided
            if gif_path and os.path.exists(gif_path):
                try:
                    with open(gif_path, 'rb') as gif_file:
                        files = {
                            'file': ('impact_play.gif', gif_file, 'image/gif')
                        }
                        # When uploading files, content goes in payload_json as proper JSON
                        payload_data = {
                            'payload_json': json.dumps(payload)
                        }
                    
                        # Send with file and text together
                        response = requests.post(
                            self.webhook_url,
                            data=payload_data,
                            files=files,
                            timeout=30
                        )
                        
                except Exception as gif_error:
                    logger.warning(f"Failed to upload GIF, sending text only: {gif_error}")
                    # Fall back to text-only message
                    response = requests.post(
                        self.webhook_url,
                        json=payload,
                        timeout=30
                    )
            else:
                # Send text-only message
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=30
                )
            
            if response.status_code == 204:
                logger.info("✅ Discord notification sent successfully")
                return True
            else:
                logger.error(f"❌ Discord webhook failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending Discord notification: {e}")
            return False
    
    def send_system_status(self, status_data: Dict) -> bool:
        """
        Send a system status update to Discord
        
        Args:
            status_data: Dictionary containing system status information
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            return False
            
        try:
            embed = {
                "title": "🤖 System Status Update",
                "color": 0x28A745 if status_data.get('healthy', True) else 0xDC3545,
                "fields": [
                    {
                        "name": "⏰ Uptime",
                        "value": status_data.get('uptime', 'Unknown'),
                        "inline": True
                    },
                    {
                        "name": "📊 Games Checked Today",
                        "value": str(status_data.get('games_checked', 0)),
                        "inline": True
                    },
                    {
                        "name": "🎯 Plays Queued",
                        "value": str(status_data.get('plays_queued', 0)),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Enhanced MLB Impact Tracker"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "MLB Impact Tracker - System"
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"❌ Error sending system status: {e}")
            return False

# Create a global instance for easy importing
discord_client = DiscordIntegration()

# Fallback webhook URL for testing/demo purposes only - NOT FOR PRODUCTION
# This is disabled by default for security
DISCORD_WEBHOOK_URL = None  # Removed hardcoded URL for security

if __name__ == "__main__":
    # Test the Discord integration
    print("🧪 Testing Discord integration...")
    success = discord_client.send_impact_notification(
        {
            'event': 'Home Run',
            'impact_score': 0.455,
            'away_team': 'NYY',
            'home_team': 'BOS',
            'away_score': 3,
            'home_score': 4,
            'inning': 9,
            'half_inning': 'top',
            'description': 'Aaron Judge homers (62) on a fly ball to center field. Anthony Rizzo scores.',
            'batter': 'Aaron Judge',
            'pitcher': 'Craig Kimbrel',
            'leverage_index': 3.2,
            'wpa': 0.455
        }
    )
    if success:
        print("✅ Discord integration test successful!")
        print("Check your Discord channel for the formatted test message.")
    else:
        print("❌ Discord integration test failed.") 