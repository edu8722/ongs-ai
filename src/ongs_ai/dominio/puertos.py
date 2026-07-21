"""Puertos de persistencia — el dominio depende de estos Protocol, no de un adapter concreto."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match


@runtime_checkable
class RepositorioEntidades(Protocol):
    def guardar_entidad(self, entidad: Entidad) -> None: ...

    def obtener_entidad(self, entidad_id: str) -> Entidad | None: ...

    def obtener_entidad_por_email(self, email: str) -> Entidad | None: ...

    def listar_entidades(self) -> list[Entidad]:
        """Todas las entidades del tenant único de plataforma (multi-tenant a
        nivel de entidad, no de instalación) — PROMPT-018: el runner de
        ingesta necesita evaluar cada convocatoria nueva contra TODAS las
        entidades registradas."""
        ...


@runtime_checkable
class RepositorioConvocatorias(Protocol):
    def guardar_convocatoria(self, convocatoria: Convocatoria) -> None: ...

    def obtener_convocatoria(self, convocatoria_id: str) -> Convocatoria | None: ...

    def obtener_por_url_origen(self, portal: str, url_origen: str) -> Convocatoria | None: ...

    def listar_convocatorias(self) -> list[Convocatoria]:
        """Lectura aditiva (ADR-006 §2.7), NO cambio de contrato: la consola
        del operador necesita el cruce global perfil×convocatoria."""
        ...


@runtime_checkable
class RepositorioMatches(Protocol):
    def guardar_match(self, match: Match) -> None: ...

    def listar_matches_por_entidad(self, entidad_id: str) -> list[Match]: ...


@runtime_checkable
class RepositorioTokensAcceso(Protocol):
    """Infraestructura de auth (ADR-005 §5) — NO forma parte del contrato congelado."""

    def crear_token(self, entidad_id: str, token_hash: str, expira_en: datetime) -> None: ...

    def consumir_token(self, token_hash: str, ahora: datetime) -> str | None:
        """Atómico: si existe, no expiró y no se ha usado, lo marca usado y
        devuelve `entidad_id`; en cualquier otro caso devuelve None (un solo
        uso posible por token)."""
        ...
