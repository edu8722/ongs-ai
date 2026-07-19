"""Puerto de notificación de propuestas — ADR-004 §2.6.

El aviso de una propuesta (match `detectada -> propuesta`) sale por este
puerto inyectable. El email real se difiere a F4.2; aquí solo el Protocol y
un stub determinista para tests (mismo patrón que `ExplicadorStub` de la capa
IA, `ongs_ai.ia.explicacion_match`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match


class Notificador(Protocol):
    def notificar_propuesta(
        self, entidad: Entidad, convocatoria: Convocatoria, match: Match
    ) -> None: ...


@dataclass
class AvisoRegistrado:
    entidad_id: str
    convocatoria_id: str
    match_id: str


@dataclass
class NotificadorStub:
    """Registra cada aviso en `avisos` en vez de enviarlo — sin red (CLAUDE.md)."""

    avisos: list[AvisoRegistrado] = field(default_factory=list)

    def notificar_propuesta(
        self, entidad: Entidad, convocatoria: Convocatoria, match: Match
    ) -> None:
        self.avisos.append(
            AvisoRegistrado(
                entidad_id=entidad.entidad_id,
                convocatoria_id=convocatoria.convocatoria_id,
                match_id=match.match_id,
            )
        )
