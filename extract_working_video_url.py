#!/usr/bin/env python3
"""
Extract the actual video URL from working Baseball Savant pages
"""

import requests
import re
import json

def extract_working_video_url():
    """Extract video URL from a working Baseball Savant page"""
    
    print("🎬 Extracting Video URL from Working Page")
    print("=" * 60)
    
    # Use one of the working URLs that contains video content
    working_url = "https://baseballsavant.mlb.com/sporty-videos?playId=7373d94a-4dcf-312c-9a24-19a9aef5eeef"
    print(f"Analyzing: {working_url}")
    print("(This is Trea Turner's home run)")
    
    try:
        response = requests.get(working_url, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            print(f"✅ Got HTML content ({len(html_content)} characters)")
            
            # Look for more specific video patterns
            video_patterns = [
                r'"videoUrl":\s*"([^"]*)"',
                r'"url":\s*"([^"]*\.mp4[^"]*)"',
                r'"src":\s*"([^"]*\.mp4[^"]*)"',
                r'data-video[^=]*=\s*"([^"]*)"',
                r'https://[^"\s]*\.mp4[^"\s]*',
                r'https://[^"\s]*cuts\.diamond\.mlb\.com[^"\s]*',
                r'https://[^"\s]*mlb-cuts-diamond[^"\s]*',
                r'"playback_url":\s*"([^"]*)"',
                r'"video":\s*{[^}]*"url":\s*"([^"]*)"',
                r'sporty-videos/[^"\'>\s]*\.mp4',
                r'window\.__INITIAL_STATE__[^;]*',
                r'window\.videoData[^;]*',
            ]
            
            found_urls = set()
            
            for pattern in video_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if match and ('mp4' in match.lower() or 'video' in match.lower() or 'mlb' in match.lower()):
                        found_urls.add(match)
            
            print(f"\n🔍 Found {len(found_urls)} potential video URLs:")
            for i, url in enumerate(sorted(found_urls), 1):
                print(f"  {i}. {url}")
            
            # Look for JavaScript objects that might contain video data
            js_object_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.videoData\s*=\s*({.*?});',
                r'var\s+videoData\s*=\s*({.*?});',
                r'const\s+videoData\s*=\s*({.*?});',
                r'"video":\s*({[^}]*})',
                r'"playback":\s*({[^}]*})',
            ]
            
            print(f"\n📊 Looking for video data objects:")
            for pattern in js_object_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                for i, match in enumerate(matches):
                    print(f"  Object {i+1}: {match[:100]}...")
                    try:
                        # Try to parse as JSON
                        obj = json.loads(match)
                        if isinstance(obj, dict):
                            # Look for video-related keys
                            video_keys = [k for k in obj.keys() if 'video' in k.lower() or 'url' in k.lower()]
                            if video_keys:
                                print(f"    Video-related keys: {video_keys}")
                                for key in video_keys:
                                    print(f"      {key}: {obj[key]}")
                    except:
                        print(f"    (Not valid JSON)")
            
            # Look for MLB video service patterns more specifically
            mlb_patterns = [
                r'https://cuts\.diamond\.mlb\.com/[^"\s]*',
                r'https://mlb-cuts-diamond\.mlb\.com/[^"\s]*',
                r'https://[^"\s]*\.mlbstatic\.com/[^"\s]*video[^"\s]*',
                r'https://[^"\s]*\.mlb\.com/[^"\s]*video[^"\s]*',
                r'playback_url["\']:\s*["\']([^"\']*)["\']',
            ]
            
            print(f"\n🏀 MLB-specific video URLs:")
            mlb_urls = set()
            for pattern in mlb_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                mlb_urls.update(matches)
            
            for url in sorted(mlb_urls):
                print(f"  🎥 {url}")
                
                # Test if these URLs work
                try:
                    test_response = requests.head(url, timeout=10)
                    content_type = test_response.headers.get('content-type', 'unknown')
                    content_length = test_response.headers.get('content-length', 'unknown')
                    print(f"      Status: {test_response.status_code}")
                    print(f"      Type: {content_type}")
                    print(f"      Size: {content_length}")
                    
                    if test_response.status_code == 200 and 'video' in content_type:
                        print(f"      ✅ This is a working video URL!")
                        
                except Exception as e:
                    print(f"      Error testing: {e}")
            
            # Save the HTML for detailed manual inspection
            with open('working_video_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n💾 Full HTML saved to: working_video_page.html")
            
            # Look for embedded video tags
            video_tag_patterns = [
                r'<video[^>]*>.*?</video>',
                r'<source[^>]*src="([^"]*)"[^>]*>',
                r'<iframe[^>]*src="([^"]*)"[^>]*>',
            ]
            
            print(f"\n📺 Looking for video tags:")
            for pattern in video_tag_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    print(f"  Found: {match[:200]}...")
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extract_working_video_url() 