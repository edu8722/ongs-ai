"""Read model del panel — ADR-004 §2.5/§2.7, F4.2.

Consultas de SOLO LECTURA sobre `RepositorioMatches`, SIEMPRE por
`entidad_id` (aislamiento por tenant, CLAUDE.md: ninguna lectura de dominio
sin `tenant_id` explícito). Pura composición de lo existente
(`listar_matches_por_entidad`) — sin nuevas consultas de puerto ni cambio de
esquema.

Agrupación por estado (ADR-004 §2.3/§2.5 — lo que el panel necesita ver):
    - `propuestas_pendientes`: PROPUESTA (elegibles, ya avisadas, esperando
      decisión de la entidad).
    - `en_preparacion`: EN_PREPARACION.
    - `presentadas`: PRESENTADA (terminal).
    - `descartadas`: DESCARTADA (terminal).
    - `detectadas_no_elegibles`: DETECTADA con `resultado_elegibilidad_dura`
      no elegible — el "casi" con su motivo (ADR-004 §2.3, "no elegible").
      DETECTADA elegible es transitorio (el orquestador la promueve en el
      acto) y no debería sobrevivir a una pasada; si apareciera, se omite de
      este cubo (no hay motivo de "no elegible" que mostrar) en vez de
      lanzar (regla de oro: degrada limpio).

Cada lista ordenada por la fecha del último asiento del match
(`match.asientos[-1].timestamp`), MÁS RECIENTE PRIMERO — decisión
conservadora documentada: no la fija el ADR, y "lo más reciente arriba" es
el orden estándar de un panel de actividad.

NOTA de alcance (dejada fuera, ver resumen de cierre): ACEPTADA no tiene
cubo propio en este read model — el prompt de F4.2 solo enumera los cinco
anteriores. Un match en ACEPTADA no aparece en ningún cubo por ahora.
"""
from __future__ import annotations

from dataclasses import dataclass

from ongs_ai.dominio.matching_estado import EstadoMatch, Match
from ongs_ai.dominio.puertos import RepositorioMatches


@dataclass(frozen=True)
class ResumenPanel:
    propuestas_pendientes: tuple[Match, ...]
    en_preparacion: tuple[Match, ...]
    presentadas: tuple[Match, ...]
    descartadas: tuple[Match, ...]
    detectadas_no_elegibles: tuple[Match, ...]


def _mas_recientes_primero(matches: list[Match]) -> tuple[Match, ...]:
    return tuple(sorted(matches, key=lambda m: m.asientos[-1].timestamp, reverse=True))


def resumen_panel(entidad_id: str, almacen: RepositorioMatches) -> ResumenPanel:
    matches_por_estado: dict[EstadoMatch, list[Match]] = {}
    for match in almacen.listar_matches_por_entidad(entidad_id):
        matches_por_estado.setdefault(match.estado_actual, []).append(match)

    detectadas_no_elegibles = [
        match
        for match in matches_por_estado.get(EstadoMatch.DETECTADA, [])
        if match.resultado_elegibilidad_dura is not None
        and not match.resultado_elegibilidad_dura.elegible
    ]

    return ResumenPanel(
        propuestas_pendientes=_mas_recientes_primero(
            matches_por_estado.get(EstadoMatch.PROPUESTA, [])
        ),
        en_preparacion=_mas_recientes_primero(
            matches_por_estado.get(EstadoMatch.EN_PREPARACION, [])
        ),
        presentadas=_mas_recientes_primero(matches_por_estado.get(EstadoMatch.PRESENTADA, [])),
        descartadas=_mas_recientes_primero(matches_por_estado.get(EstadoMatch.DESCARTADA, [])),
        detectadas_no_elegibles=_mas_recientes_primero(detectadas_no_elegibles),
    )
