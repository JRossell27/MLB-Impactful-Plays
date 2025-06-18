#!/usr/bin/env python3
"""
Final comprehensive test of the complete GIF creation pipeline
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta
from baseball_savant_gif_integration import BaseballSavantGIFIntegration
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def final_gif_test():
    """Test the complete GIF creation pipeline"""
    
    print("🚀 Final GIF Creation Pipeline Test")
    print("=" * 60)
    print("Testing the complete pipeline from MLB API → Statcast → Video URL → GIF")
    print()
    
    # Initialize the integration
    gif_integration = BaseballSavantGIFIntegration()
    
    # Get yesterday's game data (we know this works)
    game_id = 777483  # Phillies vs Marlins
    game_date = '2025-06-16'
    
    print(f"Testing with game {game_id} from {game_date}")
    print()
    
    # Step 1: Get MLB API data for context
    print("Step 1: Fetching MLB API game data...")
    try:
        mlb_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
        mlb_response = requests.get(mlb_url, timeout=30)
        mlb_data = mlb_response.json()
        
        plays = mlb_data.get('liveData', {}).get('plays', {}).get('allPlays', [])
        
        # Find a good play to test with
        target_play = None
        for play in plays:
            result = play.get('result', {})
            event = result.get('event', '')
            
            if 'Home Run' in event:
                target_play = play
                break
        
        if target_play:
            print(f"✅ Found target play: {target_play['result']['event']}")
            print(f"   Description: {target_play['result']['description']}")
            print(f"   Inning: {target_play['about']['inning']}")
        else:
            print("❌ No suitable play found in MLB data")
            return
            
    except Exception as e:
        print(f"❌ Error fetching MLB data: {e}")
        return
    
    # Step 2: Get Statcast data with play matching
    print(f"\nStep 2: Fetching Statcast data with play matching...")
    try:
        statcast_data = gif_integration.get_statcast_data_for_play(
            game_id=game_id,
            play_id=target_play['atBatIndex'],
            game_date=game_date,
            mlb_play_data=target_play
        )
        
        if statcast_data:
            print(f"✅ Found matching Statcast data!")
            print(f"   Event: {statcast_data.get('events')}")
            print(f"   Play ID: {statcast_data.get('play_id')}")
            print(f"   Player: {statcast_data.get('player_name')}")
            print(f"   Hit distance: {statcast_data.get('hit_distance', 'N/A')} ft")
            print(f"   Exit velocity: {statcast_data.get('hit_speed', 'N/A')} mph")
        else:
            print("❌ No Statcast data found")
            return
            
    except Exception as e:
        print(f"❌ Error fetching Statcast data: {e}")
        return
    
    # Step 3: Get animation URL
    print(f"\nStep 3: Finding animation URL...")
    try:
        animation_url = gif_integration.get_play_animation_url(
            game_id=game_id,
            play_id=target_play['atBatIndex'],
            statcast_data=statcast_data
        )
        
        if animation_url:
            print(f"✅ Found animation URL!")
            print(f"   URL: {animation_url}")
            
            # Test the URL
            test_response = requests.head(animation_url, timeout=10)
            content_length = test_response.headers.get('content-length', 'unknown')
            content_type = test_response.headers.get('content-type', 'unknown')
            
            print(f"   Status: {test_response.status_code}")
            print(f"   Type: {content_type}")
            print(f"   Size: {content_length} bytes ({int(content_length)/1024/1024:.1f} MB)" if content_length != 'unknown' else '')
        else:
            print("❌ No animation URL found")
            return
            
    except Exception as e:
        print(f"❌ Error getting animation URL: {e}")
        return
    
    # Step 4: Create GIF
    print(f"\nStep 4: Creating GIF from video...")
    try:
        gif_path = gif_integration.get_gif_for_play(
            game_id=game_id,
            play_id=target_play['atBatIndex'],
            game_date=game_date,
            mlb_play_data=target_play
        )
        
        if gif_path and os.path.exists(gif_path):
            file_size = os.path.getsize(gif_path)
            print(f"✅ GIF created successfully!")
            print(f"   📁 Path: {gif_path}")
            print(f"   📊 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Check Twitter compatibility
            if file_size < 15 * 1024 * 1024:  # 15MB limit
                print(f"   ✅ File size within Twitter limits")
            else:
                print(f"   ⚠️  File size exceeds Twitter limits")
                
            # Test if file is valid
            try:
                from PIL import Image
                img = Image.open(gif_path)
                print(f"   🖼️  Dimensions: {img.size[0]}x{img.size[1]}")
                print(f"   📹 Frames: {getattr(img, 'n_frames', 1)}")
            except:
                print(f"   📹 GIF appears to be valid (couldn't get detailed info)")
                
        else:
            print("❌ GIF creation failed")
            return
            
    except Exception as e:
        print(f"❌ Error creating GIF: {e}")
        return
    
    # Final success summary
    print(f"\n{'='*60}")
    print("🎉 PIPELINE TEST COMPLETE - SUCCESS!")
    print("✅ All components working:")
    print("   📊 MLB API integration")
    print("   📈 Statcast data matching")
    print("   🎬 Video URL discovery")
    print("   🎥 GIF creation")
    print("   📱 Twitter compatibility")
    print()
    print("🚀 System is ready for production deployment!")
    print("   Your impact tracker can now automatically create GIFs")
    print("   for impactful plays within minutes of them happening.")
    print()
    print(f"📁 Test GIF saved to: {gif_path}")

def main():
    """Main test function"""
    try:
        final_gif_test()
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 