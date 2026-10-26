"""Comprueba compose.traefik.yml sobre la salida de `docker compose config --format json`.

Lo usan el job `compose-traefik` del CI y el paso 3c de scripts/verificar.ps1, asi que "el
override esta bien" tiene UNA sola definicion y el job y el script local no pueden divergir.
Lee el JSON por stdin:

    docker compose --env-file <env> -f docker-compose.deploy.yml -f compose.traefik.yml \
        config --format json | python scripts/comprobar_override_traefik.py

Sale con 1 y dice que fallo. Salida en ASCII (la consola de Windows es cp1252).
"""

import json
import sys

# Solo la UI toca la red de Traefik: la API (con /admin/ y /api/token/) y Postgres no son
# alcanzables desde fuera. Si otro servicio entra aqui, queda publicado por el dominio.
EN_RED_DE_TRAEFIK = ["ui"]


def revisar(cfg: dict) -> list[str]:
    """Devuelve los incumplimientos del override (lista vacia = esta bien)."""
    servicios = cfg["services"]
    errores = []

    for nombre, srv in sorted(servicios.items()):
        if srv.get("ports"):
            errores.append(f"{nombre} publica puertos en el host (Docker se salta el firewall): {srv['ports']}")
        if not srv.get("mem_limit"):
            errores.append(f"{nombre} sin mem_limit (el VPS es compartido)")

    en_traefik = sorted(n for n, s in servicios.items() if "traefik" in s.get("networks", {}))
    if en_traefik != EN_RED_DE_TRAEFIK:
        errores.append(f"en la red de Traefik debe estar solo {EN_RED_DE_TRAEFIK} y hay {en_traefik}")

    env_api = servicios["api"].get("environment", {})
    # Con SECURE_HTTPS=True la UI (que llama a http://api:8000) recibe un 301 a https://api:8000
    # y se queda sin API: el valor por defecto del override tiene que seguir siendo False.
    if env_api.get("SECURE_HTTPS") != "False":
        errores.append(f"SECURE_HTTPS por defecto debe ser 'False' y es {env_api.get('SECURE_HTTPS')!r}")
    # API_TOKEN es de la UI. Si aparece en la API, el `env_file: .env.docker` del compose base
    # sigue aplicandose (el override debe anularlo con `!reset`).
    if "API_TOKEN" in env_api:
        errores.append("la API recibe API_TOKEN: el override ya no anula el env_file del compose base")

    return errores


def main() -> int:
    # Bytes + utf-8-sig: el pipe de PowerShell 5.1 hacia un programa nativo antepone un BOM
    # (segun $OutputEncoding) y json.load lo rechaza. En el runner Linux no hay BOM y da igual.
    errores = revisar(json.loads(sys.stdin.buffer.read().decode("utf-8-sig")))
    for error in errores:
        print(f"FALLO: {error}")
    if not errores:
        print("OK: sin puertos publicados, solo la ui en la red de Traefik, todos con mem_limit")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
