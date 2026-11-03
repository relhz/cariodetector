"""Arranque automático del dashboard Streamlit junto a la aplicación Tkinter."""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

APP = Path(__file__).resolve().parent / "app.py"
BASE_DIR = APP.parent.parent


def _puerto_libre(desde=8501, hasta=8600):
    for puerto in range(desde, hasta + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", puerto))
            except OSError:
                continue
            return puerto
    raise RuntimeError(f"No hay puertos libres entre {desde} y {hasta}")


def _esperar(puerto, proceso, timeout=40):
    url = f"http://127.0.0.1:{puerto}/_stcore/health"
    limite = time.time() + timeout

    while time.time() < limite:
        if proceso.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as respuesta:
                if respuesta.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.4)

    return False


def iniciar_dashboard(abrir_navegador=True, timeout=40):
    """Lanza Streamlit en un puerto libre. Devuelve el proceso o None si falla.

    El dashboard se ejecuta como proceso aparte para no bloquear Tkinter. Si
    Streamlit no está instalado, devuelve None y la aplicación sigue funcionando.
    """
    if not APP.exists():
        print(f"[dashboard] No se encontró {APP}")
        return None

    try:
        puerto = _puerto_libre()
    except RuntimeError as error:
        print(f"[dashboard] {error}")
        return None

    comando = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(puerto),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    entorno = {**os.environ, "STREAMLIT_SERVER_HEADLESS": "true"}
    try:
        proceso = subprocess.Popen(
            comando,
            cwd=str(BASE_DIR),
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print("[dashboard] Streamlit no está instalado; se inicia solo la interfaz Tkinter.")
        return None

    if not _esperar(puerto, proceso, timeout=timeout):
        print("[dashboard] Streamlit no respondió a tiempo; se detiene.")
        detener_dashboard(proceso)
        return None

    url = f"http://127.0.0.1:{puerto}"
    print(f"[dashboard] Disponible en {url}")
    if abrir_navegador:
        webbrowser.open(url)

    return proceso


def detener_dashboard(proceso):
    """Cierra el proceso del dashboard si sigue vivo."""
    if proceso is None or proceso.poll() is not None:
        return

    proceso.terminate()
    try:
        proceso.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=5)
