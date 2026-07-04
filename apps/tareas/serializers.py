"""Serializers del módulo Registro de Tareas."""

from rest_framework import serializers

from .models import Registro


class RegistroSerializer(serializers.ModelSerializer):
    horas = serializers.FloatField(read_only=True)

    class Meta:
        model = Registro
        fields = ["id", "fecha", "proyecto", "tarea", "duracion", "horas"]
