#!/bin/sh
# Entrypoint de la API: aplica migraciones y arranca gunicorn.
# Espeja el arranque imperativo de nicegui_ui/run_ui.py (migrate + servir),
# pero de forma declarativa dentro del contenedor.
set -e

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

echo "[entrypoint] Iniciando gunicorn en 0.0.0.0:8000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
