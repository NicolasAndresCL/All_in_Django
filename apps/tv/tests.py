"""Tests del módulo TV (scraper mockeado + endpoint)."""

import pytest
import requests

from core.exceptions import ScraperError

from . import services, views

_HTML = """
<html><body><div class="content">
  <a href="http://stream/tvn"><img src="images/tvn.png"></a>
  <a href="http://stream/mega"><img src="images/mega.png"></a>
  <a href="http://x"><img src="images/logo.png"></a>
</div></body></html>
"""


class _FakeResp:
    def __init__(self, text):
        self.text = text
        self.encoding = "iso-8859-1"


def test_scrape_parsea_y_filtra(monkeypatch):
    monkeypatch.setattr(services.requests, "get", lambda *a, **k: _FakeResp(_HTML))
    canales = services._scrape()
    nombres = {c["name"] for c in canales}
    assert "TVN Chile" in nombres and "Mega" in nombres
    assert len(canales) == 2  # 'logo.png' fue descartado


def test_scrape_error_lanza_scrapererror(monkeypatch):
    def boom(*a, **k):
        raise requests.RequestException("down")
    monkeypatch.setattr(services.requests, "get", boom)
    with pytest.raises(ScraperError):
        services._scrape()


def test_api_canales_busca(monkeypatch, api):
    monkeypatch.setattr(views, "obtener_canales", lambda: [
        {"name": "Mega", "url": "u", "logo": "l"},
        {"name": "TVN Chile", "url": "u2", "logo": "l2"},
    ])
    resp = api.get("/api/tv/canales/?buscar=meg")
    assert resp.status_code == 200
    assert resp.data["total"] == 1
    assert resp.data["canales"][0]["name"] == "Mega"
