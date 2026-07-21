"""Contrato de RepositorioHistorialConcesiones/RepositorioConvocatoriasEsperadas
(ADR-007 §3.1/§6.1) — parametrizado sobre AMBOS adapters (memoria, sqlite
':memory:'), mismo patrón que `test_contrato_persistencia.py`.
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

import pytest

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite
from ongs_ai.proactivo.modelo import Confianza, ConvocatoriaEsperada, EstadoEsperada, HistorialConcesion
from ongs_ai.proactivo.puertos import RepositorioConvocatoriasEsperadas, RepositorioHistorialConcesiones

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)


@pytest.fixture(params=["memoria", "sqlite"])
def almacen(request):
    instancia = AlmacenMemoria() if request.param == "memoria" else AlmacenSQLite(":memory:")
    yield instancia
    cerrar = getattr(instancia, "cerrar", None)
    if cerrar is not None:
        cerrar()


def _historial(
    historial_id: str = "hist-1", entidad_id: str = "ent-1", cod_concesion: str = "conc-1"
) -> HistorialConcesion:
    return HistorialConcesion(
        historial_id=historial_id,
        entidad_id=entidad_id,
        cod_concesion=cod_concesion,
        nif_beneficiario="G00000001",
        fecha_concesion=date(2024, 9, 15),
        importe_centimos=300_050,
        cod_bdns_convocatoria="700001",
        titulo_convocatoria="IRPF 0,7% estatal 2024",
        organo_nivel1="ESTADO",
        organo_nivel2="MINISTERIO X",
        organo_nivel3="DIRECCION GENERAL X",
        es_concesion_directa=False,
        serie_fingerprint="estado|ministerio x::irpf",
        apertura_convocatoria=date(2024, 5, 10),
        capturado_en=T0,
    )


def _esperada(
    esperada_id: str = "esp-1",
    entidad_id: str = "ent-1",
    serie_fingerprint: str = "estado|ministerio x::irpf",
    anio_esperado: int = 2025,
) -> ConvocatoriaEsperada:
    return ConvocatoriaEsperada(
        esperada_id=esperada_id,
        entidad_id=entidad_id,
        serie_fingerprint=serie_fingerprint,
        titulo_representativo="IRPF 0,7% estatal 2024",
        organo="ESTADO / MINISTERIO X",
        ediciones_previas=1,
        anios_observados=(2024,),
        ventana_mes_inicio=5,
        ventana_mes_fin=5,
        anio_esperado=anio_esperado,
        confianza=Confianza.BAJA,
        accionable=True,
        estado=EstadoEsperada.ESPERADA,
        convocatoria_id_enlazada=None,
        creado_en=T0,
        actualizado_en=T0,
    )


def test_almacen_satisface_los_protocolos_proactivo(almacen):
    assert isinstance(almacen, RepositorioHistorialConcesiones)
    assert isinstance(almacen, RepositorioConvocatoriasEsperadas)


# --- HistorialConcesion ------------------------------------------------------


def test_roundtrip_historial(almacen):
    historial = _historial()
    almacen.guardar_historial(historial)

    obtenido = almacen.obtener_historial_por_cod_concesion("ent-1", "conc-1")

    assert obtenido == historial


def test_obtener_historial_inexistente_devuelve_none(almacen):
    assert almacen.obtener_historial_por_cod_concesion("ent-1", "no-existe") is None


def test_listar_historial_por_entidad_sin_historial_devuelve_lista_vacia(almacen):
    assert almacen.listar_historial_por_entidad("ent-sin-historial") == []


def test_listar_historial_por_entidad_devuelve_todo_lo_guardado(almacen):
    h1 = _historial("hist-a", cod_concesion="conc-a")
    h2 = _historial("hist-b", cod_concesion="conc-b")
    almacen.guardar_historial(h1)
    almacen.guardar_historial(h2)

    listados = almacen.listar_historial_por_entidad("ent-1")

    assert {h.historial_id for h in listados} == {"hist-a", "hist-b"}


def test_historial_con_campos_opcionales_ausentes_roundtrip(almacen):
    minimo = dataclasses.replace(
        _historial("hist-minimo", cod_concesion="conc-minimo"),
        importe_centimos=None,
        organo_nivel2=None,
        organo_nivel3=None,
        apertura_convocatoria=None,
    )
    almacen.guardar_historial(minimo)

    obtenido = almacen.obtener_historial_por_cod_concesion("ent-1", "conc-minimo")

    assert obtenido == minimo


# --- ConvocatoriaEsperada -----------------------------------------------------


def test_roundtrip_esperada(almacen):
    esperada = _esperada()
    almacen.guardar_esperada(esperada)

    obtenida = almacen.obtener_esperada("ent-1", "estado|ministerio x::irpf", 2025)

    assert obtenida == esperada


def test_obtener_esperada_inexistente_devuelve_none(almacen):
    assert almacen.obtener_esperada("ent-1", "no-existe", 2025) is None


def test_obtener_esperada_no_confunde_anios_distintos(almacen):
    almacen.guardar_esperada(_esperada("esp-2024", anio_esperado=2024))
    almacen.guardar_esperada(_esperada("esp-2025", anio_esperado=2025))

    assert almacen.obtener_esperada("ent-1", "estado|ministerio x::irpf", 2024).esperada_id == "esp-2024"
    assert almacen.obtener_esperada("ent-1", "estado|ministerio x::irpf", 2025).esperada_id == "esp-2025"


def test_listar_esperadas_por_entidad_sin_esperadas_devuelve_lista_vacia(almacen):
    assert almacen.listar_esperadas_por_entidad("ent-sin-esperadas") == []


def test_listar_esperadas_por_entidad_devuelve_todas(almacen):
    e1 = _esperada("esp-a", serie_fingerprint="serie-a")
    e2 = _esperada("esp-b", serie_fingerprint="serie-b")
    almacen.guardar_esperada(e1)
    almacen.guardar_esperada(e2)

    listadas = almacen.listar_esperadas_por_entidad("ent-1")

    assert {e.esperada_id for e in listadas} == {"esp-a", "esp-b"}


def test_esperada_publicada_enlazada_roundtrip(almacen):
    enlazada = dataclasses.replace(
        _esperada("esp-enlazada"),
        estado=EstadoEsperada.PUBLICADA_ENLAZADA,
        convocatoria_id_enlazada="bdns-999999",
    )
    almacen.guardar_esperada(enlazada)

    obtenida = almacen.obtener_esperada("ent-1", "estado|ministerio x::irpf", 2025)

    assert obtenida.estado is EstadoEsperada.PUBLICADA_ENLAZADA
    assert obtenida.convocatoria_id_enlazada == "bdns-999999"


def test_guardar_esperada_actualiza_in_place_por_esperada_id(almacen):
    original = _esperada()
    almacen.guardar_esperada(original)

    actualizada = dataclasses.replace(original, ediciones_previas=3, confianza=Confianza.ALTA)
    almacen.guardar_esperada(actualizada)

    obtenida = almacen.obtener_esperada("ent-1", "estado|ministerio x::irpf", 2025)
    assert obtenida.ediciones_previas == 3
    assert obtenida.confianza is Confianza.ALTA
