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
Descarga `HarmoNiq-x86_64.AppImage`, dale permisos de ejecución y ejecútalo:
```bash
chmod +x HarmoNiq-x86_64.AppImage
./HarmoNiq-x86_64.AppImage
```

Compatible con **Linux Mint 21 y 22, Ubuntu 22.04+, Debian 12+, Fedora 36+** y
derivadas. No requiere instalar Python, Qt ni ffmpeg: todo va dentro.

**Si no abre**, ejecútalo desde una terminal con `HARMONIQ_DEBUG=1` para ver el
error, o revisa el registro en `~/.cache/HarmoNiq/harmoniq.log`:
```bash
HARMONIQ_DEBUG=1 ./HarmoNiq-x86_64.AppImage
```
En equipos con tarjetas gráficas viejas o dentro de una máquina virtual, si la
ventana sale en negro, forzá el renderizado por software:
```bash
HARMONIQ_SOFTWARE_GL=1 ./HarmoNiq-x86_64.AppImage
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

### Compilar el AppImage de Linux

```bash
./packaging/build_appimage.sh          # usa podman; ENGINE=docker para Docker
```

Genera `releases/HarmoNiq-x86_64.AppImage` y verifica su compatibilidad al final.

**El build se hace dentro de un contenedor Ubuntu 22.04 a propósito.** Un binario
de Linux se enlaza contra la glibc de la máquina donde se compiló y solo corre en
sistemas con esa versión **o más nueva**. Compilarlo en Fedora/Nobara (glibc 2.43)
o en la imagen `python:3.12` (Debian trixie, glibc 2.41) produce un AppImage que
funciona en tu equipo y **no arranca en Linux Mint** (glibc 2.35 / 2.39): el
enlazador aborta antes de ejecutar una sola línea, sin mostrar ningún mensaje.
Ubuntu 22.04 es el mínimo común razonable hoy.

Antes de publicar una release, comprobá el resultado:
```bash
./packaging/check_compat.sh releases/HarmoNiq-x86_64.AppImage
```

Otros detalles del empaquetado que importan (ver comentarios en `packaging/`):

* Se usa **onedir** en vez de onefile: onefile descomprime ~270 MB a `/tmp` en
  cada arranque y rompe a QtWebEngine, que necesita rutas estables.
* El AppRun **desactiva el sandbox de Chromium**, que no puede inicializarse
  dentro de un AppImage en Ubuntu 24.04 / Mint 22 (AppArmor bloquea los user
  namespaces sin privilegios).
* **No se empaquetan** `libGL`, `libEGL`, `libdrm`, `libgbm`, `libX11` ni
  `libxcb`: son la mitad de usuario del driver de video y tienen que venir del
  equipo del usuario.
* `libstdc++` viaja aparte en `usr/optional/` y el AppRun elige entre la del
  sistema y la del bundle según cuál sea más nueva.
* `ffmpeg` y `ffprobe` van incluidos, así la app no necesita descargarlos en el
  primer arranque.

### Compilar el ejecutable de Windows
```bash
pyinstaller HarmoNiq.spec --clean -y
```
