#!/usr/bin/env python3
"""
Setup script for Baseball Savant GIF Integration
Checks and installs required dependencies
"""

import subprocess
import sys
import platform
import os

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def install_ffmpeg():
    """Install ffmpeg based on the operating system"""
    system = platform.system().lower()
    
    print(f"🔧 Installing ffmpeg for {system}...")
    
    if system == "darwin":  # macOS
        print("Installing ffmpeg via Homebrew...")
        print("If you don't have Homebrew, install it from: https://brew.sh/")
        try:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
            print("✅ ffmpeg installed successfully!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install ffmpeg via Homebrew")
            print("   Please install Homebrew first: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False
        except FileNotFoundError:
            print("❌ Homebrew not found")
            print("   Please install Homebrew first: https://brew.sh/")
            return False
    
    elif system == "linux":
        print("Installing ffmpeg via apt...")
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], check=True)
            print("✅ ffmpeg installed successfully!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install ffmpeg via apt")
            print("   You may need to run this script with sudo privileges")
            return False
    
    elif system == "windows":
        print("❌ Automatic Windows installation not supported")
        print("   Please download ffmpeg from: https://ffmpeg.org/download.html")
        print("   1. Download Windows build")
        print("   2. Extract to a folder (e.g., C:\\ffmpeg)")
        print("   3. Add C:\\ffmpeg\\bin to your PATH environment variable")
        return False
    
    else:
        print(f"❌ Unsupported operating system: {system}")
        return False

def test_installation():
    """Test the installation"""
    print("\n🧪 Testing installation...")
    
    # Test Python imports
    try:
        import requests
        import subprocess
        from pathlib import Path
        print("✅ Python dependencies OK")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        return False
    
    # Test ffmpeg
    if check_ffmpeg():
        print("✅ ffmpeg OK")
    else:
        print("❌ ffmpeg not working")
        return False
    
    print("✅ All dependencies ready!")
    return True

def main():
    print("🏟️  Baseball Savant GIF Integration Setup")
    print("=" * 50)
    
    # Check current status
    print("🔍 Checking current installation...")
    
    ffmpeg_ok = check_ffmpeg()
    
    print(f"   ffmpeg: {'✅ installed' if ffmpeg_ok else '❌ missing'}")
    
    # Install missing dependencies
    if not ffmpeg_ok:
        print("\n📦 Installing missing dependencies...")
        if not install_ffmpeg():
            print("\n❌ Setup failed. Please install ffmpeg manually.")
            return False
    
    # Test everything
    if test_installation():
        print("\n🎉 Setup completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Run: python test_baseball_savant_gif.py")
        print("   2. Test with a live game during baseball season")
        print("   3. Integrate with your impact tracker")
        return True
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 