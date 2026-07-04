"""Modelo del módulo LiveOps: turnos del equipo (4 trabajadores)."""

from django.db import models

from core.horarios import DIAS_CHOICES, TRABAJADORES_CHOICES, calcular_horas_turno


class TurnoEquipo(models.Model):
    """Turno de un trabajador del equipo. bruto/neto/extra se calculan al guardar."""

    semana_inicio = models.DateField()
    trabajador = models.CharField(max_length=20, choices=TRABAJADORES_CHOICES)
    dia = models.CharField(max_length=12, choices=DIAS_CHOICES)
    entrada = models.TimeField(null=True, blank=True)
    salida = models.TimeField(null=True, blank=True)
    bruto = models.FloatField(default=0, editable=False)
    neto = models.FloatField(default=0, editable=False)
    extra = models.FloatField(default=0, editable=False)
    es_libre = models.BooleanField(default=False)

    class Meta:
        ordering = ["semana_inicio", "trabajador", "dia"]
        unique_together = ("semana_inicio", "trabajador", "dia")

    def save(self, *args, **kwargs):
        if self.es_libre or not self.entrada or not self.salida:
            self.es_libre = True
            self.entrada = self.salida = None
            self.bruto = self.neto = self.extra = 0
        else:
            self.bruto, self.neto, self.extra = calcular_horas_turno(
                self.dia, self.entrada, self.salida
            )
        super().save(*args, **kwargs)

    def __str__(self):
        estado = "LIBRE" if self.es_libre else f"{self.entrada}–{self.salida}"
        return f"{self.semana_inicio} · {self.trabajador} · {self.dia} · {estado}"
