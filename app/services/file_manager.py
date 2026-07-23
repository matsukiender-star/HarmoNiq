import os
import shutil
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Any

class FileManager:
    @staticmethod
    def get_system_music_dir() -> Path:
        home = Path.home()
        if platform.system() == "Windows":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                    music_path = winreg.QueryValueEx(key, "My Music")[0]
                    return Path(music_path)
            except Exception:
                pass
        elif platform.system() == "Linux":
            try:
                result = subprocess.run(["xdg-user-dir", "MUSIC"], capture_output=True, text=True, check=True)
                path = result.stdout.strip()
                if path and path != str(home):
                    return Path(path)
            except Exception:
                pass
        
        # Fallbacks for other OS or if the above fails
        candidates = ["Música", "Music", "Musique", "Musik", "Descargas", "Downloads"]
        for c in candidates:
            if (home / c).exists():
                return home / c
                
        return home / "Music"

    @staticmethod
    def get_default_download_dir() -> str:
        music_dir = FileManager.get_system_music_dir()
        
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
