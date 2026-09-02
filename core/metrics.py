"""
core/metrics.py — `/metrics` de Prometheus, detrás de un token.

`django_prometheus.urls` registra la vista **sin autenticación** (su `urls.py` no la
envuelve en nada). La regla del proyecto es que solo `/` y `/healthz/` sean públicos, y
las métricas no son inocuas: revelan las rutas que existen, el volumen por endpoint, las
latencias y el reparto de códigos de estado — un mapa de la aplicación servido gratis.

Por eso aquí va envuelta:

- Sin `METRICS_TOKEN` configurado, el endpoint responde **404**: deshabilitado, no
  abierto. Un despliegue que olvide la variable no publica sus métricas por accidente
  (el fallo por defecto es el seguro).
- Con token, exige `Authorization: Bearer <token>`. Es lo que Prometheus manda de forma
  nativa con `bearer_token` en el `scrape_config`, así que no hace falta un proxy.
- La comparación es `secrets.compare_digest`: comparar con `==` filtra información por
  el tiempo que tarda en fallar.
"""

import secrets

from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt

from core.conf import settings as env


def _token_de(request) -> str:
    """Extrae el bearer de la cabecera Authorization (cadena vacía si no viene)."""
    cabecera = request.META.get("HTTP_AUTHORIZATION", "")
    prefijo = "Bearer "
    return cabecera[len(prefijo):] if cabecera.startswith(prefijo) else ""


@csrf_exempt
def metrics(request):
    """Expone las métricas de Prometheus si el bearer coincide con `METRICS_TOKEN`."""
    esperado = env.METRICS_TOKEN
    if not esperado:
        # 404 y no 403: sin token configurado el endpoint no existe para nadie.
        return HttpResponseNotFound()

    if not secrets.compare_digest(_token_de(request), esperado):
        respuesta = HttpResponse("Credenciales invalidas para /metrics.\n", status=401)
        respuesta["WWW-Authenticate"] = 'Bearer realm="metrics"'
        return respuesta

    # Import diferido: django_prometheus toca el registro global de la librería cliente
    # al importarse, y a este módulo lo carga `config/urls.py` en el arranque.
    from django_prometheus.exports import ExportToDjangoView

    return ExportToDjangoView(request)
