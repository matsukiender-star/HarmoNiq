import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

class FileManager:
    @staticmethod
    def get_default_download_dir() -> str:
        home = Path.home()
        music_dir = home / "Música"
        if not music_dir.exists():
            music_dir = home / "Music"
        if not music_dir.exists():
            music_dir = home / "Downloads"
        
        target_dir = music_dir / "YouTube_Downloads"
        target_dir.mkdir(parents=True, exist_ok=True)
        return str(target_dir)

    @staticmethod
    def ensure_dir(path: str) -> str:
        clean_path = os.path.expanduser(path.strip())
        p = Path(clean_path)
        p.mkdir(parents=True, exist_ok=True)
        return str(p.resolve())

    @staticmethod
    def get_system_shortcuts() -> List[Dict[str, str]]:
        home = Path.home()
        shortcuts = []
        
        candidates = [
            ("Música", home / "Música"),
            ("Music", home / "Music"),
            ("Descargas", home / "Descargas"),
            ("Downloads", home / "Downloads"),
            ("Escritorio", home / "Escritorio"),
            ("Desktop", home / "Desktop"),
            ("Documentos", home / "Documentos"),
            ("Documents", home / "Documents"),
        ]
        
        seen = set()
        for name, p in candidates:
            if p.exists() and str(p) not in seen:
                seen.add(str(p))
                yt_p = p / "YouTube_Downloads"
                shortcuts.append({
                    "name": name,
                    "path": str(p),
                    "yt_path": str(yt_p)
                })
        return shortcuts

    @staticmethod
    def list_mp3_files(directory: str) -> List[Dict[str, Any]]:
        target = Path(os.path.expanduser(directory))
        if not target.exists() or not target.is_dir():
            return []
        
        files = []
        for file in target.glob("*.mp3"):
            try:
                stat = file.stat()
                files.append({
                    "filename": file.name,
                    "filepath": str(file.resolve()),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime
                })
            except Exception:
                continue
        files.sort(key=lambda x: x["modified"], reverse=True)
        return files
