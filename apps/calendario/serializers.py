"""Serializers del módulo Calendario."""

from rest_framework import serializers

from .models import Clase, TurnoPersonal


class ClaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clase
        fields = ["id", "semana_inicio", "dia", "asignatura", "entrada", "salida", "horas"]
        read_only_fields = ["horas"]


class TurnoPersonalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TurnoPersonal
        fields = [
            "id", "semana_inicio", "dia", "entrada", "salida",
            "bruto", "neto", "extra", "es_libre",
        ]
        read_only_fields = ["bruto", "neto", "extra"]
