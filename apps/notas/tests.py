"""Tests del módulo Notas (servicios + API CRUD + exportar)."""

import pytest

from . import services
from .models import Nota


# ─── servicios ───────────────────────────────────────────────────────────────
def test_markdown_a_texto():
    txt = services.markdown_a_texto("# T\n**bold** *it*\n- item\n[x](http://y)\n`c`")
    assert "#" not in txt and "**" not in txt and "`" not in txt
    assert "bold" in txt and "• item" in txt and "x" in txt and "http://y" not in txt


def test_markdown_a_texto_vacio():
    assert services.markdown_a_texto("") == ""


@pytest.mark.parametrize("titulo, esperado", [
    ("Ideas LiveOps", "Ideas_LiveOps"), ("  con  espacios ", "con_espacios"), ("", "nota"),
])
def test_slug_archivo(titulo, esperado):
    assert services.slug_archivo(titulo) == esperado


# ─── API ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_api_crud_nota(api):
    client = api
    resp = client.post("/api/notas/", {"titulo": "N1", "contenido": "# Hola", "formato": "md"},
                       format="json")
    assert resp.status_code == 201
    nid = resp.data["id"]
    assert client.get("/api/notas/").data["count"] == 1
    assert client.delete(f"/api/notas/{nid}/").status_code == 204


@pytest.mark.django_db
def test_api_exportar_txt(api):
    nota = Nota.objects.create(titulo="Mi Nota", contenido="# Título\n**negrita**", formato="md")
    resp = api.get(f"/api/notas/{nota.id}/exportar/?fmt=txt")
    assert resp.status_code == 200
    cuerpo = resp.content.decode("utf-8")
    assert "#" not in cuerpo and "**" not in cuerpo and "negrita" in cuerpo
    assert "Mi_Nota.txt" in resp["Content-Disposition"]
