"""Parseo del directorio de entidades asociadas de FEDER — utilidad de captación.

PURO (HTML -> registros), sin red — el transporte real vive en
`scripts/scrape_feder.py` (única pieza con red real, fuera de pytest). Esta
separación es la que permite testear el parseo herméticamente con un fixture
HTML sintético (`tests/fixtures/feder_*.html`).

La web (https://www.enfermedades-raras.org/movimiento-asociativo/entidades-
asociadas) publica el directorio como capa de mapa (Drupal + Geolocation):
cada entidad es un bloque `data-views-row-index="N"` con su ficha completa
(nombre, dirección, teléfonos, emails, web) embebida en `location-content`,
aunque esté oculta a la vista (`js-hide`) hasta que se pulsa su marcador.
Robusto por construcción: un campo ausente en la ficha real (dirección,
teléfono, email, web, provincia/CCAA) se traduce en cadena/tupla vacía —
jamás se inventa un dato que no está en el HTML.
"""
from __future__ import annotations

import html as html_module
import re
import urllib.parse
from dataclasses import dataclass

_MARCADOR_ENTIDAD = 'data-views-row-index="'
_MARCADORES_FIN_LISTADO = ('<div class="pager', '<nav class="pager', '</body')

_RE_TITULO = re.compile(
    r'class="views-field views-field-title"><span class="field-content">'
    r'<a href="([^"]*)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
_RE_TAG_A = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
_RE_HREF = re.compile(r'href\s*=\s*"([^"]*)"', re.IGNORECASE)
_RE_TEL_HREF = re.compile(r'<a[^>]*href="tel:[^"]*"[^>]*>([^<]*)</a>')
_RE_MAILTO_HREF = re.compile(r'href="mailto:([^"]*)"')


@dataclass(frozen=True)
class EntidadFeder:
    """Ficha de una entidad asociada tal cual consta en el directorio FEDER.

    `url_ficha` es la ruta (relativa al sitio) de su página propia — clave
    natural para deduplicar entre páginas del listado.
    """

    nombre: str
    url_ficha: str
    direccion: str = ""
    telefonos: tuple[str, ...] = ()
    emails: tuple[str, ...] = ()
    web: str = ""
    provincia: str = ""
    ccaa: str = ""


def _texto_plano(fragmento: str | None) -> str:
    if fragmento is None:
        return ""
    sin_etiquetas = re.sub(r"<[^>]+>", " ", fragmento)
    return html_module.unescape(sin_etiquetas).strip()


def _recortar_al_fin_del_listado(chunk: str) -> str:
    fin = len(chunk)
    for marcador in _MARCADORES_FIN_LISTADO:
        pos = chunk.find(marcador)
        if pos != -1:
            fin = min(fin, pos)
    return chunk[:fin]


def _campo(chunk: str, clase_campo: str) -> str | None:
    patron = re.compile(
        rf'class="views-field views-field-{re.escape(clase_campo)}"[^>]*>.*?'
        r'<div class="field-content">(.*?)</div>',
        re.DOTALL,
    )
    coincidencia = patron.search(chunk)
    return coincidencia.group(1) if coincidencia else None


def parsear_pagina_entidades(pagina_html: str) -> list[EntidadFeder]:
    """Extrae las entidades de UNA página ya descargada del directorio FEDER."""
    entidades: list[EntidadFeder] = []
    for trozo_crudo in pagina_html.split(_MARCADOR_ENTIDAD)[1:]:
        chunk = _recortar_al_fin_del_listado(trozo_crudo)

        titulo = _RE_TITULO.search(chunk)
        if titulo is None:
            continue  # bloque sin ficha de entidad (ruido de marcado): se descarta

        url_ficha = titulo.group(1).strip()
        nombre = _texto_plano(titulo.group(2))
        if not nombre or not url_ficha:
            continue

        telefono_bruto = _campo(chunk, "field-telefono-entidad-ext") or ""
        telefonos = tuple(
            _texto_plano(t) for t in _RE_TEL_HREF.findall(telefono_bruto) if _texto_plano(t)
        )

        correo_bruto = _campo(chunk, "field-correo-electronico") or ""
        emails = tuple(correo.strip() for correo in _RE_MAILTO_HREF.findall(correo_bruto) if correo.strip())

        web_bruto = _campo(chunk, "field-web-entidad") or ""
        web_href = _RE_HREF.search(web_bruto)
        web = web_href.group(1).strip() if web_href else ""

        entidades.append(
            EntidadFeder(
                nombre=nombre,
                url_ficha=url_ficha,
                direccion=_texto_plano(_campo(chunk, "field-direccion")),
                telefonos=telefonos,
                emails=emails,
                web=web,
                provincia=_texto_plano(_campo(chunk, "field-provincia")),
                ccaa=_texto_plano(_campo(chunk, "field-comunidad-autonoma")),
            )
        )
    return entidades


def extraer_url_pagina_siguiente(pagina_html: str, url_base: str) -> str | None:
    """Devuelve la URL absoluta de "página siguiente" (link `rel="next"`), o
    `None` si el HTML no trae ninguna (última página)."""
    for etiqueta in _RE_TAG_A.findall(pagina_html):
        if 'rel="next"' in etiqueta:
            href = _RE_HREF.search(etiqueta)
            if href:
                return urllib.parse.urljoin(url_base, href.group(1))
    return None
