import os
import json
import io
import shutil
import uuid
import asyncio
import subprocess
import tempfile
import ssl
import certifi
import aiohttp
import aiohttp.connector

def _find_system_ca_bundle():
    paths = [
        "/etc/ssl/certs/ca-certificates.crt",                # Debian/Ubuntu/Gentoo etc.
        "/etc/pki/tls/certs/ca-bundle.crt",                  # Fedora/RHEL 6
        "/etc/ssl/ca-bundle.pem",                            # OpenSUSE
        "/etc/pki/tls/cacert.pem",                           # OpenELEC
        "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem", # CentOS/RHEL 7, Nobara
        "/etc/ssl/cert.pem",                                 # Alpine Linux
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return certifi.where()

ca_bundle = _find_system_ca_bundle()
os.environ["SSL_CERT_FILE"] = ca_bundle
os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle

# Force completely bypass SSL verification
ssl._create_default_https_context = ssl._create_unverified_context
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()
aiohttp.connector.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
from pydantic import BaseModel

from app.services.file_manager import FileManager
from app.services.downloader import DownloaderService, active_downloads
from app.services.shazam_service import ShazamService
from app.services.tagger import TaggerService

app = FastAPI(title="HarmoNiq - YouTube MP3 & Shazam Auto-Tagger", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

shazam_service = ShazamService()

# --- Persistent config ---
def _get_config_path():
    """Returns the path to the persistent config file."""
    if platform.system() == "Windows":
        config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HarmoNiq")
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "HarmoNiq")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "settings.json")

def _load_config():
    """Loads config from disk, falling back to defaults."""
    defaults = {
        "download_dir": FileManager.get_default_download_dir(),
        "naming_pattern": "{artist} - {title}",
        "auto_shazam": True,
        "quality": "320"
    }
    config_path = _get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for key in defaults:
                if key in saved:
                    defaults[key] = saved[key]
            # Verify saved download_dir still exists, otherwise use default
            if not os.path.isdir(defaults["download_dir"]):
                defaults["download_dir"] = FileManager.get_default_download_dir()
        except Exception:
            pass
    return defaults

def _save_config(state: dict):
    """Saves current config to disk."""
    try:
        config_path = _get_config_path()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

import platform

# Global config state (loaded from disk)
app_state = _load_config()

# WebSocket active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_status(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(data)
            except Exception:
                pass

manager = ConnectionManager()

# Pydantic Schemas
class DownloadRequest(BaseModel):
    url: str
    output_dir: Optional[str] = None
    auto_shazam: Optional[bool] = True
    quality: Optional[str] = "320"

class TagRequest(BaseModel):
    file_path: str
    title: str
    artist: str
    album: str
    year: Optional[str] = ""
    genre: Optional[str] = ""
    lyrics: Optional[str] = ""
    cover_url: Optional[str] = None

class ConfigRequest(BaseModel):
    download_dir: str
    auto_shazam: Optional[bool] = True
    quality: Optional[str] = "320"


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "download_dir": app_state["download_dir"],
            "shortcuts": FileManager.get_system_shortcuts()
        }
    )

@app.get("/api/config")
async def get_config():
    return {
        "download_dir": app_state["download_dir"],
        "auto_shazam": app_state["auto_shazam"],
        "quality": app_state["quality"],
        "shortcuts": FileManager.get_system_shortcuts()
    }

@app.post("/api/config")
async def set_config(req: ConfigRequest):
    try:
        clean_path = FileManager.ensure_dir(req.download_dir)
        app_state["download_dir"] = clean_path
        app_state["auto_shazam"] = req.auto_shazam
        app_state["quality"] = req.quality
        _save_config(app_state)
        return {"success": True, "download_dir": clean_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/preview")
async def preview_url(payload: Dict[str, str]):
    url = payload.get("url", "").strip()
    if not url:
        return {"error": "Proporcione una URL válida de YouTube"}
    
    info = await asyncio.to_thread(DownloaderService.get_info, url)
    return info

@app.websocket("/ws/progress/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id)

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    task_id = str(uuid.uuid4())
    active_downloads[task_id] = False
    target_dir = FileManager.ensure_dir(req.output_dir or app_state["download_dir"])
    
    # Run download process asynchronously
    asyncio.create_task(run_download_process(
        task_id=task_id,
        url=req.url,
        target_dir=target_dir,
        auto_shazam=req.auto_shazam if req.auto_shazam is not None else app_state["auto_shazam"],
        quality=req.quality or app_state["quality"]
    ))
    
    return {"task_id": task_id, "status": "started", "target_dir": target_dir}

@app.post("/api/cancel/{task_id}")
async def cancel_download(task_id: str):
    active_downloads[task_id] = "cancelled"
    return {"success": True, "message": "Descarga cancelada"}

async def run_download_process(task_id: str, url: str, target_dir: str, auto_shazam: bool, quality: str):
    loop = asyncio.get_running_loop()

    await manager.send_status(task_id, {
        "step": "preparing",
        "message": "Obteniendo información del enlace...",
        "percent": 0
    })

    # Get info to see if it's a playlist
    info = await asyncio.to_thread(DownloaderService.get_info, url)
    if "error" in info:
        await manager.send_status(task_id, {
            "step": "error",
            "message": f"Error al obtener info: {info['error']}"
        })
        return

    entries = info.get('entries') if info.get('is_playlist') else [{'url': url, 'title': info.get('title')}]
    
    if info.get('is_playlist'):
        if "list=RD" in url:
            entries = entries[:15]
            
    total_entries = len(entries)
    
    active_downloads[task_id] = "running"
    
    for i, entry in enumerate(entries):
        is_cancelled = active_downloads.get(task_id) == "cancelled"
        if is_cancelled:
            break

        entry_url = entry['url']
        
        await manager.send_status(task_id, {
            "step": "preparing",
            "message": f"Iniciando descarga {i+1} de {total_entries}: {entry.get('title', 'Audio')}...",
            "percent": 0
        })

        def progress_callback(data):
            asyncio.run_coroutine_threadsafe(
                manager.send_status(task_id, {
                    "step": "downloading",
                    "percent": data.get("percent", 0),
                    "speed": data.get("speed", 0),
                    "eta": data.get("eta", 0),
                    "message": f"[{i+1}/{total_entries}] Descargando audio ({data.get('percent', 0)}%)"
                }),
                loop
            )

        res = await asyncio.to_thread(
            DownloaderService.download_audio,
            url=entry_url,
            output_dir=target_dir,
            quality=quality,
            progress_callback=progress_callback,
            is_cancelled=lambda: active_downloads.get(task_id) == "cancelled"
        )

        is_cancelled = active_downloads.get(task_id) == "cancelled"
        
        if is_cancelled:
            if res.get("filepath") and os.path.exists(res["filepath"]):
                try:
                    os.remove(res["filepath"])
                except:
                    pass
            break

        if not res.get("success"):
            # skip to next if playlist, else break
            continue

        mp3_file = res["filepath"]
        yt_title = res.get("title", "")
        yt_uploader = res.get("uploader", "")
        yt_thumbnail = res.get("thumbnail", "")

        metadata = {}
        if auto_shazam:
            if is_cancelled:
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                break

            await manager.send_status(task_id, {
                "step": "shazam",
                "message": f"[{i+1}/{total_entries}] Reconociendo canción con Shazam...",
                "percent": 85
            })
            
            print(f"About to shazam {mp3_file}. Exists? {os.path.exists(mp3_file)}")

            shazam_res = await shazam_service.recognize_file(mp3_file)
            
            is_cancelled = active_downloads.get(task_id) == "cancelled"
            if is_cancelled:
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                break

            if shazam_res.get("success") and shazam_res.get("matched"):
                metadata = {
                    "title": shazam_res["title"],
                    "artist": shazam_res["artist"],
                    "album": shazam_res["album"],
                    "year": shazam_res["year"],
                    "genre": shazam_res["genre"],
                    "cover_url": shazam_res["cover_url"],
                    "lyrics": shazam_res["lyrics"],
                    "matched_by_shazam": True
                }
            else:
                print("Shazam failed or didn't match. Response:", shazam_res)
                parsed = ShazamService.parse_youtube_title(yt_title, yt_uploader)
                metadata = {
                    "title": parsed["title"],
                    "artist": parsed["artist"],
                    "album": parsed["album"],
                    "year": "",
                    "genre": "",
                    "cover_url": yt_thumbnail,
                    "lyrics": "",
                    "matched_by_shazam": False
                }
        else:
            parsed = ShazamService.parse_youtube_title(yt_title, yt_uploader)
            metadata = {
                "title": parsed["title"],
                "artist": parsed["artist"],
                "album": parsed["album"],
                "year": "",
                "genre": "",
                "cover_url": yt_thumbnail,
                "lyrics": "",
                "matched_by_shazam": False
            }

        metadata["filepath"] = mp3_file

        await manager.send_status(task_id, {
            "step": "tagging",
            "message": f"[{i+1}/{total_entries}] Aplicando Etiquetas ID3...",
            "percent": 95
        })

        tag_res = await asyncio.to_thread(
            TaggerService.apply_tags,
            mp3_file,
            metadata.get("title"),
            metadata.get("artist"),
            metadata.get("album"),
            metadata.get("year"),
            metadata.get("genre"),
            metadata.get("lyrics"),
            metadata.get("cover_url")
        )

        if not tag_res.get("success"):
            pass

        await manager.send_status(task_id, {
            "step": "item_completed",
            "percent": 100,
            "message": f"[{i+1}/{total_entries}] ¡Completado!",
            "file_info": metadata
        })

    is_cancelled = active_downloads.get(task_id) == "cancelled"
    
    if is_cancelled:
        await manager.send_status(task_id, {
            "step": "error",
            "message": "Proceso cancelado por el usuario"
        })
    else:
        await manager.send_status(task_id, {
            "step": "completed",
            "percent": 100,
            "message": "¡Proceso finalizado con éxito!",
            "file_info": metadata if total_entries == 1 else None
        })
        
    if task_id in active_downloads:
        del active_downloads[task_id]


@app.post("/api/shazam-file")
async def shazam_file(file_path: Optional[str] = Form(None), file: Optional[UploadFile] = File(None)):
    target_path = file_path

    if file:
        # Save uploaded file permanently in user's download directory so it can be edited and retained!
        target_dir = FileManager.ensure_dir(app_state["download_dir"])
        safe_filename = file.filename or f"uploaded_{uuid.uuid4().hex[:8]}.mp3"
        if not safe_filename.endswith(".mp3"):
            safe_filename += ".mp3"
            
        target_path = os.path.join(target_dir, safe_filename)
        
        # Avoid overwriting by appending counter if needed
        counter = 1
        base, ext = os.path.splitext(target_path)
        while os.path.exists(target_path):
            target_path = f"{base}_{counter}{ext}"
            counter += 1

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    if not target_path or not os.path.exists(target_path):
        return {"success": False, "error": "Ruta de archivo no existe o archivo inválido"}

    res = await shazam_service.recognize_file(target_path)
    res["filepath"] = target_path
    res["filename"] = os.path.basename(target_path)
    return res

@app.post("/api/read-tags")
async def read_tags(payload: Dict[str, str]):
    file_path = payload.get("file_path", "")
    return TaggerService.read_tags(file_path)

@app.post("/api/save-tags")
async def save_tags(
    file_path: str = Form(...),
    title: str = Form(...),
    artist: str = Form(...),
    album: str = Form(...),
    year: Optional[str] = Form(""),
    genre: Optional[str] = Form(""),
    lyrics: Optional[str] = Form(""),
    cover_url: Optional[str] = Form(None),
    cover_file: Optional[UploadFile] = File(None)
):
    cover_bytes = None
    if cover_file:
        cover_bytes = await cover_file.read()

    res = TaggerService.apply_tags(
        file_path=file_path,
        title=title,
        artist=artist,
        album=album,
        year=year,
        genre=genre,
        lyrics=lyrics,
        cover_url=cover_url,
        cover_bytes=cover_bytes
    )
    
    # Optionally rename file if artist & title changed
    final_path = file_path
    if res.get("success") and artist and title:
        clean_artist = "".join([c for c in artist if c.isalnum() or c in " -_()[]"]).strip()
        clean_title = "".join([c for c in title if c.isalnum() or c in " -_()[]"]).strip()
        if clean_artist and clean_title:
            target_dir = os.path.dirname(file_path)
            new_filename = f"{clean_artist} - {clean_title}.mp3"
            new_filepath = os.path.join(target_dir, new_filename)
            try:
                if file_path != new_filepath and os.path.exists(file_path):
                    if os.path.exists(new_filepath):
                        os.remove(new_filepath)
                    os.rename(file_path, new_filepath)
                    final_path = new_filepath
            except Exception:
                pass

    res["filepath"] = final_path
    res["filename"] = os.path.basename(final_path)
    res["cover_url"] = f"/api/cover-file?path={final_path}"
    return res

@app.get("/api/files")
async def list_files(directory: Optional[str] = None):
    target_dir = directory or app_state["download_dir"]
    files = FileManager.list_mp3_files(target_dir)
    return {"directory": target_dir, "files": files}

@app.get("/api/audio-file")
async def get_audio_file(path: str):
    if not os.path.exists(path) or not path.endswith(".mp3"):
        raise HTTPException(status_code=404, detail="Archivo MP3 no encontrado")
    return FileResponse(path, media_type="audio/mpeg")

@app.get("/api/cover-file")
async def get_cover_file(path: str):
    if not os.path.exists(path) or not path.endswith(".mp3"):
        return FileResponse(os.path.join(BASE_DIR, "static/images/default_cover.svg"), media_type="image/svg+xml")

    img_bytes, mime_type = TaggerService.get_cover_art(path)
    if img_bytes:
        return Response(content=img_bytes, media_type=mime_type or "image/jpeg")

    return FileResponse(os.path.join(BASE_DIR, "static/images/default_cover.svg"), media_type="image/svg+xml")

@app.post("/api/open-folder")
async def open_folder(payload: Dict[str, str]):
    path = payload.get("path") or app_state["download_dir"]
    if os.path.exists(path):
        try:
            subprocess.Popen(["xdg-open", path])
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Ruta no existe"}
