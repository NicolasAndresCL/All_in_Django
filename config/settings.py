"""
config/settings.py — Configuración de Django alimentada por core.conf (pydantic-settings).

Los valores sensibles/ambientales (SECRET_KEY, DEBUG, ALLOWED_HOSTS, credenciales) no se
hardcodean: vienen del objeto `settings` tipado y validado de `core/conf.py`.
"""

from pathlib import Path

import dj_database_url

from core.conf import settings as env
from core.logging import LOGGING as _LOGGING

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
    "apps.calendario",
    "apps.liveops",
    "apps.tareas",
    "apps.notas",
    "apps.tv",
    "apps.extras",
]

MIDDLEWARE = [
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

LOGGING = _LOGGING
