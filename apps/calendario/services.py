"""
apps/calendario/services.py — Copiar horarios entre semanas.

Permite crear el horario de una semana nueva "basándose" en otra ya registrada
(portado de las opciones "Copiar/Cargar desde otra semana" de all_in_one).
Reemplaza lo que hubiera en la semana destino. Deja que el modelo recalcule
horas/bruto/neto/extra en `save()`.
"""

from django.db import transaction

from .models import Clase, TurnoPersonal


@transaction.atomic
def copiar_clases(origen, destino) -> int:
    """Copia las clases de la semana `origen` a `destino` (reemplaza destino)."""
    origen_qs = list(Clase.objects.filter(semana_inicio=origen))
    Clase.objects.filter(semana_inicio=destino).delete()
    for c in origen_qs:
        Clase.objects.create(
            semana_inicio=destino, dia=c.dia, asignatura=c.asignatura,
            entrada=c.entrada, salida=c.salida,
        )
    return len(origen_qs)


@transaction.atomic
def copiar_turnos_personales(origen, destino) -> int:
    """Copia los turnos personales de la semana `origen` a `destino` (reemplaza destino)."""
    origen_qs = list(TurnoPersonal.objects.filter(semana_inicio=origen))
    TurnoPersonal.objects.filter(semana_inicio=destino).delete()
    for t in origen_qs:
        TurnoPersonal.objects.create(
            semana_inicio=destino, dia=t.dia, entrada=t.entrada,
            salida=t.salida, es_libre=t.es_libre,
        )
    return len(origen_qs)
