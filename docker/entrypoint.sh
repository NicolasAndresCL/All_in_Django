#!/bin/sh
# Entrypoint de la API: aplica migraciones y arranca gunicorn.
# Espeja el arranque imperativo de nicegui_ui/run_ui.py (migrate + servir),
# pero de forma declarativa dentro del contenedor.
set -e

# Metricas entre procesos: con varios workers cada uno cuenta por su cuenta y un scrape
# devolveria solo los numeros de uno. prometheus_client agrega entre procesos si existe
# PROMETHEUS_MULTIPROC_DIR (ver docker/gunicorn.conf.py).
#
# El directorio se VACIA en cada arranque: los ficheros de la ejecucion anterior se
# sumarian a los de ahora y los contadores apareceran inflados desde el primer segundo.
#
# OJO: se borra el CONTENIDO, no el directorio. En Kubernetes el chart monta ahi un
# emptyDir, y `rm -rf` sobre un punto de montaje falla con "Resource busy"; con `set -e`
# eso es un CrashLoopBackOff en el arranque. Comprobado:
#   docker run --rm -v v:/tmp/prometheus alpine rm -rf /tmp/prometheus
#   -> rm: can't remove '/tmp/prometheus': Resource busy
# `find -mindepth 1 -delete` funciona igual sea un directorio normal o un montaje.
if [ -n "${PROMETHEUS_MULTIPROC_DIR}" ]; then
    echo "[entrypoint] Limpiando ${PROMETHEUS_MULTIPROC_DIR} para las metricas multiproceso..."
    mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"
    find "${PROMETHEUS_MULTIPROC_DIR}" -mindepth 1 -delete
fi

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

# Tabla del cache de base de datos (DatabaseCache). La migracion 0001_cache_table de
# apps/extras ya la crea, pero el comando es idempotente y cubre el caso de desplegar
# contra una base preexistente cuyo historial de migraciones no la incluya. El cache es
# donde viven los contadores de throttling: si la tabla falta, el rate limiting revienta.
echo "[entrypoint] Asegurando la tabla del cache..."
python manage.py createcachetable

echo "[entrypoint] Iniciando gunicorn en 0.0.0.0:8000..."
# La config vive en un archivo (docker/gunicorn.conf.py) y no en banderas: el hook
# child_exit que las metricas necesitan no se puede expresar en la linea de comandos.
exec gunicorn config.wsgi:application --config /app/docker/gunicorn.conf.py
