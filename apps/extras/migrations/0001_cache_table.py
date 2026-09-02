"""Crea la tabla del cache de base de datos (DatabaseCache).

Por que una migracion y no solo `createcachetable` en el entrypoint: el cache guarda
los contadores de rate limiting de DRF, asi que la tabla tiene que existir en TODOS
los entornos —dev con runserver, la base de test de pytest, el CI y el contenedor—,
no solo donde alguien se acuerde de ejecutar el comando. Un paso obligatorio que
depende de la memoria no es obligatorio.

Se llama al management command en vez de escribir el DDL a mano porque el SQL difiere
entre motores (SQLite/Postgres) y `createcachetable` ya lo resuelve por backend.
"""

from django.core.management import call_command
from django.db import migrations


def crear_tabla_cache(apps, schema_editor):
    # Idempotente: el comando comprueba si la tabla ya existe y no falla si esta.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


def borrar_tabla_cache(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS django_cache")


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.RunPython(crear_tabla_cache, borrar_tabla_cache)]
