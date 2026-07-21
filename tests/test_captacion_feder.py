"""Tests del parseo del directorio FEDER (`adapters/captacion/feder.py`).

Hermético: NUNCA red — usa fixtures HTML sintéticos con la estructura real
del sitio (Drupal + Geolocation) pero datos ficticios
(`tests/fixtures/feder_pagina_*.html`). Cubre extracción feliz, robustez ante
campos ausentes (teléfono, email/web) y descubrimiento del link de paginación
("página siguiente" / ausencia de él en la última página).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ongs_ai.adapters.captacion.feder import (
    extraer_url_pagina_siguiente,
    parsear_pagina_entidades,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def html_con_siguiente() -> str:
    return (FIXTURES / "feder_pagina_con_siguiente.html").read_text(encoding="utf-8")


@pytest.fixture
def html_sin_siguiente() -> str:
    return (FIXTURES / "feder_pagina_sin_siguiente.html").read_text(encoding="utf-8")


def test_extrae_las_tres_entidades_de_la_pagina(html_con_siguiente):
    entidades = parsear_pagina_entidades(html_con_siguiente)

    assert [e.nombre for e in entidades] == [
        "Asociación Ficticia Completa",
        "Asociación Ficticia Sin Teléfono",
        "Asociación Ficticia Sin Email Ni Web",
    ]


def test_entidad_completa_trae_todos_los_campos(html_con_siguiente):
    entidades = parsear_pagina_entidades(html_con_siguiente)
    completa = entidades[0]

    assert completa.url_ficha == (
        "/movimiento-asociativo/entidades-asociadas/asociacion-ficticia-completa"
    )
    assert completa.direccion == "Calle Inventada, 1"
    assert completa.telefonos == ("900 00 00 01",)
    assert completa.emails == ("contacto@ficticia-completa.org", "info@ficticia-completa.org")
    assert completa.web == "www.ficticia-completa.org"


def test_entidad_sin_telefono_degrada_a_tupla_vacia_sin_inventar(html_con_siguiente):
    entidades = parsear_pagina_entidades(html_con_siguiente)
    sin_telefono = entidades[1]

    assert sin_telefono.telefonos == ()
    assert sin_telefono.emails == ("hola@sin-telefono.org",)
    assert sin_telefono.web == ""


def test_entidad_sin_email_ni_web_degrada_limpio_y_soporta_varios_telefonos(html_con_siguiente):
    entidades = parsear_pagina_entidades(html_con_siguiente)
    sin_email = entidades[2]

    assert sin_email.emails == ()
    assert sin_email.web == ""
    assert sin_email.telefonos == ("900 00 00 03", "900 00 00 04")


def test_campos_ausentes_de_la_ficha_completa_quedan_vacios_no_none(html_con_siguiente):
    entidades = parsear_pagina_entidades(html_con_siguiente)
    completa = entidades[0]

    assert completa.provincia == ""
    assert completa.ccaa == ""


def test_pagina_sin_entidades_devuelve_lista_vacia_no_lanza():
    assert parsear_pagina_entidades("<html><body>sin resultados</body></html>") == []


def test_extrae_la_url_absoluta_de_pagina_siguiente(html_con_siguiente):
    url_base = "https://www.enfermedades-raras.org/movimiento-asociativo/entidades-asociadas"

    siguiente = extraer_url_pagina_siguiente(html_con_siguiente, url_base)

    assert siguiente == (
        "https://www.enfermedades-raras.org/movimiento-asociativo/entidades-asociadas?page=1"
    )


def test_ultima_pagina_no_trae_link_siguiente(html_sin_siguiente):
    url_base = "https://www.enfermedades-raras.org/movimiento-asociativo/entidades-asociadas"

    assert extraer_url_pagina_siguiente(html_sin_siguiente, url_base) is None
