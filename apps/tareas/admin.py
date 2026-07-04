"""Admin del módulo Registro de Tareas."""

from django.contrib import admin

from .models import Registro


@admin.register(Registro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ("fecha", "proyecto", "tarea", "duracion", "horas")
    list_filter = ("proyecto",)
    search_fields = ("proyecto", "tarea")
    date_hierarchy = "fecha"
