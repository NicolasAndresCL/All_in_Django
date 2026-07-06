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
        # Sin UniqueTogetherValidator: reescribir un (semana, trabajador, día) lo
        # REEMPLAZA (upsert) en vez de fallar. El modelo recalcula bruto/neto/extra.
        validators = []

    def create(self, validated_data):
        """Upsert por (semana_inicio, trabajador, dia): si existe, lo reemplaza."""
        turno = TurnoEquipo.objects.filter(
            semana_inicio=validated_data["semana_inicio"],
            trabajador=validated_data["trabajador"],
            dia=validated_data["dia"],
        ).first() or TurnoEquipo(
            semana_inicio=validated_data["semana_inicio"],
            trabajador=validated_data["trabajador"],
            dia=validated_data["dia"],
        )
        turno.entrada = validated_data.get("entrada")
        turno.salida = validated_data.get("salida")
        turno.es_libre = validated_data.get("es_libre", False)
        turno.save()  # save() completo → recalcula bruto/neto/extra y normaliza libres
        return turno


class ImportarTurnosSerializer(serializers.Serializer):
    """Solo para documentar la acción de importación en la API navegable."""

    archivo = serializers.FileField(help_text="CSV o Excel con Fecha, Agente, Entrada, Salida")
