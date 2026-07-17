# syntax=docker/dockerfile:1
# Imagen de la UI NiceGUI (cliente HTTP puro de la API; no toca el ORM).
# Habla con la API por la URL del env API_BASE (p. ej. http://api:8000/api en Compose)
# y envía Authorization: Token API_TOKEN (la API exige autenticación).
#
# El código se importa CUALIFICADO (nicegui_ui.*), así que se copia como paquete bajo
# /app/nicegui_ui y se arranca con `python -m nicegui_ui.main` (PYTHONPATH=/app).

FROM python:3.14-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.14-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app UI_HEADLESS=1
WORKDIR /app

COPY --from=builder /install /usr/local
# El contexto de build es ./nicegui_ui; se copia como paquete importable.
COPY . /app/nicegui_ui/

RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8501

CMD ["python", "-m", "nicegui_ui.main"]
