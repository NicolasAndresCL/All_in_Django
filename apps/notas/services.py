"""
apps/notas/services.py — Utilidades de formato de notas (sin Django).

Portado de all_in_one/core/notas_logic.py: conversión Markdown→texto plano y
nombre de archivo seguro. Funciones puras → fáciles de testear.
"""

import re


def markdown_a_texto(md: str) -> str:
    """Quita marcadores Markdown comunes para exportar/copiar como texto plano."""
    if not md:
        return ""
    t = md
    t = re.sub(r"```.*?```", lambda m: m.group(0).strip("`"), t, flags=re.S)  # bloques de código
    t = re.sub(r"`([^`]*)`", r"\1", t)                       # código inline
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", t)          # imágenes
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)            # enlaces
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)      # encabezados
    t = re.sub(r"^\s{0,3}>\s?", "", t, flags=re.M)           # citas
    t = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", t, flags=re.M)    # viñetas
    t = re.sub(r"(\*\*|__)(.*?)\1", r"\2", t)                # negrita
    t = re.sub(r"(\*|_)(.*?)\1", r"\2", t)                   # cursiva
    return t


def slug_archivo(titulo: str) -> str:
    """Nombre de archivo seguro a partir del título."""
    base = re.sub(r"[^\w\-]+", "_", (titulo or "").strip()).strip("_")
    return base or "nota"
