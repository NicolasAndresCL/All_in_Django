"""Modelo del módulo Notas."""

from django.db import models

FORMATOS = [("md", "Markdown"), ("txt", "Texto plano")]


class Nota(models.Model):
    """Nota en Markdown o texto plano; `creado`/`actualizado` se gestionan solos."""

    titulo = models.CharField(max_length=200, blank=True)
    contenido = models.TextField(blank=True)
    formato = models.CharField(max_length=3, choices=FORMATOS, default="md")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-actualizado", "-id"]

    def __str__(self):
        return self.titulo or f"Nota #{self.pk}"
