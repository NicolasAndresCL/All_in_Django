"""
config/settings.py — Configuración de Django alimentada por core.conf (pydantic-settings).

Los valores sensibles/ambientales (SECRET_KEY, DEBUG, ALLOWED_HOSTS, credenciales) no se
hardcodean: vienen del objeto `settings` tipado y validado de `core/conf.py`.
"""

from pathlib import Path

import dj_database_url

from core.conf import settings as env
from core.logging import construir_logging

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Seguridad ──────────────────────────────────────────────────────────────
SECRET_KEY = env.SECRET_KEY
DEBUG = env.DEBUG
ALLOWED_HOSTS = env.ALLOWED_HOSTS
# Necesario para el admin/DRF tras un proxy inverso o contenedor (esquemas https).
CSRF_TRUSTED_ORIGINS = env.CSRF_TRUSTED_ORIGINS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Endurecimiento HTTPS (toggle explícito SECURE_HTTPS; ver core/conf.py: no va atado a
# DEBUG porque Compose sirve HTTP plano con DEBUG=False). Cubre security.W004/W008/W012/W016.
if env.SECURE_HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]  # los healthchecks internos van por HTTP
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ─── Apps ───────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",  # tokens de API (modelo Token; se crean en admin o CLI)
    "drf_spectacular",  # genera el esquema OpenAPI desde el propio codigo
    "django_prometheus",  # metricas de peticiones/BD/cache para /metrics
    "apps.calendario",
    "apps.liveops",
    "apps.tareas",
    "apps.notas",
    "apps.tv",
    "apps.extras",
]

MIDDLEWARE = [
    # django-prometheus exige envolver TODA la cadena: Before el primero y After el
    # ultimo. Si se colocan en medio, las latencias medidas dejan fuera el tiempo de
    # los middlewares que queden por fuera y los contadores pierden las peticiones que
    # esos middlewares cortan antes (redirects de SSL, por ejemplo).
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise sirve los estáticos (admin/DRF) directamente desde la app, sin nginx.
    # Debe ir justo después de SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Base de datos (SQLite por defecto) ─────────────────────────────────────
# Con DATABASE_URL definida (p. ej. postgres://user:pass@host:5432/db) se usa ese motor;
# si no, SQLite local. `conn_max_age`=600 reutiliza conexiones (útil en Postgres).
if env.DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(env.DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Cache ──────────────────────────────────────────────────────────────────
# El cache NO es aqui una optimizacion: es donde DRF guarda los contadores de rate
# limiting (AnonRateThrottle/UserRateThrottle y el scope "token" del login). Sin un
# CACHES explicito Django usa LocMemCache, que vive EN EL PROCESO: con los 3 workers
# de gunicorn del contenedor cada uno lleva su propia cuenta y el limite efectivo es
# ~3x el configurado. Medido: con THROTTLE_TOKEN=10/min el 429 llegaba al intento 15.
#
# Es el MISMO patron que las metricas de Prometheus (estado por proceso en un servidor
# multiproceso) y se resuelve igual: sacando el estado del proceso. Aqui se usa la base
# que ya existe —DatabaseCache— en vez de anadir Redis: el volumen de escrituras del
# throttling es despreciable y evita un servicio mas que mantener, respaldar y vigilar.
#
# La tabla la crea la migracion apps/extras/0001_cache_table (y, como red idempotente,
# `createcachetable` en docker/entrypoint.sh): asi existe en dev, en tests y en el
# contenedor sin depender de que alguien recuerde ejecutar el comando.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# ─── DRF ────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    # Toda la API exige autenticación: token (clientes como la UI NiceGUI, header
    # "Authorization: Token <clave>") o sesión (API navegable/admin en el navegador).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    # El esquema OpenAPI lo genera drf-spectacular a partir de los serializers y de las
    # anotaciones @extend_schema de las acciones extra. Es el contrato publicado de la API
    # (/api/schema/) y la referencia contra la que se valida la coleccion Postman.
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Rate limiting (rates configurables por env; ver core/conf.py).
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env.THROTTLE_ANON,
        "user": env.THROTTLE_USER,
        "token": env.THROTTLE_TOKEN,  # scope del endpoint /api/token/
    },
}

# ─── OpenAPI (drf-spectacular) ───────────────────────────────────────────────
# SERVE_INCLUDE_SCHEMA=False: el propio endpoint del esquema no se documenta a si mismo.
# El esquema NO es publico: queda tras IsAuthenticated como el resto de /api/ (solo "/" y
# "/healthz/" son publicos). Se consulta con sesion de admin o con token.
SPECTACULAR_SETTINGS = {
    "TITLE": "All in Django - API",
    "DESCRIPTION": (
        "API REST de All in Django: calendario de estudio, turnos personales y de equipo, "
        "registro de tareas, notas y parrilla de TV chilena. Autenticacion por token "
        "(`Authorization: Token <clave>`) obtenido en `/api/token/`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ─── Password validators ─────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── i18n / tz ───────────────────────────────────────────────────────────────
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # destino de collectstatic (servido por WhiteNoise)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Formato y nivel salen de core.conf: "json" en contenedores, "texto" en desarrollo.
LOGGING = construir_logging(env.LOG_FORMATO, env.LOG_LEVEL)
