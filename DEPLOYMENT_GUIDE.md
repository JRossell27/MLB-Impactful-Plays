# 🚀 Enhanced MLB Impact Tracker - Deployment Guide

## Quick Deploy to Render

### 1. **Create Discord Webhook** 🔗
1. Go to your Discord server
2. Click **Server Settings** → **Integrations** → **Webhooks**
3. Click **Create Webhook**
4. Choose the channel for notifications
5. **Copy the Webhook URL** (you'll need this for step 3)

### 2. **Deploy to Render** 🌐
1. Fork this repository to your GitHub account
2. Go to [Render.com](https://render.com) and create an account
3. Click **New** → **Web Service**
4. Connect your GitHub account and select your forked repository
5. Configure the service:
   - **Name**: `mlb-impact-tracker` (or your preferred name)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `./startup.sh`

### 3. **Set Environment Variables** ⚙️
In your Render dashboard, go to **Environment** and add:

| Variable Name | Value | Description |
|---------------|--------|-------------|
| `DISCORD_WEBHOOK_URL` | `your_webhook_url_from_step_1` | **REQUIRED** - Your Discord webhook URL for notifications |
| `PORT` | `5000` | Optional - Port for the web dashboard |
| `FLASK_ENV` | `production` | Optional - Flask environment |

⚠️ **IMPORTANT**: Never commit webhook URLs to your repository! Always use environment variables.

### 4. **Deploy** 🚀
1. Click **Create Web Service**
2. Render will automatically deploy your service
3. You'll get a URL like `https://your-app-name.onrender.com`

### 5. **Verify Deployment** ✅
1. Visit your Render URL to see the dashboard
2. Check that monitoring status shows "🟢 ACTIVE"
3. Watch the logs for successful game monitoring

---

## 🔧 Advanced Configuration

### Custom Domain (Optional)
1. In Render dashboard: **Settings** → **Custom Domains**
2. Add your domain and follow DNS instructions

### Monitoring & Alerts
- **Dashboard**: Your Render URL shows real-time system status
- **Logs**: Check Render logs for detailed monitoring activity
- **Discord**: High-impact plays will be posted automatically

---

## 🛠️ Local Development

For local testing:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/MLB-Impactful-Plays.git
cd MLB-Impactful-Plays

# 2. Set up environment
pip install -r requirements.txt

# 3. Set Discord webhook (replace with your URL)
export DISCORD_WEBHOOK_URL="your_webhook_url_here"

# 4. Test the system
RUN_TEST=true bash startup.sh

# 5. Run the dashboard
python enhanced_dashboard.py
```

---

## 🔒 Security Best Practices

✅ **DO:**
- Set `DISCORD_WEBHOOK_URL` as environment variable in Render
- Keep your webhook URLs private
- Regenerate webhooks if compromised

❌ **DON'T:**
- Commit webhook URLs to your repository
- Share webhook URLs publicly
- Use hardcoded credentials in code

---

## 📊 System Features

- **Real-time monitoring** of all MLB games every 2 minutes
- **High-impact play detection** using Baseball Savant WP% data
- **Automatic GIF creation** for visual highlights
- **Discord notifications** with embedded content
- **Web dashboard** for system monitoring
- **Comprehensive logging** for troubleshooting

---

## 🔍 Troubleshooting

### No Discord Notifications
- Check that `DISCORD_WEBHOOK_URL` is set in Render environment
- Verify webhook URL is correct in Discord
- Check Render logs for connection errors

### System Not Monitoring
- Check dashboard shows "🟢 ACTIVE" status
- Verify Render logs show monitoring activity
- During off-season, games may be limited

### Performance Issues
- Render free tier may sleep - upgrade for 24/7 operation
- Check logs for memory or timeout issues

---

## 📈 Monitoring Stats

The system tracks:
- Games monitored per day
- High-impact plays detected
- GIFs created and posted
- System uptime and health

All stats are visible on the web dashboard and in Discord status updates. 