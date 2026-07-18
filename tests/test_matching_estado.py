import dataclasses
from datetime import datetime, timezone

import pytest

from ongs_ai.dominio.errores import TransicionIlegalError
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    EstadoMatch,
    crear_match,
    transicionar,
)

T0 = datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc)


def _match_inicial():
    return crear_match(
        match_id="match-1",
        entidad_id="ent-1",
        convocatoria_id="conv-1",
        transicion_id="t0",
        motivo="convocatoria detectada por el vigilante",
        actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )


def test_crear_match_arranca_en_detectada_con_un_asiento():
    match = _match_inicial()
    assert match.estado_actual is EstadoMatch.DETECTADA
    assert len(match.asientos) == 1
    assert match.asientos[0].de_estado is None
    assert match.creado_en == T0


def test_camino_legal_completo_hasta_presentada():
    match = _match_inicial()
    match = transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta a la entidad", actor=ActorAsiento.IA, timestamp=T0,
    )
    assert match.estado_actual is EstadoMatch.PROPUESTA
    match = transicionar(
        match, a_estado=EstadoMatch.ACEPTADA, transicion_id="t2",
        motivo="entidad acepta", actor=ActorAsiento.ENTIDAD, timestamp=T0,
    )
    assert match.estado_actual is EstadoMatch.ACEPTADA
    match = transicionar(
        match, a_estado=EstadoMatch.EN_PREPARACION, transicion_id="t3",
        motivo="se inicia preparación", actor=ActorAsiento.ENTIDAD, timestamp=T0,
    )
    assert match.estado_actual is EstadoMatch.EN_PREPARACION
    match = transicionar(
        match, a_estado=EstadoMatch.PRESENTADA, transicion_id="t4",
        motivo="solicitud presentada", actor=ActorAsiento.ENTIDAD, timestamp=T0,
    )
    assert match.estado_actual is EstadoMatch.PRESENTADA
    assert len(match.asientos) == 5


def test_propuesta_puede_descartarse():
    match = _match_inicial()
    match = transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta", actor=ActorAsiento.IA, timestamp=T0,
    )
    match = transicionar(
        match, a_estado=EstadoMatch.DESCARTADA, transicion_id="t2",
        motivo="entidad descarta", actor=ActorAsiento.ENTIDAD, timestamp=T0,
    )
    assert match.estado_actual is EstadoMatch.DESCARTADA


@pytest.mark.parametrize(
    "origen, destino",
    [
        (EstadoMatch.DESCARTADA, EstadoMatch.EN_PREPARACION),
        (EstadoMatch.PRESENTADA, EstadoMatch.DETECTADA),
        (EstadoMatch.DETECTADA, EstadoMatch.ACEPTADA),
        (EstadoMatch.DETECTADA, EstadoMatch.EN_PREPARACION),
        (EstadoMatch.PROPUESTA, EstadoMatch.EN_PREPARACION),
        (EstadoMatch.ACEPTADA, EstadoMatch.PRESENTADA),
    ],
)
def test_transiciones_ilegales_lanzan_error(origen, destino):
    with pytest.raises(TransicionIlegalError):
        _forzar_transicion_ilegal(origen, destino)


def _forzar_transicion_ilegal(origen: EstadoMatch, destino: EstadoMatch):
    match = _match_inicial()
    # Llevamos el match hasta `origen` por el camino legal correspondiente,
    # luego intentamos la transición ilegal a `destino`.
    camino = {
        EstadoMatch.DETECTADA: [],
        EstadoMatch.PROPUESTA: [EstadoMatch.PROPUESTA],
        EstadoMatch.ACEPTADA: [EstadoMatch.PROPUESTA, EstadoMatch.ACEPTADA],
        EstadoMatch.DESCARTADA: [EstadoMatch.PROPUESTA, EstadoMatch.DESCARTADA],
        EstadoMatch.EN_PREPARACION: [
            EstadoMatch.PROPUESTA, EstadoMatch.ACEPTADA, EstadoMatch.EN_PREPARACION,
        ],
        EstadoMatch.PRESENTADA: [
            EstadoMatch.PROPUESTA, EstadoMatch.ACEPTADA,
            EstadoMatch.EN_PREPARACION, EstadoMatch.PRESENTADA,
        ],
    }
    for i, estado in enumerate(camino[origen]):
        match = transicionar(
            match, a_estado=estado, transicion_id=f"c{i}",
            motivo="avance por camino legal", actor=ActorAsiento.SISTEMA, timestamp=T0,
        )
    assert match.estado_actual is origen
    transicionar(
        match, a_estado=destino, transicion_id="ilegal",
        motivo="intento ilegal", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )


def test_terminal_descartada_no_admite_ninguna_transicion():
    match = _match_inicial()
    match = transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta", actor=ActorAsiento.IA, timestamp=T0,
    )
    match = transicionar(
        match, a_estado=EstadoMatch.DESCARTADA, transicion_id="t2",
        motivo="descartada", actor=ActorAsiento.ENTIDAD, timestamp=T0,
    )
    for destino in EstadoMatch:
        with pytest.raises(TransicionIlegalError):
            transicionar(
                match, a_estado=destino, transicion_id="x",
                motivo="no debería aplicar", actor=ActorAsiento.SISTEMA, timestamp=T0,
            )


def test_reintento_tras_descartada_es_match_nuevo():
    descartado = _match_inicial()
    descartado = transicionar(
        descartado, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta", actor=ActorAsiento.IA, timestamp=T0,
    )
    descartado = transicionar(
        descartado, a_estado=EstadoMatch.DESCARTADA, transicion_id="t2",
        motivo="descartada", actor=ActorAsiento.ENTIDAD, timestamp=T0,
    )
    nuevo = crear_match(
        match_id="match-2",  # match nuevo, no reutiliza match_id
        entidad_id=descartado.entidad_id,
        convocatoria_id=descartado.convocatoria_id,
        transicion_id="t0-bis",
        motivo="reintento tras cambio de datos de la entidad",
        actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    assert nuevo.match_id != descartado.match_id
    assert nuevo.estado_actual is EstadoMatch.DETECTADA
    # el histórico del match descartado no se toca
    assert descartado.estado_actual is EstadoMatch.DESCARTADA
    assert len(descartado.asientos) == 3  # detectada -> propuesta -> descartada


def test_asientos_es_estructura_solo_anadir_no_mutable():
    match = _match_inicial()
    asientos_originales = match.asientos
    with pytest.raises(TypeError):
        match.asientos[0] = match.asientos[0]  # tupla: no admite asignación por índice
    with pytest.raises(dataclasses.FrozenInstanceError):
        match.asientos = ()  # dataclass frozen: no admite reasignación de campo
    # transicionar no muta el objeto original
    transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta", actor=ActorAsiento.IA, timestamp=T0,
    )
    assert match.asientos == asientos_originales
    assert match.estado_actual is EstadoMatch.DETECTADA


def test_transicionar_no_reescribe_asiento_existente_devuelve_nuevo_objeto():
    original = _match_inicial()
    siguiente = transicionar(
        original, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta", actor=ActorAsiento.IA, timestamp=T0,
    )
    assert siguiente is not original
    assert original.asientos[0] is siguiente.asientos[0]  # mismo asiento inicial, no reescrito
    assert len(original.asientos) == 1
    assert len(siguiente.asientos) == 2
