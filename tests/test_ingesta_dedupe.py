"""Dedupe idempotente de ingesta — mismo `portal`+`url_origen` no duplica
(ADR-001 §6.5). Corre sobre AMBOS adapters (memoria, sqlite ':memory:'), igual
que el resto de tests de contrato de persistencia.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ongs_ai.adapters.ingesta.bdns import URL_BUSQUEDA_BDNS, URL_DETALLE_BDNS, FuenteBDNS
from ongs_ai.adapters.ingesta.servicio import ingestar
from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ingesta"
AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)


def _cargar_fixture(nombre: str) -> dict:
    return json.loads((FIXTURES_DIR / nombre).read_text(encoding="utf-8"))


class _TransporteStub:
    """Transporte inyectable de test — nunca hace red, solo devuelve fixtures."""

    def __init__(self, *, paginas: dict[int, dict], detalles: dict[str, dict]) -> None:
        self._paginas = paginas
        self._detalles = detalles

    def obtener_json(self, url: str, params: dict) -> dict:
        if url == URL_BUSQUEDA_BDNS:
            return self._paginas[params["page"]]
        if url == URL_DETALLE_BDNS:
            return self._detalles[params["numConv"]]
        raise AssertionError(f"URL no esperada en el stub de transporte: {url}")


def _fuente_bdns_dos_convocatorias():
    paginas = {0: _cargar_fixture("bdns_busqueda_pagina_0.json")}
    # Solo dos de las tres de la página 0, para mantener el fixture de test pequeño.
    paginas[0] = dict(paginas[0])
    paginas[0]["content"] = paginas[0]["content"][:2]
    paginas[0]["last"] = True

    detalles = {
        "100001": _cargar_fixture("bdns_detalle_100001.json"),
        "100002": _cargar_fixture("bdns_detalle_100002.json"),
    }
    transporte = _TransporteStub(paginas=paginas, detalles=detalles)
    return FuenteBDNS(transporte, reloj=lambda: AHORA, page_size=3)


@pytest.fixture(params=["memoria", "sqlite"])
def almacen(request):
    instancia = AlmacenMemoria() if request.param == "memoria" else AlmacenSQLite(":memory:")
    yield instancia
    cerrar = getattr(instancia, "cerrar", None)
    if cerrar is not None:
        cerrar()


def test_doble_pasada_no_duplica_convocatorias(almacen):
    primera = ingestar(_fuente_bdns_dos_convocatorias(), almacen)
    assert primera.nuevas == 2
    assert primera.ya_existentes == 0

    segunda = ingestar(_fuente_bdns_dos_convocatorias(), almacen)
    assert segunda.nuevas == 0
    assert segunda.ya_existentes == 2

    assert almacen.obtener_convocatoria("bdns-100001") is not None
    assert almacen.obtener_convocatoria("bdns-100002") is not None


def test_dedupe_es_por_portal_y_url_origen_no_por_convocatoria_id(almacen):
    convocatoria = next(iter(_fuente_bdns_dos_convocatorias().buscar()))
    almacen.guardar_convocatoria(convocatoria)

    encontrada = almacen.obtener_por_url_origen(
        convocatoria.fuente.portal, convocatoria.fuente.url_origen
    )
    assert encontrada == convocatoria
    assert almacen.obtener_por_url_origen("BDNS", "https://no-existe.example") is None
    assert almacen.obtener_por_url_origen("OTRO_PORTAL", convocatoria.fuente.url_origen) is None
