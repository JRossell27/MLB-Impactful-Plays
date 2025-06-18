#!/usr/bin/env python3
"""
Extract video URLs from Baseball Savant HTML responses
"""

import requests
import re
import json

def extract_video_urls():
    """Extract video URLs from Baseball Savant responses"""
    
    print("🎬 Extracting Video URLs from Baseball Savant")
    print("=" * 60)
    
    # Test the sporty-videos URL that returned HTML with video references
    test_url = "https://baseballsavant.mlb.com/sporty-videos?playId=37"
    
    print(f"Analyzing: {test_url}")
    
    try:
        response = requests.get(test_url, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            print(f"✅ Got HTML content ({len(html_content)} characters)")
            
            # Look for various video URL patterns
            video_patterns = [
                r'https?://[^\s"\']*\.mp4[^\s"\']*',  # Direct MP4 URLs
                r'https?://[^\s"\']*\.m3u8[^\s"\']*',  # HLS streams
                r'https?://[^\s"\']*video[^\s"\']*',  # URLs containing "video"
                r'"url":\s*"([^"]*\.mp4[^"]*)"',  # JSON-style video URLs
                r'"videoUrl":\s*"([^"]*)"',  # videoUrl field
                r'"src":\s*"([^"]*\.mp4[^"]*)"',  # src attributes
                r'data-video-url="([^"]*)"',  # data attributes
                r'sporty-videos/([^"\'>\s]*)',  # sporty-videos paths
            ]
            
            all_video_urls = set()
            
            for pattern in video_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]  # Get first group if tuple
                    all_video_urls.add(match)
            
            print(f"\n🔍 Found {len(all_video_urls)} potential video URLs:")
            for i, url in enumerate(sorted(all_video_urls), 1):
                print(f"  {i}. {url}")
            
            # Look for JavaScript variables that might contain video data
            js_patterns = [
                r'var\s+(\w*[Vv]ideo\w*)\s*=\s*({[^;]*});',
                r'const\s+(\w*[Vv]ideo\w*)\s*=\s*({[^;]*});',
                r'let\s+(\w*[Vv]ideo\w*)\s*=\s*({[^;]*});',
                r'window\.(\w*[Vv]ideo\w*)\s*=\s*({[^;]*});',
            ]
            
            print(f"\n🔍 Looking for JavaScript video variables:")
            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for var_name, var_value in matches:
                    print(f"  Variable: {var_name}")
                    print(f"  Value: {var_value[:200]}...")
            
            # Look for any MLB video service URLs
            mlb_video_patterns = [
                r'https?://[^\s"\']*mlb[^\s"\']*video[^\s"\']*',
                r'https?://[^\s"\']*baseball[^\s"\']*video[^\s"\']*',
                r'https?://cuts\.diamond\.mlb\.com[^\s"\']*',
                r'https?://mlb-cuts-diamond\.mlb\.com[^\s"\']*',
            ]
            
            print(f"\n🏀 Looking for MLB video service URLs:")
            mlb_urls = set()
            for pattern in mlb_video_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                mlb_urls.update(matches)
            
            for url in sorted(mlb_urls):
                print(f"  🎥 {url}")
            
            # Save the HTML for manual inspection
            with open('savant_sporty_videos.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n💾 Full HTML saved to: savant_sporty_videos.html")
            
            # Check if any of the found URLs are actually accessible
            print(f"\n🔗 Testing accessibility of found URLs:")
            test_urls = list(all_video_urls)[:5]  # Test first 5
            
            for url in test_urls:
                if url.startswith('http'):
                    try:
                        test_response = requests.head(url, timeout=10)
                        content_type = test_response.headers.get('content-type', 'unknown')
                        print(f"  {url}: {test_response.status_code} ({content_type})")
                    except Exception as e:
                        print(f"  {url}: Error - {e}")
                else:
                    print(f"  {url}: Relative URL (needs base)")
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extract_video_urls() 