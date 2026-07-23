import os
import io
import shutil
import uuid
import asyncio
import subprocess
import tempfile
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

# Global config state
app_state = {
    "download_dir": FileManager.get_default_download_dir(),
    "naming_pattern": "{artist} - {title}",
    "auto_shazam": True,
    "quality": "320"
}

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
            task_id=task_id
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

        tag_success = await asyncio.to_thread(
            TaggerService.tag_file,
            file_path=mp3_file,
            metadata=metadata
        )

        if not tag_success:
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
