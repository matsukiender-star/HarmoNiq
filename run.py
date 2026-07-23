#!/usr/bin/env python3
import os
import sys
import webbrowser
import threading
import time
import uvicorn
import static_ffmpeg
import websockets
import uvicorn.loops.auto
import uvicorn.protocols.http.auto
import uvicorn.protocols.websockets.auto
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

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
    def start_server():
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="error", reload=False)

    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Create the PySide6 window
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("HarmoNiq - Auto-Tagger")
    window.resize(1024, 768)
    
    view = QWebEngineView()
    view.load(QUrl(url))
    
    window.setCentralWidget(view)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
