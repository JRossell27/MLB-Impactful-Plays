#!/usr/bin/env python3
"""
Baseball Savant GIF Integration Module
Fetches Baseball Savant animations and converts them to GIFs for social media posts
"""

import os
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseballSavantGIFIntegration:
    def __init__(self):
        self.savant_base = "https://baseballsavant.mlb.com"
        self.temp_dir = Path(tempfile.gettempdir()) / "baseball_gifs"
        self.temp_dir.mkdir(exist_ok=True)
        
    def get_statcast_data_for_play(self, game_id: int, play_id: int, game_date: str) -> Optional[Dict]:
        """Get Statcast data for a specific play to find animation URLs"""
        try:
            # Format date for Baseball Savant API
            date_str = game_date.replace('-', '/')
            
            # Search for the specific play using Statcast search
            params = {
                'all': 'true',
                'hfPT': '',
                'hfAB': '',
                'hfBBT': '',
                'hfPR': '',
                'hfZ': '',
                'stadium': '',
                'hfBBL': '',
                'hfNewZones': '',
                'hfGT': 'R|',  # Regular season
                'hfC': '',
                'hfSea': '2024|',  # Current season
                'hfSit': '',
                'player_type': 'batter',
                'hfOuts': '',
                'opponent': '',
                'pitcher_throws': '',
                'batter_stands': '',
                'hfSA': '',
                'game_date_gt': game_date,
                'game_date_lt': game_date,
                'hfInfield': '',
                'team': '',
                'position': '',
                'hfOutfield': '',
                'hfRO': '',
                'home_road': '',
                'game_pk': game_id,
                'hfFlag': '',
                'hfPull': '',
                'metric_1': '',
                'hfInn': '',
                'min_pitches': '0',
                'min_results': '0',
                'group_by': 'name',
                'sort_col': 'pitches',
                'player_event_sort': 'h_launch_speed',
                'sort_order': 'desc',
                'min_pas': '0',
                'type': 'details',
            }
            
            # Use the CSV export endpoint for easier parsing
            url = f"{self.savant_base}/statcast_search/csv"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse CSV data to find our specific play
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return None
                
            headers = lines[0].split(',')
            
            for line in lines[1:]:
                values = line.split(',')
                if len(values) >= len(headers):
                    play_data = dict(zip(headers, values))
                    # Match by at_bat_number or sv_id
                    if play_data.get('at_bat_number') == str(play_id):
                        return play_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Statcast data: {e}")
            return None
    
    def get_play_animation_url(self, game_id: int, play_id: int, statcast_data: Dict) -> Optional[str]:
        """Get the animation URL for a specific play from Baseball Savant"""
        try:
            # Baseball Savant animations are typically available at patterns like:
            # https://baseballsavant.mlb.com/sporty-videos/[game_id]/[play_data]
            
            # Try to construct the animation URL based on game and play data
            sv_id = statcast_data.get('sv_id', '')
            at_bat_number = statcast_data.get('at_bat_number', '')
            
            if not sv_id and not at_bat_number:
                logger.warning(f"No sv_id or at_bat_number found for play {play_id}")
                return None
            
            # Try different URL patterns Baseball Savant uses
            potential_urls = [
                f"{self.savant_base}/sporty-videos/{game_id}/{sv_id}.mp4",
                f"{self.savant_base}/videos/{game_id}/{at_bat_number}.mp4",
                f"{self.savant_base}/illustrator/download?game_pk={game_id}&sv_id={sv_id}",
            ]
            
            for url in potential_urls:
                try:
                    response = requests.head(url, timeout=10)
                    if response.status_code == 200:
                        logger.info(f"Found animation at: {url}")
                        return url
                except:
                    continue
            
            # If direct URLs don't work, try the illustrator tool
            return self._get_illustrator_animation(game_id, statcast_data)
            
        except Exception as e:
            logger.error(f"Error getting animation URL: {e}")
            return None
    
    def _get_illustrator_animation(self, game_id: int, statcast_data: Dict) -> Optional[str]:
        """Try to get animation from Baseball Savant's illustrator tool"""
        try:
            # The illustrator tool might have different endpoints
            # This would require more investigation of Baseball Savant's actual API
            
            illustrator_params = {
                'game_pk': game_id,
                'sv_id': statcast_data.get('sv_id', ''),
                'type': 'video'
            }
            
            url = f"{self.savant_base}/illustrator/api/download"
            response = requests.get(url, params=illustrator_params, timeout=20)
            
            if response.status_code == 200:
                # Check if response contains a video URL
                if response.headers.get('content-type', '').startswith('video/'):
                    return url + '?' + '&'.join([f"{k}={v}" for k, v in illustrator_params.items()])
            
            return None
            
        except Exception as e:
            logger.error(f"Error with illustrator API: {e}")
            return None
    
    def download_and_convert_to_gif(self, video_url: str, output_path: str, max_duration: int = 10) -> bool:
        """Download video and convert to GIF using ffmpeg"""
        try:
            # Download the video
            temp_video = self.temp_dir / f"temp_video_{int(time.time())}.mp4"
            
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(temp_video, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Convert to GIF using ffmpeg
            # Optimize for Twitter: max 15MB, good quality, reasonable frame rate
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', str(temp_video),
                '-t', str(max_duration),  # Limit duration
                '-vf', 'fps=15,scale=480:-1:flags=lanczos,palettegen=stats_mode=diff',
                '-y',
                str(self.temp_dir / 'palette.png')
            ]
            
            # Generate palette
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            
            # Create GIF with palette
            gif_cmd = [
                'ffmpeg',
                '-i', str(temp_video),
                '-i', str(self.temp_dir / 'palette.png'),
                '-t', str(max_duration),
                '-lavfi', 'fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5',
                '-y',
                output_path
            ]
            
            subprocess.run(gif_cmd, check=True, capture_output=True)
            
            # Clean up
            temp_video.unlink()
            (self.temp_dir / 'palette.png').unlink(missing_ok=True)
            
            # Check file size (Twitter limit is ~15MB for GIFs)
            if Path(output_path).stat().st_size > 15 * 1024 * 1024:
                logger.warning(f"GIF too large: {Path(output_path).stat().st_size / 1024 / 1024:.1f}MB")
                return False
            
            logger.info(f"Successfully created GIF: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating GIF: {e}")
            return False
    
    def get_gif_for_play(self, game_id: int, play_id: int, game_date: str, max_wait_minutes: int = 30) -> Optional[str]:
        """
        Main method to get GIF for a play
        Returns path to GIF file if successful, None otherwise
        """
        # Check if we should even try (animations take time to be available)
        play_time = datetime.now()  # In real implementation, get actual play time
        
        # Wait for animation to be available (Baseball Savant typically takes 15-30 min)
        if max_wait_minutes > 0:
            logger.info(f"Waiting up to {max_wait_minutes} minutes for animation to be available...")
            
            for attempt in range(max_wait_minutes):
                statcast_data = self.get_statcast_data_for_play(game_id, play_id, game_date)
                
                if statcast_data:
                    animation_url = self.get_play_animation_url(game_id, play_id, statcast_data)
                    
                    if animation_url:
                        # Create GIF
                        gif_path = self.temp_dir / f"play_{game_id}_{play_id}.gif"
                        
                        if self.download_and_convert_to_gif(animation_url, str(gif_path)):
                            return str(gif_path)
                
                if attempt < max_wait_minutes - 1:
                    time.sleep(60)  # Wait 1 minute between attempts
        
        logger.warning(f"Could not create GIF for play {play_id} in game {game_id}")
        return None
    
    def create_follow_up_tweet_with_gif(self, original_tweet_id: str, gif_path: str, play_description: str) -> bool:
        """Create a follow-up tweet with the GIF"""
        try:
            # This would integrate with your existing Twitter API
            # For now, just a placeholder
            
            tweet_text = f"🎬 Watch the play:\n\n{play_description}\n\nAnimation courtesy of @baseballsavant"
            
            # Upload GIF and post tweet
            # media = api.media_upload(gif_path)
            # api.update_status(
            #     status=tweet_text,
            #     media_ids=[media.media_id],
            #     in_reply_to_status_id=original_tweet_id
            # )
            
            logger.info(f"Would post follow-up tweet with GIF: {gif_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting follow-up tweet: {e}")
            return False

# Example usage integration with existing system
def integrate_with_impact_tracker():
    """
    Example of how to integrate this with your existing RealTimeImpactTracker
    """
    gif_integration = BaseballSavantGIFIntegration()
    
    # In your existing post_impact_play method, you would add:
    # 
    # # Post immediate tweet (as you do now)
    # tweet = self.post_immediate_tweet(play, game_info, impact_score)
    # 
    # # Schedule GIF follow-up (new functionality)
    # if tweet and tweet.id:
    #     threading.Thread(
    #         target=self._post_delayed_gif_tweet,
    #         args=(tweet.id, play, game_info),
    #         daemon=True
    #     ).start()
    
    pass

def _post_delayed_gif_tweet(self, original_tweet_id: str, play: Dict, game_info: Dict):
    """Helper method to add to RealTimeImpactTracker class"""
    gif_integration = BaseballSavantGIFIntegration()
    
    try:
        gif_path = gif_integration.get_gif_for_play(
            game_id=play['game_id'],
            play_id=play['play_id'],
            game_date=datetime.now().strftime('%Y-%m-%d'),
            max_wait_minutes=30
        )
        
        if gif_path:
            gif_integration.create_follow_up_tweet_with_gif(
                original_tweet_id=original_tweet_id,
                gif_path=gif_path,
                play_description=play['description']
            )
            
            # Clean up
            Path(gif_path).unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"Error in delayed GIF tweet: {e}")

if __name__ == "__main__":
    # Test the integration
    gif_integration = BaseballSavantGIFIntegration()
    
    # Example: Try to get a GIF for a recent play
    # gif_path = gif_integration.get_gif_for_play(
    #     game_id=123456,
    #     play_id=5,
    #     game_date='2024-01-15',
    #     max_wait_minutes=5
    # )
    
    print("Baseball Savant GIF integration module loaded successfully!") 