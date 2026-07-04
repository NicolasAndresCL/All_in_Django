"""Admin del módulo Calendario."""

from django.contrib import admin

from .models import Clase, TurnoPersonal


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ("semana_inicio", "dia", "asignatura", "entrada", "salida", "horas")
    list_filter = ("dia",)
    search_fields = ("asignatura",)


@admin.register(TurnoPersonal)
class TurnoPersonalAdmin(admin.ModelAdmin):
    list_display = ("semana_inicio", "dia", "entrada", "salida", "bruto", "neto", "extra", "es_libre")
    list_filter = ("dia", "es_libre")
