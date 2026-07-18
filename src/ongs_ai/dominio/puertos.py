"""Puertos de persistencia — el dominio depende de estos Protocol, no de un adapter concreto."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match


@runtime_checkable
class RepositorioEntidades(Protocol):
    def guardar_entidad(self, entidad: Entidad) -> None: ...

    def obtener_entidad(self, entidad_id: str) -> Entidad | None: ...


@runtime_checkable
class RepositorioConvocatorias(Protocol):
    def guardar_convocatoria(self, convocatoria: Convocatoria) -> None: ...

    def obtener_convocatoria(self, convocatoria_id: str) -> Convocatoria | None: ...

    def obtener_por_url_origen(self, portal: str, url_origen: str) -> Convocatoria | None: ...


@runtime_checkable
class RepositorioMatches(Protocol):
    def guardar_match(self, match: Match) -> None: ...

    def listar_matches_por_entidad(self, entidad_id: str) -> list[Match]: ...
