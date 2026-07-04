"""Serializers del módulo LiveOps."""

from rest_framework import serializers

from .models import TurnoEquipo


class TurnoEquipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TurnoEquipo
        fields = [
            "id", "semana_inicio", "trabajador", "dia", "entrada", "salida",
            "bruto", "neto", "extra", "es_libre",
        ]
        read_only_fields = ["bruto", "neto", "extra"]


class ImportarTurnosSerializer(serializers.Serializer):
    """Solo para documentar la acción de importación en la API navegable."""

    archivo = serializers.FileField(help_text="CSV o Excel con Fecha, Agente, Entrada, Salida")
