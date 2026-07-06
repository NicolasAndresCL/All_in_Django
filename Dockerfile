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
    DJANGO_SETTINGS_MODULE=config.settings
WORKDIR /app

# Dependencias instaladas en el stage builder.
COPY --from=builder /install /usr/local

# Código de la aplicación.
COPY . .
RUN chmod +x /app/docker/entrypoint.sh

# collectstatic en build: el gate de core/conf.py exige SECRET_KEY si DEBUG=False,
# así que se usa una clave throwaway solo para este paso (no queda en la imagen final).
RUN SECRET_KEY=build-only DEBUG=True python manage.py collectstatic --noinput

# Usuario no-root.
RUN useradd --create-home --uid 1000 app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# migrate + gunicorn (ver docker/entrypoint.sh).
ENTRYPOINT ["/app/docker/entrypoint.sh"]
