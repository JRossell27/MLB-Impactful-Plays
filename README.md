# MLB Marquee Moments Tracker

⭐ **Automatically tweets the most elite MLB moments as they happen live!**

This system monitors all live MLB games every 2 minutes and immediately tweets only the most significant marquee moments - plays with massive win probability impact. No noise, just the biggest moments in baseball!

## 🚀 What It Does

- **Real-Time Monitoring**: Scans all live MLB games every 2 minutes
- **Elite Detection**: Uses MLB's official Win Probability Added (WPA) data and leverage index
- **Marquee Moments**: Posts only plays with ≥40% win probability change
- **Curated Experience**: Targets 2-3 truly game-changing plays per night across all MLB
- **Text-Only Tweets**: Clean, focused tweets with official team hashtags

## 📊 Marquee Moment Thresholds

The system tweets only plays that meet these ELITE criteria:
- **≥40% win probability change** (primary threshold for marquee moments)
- **≥30% win probability change** in super high leverage (LI ≥ 3.0)
- **≥25% win probability change** in very clutch moments (LI ≥ 2.5)

This filters down to approximately **2-3 tweets per night** across all MLB games, ensuring only the most impactful moments reach your timeline.

## 🏗️ Architecture

### Real-Time Components
- **Game Monitor**: Fetches live games from MLB API
- **Play Analyzer**: Calculates impact scores using WPA and leverage
- **Tweet Generator**: Creates graphics and posts to Twitter
- **Web Dashboard**: Flask interface for monitoring and control

### Key Features
- **Duplicate Prevention**: Tracks posted plays to avoid repeats
- **Error Recovery**: Continues monitoring even if individual requests fail
- **Live Dashboard**: Real-time status at http://localhost:5000
- **Manual Control**: Start/stop monitoring via web interface

## 🛠️ Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Twitter API
Create a `.env` file:
```env
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

# For Render deployment (keep-alive pings)
SITE_URL=https://your-app-name.onrender.com
```

### 3. Test the System
```bash
python test_realtime_tracker.py
```

### 4. Start Real-Time Monitoring
```bash
python realtime_impact_tracker.py
```

Visit http://localhost:5000 and click "Start Monitoring"

## 📱 Example Tweet

```
⭐ MARQUEE MOMENT!

Aaron Judge homers (30) on a fly ball to left center field. 
Anthony Rizzo scores.

📊 Impact: 42.3% WP change
⚾ HOU 4 - 6 NYY (B9)

#BuiltForThis #RepBX
```

## 🎯 Tweet Features

Each tweet includes:
- Play description and context
- Game score and inning
- Impact score (WP change percentage)
- Official team hashtags for both teams
- Clean, focused format optimized for engagement

## 📋 Configuration

### Marquee Moment Thresholds
Edit the `is_high_impact_play()` method in `realtime_impact_tracker.py`:
```python
def is_high_impact_play(self, impact_score: float, leverage: float = 1.0) -> bool:
    if impact_score >= 0.40:  # 40%+ WP swing - elite marquee moments
        return True
    if impact_score >= 0.30 and leverage >= 3.0:  # 30%+ in super high leverage
        return True
    # Add your custom criteria here
```

### Monitoring Interval
Change the sleep time in `monitor_games()`:
```python
sleep_time = max(0, 120 - elapsed)  # 120 = 2 minutes
```

### Graphic Styling
Customize colors and layout in `create_play_graphic()`:
```python
orange = '#FF6B35'  # Primary accent color
white = '#FFFFFF'   # Text color
gray = '#8B949E'    # Secondary text
red = '#FF4444'     # High-impact indicator
```

## 📊 Web Dashboard

The system includes a web dashboard at http://localhost:5000 showing:
- **Monitoring Status**: Active/Inactive
- **Twitter Connection**: Connected/Disconnected  
- **Plays Posted**: Daily count
- **Last Check**: Most recent scan time

### Endpoints
- `/` - Main dashboard
- `/start` - Start monitoring
- `/stop` - Stop monitoring
- `/health` - Health check (JSON)

## 🚀 Deployment

### Local Development
```bash
python realtime_impact_tracker.py
# Visit http://localhost:5000
```

### Production (Render)
Set environment variable:
```
FLASK_ENV=production
SITE_URL=https://your-app-name.onrender.com
```

The system will auto-start monitoring and run the web interface.

**Keep-Alive System**: The app automatically pings itself every 6 minutes to prevent Render free tier from spinning down, ensuring continuous monitoring.

## 📋 Dependencies

- **tweepy**: Twitter API interface
- **requests**: MLB API calls  
- **Pillow (PIL)**: Graphic generation
- **Flask**: Web dashboard
- **threading**: Concurrent monitoring

## 🔍 Troubleshooting

### No Tweets Posted
- Check Twitter API credentials in `.env`
- Verify games are currently live
- Check impact thresholds (may need lowering during slow games)
- Review logs in `impact_tracker.log`

### API Errors
- MLB API sometimes has delays - system will retry
- Twitter rate limits are handled automatically
- Network issues will trigger 2-minute retry

### Testing Without Live Games
```bash
python test_realtime_tracker.py
```
This tests core functionality with recent game data.

## 🎯 Future Enhancements

- **Team Filtering**: Tweet only specific teams
- **Hashtag Customization**: Dynamic hashtags based on teams
- **Multi-Platform**: Add Discord, Slack notifications
- **Historical Analysis**: Track and analyze posted plays
- **Advanced Graphics**: Team logos, player photos

## 📈 Performance

- **Memory Usage**: ~50MB baseline
- **API Calls**: ~30 requests per 2-minute cycle (scales with live games)
- **Tweet Rate**: 2-3 marquee moments per night across all MLB games
- **Response Time**: <30 seconds from play occurrence to tweet

---

**Ready to catch every game-changing moment in real-time!** ⚾🔥 