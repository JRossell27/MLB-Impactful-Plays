# 🚀 Mets HR Tracker Deployment Guide

## Quick Deploy to Render.com

### 1. GitHub Repository
- **Repository**: https://github.com/JRossell27/Mets_HRs
- **Discord Webhook**: Already configured in code
- **Dependencies**: Listed in `requirements.txt`

### 2. Render.com Setup
1. Go to [render.com](https://render.com) and sign in
2. Click "New" → "Web Service"
3. Connect to GitHub repository: `https://github.com/JRossell27/Mets_HRs`
4. Configure service:
   - **Name**: `mets-hr-tracker`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `./startup.sh`

### 3. Environment Variables (Optional)
The Discord webhook is already hardcoded, but you can set these for customization:

```bash
# Optional overrides
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1384903371198038167/wpSac_BDyX4fNTQq4d9fWV31QtZlmCKkzcMhVZpWJF9ZtJLJY4tMZ2L_x9Kn7McGOIKB
AUTO_START_MONITORING=true
PORT=5000
```

### 4. Deploy!
- Click "Create Web Service"
- Render will automatically deploy from your GitHub repo
- Your service will be available at: `https://mets-hr-tracker.onrender.com`

## 🏠⚾ What Happens After Deploy

1. **Automatic Monitoring**: Starts checking for Mets games every 2 minutes
2. **Discord Integration**: Posts GIFs with stats to your configured webhook
3. **Web Dashboard**: Available at your Render URL for monitoring
4. **Keep-Alive**: Automatic pings prevent the service from sleeping

## 📱 Discord Message Format

Your Discord channel will receive messages like:

```
🏠⚾ **Pete Alonso** goes yard! ⚾🏠

Alonso homers (15) on a fly ball to left center field.

Exit Velocity: 108.5 mph | Launch Angle: 25° | Distance: 425 ft

#LGM
```

## 🔧 Local Testing Before Deploy

```bash
# 1. Test the system
python test_mets_tracker.py

# 2. Run locally
./startup.sh

# 3. Check dashboard
open http://localhost:5000
```

## 🛠️ Troubleshooting

### Common Issues
- **Build fails**: Check that all files are committed to GitHub
- **Discord not posting**: Webhook is hardcoded, should work automatically
- **No games found**: Normal during off-season or non-game days
- **Service sleeps**: The keep-alive system should prevent this

### Render.com Specific
- **Logs**: Check the Render dashboard for build and runtime logs
- **Redeploy**: Push to GitHub main branch to trigger redeployment
- **Environment**: Render automatically sets PORT and other variables

## 🎯 Next Steps After Deploy

1. **Monitor Dashboard**: Visit your Render URL to see the web interface
2. **Test Discord**: Wait for a Mets home run (or test with manual trigger)
3. **Share the Love**: Let other Mets fans know about the Discord channel!
4. **Enjoy**: Every Mets home run will now be automatically captured with GIFs

## 🏟️ Ready for the Season!

Your Mets HR tracker is now:
- ✅ Monitoring every Mets game
- ✅ Creating GIFs for all home runs
- ✅ Posting to Discord with Statcast data
- ✅ Available 24/7 with keep-alive
- ✅ Accessible via web dashboard

**Let's Go Mets! 🧡💙 #LGM** 