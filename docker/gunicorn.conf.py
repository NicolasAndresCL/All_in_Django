"""
docker/gunicorn.conf.py — Configuración de gunicorn, con el cableado multiproceso
que necesitan las métricas de Prometheus.

**El problema que resuelve.** Con varios workers, cada proceso tiene sus propios
contadores en memoria. Un scrape a `/metrics` cae en UNO de ellos al azar y devuelve
solo sus números: la mitad del tráfico desaparece del gráfico y nadie ve un error. Es la
misma trampa que ya pagó este proyecto con el rate limiting de DRF, cuyos contadores
viven en un `LocMemCache` por proceso y hacían que el límite real fuese ~3x el
configurado.

**La solución.** `prometheus_client` sabe agregar entre procesos si existe
`PROMETHEUS_MULTIPROC_DIR`: cada worker escribe sus muestras en ficheros de ese
directorio y el exportador los suma al servir. Requiere dos cosas más, que son las que
se olvidan:

1. **Limpiar el directorio al arrancar** (lo hace el entrypoint). Si quedan ficheros de
   una ejecución anterior, sus valores se suman a los de ahora y los contadores
   aparecen inflados desde el primer segundo.
2. **Avisar de cada worker que muere** (`child_exit`, aquí abajo). Sin esto, los
   ficheros de un worker reiniciado siguen contándose para siempre y las tasas quedan
   permanentemente sesgadas hacia arriba.
"""

import os

# --- Servidor -------------------------------------------------------------------
bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
accesslog = "-"
errorlog = "-"


# --- Logs en JSON ---------------------------------------------------------------
# El `LOGGING` de Django NO alcanza a gunicorn: sus loggers (gunicorn.access y
# gunicorn.error) son suyos y siguen su propio formato. Sin esto, el 90% de la salida
# del contenedor era texto plano y solo los logs de la aplicacion salian en JSON —
# medio requisito cumplido, que es peor que ninguno porque parece cumplido entero.
if os.environ.get("LOG_FORMATO", "texto") == "json":
    # El access log se emite ya como JSON desde la propia plantilla, en vez de
    # envolver el texto en {"message": "..."}: asi `status` y `duracion_us` son
    # campos consultables y no una cadena que haya que volver a parsear.
    #
    # Se omiten a proposito el Referer y el User-Agent: son texto libre controlado por
    # el cliente, gunicorn no escapa las comillas dobles al interpolarlos, y una sola
    # comilla en un User-Agent romperia el JSON de esa linea. Los numericos van
    # entrecomillados porque gunicorn escribe "-" cuando no hay valor, y un `-` desnudo
    # tampoco es JSON valido.
    access_log_format = (
        '{"remoto":"%(h)s","metodo":"%(m)s","ruta":"%(U)s","query":"%(q)s",'
        '"protocolo":"%(H)s","status":"%(s)s","bytes":"%(B)s","duracion_us":"%(D)s"}'
    )

    logconfig_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # El mensaje del access log YA es JSON: se emite tal cual.
            "acceso_json": {"format": "%(message)s"},
            # Los errores de gunicorn sí son texto libre: se envuelven.
            "error_json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "rename_fields": {"levelname": "level", "asctime": "timestamp"},
                "static_fields": {"service": "all-in-django", "componente": "gunicorn"},
            },
        },
        "handlers": {
            "acceso": {"class": "logging.StreamHandler", "formatter": "acceso_json", "stream": "ext://sys.stdout"},
            "error": {"class": "logging.StreamHandler", "formatter": "error_json", "stream": "ext://sys.stderr"},
        },
        "loggers": {
            "gunicorn.access": {"handlers": ["acceso"], "level": "INFO", "propagate": False},
            "gunicorn.error": {"handlers": ["error"], "level": "INFO", "propagate": False},
        },
        "root": {"handlers": ["error"], "level": "INFO"},
    }


# --- Métricas entre procesos ----------------------------------------------------
def child_exit(server, worker):
    """Descarta las muestras de un worker que acaba de morir.

    Gunicorn llama a este hook en el proceso maestro. Sin él, los ficheros del worker
    difunto se siguen agregando y los contadores nunca bajan.
    """
    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return
    # Import diferido: si el paquete no estuviera, un fallo aquí no debe impedir que
    # gunicorn siga sirviendo. Las métricas son observabilidad, no el servicio.
    try:
        from prometheus_client import multiprocess

        multiprocess.mark_process_dead(worker.pid)
    except Exception as exc:  # noqa: BLE001 - nunca tumbar el servidor por esto
        server.log.warning("No se pudo marcar el worker %s como muerto: %s", worker.pid, exc)
