#!/usr/bin/env python3
"""
Sample Tweet Generator for MLB Marquee Moments
Shows examples of what tweets will look like with 40%+ WPA threshold
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_sample_tweets():
    """Generate sample tweets for different marquee moment scenarios"""
    
    # Official team hashtags mapping
    team_hashtags = {
        'OAK': '#Athletics', 'ATL': '#BravesCountry', 'BAL': '#Birdland', 
        'BOS': '#DirtyWater', 'CWS': '#WhiteSox', 'CIN': '#ATOBTTR',
        'CLE': '#GuardsBall', 'COL': '#Rockies', 'DET': '#RepDetroit',
        'HOU': '#BuiltForThis', 'KC': '#FountainsUp', 'LAA': '#RepTheHalo',
        'LAD': '#LetsGoDodgers', 'MIA': '#MarlinsBeisbol', 'MIL': '#ThisIsMyCrew',
        'MIN': '#MNTwins', 'NYM': '#LGM', 'NYY': '#RepBX',
        'PHI': '#RingTheBell', 'PIT': '#LetsGoBucs', 'SD': '#ForTheFaithful',
        'SF': '#SFGiants', 'SEA': '#TridentsUp', 'STL': '#ForTheLou',
        'TB': '#RaysUp', 'TEX': '#AllForTX', 'TOR': '#LightsUpLetsGo',
        'WSH': '#NATITUDE', 'CHC': '#BeHereForIt'
    }
    
    sample_moments = [
        {
            'description': "Aaron Judge homers (62) on a fly ball to left field. Anthony Rizzo scores.",
            'impact_score': 0.423,
            'away_team': 'TEX',
            'home_team': 'NYY', 
            'away_score': 4,
            'home_score': 6,
            'inning': 9,
            'half_inning': 'bottom',
            'leverage': 3.1,
            'batter': 'Aaron Judge',
            'pitcher': 'Aroldis Chapman'
        },
        {
            'description': "Mookie Betts hits a grand slam (18) on a line drive to right field. Freddie Freeman scores. Will Smith scores. Max Muncy scores.",
            'impact_score': 0.487,
            'away_team': 'LAD',
            'home_team': 'SF',
            'away_score': 7,
            'home_score': 3,
            'inning': 8,
            'half_inning': 'top',
            'leverage': 2.8,
            'batter': 'Mookie Betts',
            'pitcher': 'Camilo Doval'
        },
        {
            'description': "Ronald Acuña Jr. doubles (32) on a sharp line drive to left field. Ozzie Albies scores. Matt Olson scores.",
            'impact_score': 0.401,
            'away_team': 'ATL',
            'home_team': 'PHI',
            'away_score': 5,
            'home_score': 4,
            'inning': 9,
            'half_inning': 'top',
            'leverage': 3.4,
            'batter': 'Ronald Acuña Jr.',
            'pitcher': 'Craig Kimbrel'
        }
    ]
    
    print("⭐ SAMPLE MARQUEE MOMENT TWEETS")
    print("=" * 60)
    
    for i, moment in enumerate(sample_moments, 1):
        print(f"\n🎯 SAMPLE TWEET #{i}")
        print("-" * 40)
        
        # Format tweet text
        inning_text = f"{'T' if moment['half_inning'] == 'top' else 'B'}{moment['inning']}"
        
        tweet = f"⭐ MARQUEE MOMENT!\n\n"
        tweet += f"{moment['description']}\n\n"
        tweet += f"📊 Impact: {moment['impact_score']:.1%} WP change\n"
        tweet += f"⚾ {moment['away_team']} {moment['away_score']} - {moment['home_score']} {moment['home_team']} ({inning_text})\n\n"
        
        # Add official team hashtags
        hashtags = []
        if moment['away_team'] in team_hashtags:
            hashtags.append(team_hashtags[moment['away_team']])
        if moment['home_team'] in team_hashtags and moment['home_team'] != moment['away_team']:
            hashtags.append(team_hashtags[moment['home_team']])
        
        if hashtags:
            tweet += " ".join(hashtags)
        else:
            tweet += "#MLB"
        
        print(tweet)
        print(f"\nCharacter count: {len(tweet)}")
        
        # No graphics needed
        print(f"  📝 Tweet formatted (no graphic)")
    
    print(f"\n✅ Generated {len(sample_moments)} sample tweets!")
    print("📝 No graphics created (text-only tweets)")

def create_sample_graphic(moment, number):
    """Create a sample graphic for the marquee moment"""
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
        score_text = f"{moment['away_team']} {moment['away_score']} - {moment['home_score']} {moment['home_team']}"
        draw.text((50, 100), score_text, fill=white, font=subtitle_font)
        
        # Inning info
        inning_text = f"{'Top' if moment['half_inning'] == 'top' else 'Bottom'} {moment['inning']}"
        draw.text((50, 140), inning_text, fill=gray, font=body_font)
        
        # Play description (wrapped)
        description = moment['description']
        lines = wrap_text(description, body_font, width - 100)
        y_pos = 200
        for line in lines[:3]:  # Max 3 lines
            draw.text((50, y_pos), line, fill=white, font=body_font)
            y_pos += 35
        
        # Players
        draw.text((50, y_pos + 20), f"Batter: {moment['batter']}", fill=gray, font=small_font)
        draw.text((50, y_pos + 45), f"Pitcher: {moment['pitcher']}", fill=gray, font=small_font)
        
        # Impact metrics (right side)
        metrics_x = width - 350
        
        # Impact score
        impact_text = f"{moment['impact_score']:.1%}"
        draw.text((metrics_x, 200), "IMPACT SCORE", fill=orange, font=small_font)
        draw.text((metrics_x, 230), impact_text, fill=white, font=title_font)
        
        # Leverage index
        draw.text((metrics_x, 300), "LEVERAGE", fill=orange, font=small_font)
        draw.text((metrics_x, 330), f"{moment['leverage']:.1f}", fill=white, font=subtitle_font)
        
        # Win probability (simplified for sample)
        wp = 0.75 if moment['impact_score'] > 0.45 else 0.65
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
        fill_width = min(bar_width, int(bar_width * (moment['impact_score'] / 0.5)))
        if fill_width > 0:
            color = red if moment['impact_score'] >= 0.40 else orange
            draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 
                         fill=color)
        
        # Timestamp
        draw.text((50, height - 60), f"Live • Sample Graphic", fill=gray, font=small_font)
        
        # Save graphic
        filename = f"sample_graphic_{number}.png"
        img.save(filename, "PNG", quality=95)
        print(f"  📸 Created: {filename}")
        
    except Exception as e:
        print(f"  ❌ Error creating graphic {number}: {e}")

def wrap_text(text, font, max_width):
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

if __name__ == "__main__":
    create_sample_tweets() 