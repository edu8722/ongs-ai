"""Puertos de persistencia — el dominio depende de estos Protocol, no de un adapter concreto."""
from __future__ import annotations

from typing import Protocol

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match


class RepositorioEntidades(Protocol):
    def guardar_entidad(self, entidad: Entidad) -> None: ...

    def obtener_entidad(self, entidad_id: str) -> Entidad | None: ...


class RepositorioConvocatorias(Protocol):
    def guardar_convocatoria(self, convocatoria: Convocatoria) -> None: ...

    def obtener_convocatoria(self, convocatoria_id: str) -> Convocatoria | None: ...


class RepositorioMatches(Protocol):
    def guardar_match(self, match: Match) -> None: ...

    def listar_matches_por_entidad(self, entidad_id: str) -> list[Match]: ...
