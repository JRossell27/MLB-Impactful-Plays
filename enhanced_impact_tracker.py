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
    
    def get_enhanced_wp_data_from_savant(self, game_id: int, play_data: Dict) -> Dict:
        """
        Fetch Baseball Savant's delta_home_win_exp data for a specific play
        This is the actual WP% change that Baseball Savant calculates
        """
        try:
            # Get game date from the game_id using MLB API
            try:
                # Check if we have a test_date override (for historical testing)
                if 'test_date' in play_data:
                    game_date_str = play_data['test_date']
                    logger.debug(f"Using test date override: {game_date_str}")
                else:
                    game_url = f"{self.api_base}/game/{game_id}/feed/live"
                    game_response = requests.get(game_url, timeout=15)
                    game_response.raise_for_status()
                    game_data = game_response.json()
                    
                    # Extract game date from game data
                    game_date_str = game_data.get('gameData', {}).get('datetime', {}).get('originalDate', '')
                    if not game_date_str:
                        # Fallback to the test date if we're processing historical data
                        game_date_str = "2025-06-17"  # The test date
                    
                    logger.debug(f"Using game date from MLB API: {game_date_str}")
                
            except Exception as e:
                logger.debug(f"Could not get game date from MLB API: {e}, using fallback")
                game_date_str = "2025-06-17"  # Fallback to test date
            
            # Baseball Savant Statcast search parameters for the specific game
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
                'game_date_gt': game_date_str,
                'game_date_lt': game_date_str,
                'hfInfield': '',
                'team': '',
                'position': '',
                'hfOutfield': '',
                'hfRO': '',
                'home_road': '',
                'game_pk': game_id,  # Specific game
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
            url = "https://baseballsavant.mlb.com/statcast_search/csv"
            logger.debug(f"Fetching Baseball Savant data for game {game_id} on {game_date_str}")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200 and response.text.strip():
                # Parse CSV data to look for matching play with delta_home_win_exp
                csv_reader = csv.DictReader(StringIO(response.text))
                
                target_inning = play_data.get('inning')
                target_event = play_data.get('event', '').lower()
                target_batter = play_data.get('batter', '')
                target_at_bat_index = play_data.get('play_id', 0)
                
                logger.debug(f"Looking for: Inning {target_inning}, Event: '{target_event}', Batter: '{target_batter}'")
                
                best_matches = []
                
                for row in csv_reader:
                    # Try to match the play by multiple criteria
                    match_score = 0
                    
                    # Inning match
                    if str(row.get('inning', '')) == str(target_inning):
                        match_score += 30
                    
                    # Event type match
                    row_event = row.get('events', '').lower()
                    if target_event and row_event:
                        if target_event in row_event or row_event in target_event:
                            match_score += 50
                        if target_event == row_event:
                            match_score += 100
                    
                    # Batter name match
                    row_batter = row.get('player_name', '')
                    if target_batter and row_batter:
                        if target_batter.lower() in row_batter.lower() or row_batter.lower() in target_batter.lower():
                            match_score += 40
                    
                    # At-bat index proximity (if available)
                    row_at_bat = row.get('at_bat_number', '')
                    if row_at_bat and str(row_at_bat) == str(target_at_bat_index):
                        match_score += 30
                    
                    # Check for delta_home_win_exp data
                    delta_home_win_exp = row.get('delta_home_win_exp', '')
                    if delta_home_win_exp and delta_home_win_exp != '' and delta_home_win_exp != 'null':
                        try:
                            wp_change = float(delta_home_win_exp)
                            if abs(wp_change) > 0.01:  # At least 1% change
                                match_score += 20
                                best_matches.append((match_score, wp_change, row))
                        except (ValueError, TypeError):
                            continue
                
                # Sort by match score and take the best
                if best_matches:
                    best_matches.sort(key=lambda x: x[0], reverse=True)
                    best_score, wp_change, best_row = best_matches[0]
                    
                    if best_score >= 50:  # Minimum confidence threshold
                        logger.info(f"Found Baseball Savant WP% change: {wp_change:.1%} for {target_event} (match score: {best_score})")
                        return {
                            'delta_home_win_exp': wp_change,
                            'source': 'baseball_savant_csv',
                            'matched_event': best_row.get('events', ''),
                            'matched_inning': best_row.get('inning'),
                            'batter_name': best_row.get('player_name', ''),
                            'match_score': best_score
                        }
                    else:
                        logger.debug(f"Best match score {best_score} below threshold for {target_event}")
                else:
                    logger.debug(f"No matches with delta_home_win_exp data found")
            else:
                logger.debug(f"No Baseball Savant data returned (status: {response.status_code})")
            
            return {}
            
        except Exception as e:
            logger.debug(f"Error fetching Baseball Savant WP data: {e}")
            return {}

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
        """Use Baseball Savant's delta_home_win_exp as primary metric, fall back to MLB WPA"""
        try:
            # PRIMARY: Use Baseball Savant's delta_home_win_exp directly (this is the WP% change you want)
            delta_home_win_exp = play.get('delta_home_win_exp', 0.0)
            if delta_home_win_exp != 0.0:
                # Convert to absolute value to get magnitude of impact
                impact = abs(delta_home_win_exp)
                logger.debug(f"Using Baseball Savant delta_home_win_exp: {delta_home_win_exp} -> {impact:.1%} impact")
                return impact
            
            # SECONDARY: Use actual MLB WPA (Win Probability Added) if available
            wpa = play.get('wpa', 0.0)
            if wpa != 0.0:
                # Convert WPA to percentage impact
                impact = abs(wpa)
                logger.debug(f"Using MLB WPA: {wpa} -> {impact:.1%} impact")
                return impact
            
            # DEBUG: Log what data we do have
            available_data = {
                'event': play.get('event', 'Unknown'),
                'description': play.get('description', '')[:50] + '...' if len(play.get('description', '')) > 50 else play.get('description', ''),
                'leverage_index': play.get('leverage_index', 'missing'),
                'win_probability_home': play.get('win_probability_home', 'missing'),
                'inning': play.get('inning', 'missing'),
                'half_inning': play.get('half_inning', 'missing')
            }
            logger.debug(f"No WPA/delta_home_win_exp data available for play: {available_data}")
            
            # FALLBACK: Enhanced estimation based on play type and situation
            # This gives us the actual WP% swing estimation when primary sources are missing
            win_prob_home = play.get('win_probability_home', 0.5)
            win_prob_away = play.get('win_probability_away', 0.5)
            
            leverage = play.get('leverage_index', 1.0)
            inning = play.get('inning', 1)
            event = play.get('event', '').lower()
            
            # Estimate the WP% change based on the play type and situation
            estimated_wp_change = 0.0
            
            # Base WP changes for different event types (these are estimates)
            if 'home_run' in event:
                if inning >= 9:
                    estimated_wp_change = 0.25 * leverage  # Late innings are more impactful
                else:
                    estimated_wp_change = 0.15 * leverage
            elif 'triple' in event:
                estimated_wp_change = 0.12 * leverage
            elif 'double' in event:
                estimated_wp_change = 0.08 * leverage
            elif 'single' in event:
                estimated_wp_change = 0.06 * leverage
            elif 'walk' in event or 'base_on_balls' in event:
                estimated_wp_change = 0.04 * leverage
            elif 'strikeout' in event:
                estimated_wp_change = -0.05 * leverage
            elif 'out' in event:
                estimated_wp_change = -0.03 * leverage
            elif 'walk_off' in event or 'walkoff' in event:
                estimated_wp_change = 0.50  # Walk-offs are always huge
            elif 'grand_slam' in event:
                estimated_wp_change = 0.40 * leverage
            
            # Apply situational modifiers
            if inning >= 9:
                estimated_wp_change *= 1.5  # Late game situations are more crucial
            elif inning >= 7:
                estimated_wp_change *= 1.2
            
            # Use the absolute value to get the magnitude of impact
            impact = abs(estimated_wp_change)
            
            logger.debug(f"Estimated WP% impact for {event}: {impact:.1%} (leverage: {leverage:.2f}, inning: {inning})")
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
            
            # Get the actual game date from the game info or MLB API
            actual_game_date = None
            
            # First try to get it from the test_date if this is a test
            if 'test_date' in play:
                actual_game_date = play['test_date']
                logger.debug(f"Using test date for queued play: {actual_game_date}")
            else:
                # Try to get game date from MLB API
                try:
                    game_url = f"{self.api_base}/game/{play['game_id']}/feed/live"
                    game_response = requests.get(game_url, timeout=15)
                    if game_response.status_code == 200:
                        game_data = game_response.json()
                        actual_game_date = game_data.get('gameData', {}).get('datetime', {}).get('originalDate', '')
                        if actual_game_date:
                            logger.debug(f"Got actual game date from MLB API: {actual_game_date}")
                except Exception as e:
                    logger.debug(f"Could not get game date from MLB API: {e}")
            
            # Fallback to today's date if we can't get the actual game date
            if not actual_game_date:
                actual_game_date = datetime.now().strftime('%Y-%m-%d')
                logger.debug(f"Using fallback date: {actual_game_date}")
            
            # Create queued play object
            queued_play = QueuedPlay(
                play_id=play_id,
                game_id=play['game_id'],
                game_date=actual_game_date,  # Use actual game date instead of today
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
    
    def post_to_discord(self, queued_play: QueuedPlay) -> bool:
        """Post the high-impact play to Discord with GIF and formatted text"""
        try:
            # Prepare play data for Discord formatting
            play_data = {
                'event': queued_play.event,
                'impact_score': queued_play.impact_score,
                'away_team': queued_play.away_team,
                'home_team': queued_play.home_team,
                'away_score': queued_play.away_score,
                'home_score': queued_play.home_score,
                'inning': queued_play.inning,
                'half_inning': queued_play.half_inning,
                'description': queued_play.description,
                'batter': queued_play.batter,
                'pitcher': queued_play.pitcher,
                'leverage_index': queued_play.leverage_index,
                'wpa': queued_play.wpa
            }
            
            # Post to Discord with GIF if available
            gif_path = None
            if queued_play.gif_path and os.path.exists(queued_play.gif_path):
                gif_path = queued_play.gif_path
            
            success = discord_poster.post_impact_play(play_data, gif_path)
            
            if success:
                queued_play.tweet_posted = True  # Keep this name for compatibility
                self.tweets_posted_today += 1   # Count Discord posts same as tweets
                
                logger.info(f"🎉 POSTED TO DISCORD!")
                logger.info(f"   Play: {queued_play.event}")
                logger.info(f"   Impact: {queued_play.impact_score:.1%}")
                logger.info(f"   Teams: {queued_play.away_team} @ {queued_play.home_team}")
                
                return True
            else:
                logger.error(f"❌ Failed to post to Discord for {queued_play.play_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
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
                            if self.post_to_discord(queued_play):
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
                        # STEP 1: Enhance play with Baseball Savant WP% data first
                        savant_data = self.get_enhanced_wp_data_from_savant(game_id, play)
                        if savant_data and 'delta_home_win_exp' in savant_data:
                            play['delta_home_win_exp'] = savant_data['delta_home_win_exp']
                            logger.debug(f"Enhanced play with Baseball Savant WP%: {savant_data['delta_home_win_exp']:.1%}")
                        
                        # STEP 2: Calculate impact score (now with Baseball Savant data as primary source)
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
                logger.info(f"   Queue status: {len(self.play_queue)}/{self.max_queue_size}")
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