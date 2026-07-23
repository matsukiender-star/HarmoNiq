#!/usr/bin/env python3
import os
import sys
import webbrowser
import uvicorn
import static_ffmpeg

# Ensure ffmpeg static binaries are added to PATH
static_ffmpeg.add_paths()

def main():
    port = 8000
    url = f"http://localhost:{port}"
    print("=" * 65)
    print(" 🎵 HarmoNiq - YouTube MP3 & Shazam Auto-Tagger")
    print("=" * 65)
    print(f" Iniciando servidor web local en: {url}")
    print(" Presiona Ctrl+C para detener la aplicación.")
    print("=" * 65)
    
    # Open browser automatically after brief delay
    def open_browser():
        try:
            webbrowser.open(url)
        except Exception:
            pass

    import threading
    threading.Timer(1.5, open_browser).start()
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info", reload=False)

if __name__ == "__main__":
    main()
