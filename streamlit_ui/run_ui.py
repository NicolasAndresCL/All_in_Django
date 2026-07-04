"""
run_ui.py — Orquesta el arranque completo de la UI: API Django + Streamlit.

Flujo:
  1. Si la API no responde ya, aplica migraciones y levanta `manage.py runserver`
     (como subproceso) y espera a que conteste.
  2. Elige el puerto de la UI: 8501 o, si está ocupado, el siguiente libre.
  3. Lanza Streamlit apuntando a esa API (API_BASE).
  4. Al cerrar la UI, detiene la API que este script haya levantado.

Así la UI nunca arranca "antes" que la API y se evita el error de conexión.
Variables de entorno: UI_PORT (base UI), API_HOST, API_PORT, API_BASE.

Uso:
    python run_ui.py          # con el env activado (o vía run_app.bat)
"""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]   # carpeta que contiene manage.py
MANAGE = RAIZ / "manage.py"

UI_PUERTO_BASE = int(os.environ.get("UI_PORT", "8501"))
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
MAX_INTENTOS_PUERTO = 100


# ─── puertos ──────────────────────────────────────────────────────────────────
def puerto_libre(puerto: int, host: str = "") -> bool:
    """True si `puerto` se puede abrir (host \"\" = todas las interfaces, como Streamlit).

    Sin SO_REUSEADDR a propósito: en Windows esa opción deja "robar" un puerto ya en
    uso y lo reportaría como libre; sin ella, el bind falla si está ocupado.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, puerto))
            return True
        except OSError:
            return False


def encontrar_puerto(base: int = UI_PUERTO_BASE) -> int:
    """Primer puerto libre desde `base`; si ninguno lo está, devuelve `base` igualmente."""
    for puerto in range(base, base + MAX_INTENTOS_PUERTO):
        if puerto_libre(puerto):
            return puerto
    return base  # último recurso: que Streamlit intente y reporte el error


# ─── API Django ───────────────────────────────────────────────────────────────
def api_responde(url: str, timeout: float = 2.0) -> bool:
    """True si `url` contesta con un status < 500 (la API está viva)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500          # 403/404 = servidor vivo
    except Exception:
        return False


def esperar_api(url: str, intentos: int = 40, espera: float = 0.5) -> bool:
    """Sondea `url` hasta que responda o se agoten los intentos (~20 s por defecto)."""
    for _ in range(intentos):
        if api_responde(url):
            return True
        time.sleep(espera)
    return False


def arrancar_api():
    """Levanta la API si no está ya arriba. Devuelve el proceso creado o None."""
    base = f"http://{API_HOST}:{API_PORT}"
    health = f"{base}/api/"
    if api_responde(health):
        print(f"[API] Ya responde en {base}; se reutiliza.")
        return None

    print("[API] Aplicando migraciones...")
    subprocess.run([sys.executable, str(MANAGE), "migrate", "--noinput"], cwd=str(RAIZ))

    print(f"[API] Levantando Django en {base} ...")
    proc = subprocess.Popen(
        [sys.executable, str(MANAGE), "runserver", f"{API_HOST}:{API_PORT}", "--noreload"],
        cwd=str(RAIZ),
    )
    if esperar_api(health):
        print("[API] Lista.")
    else:
        print("[API] ADVERTENCIA: no respondio a tiempo; la UI podria mostrar error de conexion.")
    return proc


# ─── orquestacion ─────────────────────────────────────────────────────────────
def main() -> int:
    # La UI apunta por defecto a la misma API que levantamos aqui.
    os.environ.setdefault("API_BASE", f"http://{API_HOST}:{API_PORT}/api")

    api_proc = arrancar_api()
    try:
        puerto = encontrar_puerto()
        if puerto != UI_PUERTO_BASE:
            print(f"[UI] Puerto {UI_PUERTO_BASE} ocupado; usando el {puerto}.")
        else:
            print(f"[UI] Usando el puerto {puerto}.")

        app = Path(__file__).with_name("app.py")
        cmd = [
            sys.executable, "-m", "streamlit", "run", str(app),
            "--server.port", str(puerto),
        ]
        return subprocess.run(cmd).returncode
    finally:
        if api_proc is not None:
            print("[API] Deteniendo Django...")
            api_proc.terminate()
            try:
                api_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
