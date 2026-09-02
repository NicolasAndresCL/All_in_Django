"""
Paridad entre los dos entornos de despliegue: Docker Compose y el chart de Helm.

**Por que existe.** La observabilidad (2026-09-02) se construyo entera para Compose:
`/metrics` tras bearer, `PROMETHEUS_MULTIPROC_DIR` para agregar entre workers y logs JSON.
Un `helm install` del dia siguiente arrancaba sin ninguna de las tres, y nada lo decia: los
pods quedaban `Running`, las probes en verde y las metricas mintiendo. Es el mismo tipo de
deriva silenciosa que la coleccion Postman envejeciendo frente al esquema OpenAPI, y se
combate igual: con un test que compare las dos fuentes y falle si una se adelanta.

No levanta nada ni hace red: lee los archivos del repo.
"""

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent
COMPOSE = RAIZ / "docker-compose.yml"
DOCKERFILE = RAIZ / "Dockerfile"
CHART = RAIZ / "infra" / "helm" / "all-in-django"

# Variables que existen en UN solo entorno con motivo, no por olvido. Cada exencion nombra
# el concepto equivalente del otro lado; si algo entra aqui sin equivalente, es deuda
# disfrazada de excepcion.
SOLO_COMPOSE = {
    # Parametros del servicio 'db' del compose. En el chart viven en `postgres.*` de
    # values.yaml y se traducen a DATABASE_URL en el helper aid.databaseUrl.
    "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
    # Puertos publicados en el HOST: concepto que no existe en Kubernetes (hay Services).
    "API_PORT", "UI_PORT", "DB_PORT", "PROMETHEUS_PORT",
    # Seleccion de imagen para el compose de despliegue; en el chart es `image.*`.
    "REGISTRY", "IMAGE_OWNER", "IMAGE_TAG",
}

# Del Dockerfile solo cuenta la configuracion de la APLICACION: PYTHON*/PIP_* configuran el
# interprete y el instalador, no el despliegue.
PREFIJOS_DE_RUNTIME = ("PYTHON", "PIP_")


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def variables_inyectadas_por_compose() -> set[str]:
    """Las que el entorno Compose tiene que PASARLE a la imagen: el `environment:` de los
    servicios api/ui y las activas (no comentadas) de .env.docker.example, su contrato
    documentado. Estas son las que el chart esta obligado a proveer tambien."""
    compose = yaml.safe_load(_texto(COMPOSE))
    claves = set()
    for servicio in ("api", "ui"):
        claves |= set(compose["services"][servicio].get("environment", {}))
    for linea in _texto(RAIZ / ".env.docker.example").splitlines():
        if m := re.match(r"^([A-Z][A-Z0-9_]*)=", linea.strip()):
            claves.add(m.group(1))
    return claves - SOLO_COMPOSE


def variables_horneadas_en_la_imagen() -> set[str]:
    """Los `ENV` del Dockerfile. La imagen es la MISMA en los dos entornos, asi que el chart
    no necesita repetirlas — pero si las nombra, tampoco es un error: son suyas igual."""
    nombres = re.findall(r"^\s*(?:ENV\s+)?([A-Z][A-Z0-9_]*)=", _texto(DOCKERFILE), re.M)
    return {n for n in nombres if not n.startswith(PREFIJOS_DE_RUNTIME)}


def variables_del_chart() -> set[str]:
    """Las del ConfigMap y el Secret (que la API recibe enteros por envFrom) mas las
    declaradas una a una en los `env:` de los Deployments."""
    claves = set()
    for nombre in ("configmap.yaml", "secret.yaml"):
        claves |= set(re.findall(r"^  ([A-Z][A-Z0-9_]*):", _texto(CHART / "templates" / nombre), re.M))
    for nombre in ("api-deployment.yaml", "ui-deployment.yaml"):
        claves |= set(re.findall(r"^\s*- name: ([A-Z][A-Z0-9_]*)$", _texto(CHART / "templates" / nombre), re.M))
    return claves


def test_el_chart_provee_todo_lo_que_el_compose_inyecta():
    """El fallo que este test impide: desplegar en K8s una app configurada a medias."""
    faltan = variables_inyectadas_por_compose() - variables_del_chart()
    assert not faltan, (
        f"En el compose pero NO en el chart: {sorted(faltan)}. "
        "Un helm install arrancaria sin ellas y nada lo diria: los pods quedan Running."
    )


def test_el_chart_no_inventa_variables_que_el_compose_desconoce():
    """La otra direccion. Lo que solo existe en K8s no lo prueba nadie: el CI corre sobre
    Compose, asi que una variable exclusiva del chart no se ejercita jamas."""
    conocidas = variables_inyectadas_por_compose() | variables_horneadas_en_la_imagen()
    sobran = variables_del_chart() - conocidas
    assert not sobran, f"En el chart pero en ninguna fuente del entorno Compose: {sorted(sobran)}"


def test_las_tres_piezas_de_observabilidad_estan_en_el_chart():
    """Explicito ademas del test de conjuntos: son las que faltaban y el motivo del test."""
    chart = variables_del_chart()
    for variable in ("METRICS_TOKEN", "PROMETHEUS_MULTIPROC_DIR", "LOG_FORMATO"):
        assert variable in chart, f"{variable} no llego al chart"


def test_el_emptydir_se_monta_donde_el_dockerfile_espera_las_metricas():
    """Si las dos rutas divergen, prometheus_client escribe en un sitio y gunicorn agrega de
    otro: las metricas quedan a cero sin un solo error."""
    encontrado = re.search(r"PROMETHEUS_MULTIPROC_DIR=(\S+)", _texto(DOCKERFILE))
    assert encontrado, "el Dockerfile ya no define PROMETHEUS_MULTIPROC_DIR: sin ella cada worker cuenta por su lado"
    del_dockerfile = encontrado.group(1)
    valores = yaml.safe_load(_texto(CHART / "values.yaml"))
    assert valores["observabilidad"]["multiprocDir"] == del_dockerfile
    deployment = _texto(CHART / "templates" / "api-deployment.yaml")
    assert "mountPath: {{ .Values.observabilidad.multiprocDir }}" in deployment
    assert "emptyDir: {}" in deployment


def test_el_entrypoint_vacia_el_directorio_sin_borrarlo():
    """`rm -rf` sobre el emptyDir montado da "Resource busy" y, con `set -e`, el pod entra en
    CrashLoopBackOff. Comprobado con `docker run -v v:/tmp/prometheus alpine rm -rf`."""
    entrypoint = _texto(RAIZ / "docker" / "entrypoint.sh")
    assert "-mindepth 1 -delete" in entrypoint
    assert 'rm -rf "${PROMETHEUS_MULTIPROC_DIR}"' not in entrypoint


def test_el_pod_de_la_api_se_anuncia_scrapeable():
    deployment = _texto(CHART / "templates" / "api-deployment.yaml")
    for anotacion in ('prometheus.io/scrape: "true"', "prometheus.io/path: /metrics",
                      'prometheus.io/port: "8000"'):
        assert anotacion in deployment


@pytest.mark.parametrize("clave", ["SECRET_KEY", "API_TOKEN"])
def test_los_secretos_obligatorios_fallan_pronto(clave):
    """Mismo fail-fast que ${VAR:?} en el compose. Sin API_TOKEN la UI levanta 'sana' y
    devuelve 401 en cada vista: healthchecks verdes y aplicacion inservible."""
    secret = _texto(CHART / "templates" / "secret.yaml")
    assert re.search(rf"{clave}:\s*\{{\{{\s*required ", secret), f"{clave} sin `required`"
