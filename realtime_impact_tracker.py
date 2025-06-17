#!/usr/bin/env python3
"""
Real-Time MLB Impact Plays Tracker
Monitors live games every 2 minutes and tweets high-impact plays immediately
"""

import os
import sys
import time
import json
import logging
import requests
import tweepy
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template_string
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('impact_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RealTimeImpactTracker:
    def __init__(self):
        self.api_base = "https://statsapi.mlb.com/api/v1.1"
        self.twitter_api = self.setup_twitter()
        self.posted_plays = set()  # Track already posted plays to avoid duplicates
        self.monitoring = False
        self.site_url = os.getenv('SITE_URL', 'http://localhost:5000')  # For keep-alive pings
        
        # Dashboard tracking
        self.last_check_time = None
        self.tweets_sent_today = 0
        self.recent_tweets = []  # Store last 5 tweets with details
        self.total_games_checked = 0
        self.start_time = None
        
        # Official team hashtags mapping
        self.team_hashtags = {
            'OAK': '#Athletics',
            'ATL': '#BravesCountry',
            'BAL': '#Birdland', 
            'BOS': '#DirtyWater',
            'CWS': '#WhiteSox',
            'CIN': '#ATOBTTR',
            'CLE': '#GuardsBall',
            'COL': '#Rockies',
            'DET': '#RepDetroit',
            'HOU': '#BuiltForThis',
            'KC': '#FountainsUp',
            'LAA': '#RepTheHalo',
            'LAD': '#LetsGoDodgers',
            'MIA': '#MarlinsBeisbol',
            'MIL': '#ThisIsMyCrew',
            'MIN': '#MNTwins',
            'NYM': '#LGM',
            'NYY': '#RepBX',
            'PHI': '#RingTheBell',
            'PIT': '#LetsGoBucs',
            'SD': '#ForTheFaithful',
            'SF': '#SFGiants',
            'SEA': '#TridentsUp',
            'STL': '#ForTheLou',
            'TB': '#RaysUp',
            'TEX': '#AllForTX',
            'TOR': '#LightsUpLetsGo',
            'WSH': '#NATITUDE',
            'CHC': '#BeHereForIt'
        }
        
    def setup_twitter(self):
        """Initialize Twitter API"""
        try:
            api_key = os.getenv('TWITTER_API_KEY')
            api_secret = os.getenv('TWITTER_API_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            
            if not all([api_key, api_secret, access_token, access_token_secret]):
                logger.error("Missing Twitter API credentials")
                return None
                
            auth = tweepy.OAuthHandler(api_key, api_secret)
            auth.set_access_token(access_token, access_token_secret)
            
            api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Test authentication
            api.verify_credentials()
            logger.info("Twitter API authenticated successfully")
            return api
            
        except Exception as e:
            logger.error(f"Failed to authenticate Twitter API: {e}")
            return None
    
    def get_live_games(self) -> List[Dict]:
        """Get all games currently live or recently finished"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{self.api_base}/schedule"
            params = {
                'sportId': 1,
                'date': today,
                'hydrate': 'linescore,decisions',
                'useLatestGames': 'false',
                'language': 'en'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            live_games = []
            
            for date_data in data.get('dates', []):
                for game in date_data.get('games', []):
                    status = game.get('status', {}).get('statusCode', '')
                    # Include live games and recently finished games (within last 30 minutes)
                    if status in ['I', 'F', 'O', 'PW', 'D']:  # In Progress, Final, Final - Other, Pre-Warmup, Delayed
                        live_games.append(game)
            
            logger.info(f"Found {len(live_games)} live/recent games")
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
        """Determine if a play qualifies as marquee moment for tweeting"""
        # MARQUEE MOMENTS ONLY - Focus on truly game-changing plays
        
        # PRIMARY: Massive WPA impact (40%+ win probability swing)
        if impact_score >= 0.40:  # 40%+ WP swing - elite marquee moments
            return True
            
        # SECONDARY: Very high impact in clutch situations
        if impact_score >= 0.30 and leverage >= 3.0:  # 30%+ swing in super high leverage
            return True
            
        # TERTIARY: Walk-off situations get lower threshold
        # (These are always marquee regardless of WPA)
        if impact_score >= 0.25 and leverage >= 2.5:  # 25%+ in very clutch moments
            return True
            
        # All other plays are filtered out - we want ONLY the biggest moments
        return False
    
    def create_play_graphic(self, play: Dict, game_info: Dict, impact_score: float) -> str:
        """Create a graphic for a single high-impact play"""
        try:
            # Create 1200x675 Twitter-optimized image
            width, height = 1200, 675
            img = Image.new('RGB', (width, height), color='#0F1419')
            draw = ImageDraw.Draw(img)
            
            # Load fonts with fallbacks
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/SF-Pro-Display-Bold.otf", 42)
                subtitle_font = ImageFont.truetype("/System/Library/Fonts/SF-Pro-Display-Medium.otf", 28)
                body_font = ImageFont.truetype("/System/Library/Fonts/SF-Pro-Display-Regular.otf", 24)
                small_font = ImageFont.truetype("/System/Library/Fonts/SF-Pro-Display-Regular.otf", 20)
            except:
                try:
                    title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
                    subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
                    body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
                    small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
                except:
                    title_font = ImageFont.load_default()
                    subtitle_font = ImageFont.load_default()
                    body_font = ImageFont.load_default()
                    small_font = ImageFont.load_default()
            
            # Colors
            orange = '#FF6B35'
            white = '#FFFFFF'
            gray = '#8B949E'
            red = '#FF4444'
            
            # Header
            draw.text((50, 40), "⭐ MARQUEE MOMENT", fill=orange, font=title_font)
            
            # Game info
            home_team = game_info.get('home_team', 'HOME')
            away_team = game_info.get('away_team', 'AWAY')
            score_text = f"{away_team} {play.get('away_score', 0)} - {play.get('home_score', 0)} {home_team}"
            draw.text((50, 100), score_text, fill=white, font=subtitle_font)
            
            # Inning info
            inning_text = f"{'Top' if play.get('half_inning') == 'top' else 'Bottom'} {play.get('inning', 1)}"
            draw.text((50, 140), inning_text, fill=gray, font=body_font)
            
            # Play description (wrapped)
            description = play.get('description', 'No description')
            lines = self.wrap_text(description, body_font, width - 100)
            y_pos = 200
            for line in lines[:3]:  # Max 3 lines
                draw.text((50, y_pos), line, fill=white, font=body_font)
                y_pos += 35
            
            # Players
            batter = play.get('batter', '')
            pitcher = play.get('pitcher', '')
            if batter:
                draw.text((50, y_pos + 20), f"Batter: {batter}", fill=gray, font=small_font)
            if pitcher:
                draw.text((50, y_pos + 45), f"Pitcher: {pitcher}", fill=gray, font=small_font)
            
            # Impact metrics (right side)
            metrics_x = width - 350
            
            # Impact score
            impact_text = f"{impact_score:.1%}"
            draw.text((metrics_x, 200), "IMPACT SCORE", fill=orange, font=small_font)
            draw.text((metrics_x, 230), impact_text, fill=white, font=title_font)
            
            # Leverage index
            leverage = play.get('leverage_index', 1.0)
            draw.text((metrics_x, 300), "LEVERAGE", fill=orange, font=small_font)
            draw.text((metrics_x, 330), f"{leverage:.1f}", fill=white, font=subtitle_font)
            
            # Win probability
            wp = play.get('win_probability_home', 0.5)
            if play.get('half_inning') == 'top':
                wp = 1 - wp  # Show batting team's WP
            draw.text((metrics_x, 400), "WIN PROB", fill=orange, font=small_font)
            draw.text((metrics_x, 430), f"{wp:.1%}", fill=white, font=subtitle_font)
            
            # Visual impact bar
            bar_width = 200
            bar_height = 20
            bar_x = metrics_x
            bar_y = 500
            
            # Background bar
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                         fill='#21262D', outline=gray)
            
            # Impact fill
            fill_width = min(bar_width, int(bar_width * (impact_score / 0.5)))  # Scale to 50% max
            if fill_width > 0:
                color = red if impact_score >= 0.20 else orange
                draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 
                             fill=color)
            
            # Timestamp
            timestamp = datetime.now().strftime("%I:%M %p ET")
            draw.text((50, height - 60), f"Live • {timestamp}", fill=gray, font=small_font)
            
            # Save graphic
            filename = f"impact_play_{int(time.time())}.png"
            img.save(filename, "PNG", quality=95)
            logger.info(f"Created graphic: {filename}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error creating graphic: {e}")
            return None
    
    def wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def format_tweet_text(self, play: Dict, game_info: Dict, impact_score: float) -> str:
        """Format tweet text for the impact play"""
        try:
            home_team = game_info.get('home_team', 'HOME')
            away_team = game_info.get('away_team', 'AWAY')
            
            description = play.get('description', '')
            # Truncate if too long
            if len(description) > 100:
                description = description[:97] + "..."
            
            inning_text = f"{'T' if play.get('half_inning') == 'top' else 'B'}{play.get('inning', 1)}"
            
            tweet = f"⭐ MARQUEE MOMENT!\n\n"
            tweet += f"{description}\n\n"
            tweet += f"📊 Impact: {impact_score:.1%} WP change\n"
            tweet += f"⚾ {away_team} {play.get('away_score', 0)} - {play.get('home_score', 0)} {home_team} ({inning_text})\n\n"
            
            # Add official team hashtags
            hashtags = []
            if away_team in self.team_hashtags:
                hashtags.append(self.team_hashtags[away_team])
            if home_team in self.team_hashtags and home_team != away_team:
                hashtags.append(self.team_hashtags[home_team])
            
            if hashtags:
                tweet += " ".join(hashtags)
            else:
                # Fallback if team not found
                tweet += "#MLB"
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error formatting tweet: {e}")
            return "Marquee moment detected! ⭐"
    
    def post_impact_play(self, play: Dict, game_info: Dict, impact_score: float):
        """Post a high-impact play to Twitter"""
        try:
            if not self.twitter_api:
                logger.warning("Twitter API not available")
                return False
            
            # Create unique play ID to avoid duplicates
            play_id = f"{play['game_id']}_{play['play_id']}_{play['inning']}_{play['half_inning']}"
            
            if play_id in self.posted_plays:
                logger.info(f"Play {play_id} already posted, skipping")
                return False
            
            # Format tweet (no graphics needed)
            tweet_text = self.format_tweet_text(play, game_info, impact_score)
            
            # Post tweet without graphic
            try:
                tweet = self.twitter_api.update_status(status=tweet_text)
                
                self.posted_plays.add(play_id)
                self.tweets_sent_today += 1
                
                # Store recent tweet details (keep last 5)
                tweet_info = f"{datetime.now().strftime('%H:%M')} - {game_info.get('away_team', 'AWAY')} vs {game_info.get('home_team', 'HOME')} ({impact_score:.1%})"
                self.recent_tweets.insert(0, tweet_info)
                if len(self.recent_tweets) > 5:
                    self.recent_tweets.pop()
                
                logger.info(f"✅ Posted marquee moment tweet: {tweet.id}")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to post tweet: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting marquee moment: {e}")
            return False
    
    def reset_daily_counters(self):
        """Reset daily counters at 9 AM (after all games are done)"""
        now = datetime.now()
        current_date = now.date()
        
        # If it's past 9 AM today and we haven't reset yet for this date
        if now.hour >= 9:
            reset_date = current_date
        else:
            # If it's before 9 AM, we're still counting for "yesterday's" games
            reset_date = current_date - timedelta(days=1)
        
        if not hasattr(self, 'last_reset_date') or self.last_reset_date != reset_date:
            self.tweets_sent_today = 0
            self.recent_tweets = []
            self.last_reset_date = reset_date
            logger.info("🔄 Daily counters reset at 9 AM - new day started")
    
    def monitor_games(self):
        """Main monitoring loop - checks every 2 minutes"""
        logger.info("Starting real-time marquee moments monitoring...")
        self.monitoring = True
        self.start_time = datetime.now()
        ping_counter = 0  # Track cycles for keep-alive pings
        
        while self.monitoring:
            try:
                start_time = time.time()
                self.last_check_time = datetime.now()
                
                # Reset daily counters if new day
                self.reset_daily_counters()
                
                # Keep-alive ping every 6 minutes (3 cycles of 2 minutes)
                ping_counter += 1
                if ping_counter >= 3:
                    self.keep_alive_ping()
                    ping_counter = 0
                
                # Get live games
                live_games = self.get_live_games()
                self.total_games_checked += len(live_games)
                
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
                    
                    # Process all plays for impact
                    for play in plays:
                        impact_score = self.calculate_impact_score(play)
                        
                        # Check if this is a marquee moment worth tweeting
                        if self.is_high_impact_play(impact_score, play.get('leverage_index', 1.0)):
                            logger.info(f"⭐ Marquee moment detected: {impact_score:.1%} impact")
                            self.post_impact_play(play, game_info, impact_score)
                
                # Calculate sleep time to maintain 2-minute intervals
                elapsed = time.time() - start_time
                sleep_time = max(0, 120 - elapsed)  # 2 minutes = 120 seconds
                
                logger.info(f"Scan completed in {elapsed:.1f}s, checked {len(live_games)} games, sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(120)  # Wait 2 minutes before retrying
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.monitoring = False
        logger.info("Stopping monitoring...")
    
    def keep_alive_ping(self):
        """Send a ping to keep the site awake on free hosting"""
        try:
            # Only ping if we're in production (not localhost)
            if 'localhost' not in self.site_url and '127.0.0.1' not in self.site_url:
                response = requests.get(f"{self.site_url}/health", timeout=10)
                if response.status_code == 200:
                    logger.debug("Keep-alive ping successful")
                else:
                    logger.warning(f"Keep-alive ping returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Keep-alive ping failed: {e}")
            # Don't let ping failures stop monitoring

# Flask web interface
app = Flask(__name__)
tracker = RealTimeImpactTracker()

@app.route('/')
def dashboard():
    """Simple dashboard showing system status"""
    status = {
        'monitoring': tracker.monitoring,
        'posted_plays': len(tracker.posted_plays),
        'twitter_connected': tracker.twitter_api is not None,
        'last_check_time': tracker.last_check_time.strftime('%Y-%m-%d %H:%M:%S ET') if tracker.last_check_time else 'Never',
        'tweets_sent_today': tracker.tweets_sent_today,
        'recent_tweets': tracker.recent_tweets,
        'total_games_checked': tracker.total_games_checked,
        'start_time': tracker.start_time.strftime('%Y-%m-%d %H:%M:%S ET') if tracker.start_time else 'Not started',
        'uptime': str(datetime.now() - tracker.start_time).split('.')[0] if tracker.start_time else 'Not started',
        'next_reset': 'Tomorrow at 9:00 AM ET' if datetime.now().hour >= 9 else 'Today at 9:00 AM ET'
    }
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MLB Impact Plays Tracker</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f1419; color: white; }
            .header { color: #ff6b35; margin-bottom: 30px; }
            .status { background: #21262d; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .metric { margin: 10px 0; }
            .connected { color: #28a745; }
            .disconnected { color: #dc3545; }
            .monitoring { color: #ff6b35; }
        </style>
    </head>
    <body>
        <h1 class="header">⭐ MLB Marquee Moments Tracker</h1>
        
        <div class="status">
            <h2>System Status</h2>
            <div class="metric">
                <strong>Monitoring:</strong> 
                <span class="{{ 'monitoring' if status.monitoring else 'disconnected' }}">
                    {{ '🟢 ACTIVE' if status.monitoring else '🔴 INACTIVE' }}
                </span>
            </div>
            <div class="metric">
                <strong>Twitter API:</strong>
                <span class="{{ 'connected' if status.twitter_connected else 'disconnected' }}">
                    {{ '🟢 CONNECTED' if status.twitter_connected else '🔴 DISCONNECTED' }}
                </span>
            </div>
            <div class="metric">
                <strong>Plays Posted Today:</strong> {{ status.posted_plays }}
            </div>
            <div class="metric">
                <strong>Last Check:</strong> {{ status.last_check_time }}
            </div>
            <div class="metric">
                <strong>Tweets Sent Today:</strong> 
                <span class="{{ 'monitoring' if status.tweets_sent_today > 0 else 'disconnected' }}">
                    {{ status.tweets_sent_today }}
                </span>
            </div>
            <div class="metric">
                <strong>Total Games Checked:</strong> {{ status.total_games_checked }}
            </div>
            <div class="metric">
                <strong>Start Time:</strong> {{ status.start_time }}
            </div>
            <div class="metric">
                <strong>Uptime:</strong> {{ status.uptime }}
            </div>
            <div class="metric">
                <strong>Next Reset:</strong> {{ status.next_reset }}
            </div>
        </div>
        
        <div class="status">
            <h3>Recent Marquee Moments</h3>
            {% if status.recent_tweets %}
                {% for tweet in status.recent_tweets %}
                <div class="metric">• {{ tweet }}</div>
                {% endfor %}
            {% else %}
                <div class="metric">No marquee moments detected yet today</div>
            {% endif %}
        </div>
        
        <div class="status">
            <h3>How It Works</h3>
            <p>• Monitors all live MLB games every 2 minutes</p>
            <p>• Calculates win probability impact for each play</p>
            <p>• Tweets MARQUEE MOMENTS (≥40% WP change) immediately when they occur</p>
            <p>• NO scheduled tweets - only real-time detection and instant posting</p>
            <p>• Daily counters reset at 9:00 AM ET (after all games finish)</p>
            <p>• Targets 2-3 elite plays per night across MLB</p>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, status=status)

@app.route('/start')
def start_monitoring():
    """Start monitoring endpoint"""
    if not tracker.monitoring:
        monitoring_thread = threading.Thread(target=tracker.monitor_games, daemon=True)
        monitoring_thread.start()
        return "✅ Monitoring started!"
    return "⚠️ Already monitoring"

@app.route('/stop')
def stop_monitoring():
    """Stop monitoring endpoint"""
    tracker.stop_monitoring()
    return "🛑 Monitoring stopped"

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'monitoring': tracker.monitoring,
        'twitter_api': tracker.twitter_api is not None,
        'timestamp': datetime.now().isoformat()
    }

def main():
    """Main function to start the tracker"""
    print("🔥 MLB Real-Time Impact Plays Tracker")
    print("=" * 50)
    
    # Check if running in production
    if os.getenv('FLASK_ENV') == 'production':
        # Start monitoring automatically in production
        monitoring_thread = threading.Thread(target=tracker.monitor_games, daemon=True)
        monitoring_thread.start()
        
        # Run Flask app
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    else:
        # Development mode - manual control
        print("Development mode - use web interface to control monitoring")
        print("Visit: http://localhost:5000")
        print("Start monitoring: http://localhost:5000/start")
        print("Stop monitoring: http://localhost:5000/stop")
        
        app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    main() 