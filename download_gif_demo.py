#!/usr/bin/env python3
"""
Download and save a GIF demo - creates a GIF you can actually view
"""

import os
import requests
from datetime import datetime
from baseball_savant_gif_integration import BaseballSavantGIFIntegration
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_gif_demo():
    """Download a GIF to the current directory"""
    
    print("🎬 Baseball Savant GIF Download Demo")
    print("=" * 50)
    print("This will create a GIF of Trea Turner's home run that you can view!")
    print()
    
    # Initialize the integration
    gif_integration = BaseballSavantGIFIntegration()
    
    # Use the game data we know works
    game_id = 777483  # Phillies vs Marlins
    game_date = '2025-06-16'
    
    # Get MLB API data for the home run
    print("Step 1: Getting MLB game data...")
    try:
        mlb_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
        mlb_response = requests.get(mlb_url, timeout=30)
        mlb_data = mlb_response.json()
        
        plays = mlb_data.get('liveData', {}).get('plays', {}).get('allPlays', [])
        
        # Find Trea Turner's home run
        target_play = None
        for play in plays:
            result = play.get('result', {})
            event = result.get('event', '')
            batter = play.get('matchup', {}).get('batter', {}).get('fullName', '')
            
            if 'Home Run' in event and 'Turner' in batter:
                target_play = play
                break
        
        if not target_play:
            print("❌ Couldn't find Trea Turner's home run")
            return
            
        print(f"✅ Found: {target_play['result']['description']}")
        
    except Exception as e:
        print(f"❌ Error getting MLB data: {e}")
        return
    
    # Create the GIF in current directory
    print(f"\nStep 2: Creating GIF...")
    
    try:
        # Create a custom filename in the current directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        gif_filename = f"trea_turner_home_run_{timestamp}.gif"
        gif_path = os.path.join(os.getcwd(), gif_filename)
        
        print(f"Creating: {gif_filename}")
        
        # Get the GIF using our integration
        temp_gif_path = gif_integration.get_gif_for_play(
            game_id=game_id,
            play_id=target_play['atBatIndex'],
            game_date=game_date,
            mlb_play_data=target_play
        )
        
        if temp_gif_path and os.path.exists(temp_gif_path):
            # Copy from temp location to current directory
            import shutil
            shutil.copy2(temp_gif_path, gif_path)
            
            # Get file info
            file_size = os.path.getsize(gif_path)
            print(f"✅ GIF created successfully!")
            print(f"📁 Location: {gif_path}")
            print(f"📊 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Try to get GIF details
            try:
                from PIL import Image
                with Image.open(gif_path) as img:
                    print(f"🖼️  Dimensions: {img.size[0]}x{img.size[1]} pixels")
                    print(f"📹 Frames: {getattr(img, 'n_frames', 1)}")
                    print(f"⏱️  Duration: ~{getattr(img, 'n_frames', 1) / 15:.1f} seconds (approx)")
            except ImportError:
                print("📹 GIF created (install Pillow for detailed info)")
            except Exception:
                print("📹 GIF created successfully")
            
            print(f"\n🎉 SUCCESS!")
            print(f"You can now view the GIF at: {gif_filename}")
            print(f"It shows Trea Turner's home run from the Phillies vs Marlins game!")
            
            # Clean up temp file
            try:
                os.remove(temp_gif_path)
            except:
                pass
                
            return gif_path
            
        else:
            print("❌ Failed to create GIF")
            return None
            
    except Exception as e:
        print(f"❌ Error creating GIF: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function"""
    try:
        gif_path = download_gif_demo()
        
        if gif_path:
            print(f"\n" + "="*50)
            print("🎯 DEMO COMPLETE!")
            print(f"Your GIF is ready: {os.path.basename(gif_path)}")
            print("You can open it with any image viewer or web browser.")
            print("It shows the actual Baseball Savant animation of the play!")
        else:
            print(f"\n❌ Demo failed - no GIF created")
            
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 