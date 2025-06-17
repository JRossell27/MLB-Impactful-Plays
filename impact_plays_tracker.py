import os
import time
import logging
import warnings
from datetime import datetime, timedelta
import tweepy
from dotenv import load_dotenv
import requests
import schedule
import threading
from flask import Flask
import pytz

# Suppress warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Test mode flag
TEST_MODE = True  # Set to False for production

# Twitter API setup
if not TEST_MODE:
    try:
        client = tweepy.Client(
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
        )
        logger.info("Twitter client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Twitter client: {str(e)}")

# Eastern timezone
eastern_tz = pytz.timezone('US/Eastern')

def get_yesterday_date():
    """Get yesterday's date in MM/DD/YYYY format"""
    yesterday = datetime.now(eastern_tz) - timedelta(days=1)
    return yesterday.strftime("%m/%d/%Y")

def get_games_for_date(date_str):
    """Get all MLB games for a specific date"""
    try:
        url = "https://statsapi.mlb.com/api/v1/schedule"
        params = {
            "sportId": 1,
            "date": date_str,
            "hydrate": "game(content(editorial(recap))),decisions,person,probablePitcher,stats,homeRuns,previousPlay,team"
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch games: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching games: {str(e)}")
        return None

def get_play_by_play(game_id):
    """Get detailed play-by-play data for a game"""
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch play-by-play for game {game_id}: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching play-by-play for game {game_id}: {str(e)}")
        return None

def get_mlb_data(date_str=None):
    """Get MLB game data for a specific date with play-by-play including WPA data"""
    if date_str is None:
        date_str = get_yesterday_date()
    
    logger.info(f"🔍 Fetching MLB data for {date_str}")
    
    try:
        # First get the schedule to find game IDs
        url = "https://statsapi.mlb.com/api/v1/schedule"
        params = {
            "sportId": 1,
            "date": date_str,
            "hydrate": "game(content(editorial(recap))),decisions"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('dates') or not data['dates'][0].get('games'):
            logger.warning(f"No games found for {date_str}")
            return []
        
        all_plays = []
        games = data['dates'][0]['games']
        
        for game in games:
            game_pk = game['gamePk']
            logger.info(f"🎯 Fetching live feed data for game {game_pk}")
            
            # Get live feed data for this specific game (contains WPA data)
            live_feed_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
            
            try:
                live_response = requests.get(live_feed_url, timeout=15)
                live_response.raise_for_status()
                live_data = live_response.json()
                
                # Extract plays from live feed
                plays_data = live_data.get('liveData', {}).get('plays', {}).get('allPlays', [])
                
                for play in plays_data:
                    # Add game context to each play
                    play['gamePk'] = game_pk
                    play['game_info'] = {
                        'away_team': game['teams']['away']['team']['name'],
                        'home_team': game['teams']['home']['team']['name'],
                        'away_score': game['teams']['away'].get('score', 0),
                        'home_score': game['teams']['home'].get('score', 0)
                    }
                    all_plays.append(play)
                    
                logger.info(f"✅ Retrieved {len(plays_data)} plays from game {game_pk}")
                
            except Exception as e:
                logger.error(f"❌ Error fetching live feed for game {game_pk}: {e}")
                continue
        
        logger.info(f"🎯 Total plays retrieved: {len(all_plays)}")
        return all_plays
        
    except Exception as e:
        logger.error(f"❌ Error fetching MLB data: {e}")
        return []

def calculate_win_probability_impact(play):
    """Calculate win probability impact using actual MLB WPA data when available"""
    try:
        # PRIORITY 1: Use actual MLB WPA data from result.wpa (live games only)
        result_info = play.get('result', {})
        if 'wpa' in result_info and result_info['wpa'] is not None:
            wpa = float(result_info['wpa'])
            # Convert WPA to absolute impact percentage (WPA is -1.0 to 1.0)
            impact = abs(wpa) * 100  # Convert to percentage
            logger.debug(f"🎯 Using actual MLB WPA: {wpa} -> {impact:.1f}% impact")
            return impact
        
        # PRIORITY 2: Check playEvents for WPA data (live games only)
        play_events = play.get('playEvents', [])
        for event in play_events:
            if 'wpa' in event and event['wpa'] is not None:
                wpa = float(event['wpa'])
                impact = abs(wpa) * 100
                logger.debug(f"🎯 Using playEvent WPA: {wpa} -> {impact:.1f}% impact")
                return impact
        
        # FALLBACK: Enhanced statistical model for completed games
        logger.debug("📊 No WPA data found, using enhanced statistical model")
        return calculate_enhanced_statistical_win_probability(play)
        
    except Exception as e:
        logger.error(f"❌ Error calculating win probability impact: {e}")
        return calculate_enhanced_statistical_win_probability(play)

def calculate_enhanced_statistical_win_probability(play):
    """Enhanced statistical win probability calculation based on real MLB scenarios"""
    try:
        about = play.get('about', {})
        result = play.get('result', {})
        count = play.get('count', {})
        runners = play.get('runners', [])
        
        # Extract key game situation variables
        inning = about.get('inning', 5)
        is_top = about.get('isTopInning', True)
        outs = count.get('outs', 1)
        
        # Score situation from game context
        game_info = play.get('game_info', {})
        away_score = game_info.get('away_score', 0)
        home_score = game_info.get('home_score', 0)
        
        # Calculate score differential (from perspective of batting team)
        if is_top:  # Away team batting
            score_diff = away_score - home_score
        else:  # Home team batting
            score_diff = home_score - away_score
        
        # Get runners on base
        runners_on_base = 0
        for runner in runners:
            start_base = runner.get('movement', {}).get('start')
            if start_base and start_base != 'batter':
                runners_on_base += 1
        
        # Get play outcome info
        event = result.get('event', '').lower()
        rbi = result.get('rbi', 0)
        is_scoring_play = about.get('isScoringPlay', False)
        
        # Base leverage factor (typical MLB play impact range: 2-20%)
        base_impact = 5.0
        
        # === LEVERAGE MULTIPLIERS (based on real MLB WPA studies) ===
        
        # 1. Inning multiplier (late innings have exponentially higher leverage)
        if inning >= 9:
            inning_mult = 3.5 if abs(score_diff) <= 2 else 2.0
        elif inning >= 7:
            inning_mult = 2.2 if abs(score_diff) <= 3 else 1.5
        elif inning >= 5:
            inning_mult = 1.4
        else:
            inning_mult = 0.8
        
        # 2. Score situation multiplier (closer games = higher leverage)
        abs_diff = abs(score_diff)
        if abs_diff == 0:  # Tied game
            score_mult = 2.8
        elif abs_diff == 1:  # One-run game
            score_mult = 2.4
        elif abs_diff == 2:  # Two-run game
            score_mult = 1.8
        elif abs_diff == 3:  # Three-run game
            score_mult = 1.3
        elif abs_diff <= 5:  # Close game
            score_mult = 0.9
        else:  # Blowout
            score_mult = 0.4
        
        # 3. Outs multiplier (pressure increases with outs)
        outs_mult = {0: 1.0, 1: 1.3, 2: 1.8}.get(outs, 1.0)
        
        # 4. Runners multiplier (more baserunners = higher potential impact)
        if runners_on_base == 0:
            runners_mult = 0.8
        elif runners_on_base == 1:
            runners_mult = 1.2
        elif runners_on_base == 2:
            runners_mult = 1.6
        else:  # Bases loaded
            runners_mult = 2.4
        
        # 5. Play type multiplier (based on actual run values)
        play_mult = 1.0
        if 'grand slam' in event or (rbi >= 4):
            play_mult = 4.5
        elif 'home run' in event:
            if rbi >= 3:
                play_mult = 3.5
            elif rbi == 2:
                play_mult = 2.8
            elif rbi == 1:
                play_mult = 2.2
            else:
                play_mult = 1.8  # Solo home run
        elif 'triple' in event:
            play_mult = 1.8 + (rbi * 0.4)
        elif 'double' in event:
            play_mult = 1.3 + (rbi * 0.3)
        elif 'single' in event and rbi > 0:
            play_mult = 1.1 + (rbi * 0.2)
        elif 'walk' in event and runners_on_base >= 2:
            play_mult = 1.4  # Bases loaded walk situation
        elif 'double play' in event or 'grounded into double play' in event:
            play_mult = 1.9  # Significant negative impact
        elif 'sacrifice fly' in event or 'sacrifice' in event:
            play_mult = 1.1
        elif is_scoring_play:
            play_mult = 1.3 + (rbi * 0.15)
        elif 'strikeout' in event or 'struck out' in event:
            play_mult = 0.9
        else:
            play_mult = 0.8  # Generic play
        
        # Calculate final impact
        impact = base_impact * inning_mult * score_mult * outs_mult * runners_mult * play_mult
        
        # Add small situational variance for uniqueness (but keep it realistic)
        situation_factor = (inning * 0.3) + (abs(score_diff) * 0.2) + (outs * 0.1) + (runners_on_base * 0.4)
        impact += situation_factor
        
        # Realistic caps based on actual MLB WPA data
        # Most significant plays: 15-35%, extreme plays: 35-50%, once-in-a-season: 50-60%
        if inning >= 9 and abs(score_diff) <= 1:
            max_impact = 60.0  # Walk-off situations
        elif inning >= 8 and abs(score_diff) <= 2:
            max_impact = 50.0  # Very high leverage
        elif inning >= 7 and abs(score_diff) <= 3:
            max_impact = 40.0  # High leverage
        else:
            max_impact = 35.0  # Normal high-impact plays
        
        # Ensure minimum impact for significant plays
        min_impact = 5.0 if play_mult > 1.5 or is_scoring_play else 3.0
        
        final_impact = max(min_impact, min(impact, max_impact))
        
        logger.debug(f"📊 Statistical calculation: inning {inning}, outs {outs}, score_diff {score_diff}, "
                   f"runners {runners_on_base}, event '{event}' -> {final_impact:.1f}% impact")
        
        return final_impact
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced statistical calculation: {e}")
        return 15.0  # Safe default

def extract_high_impact_plays():
    """Extract the highest impact plays from yesterday's games"""
    yesterday = get_yesterday_date()
    games_data = get_games_for_date(yesterday)
    
    if not games_data or 'dates' not in games_data or not games_data['dates']:
        logger.warning("No games found for yesterday")
        return []
    
    high_impact_plays = []
    
    for date_info in games_data['dates']:
        for game in date_info.get('games', []):
            game_id = game['gamePk']
            game_info = {
                'game_id': game_id,
                'away_team': game['teams']['away']['team']['name'],
                'home_team': game['teams']['home']['team']['name'],
                'away_score': game['teams']['away'].get('score', 0),
                'home_score': game['teams']['home'].get('score', 0)
            }
            
            # Get play-by-play data
            pbp_data = get_play_by_play(game_id)
            if not pbp_data:
                continue
            
            # Extract plays with significant impact
            plays = pbp_data.get('liveData', {}).get('plays', {}).get('allPlays', [])
            
            for play in plays:
                impact = calculate_win_probability_impact(play)
                if impact > 0.05:  # Only consider plays with >5% WP impact
                    play_info = {
                        'impact': impact,
                        'game_info': game_info,
                        'play': play,
                        'inning': play.get('about', {}).get('inning', 0),
                        'half_inning': play.get('about', {}).get('halfInning', ''),
                        'batter': play.get('matchup', {}).get('batter', {}).get('fullName', 'Unknown'),
                        'pitcher': play.get('matchup', {}).get('pitcher', {}).get('fullName', 'Unknown'),
                        'description': play.get('result', {}).get('description', ''),
                        'event': play.get('result', {}).get('event', '')
                    }
                    high_impact_plays.append(play_info)
    
    # Sort by impact and return top 3
    high_impact_plays.sort(key=lambda x: x['impact'], reverse=True)
    return high_impact_plays[:3]

def get_font(size, bold=False):
    """Get font with fallback options"""
    try:
        if bold:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        else:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        try:
            # Windows fallback
            if bold:
                return ImageFont.truetype("arial.ttf", size)
            else:
                return ImageFont.truetype("arial.ttf", size)
        except:
            # Ultimate fallback
            return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def get_team_logo_color(team_name):
    """Get team primary colors and simplified team codes"""
    teams = {
        'Yankees': {'color': '#0C2340', 'accent': '#C4CED4', 'code': 'NYY'},
        'Red Sox': {'color': '#BD3039', 'accent': '#0C2340', 'code': 'BOS'},
        'Dodgers': {'color': '#005A9C', 'accent': '#EF3E42', 'code': 'LAD'},
        'Giants': {'color': '#FD5A1E', 'accent': '#27251F', 'code': 'SF'},
        'Braves': {'color': '#CE1141', 'accent': '#13274F', 'code': 'ATL'},
        'Phillies': {'color': '#E81828', 'accent': '#002D72', 'code': 'PHI'},
        'Angels': {'color': '#BA0021', 'accent': '#003263', 'code': 'LAA'},
        'Marlins': {'color': '#00A3E0', 'accent': '#EF3340', 'code': 'MIA'},
        'Nationals': {'color': '#AB0003', 'accent': '#14225A', 'code': 'WSH'},
        'Rockies': {'color': '#33006F', 'accent': '#C4CED4', 'code': 'COL'},
        'Astros': {'color': '#EB6E1F', 'accent': '#002D62', 'code': 'HOU'},
        'Rangers': {'color': '#C0111F', 'accent': '#003278', 'code': 'TEX'},
        'Guardians': {'color': '#E31937', 'accent': '#0C2340', 'code': 'CLE'},
        'Tigers': {'color': '#0C2340', 'accent': '#FA4616', 'code': 'DET'},
        'Twins': {'color': '#002B5C', 'accent': '#D31145', 'code': 'MIN'},
        'White Sox': {'color': '#27251F', 'accent': '#C4CED4', 'code': 'CWS'},
        'Royals': {'color': '#004687', 'accent': '#BD9B60', 'code': 'KC'},
        'Orioles': {'color': '#DF4601', 'accent': '#000000', 'code': 'BAL'},
        'Blue Jays': {'color': '#134A8E', 'accent': '#1D2D5C', 'code': 'TOR'},
        'Rays': {'color': '#092C5C', 'accent': '#8FBCE6', 'code': 'TB'},
        'Mets': {'color': '#002D72', 'accent': '#FF5910', 'code': 'NYM'},
        'Padres': {'color': '#2F241D', 'accent': '#FFC425', 'code': 'SD'},
        'Diamondbacks': {'color': '#A71930', 'accent': '#E3D4AD', 'code': 'AZ'},
        'Cardinals': {'color': '#C41E3A', 'accent': '#FEDB00', 'code': 'STL'},
        'Cubs': {'color': '#0E3386', 'accent': '#CC3433', 'code': 'CHC'},
        'Brewers': {'color': '#FFC52F', 'accent': '#12284B', 'code': 'MIL'},
        'Pirates': {'color': '#FDB827', 'accent': '#27251F', 'code': 'PIT'},
        'Reds': {'color': '#C6011F', 'accent': '#000000', 'code': 'CIN'},
        'Mariners': {'color': '#0C2C56', 'accent': '#005C5C', 'code': 'SEA'},
        'Athletics': {'color': '#003831', 'accent': '#EFB21E', 'code': 'OAK'}
    }
    
    team_key = team_name.split()[-1]
    return teams.get(team_key, {'color': '#FF6B35', 'accent': '#1A1A1A', 'code': 'MLB'})

def draw_team_logo_placeholder(draw, x, y, size, team_info):
    """Draw a team logo placeholder with team colors"""
    color = team_info['color']
    accent = team_info['accent']
    code = team_info['code']
    
    # Draw circular team badge
    draw.ellipse([x, y, x + size, y + size], fill=color, outline=accent, width=3)
    
    # Add team code text
    font = get_font(int(size * 0.3), bold=True)
    bbox = draw.textbbox((0, 0), code, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = x + (size - text_width) // 2
    text_y = y + (size - text_height) // 2
    draw.text((text_x, text_y), code, fill='white', font=font)

def create_impact_plays_graphic(plays):
    """Create a professional sports broadcast-style graphic"""
    try:
        # Professional broadcast dimensions
        width, height = 1200, 800  # 3:2 ratio like ESPN graphics
        
        # Create image with sports broadcast background
        img = Image.new('RGB', (width, height), color='#0f1419')
        draw = ImageDraw.Draw(img)
        
        # Background gradient (subtle)
        for y in range(height):
            ratio = y / height
            r = int(15 + (25 * ratio))  # Dark blue gradient
            g = int(20 + (35 * ratio))
            b = int(25 + (45 * ratio))
            color = f"#{r:02x}{g:02x}{b:02x}"
            draw.line([(0, y), (width, y)], fill=color, width=1)
        
        # Main header bar
        header_height = 120
        draw.rectangle([0, 0, width, header_height], fill='#1a2332', outline='#2a3441', width=2)
        
        # Title styling like ESPN
        title_font = get_font(42, bold=True)
        subtitle_font = get_font(24, bold=True)
        
        # Main title
        title_text = "TOP 3"
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = bbox[2] - bbox[0]
        draw.text((50, 25), title_text, fill='#ffffff', font=title_font)
        
        # Subtitle
        subtitle_text = "HIGHEST IMPACT MLB PLAYS"
        draw.text((50 + title_width + 20, 35), subtitle_text, fill='#ff6b35', font=subtitle_font)
        
        # Date
        date_font = get_font(18)
        yesterday = get_yesterday_date()
        date_text = f"FROM {yesterday}"
        date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text((width - date_width - 50, 75), date_text, fill='#888888', font=date_font)
        
        # Table header
        table_start_y = header_height + 30
        row_height = 140
        
        # Header row
        header_y = table_start_y
        draw.rectangle([40, header_y, width - 40, header_y + 50], fill='#2a3441', outline='#3a4451', width=1)
        
        # Column headers
        header_font = get_font(20, bold=True)
        draw.text((60, header_y + 15), "RANK", fill='#ffffff', font=header_font)
        draw.text((150, header_y + 15), "TEAMS", fill='#ffffff', font=header_font)
        draw.text((350, header_y + 15), "IMPACT", fill='#ffffff', font=header_font)
        draw.text((480, header_y + 15), "PLAY", fill='#ffffff', font=header_font)
        draw.text((650, header_y + 15), "SITUATION", fill='#ffffff', font=header_font)
        draw.text((900, header_y + 15), "PLAYERS", fill='#ffffff', font=header_font)
        
        # Draw each play row
        for i, play in enumerate(plays):
            row_y = table_start_y + 50 + (i * row_height)
            
            # Row background (alternating)
            bg_color = '#1a2332' if i % 2 == 0 else '#0f1419'
            draw.rectangle([40, row_y, width - 40, row_y + row_height], fill=bg_color, outline='#2a3441', width=1)
            
            # Get team info
            home_team_info = get_team_logo_color(play['game_info']['home_team'])
            away_team_info = get_team_logo_color(play['game_info']['away_team'])
            
            # Rank circle
            rank_size = 50
            rank_x = 60
            rank_y = row_y + (row_height - rank_size) // 2
            
            # Rank colors (gold, silver, bronze)
            rank_colors = ['#FFD700', '#C0C0C0', '#CD7F32']
            draw.ellipse([rank_x, rank_y, rank_x + rank_size, rank_y + rank_size], 
                        fill=rank_colors[i], outline='#ffffff', width=3)
            
            # Rank number
            rank_font = get_font(28, bold=True)
            rank_text = str(i + 1)
            bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text((rank_x + (rank_size - text_width) // 2, rank_y + (rank_size - text_height) // 2), 
                     rank_text, fill='black', font=rank_font)
            
            # Team logos and matchup
            logo_size = 40
            away_logo_x = 150
            away_logo_y = row_y + 20
            home_logo_x = 240
            home_logo_y = row_y + 20
            
            # Draw team logo placeholders
            draw_team_logo_placeholder(draw, away_logo_x, away_logo_y, logo_size, away_team_info)
            draw_team_logo_placeholder(draw, home_logo_x, home_logo_y, logo_size, home_team_info)
            
            # Score
            score_font = get_font(24, bold=True)
            score_text = f"{play['game_info']['away_score']} - {play['game_info']['home_score']}"
            draw.text((away_logo_x + 10, away_logo_y + logo_size + 10), score_text, fill='#ffffff', font=score_font)
            
            # Team names (abbreviated)
            team_font = get_font(16)
            draw.text((away_logo_x, away_logo_y + logo_size + 40), away_team_info['code'], fill='#cccccc', font=team_font)
            draw.text((home_logo_x, home_logo_y + logo_size + 40), home_team_info['code'], fill='#cccccc', font=team_font)
            
            # Impact percentage (large and prominent)
            impact_font = get_font(36, bold=True)
            impact_text = f"{play['impact']:.1%}"
            draw.text((350, row_y + 30), impact_text, fill='#00ff88', font=impact_font)
            
            # "WIN PROB" label
            label_font = get_font(14)
            draw.text((350, row_y + 75), "WIN PROB", fill='#888888', font=label_font)
            
            # Play type with icon
            play_font = get_font(20, bold=True)
            event_icons = {
                'Home Run': '⚾💥',
                'Double': '⚾🔥',
                'Triple': '⚾⚡',
                'Single': '⚾✨',
                'Walk': '🚶‍♂️',
                'Strikeout': '❌',
                'Grounded Into DP': '⬇️',
                'Field Error': '🤦',
                'Wild Pitch': '🌪️',
                'Sacrifice Fly': '🕊️'
            }
            
            event = play.get('event', 'Play')
            icon = event_icons.get(event, '⚾')
            play_text = f"{icon}"
            draw.text((480, row_y + 25), play_text, fill='white', font=play_font)
            
            # Event name
            event_font = get_font(18, bold=True)
            event_name = event.upper() if len(event) <= 12 else event[:9] + "..."
            draw.text((480, row_y + 60), event_name, fill=home_team_info['color'], font=event_font)
            
            # Situation (inning, runners)
            situation_font = get_font(16)
            inning_text = f"T{play['inning']}" if play['half_inning'] == 'top' else f"B{play['inning']}"
            draw.text((650, row_y + 30), inning_text, fill='#ffffff', font=situation_font)
            
            # Additional context
            context_font = get_font(14)
            context_text = f"High Leverage"
            draw.text((650, row_y + 55), context_text, fill='#ffaa00', font=context_font)
            
            # Players
            player_font = get_font(16)
            batter = play['batter'].split()[-1] if play.get('batter') else 'Unknown'
            pitcher = play['pitcher'].split()[-1] if play.get('pitcher') else 'Unknown'
            
            draw.text((900, row_y + 25), f"BATTER:", fill='#888888', font=get_font(12))
            draw.text((900, row_y + 45), batter, fill='#ffffff', font=player_font)
            
            draw.text((900, row_y + 70), f"PITCHER:", fill='#888888', font=get_font(12))
            draw.text((900, row_y + 90), pitcher, fill='#ffffff', font=player_font)
        
        # Bottom branding
        footer_y = height - 60
        draw.rectangle([0, footer_y, width, height], fill='#1a2332')
        
        footer_font = get_font(16)
        branding_text = "MLB IMPACT TRACKER • WIN PROBABILITY ANALYSIS"
        bbox = draw.textbbox((0, 0), branding_text, font=footer_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, footer_y + 20), branding_text, fill='#888888', font=footer_font)
        
        # Hashtags
        hashtag_font = get_font(14)
        hashtags = "#MLB #Baseball #Analytics #WinProbability"
        bbox = draw.textbbox((0, 0), hashtags, font=hashtag_font)
        hashtag_width = bbox[2] - bbox[0]
        draw.text(((width - hashtag_width) // 2, footer_y + 40), hashtags, fill='#666666', font=hashtag_font)
        
        # Convert to BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG', quality=95, optimize=True)
        img_buffer.seek(0)
        
        return img_buffer
        
    except Exception as e:
        logger.error(f"Error creating professional impact plays graphic: {str(e)}")
        return None

def send_daily_impact_tweet():
    """Send the daily tweet with top impact plays from PREVIOUS DAY (not current day)"""
    try:
        logger.info("🚨 Preparing daily impact plays tweet for PREVIOUS DAY...")
        
        # Import the live tracker to get PREVIOUS day's data
        from live_impact_tracker import LiveImpactTracker
        
        # Load the live tracker and get PREVIOUS day's top plays
        tracker = LiveImpactTracker()
        top_plays_data = tracker.get_previous_day_top_plays()  # Changed from get_daily_top_plays()
        
        if not top_plays_data:
            logger.warning("❌ No high-impact plays found for previous day")
            if not TEST_MODE:
                previous_date = tracker.get_previous_date()
                previous_date_formatted = datetime.strptime(previous_date, "%Y-%m-%d").strftime("%m/%d/%Y")
                fallback_tweet = f"🚨 No major impact plays detected in MLB games on {previous_date_formatted}. Sometimes that's just how baseball goes! Check back tomorrow for the biggest moments. ⚾"
                client.create_tweet(text=fallback_tweet)
                logger.info("✅ Sent fallback tweet for previous day")
            return
        
        # Convert ImpactPlay objects to the format expected by our tweet formatting
        top_plays = []
        for play_data in top_plays_data:
            play_info = {
                'impact': play_data.impact,
                'game_info': {
                    'game_id': play_data.game_id,
                    'away_team': play_data.away_team,
                    'home_team': play_data.home_team,
                    'away_score': play_data.away_score,
                    'home_score': play_data.home_score
                },
                'inning': play_data.inning,
                'half_inning': play_data.half_inning,
                'batter': play_data.batter,
                'pitcher': play_data.pitcher,
                'description': play_data.description,
                'event': play_data.event,
                'has_real_wpa': play_data.has_real_wpa,
                'wpa': play_data.wpa
            }
            top_plays.append(play_info)
        
        # Create tweet text using PREVIOUS day's date
        previous_date = tracker.get_previous_date()
        previous_date_formatted = datetime.strptime(previous_date, "%Y-%m-%d").strftime("%m/%d/%Y")
        
        tweet_text = f"🚨 BIGGEST MLB IMPACT PLAYS ({previous_date_formatted}) 🚨\n\n"
        
        # Medal emojis for ranking
        medals = ["🥇", "🥈", "🥉"]
        
        for i, play in enumerate(top_plays):
            # Get team abbreviations
            away_team = get_team_abbreviation(play['game_info']['away_team'])
            home_team = get_team_abbreviation(play['game_info']['home_team'])
            
            # Get game situation
            inning = play['inning']
            half_inning = "Bot" if play['half_inning'] == 'bottom' else "Top"
            
            # Format impact percentage - show if it's real WPA or statistical
            impact_pct = f"{play['impact']:.1%}"
            wpa_source = "🎯 MLB WPA" if play.get('has_real_wpa', False) else "📊 Statistical"
            
            # Final scores
            away_score = play['game_info']['away_score']
            home_score = play['game_info']['home_score']
            
            # Build the play description
            tweet_text += f"{medals[i]} {play['description']}\n"
            tweet_text += f"{half_inning} {inning} • Impact: {impact_pct} ({wpa_source})\n"
            tweet_text += f"Final: {away_team} {away_score}, {home_team} {home_score}\n\n"
        
        tweet_text += "#MLB #Baseball #WinProbability #LiveTracking"
        
        # Send tweet
        if not TEST_MODE:
            client.create_tweet(text=tweet_text)
            logger.info(f"✅ Successfully sent daily impact plays tweet for {previous_date_formatted}")
        else:
            logger.info(f"TEST MODE - Would send tweet for {previous_date_formatted}:\n{tweet_text}")
        
        # Also log summary
        real_wpa_count = sum(1 for play in top_plays if play.get('has_real_wpa', False))
        logger.info(f"📊 Tweet summary: {len(top_plays)} plays from {previous_date_formatted} ({real_wpa_count} with real WPA, {len(top_plays) - real_wpa_count} statistical)")
        
    except Exception as e:
        logger.error(f"❌ Error sending daily impact tweet: {e}")
        import traceback
        traceback.print_exc()

def get_team_abbreviation(team_name):
    """Get team abbreviation from full name"""
    abbreviations = {
        'Yankees': 'NYY', 'Red Sox': 'BOS', 'Dodgers': 'LAD', 'Giants': 'SF',
        'Braves': 'ATL', 'Phillies': 'PHI', 'Angels': 'LAA', 'Marlins': 'MIA',
        'Nationals': 'WSH', 'Rockies': 'COL', 'Astros': 'HOU', 'Rangers': 'TEX',
        'Guardians': 'CLE', 'Tigers': 'DET', 'Twins': 'MIN', 'White Sox': 'CWS',
        'Royals': 'KC', 'Orioles': 'BAL', 'Blue Jays': 'TOR', 'Rays': 'TB',
        'Mets': 'NYM', 'Padres': 'SD', 'Diamondbacks': 'AZ', 'Cardinals': 'STL',
        'Cubs': 'CHC', 'Brewers': 'MIL', 'Pirates': 'PIT', 'Reds': 'CIN',
        'Mariners': 'SEA', 'Athletics': 'OAK'
    }
    
    team_key = team_name.split()[-1]
    return abbreviations.get(team_key, team_key[:3].upper())

def schedule_daily_tweet():
    """Schedule the daily tweet for 12 PM Eastern"""
    schedule.every().day.at("12:00").do(send_daily_impact_tweet)
    logger.info("Scheduled daily tweet for 12:00 PM Eastern")

def run_scheduler():
    """Run the scheduler in a separate thread"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

@app.route('/')
def home():
    """Simple health check endpoint"""
    try:
        current_time = datetime.now(eastern_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        next_run = schedule.next_run()
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "Not scheduled"
        
        return f"""
        <html>
        <head><title>MLB Impact Plays Tracker</title></head>
        <body style="font-family: Arial, sans-serif; background-color: #1a1a1a; color: white; padding: 20px;">
            <h1>🚨 MLB Impact Plays Tracker 🚨</h1>
            <p><strong>Status:</strong> Active</p>
            <p><strong>Current Time (ET):</strong> {current_time}</p>
            <p><strong>Next Scheduled Tweet:</strong> {next_run_str}</p>
            <p><strong>Function:</strong> Daily tweets at 12 PM ET with top 3 impact plays from previous day</p>
            <p><strong>Test Mode:</strong> {'ON' if TEST_MODE else 'OFF'}</p>
            <hr>
            <p style="color: #ff6b35;">Tracking the biggest moments in baseball, one win probability swing at a time! ⚾</p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/test')
def test_endpoint():
    """Test endpoint to manually trigger impact analysis"""
    try:
        send_daily_impact_tweet()
        return "Test tweet sent successfully!"
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return f"Error: {str(e)}", 500

def main():
    """Main function to start the application"""
    logger.info("Starting MLB Impact Plays Tracker...")
    
    # Schedule the daily tweet
    schedule_daily_tweet()
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main() 