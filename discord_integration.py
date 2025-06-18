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

class DiscordPoster:
    """Handles posting impact plays to Discord via webhook"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.username = "MLB Impact Bot"
        
    def post_impact_play(self, play_data: Dict, gif_path: Optional[str] = None) -> bool:
        """
        Post a high-impact play to Discord with GIF and formatted text
        
        Args:
            play_data: Dictionary containing play information
            gif_path: Path to GIF file (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format the main message
            message_content = self._format_discord_message(play_data)
            
            # Prepare the Discord payload
            payload = {
                "content": message_content,
                "username": self.username
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
                    
                        # Check response for file upload
                        if response.status_code in [200, 204]:
                            logger.info("✅ Successfully posted to Discord with GIF")
                            return True
                        else:
                            logger.error(f"❌ Discord post with GIF failed: {response.status_code} - {response.text}")
                            # Fall back to text-only post
                    
                except Exception as e:
                    logger.error(f"Error uploading GIF to Discord: {e}")
                    # Fall back to text-only post
            
            # Send text-only if no GIF or if GIF upload failed
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=15
            )
            
            # Check response
            if response.status_code in [200, 204]:
                logger.info("✅ Successfully posted to Discord (text only)")
                return True
            else:
                logger.error(f"❌ Discord post failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
            return False
    
    def _format_discord_message(self, play_data: Dict) -> str:
        """Format the Discord message with clean copy-paste text for Twitter"""
        
        # Extract key information
        event = play_data.get('event', 'Unknown Play')
        impact_score = play_data.get('impact_score', 0.0)
        away_team = play_data.get('away_team', 'AWAY')
        home_team = play_data.get('home_team', 'HOME')
        away_score = play_data.get('away_score', 0)
        home_score = play_data.get('home_score', 0)
        inning = play_data.get('inning', 1)
        half_inning = play_data.get('half_inning', 'top')
        description = play_data.get('description', '')
        
        # Format inning display
        inning_display = f"{'T' if half_inning == 'top' else 'B'}{inning}"
        
        # Truncate description if too long for Twitter
        if len(description) > 100:
            description = description[:97] + "..."
        
        # Create clean Twitter copy text
        twitter_text = f"""⭐ MARQUEE MOMENT!

{description}

📊 Impact: {impact_score:.1%} WP change
⚾ {away_team} {away_score} - {home_score} {home_team} ({inning_display})

#{away_team.replace(' ', '')} #{home_team.replace(' ', '')} #MLB"""

        return twitter_text
    
    def post_test_message(self) -> bool:
        """Post a test message to verify webhook is working"""
        test_data = {
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
        
        return self.post_impact_play(test_data)

# Initialize Discord poster with your webhook
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1384897092501114941/rm-qdGHW0zB4CLzuU8RksldRpxnfZbszo2AF66d_is4Rru_ubscZSzl0qgBzkoUorX7p"
discord_poster = DiscordPoster(DISCORD_WEBHOOK_URL)

if __name__ == "__main__":
    # Test the Discord integration
    print("🧪 Testing Discord integration...")
    success = discord_poster.post_test_message()
    if success:
        print("✅ Discord integration test successful!")
        print("Check your Discord channel for the formatted test message.")
    else:
        print("❌ Discord integration test failed.") 