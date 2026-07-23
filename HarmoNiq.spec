# -*- mode: python ; coding: utf-8 -*-
#
# Spec de Windows para HarmoNiq. Genera un bundle "onedir" (carpeta), NO onefile.
#
# Por que onedir: el modo onefile descomprime ~270 MB a un temporal en CADA
# arranque (arranque lento con ventana en negro) y, sobre todo, rompe a
# QtWebEngine, que necesita rutas estables para lanzar QtWebEngineProcess.exe.
# El resultado (dist/HarmoNiq/) se comprime a un .zip en el workflow de CI.

import os
from PyInstaller.utils.hooks import collect_all

# SPECPATH es la carpeta del propio spec; aqui coincide con la raiz del repo.
ROOT = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(ROOT, 'app', 'templates'), 'app/templates'),
    (os.path.join(ROOT, 'app', 'static'), 'app/static'),
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
        # Modulos Qt pesados que no se usan. Recortan cientos de MB.
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
    upx=False,               # UPX corrompe las DLL de Qt/Chromium y dispara antivirus
    console=False,           # app GUI: sin ventana de consola (CMD)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'packaging', 'harmoniq.ico'),
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
