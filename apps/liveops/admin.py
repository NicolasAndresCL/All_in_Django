"""Admin del módulo LiveOps."""

from django.contrib import admin

from .models import TurnoEquipo


@admin.register(TurnoEquipo)
class TurnoEquipoAdmin(admin.ModelAdmin):
    list_display = ("semana_inicio", "trabajador", "dia", "entrada", "salida",
                    "bruto", "neto", "extra", "es_libre")
    list_filter = ("trabajador", "dia", "es_libre")
