#!/usr/bin/env python3
"""
Inspect what Baseball Savant URLs actually return
"""

import requests
import json

def inspect_savant_response():
    """Examine the actual response from Baseball Savant URLs"""
    
    print("🔍 Inspecting Baseball Savant Response Structure")
    print("=" * 60)
    
    # Test with one of the working URLs
    test_url = "https://baseballsavant.mlb.com/gf?game_pk=777483&at_bat_number=37"
    
    print(f"Testing URL: {test_url}")
    
    try:
        response = requests.get(test_url, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n📊 JSON Structure:")
                print(f"Type: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"Keys: {list(data.keys())}")
                    
                    # Look for animation/video related fields
                    for key, value in data.items():
                        print(f"\n🔑 {key}:")
                        if isinstance(value, (str, int, float, bool)):
                            print(f"   {value}")
                        elif isinstance(value, list):
                            print(f"   List with {len(value)} items")
                            if value and len(value) > 0:
                                print(f"   First item: {value[0]}")
                        elif isinstance(value, dict):
                            print(f"   Dict with keys: {list(value.keys())}")
                        else:
                            print(f"   Type: {type(value)}")
                
                elif isinstance(data, list):
                    print(f"List with {len(data)} items")
                    if data:
                        print(f"First item: {data[0]}")
                
                # Save full response for analysis
                with open('savant_response_sample.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n💾 Full response saved to: savant_response_sample.json")
                
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
                print(f"Response text (first 500 chars): {response.text[:500]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Also test the sporty-videos pattern
    print(f"\n{'='*60}")
    print("Testing sporty-videos pattern...")
    
    sporty_url = "https://baseballsavant.mlb.com/sporty-videos?playId=37"
    print(f"Testing URL: {sporty_url}")
    
    try:
        response = requests.get(sporty_url, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            print(f"Response length: {len(response.text)} characters")
            
            # Check if it's JSON or HTML
            if 'application/json' in response.headers.get('content-type', ''):
                try:
                    data = response.json()
                    print("✅ Got JSON response")
                    print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                except:
                    print("❌ JSON parse failed")
            elif 'text/html' in response.headers.get('content-type', ''):
                print("📄 Got HTML response")
                # Look for video-related content
                if 'video' in response.text.lower():
                    print("🎬 HTML contains video references!")
                    # Extract video URLs
                    import re
                    video_urls = re.findall(r'https?://[^\s"\']*\.mp4[^\s"\']*', response.text)
                    if video_urls:
                        print(f"Found video URLs: {video_urls}")
                else:
                    print("📄 No video references found in HTML")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_savant_response() 