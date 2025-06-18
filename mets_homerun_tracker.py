#!/usr/bin/env python3
"""
New York Mets Home Run Tracker with GIF Integration
Monitors live games every 2 minutes for ALL Mets home runs and creates GIFs in real time
No WPA filtering - just pure Mets home run coverage
"""

import os
import sys
import time
import json
import logging
import requests
import csv
from io import StringIO
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import pickle
from dataclasses import dataclass, asdict
import threading
import signal
from baseball_savant_gif_integration import BaseballSavantGIFIntegration
from discord_integration import discord_poster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mets_homerun_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MetsHomeRun:
    """Represents a Mets home run queued for GIF processing"""
    play_id: str
    game_id: int
    game_date: str
    description: str
    batter: str
    pitcher: str
    inning: int
    half_inning: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    distance: Optional[float] = None
    exit_velocity: Optional[float] = None
    launch_angle: Optional[float] = None
    timestamp: datetime = None
    mlb_play_data: Dict = None
    game_info: Dict = None
    gif_attempts: int = 0
    max_attempts: int = 5
    last_attempt: Optional[datetime] = None
    gif_created: bool = False
    posted: bool = False
    gif_path: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        data['last_attempt'] = self.last_attempt.isoformat() if self.last_attempt else None
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data['last_attempt']:
            data['last_attempt'] = datetime.fromisoformat(data['last_attempt'])
        return cls(**data)

class MetsHomeRunTracker:
    def __init__(self):
        self.api_base = "https://statsapi.mlb.com/api/v1.1"
        self.schedule_api_base = "https://statsapi.mlb.com/api/v1"
        self.gif_integration = BaseballSavantGIFIntegration()
        
        # Queue management
        self.homerun_queue: List[MetsHomeRun] = []
        self.processed_plays: Set[str] = set()
        self.queue_file = "mets_homerun_queue.pkl"
        self.max_queue_size = 20  # More generous for HRs
        self.max_processed_plays = 200
        
        # Monitoring state
        self.monitoring = False
        self.processing_gifs = False
        
        # Mets team ID
        self.mets_team_id = 121
        
        # Statistics
        self.start_time = None
        self.last_check_time = None
        self.homeruns_posted_today = 0
        self.gifs_created_today = 0
        self.homeruns_queued_today = 0
        
        # Load existing queue
        self.load_queue()
        
    def load_queue(self):
        """Load the home run queue from disk"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'rb') as f:
                    data = pickle.load(f)
                    self.homerun_queue = [MetsHomeRun.from_dict(hr_data) for hr_data in data.get('queue', [])]
                    self.processed_plays = set(data.get('processed_plays', []))
                    logger.info(f"🏠 Loaded {len(self.homerun_queue)} Mets HRs from queue")
            else:
                logger.info("🏠 No existing queue file, starting fresh")
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            self.homerun_queue = []
            self.processed_plays = set()
    
    def save_queue(self):
        """Save the home run queue to disk"""
        try:
            data = {
                'queue': [hr.to_dict() for hr in self.homerun_queue],
                'processed_plays': list(self.processed_plays),
                'saved_at': datetime.now().isoformat()
            }
            with open(self.queue_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
    
    def get_live_mets_games(self) -> List[Dict]:
        """Get all Mets games currently live or recently finished"""
        try:
            live_games = []
            today = datetime.now()
            
            # Check today and yesterday for games
            check_dates = [
                today.strftime('%Y-%m-%d'),
                (today - timedelta(days=1)).strftime('%Y-%m-%d')
            ]
            
            for date_str in check_dates:
                try:
                    url = f"{self.schedule_api_base}/schedule"
                    params = {
                        'sportId': 1,
                        'date': date_str,
                        'teamId': self.mets_team_id,  # Filter for Mets games only
                        'hydrate': 'linescore,decisions,team',
                        'useLatestGames': 'false',
                        'language': 'en'
                    }
                    
                    response = requests.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    for date_data in data.get('dates', []):
                        for game in date_data.get('games', []):
                            status = game.get('status', {}).get('statusCode', '')
                            
                            # Include live games and recently finished games
                            if status in ['I', 'F', 'O', 'W', 'D', 'PW']:
                                # For finished games, only include if recent (within 3 hours)
                                if status in ['F', 'O']:
                                    game_time = game.get('gameDate', '')
                                    if game_time:
                                        try:
                                            game_dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                                            hours_since = (datetime.now(game_dt.tzinfo) - game_dt).total_seconds() / 3600
                                            if hours_since > 3:
                                                continue
                                        except:
                                            continue
                                
                                live_games.append(game)
                                logger.info(f"🏟️ Found Mets game: {game.get('teams', {}).get('away', {}).get('team', {}).get('name', '')} @ {game.get('teams', {}).get('home', {}).get('team', {}).get('name', '')} - {status}")
                
                except Exception as e:
                    logger.error(f"Error checking games for {date_str}: {e}")
                    continue
            
            logger.info(f"📊 Found {len(live_games)} active/recent Mets games")
            return live_games
            
        except Exception as e:
            logger.error(f"Error fetching Mets games: {e}")
            return []
    
    def get_game_plays(self, game_id: int) -> List[Dict]:
        """Get all plays from a specific game"""
        try:
            url = f"{self.api_base}/game/{game_id}/feed/live"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            plays = []
            
            live_plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])
            game_info = data.get('gameData', {})
            
            for play in live_plays:
                about = play.get('about', {})
                result = play.get('result', {})
                matchup = play.get('matchup', {})
                
                play_data = {
                    'game_id': game_id,
                    'play_id': about.get('atBatIndex', 0),
                    'inning': about.get('inning', 0),
                    'half_inning': about.get('halfInning', ''),
                    'description': result.get('description', ''),
                    'event': result.get('event', ''),
                    'home_score': result.get('homeScore', 0),
                    'away_score': result.get('awayScore', 0),
                    'batter': matchup.get('batter', {}).get('fullName', ''),
                    'batter_team_id': matchup.get('batter', {}).get('team', {}).get('id'),
                    'pitcher': matchup.get('pitcher', {}).get('fullName', ''),
                    'timestamp': about.get('startTime', ''),
                    'play_data': play,
                    'game_info': game_info
                }
                plays.append(play_data)
            
            return plays
            
        except Exception as e:
            logger.error(f"Error fetching plays for game {game_id}: {e}")
            return []
    
    def is_mets_home_run(self, play: Dict) -> bool:
        """Check if this is a Mets home run"""
        event = play.get('event', '').lower()
        batter_team_id = play.get('batter_team_id')
        
        # Must be a home run event and batter must be on the Mets
        is_home_run = 'home_run' in event or event == 'home run'
        is_mets_batter = batter_team_id == self.mets_team_id
        
        if is_home_run and is_mets_batter:
            logger.info(f"⚾ METS HOME RUN: {play.get('batter')} - {play.get('description')}")
            return True
        
        return False
    
    def queue_mets_home_run(self, play: Dict, game_info: Dict):
        """Queue a Mets home run for GIF processing"""
        try:
            play_key = f"{play['game_id']}_{play['play_id']}"
            
            # Avoid duplicates
            if play_key in self.processed_plays:
                logger.debug(f"Already processed play {play_key}")
                return
            
            # Create MetsHomeRun object
            home_run = MetsHomeRun(
                play_id=play_key,
                game_id=play['game_id'],
                game_date=datetime.now().strftime('%Y-%m-%d'),
                description=play['description'],
                batter=play['batter'],
                pitcher=play['pitcher'],
                inning=play['inning'],
                half_inning=play['half_inning'],
                home_team=game_info.get('teams', {}).get('home', {}).get('name', ''),
                away_team=game_info.get('teams', {}).get('away', {}).get('name', ''),
                home_score=play['home_score'],
                away_score=play['away_score'],
                timestamp=datetime.now(),
                mlb_play_data=play['play_data'],
                game_info=game_info
            )
            
            # Add to queue
            self.homerun_queue.append(home_run)
            self.processed_plays.add(play_key)
            self.homeruns_queued_today += 1
            
            # Maintain queue size
            if len(self.homerun_queue) > self.max_queue_size:
                removed = self.homerun_queue.pop(0)
                logger.info(f"Removed oldest queued HR: {removed.batter}")
            
            # Maintain processed plays size
            if len(self.processed_plays) > self.max_processed_plays:
                # Remove oldest 50 entries
                plays_list = list(self.processed_plays)
                self.processed_plays = set(plays_list[-self.max_processed_plays + 50:])
            
            logger.info(f"🏠⚾ QUEUED METS HR: {home_run.batter} - {home_run.description}")
            logger.info(f"📊 Queue: {len(self.homerun_queue)} HRs, Processed: {len(self.processed_plays)} plays")
            
            self.save_queue()
            
        except Exception as e:
            logger.error(f"Error queuing Mets home run: {e}")
    
    def process_gif_queue(self):
        """Process the home run queue for GIF creation"""
        if self.processing_gifs:
            logger.debug("Already processing GIFs, skipping")
            return
        
        self.processing_gifs = True
        
        try:
            for home_run in self.homerun_queue[:]:  # Copy list to avoid modification issues
                if home_run.gif_created and home_run.posted:
                    continue
                
                # Skip if too many attempts
                if home_run.gif_attempts >= home_run.max_attempts:
                    logger.warning(f"Max attempts reached for {home_run.batter} HR")
                    self.cleanup_completed_homerun(home_run)
                    continue
                
                # Rate limiting - wait between attempts
                if home_run.last_attempt:
                    time_since_attempt = datetime.now() - home_run.last_attempt
                    if time_since_attempt.total_seconds() < 300:  # 5 minutes between attempts
                        continue
                
                logger.info(f"🎬 Processing GIF for {home_run.batter} HR (attempt {home_run.gif_attempts + 1})")
                
                # Update attempt tracking
                home_run.gif_attempts += 1
                home_run.last_attempt = datetime.now()
                
                try:
                    # Create GIF
                    gif_path = self.gif_integration.get_gif_for_play(
                        home_run.game_id,
                        home_run.play_id.split('_')[1] if '_' in home_run.play_id else 0,
                        home_run.game_date,
                        home_run.mlb_play_data
                    )
                    
                    if gif_path and os.path.exists(gif_path):
                        home_run.gif_created = True
                        home_run.gif_path = gif_path
                        self.gifs_created_today += 1
                        
                        logger.info(f"✅ GIF created for {home_run.batter} HR: {gif_path}")
                        
                        # Post to Discord
                        if self.post_to_discord(home_run):
                            home_run.posted = True
                            self.homeruns_posted_today += 1
                            logger.info(f"📱 Posted {home_run.batter} HR to Discord")
                        
                        # Clean up completed home run
                        self.cleanup_completed_homerun(home_run)
                        
                    else:
                        logger.warning(f"❌ Failed to create GIF for {home_run.batter} HR")
                
                except Exception as e:
                    logger.error(f"Error processing {home_run.batter} HR: {e}")
                
                # Save progress
                self.save_queue()
                
                # Small delay between processing
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Error in GIF processing: {e}")
        finally:
            self.processing_gifs = False
    
    def post_to_discord(self, home_run: MetsHomeRun) -> bool:
        """Post home run GIF to Discord"""
        try:
            if not home_run.gif_path or not os.path.exists(home_run.gif_path):
                logger.error(f"No GIF file to post for {home_run.batter}")
                return False
            
            # Get Statcast data for exit velocity and launch angle
            stats_line = ""
            try:
                statcast_data = self.gif_integration.get_statcast_data_for_play(
                    home_run.game_id,
                    home_run.play_id.split('_')[1] if '_' in home_run.play_id else 0,
                    home_run.game_date,
                    home_run.mlb_play_data
                )
                
                if statcast_data:
                    stat_parts = []
                    
                    # Exit velocity (launch_speed in CSV)
                    exit_velocity = statcast_data.get('launch_speed')
                    if exit_velocity and exit_velocity != '':
                        try:
                            ev_value = float(exit_velocity)
                            stat_parts.append(f"Exit Velocity: {ev_value:.1f} mph")
                        except:
                            pass
                    
                    # Launch angle 
                    launch_angle = statcast_data.get('launch_angle')
                    if launch_angle and launch_angle != '':
                        try:
                            la_value = float(launch_angle)
                            stat_parts.append(f"Launch Angle: {la_value:.0f}°")
                        except:
                            pass
                    
                    # Distance (optional bonus stat)
                    distance = statcast_data.get('hit_distance_sc')
                    if distance and distance != '':
                        try:
                            dist_value = float(distance)
                            stat_parts.append(f"Distance: {dist_value:.0f} ft")
                        except:
                            pass
                    
                    if stat_parts:
                        stats_line = f"\n{' | '.join(stat_parts)}\n"
                        
            except Exception as e:
                logger.warning(f"Could not get Statcast data for {home_run.batter}: {e}")
            
            # Create message content
            message = f"""🏠⚾ **{home_run.batter}** goes yard! ⚾🏠

{home_run.description}{stats_line}
#LGM"""
            
            # Post to Discord using existing integration
            success = discord_poster.post_message_with_gif(
                message=message,
                gif_path=home_run.gif_path,
                title=f"Mets HR: {home_run.batter}"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
            return False
    
    def cleanup_completed_homerun(self, home_run: MetsHomeRun):
        """Remove completed home run from queue and clean up files"""
        try:
            if home_run in self.homerun_queue:
                self.homerun_queue.remove(home_run)
                logger.info(f"🧹 Cleaned up completed HR: {home_run.batter}")
            
            # Clean up GIF file after posting
            if home_run.gif_path and os.path.exists(home_run.gif_path):
                try:
                    os.remove(home_run.gif_path)
                    logger.info(f"🗑️ Deleted GIF file: {home_run.gif_path}")
                except:
                    pass  # Don't fail if file cleanup fails
                    
        except Exception as e:
            logger.error(f"Error cleaning up home run: {e}")
    
    def monitor_games(self):
        """Main monitoring loop for Mets home runs"""
        logger.info("🚀 Starting Mets Home Run monitoring...")
        self.monitoring = True
        self.start_time = datetime.now()
        
        # Set up graceful shutdown
        def signal_handler(signum, frame):
            logger.info("📤 Shutdown signal received")
            self.stop_monitoring()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            while self.monitoring:
                try:
                    self.last_check_time = datetime.now()
                    logger.info(f"🔍 Checking for Mets games at {self.last_check_time.strftime('%H:%M:%S')}")
                    
                    # Get active Mets games
                    games = self.get_live_mets_games()
                    
                    for game in games:
                        game_id = game['gamePk']
                        
                        # Get plays from this game
                        plays = self.get_game_plays(game_id)
                        
                        # Check for Mets home runs
                        for play in plays:
                            if self.is_mets_home_run(play):
                                self.queue_mets_home_run(play, play['game_info'])
                    
                    # Process GIF queue
                    if self.homerun_queue:
                        logger.info(f"🎬 Processing {len(self.homerun_queue)} HRs in queue")
                        self.process_gif_queue()
                    
                    # Wait 2 minutes before next check
                    for i in range(120):  # 2 minutes = 120 seconds
                        if not self.monitoring:
                            break
                        time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}")
                    # Wait a bit before retrying
                    time.sleep(30)
                    
        except KeyboardInterrupt:
            logger.info("⌨️ Keyboard interrupt received")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        logger.info("🛑 Stopping Mets Home Run monitoring...")
        self.monitoring = False
        
        # Save final state
        self.save_queue()
        
        logger.info("✅ Mets Home Run Tracker stopped")
    
    def get_status(self) -> Dict:
        """Get current system status"""
        uptime = None
        if self.start_time:
            uptime = str(datetime.now() - self.start_time)
        
        return {
            'monitoring': self.monitoring,
            'processing_gifs': self.processing_gifs,
            'uptime': uptime,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'queue_size': len(self.homerun_queue),
            'processed_plays': len(self.processed_plays),
            'stats': {
                'homeruns_posted_today': self.homeruns_posted_today,
                'gifs_created_today': self.gifs_created_today,
                'homeruns_queued_today': self.homeruns_queued_today
            }
        }

def main():
    """Main function"""
    try:
        tracker = MetsHomeRunTracker()
        tracker.monitor_games()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 