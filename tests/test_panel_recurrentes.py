"""Read model de "Tus ayudas recurrentes" (`servicios/panel_recurrentes.py`)
— bloque B del prompt del arquitecto tras ADR-007. Sin red, sin HTTP: solo
las funciones puras de traducción a lenguaje natural."""
from __future__ import annotations

from datetime import date

from ongs_ai.proactivo.modelo import Confianza
from ongs_ai.servicios.panel_recurrentes import etiqueta_honesta, ventana_en_lenguaje_natural

from test_web_panel import _esperada


def test_ventana_en_lenguaje_natural_mismo_mes():
    assert ventana_en_lenguaje_natural(5, 5) == "en torno a mayo"


def test_ventana_en_lenguaje_natural_rango():
    assert ventana_en_lenguaje_natural(5, 6) == "mayo–junio"


def test_etiqueta_honesta_una_edicion():
    esperada = _esperada("ent-1", "esp-1", serie_fingerprint="s1", titulo="x", ediciones_previas=1)
    assert etiqueta_honesta(esperada) == "una sola edición previa — sin patrón confirmado"


def test_etiqueta_honesta_irregular():
    esperada = _esperada(
        "ent-1", "esp-1", serie_fingerprint="s1", titulo="x", ediciones_previas=2, ventana=(1, 9)
    )
    assert etiqueta_honesta(esperada) == "irregular"


def test_etiqueta_honesta_ninguna_para_ventana_agrupada_con_varias_ediciones():
    esperada = _esperada(
        "ent-1", "esp-1", serie_fingerprint="s1", titulo="x", ediciones_previas=3,
        ventana=(5, 6), confianza=Confianza.ALTA,
    )
    assert etiqueta_honesta(esperada) is None
