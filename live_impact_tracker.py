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
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('dates') or not data['dates']:
                return []
            
            games = data['dates'][0].get('games', [])
            
            # Filter for games that are live, recent, or completed today
            relevant_games = []
            for game in games:
                status = game.get('status', {}).get('statusCode', '')
                # Include live games, recently completed games, and games in progress
                if status in ['I', 'F', 'O', 'S', 'PW', 'D']:  # In progress, Final, Other, Suspended, Pre-Warmup, Delayed
                    relevant_games.append(game)
            
            logger.debug(f"🎮 Found {len(relevant_games)} relevant games out of {len(games)} total")
            return relevant_games
            
        except Exception as e:
            logger.error(f"❌ Error fetching live games: {e}")
            return []
    
    def get_game_plays(self, game_id: str) -> List[Dict]:
        """Get all plays for a specific game"""
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
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
        try:
            live_games = self.get_live_games()
            if not live_games:
                logger.debug("📭 No live games found")
                return
            
            logger.info(f"🔍 Scanning {len(live_games)} games for impact plays...")
            
            new_impacts_found = 0
            
            for game in live_games:
                game_id = game['gamePk']
                status = game.get('status', {}).get('abstractGameState', '')
                
                logger.debug(f"🎮 Checking game {game_id} ({status})")
                
                plays = self.get_game_plays(game_id)
                if not plays:
                    continue
                
                # Check each play for impact
                for play in plays:
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
            
            if new_impacts_found > 0:
                logger.info(f"✅ Found {new_impacts_found} new high-impact plays")
                self.print_current_leaderboard()
            else:
                logger.debug("📊 No new high-impact plays found")
                
        except Exception as e:
            logger.error(f"❌ Error during impact scan: {e}")
    
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
    
    def start_monitoring(self, interval_minutes=2):
        """Start the continuous monitoring loop"""
        logger.info(f"🚀 Starting live impact monitoring (every {interval_minutes} minutes)")
        self.is_running = True
        
        while self.is_running:
            try:
                # Check if we need to reset for a new day
                current_date = self.get_today_date()
                if hasattr(self, '_last_date') and self._last_date != current_date:
                    logger.info("📅 New day detected - resetting daily data")
                    self.reset_daily_data()
                self._last_date = current_date
                
                # Scan for new impacts
                self.scan_for_impacts()
                
                # Wait before next scan
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_running = False

def main():
    """Main function to start live monitoring"""
    tracker = LiveImpactTracker()
    
    # Print current state
    if tracker.top_plays:
        tracker.print_current_leaderboard()
    else:
        logger.info("📭 No high-impact plays found yet today")
    
    # Start monitoring
    try:
        tracker.start_monitoring(interval_minutes=2)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    finally:
        tracker.save_daily_data()

if __name__ == "__main__":
    main() 