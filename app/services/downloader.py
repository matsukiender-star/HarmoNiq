import os
import shutil


def _ensure_ffmpeg():
    """Deja ffmpeg/ffprobe disponibles en el PATH.

    Si ya hay un ffmpeg utilizable (el que viene dentro del AppImage, o el del
    sistema) no se toca nada. Solo se recurre a static_ffmpeg como ultimo
    recurso, porque su add_paths() escribe un lock dentro del paquete y dentro
    de un AppImage el sistema de archivos es de solo lectura:
        OSError: [Errno 30] Read-only file system: '.../static_ffmpeg/lock.file'
    Eso tumbaba la app al arrancar, antes de mostrar ninguna ventana.
    """
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as exc:  # pragma: no cover - depende del entorno
        print(f"[ffmpeg] no se pudo preparar static_ffmpeg: {exc}")


_ensure_ffmpeg()

import asyncio
from typing import Dict, Any, Callable, Optional
from yt_dlp import YoutubeDL

active_downloads: Dict[str, bool] = {}

class DownloaderService:
    @staticmethod
    def get_info(url: str) -> Dict[str, Any]:
        """Fetch YouTube video/playlist info without downloading"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios', 'mweb'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    # Playlist
                    entries = []
                    for entry in info['entries']:
                        if entry:
                            entries.append({
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'duration': entry.get('duration', 0),
                                'uploader': entry.get('uploader', '')
                            })
                    return {
                        'is_playlist': True,
                        'title': info.get('title', 'Lista de reproducción'),
                        'count': len(entries),
                        'entries': entries
                    }
                else:
                    return {
                        'is_playlist': False,
                        'id': info.get('id'),
                        'title': info.get('title'),
                        'uploader': info.get('uploader'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail'),
                        'description': info.get('description', '')
                    }
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def download_audio(
        url: str,
        output_dir: str,
        filename_template: str = "%(title)s.%(ext)s",
        quality: str = "320",
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        
        current_filename = None
        def my_hook(d):
            nonlocal current_filename
            if d.get('filename'):
                current_filename = d.get('filename')
                
            if is_cancelled and is_cancelled():
                raise Exception("Descarga cancelada por el usuario")

            if progress_callback and d.get('status') == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded_bytes = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                percent = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
                
                progress_callback({
                    'status': 'downloading',
                    'percent': round(percent, 1),
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes,
                    'speed': speed,
                    'eta': eta,
                    'filename': d.get('filename')
                })
            elif progress_callback and d.get('status') == 'finished':
                progress_callback({
                    'status': 'converting',
                    'percent': 100.0,
                    'message': 'Convirtiendo audio a MP3...'
                })

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'outtmpl': os.path.join(output_dir, filename_template),
            'progress_hooks': [my_hook],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios', 'mweb'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                final_mp3 = None
                if info.get('requested_downloads'):
                    for rd in info['requested_downloads']:
                        fp = rd.get('filepath')
                        if fp:
                            final_mp3 = os.path.splitext(fp)[0] + ".mp3"
                            break

                if not final_mp3 or not os.path.exists(final_mp3):
                    prepared = ydl.prepare_filename(info)
                    final_mp3 = os.path.splitext(prepared)[0] + ".mp3"
                
                return {
                    'success': True,
                    'filepath': final_mp3,
                    'title': info.get('title'),
                    'uploader': info.get('uploader'),
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'description': info.get('description', '')
                }
        except Exception as e:
            if current_filename:
                # Intenta borrar el archivo parcial (.part o incompleto) y su version .mp3
                try:
                    if os.path.exists(current_filename):
                        os.remove(current_filename)
                    if current_filename.endswith(".part"):
                        base = current_filename[:-5]
                        if os.path.exists(base):
                            os.remove(base)
                    mp3_ver = os.path.splitext(current_filename)[0] + ".mp3"
                    if os.path.exists(mp3_ver):
                        os.remove(mp3_ver)
                except:
                    pass
            return {'success': False, 'error': str(e)}
