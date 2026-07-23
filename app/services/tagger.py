import os
import io
import base64
import urllib.request
from typing import Dict, Any, Optional, Tuple
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3, TIT2, TPE1, TALB, TDRC, TCON, USLT, APIC, ID3NoHeaderError
)

class TaggerService:
    @staticmethod
    def detect_mime_type(data: bytes) -> str:
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        elif data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
            return 'image/webp'
        return 'image/jpeg'

    @staticmethod
    def apply_tags(
        file_path: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        year: Optional[str] = None,
        genre: Optional[str] = None,
        lyrics: Optional[str] = None,
        cover_url: Optional[str] = None,
        cover_bytes: Optional[bytes] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Archivo no encontrado: {file_path}"}

        try:
            try:
                audio = MP3(file_path, ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(file_path)
                audio.add_tags()

            tags = audio.tags

            if title:
                tags.add(TIT2(encoding=3, text=title))
            if artist:
                tags.add(TPE1(encoding=3, text=artist))
            if album:
                tags.add(TALB(encoding=3, text=album))
            if year:
                tags.add(TDRC(encoding=3, text=str(year)))
            if genre:
                tags.add(TCON(encoding=3, text=genre))
            if lyrics:
                tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))

            # Cover Art embedding
            img_data = cover_bytes

            # Check if cover_url is a base64 data URI
            if not img_data and cover_url and cover_url.startswith("data:image"):
                try:
                    header, encoded = cover_url.split(",", 1)
                    img_data = base64.b64decode(encoded)
                except Exception as b64_err:
                    print(f"Error decodificando imagen base64: {b64_err}")

            # Download cover from HTTP URL if no bytes passed
            if not img_data and cover_url and cover_url.startswith(("http://", "https://")):
                try:
                    req = urllib.request.Request(
                        cover_url, 
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        img_data = response.read()
                except Exception as img_err:
                    print(f"Error descargando carátula ({cover_url}): {img_err}")

            if img_data:
                mime_type = TaggerService.detect_mime_type(img_data)
                # Clear all existing APIC frames before inserting the new cover
                tags.delall('APIC')
                tags.add(
                    APIC(
                        encoding=3,
                        mime=mime_type,
                        type=3,  # 3 is front cover
                        desc='Cover',
                        data=img_data
                    )
                )

            tags.save(file_path, v2_version=3)
            return {"success": True, "message": "Etiquetas ID3 aplicadas correctamente."}
        except Exception as e:
            return {"success": False, "error": f"Error al escribir etiquetas ID3: {str(e)}"}

    @staticmethod
    def read_tags(file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"success": False, "error": "Archivo no encontrado"}

        try:
            try:
                audio = MP3(file_path, ID3=ID3)
                tags = audio.tags
            except Exception:
                tags = None

            if not tags:
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                return {
                    "success": True,
                    "title": name_without_ext,
                    "artist": "Artista Desconocido",
                    "album": "Álbum Desconocido",
                    "year": "",
                    "genre": "",
                    "lyrics": "",
                    "has_cover": False
                }

            def get_text(frame_key):
                frame = tags.get(frame_key)
                if frame and frame.text:
                    return str(frame.text[0])
                return ""

            title = get_text("TIT2") or os.path.splitext(os.path.basename(file_path))[0]
            artist = get_text("TPE1")
            album = get_text("TALB")
            year = get_text("TDRC") or get_text("TYER")
            genre = get_text("TCON")
            
            lyrics = ""
            for key in tags.keys():
                if key.startswith("USLT"):
                    lyrics = str(tags[key].text)
                    break

            has_cover = False
            for key in tags.keys():
                if key.startswith("APIC"):
                    has_cover = True
                    break

            return {
                "success": True,
                "title": title,
                "artist": artist,
                "album": album,
                "year": year,
                "genre": genre,
                "lyrics": lyrics,
                "has_cover": has_cover
            }
        except Exception as e:
            return {"success": False, "error": f"Error leyendo etiquetas: {str(e)}"}

    @staticmethod
    def get_cover_art(file_path: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Extract embedded APIC cover image bytes and MIME type from MP3"""
        if not os.path.exists(file_path):
            return None, None
        try:
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                for key in audio.tags.keys():
                    if key.startswith("APIC"):
                        apic = audio.tags[key]
                        return apic.data, apic.mime
        except Exception:
            pass
        return None, None
