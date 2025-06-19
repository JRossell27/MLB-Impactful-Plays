#!/usr/bin/env python3
"""
Flask Dashboard for Enhanced MLB Impact Tracker
Displays real-time queue status, GIF processing, and system metrics
"""

from flask import Flask, render_template_string, jsonify, redirect, url_for, flash
import threading
import os
from datetime import datetime
from enhanced_impact_tracker import EnhancedImpactTracker
from discord_integration import discord_client
import logging

app = Flask(__name__)
tracker = None
logger = logging.getLogger(__name__)

@app.route('/')
def dashboard():
    """Enhanced dashboard showing queue status and GIF processing"""
    status = tracker.get_status() if tracker else {}
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced MLB Impact Tracker</title>
        <meta http-equiv="refresh" content="15">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                min-height: 100vh;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { 
                text-align: center; 
                margin-bottom: 40px; 
                padding: 30px;
                background: rgba(0,0,0,0.2);
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            .header h1 { 
                font-size: 2.5em; 
                margin: 0;
                background: linear-gradient(45deg, #ff6b35, #f7931e);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .header p { 
                font-size: 1.2em; 
                opacity: 0.9; 
                margin: 10px 0 0 0;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }
            
            .stat-card {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 25px;
                border: 1px solid rgba(255,255,255,0.2);
                transition: transform 0.3s ease;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
            }
            
            .stat-title {
                font-size: 1.1em;
                margin-bottom: 15px;
                color: #ff6b35;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .stat-value {
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 10px;
                color: #00ff88;
            }
            
            .stat-label {
                opacity: 0.8;
                font-size: 0.9em;
            }
            
            .status-indicator {
                display: inline-block;
                padding: 8px 16px;
                border-radius: 25px;
                font-weight: 600;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .status-active {
                background: linear-gradient(45deg, #28a745, #20c997);
                color: white;
            }
            
            .status-inactive {
                background: linear-gradient(45deg, #dc3545, #c82333);
                color: white;
            }
            
            .queue-section {
                background: rgba(0,0,0,0.3);
                border-radius: 15px;
                padding: 30px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
            }
            
            .queue-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid rgba(255,107,53,0.3);
            }
            
            .queue-title {
                font-size: 1.5em;
                font-weight: bold;
                color: #ff6b35;
            }
            
            .queue-count {
                background: linear-gradient(45deg, #ff6b35, #f7931e);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
            }
            
            .queue-item {
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                border-left: 4px solid #ff6b35;
                transition: all 0.3s ease;
            }
            
            .queue-item:hover {
                background: rgba(255,255,255,0.1);
                transform: translateX(5px);
            }
            
            .play-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .play-event {
                font-size: 1.2em;
                font-weight: bold;
                color: #00ff88;
            }
            
            .play-impact {
                background: linear-gradient(45deg, #6f42c1, #e83e8c);
                color: white;
                padding: 6px 12px;
                border-radius: 15px;
                font-weight: bold;
                font-size: 0.9em;
            }
            
            .play-details {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 15px;
            }
            
            .detail-item {
                text-align: center;
            }
            
            .detail-label {
                font-size: 0.8em;
                opacity: 0.7;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }
            
            .detail-value {
                font-weight: bold;
                font-size: 1.1em;
            }
            
            .progress-bar {
                background: rgba(0,0,0,0.3);
                border-radius: 10px;
                height: 8px;
                margin-top: 15px;
                overflow: hidden;
            }
            
            .progress-fill {
                height: 100%;
                border-radius: 10px;
                transition: width 0.3s ease;
            }
            
            .progress-gif-pending { background: linear-gradient(45deg, #ffc107, #fd7e14); }
            .progress-gif-processing { background: linear-gradient(45deg, #17a2b8, #6f42c1); }
            .progress-gif-ready { background: linear-gradient(45deg, #28a745, #20c997); }
            
            .no-queue {
                text-align: center;
                padding: 40px;
                opacity: 0.7;
                font-size: 1.1em;
            }
            
            .footer {
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                opacity: 0.6;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎬 Enhanced MLB Impact Tracker</h1>
                <p>Real-time monitoring with GIF integration</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">🔍 Monitoring Status</div>
                    <div class="stat-value">
                        <span class="status-indicator {{ 'status-active' if status.get('monitoring') else 'status-inactive' }}">
                            {{ '🟢 ACTIVE' if status.get('monitoring') else '🔴 INACTIVE' }}
                        </span>
                    </div>
                    <div class="stat-label">System Status</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">🎬 GIF Processing</div>
                    <div class="stat-value">
                        <span class="status-indicator {{ 'status-active' if status.get('processing_gifs') else 'status-inactive' }}">
                            {{ '🟢 RUNNING' if status.get('processing_gifs') else '🔴 STOPPED' }}
                        </span>
                    </div>
                    <div class="stat-label">Background Thread</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">📊 Plays Queued Today</div>
                    <div class="stat-value">{{ status.get('plays_queued_today', 0) }}</div>
                    <div class="stat-label">High-Impact Plays Detected</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">🎬 GIFs Created Today</div>
                    <div class="stat-value">{{ status.get('gifs_created_today', 0) }}</div>
                    <div class="stat-label">Successful Video Processing</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">🎬 Tweets Posted Today</div>
                    <div class="stat-value">{{ status.get('tweets_posted_today', 0) }}</div>
                    <div class="stat-label">Complete Posts with GIFs</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">⏰ System Uptime</div>
                    <div class="stat-value" style="font-size: 1.5em;">{{ status.get('uptime', 'Not started') }}</div>
                    <div class="stat-label">Running Since Start</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-title">💬 Discord Test</div>
                    <div class="stat-value" style="font-size: 1.2em;">
                        <a href="/test-discord" style="text-decoration: none;">
                            <button style="
                                background: linear-gradient(45deg, #5865F2, #7289DA);
                                color: white;
                                border: none;
                                padding: 12px 24px;
                                border-radius: 25px;
                                font-weight: bold;
                                cursor: pointer;
                                transition: transform 0.2s ease;
                                font-size: 0.9em;
                                text-transform: uppercase;
                                letter-spacing: 1px;
                            " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                🚀 Send Test Message
                            </button>
                        </a>
                    </div>
                    <div class="stat-label">Test Discord Webhook</div>
                </div>
            </div>
            
            <div class="queue-section">
                <div class="queue-header">
                    <div class="queue-title">🎯 Processing Queue</div>
                    <div class="queue-count">{{ status.get('current_queue_size', 0) }} plays</div>
                </div>
                
                {% if status.get('queue_details') %}
                    {% for play in status.queue_details %}
                        <div class="queue-item">
                            <div class="play-header">
                                <div class="play-event">{{ play.event }}</div>
                                <div class="play-impact">{{ play.impact }} Impact</div>
                            </div>
                            
                            <div class="play-details">
                                <div class="detail-item">
                                    <div class="detail-label">Teams</div>
                                    <div class="detail-value">{{ play.teams }}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Queued At</div>
                                    <div class="detail-value">{{ play.timestamp }}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">GIF Attempts</div>
                                    <div class="detail-value">{{ play.attempts }}/5</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Status</div>
                                    <div class="detail-value">
                                        {% if play.tweet_posted %}
                                            ✅ Posted
                                        {% elif play.gif_created %}
                                            🎬 GIF Ready
                                        {% else %}
                                            ⏳ Processing
                                        {% endif %}
                                    </div>
                                </div>
                            </div>
                            
                            <div class="progress-bar">
                                {% if play.tweet_posted %}
                                    <div class="progress-fill progress-gif-ready" style="width: 100%;"></div>
                                {% elif play.gif_created %}
                                    <div class="progress-fill progress-gif-ready" style="width: 75%;"></div>
                                {% elif play.attempts > 0 %}
                                    <div class="progress-fill progress-gif-processing" style="width: {{ (play.attempts / 5) * 50 }}%;"></div>
                                {% else %}
                                    <div class="progress-fill progress-gif-pending" style="width: 10%;"></div>
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="no-queue">
                        <div>🎯 No plays currently in queue</div>
                        <div style="margin-top: 10px; opacity: 0.6;">Monitoring for high-impact plays...</div>
                    </div>
                {% endif %}
            </div>
            
            <div class="footer">
                <div>Last Updated: {{ status.get('last_check_time', 'Never') }}</div>
                <div>Twitter Connected: {{ '✅' if status.get('twitter_connected') else '❌' }}</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, status=status)

@app.route('/api/status')
def api_status():
    """API endpoint for status data"""
    return jsonify(tracker.get_status() if tracker else {})

@app.route('/start')
def start_monitoring():
    """Start the enhanced monitoring"""
    global tracker
    if not tracker:
        tracker = EnhancedImpactTracker()
    
    if not tracker.monitoring:
        # Start monitoring in a separate thread
        monitoring_thread = threading.Thread(target=tracker.monitor_games, daemon=True)
        monitoring_thread.start()
        return "✅ Enhanced monitoring started!"
    else:
        return "ℹ️ Monitoring already running"

@app.route('/stop')
def stop_monitoring():
    """Stop the enhanced monitoring"""
    if tracker and tracker.monitoring:
        tracker.stop_monitoring()
        return "🛑 Enhanced monitoring stopped!"
    else:
        return "ℹ️ Monitoring not running"

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring services"""
    return {'status': 'healthy', 'timestamp': str(datetime.now())}

@app.route('/test-discord')
def test_discord():
    """Send a test message to Discord webhook"""
    if not discord_client.is_configured():
        return "❌ Discord webhook not configured. Please set DISCORD_WEBHOOK_URL environment variable."
    
    try:
        # Create test play data
        test_play_data = {
            'event': 'Discord Test Message',
            'description': f'🧪 Test message sent from Enhanced MLB Impact Tracker dashboard at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'away_team': 'Test Team A',
            'home_team': 'Test Team B',
            'impact_score': 0.42,  # 42% for fun
            'inning': '9',
            'half_inning': 'Bot',
            'batter': 'Dashboard Tester',
            'pitcher': 'System Bot',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send test message
        success = discord_client.send_impact_notification(test_play_data)
        
        if success:
            return "✅ Discord test message sent successfully! Check your Discord channel."
        else:
            return "❌ Failed to send Discord test message. Check the logs for details."
            
    except Exception as e:
        return f"❌ Error sending Discord test message: {str(e)}"

def main():
    """Main function to run the dashboard"""
    global tracker
    tracker = EnhancedImpactTracker()
    
    # Auto-start monitoring like the original system
    logger.info("🏃 Auto-starting monitoring...")
    monitoring_thread = threading.Thread(target=tracker.monitor_games, daemon=True)
    monitoring_thread.start()
    logger.info("🚀 Started Enhanced Impact tracker thread")
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main() 