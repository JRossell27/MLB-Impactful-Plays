#!/usr/bin/env python3
"""
Live MLB Impact Tracker - Continuously monitors live games for WPA data
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
import requests
import pytz
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import pickle

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Eastern timezone
eastern_tz = pytz.timezone('US/Eastern')

@dataclass
class ImpactPlay:
    """Represents a high-impact play with all necessary metadata"""
    impact: float
    game_id: str
    play_id: str
    wpa: float
    event: str
    description: str
    batter: str
    pitcher: str
    inning: int
    half_inning: str
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    timestamp: str
    has_real_wpa: bool = True
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class LiveImpactTracker:
    """Main class for tracking live impact plays"""
    
    def __init__(self, data_file="daily_top_plays.pkl"):
        self.data_file = data_file
        self.top_plays: List[ImpactPlay] = []
        self.processed_plays = set()  # Track plays we've already processed
        self.is_running = False
        self.load_daily_data()
    
    def load_daily_data(self):
        """Load today's top plays from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'rb') as f:
                    data = pickle.load(f)
                    # Check if data is from today
                    if data.get('date') == self.get_today_date():
                        self.top_plays = [ImpactPlay.from_dict(play_data) for play_data in data.get('plays', [])]
                        self.processed_plays = set(data.get('processed_plays', []))
                        logger.info(f"📂 Loaded {len(self.top_plays)} plays from today's data")
                    else:
                        logger.info("📅 Starting fresh for new day")
                        self.reset_daily_data()
            else:
                logger.info("📂 No existing data file, starting fresh")
                self.reset_daily_data()
        except Exception as e:
            logger.error(f"❌ Error loading daily data: {e}")
            self.reset_daily_data()
    
    def save_daily_data(self):
        """Save current top plays to file"""
        try:
            data = {
                'date': self.get_today_date(),
                'plays': [play.to_dict() for play in self.top_plays],
                'processed_plays': list(self.processed_plays),
                'last_updated': datetime.now(eastern_tz).isoformat()
            }
            with open(self.data_file, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"💾 Saved daily data with {len(self.top_plays)} plays")
        except Exception as e:
            logger.error(f"❌ Error saving daily data: {e}")
    
    def save_previous_day_data(self):
        """Save current top plays as previous day's data for tweeting"""
        try:
            previous_date = self.get_previous_date()
            previous_data_file = f"daily_top_plays_{previous_date}.pkl"
            
            data = {
                'date': previous_date,
                'plays': [play.to_dict() for play in self.top_plays],
                'processed_plays': list(self.processed_plays),
                'last_updated': datetime.now(eastern_tz).isoformat(),
                'finalized': True  # Mark as finalized for tweeting
            }
            
            with open(previous_data_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"💾 Saved previous day data ({previous_date}) with {len(self.top_plays)} plays")
        except Exception as e:
            logger.error(f"❌ Error saving previous day data: {e}")
    
    def load_previous_day_data(self) -> List[ImpactPlay]:
        """Load the previous day's top plays for tweeting"""
        try:
            previous_date = self.get_previous_date()
            previous_data_file = f"daily_top_plays_{previous_date}.pkl"
            
            if os.path.exists(previous_data_file):
                with open(previous_data_file, 'rb') as f:
                    data = pickle.load(f)
                    if data.get('date') == previous_date:
                        plays = [ImpactPlay.from_dict(play_data) for play_data in data.get('plays', [])]
                        logger.info(f"📂 Loaded {len(plays)} plays from previous day ({previous_date})")
                        return plays
            
            logger.warning(f"❌ No previous day data found for {previous_date}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error loading previous day data: {e}")
            return []
    
    def reset_daily_data(self):
        """Reset data for a new day"""
        # Before resetting, save current data as previous day's data if we have plays
        if self.top_plays:
            self.save_previous_day_data()
        
        self.top_plays = []
        self.processed_plays = set()
        self.save_daily_data()
    
    def get_today_date(self):
        """Get today's date in YYYY-MM-DD format"""
        return datetime.now(eastern_tz).strftime("%Y-%m-%d")
    
    def get_previous_date(self):
        """Get previous day's date in YYYY-MM-DD format"""
        yesterday = datetime.now(eastern_tz) - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
    
    def get_data_last_updated(self):
        """Get the last updated timestamp for the current data"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'rb') as f:
                    data = pickle.load(f)
                    return data.get('last_updated', 'Unknown')
            return 'No data file found'
        except Exception as e:
            logger.error(f"❌ Error getting last updated time: {e}")
            return 'Error reading data'
    
    def get_live_games(self):
        """Get all live/recent games for today"""
        try:
            today = self.get_today_date()
            url = "https://statsapi.mlb.com/api/v1/schedule"
            params = {
                "sportId": 1,
                "date": today,
                "hydrate": "game(content(editorial(recap))),decisions"
            }
            
            # Increased timeout and added retry logic
            for attempt in range(3):
                try:
                    response = requests.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt < 2:
                        logger.warning(f"⚠️ API request failed (attempt {attempt + 1}), retrying in 5 seconds: {e}")
                        time.sleep(5)
                        continue
                    else:
                        raise
            
            data = response.json()
            
            if not data.get('dates') or not data['dates']:
                logger.info("📭 No games scheduled for today")
                return []
            
            games = data['dates'][0].get('games', [])
            
            # Enhanced game filtering - include more game states for better coverage
            relevant_games = []
            for game in games:
                status = game.get('status', {}).get('statusCode', '')
                detailed_state = game.get('status', {}).get('detailedState', '')
                
                # Include live games, recently completed games, delayed games, and postponed games
                # This ensures we don't miss any games during periods of inactivity
                if status in ['I', 'F', 'O', 'S', 'PW', 'D', 'P', 'C']:  # Added P (Postponed) and C (Cancelled)
                    relevant_games.append(game)
                    logger.debug(f"🎮 Including game: {game.get('teams', {}).get('away', {}).get('name', 'Unknown')} @ {game.get('teams', {}).get('home', {}).get('name', 'Unknown')} ({detailed_state})")
            
            logger.info(f"🎮 Found {len(relevant_games)} relevant games out of {len(games)} total scheduled")
            
            # If no relevant games today, also check for games that might have started late or extended
            if not relevant_games:
                logger.info("🔍 No relevant games found for today, checking if any games are running late...")
                # You could add logic here to check yesterday's games that might still be ongoing
            
            return relevant_games
            
        except Exception as e:
            logger.error(f"❌ Error fetching live games: {e}")
            # Don't return empty list immediately, log the error and continue monitoring
            logger.info("🔄 Will continue monitoring despite API error...")
            return []
    
    def get_game_plays(self, game_id: str) -> List[Dict]:
        """Get all plays for a specific game"""
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
            
            # Increased timeout and added retry logic
            for attempt in range(3):
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt < 2:
                        logger.warning(f"⚠️ Game data request failed for {game_id} (attempt {attempt + 1}), retrying: {e}")
                        time.sleep(3)
                        continue
                    else:
                        logger.error(f"❌ Failed to get game data for {game_id} after 3 attempts: {e}")
                        return []
            
            data = response.json()
            
            plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])
            
            # Add game context to each play
            game_data = data.get('gameData', {})
            teams = game_data.get('teams', {})
            
            for play in plays:
                play['game_context'] = {
                    'game_id': game_id,
                    'away_team': teams.get('away', {}).get('name', 'Unknown'),
                    'home_team': teams.get('home', {}).get('name', 'Unknown'),
                }
            
            logger.debug(f"📊 Retrieved {len(plays)} plays for game {game_id}")
            return plays
            
        except Exception as e:
            logger.error(f"❌ Error fetching plays for game {game_id}: {e}")
            return []
    
    def extract_impact_from_play(self, play: Dict) -> Optional[ImpactPlay]:
        """Extract impact data from a play, prioritizing real WPA"""
        try:
            result = play.get('result', {})
            about = play.get('about', {})
            matchup = play.get('matchup', {})
            game_context = play.get('game_context', {})
            
            # Create unique play ID
            play_id = f"{game_context.get('game_id', 'unknown')}_{about.get('atBatIndex', 0)}_{about.get('playIndex', 0)}"
            
            # Skip if we've already processed this play
            if play_id in self.processed_plays:
                return None
            
            # Priority 1: Real WPA data
            wpa_value = None
            has_real_wpa = False
            
            if 'wpa' in result and result['wpa'] is not None:
                wpa_value = float(result['wpa'])
                has_real_wpa = True
                impact = abs(wpa_value) * 100  # Convert to percentage
                logger.info(f"🎯 Found real WPA: {wpa_value:.3f} → {impact:.1f}% impact")
            else:
                # Check playEvents for WPA
                for event in play.get('playEvents', []):
                    if 'wpa' in event and event['wpa'] is not None:
                        wpa_value = float(event['wpa'])
                        has_real_wpa = True
                        impact = abs(wpa_value) * 100
                        logger.info(f"🎯 Found real WPA in event: {wpa_value:.3f} → {impact:.1f}% impact")
                        break
            
            # If no real WPA, use our statistical model (but mark it as such)
            if wpa_value is None:
                from impact_plays_tracker import calculate_enhanced_statistical_win_probability
                impact = calculate_enhanced_statistical_win_probability(play)
                wpa_value = impact / 100.0  # Convert back to WPA scale
                has_real_wpa = False
            
            # Only consider plays with significant impact
            min_impact = 10.0 if has_real_wpa else 25.0  # Lower threshold for real WPA
            
            if impact < min_impact:
                return None
            
            # Get scores from live data
            live_data = play.get('liveData', {})
            linescore = live_data.get('linescore', {}) if live_data else {}
            away_score = linescore.get('teams', {}).get('away', {}).get('runs', 0)
            home_score = linescore.get('teams', {}).get('home', {}).get('runs', 0)
            
            # If not available, try from play result
            if away_score == 0 and home_score == 0:
                away_score = result.get('awayScore', 0)
                home_score = result.get('homeScore', 0)
            
            # Create ImpactPlay object
            impact_play = ImpactPlay(
                impact=impact,
                game_id=game_context.get('game_id', 'unknown'),
                play_id=play_id,
                wpa=wpa_value,
                event=result.get('event', 'Unknown'),
                description=result.get('description', ''),
                batter=matchup.get('batter', {}).get('fullName', 'Unknown'),
                pitcher=matchup.get('pitcher', {}).get('fullName', 'Unknown'),
                inning=about.get('inning', 0),
                half_inning=about.get('halfInning', ''),
                away_team=game_context.get('away_team', 'Unknown'),
                home_team=game_context.get('home_team', 'Unknown'),
                away_score=away_score,
                home_score=home_score,
                timestamp=datetime.now(eastern_tz).isoformat(),
                has_real_wpa=has_real_wpa
            )
            
            # Mark this play as processed
            self.processed_plays.add(play_id)
            
            return impact_play
            
        except Exception as e:
            logger.error(f"❌ Error extracting impact from play: {e}")
            return None
    
    def update_top_plays(self, new_play: ImpactPlay):
        """Update the top 3 plays with a new high-impact play"""
        # Add to list
        self.top_plays.append(new_play)
        
        # Sort by impact (prioritize real WPA, then by impact value)
        self.top_plays.sort(key=lambda p: (p.has_real_wpa, p.impact), reverse=True)
        
        # Keep only top 3
        if len(self.top_plays) > 3:
            removed_play = self.top_plays.pop()
            logger.info(f"📉 Removed play: {removed_play.event} ({removed_play.impact:.1f}%)")
        
        logger.info(f"🏆 Updated top plays! New #1: {new_play.event} ({new_play.impact:.1f}% impact)")
        self.save_daily_data()
    
    def scan_for_impacts(self):
        """Scan all live games for new high-impact plays"""
        scan_start_time = time.time()
        try:
            live_games = self.get_live_games()
            if not live_games:
                logger.info("📭 No live games found - system continuing to monitor")
                # During off-season or between games, perform keep-alive activities
                self.perform_keep_alive_activities()
                return
            
            logger.info(f"🔍 Scanning {len(live_games)} games for impact plays...")
            
            new_impacts_found = 0
            games_processed = 0
            
            for game in live_games:
                try:
                    game_id = game['gamePk']
                    status = game.get('status', {}).get('abstractGameState', '')
                    detailed_state = game.get('status', {}).get('detailedState', '')
                    
                    logger.debug(f"🎮 Checking game {game_id} ({detailed_state})")
                    
                    plays = self.get_game_plays(game_id)
                    if not plays:
                        logger.debug(f"⚠️ No plays found for game {game_id}")
                        continue
                    
                    games_processed += 1
                    
                    # Check each play for impact
                    for play in plays:
                        try:
                            impact_play = self.extract_impact_from_play(play)
                            if impact_play:
                                # Check if this impact is high enough for top 3
                                min_impact_for_top3 = min(p.impact for p in self.top_plays) if len(self.top_plays) == 3 else 0
                                
                                if len(self.top_plays) < 3 or impact_play.impact > min_impact_for_top3:
                                    self.update_top_plays(impact_play)
                                    new_impacts_found += 1
                                    
                                    # Log the discovery
                                    wpa_type = "🎯 REAL WPA" if impact_play.has_real_wpa else "📊 Statistical"
                                    logger.info(f"🚨 NEW HIGH IMPACT PLAY! {wpa_type}")
                                    logger.info(f"   {impact_play.event} - {impact_play.impact:.1f}% impact")
                                    logger.info(f"   {impact_play.away_team} @ {impact_play.home_team}")
                                    logger.info(f"   Inning {impact_play.inning}{impact_play.half_inning}")
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing individual play: {e}")
                            continue  # Continue with next play
                            
                except Exception as e:
                    logger.warning(f"⚠️ Error processing game {game.get('gamePk', 'unknown')}: {e}")
                    continue  # Continue with next game
            
            scan_duration = time.time() - scan_start_time
            
            if new_impacts_found > 0:
                logger.info(f"✅ Found {new_impacts_found} new high-impact plays (processed {games_processed} games in {scan_duration:.1f}s)")
                self.print_current_leaderboard()
            else:
                logger.info(f"📊 No new high-impact plays found (processed {games_processed} games in {scan_duration:.1f}s)")
                
        except Exception as e:
            logger.error(f"❌ Critical error during impact scan: {e}")
            logger.info("🔄 System will continue monitoring despite error...")
    
    def perform_keep_alive_activities(self):
        """Perform activities to keep the system active during periods of no games"""
        try:
            # Log system status
            current_time = datetime.now(eastern_tz)
            logger.info(f"🔄 Keep-alive check at {current_time.strftime('%H:%M:%S ET')}")
            
            # Check data file status
            if hasattr(self, 'data_file') and os.path.exists(self.data_file):
                file_size = os.path.getsize(self.data_file)
                logger.debug(f"📁 Data file size: {file_size} bytes")
            
            # Log current standings if we have any
            if self.top_plays:
                logger.info(f"🏆 Current leaderboard maintained with {len(self.top_plays)} plays")
            
            # Check for tomorrow's schedule to show system is forward-looking
            tomorrow = (datetime.now(eastern_tz) + timedelta(days=1)).strftime("%Y-%m-%d")
            try:
                url = "https://statsapi.mlb.com/api/v1/schedule"
                params = {"sportId": 1, "date": tomorrow}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    tomorrow_games = data.get('dates', [{}])[0].get('games', []) if data.get('dates') else []
                    logger.info(f"📅 Tomorrow ({tomorrow}): {len(tomorrow_games)} games scheduled")
            except:
                pass  # Don't let keep-alive activities fail the main loop
                
        except Exception as e:
            logger.debug(f"Keep-alive activity error (non-critical): {e}")
    
    def print_current_leaderboard(self):
        """Print the current top 3 plays"""
        logger.info("🏆 CURRENT TOP 3 IMPACT PLAYS:")
        for i, play in enumerate(self.top_plays, 1):
            wpa_indicator = "🎯" if play.has_real_wpa else "📊"
            logger.info(f"  #{i} {wpa_indicator} {play.event} - {play.impact:.1f}% impact")
            logger.info(f"      {play.away_team} vs {play.home_team} (Inning {play.inning})")
            logger.info(f"      {play.description[:60]}...")
    
    def get_daily_top_plays(self) -> List[ImpactPlay]:
        """Get the current top 3 plays for display (current day)"""
        return self.top_plays.copy()
    
    def get_previous_day_top_plays(self) -> List[ImpactPlay]:
        """Get the previous day's top 3 plays for tweeting"""
        return self.load_previous_day_data()
    
    def start_monitoring(self, interval_minutes=2, keep_alive_url=None):
        """Start the continuous monitoring loop with enhanced error handling and keep-alive ping"""
        logger.info(f"🚀 Starting live impact monitoring (every {interval_minutes} minutes)")
        logger.info("🔄 Enhanced monitoring with improved error handling and timeout management")
        if keep_alive_url:
            logger.info(f"💓 Keep-alive URL configured: {keep_alive_url}")
        
        self.is_running = True
        scan_count = 0
        consecutive_errors = 0
        last_heartbeat = time.time()
        
        while self.is_running:
            try:
                scan_count += 1
                current_time = datetime.now(eastern_tz)
                
                # Heartbeat logging every 5 minutes to show system is alive
                if scan_count == 1 or time.time() - last_heartbeat > 300:  # First scan or every 5 minutes (300 seconds)
                    logger.info(f"💓 System heartbeat - Scan #{scan_count} at {current_time.strftime('%Y-%m-%d %H:%M:%S ET')}")
                    logger.info(f"💓 Uptime: System has been running continuously")
                    logger.info(f"💓 Current top plays: {len(self.top_plays)}")
                    last_heartbeat = time.time()
                
                # Check if we need to reset for a new day
                current_date = self.get_today_date()
                if hasattr(self, '_last_date') and self._last_date != current_date:
                    logger.info("📅 New day detected - resetting daily data")
                    self.reset_daily_data()
                    scan_count = 1  # Reset scan count for new day
                self._last_date = current_date
                
                # Scan for new impacts
                logger.debug(f"🔍 Starting scan #{scan_count}")
                self.scan_for_impacts()
                
                # Reset consecutive error counter on successful scan
                consecutive_errors = 0
                
                # Keep-alive ping to prevent Render from spinning down
                if keep_alive_url:
                    try:
                        response = requests.get(keep_alive_url, timeout=10)
                        if response.status_code == 200:
                            logger.debug("💓 Keep-alive ping successful")
                        else:
                            logger.warning(f"⚠️ Keep-alive ping returned status {response.status_code}")
                    except Exception as e:
                        logger.warning(f"⚠️ Keep-alive ping failed: {e}")
                
                # Wait before next scan
                logger.debug(f"😴 Sleeping for {interval_minutes} minutes until next scan...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ Error in monitoring loop (scan #{scan_count}): {e}")
                logger.error(f"   Exception type: {type(e).__name__}")
                
                # Implement exponential backoff for consecutive errors
                if consecutive_errors <= 3:
                    wait_time = min(60 * consecutive_errors, 300)  # Max 5 minutes
                    logger.info(f"🔄 Consecutive error #{consecutive_errors} - waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                else:
                    # After 3 consecutive errors, use standard interval but log warning
                    logger.warning(f"⚠️ {consecutive_errors} consecutive errors detected - continuing with standard interval")
                    logger.warning("⚠️ This may indicate a persistent issue, but system will continue operating")
                    time.sleep(interval_minutes * 60)
                
                # Log system status for debugging
                logger.info(f"🔍 System status: is_running={self.is_running}, top_plays={len(self.top_plays)}")
        
        logger.info("🛑 Monitoring loop ended")
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_running = False
        logger.info("🛑 Stopping live impact monitoring...")

def main():
    """Main function to start live monitoring"""
    tracker = LiveImpactTracker()
    
    # Print current state
    if tracker.top_plays:
        tracker.print_current_leaderboard()
    else:
        logger.info("📭 No high-impact plays found yet today")
    
    # Start monitoring with keep-alive URL for Render hosting
    try:
        # Get keep-alive URL from environment or use default
        keep_alive_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://mlb-impactful-plays.onrender.com')
        if keep_alive_url and not keep_alive_url.endswith('/api/ping'):
            keep_alive_url += '/api/ping'
        
        logger.info(f"💓 Using keep-alive URL: {keep_alive_url}")
        tracker.start_monitoring(interval_minutes=2, keep_alive_url=keep_alive_url)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    finally:
        tracker.save_daily_data()

if __name__ == "__main__":
    main() 