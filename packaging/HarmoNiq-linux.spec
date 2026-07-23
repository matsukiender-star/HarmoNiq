# -*- mode: python ; coding: utf-8 -*-
#
# Spec de Linux para HarmoNiq. A diferencia del HarmoNiq.spec original, este
# genera un bundle "onedir" en vez de "onefile".
#
# Por que onedir: el modo onefile descomprime ~270 MB a /tmp en CADA arranque
# (10-15 s de espera con la pantalla en negro) y, sobre todo, rompe a
# QtWebEngine, que necesita rutas estables para lanzar QtWebEngineProcess.
# Dentro de un AppImage el onedir ya viene "montado", asi que el arranque es
# inmediato y QtWebEngine encuentra sus recursos.

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# PyInstaller resuelve las rutas del spec relativas a la carpeta del propio
# spec (packaging/), no al cwd. Como este spec vive en un subdirectorio, todo
# se ancla explicitamente a la raiz del proyecto.
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

datas = [
    (os.path.join(ROOT, 'app/templates'), 'app/templates'),
    (os.path.join(ROOT, 'app/static'), 'app/static'),
]
binaries = []
hiddenimports = [
    # uvicorn resuelve estos por nombre en runtime, PyInstaller no los ve solo.
    'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto', 'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan.on', 'uvicorn.lifespan.off',
    'app.main', 'app.services.downloader', 'app.services.file_manager',
    'app.services.shazam_service', 'app.services.tagger',
]

for pkg in ('shazamio', 'shazamio_core', 'yt_dlp', 'static_ffmpeg', 'certifi', 'mutagen'):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception as exc:
        print(f'[spec] aviso: no se pudo recolectar {pkg}: {exc}')

# ffmpeg/ffprobe precargados por el build script (ver build_appimage.sh).
# Se meten en el bundle para que la app NO tenga que descargarlos en el primer
# arranque: en una Mint recien instalada esa descarga se cuelga o falla y la
# app se queda "sin hacer nada".
for _tool in ('ffmpeg', 'ffprobe'):
    _p = os.path.join(ROOT, 'vendor', _tool)
    if os.path.exists(_p):
        binaries.append((_p, '.'))
    else:
        print(f'[spec] aviso: falta vendor/{_tool}, se dependera de descarga en runtime')

a = Analysis(
    [os.path.join(ROOT, 'run.py')],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Modulos Qt pesados que no se usan. Recortan ~150 MB del AppImage.
        'PySide6.QtQuick3D', 'PySide6.Qt3DCore', 'PySide6.Qt3DRender',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtBluetooth',
        'PySide6.QtNfc', 'PySide6.QtSerialPort', 'PySide6.QtDesigner',
        'PySide6.QtHelp', 'PySide6.QtTest', 'PySide6.QtSql', 'PySide6.QtMultimedia',
        'tkinter', 'matplotlib', 'PyQt5', 'PyQt6',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # <- onedir
    name='HarmoNiq',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX corrompe las .so de Qt/Chromium
    console=True,            # deja stderr util; el AppRun lo redirige a un log
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='HarmoNiq',
)
