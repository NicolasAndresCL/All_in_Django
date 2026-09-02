# syntax=docker/dockerfile:1
# Imagen de la API Django (perfil producción: gunicorn + WhiteNoise, usuario no-root).
# psycopg[binary] trae wheels precompilados → no hace falta libpq-dev ni compilador.

# ─── Stage 1: dependencias ───────────────────────────────────────────────────
FROM python:3.14-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
WORKDIR /app

# Dependencias instaladas en el stage builder.
COPY --from=builder /install /usr/local

# Código de la aplicación.
COPY . .
RUN chmod +x /app/docker/entrypoint.sh

# collectstatic en build: el gate de core/conf.py exige SECRET_KEY si DEBUG=False,
# así que se usa una clave throwaway solo para este paso (no queda en la imagen final).
RUN SECRET_KEY=build-only DEBUG=True python manage.py collectstatic --noinput

# Usuario no-root. El directorio de metricas multiproceso se crea aqui para que
# pertenezca a 'app': el entrypoint lo vacia en cada arranque y no podria hacerlo si
# fuese de root. Va en /tmp, efimero por naturaleza — son datos de un solo ciclo de
# vida del contenedor, no estado que deba sobrevivir.
RUN mkdir -p /tmp/prometheus \
    && useradd --create-home --uid 1000 app \
    && chown -R app:app /app /tmp/prometheus
USER app

EXPOSE 8000

# Readiness real (/healthz/ hace SELECT 1), no "el proceso sigue vivo". Vive en la IMAGEN
# y no en el compose: asi la hereda cualquier `docker run` del artefacto de GHCR y existe
# una sola definicion de "sano" (antes estaba duplicada en los dos docker-compose).
# La imagen slim no trae curl -> urllib.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6     CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz/',timeout=3).status==200 else 1)"]

# migrate + gunicorn (ver docker/entrypoint.sh).
ENTRYPOINT ["/app/docker/entrypoint.sh"]
