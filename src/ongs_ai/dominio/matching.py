"""Servicio de detección de matches — ADR-001 §1.4, F3.

Determinista: ids y timestamps SIEMPRE inyectados (nunca `datetime.now()` ni
`uuid4()` implícitos en dominio). La capa IA es opcional y nunca decide
elegibilidad ni lanza al dominio: si falla o no está configurada, el Match
resultante simplemente no lleva `explicacion_ia`.

`GeneradorExplicacion` se redefine aquí (Protocol local, estructuralmente
compatible con `ongs_ai.ia.explicacion_match.GeneradorExplicacion`) para que
este módulo de dominio no importe el paquete `ia` — dominio puro (CLAUDE.md).
La transición `detectada -> propuesta` es F4, no se implementa aquí.
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime
from typing import Callable, Iterable, Protocol

from ongs_ai.dominio.elegibilidad import evaluar_elegibilidad
from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    Match,
    ResultadoElegibilidad,
    crear_match,
)


class GeneradorExplicacion(Protocol):
    def generar(
        self, entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
    ) -> str: ...


def detectar_matches(
    entidades: Iterable[Entidad],
    convocatorias: Iterable[Convocatoria],
    fecha_referencia: date,
    *,
    generador_ids: Callable[[], str],
    reloj: Callable[[], datetime],
    generador_explicacion: GeneradorExplicacion | None = None,
) -> list[Match]:
    """Evalúa cada pareja Entidad×Convocatoria y crea un Match `detectada` por pareja.

    `resultado_elegibilidad_dura` SIEMPRE informado (guardarraíl determinista);
    `explicacion_ia` solo se rellena si la pareja es elegible y el generador
    responde con texto no vacío sin lanzar excepción.
    """
    matches: list[Match] = []
    for entidad in entidades:
        for convocatoria in convocatorias:
            resultado = evaluar_elegibilidad(entidad, convocatoria, fecha_referencia)

            explicacion_ia: str | None = None
            if resultado.elegible and generador_explicacion is not None:
                try:
                    texto = generador_explicacion.generar(entidad, convocatoria, resultado)
                except Exception:
                    texto = None
                explicacion_ia = texto or None

            match = crear_match(
                match_id=generador_ids(),
                entidad_id=entidad.entidad_id,
                convocatoria_id=convocatoria.convocatoria_id,
                transicion_id=generador_ids(),
                motivo="convocatoria detectada por matching determinista (F3)",
                actor=ActorAsiento.SISTEMA,
                timestamp=reloj(),
            )
            match = dataclasses.replace(
                match,
                resultado_elegibilidad_dura=resultado,
                explicacion_ia=explicacion_ia,
            )
            matches.append(match)
    return matches
