# 🏠⚾ New York Mets Home Run Tracker

A real-time monitoring system that captures **EVERY SINGLE** New York Mets home run and automatically creates GIFs with Discord notifications.

## 🎯 What This Does

- **🔍 Monitors Live Games**: Checks every 2 minutes for active Mets games
- **🏠 Detects All Mets HRs**: Captures every single Mets home run (no WPA filtering)
- **🎬 Creates GIFs**: Automatically generates GIFs from Baseball Savant
- **📱 Posts to Discord**: Sends HR GIFs with game context to Discord channels
- **💓 Keep-Alive System**: Prevents deployment sleep with automatic pings

## 🚀 Key Features

### ✨ No Impact Filtering
Unlike the previous system, this captures **ALL** Mets home runs regardless of game situation or win probability impact.

### ⚡ Real-Time Processing
- Monitors every 2 minutes during live games
- Processes GIFs in background queue
- Handles multiple concurrent home runs

### 🎬 Baseball Savant Integration
- Fetches high-quality video clips
- Converts to GIFs automatically
- Matches plays using MLB API data
- Includes Statcast data (exit velocity, launch angle, distance)

### 📊 Dashboard Monitoring
- Beautiful web interface with Mets colors
- Real-time status updates
- Queue management and statistics

## 🔧 Setup Instructions

### 1. Environment Variables
Create a `.env` file or set these environment variables:

```bash
# Discord Integration - YOUR WEBHOOK
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB

# Optional: Deployment Settings
SITE_URL=your_deployment_url  # For keep-alive pings
AUTO_START_MONITORING=true    # Auto-start on deployment
PORT=5000                     # Web dashboard port

# GitHub Repository
GITHUB_REPO=https://github.com/JRossell27/Mets_HRs
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Test the System
```bash
python test_mets_tracker.py
```

### 4. Start Monitoring
```bash
# Using startup script
./startup.sh

# Or directly
python mets_dashboard.py
```

## 🎮 Usage

### Web Dashboard
Visit `http://localhost:5000` (or your deployment URL) to:
- ✅ Start/stop monitoring
- 📊 View real-time statistics
- 🧪 Test system functionality
- 👁️ Monitor queue status

### API Endpoints
- `GET /` - Dashboard interface
- `GET /api/status` - JSON status
- `GET /health` - Health check
- `GET /ping` - Keep-alive ping
- `GET /start` - Start monitoring
- `GET /stop` - Stop monitoring
- `GET /test` - Test system

## 📱 Discord Integration

### Message Format
```
🏠⚾ **Pete Alonso** goes yard! ⚾🏠

Alonso homers (15) on a fly ball to left center field.

Exit Velocity: 108.5 mph | Launch Angle: 25° | Distance: 425 ft

#LGM
```

### Discord Setup
Your webhook is already configured in the system:
- **Webhook URL**: `https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB`
- **Format**: Player name + "goes yard" + description + Statcast stats + #LGM
- **Auto-posting**: GIFs are automatically posted when home runs are detected

## 🔄 How It Works

### 1. Game Monitoring
```python
# Checks for live/recent Mets games
games = tracker.get_live_mets_games()

# Filters for team ID 121 (Mets)
# Includes live games and recently finished (for video availability)
```

### 2. Home Run Detection
```python
def is_mets_home_run(self, play: Dict) -> bool:
    event = play.get('event', '').lower()
    batter_team_id = play.get('batter_team_id')
    
    is_home_run = 'home_run' in event
    is_mets_batter = batter_team_id == 121  # Mets team ID
    
    return is_home_run and is_mets_batter
```

### 3. GIF Processing Queue
- ⏰ Rate limited (5 minutes between attempts)
- 🔄 Retry logic (max 5 attempts per HR)
- 🧹 Automatic cleanup after posting
- 💾 Persistent queue across restarts

## 📊 Monitoring & Statistics

### Dashboard Metrics
- 🏠 Home runs posted today
- ⏳ Current queue size
- 🎬 GIFs created today
- ⏱️ System uptime
- 🔍 Last check time

### Logging
All activity is logged to:
- `mets_homerun_tracker.log` - Main system log
- Console output for real-time monitoring

## 🛠️ Technical Details

### Key Components
- **`mets_homerun_tracker.py`** - Core monitoring logic
- **`mets_dashboard.py`** - Web interface and controls
- **`baseball_savant_gif_integration.py`** - GIF creation (inherited)
- **`discord_integration.py`** - Discord posting (inherited)

### Data Flow
1. 📡 **Monitor** → Check live Mets games every 2 minutes
2. 🔍 **Detect** → Find home run events for Mets batters
3. 📝 **Queue** → Add home runs to processing queue
4. 🎬 **Process** → Create GIF from Baseball Savant + get Statcast data
5. 📱 **Post** → Send to Discord with exit velocity/launch angle stats
6. 🧹 **Cleanup** → Remove from queue and delete files

### Memory Management
- Queue size limits (20 HRs max)
- Automatic file cleanup
- Processed plays tracking (200 max)
- Graceful handling of deployment constraints

## 🚀 Deployment

### GitHub Repository
- **Repository**: https://github.com/JRossell27/Mets_HRs
- **Webhook Configured**: Discord posting ready to go
- **Auto-Deploy**: Ready for Render.com or similar platforms

### Render.com (Recommended)
1. Connect GitHub repository (`https://github.com/JRossell27/Mets_HRs`)
2. Set environment variables in Render dashboard
3. Uses `startup.sh` automatically
4. Built-in keep-alive system prevents sleep

### Docker
```dockerfile
FROM python:3.9
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["./startup.sh"]
```

### Environment Variables for Production
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB
SITE_URL=https://your-app.onrender.com
AUTO_START_MONITORING=true
PORT=5000
```

## 🏟️ Why Mets-Specific?

This system is optimized specifically for Mets fans:
- 🎯 **Team ID 121**: Only monitors Mets games
- 🎨 **Mets Colors**: Orange and blue dashboard theme
- 📱 **#LGM**: Proper hashtags and fan terminology
- ⚾ **Every Homer**: No filtering - every Mets HR matters!
- 📊 **Statcast Stats**: Exit velocity, launch angle, and distance for each HR

## 🔧 Troubleshooting

### Common Issues
1. **No GIFs Created**: Check Baseball Savant connectivity
2. **Discord Not Posting**: Verify webhook URL
3. **No Games Found**: Check if it's baseball season
4. **System Sleep**: Ensure keep-alive pings are working
5. **Missing Stats**: Statcast data may not be available immediately

### Debug Mode
```bash
# Test individual components
python test_mets_tracker.py

# Check current Mets games
python -c "from mets_homerun_tracker import MetsHomeRunTracker; print(MetsHomeRunTracker().get_live_mets_games())"
```

## 📈 Future Enhancements

- 📊 Historical HR database
- 🎥 Multiple video angles
- 📱 Twitter integration
- 🏆 Season/career stats overlay
- 🔔 Push notifications
- 📱 Mobile-optimized dashboard
- 🎯 Spray chart overlays

## 🤝 Contributing

This system builds on the existing Baseball Impact Players infrastructure:
- Inherits GIF creation capabilities
- Reuses Discord integration
- Maintains deployment compatibility
- Adds Mets-specific filtering and theming

## 📄 License

Built for Mets fans, by Mets fans. Let's Go Mets! 🧡💙

---

## 🏃‍♂️ Quick Start

```bash
# 1. Clone from GitHub
git clone https://github.com/JRossell27/Mets_HRs
cd Mets_HRs

# 2. Install dependencies
pip install -r requirements.txt

# 3. Discord webhook is already configured in the code
# No additional setup needed for Discord!

# 4. Test system
python test_mets_tracker.py

# 5. Start monitoring
./startup.sh
```

**Dashboard**: http://localhost:5000

**Ready for every Mets home run! 🏠⚾** 