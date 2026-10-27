"""Comprueba compose.traefik.yml sobre la salida de `docker compose config --format json`.

Lo usan el job `compose-traefik` del CI y el paso 3c de scripts/verificar.ps1, asi que "el
override esta bien" tiene UNA sola definicion y el job y el script local no pueden divergir.
Lee el JSON por stdin:

    docker compose --env-file <env> -f docker-compose.deploy.yml -f compose.traefik.yml \
        config --format json | python scripts/comprobar_override_traefik.py

    # con compose.n8n.yml encima (red interna con n8n), ademas:
    ... -f compose.traefik.yml -f compose.n8n.yml config --format json \
        | python scripts/comprobar_override_traefik.py --con-n8n

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


# compose.n8n.yml: la red compartida con n8n lleva SOLO la API, con un alias estable. Si entrara
# Postgres, el worker de n8n podria hablarle directo a la base, saltandose la API y su token.
EN_RED_DE_N8N = ["api"]
ALIAS_N8N = "all-in-django-api"


def revisar_n8n(cfg: dict) -> list[str]:
    """Incumplimientos de compose.n8n.yml aplicado encima (lista vacia = esta bien)."""
    servicios = cfg["services"]
    red = cfg.get("networks", {}).get("n8n")
    if red is None:
        return ["no hay red 'n8n': falta aplicar compose.n8n.yml"]

    errores = []
    if not red.get("external"):
        errores.append("la red 'n8n' debe ser external (se crea una vez con `docker network create --internal`)")
    en_n8n = sorted(n for n, s in servicios.items() if "n8n" in (s.get("networks") or {}))
    if en_n8n != EN_RED_DE_N8N:
        errores.append(f"en la red de n8n debe estar solo {EN_RED_DE_N8N} y hay {en_n8n}")
    alias = ((servicios["api"].get("networks") or {}).get("n8n") or {}).get("aliases") or []
    if ALIAS_N8N not in alias:
        errores.append(f"la api no tiene el alias {ALIAS_N8N!r} en la red de n8n (lo usan los workflows)")
    hosts = servicios["api"].get("environment", {}).get("ALLOWED_HOSTS", "")
    if ALIAS_N8N not in hosts.split(","):
        errores.append(f"ALLOWED_HOSTS no incluye {ALIAS_N8N!r}: Django responderia 400 a n8n")
    # El override de n8n no debe deshacer lo del de Traefik.
    if "traefik" in (servicios["api"].get("networks") or {}):
        errores.append("la api quedo en la red de Traefik")
    return errores


def main() -> int:
    con_n8n = "--con-n8n" in sys.argv[1:]
    # Bytes + utf-8-sig: el pipe de PowerShell 5.1 hacia un programa nativo antepone un BOM
    # (segun $OutputEncoding) y json.load lo rechaza. En el runner Linux no hay BOM y da igual.
    cfg = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    errores = revisar(cfg) + (revisar_n8n(cfg) if con_n8n else [])
    for error in errores:
        print(f"FALLO: {error}")
    if not errores:
        print("OK: sin puertos publicados, solo la ui en la red de Traefik, todos con mem_limit"
              + ("; solo la api en la red de n8n, con su alias y en ALLOWED_HOSTS" if con_n8n else ""))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
