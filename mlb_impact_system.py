#!/usr/bin/env python3
"""
Complete MLB Impact System - Live tracking + Daily tweets
"""

import os
import time
import logging
import threading
from datetime import datetime
import schedule
import pytz
from flask import Flask

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Eastern timezone
eastern_tz = pytz.timezone('US/Eastern')

class MLBImpactSystem:
    """Complete system for tracking and tweeting MLB impact plays"""
    
    def __init__(self):
        self.live_tracker = None
        self.is_running = False
        self.tracker_thread = None
        self.scheduler_thread = None
    
    def start_live_tracking(self):
        """Start the live tracking in a background thread"""
        from live_impact_tracker import LiveImpactTracker
        
        self.live_tracker = LiveImpactTracker()
        
        def run_tracker():
            logger.info("🚀 Starting live impact tracking...")
            self.live_tracker.start_monitoring(interval_minutes=2)
        
        self.tracker_thread = threading.Thread(target=run_tracker, daemon=True)
        self.tracker_thread.start()
        logger.info("✅ Live tracking started in background")
    
    def schedule_daily_tweets(self):
        """Schedule daily tweets"""
        from impact_plays_tracker import send_daily_impact_tweet
        
        # Schedule for 12:00 PM Eastern
        schedule.every().day.at("12:00").do(send_daily_impact_tweet)
        logger.info("📅 Scheduled daily tweets for 12:00 PM Eastern")
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("✅ Tweet scheduler started")
    
    def start_system(self):
        """Start the complete system"""
        logger.info("🚨 Starting MLB Impact System...")
        self.is_running = True
        
        # Start live tracking
        self.start_live_tracking()
        
        # Start tweet scheduler
        self.schedule_daily_tweets()
        
        logger.info("✅ MLB Impact System fully operational!")
    
    def stop_system(self):
        """Stop the system"""
        logger.info("🛑 Stopping MLB Impact System...")
        self.is_running = False
        
        if self.live_tracker:
            self.live_tracker.stop_monitoring()
    
    def get_current_status(self):
        """Get current system status"""
        status = {
            'system_running': self.is_running,
            'live_tracker_active': self.live_tracker is not None and self.live_tracker.is_running,
            'current_time': datetime.now(eastern_tz).isoformat(),
            'next_tweet': None,
            'top_plays_count': 0,
            'last_updated': 'Unknown'
        }
        
        # Get next scheduled tweet time
        try:
            if schedule.jobs:
                next_run = schedule.next_run()
                if next_run:
                    status['next_tweet'] = next_run.strftime("%Y-%m-%d %H:%M:%S ET")
        except Exception as e:
            logger.error(f"Error getting next tweet schedule: {e}")
        
        # Get current top plays count and details
        if self.live_tracker:
            try:
                top_plays = self.live_tracker.get_daily_top_plays()
                status['top_plays_count'] = len(top_plays)
                status['top_plays'] = []
                
                for i, play in enumerate(top_plays, 1):
                    play_info = {
                        'rank': i,
                        'event': play.event,
                        'impact': f"{play.impact:.1f}%",
                        'teams': f"{play.away_team} @ {play.home_team}",
                        'inning': f"{play.half_inning.title()} {play.inning}",
                        'has_real_wpa': play.has_real_wpa,
                        'timestamp': play.timestamp
                    }
                    status['top_plays'].append(play_info)
                
                # Get last updated time
                status['last_updated'] = self.live_tracker.get_data_last_updated()
                
            except Exception as e:
                logger.error(f"Error getting top plays status: {e}")
                status['error'] = f"Error retrieving plays: {str(e)}"
        
        return status

# Global system instance
mlb_system = MLBImpactSystem()

@app.route('/')
def home():
    """Professional system status dashboard"""
    try:
        status = mlb_system.get_current_status()
        
        # Get last updated time from live tracker
        last_updated = "Unknown"
        if mlb_system.live_tracker:
            last_updated = mlb_system.live_tracker.get_data_last_updated()
            if last_updated != "Unknown" and last_updated != "No data file found":
                try:
                    # Parse and format the timestamp
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    last_updated = dt.strftime("%Y-%m-%d %H:%M:%S ET")
                except:
                    pass
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MLB Impact System Dashboard</title>
            <meta http-equiv="refresh" content="30">
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
                    color: #ffffff;
                    min-height: 100vh;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 30px;
                    background: linear-gradient(45deg, #ff6b35, #f7931e);
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(255, 107, 53, 0.3);
                }}
                
                .header h1 {{
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }}
                
                .header p {{
                    font-size: 1.2em;
                    opacity: 0.9;
                }}
                
                .status-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                
                .status-card {{
                    background: rgba(42, 52, 65, 0.8);
                    border-radius: 12px;
                    padding: 25px;
                    border: 1px solid #3a4451;
                    backdrop-filter: blur(10px);
                    transition: transform 0.3s ease;
                }}
                
                .status-card:hover {{
                    transform: translateY(-5px);
                }}
                
                .status-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin: 15px 0;
                    padding: 10px 0;
                    border-bottom: 1px solid #404854;
                }}
                
                .status-item:last-child {{
                    border-bottom: none;
                }}
                
                .status-label {{
                    font-weight: 600;
                    color: #cccccc;
                }}
                
                .status-value {{
                    font-weight: 700;
                    color: #ffffff;
                }}
                
                .status-active {{ color: #28a745; }}
                .status-inactive {{ color: #dc3545; }}
                .status-warning {{ color: #ffc107; }}
                
                .plays-section {{
                    margin-top: 30px;
                }}
                
                .section-title {{
                    font-size: 1.8em;
                    margin-bottom: 25px;
                    color: #ff6b35;
                    text-align: center;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
                }}
                
                .play-item {{
                    background: linear-gradient(135deg, #2a3441 0%, #1e2631 100%);
                    padding: 25px;
                    margin: 15px 0;
                    border-radius: 12px;
                    border-left: 5px solid #ff6b35;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
                    transition: all 0.3s ease;
                }}
                
                .play-item:hover {{
                    transform: translateX(5px);
                    box-shadow: 0 6px 20px rgba(255, 107, 53, 0.2);
                }}
                
                .play-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                
                .play-rank {{
                    font-size: 1.5em;
                    font-weight: bold;
                    padding: 8px 15px;
                    border-radius: 25px;
                    color: black;
                    text-shadow: none;
                }}
                
                .rank-1 {{ background: linear-gradient(45deg, #FFD700, #FFA500); }}
                .rank-2 {{ background: linear-gradient(45deg, #C0C0C0, #A0A0A0); }}
                .rank-3 {{ background: linear-gradient(45deg, #CD7F32, #B8860B); }}
                
                .wpa-indicator {{
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 600;
                    text-transform: uppercase;
                }}
                
                .real-wpa {{
                    background: linear-gradient(45deg, #28a745, #20c997);
                    color: white;
                }}
                
                .statistical {{
                    background: linear-gradient(45deg, #6c757d, #545b62);
                    color: white;
                }}
                
                .play-details {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-top: 15px;
                }}
                
                .detail-item {{
                    background: rgba(15, 20, 25, 0.5);
                    padding: 10px 15px;
                    border-radius: 8px;
                    border: 1px solid #404854;
                }}
                
                .detail-label {{
                    font-size: 0.85em;
                    color: #888888;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .detail-value {{
                    font-size: 1.1em;
                    font-weight: 600;
                    color: #ffffff;
                    margin-top: 5px;
                }}
                
                .no-plays {{
                    text-align: center;
                    padding: 60px 20px;
                    background: rgba(42, 52, 65, 0.3);
                    border-radius: 12px;
                    border: 2px dashed #404854;
                }}
                
                .no-plays-icon {{
                    font-size: 4em;
                    margin-bottom: 20px;
                    opacity: 0.5;
                }}
                
                .footer {{
                    margin-top: 50px;
                    padding: 30px;
                    background: rgba(15, 20, 25, 0.8);
                    border-radius: 12px;
                    text-align: center;
                    border: 1px solid #2a3441;
                }}
                
                .footer-info {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                
                .footer-item {{
                    padding: 15px;
                    background: rgba(42, 52, 65, 0.5);
                    border-radius: 8px;
                }}
                
                .refresh-indicator {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(255, 107, 53, 0.9);
                    color: white;
                    padding: 10px 15px;
                    border-radius: 25px;
                    font-size: 0.9em;
                    font-weight: 600;
                    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                }}
                
                @media (max-width: 768px) {{
                    .header h1 {{ font-size: 2em; }}
                    .status-grid {{ grid-template-columns: 1fr; }}
                    .play-details {{ grid-template-columns: 1fr; }}
                    .footer-info {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="refresh-indicator">🔄 Auto-refresh: 30s</div>
            
            <div class="container">
                <div class="header">
                    <h1>🚨 MLB Impact System Dashboard 🚨</h1>
                    <p>Real-time tracking of the biggest moments in baseball</p>
                </div>
                
                <div class="status-grid">
                    <div class="status-card">
                        <h3>🖥️ System Status</h3>
                        <div class="status-item">
                            <span class="status-label">System:</span>
                            <span class="status-value {'status-active' if status['system_running'] else 'status-inactive'}">
                                {'🟢 Active' if status['system_running'] else '🔴 Inactive'}
                            </span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Live Tracker:</span>
                            <span class="status-value {'status-active' if status['live_tracker_active'] else 'status-inactive'}">
                                {'🟢 Running' if status['live_tracker_active'] else '🔴 Stopped'}
                            </span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Current Time:</span>
                            <span class="status-value">{status['current_time'][:19]} ET</span>
                        </div>
                    </div>
                    
                    <div class="status-card">
                        <h3>📊 Data Status</h3>
                        <div class="status-item">
                            <span class="status-label">Last Updated:</span>
                            <span class="status-value">{last_updated}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Top Plays Today:</span>
                            <span class="status-value {'status-active' if status['top_plays_count'] > 0 else 'status-warning'}">
                                {status['top_plays_count']}/3
                            </span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Monitoring:</span>
                            <span class="status-value status-active">Every 2 minutes</span>
                        </div>
                    </div>
                    
                    <div class="status-card">
                        <h3>🐦 Tweet Status</h3>
                        <div class="status-item">
                            <span class="status-label">Next Tweet:</span>
                            <span class="status-value">{status['next_tweet'] or 'Not scheduled'}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Tweet Content:</span>
                            <span class="status-value">Previous Day's Top 3</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Schedule:</span>
                            <span class="status-value">Daily at 12:00 PM ET</span>
                        </div>
                    </div>
                </div>
                
                <div class="plays-section">
                    <h2 class="section-title">🏆 Current Top Impact Plays (Today)</h2>
        """
        
        if status['top_plays']:
            for i, play in enumerate(status['top_plays']):
                rank_class = f"rank-{i+1}"
                wpa_class = 'real-wpa' if play['has_real_wpa'] else 'statistical'
                wpa_text = '🎯 MLB WPA' if play['has_real_wpa'] else '📊 Statistical'
                
                html += f"""
                <div class="play-item">
                    <div class="play-header">
                        <div class="play-rank {rank_class}">#{play['rank']}</div>
                        <div class="wpa-indicator {wpa_class}">{wpa_text}</div>
                    </div>
                    
                    <h3 style="margin-bottom: 15px; color: #ff6b35;">{play['event']}</h3>
                    
                    <div class="play-details">
                        <div class="detail-item">
                            <div class="detail-label">Impact</div>
                            <div class="detail-value" style="color: #00ff88;">{play['impact']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Teams</div>
                            <div class="detail-value">{play['teams']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Inning</div>
                            <div class="detail-value">{play['inning']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Tracked</div>
                            <div class="detail-value">{play['timestamp'][:16]}</div>
                        </div>
                    </div>
                </div>
                """
        else:
            html += """
            <div class="no-plays">
                <div class="no-plays-icon">⚾</div>
                <h3>No High-Impact Plays Found Yet Today</h3>
                <p>System is actively monitoring all live MLB games...<br>
                Check back soon for the biggest moments!</p>
            </div>
            """
        
        html += f"""
                </div>
                
                <div class="footer">
                    <div class="footer-info">
                        <div class="footer-item">
                            <strong>🔄 Auto-Refresh</strong><br>
                            Page refreshes every 30 seconds
                        </div>
                        <div class="footer-item">
                            <strong>📊 Live Monitoring</strong><br>
                            All MLB games checked every 2 minutes
                        </div>
                        <div class="footer-item">
                            <strong>🐦 Daily Tweets</strong><br>
                            Sent at 12:00 PM ET with previous day's top 3
                        </div>
                        <div class="footer-item">
                            <strong>🎯 Data Sources</strong><br>
                            Real MLB WPA + Statistical fallback
                        </div>
                    </div>
                    
                    <p style="margin-top: 20px; color: #888888;">
                        MLB Impact System • Deployed on Render • 
                        <a href="/test-tweet" style="color: #ff6b35;">Test Tweet</a> • 
                        <a href="/current-plays" style="color: #ff6b35;">API</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return f"""
        <html>
        <body style="font-family: Arial; background: #1a1a1a; color: white; padding: 20px;">
            <h1>❌ Dashboard Error</h1>
            <p>Error loading dashboard: {str(e)}</p>
            <p><a href="/" style="color: #ff6b35;">Try Again</a></p>
        </body>
        </html>
        """, 500

@app.route('/test-tweet')
def test_tweet():
    """Test endpoint to manually trigger daily tweet"""
    try:
        from impact_plays_tracker import send_daily_impact_tweet
        send_daily_impact_tweet()
        return "✅ Test tweet sent successfully!"
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return f"❌ Error: {str(e)}", 500

@app.route('/current-plays')
def current_plays():
    """API endpoint to get current top plays as JSON"""
    try:
        status = mlb_system.get_current_status()
        return {
            'success': True,
            'plays_count': status['top_plays_count'],
            'plays': status['top_plays'],
            'last_updated': status['current_time']
        }
    except Exception as e:
        logger.error(f"Error in current plays endpoint: {e}")
        return {'success': False, 'error': str(e)}, 500

def main():
    """Main function to start the complete system"""
    logger.info("🚀 Initializing MLB Impact System...")
    
    try:
        # Start the system
        mlb_system.start_system()
        
        # Run Flask app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down system...")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
    finally:
        mlb_system.stop_system()

if __name__ == "__main__":
    main() 