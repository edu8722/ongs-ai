"""Tests del read model del panel (`servicios/panel.py`) — ADR-004 §2.5/§2.7, F4.2.

Parametrizados sobre AMBOS almacenes (memoria, sqlite `:memory:`), herméticos,
como el resto de tests de persistencia. Cubre agrupación por estado, motivo
de los no-elegibles, orden por fecha del último asiento, y AISLAMIENTO POR
TENANT (entidad A no ve nada de B) — regla de oro CLAUDE.md.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    EstadoMatch,
    ResultadoElegibilidad,
    crear_match,
    transicionar,
)
from ongs_ai.servicios.panel import resumen_panel

T0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 7, 10, tzinfo=timezone.utc)
T2 = datetime(2026, 7, 20, tzinfo=timezone.utc)


@pytest.fixture(params=["memoria", "sqlite"])
def almacen(request):
    instancia = AlmacenMemoria() if request.param == "memoria" else AlmacenSQLite(":memory:")
    yield instancia
    cerrar = getattr(instancia, "cerrar", None)
    if cerrar is not None:
        cerrar()


def _match_detectada_no_elegible(match_id: str, entidad_id: str, motivo_detalle: str, ts: datetime):
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=f"conv-{match_id}",
        transicion_id=f"t0-{match_id}", motivo="detectada por matching",
        actor=ActorAsiento.SISTEMA, timestamp=ts,
    )
    return dataclasses.replace(
        match,
        resultado_elegibilidad_dura=ResultadoElegibilidad(elegible=False, detalle=motivo_detalle),
    )


def _match_en_estado(match_id: str, entidad_id: str, estado_final: EstadoMatch, ts: datetime):
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=f"conv-{match_id}",
        transicion_id=f"t0-{match_id}", motivo="detectada", actor=ActorAsiento.SISTEMA, timestamp=ts,
    )
    if estado_final == EstadoMatch.DETECTADA:
        return match
    match = transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id=f"t1-{match_id}",
        motivo="propuesta", actor=ActorAsiento.SISTEMA, timestamp=ts,
    )
    if estado_final == EstadoMatch.PROPUESTA:
        return match
    if estado_final == EstadoMatch.DESCARTADA:
        return transicionar(
            match, a_estado=EstadoMatch.DESCARTADA, transicion_id=f"t2-{match_id}",
            motivo="descartada por la entidad", actor=ActorAsiento.ENTIDAD, timestamp=ts,
        )
    match = transicionar(
        match, a_estado=EstadoMatch.ACEPTADA, transicion_id=f"t2-{match_id}",
        motivo="aceptada", actor=ActorAsiento.ENTIDAD, timestamp=ts,
    )
    if estado_final == EstadoMatch.ACEPTADA:
        return match
    match = transicionar(
        match, a_estado=EstadoMatch.EN_PREPARACION, transicion_id=f"t3-{match_id}",
        motivo="en preparación", actor=ActorAsiento.ENTIDAD, timestamp=ts,
    )
    if estado_final == EstadoMatch.EN_PREPARACION:
        return match
    return transicionar(
        match, a_estado=EstadoMatch.PRESENTADA, transicion_id=f"t4-{match_id}",
        motivo="presentada", actor=ActorAsiento.ENTIDAD, timestamp=ts,
    )


def test_agrupa_por_estado_correctamente(almacen):
    entidad_id = "ent-panel-1"
    almacen.guardar_match(_match_en_estado("m-propuesta", entidad_id, EstadoMatch.PROPUESTA, T0))
    almacen.guardar_match(_match_en_estado("m-aceptada", entidad_id, EstadoMatch.ACEPTADA, T0))
    almacen.guardar_match(_match_en_estado("m-preparacion", entidad_id, EstadoMatch.EN_PREPARACION, T0))
    almacen.guardar_match(_match_en_estado("m-presentada", entidad_id, EstadoMatch.PRESENTADA, T0))
    almacen.guardar_match(_match_en_estado("m-descartada", entidad_id, EstadoMatch.DESCARTADA, T0))
    almacen.guardar_match(
        _match_detectada_no_elegible("m-no-elegible", entidad_id, "ámbito territorial incompatible", T0)
    )

    resumen = resumen_panel(entidad_id, almacen)

    assert [m.match_id for m in resumen.propuestas_pendientes] == ["m-propuesta"]
    assert [m.match_id for m in resumen.aceptadas] == ["m-aceptada"]
    assert [m.match_id for m in resumen.en_preparacion] == ["m-preparacion"]
    assert [m.match_id for m in resumen.presentadas] == ["m-presentada"]
    assert [m.match_id for m in resumen.descartadas] == ["m-descartada"]
    assert [m.match_id for m in resumen.detectadas_no_elegibles] == ["m-no-elegible"]
    assert resumen.detectadas_no_elegibles[0].resultado_elegibilidad_dura.detalle == (
        "ámbito territorial incompatible"
    )


def test_detectada_elegible_no_aparece_en_detectadas_no_elegibles(almacen):
    entidad_id = "ent-panel-2"
    match = crear_match(
        match_id="m-detectada-elegible", entidad_id=entidad_id, convocatoria_id="conv-x",
        transicion_id="t0", motivo="detectada", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )
    match = dataclasses.replace(
        match, resultado_elegibilidad_dura=ResultadoElegibilidad(elegible=True, detalle="cumple todo")
    )
    almacen.guardar_match(match)

    resumen = resumen_panel(entidad_id, almacen)

    assert resumen.detectadas_no_elegibles == ()
    assert resumen.propuestas_pendientes == ()


def test_detectada_sin_resultado_no_rompe_y_se_omite(almacen):
    entidad_id = "ent-panel-3"
    match = crear_match(
        match_id="m-sin-resultado", entidad_id=entidad_id, convocatoria_id="conv-x",
        transicion_id="t0", motivo="detectada", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )
    almacen.guardar_match(match)

    resumen = resumen_panel(entidad_id, almacen)  # no debe lanzar

    assert resumen.detectadas_no_elegibles == ()


def test_orden_por_fecha_del_ultimo_asiento_mas_reciente_primero(almacen):
    entidad_id = "ent-panel-4"
    almacen.guardar_match(_match_en_estado("m-antiguo", entidad_id, EstadoMatch.PROPUESTA, T0))
    almacen.guardar_match(_match_en_estado("m-reciente", entidad_id, EstadoMatch.PROPUESTA, T2))
    almacen.guardar_match(_match_en_estado("m-medio", entidad_id, EstadoMatch.PROPUESTA, T1))

    resumen = resumen_panel(entidad_id, almacen)

    assert [m.match_id for m in resumen.propuestas_pendientes] == [
        "m-reciente", "m-medio", "m-antiguo",
    ]


def test_entidad_sin_matches_devuelve_todos_los_cubos_vacios(almacen):
    resumen = resumen_panel("ent-sin-matches", almacen)

    assert resumen.propuestas_pendientes == ()
    assert resumen.aceptadas == ()
    assert resumen.en_preparacion == ()
    assert resumen.presentadas == ()
    assert resumen.descartadas == ()
    assert resumen.detectadas_no_elegibles == ()


def test_aislamiento_por_tenant_entidad_a_no_ve_nada_de_b(almacen):
    entidad_a, entidad_b = "ent-A-panel", "ent-B-panel"
    almacen.guardar_match(_match_en_estado("m-a-propuesta", entidad_a, EstadoMatch.PROPUESTA, T0))
    almacen.guardar_match(
        _match_detectada_no_elegible("m-a-no-elegible", entidad_a, "motivo de A", T0)
    )
    almacen.guardar_match(_match_en_estado("m-b-propuesta", entidad_b, EstadoMatch.PROPUESTA, T0))
    almacen.guardar_match(_match_en_estado("m-b-aceptada", entidad_b, EstadoMatch.ACEPTADA, T0))
    almacen.guardar_match(
        _match_detectada_no_elegible("m-b-no-elegible", entidad_b, "motivo de B", T0)
    )
    almacen.guardar_match(_match_en_estado("m-b-descartada", entidad_b, EstadoMatch.DESCARTADA, T0))

    resumen_a = resumen_panel(entidad_a, almacen)

    todos_los_ids_de_a = {
        m.match_id
        for cubo in (
            resumen_a.propuestas_pendientes, resumen_a.aceptadas, resumen_a.en_preparacion,
            resumen_a.presentadas, resumen_a.descartadas, resumen_a.detectadas_no_elegibles,
        )
        for m in cubo
    }
    assert todos_los_ids_de_a == {"m-a-propuesta", "m-a-no-elegible"}
    assert all(m.entidad_id == entidad_a for cubo in (
        resumen_a.propuestas_pendientes, resumen_a.aceptadas, resumen_a.en_preparacion,
        resumen_a.presentadas, resumen_a.descartadas, resumen_a.detectadas_no_elegibles,
    ) for m in cubo)
    assert resumen_a.descartadas == ()  # A no tiene descartadas; sobre todo, no la de B
    assert resumen_a.aceptadas == ()  # A no tiene aceptadas; sobre todo, no la de B
