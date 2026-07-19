"""Orquestador de detección-y-propuesta — ADR-004 §5, F4.1.

NO es dominio puro: compone puertos (`RepositorioMatches`, `Notificador`) con
el guardarraíl determinista (`evaluar_elegibilidad`) y la máquina de estados
de F3, igual que `adapters/ingesta/servicio.py` compone una fuente con un
puerto de persistencia. Ids y reloj SIEMPRE inyectados (CLAUDE.md).

Algoritmo por entidad (ADR-004 §2.2-§2.4):
    1. Indexar en memoria los matches ya persistidos de la entidad, por
       `convocatoria_id`.
    2. PRE-PUERTA: solo convocatorias `VERIFICADA` con plazo abierto entran a
       evaluación; el resto se cuenta y se ignora (ni se evalúa ni se
       persiste).
    3. Por pareja: si hay un match ACTIVO (estado no terminal), se
       actualiza/transiciona in-place; si solo hay un match TERMINAL
       (`descartada`/`presentada`), se respeta y no se hace nada; si no hay
       match, se crea uno nuevo.
    4. La transición `detectada -> propuesta` (elegible en la creación o
       sobrevenida en una re-detección) siempre notifica; una `propuesta` que
       sigue elegible NO re-avisa; una regresión (elegible -> no elegible en
       un match ya avanzado) actualiza el resultado sin retroceder de estado
       ni avisar.
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Iterable

from ongs_ai.dominio.elegibilidad import evaluar_elegibilidad
from ongs_ai.dominio.entidades import Convocatoria, Entidad, EstadoIngesta
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    EstadoMatch,
    Match,
    ResultadoElegibilidad,
    crear_match,
    transicionar,
)
from ongs_ai.dominio.puertos import RepositorioMatches
from ongs_ai.ia.explicacion_match import GeneradorExplicacion
from ongs_ai.servicios.notificacion import Notificador

logger = logging.getLogger(__name__)

_ESTADOS_TERMINALES = frozenset({EstadoMatch.DESCARTADA, EstadoMatch.PRESENTADA})


@dataclass(frozen=True)
class ResumenPropuestas:
    """Contadores de una pasada de `detectar_y_proponer` (documentados en ADR-004 §5).

    - `nuevas_propuestas`: parejas sin match previo, elegibles en esta misma
      pasada → match creado directamente en `propuesta` + aviso.
    - `propuestas_sobrevenidas`: match activo que estaba en `detectada` (no
      elegible en una pasada anterior) y pasa a elegible ahora → transiciona
      a `propuesta` + aviso (ADR-004 §2.4).
    - `no_elegibles_persistidas`: parejas (nuevas o ya existentes) que
      permanecen en `detectada` por no ser elegibles; se persiste el motivo,
      sin aviso.
    - `ya_existentes_sin_cambio`: match activo ya en `propuesta` (o posterior)
      que sigue elegible (no re-avisa), regresiones (elegible -> no elegible
      en un match ya avanzado, que NO retrocede de estado) y parejas con
      match TERMINAL (`descartada`/`presentada`) respetadas sin persistir.
    - `saltadas_pre_puerta`: pares entidad×convocatoria ignorados porque la
      convocatoria no está `VERIFICADA` o no tiene plazo abierto.
    """

    nuevas_propuestas: int
    propuestas_sobrevenidas: int
    no_elegibles_persistidas: int
    ya_existentes_sin_cambio: int
    saltadas_pre_puerta: int


def _pasa_pre_puerta(convocatoria: Convocatoria, fecha_referencia: date) -> bool:
    if convocatoria.estado_ingesta != EstadoIngesta.VERIFICADA:
        return False
    fecha_cierre = convocatoria.plazos.fecha_cierre
    if fecha_cierre is None:
        return False
    return fecha_cierre >= fecha_referencia


def _generar_explicacion(
    generador_explicacion: GeneradorExplicacion | None,
    entidad: Entidad,
    convocatoria: Convocatoria,
    resultado: ResultadoElegibilidad,
) -> str | None:
    if generador_explicacion is None:
        return None
    try:
        texto = generador_explicacion.generar(entidad, convocatoria, resultado)
    except Exception:
        texto = None
    return texto or None


def _notificar_seguro(
    notificador: Notificador, entidad: Entidad, convocatoria: Convocatoria, match: Match
) -> None:
    """Degrada limpio: un notificador que lanza nunca rompe la persistencia (CLAUDE.md)."""
    try:
        notificador.notificar_propuesta(entidad, convocatoria, match)
    except Exception:
        logger.warning(
            "Notificador falló para match %s (entidad=%s, convocatoria=%s)",
            match.match_id,
            entidad.entidad_id,
            convocatoria.convocatoria_id,
            exc_info=True,
        )


def detectar_y_proponer(
    entidades: Iterable[Entidad],
    convocatorias: Iterable[Convocatoria],
    fecha_referencia: date,
    almacen: RepositorioMatches,
    notificador: Notificador,
    *,
    generador_ids: Callable[[], str],
    reloj: Callable[[], datetime],
    generador_explicacion: GeneradorExplicacion | None = None,
) -> ResumenPropuestas:
    convocatorias = list(convocatorias)

    nuevas_propuestas = 0
    propuestas_sobrevenidas = 0
    no_elegibles_persistidas = 0
    ya_existentes_sin_cambio = 0
    saltadas_pre_puerta = 0

    for entidad in entidades:
        matches_por_convocatoria: dict[str, list[Match]] = {}
        for match_existente in almacen.listar_matches_por_entidad(entidad.entidad_id):
            matches_por_convocatoria.setdefault(match_existente.convocatoria_id, []).append(
                match_existente
            )

        for convocatoria in convocatorias:
            if not _pasa_pre_puerta(convocatoria, fecha_referencia):
                saltadas_pre_puerta += 1
                continue

            resultado = evaluar_elegibilidad(entidad, convocatoria, fecha_referencia)
            matches_pareja = matches_por_convocatoria.get(convocatoria.convocatoria_id, [])
            activo = next(
                (m for m in matches_pareja if m.estado_actual not in _ESTADOS_TERMINALES), None
            )
            existe_terminal = any(m.estado_actual in _ESTADOS_TERMINALES for m in matches_pareja)

            if activo is not None:
                match = dataclasses.replace(activo, resultado_elegibilidad_dura=resultado)

                if match.estado_actual == EstadoMatch.DETECTADA and resultado.elegible:
                    match = transicionar(
                        match,
                        a_estado=EstadoMatch.PROPUESTA,
                        transicion_id=generador_ids(),
                        motivo="propuesta automática: elegibilidad sobrevenida tras re-detección (F4)",
                        actor=ActorAsiento.SISTEMA,
                        timestamp=reloj(),
                    )
                    match = dataclasses.replace(
                        match,
                        explicacion_ia=_generar_explicacion(
                            generador_explicacion, entidad, convocatoria, resultado
                        ),
                    )
                    almacen.guardar_match(match)
                    _notificar_seguro(notificador, entidad, convocatoria, match)
                    propuestas_sobrevenidas += 1
                elif match.estado_actual == EstadoMatch.DETECTADA:
                    almacen.guardar_match(match)
                    no_elegibles_persistidas += 1
                else:
                    # PROPUESTA (u otro estado ya avanzado): ya avisado, o
                    # regresión que NO retrocede de estado ni avisa (ADR-004 §2.4).
                    almacen.guardar_match(match)
                    ya_existentes_sin_cambio += 1
            elif existe_terminal:
                # Respeta la conclusión humana/sistema: no resucita `descartada`
                # ni re-propone `presentada` (ADR-004 §2.2).
                ya_existentes_sin_cambio += 1
            else:
                match = crear_match(
                    match_id=generador_ids(),
                    entidad_id=entidad.entidad_id,
                    convocatoria_id=convocatoria.convocatoria_id,
                    transicion_id=generador_ids(),
                    motivo="convocatoria detectada por matching determinista (F4 orquestador)",
                    actor=ActorAsiento.SISTEMA,
                    timestamp=reloj(),
                )
                match = dataclasses.replace(match, resultado_elegibilidad_dura=resultado)

                if resultado.elegible:
                    match = transicionar(
                        match,
                        a_estado=EstadoMatch.PROPUESTA,
                        transicion_id=generador_ids(),
                        motivo="propuesta automática: elegible en primera detección (F4)",
                        actor=ActorAsiento.SISTEMA,
                        timestamp=reloj(),
                    )
                    match = dataclasses.replace(
                        match,
                        explicacion_ia=_generar_explicacion(
                            generador_explicacion, entidad, convocatoria, resultado
                        ),
                    )
                    almacen.guardar_match(match)
                    _notificar_seguro(notificador, entidad, convocatoria, match)
                    nuevas_propuestas += 1
                else:
                    almacen.guardar_match(match)
                    no_elegibles_persistidas += 1

    return ResumenPropuestas(
        nuevas_propuestas=nuevas_propuestas,
        propuestas_sobrevenidas=propuestas_sobrevenidas,
        no_elegibles_persistidas=no_elegibles_persistidas,
        ya_existentes_sin_cambio=ya_existentes_sin_cambio,
        saltadas_pre_puerta=saltadas_pre_puerta,
    )
