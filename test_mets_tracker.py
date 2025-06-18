#!/usr/bin/env python3
"""
Test script for Mets Home Run Tracker
Verifies all components work correctly before deployment
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from mets_homerun_tracker import MetsHomeRunTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_functionality():
    """Test basic tracker functionality"""
    logger.info("🧪 Testing basic Mets HR Tracker functionality...")
    
    try:
        # Initialize tracker
        tracker = MetsHomeRunTracker()
        logger.info("✅ Tracker initialized successfully")
        
        # Test getting Mets games
        games = tracker.get_live_mets_games()
        logger.info(f"✅ Found {len(games)} Mets games")
        
        if games:
            # Test getting plays from first game
            game_id = games[0]['gamePk']
            plays = tracker.get_game_plays(game_id)
            logger.info(f"✅ Found {len(plays)} plays in game {game_id}")
            
            # Test home run detection
            mets_hrs = 0
            for play in plays:
                if tracker.is_mets_home_run(play):
                    mets_hrs += 1
                    logger.info(f"🏠 Found Mets HR: {play.get('batter')} - {play.get('description')}")
            
            logger.info(f"✅ Found {mets_hrs} Mets home runs in the game")
        
        # Test status
        status = tracker.get_status()
        logger.info(f"✅ Status: {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_gif_integration():
    """Test GIF integration capabilities"""
    logger.info("🎬 Testing GIF integration...")
    
    try:
        from baseball_savant_gif_integration import BaseballSavantGIFIntegration
        gif_integration = BaseballSavantGIFIntegration()
        logger.info("✅ GIF integration initialized")
        return True
    except Exception as e:
        logger.error(f"❌ GIF integration test failed: {e}")
        return False

def test_discord_integration():
    """Test Discord integration"""
    logger.info("📱 Testing Discord integration...")
    
    try:
        from discord_integration import discord_poster
        logger.info("✅ Discord integration imported")
        
        # Test environment variables (without actually posting)
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url:
            logger.info("✅ Discord webhook URL configured")
        else:
            logger.warning("⚠️ Discord webhook URL not configured")
            
        return True
    except Exception as e:
        logger.error(f"❌ Discord integration test failed: {e}")
        return False

def test_monitoring_cycle():
    """Test a single monitoring cycle"""
    logger.info("🔄 Testing monitoring cycle...")
    
    try:
        tracker = MetsHomeRunTracker()
        
        # Simulate one monitoring cycle
        games = tracker.get_live_mets_games()
        logger.info(f"Found {len(games)} Mets games to monitor")
        
        for game in games:
            game_id = game['gamePk']
            logger.info(f"Checking game {game_id}...")
            
            plays = tracker.get_game_plays(game_id)
            home_runs = [play for play in plays if tracker.is_mets_home_run(play)]
            
            logger.info(f"Found {len(home_runs)} Mets HRs in game {game_id}")
            
            # Test queuing (without actually processing)
            for hr in home_runs:
                logger.info(f"Would queue: {hr.get('batter')} HR")
        
        logger.info("✅ Monitoring cycle test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Monitoring cycle test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    logger.info("🚀 Starting Mets Home Run Tracker Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("GIF Integration", test_gif_integration),
        ("Discord Integration", test_discord_integration),
        ("Monitoring Cycle", test_monitoring_cycle)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📝 Running {test_name} test...")
        start_time = time.time()
        success = test_func()
        duration = time.time() - start_time
        
        results.append({
            'name': test_name,
            'success': success,
            'duration': duration
        })
        
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} - {test_name} ({duration:.2f}s)")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        logger.info(f"{status} {result['name']} ({result['duration']:.2f}s)")
    
    logger.info("-" * 50)
    logger.info(f"OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Mets HR Tracker is ready!")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1) 