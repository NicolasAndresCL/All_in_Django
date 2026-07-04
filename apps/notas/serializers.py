"""Serializers del módulo Notas."""

from rest_framework import serializers

from .models import Nota


class NotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nota
        fields = ["id", "titulo", "contenido", "formato", "creado", "actualizado"]
        read_only_fields = ["creado", "actualizado"]
