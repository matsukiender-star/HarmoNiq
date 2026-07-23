import asyncio
import os
import re
from typing import Dict, Any, Optional
from shazamio import Shazam

class ShazamService:
    def __init__(self):
        self.shazam = Shazam()

    async def recognize_file(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Archivo no encontrado: {file_path}"}
        
        try:
            out = await self.shazam.recognize(file_path)
            track = out.get("track")
            if not track:
                return {
                    "success": False,
                    "matched": False,
                    "message": "No se encontraron coincidencias en Shazam para esta canción."
                }
            
            title = track.get("title", "")
            artist = track.get("subtitle", "")
            
            # Extract image
            images = track.get("images", {})
            cover_url = images.get("coverarthdq") or images.get("coverart") or images.get("background")
            
            # Extract Album, Release Year, Genre, Lyrics
            album = ""
            year = ""
            genre = track.get("genres", {}).get("primary", "")
            lyrics = ""
            
            sections = track.get("sections", [])
            for sec in sections:
                sec_type = sec.get("type", "")
                if sec_type == "SONG":
                    metadata = sec.get("metadata", [])
                    for item in metadata:
                        item_title = item.get("title", "").lower()
                        item_text = item.get("text", "")
                        if "album" in item_title:
                            album = item_text
                        elif "released" in item_title or "año" in item_title or "lanzamiento" in item_title or "year" in item_title:
                            year = item_text
                elif sec_type == "LYRICS":
                    text_list = sec.get("text", [])
                    if text_list:
                        lyrics = "\n".join(text_list)

            shazam_url = track.get("share", {}).get("href", "") or track.get("url", "")
            
            return {
                "success": True,
                "matched": True,
                "title": title,
                "artist": artist,
                "album": album or f"{title} - Single",
                "year": year,
                "genre": genre,
                "cover_url": cover_url,
                "lyrics": lyrics,
                "shazam_url": shazam_url,
                "raw_track": track
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error al procesar con Shazam: {str(e)}"
            }

    @staticmethod
    def parse_youtube_title(yt_title: str, channel_name: str = "") -> Dict[str, str]:
        """Fallback helper to extract artist and song title from YouTube video title"""
        clean_title = yt_title
        # Remove common fluff in video titles
        fluff_patterns = [
            r'\(Official Music Video\)', r'\(Official Video\)', r'\(Video Oficial\)',
            r'\(Letra\)', r'\(Lyrics\)', r'\(Audio\)', r'\(Visualizer\)', r'\[Official Audio\]',
            r'\[Official Music Video\]', r'\(HD\)', r'\(4K\)', r'\(MV\)', r'\|.*$'
        ]
        for pattern in fluff_patterns:
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
        
        clean_title = clean_title.strip()
        
        # Check if title has "Artist - Title" format
        if " - " in clean_title:
            parts = clean_title.split(" - ", 1)
            artist = parts[0].strip()
            song_title = parts[1].strip()
        else:
            artist = channel_name.replace("VEVO", "").replace("Official", "").strip() if channel_name else "Artista Desconocido"
            song_title = clean_title
            
        return {
            "title": song_title,
            "artist": artist,
            "album": f"{song_title} (Single)"
        }
