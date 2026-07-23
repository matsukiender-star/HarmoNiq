#!/usr/bin/env python3
"""
Wrapper for Windows: opens the browser and runs the server.
Must be run as HarmoNiq.exe on Windows.
"""
import os
import sys
import webbrowser
import threading
import subprocess
import static_ffmpeg

# Ensure ffmpeg static binaries are added to PATH
static_ffmpeg.add_paths()

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def main():
    import uvicorn
    port = 8000
    url = f"http://localhost:{port}"
    
    print("=" * 65)
    print(" HarmoNiq - YouTube MP3 & Shazam Auto-Tagger")
    print("=" * 65)
    print(f" Server: {url}")
    print(" Press Ctrl+C to stop.")
    print("=" * 65)

    threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    
    # Set template/static paths based on bundle location
    base = get_base_dir()
    os.environ["HARMONIQ_BASE"] = base
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning", reload=False)

if __name__ == "__main__":
    main()
