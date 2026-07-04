"""Modelo del módulo Registro de Tareas (Workshift Analytics)."""

from django.db import models


class Registro(models.Model):
    """Actividad registrada. `horas` se deriva de `duracion` (no se almacena)."""

    fecha = models.DateField()
    proyecto = models.CharField(max_length=120)
    # Texto libre (descripciones desde la UI): límite holgado. SQLite no valida longitud
    # pero Postgres sí, y había registros de ~250 chars que no cabían en 200.
    tarea = models.CharField(max_length=500)
    duracion = models.DurationField(help_text="Duración de la actividad (timedelta)")

    class Meta:
        ordering = ["-fecha", "id"]

    @property
    def horas(self) -> float:
        return round(self.duracion.total_seconds() / 3600, 2)

    def __str__(self):
        return f"{self.fecha} · {self.proyecto} · {self.tarea} ({self.horas} h)"
