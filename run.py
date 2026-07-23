#!/usr/bin/env python3
import os
import sys
import webbrowser
import threading
import time
import socket

import certifi
import os
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

import uvicorn
import static_ffmpeg
import websockets
import uvicorn.loops.auto
import uvicorn.protocols.http.auto
import uvicorn.protocols.websockets.auto
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

import app.main  # Force PyInstaller to bundle the entire backend

# Ensure ffmpeg static binaries are added to PATH
static_ffmpeg.add_paths()

def find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def main():
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
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
    
    # Wait for the backend server to start before loading
    import socket
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.1)

    view.load(QUrl(url))
    
    window.setCentralWidget(view)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
