"""Modelos del módulo Calendario: clases de estudio y turnos laborales personales."""

from datetime import datetime, timedelta

from django.db import models

from core.horarios import DIAS_CHOICES, calcular_horas_turno


class Clase(models.Model):
    """Clase de Santo Tomás en una semana. `horas` se calcula al guardar."""

    semana_inicio = models.DateField(help_text="Lunes de la semana (YYYY-MM-DD)")
    dia = models.CharField(max_length=12, choices=DIAS_CHOICES)
    asignatura = models.CharField(max_length=120)
    entrada = models.TimeField()
    salida = models.TimeField()
    horas = models.FloatField(default=0, editable=False)

    class Meta:
        ordering = ["semana_inicio", "dia"]

    def save(self, *args, **kwargs):
        dt_i = datetime.combine(datetime.today(), self.entrada)
        dt_o = datetime.combine(datetime.today(), self.salida)
        if self.salida < self.entrada:  # cruza medianoche
            dt_o += timedelta(days=1)
        self.horas = round((dt_o - dt_i).total_seconds() / 3600, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.semana_inicio} · {self.dia} · {self.asignatura}"


class TurnoPersonal(models.Model):
    """Turno laboral personal (PedidosYa). bruto/neto/extra se calculan al guardar."""

    semana_inicio = models.DateField()
    dia = models.CharField(max_length=12, choices=DIAS_CHOICES)
    entrada = models.TimeField(null=True, blank=True)
    salida = models.TimeField(null=True, blank=True)
    bruto = models.FloatField(default=0, editable=False)
    neto = models.FloatField(default=0, editable=False)
    extra = models.FloatField(default=0, editable=False)
    es_libre = models.BooleanField(default=False)

    class Meta:
        ordering = ["semana_inicio", "dia"]
        unique_together = ("semana_inicio", "dia")

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
        return f"{self.semana_inicio} · {self.dia} · {estado}"
