#!/usr/bin/env python3
"""
Render-deployable web app to test GIF integration
Shows results on a web page - safe for deployment
"""

import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from test_gif_with_real_games import GIFTestRunner

app = Flask(__name__)

class RenderGIFTestApp:
    def __init__(self):
        self.test_runner = GIFTestRunner()
        self.test_status = "Not Started"
        self.test_results = []
        self.last_test_time = None
        
    def run_tests_background(self):
        """Run GIF tests in background thread"""
        try:
            self.test_status = "Running Tests..."
            self.test_runner.run_comprehensive_test()
            self.test_results = self.test_runner.test_results
            self.test_status = "Tests Completed"
            self.last_test_time = datetime.now()
        except Exception as e:
            self.test_status = f"Test Failed: {str(e)}"

# Global test app instance
gif_app = RenderGIFTestApp()

@app.route('/')
def dashboard():
    """Main dashboard showing GIF test results"""
    
    # Count successful tests
    successful_gifs = sum(1 for r in gif_app.test_results if r.get('gif_created', False))
    total_tests = len(gif_app.test_results)
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MLB GIF Integration Test - Render Deployment</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #1f2937; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .status-card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .success { color: #10b981; }
            .error { color: #ef4444; }
            .warning { color: #f59e0b; }
            .test-result { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 15px; margin: 10px 0; }
            .btn { background: #3b82f6; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #2563eb; }
            .timestamp { color: #6b7280; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎾 MLB GIF Integration Test</h1>
                <p>Baseball Savant GIF Testing on Render - Live Deployment</p>
            </div>
            
            <div class="status-card">
                <h2>Test Status</h2>
                <p><strong>Status:</strong> <span class="{{ 'success' if 'Completed' in test_status else 'warning' }}">{{ test_status }}</span></p>
                <p><strong>Total Tests:</strong> {{ total_tests }}</p>
                <p><strong>Successful GIFs:</strong> {{ successful_gifs }}</p>
                {% if last_test_time %}
                <p><strong>Last Test:</strong> <span class="timestamp">{{ last_test_time.strftime('%Y-%m-%d %H:%M:%S UTC') }}</span></p>
                {% endif %}
                
                <a href="/run_test" class="btn">Run New Test</a>
                <a href="/api/results" class="btn">View JSON Results</a>
            </div>
            
            {% if test_results %}
            <div class="status-card">
                <h2>Test Results</h2>
                {% for result in test_results %}
                <div class="test-result">
                    <h3>Game {{ result.game_id }} - Play {{ result.play_id }}</h3>
                    <p><strong>Event:</strong> {{ result.event }}</p>
                    <p><strong>Description:</strong> {{ result.description }}</p>
                    <p><strong>Statcast Data:</strong> 
                        <span class="{{ 'success' if result.statcast_found else 'error' }}">
                            {{ '✅ Found' if result.statcast_found else '❌ Not Found' }}
                        </span>
                    </p>
                    <p><strong>GIF Created:</strong> 
                        <span class="{{ 'success' if result.gif_created else 'error' }}">
                            {{ '✅ Success' if result.gif_created else '❌ Failed' }}
                        </span>
                    </p>
                    {% if result.gif_path %}
                    <p><strong>GIF Path:</strong> {{ result.gif_path }}</p>
                    {% endif %}
                    {% if result.error %}
                    <p><strong>Error:</strong> <span class="error">{{ result.error }}</span></p>
                    {% endif %}
                    <p class="timestamp">{{ result.timestamp }}</p>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="status-card">
                <h2>How It Works</h2>
                <ul>
                    <li>🔍 Fetches today's MLB games from MLB API</li>
                    <li>🎮 Analyzes recent plays for GIF-worthy content</li>
                    <li>📊 Checks Baseball Savant for Statcast data</li>
                    <li>🎬 Downloads animations and converts to GIF</li>
                    <li>✅ Reports success/failure for each play</li>
                </ul>
                
                <h3>Next Steps (When Games Are Live):</h3>
                <ul>
                    <li>🔥 High-impact plays will generate GIFs automatically</li>
                    <li>🐦 Integration with Twitter posting (when enabled)</li>
                    <li>⚡ Real-time monitoring during games</li>
                </ul>
            </div>
            
            <div class="status-card">
                <h2>Technical Info</h2>
                <p><strong>Environment:</strong> Render Deployment</p>
                <p><strong>Time Zone:</strong> UTC</p>
                <p><strong>Python Version:</strong> 3.9</p>
                <p><strong>Dependencies:</strong> ffmpeg, requests, flask, ffmpeg-python</p>
                <p><strong>Repository:</strong> <a href="https://github.com/JRossell27/Impact-plays-Visual-TEST.git" target="_blank">GitHub</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_template, 
                                test_status=gif_app.test_status,
                                test_results=gif_app.test_results,
                                total_tests=total_tests,
                                successful_gifs=successful_gifs,
                                last_test_time=gif_app.last_test_time)

@app.route('/run_test')
def run_test():
    """Start a new test run"""
    if gif_app.test_status != "Running Tests...":
        # Start tests in background thread
        test_thread = threading.Thread(target=gif_app.run_tests_background)
        test_thread.daemon = True
        test_thread.start()
        return "Test started! <a href='/'>Return to dashboard</a>"
    else:
        return "Test already running! <a href='/'>Return to dashboard</a>"

@app.route('/api/results')
def api_results():
    """Return test results as JSON"""
    return jsonify({
        'status': gif_app.test_status,
        'total_tests': len(gif_app.test_results),
        'successful_gifs': sum(1 for r in gif_app.test_results if r.get('gif_created', False)),
        'last_test_time': gif_app.last_test_time.isoformat() if gif_app.last_test_time else None,
        'results': gif_app.test_results
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Auto-start first test
    print("🚀 Starting MLB GIF Integration Test on Render")
    print(f"🌐 Web interface will be available on port {port}")
    
    # Start initial test in background
    initial_test_thread = threading.Thread(target=gif_app.run_tests_background)
    initial_test_thread.daemon = True
    initial_test_thread.start()
    
    app.run(host='0.0.0.0', port=port, debug=False) 