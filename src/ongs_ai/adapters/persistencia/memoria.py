"""Adapter de persistencia en memoria pura — para tests. Sin red, sin disco."""
from __future__ import annotations

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match


class AlmacenMemoria:
    """Implementa RepositorioEntidades + RepositorioConvocatorias + RepositorioMatches."""

    def __init__(self) -> None:
        self._entidades: dict[str, Entidad] = {}
        self._convocatorias: dict[str, Convocatoria] = {}
        self._matches: dict[str, Match] = {}

    # Entidades ------------------------------------------------------
    def guardar_entidad(self, entidad: Entidad) -> None:
        self._entidades[entidad.entidad_id] = entidad

    def obtener_entidad(self, entidad_id: str) -> Entidad | None:
        return self._entidades.get(entidad_id)

    # Convocatorias (no son dato de tenant, ADR §4.2) -----------------
    def guardar_convocatoria(self, convocatoria: Convocatoria) -> None:
        self._convocatorias[convocatoria.convocatoria_id] = convocatoria

    def obtener_convocatoria(self, convocatoria_id: str) -> Convocatoria | None:
        return self._convocatorias.get(convocatoria_id)

    def obtener_por_url_origen(self, portal: str, url_origen: str) -> Convocatoria | None:
        """Clave natural de dedupe (ADR-001 §6.5): `portal`+`url_origen`."""
        for convocatoria in self._convocatorias.values():
            if convocatoria.fuente.portal == portal and convocatoria.fuente.url_origen == url_origen:
                return convocatoria
        return None

    # Matches — SIEMPRE filtrados por entidad_id ----------------------
    def guardar_match(self, match: Match) -> None:
        self._matches[match.match_id] = match

    def listar_matches_por_entidad(self, entidad_id: str) -> list[Match]:
        return [m for m in self._matches.values() if m.entidad_id == entidad_id]
