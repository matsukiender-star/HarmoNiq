#!/usr/bin/env python3
"""Punto de entrada de HarmoNiq: levanta el backend FastAPI en un puerto local
y lo muestra dentro de una ventana Qt con su propio Chromium (QtWebEngine)."""
import os
import sys
import socket
import threading
import time
import traceback
import multiprocessing

# Congelada en Windows, los procesos hijos de multiprocessing re-ejecutan el .exe
# desde el principio. freeze_support() hace que el hijo corra su tarea y salga, en
# vez de re-arrancar toda la app (lo que re-disparaba la descarga de ffmpeg y
# tumbaba el arranque). Debe llamarse lo antes posible.
multiprocessing.freeze_support()


def _ensure_std_streams():
    """Evita el crash 'NoneType has no attribute flush' en Windows.

    Empaquetada en modo ventana (PyInstaller console=False), Windows deja
    sys.stdout y sys.stderr en None. Cualquier print()/flush() posterior revienta
    con AttributeError antes de mostrar la ventana. Se redirigen a un archivo de
    log (o a devnull si no se puede) para que todo funcione y quede registro.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    stream = None
    try:
        if os.name == "nt":
            base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "HarmoNiq")
        else:
            base = os.path.join(os.path.expanduser("~"), ".cache", "HarmoNiq")
        os.makedirs(base, exist_ok=True)
        stream = open(os.path.join(base, "harmoniq.log"), "a", buffering=1, encoding="utf-8")
    except Exception:
        stream = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


_ensure_std_streams()

# --- Entorno previo a cualquier import pesado -------------------------------

FROZEN = getattr(sys, "frozen", False)


def _bundle_dir():
    """Carpeta donde viven los datos empaquetados (o el repo, en desarrollo)."""
    if FROZEN:
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BUNDLE_DIR = _bundle_dir()

# ffmpeg/ffprobe empaquetados junto al ejecutable. Ponerlos primero en el PATH
# evita que static_ffmpeg intente descargarlos en el primer arranque, que es
# lento y falla en equipos sin conexion o detras de un proxy.
os.environ["PATH"] = BUNDLE_DIR + os.pathsep + os.environ.get("PATH", "")

import certifi  # noqa: E402

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import uvicorn  # noqa: E402
import uvicorn.loops.auto  # noqa: E402,F401
import uvicorn.protocols.http.auto  # noqa: E402,F401
import uvicorn.protocols.websockets.auto  # noqa: E402,F401
import websockets  # noqa: E402,F401

from PySide6.QtCore import QUrl, Qt, QObject, Slot, QFile, QIODevice  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PySide6.QtWebEngineCore import QWebEngineScript  # noqa: E402
from PySide6.QtWebChannel import QWebChannel  # noqa: E402

# Se importa el OBJETO app, no la ruta "app.main:app" como string.
# uvicorn.run("app.main:app") obliga a uvicorn a re-importar el modulo por
# nombre en un hilo aparte, y dentro del bundle de PyInstaller esa resolucion
# falla con: 'Error loading ASGI app. Could not import module "app.main"'.
# Pasar el objeto ya importado elimina el problema por completo.
from app.main import app as fastapi_app  # noqa: E402


def restore_host_env():
    """Devuelve el entorno limpio del sistema para procesos hijos.

    El AppRun antepone las librerias del bundle a LD_LIBRARY_PATH. Si un hijo
    (xdg-open, el gestor de archivos, el navegador) hereda eso, carga el
    libssl/libcrypto del bundle y muere con errores tipo
    'version OPENSSL_3.4.0 not found'. Esta funcion da un env seguro para
    subprocess.Popen(..., env=restore_host_env()).
    """
    env = dict(os.environ)
    host = env.pop("HARMONIQ_HOST_LD_LIBRARY_PATH", "")
    if host:
        env["LD_LIBRARY_PATH"] = host
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(port, timeout=30.0):
    """Espera a que el backend acepte conexiones. Devuelve True si arranco."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.15)
    return False


class _NativeBridge(QObject):
    """Puente entre la interfaz web y los diálogos nativos del sistema.

    Se expone a JavaScript vía QWebChannel como `window.hqBackend`. Así el botón
    'Explorar' de la web abre el selector de carpetas NATIVO (Explorador de
    Windows / diálogo de GTK-KDE en Linux) en vez de pedir la ruta a mano.
    """

    def __init__(self, get_parent):
        super().__init__()
        self._get_parent = get_parent

    @Slot(str, result=str)
    def selectDirectory(self, current):
        parent = self._get_parent()
        start = current if current and os.path.isdir(current) else os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            parent, "Selecciona una carpeta", start,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        return path or ""


def _install_native_bridge(view, window):
    """Registra el puente y inyecta qwebchannel.js en la página.

    Es una mejora opcional: si algo falla, la web sigue funcionando y el botón
    'Explorar' cae al prompt de texto. Por eso todo va dentro de try/except.
    """
    try:
        bridge = _NativeBridge(lambda: window)
        channel = QWebChannel(view.page())
        channel.registerObject("backend", bridge)
        view.page().setWebChannel(channel)
        # window guarda referencia para que el GC no se lleve el puente/canal.
        window._hq_bridge = bridge
        window._hq_channel = channel

        qfile = QFile(":/qtwebchannel/qwebchannel.js")
        if not qfile.open(QIODevice.ReadOnly):
            print("[bridge] no se pudo leer qwebchannel.js", file=sys.stderr)
            return
        qwc = bytes(qfile.readAll()).decode("utf-8", "replace")
        qfile.close()

        script = QWebEngineScript()
        script.setSourceCode(qwc + """
            (function () {
                function init() {
                    new QWebChannel(qt.webChannelTransport, function (channel) {
                        window.hqBackend = channel.objects.backend;
                    });
                }
                if (window.qt && qt.webChannelTransport) { init(); }
                else { document.addEventListener('DOMContentLoaded', init); }
            })();
        """)
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(False)
        view.page().scripts().insert(script)
        print("[bridge] selector de carpetas nativo instalado")
    except Exception:
        traceback.print_exc()
        print("[bridge] no se pudo instalar el puente nativo; se usará el prompt", file=sys.stderr)


def main():
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    print("=" * 65)
    print(" HarmoNiq - YouTube MP3 & Shazam Auto-Tagger")
    print("=" * 65)
    print(f" Servidor local: {url}")
    print("=" * 65)
    sys.stdout.flush()

    server_error = []

    def start_server():
        try:
            uvicorn.run(
                fastapi_app,
                host="127.0.0.1",
                port=port,
                log_level="error",
                reload=False,
            )
        except Exception:
            server_error.append(traceback.format_exc())
            traceback.print_exc()

    threading.Thread(target=start_server, daemon=True).start()

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("HarmoNiq")
    qt_app.setDesktopFileName("harmoniq")

    icon_path = os.path.join(BUNDLE_DIR, "app", "static", "images", "harmoniq_icon.png")
    if os.path.exists(icon_path):
        qt_app.setWindowIcon(QIcon(icon_path))

    if not wait_for_server(port):
        detalle = server_error[0] if server_error else "El servidor no respondio a tiempo."
        print(detalle, file=sys.stderr)
        QMessageBox.critical(
            None,
            "HarmoNiq",
            "No se pudo iniciar el servidor interno.\n\n"
            "Detalles en: ~/.cache/HarmoNiq/harmoniq.log",
        )
        return 1

    window = QMainWindow()
    window.setWindowTitle("HarmoNiq - Auto-Tagger")
    window.resize(1200, 820)

    view = QWebEngineView()
    _install_native_bridge(view, window)
    view.load(QUrl(url))
    window.setCentralWidget(view)
    window.show()

    return qt_app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Sin esto, cualquier fallo temprano cierra la app en silencio y el
        # usuario solo ve que "no pasa nada".
        traceback.print_exc()
        sys.stderr.flush()
        sys.exit(1)
