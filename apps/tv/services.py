"""
apps/tv/services.py — Scraper de canales de TV chilena (requests + BeautifulSoup).

Portado de all_in_one/views/tv_chile.py. Resultado cacheado 1h con cachetools.
"""

import urllib.parse

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached

from core.exceptions import ScraperError
from core.logging import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://www.refnet.cl/"
_URL = "https://www.refnet.cl/tvonline.html"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
_NAME_FIXER = {
    "TVN": "TVN Chile", "CHILEVISION": "Chilevisión", "CANAL13": "Canal 13",
    "CANAL13C": "13C", "MEGA": "Mega", "NTV": "NTV", "UCV": "UCV TV",
    "TVMAS": "TV+", "STGO": "STGO TV", "UCHILE": "Uchile TV", "BIOBIO": "BioBio TV",
    "ARICA": "Arica TV", "CONTIVISION": "Contivisión", "TV9": "TV9 BioBio",
    "CANAL5": "Canal 5 Puerto Montt", "OSORNOTV": "Osorno TV+", "CHILOTE": "Canal Chilote",
    "TVSENADO": "TV Senado", "CAMARA": "TV Cámara",
}

_cache = TTLCache(maxsize=1, ttl=3600)


def _scrape() -> list[dict]:
    try:
        resp = requests.get(_URL, headers=_HEADERS, timeout=15)
        resp.encoding = "iso-8859-1"
    except requests.RequestException as exc:
        logger.warning("Scraper TV falló: %s", exc)
        raise ScraperError(f"No se pudo contactar la fuente de canales: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.find("div", class_="content") or soup.body
    canales = []
    for link in content.find_all("a", href=True):
        img = link.find("img")
        if not (img and "src" in img.attrs):
            continue
        raw_id = img["src"].split("/")[-1].split(".")[0].upper()
        clean_id = "".join(ch for ch in raw_id if not ch.isdigit())
        if any(x in clean_id.lower() for x in ["inicio", "computacion", "logo", "banner"]):
            continue
        canales.append({
            "name": _NAME_FIXER.get(clean_id, clean_id),
            "url": link["href"],
            "logo": urllib.parse.urljoin(_BASE_URL, img["src"]),
        })
    # Únicos por URL, ordenados por nombre (comprensión + dict).
    unicos = list({c["url"]: c for c in canales}.values())
    return sorted(unicos, key=lambda c: c["name"])


@cached(_cache)
def obtener_canales() -> list[dict]:
    """Canales cacheados 1h. Lanza ScraperError si la fuente no responde."""
    return _scrape()
