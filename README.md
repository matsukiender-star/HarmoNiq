<div align="center">
  <img src="app/static/images/harmoniq_icon.png" alt="HarmoNiq" width="128" height="128">

  <h1>🎵 HarmoNiq</h1>

  <p><strong>Descarga música de YouTube y etiquétala automáticamente con Shazam.</strong></p>

  <p>
    <img alt="Plataformas" src="https://img.shields.io/badge/plataformas-Windows%20%7C%20Linux-blue">
    <img alt="Python" src="https://img.shields.io/badge/python-3.12-yellow">
    <a href="https://github.com/matsukiender-star/HarmoNiq/actions/workflows/build.yml">
      <img alt="Build" src="https://github.com/matsukiender-star/HarmoNiq/actions/workflows/build.yml/badge.svg">
    </a>
    <a href="https://github.com/matsukiender-star/HarmoNiq/releases">
      <img alt="Release" src="https://img.shields.io/github/v/release/matsukiender-star/HarmoNiq?include_prereleases">
    </a>
  </p>
</div>

---

## 🌟 ¿Qué es HarmoNiq?

**HarmoNiq** descarga música (MP3) desde YouTube — un video o una playlist entera — y, mientras descarga, **identifica cada canción con Shazam** para aplicarle automáticamente las etiquetas ID3 correctas: **artista, título, álbum y la carátula oficial en alta calidad**.

Olvídate de archivos como `videoclip_oficial_lyrics_2024.mp3` sin portada. HarmoNiq deja tu música lista y ordenada para que se vea perfecta en cualquier reproductor.

## ✨ Características

- 📥 **Descarga individual y de playlists** — un video o una lista completa de YouTube.
- 🎧 **Auto-etiquetado con Shazam** — reconocimiento acústico del audio para obtener la metadata real y la carátula oficial.
- ✏️ **Editor manual de metadatos** — si Shazam no encuentra la canción, editas título, artista y portada a mano antes de guardar.
- 🎨 **Interfaz moderna** — construida con tecnologías web dentro de una ventana nativa (PySide6 + FastAPI), con animaciones fluidas y modo oscuro.
- 📂 **Carpeta de música inteligente** — detecta tu carpeta de música del sistema automáticamente (Windows y Linux).
- 🚀 **Multiplataforma y portable** — un solo archivo para Windows y para Linux. No necesitas instalar Python, Qt ni ffmpeg: todo va dentro.

## 📦 Descarga e instalación

Ve a la pestaña **[Releases](https://github.com/matsukiender-star/HarmoNiq/releases)** y descarga la última versión.

### 🪟 Windows

1. Descarga `HarmoNiq-Windows-x86_64.zip`.
2. Descomprímelo en una carpeta.
3. Ejecuta **`HarmoNiq.exe`**.

> Windows Defender puede mostrar "Editor desconocido". Haz clic en **Más información → Ejecutar de todas formas** (la app no está firmada digitalmente, pero es segura).

### 🐧 Linux

Descarga `HarmoNiq-x86_64.AppImage`, dale permisos y ejecútalo:

```bash
chmod +x HarmoNiq-x86_64.AppImage
./HarmoNiq-x86_64.AppImage
```

Compatible con **Linux Mint 21/22, Ubuntu 22.04+, Debian 12+, Fedora 36+** y derivadas.

## 🎮 Cómo se usa

1. Abre HarmoNiq.
2. Pega la **URL de un video o playlist** de YouTube.
3. (Opcional) Elige la carpeta de destino y el patrón de nombres.
4. Dale a **Descargar**. HarmoNiq baja el audio, lo identifica con Shazam y le pone artista, título, álbum y carátula.
5. Si alguna canción no se reconoce, usa el **editor manual** para completarla.

## 🩺 Solución de problemas

**La app no abre (Linux).** Ejecútala desde una terminal para ver el error:
```bash
HARMONIQ_DEBUG=1 ./HarmoNiq-x86_64.AppImage
```
O revisa el registro en `~/.cache/HarmoNiq/harmoniq.log`.

**La ventana sale en negro** (tarjetas gráficas viejas o máquina virtual). Fuerza el renderizado por software:
```bash
HARMONIQ_SOFTWARE_GL=1 ./HarmoNiq-x86_64.AppImage
```

**Una descarga se queda "sin hacer nada".** Suele ser un problema de red al contactar YouTube o Shazam. Revisa tu conexión y vuelve a intentar.

Más detalles en la **[Wiki → Troubleshooting](https://github.com/matsukiender-star/HarmoNiq/wiki)**.

## 🛠️ Tecnologías

| Componente | Uso |
|---|---|
| **Python 3.12** | Lenguaje base |
| **PySide6 (Qt WebEngine)** | Ventana nativa que renderiza la interfaz web |
| **FastAPI + Uvicorn** | Servidor backend local |
| **yt-dlp** | Motor de descargas de YouTube |
| **shazamio** | Reconocimiento acústico de canciones |
| **mutagen** | Escritura de etiquetas ID3 |
| **HTML/CSS/JS** | Interfaz de usuario |
| **PyInstaller** | Empaquetado del ejecutable |

## 🚀 Compilar desde el código fuente

### Modo desarrollo

```bash
git clone https://github.com/matsukiender-star/HarmoNiq.git
cd HarmoNiq
pip install -r requirements.txt
python run.py
```

### AppImage de Linux

```bash
./packaging/build_appimage.sh          # usa podman; ENGINE=docker para Docker
```

Genera `releases/HarmoNiq-x86_64.AppImage` y verifica su compatibilidad al final.

> **El build se hace dentro de un contenedor Ubuntu 22.04 a propósito.** Un binario de Linux se enlaza contra la glibc de la máquina donde se compiló y solo corre en sistemas con esa versión **o más nueva**. Compilarlo en Fedora/Nobara (glibc 2.43) produce un AppImage que **no arranca en Linux Mint** (glibc 2.35/2.39): el enlazador aborta sin mostrar ningún mensaje. Ubuntu 22.04 es el mínimo común razonable hoy.

Comprueba el resultado antes de publicar:
```bash
./packaging/check_compat.sh releases/HarmoNiq-x86_64.AppImage
```

### Ejecutable de Windows

```bash
pyinstaller HarmoNiq.spec --clean -y
```

Genera la carpeta `dist/HarmoNiq/` con `HarmoNiq.exe` dentro. **Debe compilarse en Windows** (PyInstaller no hace cross-compile desde Linux).

### Builds automáticos (CI)

Cada push de un tag `v*` dispara **[GitHub Actions](https://github.com/matsukiender-star/HarmoNiq/actions)**, que compila el AppImage de Linux y el `.exe` de Windows en máquinas reales y publica un Release con ambos. También puedes lanzarlo manualmente desde la pestaña Actions (**Run workflow**).

## 🔧 Notas técnicas del empaquetado

Detalles que importan (ver comentarios en `packaging/` y en los `.spec`):

- Se usa **onedir**, no onefile: onefile descomprime ~270 MB a un temporal en cada arranque y **rompe a QtWebEngine**, que necesita rutas estables para lanzar `QtWebEngineProcess`.
- **UPX desactivado**: corrompe las DLL/`.so` de Qt/Chromium y dispara falsos positivos de antivirus.
- En Linux, el AppRun **desactiva el sandbox de Chromium** (no puede inicializarse dentro de un AppImage en Ubuntu 24.04 / Mint 22 por AppArmor).
- **No se empaquetan** `libGL`, `libEGL`, `libdrm`, `libgbm`, `libX11` ni `libxcb`: son la mitad de usuario del driver de video y deben venir del equipo del usuario.
- `libstdc++` viaja aparte en `usr/optional/`; el AppRun elige entre la del sistema y la del bundle según cuál sea más nueva.
- `ffmpeg`/`ffprobe` van incluidos para no depender de descargas en el primer arranque.

## 🤝 Contribuir

Los reportes de errores y sugerencias son bienvenidos en **[Issues](https://github.com/matsukiender-star/HarmoNiq/issues)**. Para dudas y conversación general, usa **[Discussions](https://github.com/matsukiender-star/HarmoNiq/discussions)**.

## ⚖️ Aviso legal

HarmoNiq es una herramienta educativa. Descarga solo contenido sobre el que tengas derechos o que sea de dominio público, y respeta los Términos de Servicio de YouTube y las leyes de copyright de tu país.

---

<div align="center">
  <sub>Hecho con 🎵 por <a href="https://github.com/matsukiender-star">matsukiender-star</a></sub>
</div>
