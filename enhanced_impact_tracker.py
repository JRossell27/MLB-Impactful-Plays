#!/usr/bin/env python3
"""
Enhanced MLB Impact Tracker with GIF Integration
Monitors live games every 2 minutes, queues high-impact plays, creates GIFs, and posts complete tweets
"""

import os
import sys
import time
import json
import logging
import requests
import tweepy
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
from baseball_savant_gif_integration import BaseballSavantGIFIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_impact_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class QueuedPlay:
    """Represents a high-impact play queued for GIF processing"""
    play_id: str
    game_id: int
    game_date: str
    impact_score: float
    wpa: float
    description: str
    event: str
    batter: str
    pitcher: str
    inning: int
    half_inning: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    leverage_index: float
    timestamp: datetime
    mlb_play_data: Dict
    game_info: Dict
    gif_attempts: int = 0
    max_attempts: int = 5
    last_attempt: Optional[datetime] = None
    gif_created: bool = False
    tweet_posted: bool = False
    gif_path: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['last_attempt'] = self.last_attempt.isoformat() if self.last_attempt else None
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data['last_attempt']:
            data['last_attempt'] = datetime.fromisoformat(data['last_attempt'])
        return cls(**data)

class EnhancedImpactTracker:
    def __init__(self):
        self.api_base = "https://statsapi.mlb.com/api/v1.1"
        self.schedule_api_base = "https://statsapi.mlb.com/api/v1"  # Schedule uses v1 API
        self.twitter_api = self.setup_twitter()
        self.gif_integration = BaseballSavantGIFIntegration()
        
        # Queue management - Memory conscious settings for 512MB deployment
        self.play_queue: List[QueuedPlay] = []
        self.processed_plays: Set[str] = set()  # Track plays we've seen to avoid duplicates
        self.queue_file = "play_queue.pkl"
        self.max_queue_size = 10  # Limit queue size for memory conservation
        self.max_processed_plays = 100  # Limit processed plays tracking
        
        # Monitoring state
        self.monitoring = False
        self.processing_gifs = False
        
        # Statistics
        self.start_time = None
        self.last_check_time = None
        self.tweets_posted_today = 0
        self.gifs_created_today = 0
        self.plays_queued_today = 0
        
        # Load existing queue
        self.load_queue()
        
        # Team hashtags for social media
        self.team_hashtags = {
            'LAA': '#Angels', 'HOU': '#Astros', 'OAK': '#Athletics', 'TOR': '#BlueJays',
            'ATL': '#Braves', 'MIL': '#Brewers', 'STL': '#Cardinals', 'CHC': '#Cubs',
            'ARI': '#Dbacks', 'LAD': '#Dodgers', 'SF': '#SFGiants', 'CLE': '#Guardians',
            'SEA': '#Mariners', 'MIA': '#Marlins', 'NYM': '#Mets', 'WSH': '#Nationals',
            'BAL': '#Orioles', 'SD': '#Padres', 'PHI': '#Phillies', 'PIT': '#Pirates',
            'TEX': '#Rangers', 'TB': '#Rays', 'BOS': '#RedSox', 'CIN': '#Reds',
            'COL': '#Rockies', 'KC': '#Royals', 'DET': '#Tigers', 'MIN': '#Twins',
            'CWS': '#WhiteSox', 'NYY': '#Yankees'
        }
    
    def setup_twitter(self):
        """Initialize Twitter API connection"""
        try:
            # Check for both naming conventions
            consumer_key = os.getenv('TWITTER_CONSUMER_KEY') or os.getenv('TWITTER_API_KEY')
            consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET') or os.getenv('TWITTER_API_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            
            missing_vars = []
            if not consumer_key:
                missing_vars.append('TWITTER_CONSUMER_KEY (or TWITTER_API_KEY)')
            if not consumer_secret:
                missing_vars.append('TWITTER_CONSUMER_SECRET (or TWITTER_API_SECRET)')
            if not access_token:
                missing_vars.append('TWITTER_ACCESS_TOKEN')
            if not access_token_secret:
                missing_vars.append('TWITTER_ACCESS_TOKEN_SECRET')
            
            if missing_vars:
                logger.warning(f"Twitter credentials not found in environment variables: {', '.join(missing_vars)}")
                return None
            
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_token, access_token_secret)
            
            api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Test the connection
            api.verify_credentials()
            logger.info("✅ Twitter API connected successfully")
            return api
            
        except Exception as e:
            logger.error(f"Twitter API setup failed: {e}")
            return None
    
    def retry_twitter_setup(self):
        """Retry Twitter setup - useful if credentials weren't available at startup"""
        if self.twitter_api is None:
            logger.info("🔄 Retrying Twitter API setup...")
            self.twitter_api = self.setup_twitter()
            return self.twitter_api is not None
        return True
    
    def load_queue(self):
        """Load the play queue from disk"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'rb') as f:
                    data = pickle.load(f)
                    self.play_queue = [QueuedPlay.from_dict(play_data) for play_data in data.get('queue', [])]
                    self.processed_plays = set(data.get('processed_plays', []))
                    logger.info(f"📂 Loaded {len(self.play_queue)} plays from queue")
            else:
                logger.info("📂 No existing queue file, starting fresh")
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            self.play_queue = []
            self.processed_plays = set()
    
    def save_queue(self):
        """Save the play queue to disk"""
        try:
            data = {
                'queue': [play.to_dict() for play in self.play_queue],
                'processed_plays': list(self.processed_plays),
                'saved_at': datetime.now().isoformat()
            }
            with open(self.queue_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
    
    def get_live_games(self) -> List[Dict]:
        """Get all games currently live or recently finished - checks multiple days during off-season"""
        try:
            live_games = []
            today = datetime.now()
            
            # During baseball season, check today + yesterday for recently finished games
            # During off-season, expand the search window
            check_dates = []
            
            # Always check today
            check_dates.append(today.strftime('%Y-%m-%d'))
            
            # Check yesterday for recently finished games (video availability)
            yesterday = today - timedelta(days=1)
            check_dates.append(yesterday.strftime('%Y-%m-%d'))
            
            # During potential off-season (November-February), also check recent dates
            if today.month in [11, 12, 1, 2]:
                for i in range(2, 7):  # Check 5 more days back
                    past_date = today - timedelta(days=i)
                    check_dates.append(past_date.strftime('%Y-%m-%d'))
            
            # Check each date for games
            for date_str in check_dates:
                try:
                    url = f"{self.schedule_api_base}/schedule"
                    params = {
                        'sportId': 1,
                        'date': date_str,
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
                            if status in ['I', 'F', 'O', 'W', 'D', 'PW']:  # In Progress, Final, Final-Other, Warmup, Delayed, Pre-Warmup
                                # For finished games, only include if recent (within 3 hours for video availability)
                                if status in ['F', 'O']:
                                    game_time = game.get('gameDate', '')
                                    if game_time:
                                        try:
                                            game_dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                                            hours_since = (datetime.now(game_dt.tzinfo) - game_dt).total_seconds() / 3600
                                            if hours_since > 3:  # Skip games older than 3 hours
                                                continue
                                        except:
                                            pass  # If we can't parse time, include the game anyway
                                
                                if game not in live_games:  # Avoid duplicates
                                    live_games.append(game)
                                    
                except requests.exceptions.RequestException as e:
                    logger.debug(f"No games found for {date_str}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error checking games for {date_str}: {e}")
                    continue
            
            logger.debug(f"Found {len(live_games)} live/recent games across {len(check_dates)} dates")
            
            # If no games found, log appropriate message
            if len(live_games) == 0:
                current_month = today.month
                if current_month in [11, 12, 1, 2]:
                    logger.info("🏈 Off-season: No live MLB games found (expected November-February)")
                elif current_month in [3]:
                    logger.info("🌸 Spring Training: Limited games may be available")
                else:
                    logger.info("⚾ No live/recent MLB games found - checking again in 2 minutes")
            
            return live_games
            
        except Exception as e:
            logger.error(f"Error fetching live games: {e}")
            return []
    
    def get_game_plays(self, game_id: int) -> List[Dict]:
        """Get all plays from a specific game with live feed data"""
        try:
            url = f"{self.api_base}/game/{game_id}/feed/live"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            plays = []
            
            # Get plays from live feed which includes WPA data
            live_plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])
            
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
                    'leverage_index': about.get('leverageIndex', 1.0),
                    'win_probability_home': about.get('homeWinExpectancy', 0.5),
                    'win_probability_away': about.get('awayWinExpectancy', 0.5),
                    'wpa': result.get('wpa', 0.0),  # Win Probability Added from MLB
                    'batter': matchup.get('batter', {}).get('fullName', ''),
                    'pitcher': matchup.get('pitcher', {}).get('fullName', ''),
                    'timestamp': about.get('startTime', ''),
                    'play_data': play
                }
                plays.append(play_data)
            
            return plays
            
        except Exception as e:
            logger.error(f"Error fetching plays for game {game_id}: {e}")
            return []
    
    def calculate_impact_score(self, play: Dict) -> float:
        """Calculate impact score using MLB's WPA data when available"""
        try:
            # Use actual MLB WPA (Win Probability Added) if available
            wpa = play.get('wpa', 0.0)
            if wpa != 0.0:
                # Convert WPA to percentage impact
                impact = abs(wpa)
                logger.debug(f"Using MLB WPA: {wpa} -> {impact:.1%} impact")
                return impact
            
            # Fallback: Calculate based on leverage and situation
            leverage = play.get('leverage_index', 1.0)
            inning = play.get('inning', 1)
            event = play.get('event', '').lower()
            
            # Base impact estimation
            base_impact = 0.05  # 5% base
            
            # Event type bonuses
            if 'home_run' in event:
                base_impact = 0.12
            elif 'triple' in event:
                base_impact = 0.10
            elif 'double' in event:
                base_impact = 0.08
            elif 'walk_off' in event or 'walkoff' in event:
                base_impact = 0.25
            elif 'grand_slam' in event:
                base_impact = 0.20
            
            # Leverage multiplier
            impact = base_impact * leverage
            
            # Late game bonus
            if inning >= 9:
                impact *= 1.3
            elif inning >= 7:
                impact *= 1.1
            
            return round(impact, 4)
            
        except Exception as e:
            logger.error(f"Error calculating impact: {e}")
            return 0.0
    
    def is_high_impact_play(self, impact_score: float, leverage: float = 1.0) -> bool:
        """Determine if a play qualifies as marquee moment for queuing"""
        # MARQUEE MOMENTS ONLY - Focus on truly game-changing plays
        
        # PRIMARY: Massive WPA impact (40%+ win probability swing)
        if impact_score >= 0.40:  # 40%+ WP swing - elite marquee moments
            return True
            
        # SECONDARY: Very high impact in clutch situations
        if impact_score >= 0.30 and leverage >= 3.0:  # 30%+ swing in super high leverage
            return True
            
        # TERTIARY: Walk-off situations get lower threshold
        if impact_score >= 0.25 and leverage >= 2.5:  # 25%+ in very clutch moments
            return True
            
        return False
    
    def queue_high_impact_play(self, play: Dict, game_info: Dict, impact_score: float):
        """Queue a high-impact play for GIF processing and posting"""
        try:
            # Create unique play ID to avoid duplicates
            play_id = f"{play['game_id']}_{play['play_id']}_{play['inning']}_{play['half_inning']}"
            
            if play_id in self.processed_plays:
                logger.debug(f"Play {play_id} already processed, skipping")
                return False
            
            # Memory management: Limit queue size
            if len(self.play_queue) >= self.max_queue_size:
                # Remove oldest completed plays first
                completed_plays = [p for p in self.play_queue if p.tweet_posted]
                if completed_plays:
                    oldest_completed = min(completed_plays, key=lambda x: x.timestamp)
                    self.play_queue.remove(oldest_completed)
                    logger.info(f"Removed completed play to free memory: {oldest_completed.event}")
                else:
                    # If no completed plays, remove oldest failed play
                    oldest_failed = [p for p in self.play_queue if p.gif_attempts >= p.max_attempts]
                    if oldest_failed:
                        to_remove = min(oldest_failed, key=lambda x: x.timestamp)
                        self.play_queue.remove(to_remove)
                        logger.info(f"Removed failed play to free memory: {to_remove.event}")
                    else:
                        logger.warning(f"Queue at max size ({self.max_queue_size}), skipping new play")
                        return False
            
            # Memory management: Limit processed plays tracking
            if len(self.processed_plays) >= self.max_processed_plays:
                # Remove oldest 20% of processed plays
                to_remove = list(self.processed_plays)[:20]
                for old_id in to_remove:
                    self.processed_plays.discard(old_id)
                logger.debug(f"Cleaned up {len(to_remove)} old processed play IDs")
            
            # Create queued play object
            queued_play = QueuedPlay(
                play_id=play_id,
                game_id=play['game_id'],
                game_date=datetime.now().strftime('%Y-%m-%d'),
                impact_score=impact_score,
                wpa=play.get('wpa', 0.0),
                description=play.get('description', ''),
                event=play.get('event', ''),
                batter=play.get('batter', ''),
                pitcher=play.get('pitcher', ''),
                inning=play.get('inning', 0),
                half_inning=play.get('half_inning', ''),
                home_team=game_info.get('home_team', 'HOME'),
                away_team=game_info.get('away_team', 'AWAY'),
                home_score=play.get('home_score', 0),
                away_score=play.get('away_score', 0),
                leverage_index=play.get('leverage_index', 1.0),
                timestamp=datetime.now(),
                mlb_play_data=play.get('play_data', {}),
                game_info=game_info
            )
            
            # Add to queue
            self.play_queue.append(queued_play)
            self.processed_plays.add(play_id)
            self.plays_queued_today += 1
            
            logger.info(f"🎯 QUEUED HIGH-IMPACT PLAY!")
            logger.info(f"   {queued_play.event} - {impact_score:.1%} WPA impact")
            logger.info(f"   {queued_play.away_team} @ {queued_play.home_team} (Inning {queued_play.inning})")
            logger.info(f"   Queue size: {len(self.play_queue)}/{self.max_queue_size}")
            
            # Save queue to disk
            self.save_queue()
            
            return True
            
        except Exception as e:
            logger.error(f"Error queueing play: {e}")
            return False
    
    def format_complete_tweet_text(self, queued_play: QueuedPlay) -> str:
        """Format tweet text for the complete post with GIF"""
        try:
            description = queued_play.description
            # Truncate if too long to leave room for other content
            if len(description) > 100:
                description = description[:97] + "..."
            
            inning_text = f"{'T' if queued_play.half_inning == 'top' else 'B'}{queued_play.inning}"
            
            tweet = f"⭐ MARQUEE MOMENT!\n\n"
            tweet += f"{description}\n\n"
            tweet += f"📊 Impact: {queued_play.impact_score:.1%} WP change\n"
            tweet += f"⚾ {queued_play.away_team} {queued_play.away_score} - {queued_play.home_score} {queued_play.home_team} ({inning_text})\n\n"
            
            # Add official team hashtags
            hashtags = []
            if queued_play.away_team in self.team_hashtags:
                hashtags.append(self.team_hashtags[queued_play.away_team])
            if queued_play.home_team in self.team_hashtags and queued_play.home_team != queued_play.away_team:
                hashtags.append(self.team_hashtags[queued_play.home_team])
            
            if hashtags:
                tweet += " ".join(hashtags)
            else:
                tweet += "#MLB"
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error formatting tweet: {e}")
            return "Marquee moment detected! ⭐"
    
    def post_complete_tweet_with_gif(self, queued_play: QueuedPlay) -> bool:
        """Post the complete tweet with both text and GIF"""
        try:
            if not self.twitter_api:
                logger.warning("Twitter API not available")
                return False
            
            if not queued_play.gif_path or not os.path.exists(queued_play.gif_path):
                logger.error(f"GIF file not found: {queued_play.gif_path}")
                return False
            
            # Format tweet text
            tweet_text = self.format_complete_tweet_text(queued_play)
            
            # Upload GIF
            try:
                media = self.twitter_api.media_upload(queued_play.gif_path)
                logger.info(f"✅ GIF uploaded to Twitter: {media.media_id}")
                
                # Post tweet with GIF
                tweet = self.twitter_api.update_status(
                    status=tweet_text,
                    media_ids=[media.media_id]
                )
                
                queued_play.tweet_posted = True
                self.tweets_posted_today += 1
                
                logger.info(f"🎉 COMPLETE TWEET POSTED!")
                logger.info(f"   Tweet ID: {tweet.id}")
                logger.info(f"   Play: {queued_play.event}")
                logger.info(f"   Impact: {queued_play.impact_score:.1%}")
                
                # Immediately post the complete tweet
                if self.post_complete_tweet_with_gif(queued_play):
                    logger.info(f"🎉 Complete tweet posted for {queued_play.play_id}")
                    
                    # Aggressive cleanup for memory conservation
                    self.cleanup_completed_play(queued_play)
                else:
                    logger.error(f"❌ Failed to post tweet for {queued_play.play_id}")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to upload GIF or post tweet: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting complete tweet: {e}")
            return False
    
    def process_gif_queue(self):
        """Process queued plays to create GIFs and post tweets"""
        logger.info("🎬 Starting GIF processing thread...")
        
        while self.processing_gifs:
            try:
                # Process plays in queue
                for i, queued_play in enumerate(self.play_queue):
                    if queued_play.tweet_posted:
                        continue
                    
                    # Check if we should attempt to create GIF
                    now = datetime.now()
                    
                    # Don't retry too frequently (wait at least 5 minutes between attempts)
                    if (queued_play.last_attempt and 
                        (now - queued_play.last_attempt).total_seconds() < 300):
                        continue
                    
                    # Give up after max attempts
                    if queued_play.gif_attempts >= queued_play.max_attempts:
                        logger.warning(f"❌ Giving up on GIF for play {queued_play.play_id} after {queued_play.max_attempts} attempts")
                        continue
                    
                    # Try to create GIF
                    logger.info(f"🎬 Attempting to create GIF for play {queued_play.play_id} (attempt {queued_play.gif_attempts + 1})")
                    
                    queued_play.gif_attempts += 1
                    queued_play.last_attempt = now
                    
                    try:
                        gif_path = self.gif_integration.get_gif_for_play(
                            game_id=queued_play.game_id,
                            play_id=queued_play.mlb_play_data.get('atBatIndex', 0),
                            game_date=queued_play.game_date,
                            mlb_play_data=queued_play.mlb_play_data
                        )
                        
                        if gif_path and os.path.exists(gif_path):
                            queued_play.gif_created = True
                            queued_play.gif_path = gif_path
                            self.gifs_created_today += 1
                            
                            logger.info(f"✅ GIF created successfully for {queued_play.play_id}")
                            
                            # Immediately post the complete tweet
                            if self.post_complete_tweet_with_gif(queued_play):
                                logger.info(f"🎉 Complete tweet posted for {queued_play.play_id}")
                                
                                # Aggressive cleanup for memory conservation
                                self.cleanup_completed_play(queued_play)
                            else:
                                logger.error(f"❌ Failed to post tweet for {queued_play.play_id}")
                        else:
                            logger.warning(f"⏳ GIF not yet available for play {queued_play.play_id}")
                    
                    except Exception as e:
                        logger.error(f"Error creating GIF for play {queued_play.play_id}: {e}")
                    
                    # Save queue state after each attempt
                    self.save_queue()
                
                # Clean up completed plays from queue
                self.play_queue = [play for play in self.play_queue if not play.tweet_posted]
                
                # Sleep before next processing cycle
                time.sleep(60)  # Check every minute for GIF creation
                
            except Exception as e:
                logger.error(f"Error in GIF processing loop: {e}")
                time.sleep(60)
    
    def cleanup_completed_play(self, queued_play: QueuedPlay):
        """Aggressively clean up resources for a completed play"""
        try:
            # Remove GIF file immediately if it exists
            if queued_play.gif_path and os.path.exists(queued_play.gif_path):
                os.remove(queued_play.gif_path)
                logger.debug(f"Cleaned up GIF file: {queued_play.gif_path}")
            
            # Clear large data structures from the play object
            queued_play.mlb_play_data = {}
            queued_play.game_info = {}
            
            # Force garbage collection hint for Python
            import gc
            gc.collect()
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def monitor_games(self):
        """Main monitoring loop - checks every 2 minutes for high-impact plays"""
        logger.info("🚀 Starting enhanced impact monitoring with GIF integration...")
        logger.info("🔄 Continuous monitoring: Will check for MLB games every 2 minutes year-round")
        self.monitoring = True
        self.processing_gifs = True
        self.start_time = datetime.now()
        
        # Start GIF processing thread
        gif_thread = threading.Thread(target=self.process_gif_queue, daemon=True)
        gif_thread.start()
        
        scan_count = 0
        
        while self.monitoring:
            try:
                scan_count += 1
                start_time = time.time()
                self.last_check_time = datetime.now()
                
                logger.debug(f"🔍 Starting scan #{scan_count} at {self.last_check_time.strftime('%H:%M:%S')}")
                
                # Get live games
                live_games = self.get_live_games()
                
                high_impact_plays_found = 0
                total_plays_checked = 0
                
                for game in live_games:
                    game_id = game.get('gamePk')
                    if not game_id:
                        continue
                    
                    # Get game info
                    game_info = {
                        'home_team': game.get('teams', {}).get('home', {}).get('team', {}).get('abbreviation', 'HOME'),
                        'away_team': game.get('teams', {}).get('away', {}).get('team', {}).get('abbreviation', 'AWAY'),
                        'status': game.get('status', {}).get('statusCode', ''),
                        'game_id': game_id
                    }
                    
                    # Get plays from this game
                    plays = self.get_game_plays(game_id)
                    total_plays_checked += len(plays)
                    
                    # Process all plays for impact
                    for play in plays:
                        impact_score = self.calculate_impact_score(play)
                        
                        # Check if this is a marquee moment worth queuing
                        if self.is_high_impact_play(impact_score, play.get('leverage_index', 1.0)):
                            high_impact_plays_found += 1
                            logger.info(f"⭐ High-impact play detected: {impact_score:.1%} impact")
                            self.queue_high_impact_play(play, game_info, impact_score)
                
                # Calculate sleep time to maintain 2-minute intervals
                elapsed = time.time() - start_time
                sleep_time = max(0, 120 - elapsed)  # 2 minutes = 120 seconds
                
                # Comprehensive status logging
                logger.info(f"📊 Scan #{scan_count} completed in {elapsed:.1f}s")
                logger.info(f"   Live/recent games found: {len(live_games)}")
                logger.info(f"   Total plays checked: {total_plays_checked}")
                logger.info(f"   High-impact plays found this scan: {high_impact_plays_found}")
                logger.info(f"   Daily totals - Queued: {self.plays_queued_today}, GIFs: {self.gifs_created_today}, Tweets: {self.tweets_posted_today}")
                logger.info(f"   Queue status: {len(self.play_queue)}/{self.max_queue_size} plays")
                logger.info(f"   System uptime: {str(datetime.now() - self.start_time).split('.')[0]}")
                logger.info(f"   Next scan in {sleep_time:.1f}s...")
                
                # If it's been a while since we found games, remind user system is still active
                if len(live_games) == 0 and scan_count % 30 == 0:  # Every hour when no games
                    logger.info(f"🤖 System active: Completed {scan_count} scans, monitoring continuously for MLB games")
                
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop (scan #{scan_count}): {e}")
                logger.info("🔄 Continuing monitoring in 2 minutes...")
                time.sleep(120)  # Wait 2 minutes before retrying
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.monitoring = False
        self.processing_gifs = False
        logger.info("Stopping enhanced monitoring...")
        
        # Save final queue state
        self.save_queue()
    
    def get_status(self) -> Dict:
        """Get current system status"""
        status = {
            'monitoring': self.monitoring,
            'processing_gifs': self.processing_gifs,
            'twitter_connected': self.twitter_api is not None,
            'last_check_time': self.last_check_time.strftime('%Y-%m-%d %H:%M:%S ET') if self.last_check_time else 'Never',
            'uptime': str(datetime.now() - self.start_time).split('.')[0] if self.start_time else 'Not started',
            'plays_queued_today': self.plays_queued_today,
            'gifs_created_today': self.gifs_created_today,
            'tweets_posted_today': self.tweets_posted_today,
            'current_queue_size': len(self.play_queue),
            'max_queue_size': self.max_queue_size,
            'processed_plays_count': len(self.processed_plays),
            'max_processed_plays': self.max_processed_plays,
            'queue_details': []
        }
        
        # Add queue details
        for play in self.play_queue:
            if not play.tweet_posted:
                status['queue_details'].append({
                    'event': play.event,
                    'impact': f"{play.impact_score:.1%}",
                    'teams': f"{play.away_team} @ {play.home_team}",
                    'attempts': play.gif_attempts,
                    'gif_created': play.gif_created,
                    'tweet_posted': play.tweet_posted,
                    'timestamp': play.timestamp.strftime('%H:%M:%S')
                })
        
        return status

def main():
    """Main function to start the enhanced tracker"""
    tracker = EnhancedImpactTracker()
    
    try:
        tracker.monitor_games()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    finally:
        tracker.stop_monitoring()

if __name__ == "__main__":
    main() 