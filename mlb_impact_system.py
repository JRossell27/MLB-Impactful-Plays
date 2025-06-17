#!/usr/bin/env python3
"""
Complete MLB Impact System - Enhanced with GIF Integration
"""

import os
import time
import logging
import threading
from datetime import datetime
import pytz
from flask import Flask
import json
import requests

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
        self.enhanced_tracker = None
        self.is_running = False
        self.tracker_thread = None
        self.ping_thread = None
        self.keep_alive = False
    
    def start_enhanced_tracking(self):
        """Start the enhanced tracking with GIF integration"""
        try:
            from enhanced_impact_tracker import EnhancedImpactTracker
            
            self.enhanced_tracker = EnhancedImpactTracker()
            
            def run_tracker():
                logger.info("🚀 Starting enhanced impact tracking with GIF integration...")
                self.enhanced_tracker.monitor_games()
            
            self.tracker_thread = threading.Thread(target=run_tracker, daemon=True)
            self.tracker_thread.start()
            logger.info("✅ Enhanced tracking started in background")
            
        except ImportError as e:
            logger.error(f"Failed to import enhanced tracker: {e}")
            # Fallback to basic tracker if enhanced isn't available
            self.start_basic_tracking()
    
    def start_basic_tracking(self):
        """Fallback to basic real-time tracking"""
        try:
            from realtime_impact_tracker import RealTimeImpactTracker
            
            self.basic_tracker = RealTimeImpactTracker()
            
            def run_basic_tracker():
                logger.info("🚀 Starting basic real-time tracking...")
                self.basic_tracker.monitor_games()
            
            self.tracker_thread = threading.Thread(target=run_basic_tracker, daemon=True)
            self.tracker_thread.start()
            logger.info("✅ Basic tracking started in background")
            
        except ImportError as e:
            logger.error(f"Failed to import any tracker: {e}")
    
    def start_system(self):
        """Start the complete system"""
        logger.info("🚨 Starting MLB Impact System...")
        self.is_running = True
        
        # Start enhanced tracking (with fallback)
        self.start_enhanced_tracking()
        
        # Start keep-alive ping service for Render
        self.start_keep_alive_ping()
        
        logger.info("✅ MLB Impact System fully operational!")
    
    def stop_system(self):
        """Stop the system"""
        logger.info("🛑 Stopping MLB Impact System...")
        self.is_running = False
        self.keep_alive = False
        
        if hasattr(self, 'enhanced_tracker') and self.enhanced_tracker:
            self.enhanced_tracker.stop_monitoring()
        elif hasattr(self, 'basic_tracker') and self.basic_tracker:
            self.basic_tracker.stop_monitoring()
        
        logger.info("🛑 All services stopped")
    
    def get_current_status(self):
        """Get current system status"""
        status = {
            'system_running': self.is_running,
            'enhanced_tracker_active': hasattr(self, 'enhanced_tracker') and self.enhanced_tracker is not None,
            'keep_alive_active': self.keep_alive,
            'current_time': datetime.now(eastern_tz).isoformat(),
            'tracker_type': 'Enhanced with GIF Integration' if hasattr(self, 'enhanced_tracker') else 'Basic Real-time',
            'last_updated': 'Unknown'
        }
        
        # Get status from enhanced tracker if available
        if hasattr(self, 'enhanced_tracker') and self.enhanced_tracker:
            try:
                enhanced_status = self.enhanced_tracker.get_status()
                status.update({
                    'monitoring': enhanced_status.get('monitoring', False),
                    'processing_gifs': enhanced_status.get('processing_gifs', False),
                    'twitter_connected': enhanced_status.get('twitter_connected', False),
                    'plays_queued_today': enhanced_status.get('plays_queued_today', 0),
                    'gifs_created_today': enhanced_status.get('gifs_created_today', 0),
                    'tweets_posted_today': enhanced_status.get('tweets_posted_today', 0),
                    'queue_size': enhanced_status.get('current_queue_size', 0),
                    'last_check_time': enhanced_status.get('last_check_time', 'Never')
                })
            except Exception as e:
                logger.error(f"Error getting enhanced tracker status: {e}")
        
        return status

    def start_keep_alive_ping(self):
        """Start the keep-alive ping to prevent Render spin-down"""
        def ping_self():
            logger.info("🏓 Starting keep-alive ping service...")
            
            # Try to detect the service URL from environment
            service_url = os.getenv('RENDER_EXTERNAL_URL')
            if not service_url:
                # Fallback - try to construct from common patterns
                service_name = os.getenv('RENDER_SERVICE_NAME', 'mlb-impact-system')
                service_url = f"https://{service_name}.onrender.com"
            
            logger.info(f"🌐 Keep-alive target: {service_url}")
            
            while self.keep_alive:
                try:
                    # Ping the health endpoint every 10 minutes
                    response = requests.get(f"{service_url}/health", timeout=30)
                    if response.status_code == 200:
                        logger.info(f"🏓 Keep-alive ping successful ({response.status_code})")
                    else:
                        logger.warning(f"🏓 Keep-alive ping returned {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"🏓 Keep-alive ping failed: {e}")
                except Exception as e:
                    logger.error(f"🏓 Keep-alive ping error: {e}")
                
                # Wait 10 minutes (600 seconds) before next ping
                # Use shorter intervals to check if we should stop
                for _ in range(120):  # 120 * 5 = 600 seconds = 10 minutes
                    if not self.keep_alive:
                        break
                    time.sleep(5)
        
        self.keep_alive = True
        self.ping_thread = threading.Thread(target=ping_self, daemon=True)
        self.ping_thread.start()
        logger.info("✅ Keep-alive ping service started")

# Global system instance
mlb_system = MLBImpactSystem()

@app.route('/')
def home():
    """System status dashboard"""
    try:
        status = mlb_system.get_current_status()
        
        # Check if we should show enhanced dashboard instead
        show_enhanced = (hasattr(mlb_system, 'enhanced_tracker') and 
                        mlb_system.enhanced_tracker and 
                        status.get('monitoring', False))
        
        if show_enhanced:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>MLB Enhanced Impact System</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; 
                        text-align: center;
                        padding: 50px;
                    }
                    .loading { font-size: 24px; margin-bottom: 20px; }
                    .info { font-size: 16px; opacity: 0.8; margin: 10px 0; }
                    .button { 
                        display: inline-block; 
                        background: #ff6b35; 
                        color: white; 
                        padding: 10px 20px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 10px;
                    }
                </style>
            </head>
            <body>
                <div class="loading">🎬 Enhanced MLB Impact Tracker Active!</div>
                <div class="info">✅ System is monitoring for high-impact plays</div>
                <div class="info">🎥 GIF integration ready</div>
                <div class="info">🐦 Twitter connected</div>
                
                <div style="margin-top: 30px;">
                    <a href="/enhanced" class="button">📊 View Enhanced Dashboard</a>
                    <a href="/debug/status" class="button">🔍 Debug Status</a>
                    <a href="/debug/twitter" class="button">🐦 Twitter Debug</a>
                </div>
            </body>
            </html>
            """
        
        # Show detailed status page if enhanced tracker not fully active
        monitoring_status = status.get('monitoring', False)
        processing_gifs = status.get('processing_gifs', False)
        twitter_connected = status.get('twitter_connected', False)
        keep_alive_active = status.get('keep_alive_active', False)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MLB Impact System</title>
            <meta http-equiv="refresh" content="15">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background: #0f1419; 
                    color: white; 
                    padding: 40px;
                }}
                .header {{ color: #ff6b35; margin-bottom: 30px; }}
                .status {{ background: #21262d; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .metric {{ margin: 15px 0; padding: 10px; background: #1a1a1a; border-radius: 5px; }}
                .active {{ color: #28a745; }}
                .inactive {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
                .buttons {{ margin-top: 20px; }}
                .button {{ 
                    display: inline-block; 
                    background: #ff6b35; 
                    color: white; 
                    padding: 8px 16px; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 5px;
                }}
            </style>
        </head>
        <body>
            <h1 class="header">🎯 MLB Impact System</h1>
            
            <div class="status">
                <h3>System Status</h3>
                <div class="metric">
                    <strong>Overall Status:</strong> 
                    <span class="{'active' if status['system_running'] else 'inactive'}">
                        {'🟢 SYSTEM RUNNING' if status['system_running'] else '🔴 SYSTEM STOPPED'}
                    </span>
                </div>
                
                <div class="metric">
                    <strong>Game Monitoring:</strong> 
                    <span class="{'active' if monitoring_status else 'inactive'}">
                        {'🟢 ACTIVE' if monitoring_status else '🔴 INACTIVE'}
                    </span>
                </div>
                
                <div class="metric">
                    <strong>GIF Processing:</strong> 
                    <span class="{'active' if processing_gifs else 'inactive'}">
                        {'🟢 RUNNING' if processing_gifs else '🔴 STOPPED'}
                    </span>
                </div>
                
                <div class="metric">
                    <strong>Twitter:</strong> 
                    <span class="{'active' if twitter_connected else 'inactive'}">
                        {'🟢 CONNECTED' if twitter_connected else '🔴 DISCONNECTED'}
                    </span>
                </div>
                
                <div class="metric">
                    <strong>Keep-Alive Service:</strong> 
                    <span class="{'active' if keep_alive_active else 'inactive'}">
                        {'🟢 RUNNING' if keep_alive_active else '🔴 STOPPED'}
                    </span>
                    <span style="font-size: 0.8em; opacity: 0.7;"> (Prevents Render spin-down)</span>
                </div>
                
                <div class="metric"><strong>Tracker Type:</strong> {status.get('tracker_type', 'Unknown')}</div>
                <div class="metric"><strong>Last Check:</strong> {status.get('last_check_time', 'Never')}</div>
                <div class="metric"><strong>System Time:</strong> {status.get('current_time', 'Unknown')}</div>
                
                {'<div class="metric"><strong>Queue Size:</strong> ' + str(status.get('queue_size', 0)) + ' plays</div>' if 'queue_size' in status else ''}
                {'<div class="metric"><strong>Today - Queued:</strong> ' + str(status.get('plays_queued_today', 0)) + ', GIFs: ' + str(status.get('gifs_created_today', 0)) + ', Tweets: ' + str(status.get('tweets_posted_today', 0)) + '</div>' if 'plays_queued_today' in status else ''}
            </div>
            
            <div class="buttons">
                <a href="/enhanced" class="button">📊 Enhanced Dashboard</a>
                <a href="/debug/status" class="button">🔍 Debug Status</a>
                <a href="/debug/twitter" class="button">🐦 Twitter Debug</a>
                <a href="/retry-twitter" class="button">🔄 Retry Twitter</a>
            </div>
            
            <div style="margin-top: 20px; font-size: 0.9em; opacity: 0.7;">
                Page auto-refreshes every 15 seconds
            </div>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        return f"<h1>System Error</h1><p>{str(e)}</p>"

@app.route('/enhanced')
def enhanced_dashboard():
    """Redirect to enhanced dashboard if available"""
    try:
        if hasattr(mlb_system, 'enhanced_tracker') and mlb_system.enhanced_tracker:
            # Import and serve enhanced dashboard
            from enhanced_dashboard import dashboard
            return dashboard()
        else:
            return "<h1>Enhanced Dashboard Not Available</h1><p>Enhanced tracker not loaded</p>"
    except Exception as e:
        return f"<h1>Enhanced Dashboard Error</h1><p>{str(e)}</p>"

@app.route('/debug/twitter')
def debug_twitter():
    """Debug Twitter credentials (shows presence, not values)"""
    import os
    
    # Check for both naming conventions
    consumer_key = os.getenv('TWITTER_CONSUMER_KEY') or os.getenv('TWITTER_API_KEY')
    consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET') or os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
    
    credentials = {
        'TWITTER_CONSUMER_KEY / TWITTER_API_KEY': bool(consumer_key),
        'TWITTER_CONSUMER_SECRET / TWITTER_API_SECRET': bool(consumer_secret),
        'TWITTER_ACCESS_TOKEN': bool(access_token),
        'TWITTER_ACCESS_TOKEN_SECRET': bool(access_token_secret),
        'TWITTER_BEARER_TOKEN (optional)': bool(bearer_token)
    }
    
    # Check individual variables for detailed view
    individual_vars = {
        'TWITTER_CONSUMER_KEY': bool(os.getenv('TWITTER_CONSUMER_KEY')),
        'TWITTER_API_KEY': bool(os.getenv('TWITTER_API_KEY')),
        'TWITTER_CONSUMER_SECRET': bool(os.getenv('TWITTER_CONSUMER_SECRET')),
        'TWITTER_API_SECRET': bool(os.getenv('TWITTER_API_SECRET')),
        'TWITTER_ACCESS_TOKEN': bool(os.getenv('TWITTER_ACCESS_TOKEN')),
        'TWITTER_ACCESS_TOKEN_SECRET': bool(os.getenv('TWITTER_ACCESS_TOKEN_SECRET')),
        'TWITTER_BEARER_TOKEN': bool(os.getenv('TWITTER_BEARER_TOKEN'))
    }
    
    # Check if required credentials are available
    required_present = consumer_key and consumer_secret and access_token and access_token_secret
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Twitter Credentials Debug</title>
        <style>
            body {{ font-family: Arial; background: #0f1419; color: white; padding: 20px; }}
            .credential {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
            .present {{ background: #28a745; }}
            .missing {{ background: #dc3545; }}
            .summary {{ margin-top: 20px; padding: 15px; border-radius: 5px; }}
            .section {{ margin: 20px 0; padding: 15px; background: #21262d; border-radius: 8px; }}
            .small {{ font-size: 0.9em; opacity: 0.8; }}
        </style>
    </head>
    <body>
        <h1>🐦 Twitter Credentials Status</h1>
        
        <div class="section">
            <h3>Required Credentials (with fallback naming):</h3>
            {''.join([f'<div class="credential {"present" if present else "missing"}">{"✅" if present else "❌"} {name}: {"Present" if present else "Missing"}</div>' for name, present in credentials.items()])}
        </div>
        
        <div class="summary {'present' if required_present else 'missing'}">
            <strong>Overall Status: {'✅ All required credentials present' if required_present else '❌ Some required credentials missing'}</strong>
        </div>
        
        <div class="section">
            <h3>Individual Environment Variables:</h3>
            <div class="small">Shows exactly which variables are set in your environment:</div>
            {''.join([f'<div class="credential {"present" if present else "missing"}">{"✅" if present else "❌"} {name}: {"Set" if present else "Not Set"}</div>' for name, present in individual_vars.items()])}
        </div>
        
        <div class="section small">
            <strong>Note:</strong> The system will use TWITTER_API_KEY if TWITTER_CONSUMER_KEY is not found, and TWITTER_API_SECRET if TWITTER_CONSUMER_SECRET is not found.
        </div>
        
        <p style="margin-top: 20px;">
            <a href="/" style="color: #ff6b35;">← Back to Dashboard</a> | 
            <a href="/retry-twitter" style="color: #ff6b35;">Retry Twitter Auth</a>
        </p>
    </body>
    </html>
    """
    
    return html

@app.route('/retry-twitter')
def retry_twitter():
    """Manually retry Twitter authentication"""
    try:
        if hasattr(mlb_system, 'enhanced_tracker') and mlb_system.enhanced_tracker:
            success = mlb_system.enhanced_tracker.retry_twitter_setup()
            if success:
                return "✅ Twitter authentication successful!"
            else:
                return "❌ Twitter authentication failed - check credentials and /debug/twitter"
        else:
            return "❌ Enhanced tracker not available"
    except Exception as e:
        return f"❌ Error during Twitter retry: {str(e)}"

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': str(datetime.now())}

@app.route('/start')
def start_system():
    """Start the system"""
    if not mlb_system.is_running:
        mlb_system.start_system()
        return "✅ System started!"
    else:
        return "ℹ️ System already running"

@app.route('/stop')
def stop_system():
    """Stop the system"""
    if mlb_system.is_running:
        mlb_system.stop_system()
        return "🛑 System stopped!"
    else:
        return "ℹ️ System not running"

@app.route('/debug/status')
def debug_status():
    """Debug system status in detail"""
    try:
        import os
        status = mlb_system.get_current_status()
        
        # Get additional debug info
        debug_info = {
            'mlb_system_is_running': mlb_system.is_running,
            'has_enhanced_tracker': hasattr(mlb_system, 'enhanced_tracker'),
            'enhanced_tracker_not_none': hasattr(mlb_system, 'enhanced_tracker') and mlb_system.enhanced_tracker is not None,
            'tracker_thread_alive': mlb_system.tracker_thread.is_alive() if mlb_system.tracker_thread else False,
            'keep_alive_active': mlb_system.keep_alive,
            'ping_thread_alive': mlb_system.ping_thread.is_alive() if mlb_system.ping_thread else False,
            'render_external_url': os.getenv('RENDER_EXTERNAL_URL', 'Not set'),
            'render_service_name': os.getenv('RENDER_SERVICE_NAME', 'Not set')
        }
        
        # Try to get enhanced tracker status directly
        enhanced_status = {}
        if hasattr(mlb_system, 'enhanced_tracker') and mlb_system.enhanced_tracker:
            try:
                enhanced_status = mlb_system.enhanced_tracker.get_status()
            except Exception as e:
                enhanced_status = {'error': str(e)}
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Status Debug</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body {{ font-family: Arial; background: #0f1419; color: white; padding: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; background: #21262d; border-radius: 8px; }}
                .value {{ color: #28a745; }}
                .error {{ color: #dc3545; }}
                pre {{ background: #1a1a1a; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>🔍 System Status Debug</h1>
            
            <div class="section">
                <h3>System Status:</h3>
                <pre>{json.dumps(status, indent=2, default=str)}</pre>
            </div>
            
            <div class="section">
                <h3>Debug Info:</h3>
                <pre>{json.dumps(debug_info, indent=2, default=str)}</pre>
            </div>
            
            <div class="section">
                <h3>Enhanced Tracker Status:</h3>
                <pre>{json.dumps(enhanced_status, indent=2, default=str)}</pre>
            </div>
            
            <p><a href="/" style="color: #ff6b35;">← Back to Dashboard</a></p>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"<h1>Debug Error</h1><pre>{str(e)}</pre>"

def main():
    """Main function to start the system"""
    logger.info("🚀 Initializing MLB Impact System...")
    
    try:
        # Start the system automatically
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