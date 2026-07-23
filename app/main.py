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
    active_downloads[task_id] = True
    return {"success": True, "message": "Descarga cancelada"}

async def run_download_process(task_id: str, url: str, target_dir: str, auto_shazam: bool, quality: str):
    loop = asyncio.get_running_loop()

    await manager.send_status(task_id, {
        "step": "preparing",
        "message": "Iniciando descarga de audio...",
        "percent": 0
    })

    def progress_callback(data):
        asyncio.run_coroutine_threadsafe(
            manager.send_status(task_id, {
                "step": "downloading",
                "percent": data.get("percent", 0),
                "speed": data.get("speed", 0),
                "eta": data.get("eta", 0),
                "message": f"Descargando audio ({data.get('percent', 0)}%)"
            }),
            loop
        )

    # 1. Download YouTube video audio
    res = await asyncio.to_thread(
        DownloaderService.download_audio,
        url=url,
        output_dir=target_dir,
        quality=quality,
        progress_callback=progress_callback,
        task_id=task_id
    )

    # Limpiar estado
    if task_id in active_downloads:
        del active_downloads[task_id]

    if not res.get("success"):
        await manager.send_status(task_id, {
            "step": "error",
            "message": f"Error al descargar: {res.get('error')}"
        })
        return

    mp3_file = res["filepath"]
    yt_title = res.get("title", "")
    yt_uploader = res.get("uploader", "")
    yt_thumbnail = res.get("thumbnail", "")

    # 2. Shazam Recognition if requested
    metadata = {}
    if auto_shazam:
        await manager.send_status(task_id, {
            "step": "shazam",
            "message": "Reconociendo canción con Shazam...",
            "percent": 85
        })

        shazam_res = await shazam_service.recognize_file(mp3_file)
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
            # Fallback to YouTube title parsing
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

    # 3. Apply ID3 Tags
    await manager.send_status(task_id, {
        "step": "tagging",
        "message": "Escribiendo etiquetas ID3 y portada de álbum...",
        "percent": 95
    })

    tag_res = TaggerService.apply_tags(
        file_path=mp3_file,
        title=metadata.get("title"),
        artist=metadata.get("artist"),
        album=metadata.get("album"),
        year=metadata.get("year"),
        genre=metadata.get("genre"),
        lyrics=metadata.get("lyrics"),
        cover_url=metadata.get("cover_url")
    )

    # 4. Optional rename file according to pattern
    final_filepath = mp3_file
    if metadata.get("artist") and metadata.get("title"):
        clean_artist = "".join([c for c in metadata["artist"] if c.isalnum() or c in " -_()[]"]).strip()
        clean_title = "".join([c for c in metadata["title"] if c.isalnum() or c in " -_()[]"]).strip()
        if clean_artist and clean_title:
            new_filename = f"{clean_artist} - {clean_title}.mp3"
            new_filepath = os.path.join(target_dir, new_filename)
            try:
                if mp3_file != new_filepath:
                    if os.path.exists(new_filepath):
                        os.remove(new_filepath)
                    os.rename(mp3_file, new_filepath)
                    final_filepath = new_filepath
            except Exception:
                pass

    # 5. Finished
    await manager.send_status(task_id, {
        "step": "completed",
        "message": "¡Descarga y etiquetado completados!",
        "percent": 100,
        "file_info": {
            "filepath": final_filepath,
            "filename": os.path.basename(final_filepath),
            "title": metadata.get("title"),
            "artist": metadata.get("artist"),
            "album": metadata.get("album"),
            "year": metadata.get("year"),
            "genre": metadata.get("genre"),
            "cover_url": f"/api/cover-file?path={final_filepath}",
            "matched_by_shazam": metadata.get("matched_by_shazam", False)
        }
    })

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
        return FileResponse(os.path.join(BASE_DIR, "static/images/default_cover.svg"))

    img_bytes, mime_type = TaggerService.get_cover_art(path)
    if img_bytes:
        return Response(content=img_bytes, media_type=mime_type or "image/jpeg")

    return FileResponse(os.path.join(BASE_DIR, "static/images/default_cover.svg"))

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
