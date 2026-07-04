"""Admin del módulo Notas."""

from django.contrib import admin

from .models import Nota


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "formato", "actualizado")
    list_filter = ("formato",)
    search_fields = ("titulo", "contenido")
