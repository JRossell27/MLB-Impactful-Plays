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
        
        logger.info("✅ MLB Impact System fully operational!")
    
    def stop_system(self):
        """Stop the system"""
        logger.info("🛑 Stopping MLB Impact System...")
        self.is_running = False
        
        if hasattr(self, 'enhanced_tracker') and self.enhanced_tracker:
            self.enhanced_tracker.stop_monitoring()
        elif hasattr(self, 'basic_tracker') and self.basic_tracker:
            self.basic_tracker.stop_monitoring()
    
    def get_current_status(self):
        """Get current system status"""
        status = {
            'system_running': self.is_running,
            'enhanced_tracker_active': hasattr(self, 'enhanced_tracker') and self.enhanced_tracker is not None,
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

# Global system instance
mlb_system = MLBImpactSystem()

@app.route('/')
def home():
    """System status dashboard"""
    try:
        status = mlb_system.get_current_status()
        
        # If enhanced tracker is available, redirect to enhanced dashboard
        if hasattr(mlb_system, 'enhanced_tracker') and mlb_system.enhanced_tracker:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>MLB Enhanced Impact System</title>
                <meta http-equiv="refresh" content="2;url=/enhanced">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; 
                        text-align: center;
                        padding: 50px;
                    }
                    .loading { font-size: 24px; margin-bottom: 20px; }
                    .info { font-size: 16px; opacity: 0.8; }
                </style>
            </head>
            <body>
                <div class="loading">🎬 Loading Enhanced MLB Impact Tracker...</div>
                <div class="info">Redirecting to enhanced dashboard with GIF integration...</div>
                <div class="info">If not redirected, <a href="/enhanced" style="color: #ff6b35;">click here</a></div>
            </body>
            </html>
            """
        
        # Basic status page
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MLB Impact System</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background: #0f1419; 
                    color: white; 
                    padding: 40px;
                }}
                .header {{ color: #ff6b35; margin-bottom: 30px; }}
                .status {{ background: #21262d; padding: 20px; border-radius: 8px; }}
                .metric {{ margin: 10px 0; }}
                .active {{ color: #28a745; }}
                .inactive {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <h1 class="header">🎯 MLB Impact System</h1>
            <div class="status">
                <div class="metric"><strong>Status:</strong> 
                    <span class="{'active' if status['system_running'] else 'inactive'}">
                        {'🟢 RUNNING' if status['system_running'] else '🔴 STOPPED'}
                    </span>
                </div>
                <div class="metric"><strong>Type:</strong> {status.get('tracker_type', 'Unknown')}</div>
                <div class="metric"><strong>Time:</strong> {status.get('current_time', 'Unknown')}</div>
                {'<div class="metric"><strong>Queue Size:</strong> ' + str(status.get('queue_size', 0)) + '</div>' if 'queue_size' in status else ''}
                {'<div class="metric"><strong>Tweets Today:</strong> ' + str(status.get('tweets_posted_today', 0)) + '</div>' if 'tweets_posted_today' in status else ''}
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