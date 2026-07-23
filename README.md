# 🎵 HarmoNiq - YouTube MP3 & Shazam Auto-Tagger

HarmoNiq es una aplicación de escritorio con interfaz web ultra-moderna (Glassmorphic Dark Mode) diseñada para descargar audio de YouTube en formato MP3 (hasta 320 kbps), identificar la canción automáticamente utilizando la API acústica de **Shazam** y escribir los metadatos ID3 completando artista, título, álbum, año, género, letra y portada del álbum en alta definición directamente en el archivo MP3.

---

## 🚀 Características Principales

1. **Descargador de YouTube a MP3 Alta Calidad:**
   - Soporta enlaces de videos individuales, Shorts y Listas de reproducción de YouTube.
   - Selección de bitrate de audio: 320 kbps (Máxima calidad), 256 kbps, 192 kbps, 128 kbps.
   - Progreso en tiempo real con indicador de porcentaje, velocidad de descarga (MB/s) y tiempo restante (ETA).

2. **Reconocimiento Acústico con Shazam:**
   - Analiza la huella digital del audio descargado (o de cualquier MP3 local) usando Shazam.
   - Extrae automáticamente: Título, Artista, Álbum, Año de lanzamiento, Género musical, Portada HD e historia de letras.
   - Alternativa Inteligente (Fallback): Si Shazam no encuentra coincidencias, analiza el título del video de YouTube y limpia etiquetas no deseadas.

3. **Editor de Etiquetas ID3 & Modo Viceversa:**
   - Escribe etiquetas nativas ID3v2 en el archivo `.mp3`.
   - Permite escanear cualquier canción MP3 existente en tu equipo con Shazam para autocompletar su información.
   - Permite la edición manual completa de título, artista, álbum, año, género, letra y sustitución de portada de disco.

4. **Directorio Personalizable por el Usuario:**
   - Guarda los archivos en cualquier ubicación seleccionada de tu PC (por defecto: `~/Música/YouTube_Downloads`).
   - Selección rápida mediante accesos directos (`Música`, `Descargas`, `Escritorio`, `Documentos`).
   - Botón integrado para abrir la carpeta de descargas directamente en el explorador de archivos del sistema.

5. **Reproductor de Audio Integrado:**
   - Escucha las canciones descargadas directamente desde la aplicación con el reproductor interactivo.

---

## 🛠️ Cómo Ejecutar la Aplicación

Puedes iniciar HarmoNiq con un solo comando desde tu terminal:

```bash
cd /home/daetrox/youtube_mp3_shazam
./run.sh
```

La aplicación se iniciará localmente en `http://localhost:8000` y abrirá automáticamente tu navegador web.

---

## 📂 Estructura del Proyecto

```
/home/daetrox/youtube_mp3_shazam/
├── app/
│   ├── main.py               # Servidor FastAPI y WebSockets
│   ├── services/
│   │   ├── downloader.py     # Servicio de descarga con yt-dlp & ffmpeg
│   │   ├── shazam_service.py # Servicio de reconocimiento acústico con shazamio
│   │   ├── tagger.py         # Escritura y lectura de etiquetas ID3 con mutagen
│   │   └── file_manager.py   # Gestión de carpetas personalizables y accesos directos
│   ├── static/               # Estilos CSS, JS y recursos gráficos
│   └── templates/            # Plantilla HTML5 Glassmorphism
├── venv/                     # Entorno virtual con todas las dependencias
├── run.py                    # Script de inicio principal
└── run.sh                    # Ejecutable bash
```
