"""Adapter de persistencia en memoria pura — para tests. Sin red, sin disco."""
from __future__ import annotations

from datetime import datetime

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match


class AlmacenMemoria:
    """Implementa RepositorioEntidades + RepositorioConvocatorias + RepositorioMatches
    + RepositorioTokensAcceso."""

    def __init__(self) -> None:
        self._entidades: dict[str, Entidad] = {}
        self._convocatorias: dict[str, Convocatoria] = {}
        self._matches: dict[str, Match] = {}
        self._tokens_acceso: dict[str, dict] = {}
        self.entidades_duplicadas_por_email = 0

    # Entidades ------------------------------------------------------
    def guardar_entidad(self, entidad: Entidad) -> None:
        self._entidades[entidad.entidad_id] = entidad

    def obtener_entidad(self, entidad_id: str) -> Entidad | None:
        return self._entidades.get(entidad_id)

    def obtener_entidad_por_email(self, email: str) -> Entidad | None:
        """Login por email (ADR-005 §5). Email duplicado entre entidades =
        login ambiguo: decisión conservadora, devuelve None y lo cuenta —
        nunca elige una entidad al azar entre coincidencias."""
        coincidencias = [e for e in self._entidades.values() if e.contacto.email == email]
        if len(coincidencias) != 1:
            if len(coincidencias) > 1:
                self.entidades_duplicadas_por_email += 1
            return None
        return coincidencias[0]

    def listar_entidades(self) -> list[Entidad]:
        return list(self._entidades.values())

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

    # Tokens de acceso (magic link) — ADR-005 §5 ------------------------
    def crear_token(self, entidad_id: str, token_hash: str, expira_en: datetime) -> None:
        self._tokens_acceso[token_hash] = {
            "entidad_id": entidad_id,
            "expira_en": expira_en,
            "usado": False,
        }

    def consumir_token(self, token_hash: str, ahora: datetime) -> str | None:
        registro = self._tokens_acceso.get(token_hash)
        if registro is None or registro["usado"] or ahora >= registro["expira_en"]:
            return None
        registro["usado"] = True
        return registro["entidad_id"]
