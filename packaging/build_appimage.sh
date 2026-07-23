#!/usr/bin/env bash
# Construye HarmoNiq-x86_64.AppImage dentro de un contenedor Ubuntu 22.04.
#
# Uso:   ./packaging/build_appimage.sh
# Salida: releases/HarmoNiq-x86_64.AppImage
#
# El build NO se hace en el sistema anfitrion a proposito. Compilar en Nobara
# (glibc 2.43) o en la imagen python:3.12 (Debian trixie, glibc 2.41) produce
# un binario que no arranca en Linux Mint 21 (glibc 2.35) ni Mint 22 (2.39):
# el enlazador dinamico aborta antes de ejecutar una sola linea, sin mensaje.
# Ubuntu 22.04 es el minimo comun que cubre todo lo que la gente usa hoy.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

ENGINE="${ENGINE:-podman}"
IMAGE="harmoniq-build:ubuntu2204"

command -v "${ENGINE}" >/dev/null || { echo "Falta ${ENGINE}"; exit 1; }

echo ">> [1/4] Construyendo imagen de build (Ubuntu 22.04 / glibc 2.35)..."
"${ENGINE}" build -t "${IMAGE}" -f packaging/Containerfile packaging/

echo ">> [2/4] Compilando con PyInstaller dentro del contenedor..."
"${ENGINE}" run --rm \
    -v "${PROJECT_DIR}":/src:z \
    -w /src \
    "${IMAGE}" \
    bash -euxo pipefail -c '
        pip install --no-cache-dir \
            PySide6 fastapi uvicorn shazamio mutagen aiohttp python-multipart \
            websockets aiofiles static-ffmpeg jinja2 yt-dlp certifi pyinstaller

        # ffmpeg estatico, para no depender de descargas en el primer arranque.
        mkdir -p vendor
        if [ ! -x vendor/ffmpeg ]; then
            curl -fsSL -o /tmp/ff.tar.xz \
                https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
            mkdir -p /tmp/ff && tar -xJf /tmp/ff.tar.xz -C /tmp/ff --strip-components=1
            cp /tmp/ff/ffmpeg /tmp/ff/ffprobe vendor/
            chmod +x vendor/ffmpeg vendor/ffprobe
        fi

        rm -rf build dist
        pyinstaller packaging/HarmoNiq-linux.spec --clean -y --distpath dist --workpath build
        chmod -R a+rX dist
    '

echo ">> [3/4] Armando el AppDir..."
rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/icons/hicolor/256x256/apps AppDir/usr/share/applications

cp -a dist/HarmoNiq AppDir/usr/bin/HarmoNiq
chmod +x AppDir/usr/bin/HarmoNiq/HarmoNiq

# --- Purga de librerias que NUNCA deben viajar dentro de un AppImage --------
# libGL/libEGL/libdrm/libgbm son la mitad de usuario del driver de video: van
# emparejadas con el kernel y la GPU de CADA maquina. Si se empaquetan, quedan
# antes que las del sistema en LD_LIBRARY_PATH y Chromium muere con
#   "ANGLE Display::initialize error 12289: Failed to get system egl display"
# seguido de un abort, sin ventana. Lo mismo con libwayland y libX11.
# Al borrarlas, el enlazador usa las del equipo del usuario, que si funcionan.
PRUNE_DIR="AppDir/usr/bin/HarmoNiq/_internal"
for pat in \
    'libGL.so*' 'libEGL.so*' 'libGLX.so*' 'libGLdispatch.so*' 'libOpenGL.so*' \
    'libGLESv2.so*' 'libglapi.so*' 'libgbm.so*' 'libdrm.so*' \
    'libwayland-client.so*' 'libwayland-server.so*' 'libwayland-egl.so*' \
    'libwayland-cursor.so*' 'libX11.so*' 'libX11-xcb.so*' 'libxcb.so*' \
    'libxcb-dri2.so*' 'libxcb-dri3.so*' 'libxcb-glx.so*' 'libxcb-present.so*' \
    'libxcb-sync.so*' 'libxshmfence.so*' 'libnvidia*' 'libcuda*' \
    'libasound.so*' 'libpulse*'
do
    find "${PRUNE_DIR}" -maxdepth 2 -name "${pat}" -delete 2>/dev/null || true
done

# libstdc++ y libgcc no se borran, se apartan: si el sistema del usuario es mas
# viejo que el contenedor de build, hacen falta. Pero si se dejan en el PATH de
# librerias tapan la del sistema y rompen los drivers de video:
#   "libstdc++.so.6: version GLIBCXX_3.4.32 not found (required by libSPIRV-Tools.so)"
# El AppRun compara versiones en arranque y decide cual usar.
mkdir -p AppDir/usr/optional
for lib in libstdc++.so.6 libgcc_s.so.1; do
    if [ -f "${PRUNE_DIR}/${lib}" ]; then
        mv "${PRUNE_DIR}/${lib}" "AppDir/usr/optional/${lib}"
    fi
done

install -m 755 packaging/AppRun AppDir/AppRun

ICON_SRC="app/static/images/harmoniq_icon.png"
if [ -f "${ICON_SRC}" ]; then
    cp "${ICON_SRC}" AppDir/harmoniq.png
    cp "${ICON_SRC}" AppDir/usr/share/icons/hicolor/256x256/apps/harmoniq.png
    cp "${ICON_SRC}" AppDir/.DirIcon
fi

cat > AppDir/harmoniq.desktop << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=HarmoNiq
GenericName=YouTube MP3 Downloader
Comment=Descarga musica de YouTube con etiquetado automatico por Shazam
Exec=AppRun %U
Icon=harmoniq
Terminal=false
Categories=AudioVideo;Audio;Music;
Keywords=youtube;mp3;music;shazam;download;
StartupNotify=true
StartupWMClass=harmoniq
DESKTOP
cp AppDir/harmoniq.desktop AppDir/usr/share/applications/harmoniq.desktop

echo ">> [4/4] Empaquetando el AppImage..."
TOOL="packaging/.cache/appimagetool"
mkdir -p packaging/.cache
if [ ! -x "${TOOL}" ]; then
    curl -fsSL -o "${TOOL}" \
        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "${TOOL}"
fi

mkdir -p releases
# --appimage-extract-and-run evita necesitar FUSE en la maquina de build.
ARCH=x86_64 "${TOOL}" --appimage-extract-and-run AppDir releases/HarmoNiq-x86_64.AppImage

echo
echo "OK -> releases/HarmoNiq-x86_64.AppImage ($(du -h releases/HarmoNiq-x86_64.AppImage | cut -f1))"
echo "Comprobacion de compatibilidad:"
bash packaging/check_compat.sh releases/HarmoNiq-x86_64.AppImage || true
