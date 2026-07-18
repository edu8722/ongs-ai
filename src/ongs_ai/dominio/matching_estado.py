"""Match/Propuesta — máquina de estados con asientos inmutables (ADR §1.4 + §6.4).

Transiciones legales EXACTAS:
    detectada       -> propuesta
    propuesta       -> aceptada
    propuesta       -> descartada
    aceptada        -> en_preparacion
    en_preparacion  -> presentada

`descartada` y `presentada` son terminales: ninguna transición sale de ellos.
El reintento tras `descartada` es un Match NUEVO (mismo Entidad+Convocatoria);
el histórico del Match anterior no se toca — no se implementa aquí, es
responsabilidad del llamador (crear_match de nuevo).

Cada transición añade un asiento nuevo; nunca se reescribe uno existente
(Match y Asiento son dataclasses frozen; `asientos` es una tupla).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ongs_ai.dominio.errores import TransicionIlegalError


class EstadoMatch(str, Enum):
    DETECTADA = "detectada"
    PROPUESTA = "propuesta"
    ACEPTADA = "aceptada"
    DESCARTADA = "descartada"
    EN_PREPARACION = "en_preparacion"
    PRESENTADA = "presentada"


class ActorAsiento(str, Enum):
    IA = "ia"
    ENTIDAD = "entidad"
    SISTEMA = "sistema"


TRANSICIONES_LEGALES: dict[EstadoMatch, frozenset[EstadoMatch]] = {
    EstadoMatch.DETECTADA: frozenset({EstadoMatch.PROPUESTA}),
    EstadoMatch.PROPUESTA: frozenset({EstadoMatch.ACEPTADA, EstadoMatch.DESCARTADA}),
    EstadoMatch.ACEPTADA: frozenset({EstadoMatch.EN_PREPARACION}),
    EstadoMatch.EN_PREPARACION: frozenset({EstadoMatch.PRESENTADA}),
    EstadoMatch.DESCARTADA: frozenset(),  # terminal
    EstadoMatch.PRESENTADA: frozenset(),  # terminal
}


@dataclass(frozen=True)
class Asiento:
    transicion_id: str
    de_estado: EstadoMatch | None  # None solo en el asiento inicial (detectada)
    a_estado: EstadoMatch
    motivo: str
    actor: ActorAsiento
    timestamp: datetime


@dataclass(frozen=True)
class ResultadoElegibilidad:
    """Salida del guardarraíl determinista — nunca de la IA (ADR §2)."""

    elegible: bool
    detalle: str


@dataclass(frozen=True)
class Match:
    match_id: str
    entidad_id: str
    convocatoria_id: str
    asientos: tuple[Asiento, ...]
    explicacion_ia: str | None = None
    resultado_elegibilidad_dura: ResultadoElegibilidad | None = None

    def __post_init__(self) -> None:
        if not self.asientos:
            raise TransicionIlegalError(
                "Match sin asientos: falta el asiento inicial 'detectada'"
            )

    @property
    def estado_actual(self) -> EstadoMatch:
        """Derivado del último asiento — nunca fuente de verdad independiente (ADR §1.4)."""
        return self.asientos[-1].a_estado

    @property
    def creado_en(self) -> datetime:
        """Del primer asiento (detectada), ADR §1.4."""
        return self.asientos[0].timestamp


def crear_match(
    *,
    match_id: str,
    entidad_id: str,
    convocatoria_id: str,
    transicion_id: str,
    motivo: str,
    actor: ActorAsiento,
    timestamp: datetime,
) -> Match:
    """Crea un Match nuevo en estado inicial `detectada`."""
    asiento_inicial = Asiento(
        transicion_id=transicion_id,
        de_estado=None,
        a_estado=EstadoMatch.DETECTADA,
        motivo=motivo,
        actor=actor,
        timestamp=timestamp,
    )
    return Match(
        match_id=match_id,
        entidad_id=entidad_id,
        convocatoria_id=convocatoria_id,
        asientos=(asiento_inicial,),
    )


def transicionar(
    match: Match,
    *,
    a_estado: EstadoMatch,
    transicion_id: str,
    motivo: str,
    actor: ActorAsiento,
    timestamp: datetime,
) -> Match:
    """Aplica una transición legal y devuelve un Match NUEVO con el asiento añadido.

    Nunca muta `match`: el asiento anterior permanece intacto en el objeto
    original. Lanza TransicionIlegalError si la transición no está permitida
    desde el estado actual (incluye transiciones desde estados terminales).
    """
    estado_actual = match.estado_actual
    legales = TRANSICIONES_LEGALES.get(estado_actual, frozenset())
    if a_estado not in legales:
        raise TransicionIlegalError(
            f"Transición ilegal: {estado_actual.value} -> {a_estado.value}"
        )
    nuevo_asiento = Asiento(
        transicion_id=transicion_id,
        de_estado=estado_actual,
        a_estado=a_estado,
        motivo=motivo,
        actor=actor,
        timestamp=timestamp,
    )
    return dataclasses.replace(match, asientos=match.asientos + (nuevo_asiento,))
