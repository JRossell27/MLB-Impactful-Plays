#!/usr/bin/env python3
"""
Get play UUID from Baseball Savant gf endpoint
"""

import requests
import json

def get_play_uuid():
    """Get the play UUID from Baseball Savant"""
    
    print("🔍 Getting Play UUID from Baseball Savant")
    print("=" * 60)
    
    game_id = 777483
    
    # Get the game data from Baseball Savant /gf endpoint
    gf_url = f"https://baseballsavant.mlb.com/gf?game_pk={game_id}&at_bat_number=1"
    
    print(f"Fetching: {gf_url}")
    
    try:
        response = requests.get(gf_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Look at home team plays (Phillies)
            home_plays = data.get('team_home', [])
            print(f"Found {len(home_plays)} home team plays")
            
            # Find home runs
            home_runs = []
            for play in home_plays:
                event = play.get('events', '')
                if 'Home Run' in event:
                    home_runs.append(play)
            
            print(f"Found {len(home_runs)} home runs:")
            for i, hr in enumerate(home_runs):
                print(f"\n  Home Run {i+1}:")
                print(f"    Event: {hr.get('events')}")
                print(f"    Player: {hr.get('batter_name')}")
                print(f"    Inning: {hr.get('inning')}")
                print(f"    Play ID: {hr.get('play_id')}")
                print(f"    At-bat: {hr.get('ab_number')}")
                print(f"    Description: {hr.get('des', '')[:100]}...")
                
                # Check if this is Trea Turner's home run
                if 'Turner' in hr.get('batter_name', '') and hr.get('inning') == 1:
                    print(f"    ✅ This is Trea Turner's home run!")
                    play_uuid = hr.get('play_id')
                    
                    if play_uuid:
                        print(f"    🎯 Play UUID: {play_uuid}")
                        
                        # Test the video URL
                        video_url = f"https://baseballsavant.mlb.com/sporty-videos?playId={play_uuid}"
                        print(f"    🎬 Testing video URL: {video_url}")
                        
                        try:
                            video_response = requests.get(video_url, timeout=10)
                            if video_response.status_code == 200:
                                print(f"    ✅ Video page accessible!")
                                
                                # Look for the actual video URL
                                import re
                                video_pattern = r'https://sporty-clips\.mlb\.com/[^"\s]*\.mp4'
                                matches = re.findall(video_pattern, video_response.text)
                                
                                if matches:
                                    actual_video_url = matches[0]
                                    print(f"    🎥 Found video URL: {actual_video_url}")
                                    
                                    # Test the actual video
                                    video_test = requests.head(actual_video_url, timeout=10)
                                    print(f"    📊 Video status: {video_test.status_code}")
                                    print(f"    📊 Video type: {video_test.headers.get('content-type')}")
                                    print(f"    📊 Video size: {video_test.headers.get('content-length')} bytes")
                                    
                                    if video_test.status_code == 200:
                                        print(f"    🎉 COMPLETE SUCCESS! Video URL works!")
                                        return actual_video_url
                                else:
                                    print(f"    ❌ No video URL found in HTML")
                            else:
                                print(f"    ❌ Video page not accessible: {video_response.status_code}")
                        except Exception as e:
                            print(f"    ❌ Error testing video: {e}")
                    else:
                        print(f"    ❌ No play_id in data")
        
        else:
            print(f"❌ Failed to get data: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

if __name__ == "__main__":
    get_play_uuid() 