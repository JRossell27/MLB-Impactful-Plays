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
import csv
from io import StringIO
import re

logger = logging.getLogger(__name__)

class BaseballSavantGIFIntegration:
    def __init__(self):
        self.savant_base = "https://baseballsavant.mlb.com"
        self.temp_dir = Path(tempfile.gettempdir()) / "baseball_gifs"
        self.temp_dir.mkdir(exist_ok=True)
        
    def get_statcast_data_for_play(self, game_id: int, play_id: int, game_date: str, mlb_play_data: Dict = None) -> Optional[Dict]:
        """Get Statcast data for a specific play"""
        try:
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
                'hfSea': '2025|',  # Current season
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
            
            # Parse CSV data
            csv_reader = csv.DictReader(StringIO(response.text))
            
            # Get all plays with events (not just pitches)
            plays_with_events = []
            for row in csv_reader:
                if row.get('events'):  # Only rows with actual events
                    plays_with_events.append(row)
            
            logger.info(f"Found {len(plays_with_events)} plays with events for game {game_id}")
            
            # If we have MLB play data to match against, try to find the exact play
            if mlb_play_data:
                target_event = mlb_play_data.get('result', {}).get('event', '').lower()
                target_inning = mlb_play_data.get('about', {}).get('inning')
                target_batter = mlb_play_data.get('matchup', {}).get('batter', {}).get('id')
                
                logger.info(f"Looking for play: {target_event} in inning {target_inning}")
                
                # Try to find exact match
                for play in plays_with_events:
                    event = play.get('events', '').lower()
                    inning = play.get('inning')
                    batter_id = play.get('batter')
                    
                    # Match by event type and inning
                    if (target_event in event or event in target_event) and str(inning) == str(target_inning):
                        logger.info(f"Found matching play: {event} in inning {inning}")
                        return play
                
                # If no exact match, try just by event type
                for play in plays_with_events:
                    event = play.get('events', '').lower()
                    if target_event in event or event in target_event:
                        logger.info(f"Found play by event type: {event}")
                        return play
            
            # Fallback: prioritize visually interesting plays
            for play in plays_with_events:
                event = play.get('events', '').lower()
                # Prioritize visually interesting plays
                if any(keyword in event for keyword in ['home_run', 'double', 'triple', 'single']):
                    logger.info(f"Found interesting play: {event}")
                    return play
            
            # If no interesting plays, return the first play with events
            if plays_with_events:
                logger.info(f"Returning first available play: {plays_with_events[0].get('events')}")
                return plays_with_events[0]
            
            logger.warning(f"No plays with events found for game {game_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Statcast data: {e}")
            return None
    
    def get_play_animation_url(self, game_id: int, play_id: int, statcast_data: Dict, mlb_play_data: Dict = None) -> Optional[str]:
        """Get the animation URL for a specific play from Baseball Savant"""
        try:
            # We need to get the play UUID from the Baseball Savant /gf endpoint
            # since the Statcast CSV doesn't include it
            
            logger.info(f"Getting play UUID for game {game_id}, play {play_id}")
            
            # Get game data from Baseball Savant /gf endpoint
            gf_url = f"{self.savant_base}/gf?game_pk={game_id}&at_bat_number=1"
            gf_response = requests.get(gf_url, timeout=15)
            
            if gf_response.status_code != 200:
                logger.warning(f"Failed to get game data from /gf endpoint: {gf_response.status_code}")
                return None
            
            gf_data = gf_response.json()
            
            # Look in both home and away team plays
            all_plays = []
            all_plays.extend(gf_data.get('team_home', []))
            all_plays.extend(gf_data.get('team_away', []))
            
            logger.info(f"Found {len(all_plays)} total plays in game data")
            
            # Find the matching play using MLB API data if available
            target_play_uuid = None
            
            if mlb_play_data:
                target_event = mlb_play_data.get('result', {}).get('event', '').lower()
                target_inning = mlb_play_data.get('about', {}).get('inning')
                target_batter = mlb_play_data.get('matchup', {}).get('batter', {}).get('fullName', '')
                
                logger.info(f"Looking for {target_batter} {target_event} in inning {target_inning}")
                
                # Try to find exact match - prioritize plays that have the actual event in their description
                best_matches = []
                for play in all_plays:
                    play_event = play.get('events', '').lower()
                    play_description = play.get('des', '').lower()
                    play_inning = play.get('inning')
                    play_batter = play.get('batter_name', '')
                    play_uuid = play.get('play_id')
                    
                    # Must match inning and have a play UUID
                    if str(play_inning) == str(target_inning) and play_uuid:
                        # Check if batter matches
                        batter_match = (target_batter.split()[-1].lower() in play_batter.lower() or 
                                      play_batter.split()[-1].lower() in target_batter.lower())
                        
                        if batter_match:
                            # Score this match based on how well it matches the event
                            score = 0
                            
                            # HIGHEST PRIORITY: This is the actual contact pitch (not just a pitch in the at-bat)
                            pitch_call = play.get('pitch_call', '')
                            call = play.get('call', '')
                            if pitch_call == 'hit_into_play' or call == 'X':
                                score += 1000  # Heavily prioritize the contact pitch
                            
                            # High priority: event description contains the target event
                            if target_event in play_description or target_event.replace(' ', '') in play_description.replace(' ', ''):
                                score += 100
                            
                            # Medium priority: events field contains the target event  
                            if target_event in play_event or target_event.replace(' ', '') in play_event.replace(' ', ''):
                                score += 50
                            
                            # For home runs, look for specific indicators
                            if 'home' in target_event and 'run' in target_event:
                                if 'homer' in play_description or 'home run' in play_description:
                                    score += 100
                                if 'homer' in play_event or 'home run' in play_event:
                                    score += 50
                                
                                # Additional bonus for hit data which confirms this was the contact pitch
                                if play.get('hit_speed') or play.get('hit_distance'):
                                    score += 500
                            
                            # Bonus for exact event match
                            if play_event.strip() == target_event.strip():
                                score += 200
                            
                            best_matches.append((score, play, play_uuid))
                            logger.info(f"Found potential match (score {score}): {play_batter} - {play_event} - pitch_call: {pitch_call} - {play_description[:50]}...")
                
                # Sort by score and take the best match
                if best_matches:
                    best_matches.sort(key=lambda x: x[0], reverse=True)
                    best_score, best_play, target_play_uuid = best_matches[0]
                    
                    logger.info(f"Selected best match (score {best_score}): {best_play.get('batter_name')} - {best_play.get('events')}")
                    logger.info(f"Play UUID: {target_play_uuid}")
            
            # Fallback: look for interesting plays if no exact match
            if not target_play_uuid:
                logger.info("No exact match found, looking for interesting plays...")
                for play in all_plays:
                    play_event = play.get('events', '').lower()
                    play_uuid = play.get('play_id')
                    
                    if play_uuid and any(keyword in play_event for keyword in ['home run', 'double', 'triple']):
                        logger.info(f"Found interesting play: {play_event}")
                        target_play_uuid = play_uuid
                        break
            
            if not target_play_uuid:
                logger.warning("No suitable play with UUID found")
                return None
            
            # Now get the video URL using the UUID
            logger.info(f"Getting video URL for play UUID: {target_play_uuid}")
            
            sporty_url = f"{self.savant_base}/sporty-videos?playId={target_play_uuid}"
            response = requests.get(sporty_url, timeout=15)
            
            if response.status_code == 200:
                html_content = response.text
                logger.info(f"Got video page ({len(html_content)} chars)")
                
                # Extract the actual video URL from the HTML
                video_url_patterns = [
                    r'https://sporty-clips\.mlb\.com/[^"\s]*\.mp4',
                    r'"src":\s*"(https://sporty-clips\.mlb\.com/[^"]*\.mp4)"',
                    r'data-src="(https://sporty-clips\.mlb\.com/[^"]*\.mp4)"',
                ]
                
                for pattern in video_url_patterns:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        video_url = match[0] if isinstance(match, tuple) else match
                        logger.info(f"Found potential video URL: {video_url}")
                        
                        # Test if this URL actually works
                        try:
                            test_response = requests.head(video_url, timeout=10)
                            if test_response.status_code == 200:
                                content_type = test_response.headers.get('content-type', '')
                                if 'video' in content_type:
                                    logger.info(f"✅ Confirmed working video URL: {video_url}")
                                    return video_url
                        except Exception as e:
                            logger.warning(f"Video URL test failed: {e}")
                            continue
                
                logger.warning(f"No working video URL found in HTML")
                return None
            else:
                logger.warning(f"Failed to fetch video page: {response.status_code}")
                return None
            
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
    
    def get_gif_for_play(self, game_id: int, play_id: int, game_date: str, mlb_play_data: Dict = None) -> Optional[str]:
        """Create a GIF for a specific play and return the file path"""
        try:
            logger.info(f"Creating GIF for game {game_id}, play {play_id}")
            
            # Step 1: Get Statcast data for the play
            statcast_data = self.get_statcast_data_for_play(game_id, play_id, game_date, mlb_play_data)
            if not statcast_data:
                logger.warning(f"No Statcast data found for play {play_id}")
                return None
            
            # Step 2: Get the animation URL
            animation_url = self.get_play_animation_url(game_id, play_id, statcast_data, mlb_play_data)
            if not animation_url:
                logger.warning(f"No animation URL found for play {play_id}")
                return None
                
            # Step 3: Create the GIF
            gif_filename = f"play_{game_id}_{play_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
            gif_path = self.temp_dir / gif_filename
            
            success = self.download_and_convert_to_gif(animation_url, str(gif_path))
            
            if success and gif_path.exists():
                logger.info(f"Successfully created GIF: {gif_path}")
                return str(gif_path)
            else:
                logger.error(f"Failed to create GIF for play {play_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating GIF for play {play_id}: {e}")
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
            mlb_play_data=play
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
    #     mlb_play_data=play_data
    # )
    
    print("Baseball Savant GIF integration module loaded successfully!") 