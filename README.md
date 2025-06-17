# MLB Impact System

A real-time tracking system for the biggest moments in Major League Baseball, using Win Probability Added (WPA) data to identify high-impact plays and automatically tweet daily summaries.

## 🚀 Features

- **Live Game Monitoring**: Tracks all MLB games every 2 minutes
- **Real WPA Data**: Uses official MLB WPA data when available, statistical model as fallback
- **Daily Tweets**: Automatically tweets top 3 impact plays from previous day at 12 PM ET
- **Web Dashboard**: Professional interface showing current status and top plays
- **Previous Day Focus**: Ensures early games don't interfere with scheduled tweets

## 🏗️ System Architecture

- **Live Impact Tracker** (`live_impact_tracker.py`): Continuously monitors games and collects impact plays
- **Tweet System** (`impact_plays_tracker.py`): Handles daily tweet generation and formatting
- **Web Interface** (`mlb_impact_system.py`): Flask dashboard with auto-refresh and status monitoring

## 📊 Data Sources

1. **Primary**: Real MLB WPA data from `statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live`
2. **Fallback**: Enhanced statistical model based on game situation and leverage

## 🚀 Render Deployment

### Environment Variables

Set these in your Render dashboard:

```env
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
PORT=5000
```

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
python mlb_impact_system.py
```

### Service Configuration

- **Service Type**: Web Service
- **Environment**: Python 3.11+
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python mlb_impact_system.py`
- **Health Check Path**: `/`

## 🖥️ Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file with Twitter API credentials
4. Run: `python mlb_impact_system.py`
5. Visit: `http://localhost:5000`

## 📱 Web Dashboard

The dashboard provides:

- **Real-time Status**: System health and tracking status
- **Current Top Plays**: Today's highest impact plays
- **Tweet Schedule**: Next scheduled tweet time
- **Auto-refresh**: Updates every 30 seconds
- **Mobile Responsive**: Works on all devices

### Dashboard Features

- 🟢 **System Status**: Live/stopped indicators
- 📊 **Data Tracking**: Last update time and play counts
- 🐦 **Tweet Status**: Schedule and content information
- 🏆 **Live Leaderboard**: Current top 3 plays with details
- 🎯 **WPA Indicators**: Shows real vs statistical calculations

## 🤖 Tweet Logic

- **Schedule**: Daily at 12:00 PM ET
- **Content**: Previous day's top 3 impact plays
- **Format**: Medals (🥇🥈🥉), impact percentages, WPA source indicators
- **Fallback**: If no plays found, sends explanatory tweet

## 📈 Impact Calculation

### Real WPA (Priority 1)
- Uses `result.wpa` from MLB live feed
- Values range from -1.0 to 1.0
- Converted to percentage: `abs(wpa) * 100`

### Statistical Model (Fallback)
- Inning leverage multiplier
- Score situation impact
- Runner/out state factors
- Play type significance
- Realistic caps based on MLB data

## 🔧 Configuration

### Test Mode
Set `TEST_MODE = True` in `impact_plays_tracker.py` to prevent actual tweets.

### Monitoring Interval
Default: 2 minutes (configurable in `start_monitoring()`)

### Data Persistence
- Current day: `daily_top_plays.pkl`
- Previous days: `daily_top_plays_YYYY-MM-DD.pkl`

## 📊 API Endpoints

- `/` - Main dashboard
- `/test-tweet` - Manual tweet trigger
- `/current-plays` - JSON API for current plays

## 🛠️ Troubleshooting

### Common Issues

1. **No plays found**: System may need time to detect games
2. **Twitter API errors**: Check credentials and rate limits
3. **Data loading issues**: Check file permissions and disk space

### Logs

System provides detailed logging for:
- Game discovery and monitoring
- WPA data extraction
- Tweet generation and sending
- Error tracking and recovery

## 📝 File Structure

```
mlb-impact-system/
├── mlb_impact_system.py      # Main system orchestrator
├── live_impact_tracker.py    # Live game monitoring
├── impact_plays_tracker.py   # Tweet generation
├── requirements.txt          # Dependencies
├── README.md                # This file
└── .env                     # Environment variables (local)
```

## 🔒 Security

- Environment variables for sensitive data
- No API keys in code
- Secure token handling
- Rate limiting respect

## 📞 Support

For issues or questions about deployment, check:
1. Render logs for startup errors
2. Dashboard status indicators
3. Environment variable configuration
4. Twitter API credential validity 