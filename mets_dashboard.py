#!/usr/bin/env python3
"""
Mets Home Run Tracker Dashboard
Web interface for monitoring and controlling the Mets HR tracking system
"""

import os
import json
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from mets_homerun_tracker import MetsHomeRunTracker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global tracker instance
tracker = None
tracker_thread = None

def start_tracker_thread():
    """Start the tracker in a separate thread"""
    global tracker, tracker_thread
    
    if tracker is None:
        tracker = MetsHomeRunTracker()
    
    if tracker_thread is None or not tracker_thread.is_alive():
        tracker_thread = threading.Thread(target=tracker.monitor_games, daemon=True)
        tracker_thread.start()
        logger.info("🚀 Started Mets HR tracker thread")

def stop_tracker():
    """Stop the tracker"""
    global tracker
    if tracker:
        tracker.stop_monitoring()

def keep_alive_ping():
    """Send keep-alive ping to prevent deployment sleep"""
    try:
        site_url = os.getenv('SITE_URL', 'http://localhost:5000')
        if site_url != 'http://localhost:5000':  # Only ping if deployed
            requests.get(f"{site_url}/health", timeout=10)
            logger.info("💓 Keep-alive ping sent")
    except Exception as e:
        logger.warning(f"Keep-alive ping failed: {e}")

# HTML Template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠⚾ Mets Home Run Tracker</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #ff6600, #004488);
            color: white;
            min-height: 100vh;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 15px;
        }
        .logo {
            font-size: 4em;
            margin-bottom: 10px;
        }
        .title {
            font-size: 2.5em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .subtitle {
            font-size: 1.2em;
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .status-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            backdrop-filter: blur(10px);
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .status-item {
            background: rgba(255,255,255,0.15);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .status-value {
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .status-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.3);
            color: white;
            padding: 12px 24px;
            margin: 0 10px;
            border-radius: 25px;
            font-size: 1.1em;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .btn.start { border-color: #4CAF50; }
        .btn.stop { border-color: #f44336; }
        .btn.start:hover { background: rgba(76,175,80,0.3); }
        .btn.stop:hover { background: rgba(244,67,54,0.3); }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background-color: #4CAF50; }
        .status-stopped { background-color: #f44336; }
        .status-processing { background-color: #FF9800; }
        .recent-activity {
            margin-top: 30px;
        }
        .activity-item {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #ff6600;
        }
        .activity-time {
            font-size: 0.9em;
            opacity: 0.7;
            margin-bottom: 5px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            opacity: 0.7;
            font-size: 0.9em;
        }
        .auto-refresh {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 10px;
            font-size: 0.9em;
        }
        .emoji { font-size: 1.2em; }
        @media (max-width: 768px) {
            .title { font-size: 2em; }
            .logo { font-size: 3em; }
            .status-grid { grid-template-columns: 1fr; }
        }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function(){
            window.location.reload();
        }, 30000);
        
        // Keep-alive ping every 10 minutes
        setInterval(function() {
            fetch('/health').catch(() => {});
        }, 600000);
    </script>
</head>
<body>
    <div class="auto-refresh">
        🔄 Auto-refresh: 30s
    </div>
    
    <div class="header">
        <div class="logo">🏠⚾</div>
        <h1 class="title">Mets Home Run Tracker</h1>
        <p class="subtitle">Live monitoring for every single New York Mets home run</p>
    </div>

    <div class="status-panel">
        <h2>
            <span class="status-indicator {{ 'status-running' if status.monitoring else 'status-stopped' }}"></span>
            System Status: {{ 'MONITORING' if status.monitoring else 'STOPPED' }}
        </h2>
        
        <div class="status-grid">
            <div class="status-item">
                <div class="status-value">{{ status.stats.homeruns_posted_today }}</div>
                <div class="status-label">🏠 HRs Posted Today</div>
            </div>
            <div class="status-item">
                <div class="status-value">{{ status.queue_size }}</div>
                <div class="status-label">⏳ Queue Size</div>
            </div>
            <div class="status-item">
                <div class="status-value">{{ status.stats.gifs_created_today }}</div>
                <div class="status-label">🎬 GIFs Created</div>
            </div>
            <div class="status-item">
                <div class="status-value">{{ status.uptime or 'Not Started' }}</div>
                <div class="status-label">⏱️ Uptime</div>
            </div>
        </div>
        
        {% if status.last_check %}
        <p style="text-align: center; margin-top: 15px; opacity: 0.8;">
            Last check: {{ status.last_check[:19].replace('T', ' ') }}
        </p>
        {% endif %}
    </div>

    <div class="controls">
        <a href="/start" class="btn start">🚀 Start Monitoring</a>
        <a href="/stop" class="btn stop">🛑 Stop Monitoring</a>
        <a href="/test" class="btn">🧪 Test System</a>
    </div>

    <div class="status-panel recent-activity">
        <h3>📊 System Information</h3>
        <div class="activity-item">
            <div class="activity-time">Monitoring Focus</div>
            <div>🎯 <strong>New York Mets Home Runs Only</strong></div>
            <div style="margin-top: 5px; font-size: 0.9em; opacity: 0.8;">
                No WPA filtering - captures every single Mets homer in real time
            </div>
        </div>
        
        <div class="activity-item">
            <div class="activity-time">Check Frequency</div>
            <div>⏰ <strong>Every 2 minutes</strong></div>
            <div style="margin-top: 5px; font-size: 0.9em; opacity: 0.8;">
                Constant monitoring during live and recently finished games
            </div>
        </div>
        
        <div class="activity-item">
            <div class="activity-time">GIF Processing</div>
            <div>🎬 <strong>Baseball Savant Integration</strong></div>
            <div style="margin-top: 5px; font-size: 0.9em; opacity: 0.8;">
                Automatic GIF creation and Discord posting for every HR
            </div>
        </div>
        
        {% if status.queue_size > 0 %}
        <div class="activity-item">
            <div class="activity-time">Current Queue</div>
            <div>🏠 <strong>{{ status.queue_size }} home runs</strong> being processed</div>
        </div>
        {% endif %}
    </div>

    <div class="footer">
        <p>🏟️ Let's Go Mets! #LGM</p>
        <p>Built with ❤️ for Mets fans everywhere</p>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard"""
    global tracker
    
    # Get status
    if tracker:
        status = tracker.get_status()
    else:
        status = {
            'monitoring': False,
            'processing_gifs': False,
            'uptime': None,
            'last_check': None,
            'queue_size': 0,
            'processed_plays': 0,
            'stats': {
                'homeruns_posted_today': 0,
                'gifs_created_today': 0,
                'homeruns_queued_today': 0
            }
        }
    
    return render_template_string(DASHBOARD_TEMPLATE, status=status)

@app.route('/start')
def start_monitoring():
    """Start the monitoring system"""
    try:
        start_tracker_thread()
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error starting tracker: {e}")
        return f"Error starting tracker: {e}", 500

@app.route('/stop')
def stop_monitoring():
    """Stop the monitoring system"""
    try:
        stop_tracker()
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error stopping tracker: {e}")
        return f"Error stopping tracker: {e}", 500

@app.route('/test')
def test_system():
    """Test the system without starting monitoring"""
    global tracker
    try:
        if tracker is None:
            tracker = MetsHomeRunTracker()
        
        # Get current status
        games = tracker.get_live_mets_games()
        status = tracker.get_status()
        
        test_result = {
            'status': 'success',
            'message': f'System test completed successfully',
            'games_found': len(games),
            'system_status': status
        }
        
        return jsonify(test_result)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Test failed: {e}'
        }), 500

@app.route('/api/status')
def api_status():
    """API endpoint for status"""
    global tracker
    if tracker:
        return jsonify(tracker.get_status())
    else:
        return jsonify({
            'monitoring': False,
            'error': 'Tracker not initialized'
        })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'mets-homerun-tracker'
    })

@app.route('/ping')
def ping():
    """Keep-alive ping endpoint"""
    keep_alive_ping()
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat()
    })

def main():
    """Main function"""
    logger.info("🚀 Starting Mets Home Run Tracker Dashboard...")
    
    # Determine if we should auto-start monitoring
    auto_start = os.getenv('AUTO_START_MONITORING', 'true').lower() == 'true'
    
    if auto_start:
        logger.info("🏃 Auto-starting monitoring...")
        start_tracker_thread()
    
    # Start Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main() 