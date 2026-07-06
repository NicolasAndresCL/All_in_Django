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
        # Sin UniqueTogetherValidator (que rechazaba reescribir un día): registrar de
        # nuevo un (semana, día) lo REEMPLAZA en vez de fallar. Así se corrige una
        # semana editando el día errado, sin borrar día a día. El modelo recalcula
        # bruto/neto/extra en save().
        validators = []

    def create(self, validated_data):
        """Upsert por (semana_inicio, dia): si el día ya existe, lo reemplaza.

        No se usa `update_or_create` porque este pasa `update_fields` a `save()`, y
        entonces los campos calculados en el modelo (`bruto/neto/extra`, y el reseteo
        de `entrada/salida` cuando es libre) no se persistirían. Hacemos un `save()`
        completo para que el modelo recalcule todo.
        """
        turno = TurnoPersonal.objects.filter(
            semana_inicio=validated_data["semana_inicio"], dia=validated_data["dia"]
        ).first() or TurnoPersonal(
            semana_inicio=validated_data["semana_inicio"], dia=validated_data["dia"]
        )
        turno.entrada = validated_data.get("entrada")
        turno.salida = validated_data.get("salida")
        turno.es_libre = validated_data.get("es_libre", False)
        turno.save()  # recalcula bruto/neto/extra y normaliza los días libres
        return turno
