# 🎵 HarmoNiq

<div align="center">
  <h1>🎵 HarmoNiq</h1>
  <p><strong>A modern, elegant desktop application for downloading and auto-tagging YouTube music.</strong></p>
</div>

## 🌟 Descripción

**HarmoNiq** es una herramienta potente y fácil de usar diseñada para descargar música (MP3) directamente desde YouTube o listas de reproducción de forma rápida. Lo que hace único a HarmoNiq es su integración nativa con **Shazam**, la cual identifica las canciones mientras se descargan y automáticamente aplica las etiquetas ID3 correctas (Nombre del Artista, Título de la Canción, Álbum y Carátula Oficial).

Olvídate de tener archivos llamados `videoclip_oficial_lyrics_2024.mp3` sin portada. ¡HarmoNiq organiza tu música para que se vea perfecta en cualquier reproductor!

## ✨ Características Principales

* 📥 **Descarga Individual y de Playlists:** Descarga un solo video o una lista de reproducción entera de YouTube.
* 🎧 **Auto-Etiquetado con Shazam (ID3):** Analiza acústicamente el audio descargado para encontrar la metadata real de la canción y añade la carátula oficial de alta calidad.
* 🎨 **Diseño Moderno y Responsivo:** Interfaz construida con tecnologías web dentro de una app de escritorio nativa usando PySide6 y FastAPI, brindando animaciones fluidas y soporte para modo oscuro.
* ✏️ **Editor de Metadatos Manual:** Si Shazam no encuentra la canción, puedes editar fácilmente el título, artista y agregar una imagen manualmente antes de guardarla.
* 🚀 **Multiplataforma:** Disponible para Windows y Linux.

## 🛠️ Tecnologías

* **Python 3.12**
* **PySide6 / PyQt** (Para el renderizado de la ventana nativa y WebEngine)
* **FastAPI & Uvicorn** (Servidor backend local)
* **yt-dlp** (Motor principal de descargas)
* **shazamio** (Reconocimiento acústico de canciones)
* **mutagen** (Manipulación de etiquetas de audio)
* **Vanilla HTML/CSS/JS** (Interfaz de usuario moderna y estilizada)

## 📦 Instalación

Ve a la pestaña de **Releases** para descargar la versión compilada más reciente:

### Para Windows
Descarga el archivo `HarmoNiq-Windows-x86_64.exe` y ejecútalo. (Puede que Windows Defender lance una advertencia de "Editor desconocido", simplemente dale a "Más información" -> "Ejecutar de todas formas").

### Para Linux
Descarga el archivo `HarmoNiq-Linux-x86_64`, dale permisos de ejecución y ejecútalo:
```bash
chmod +x HarmoNiq-Linux-x86_64
./HarmoNiq-Linux-x86_64
```

## 🚀 Compilar desde el código fuente

Si prefieres ejecutar o compilar el programa tú mismo:

```bash
# 1. Clona el repositorio
git clone https://github.com/tu-usuario/HarmoNiq.git
cd HarmoNiq

# 2. Instala las dependencias
pip install -r requirements.txt

# 3. Ejecuta el modo desarrollador
python app/main.py
```

Para generar tu propio binario ejecutable con PyInstaller:
```bash
pyinstaller HarmoNiq.spec --clean -y
```
