"""Servicio de autenticación — magic link (ADR-005 §2.2/§5).

Compone puertos (RepositorioEntidades, RepositorioTokensAcceso) con un
enviador de enlace inyectable — no es dominio puro, mismo patrón que
`servicios/propuestas.py`. Ids/token/reloj SIEMPRE inyectados (CLAUDE.md).

Anti user-enumeration (ADR §2.2/§2.4): si el email no existe,
`generar_y_enviar_enlace` no hace nada — el llamador HTTP responde SIEMPRE
el mismo mensaje genérico, exista o no la entidad, haya fallado o no el envío.

Solo se persiste el HASH del token (sha256), nunca el valor en claro.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Protocol

from ongs_ai.dominio.entidades import Entidad
from ongs_ai.dominio.puertos import RepositorioEntidades, RepositorioTokensAcceso

logger = logging.getLogger(__name__)

TTL_TOKEN_DEFECTO = timedelta(minutes=60)


class EnviadorEnlaceAcceso(Protocol):
    def enviar_enlace_acceso(self, entidad: Entidad, token: str) -> None: ...


@dataclass
class EnlaceRegistrado:
    entidad_id: str
    token: str


@dataclass
class EnviadorEnlaceAccesoStub:
    """Registra cada enlace en `enlaces` en vez de enviarlo — sin red (CLAUDE.md)."""

    enlaces: list[EnlaceRegistrado] = field(default_factory=list)

    def enviar_enlace_acceso(self, entidad: Entidad, token: str) -> None:
        self.enlaces.append(EnlaceRegistrado(entidad_id=entidad.entidad_id, token=token))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generar_y_enviar_enlace(
    email: str,
    almacen_entidades: RepositorioEntidades,
    almacen_tokens: RepositorioTokensAcceso,
    enviador_email: EnviadorEnlaceAcceso,
    *,
    generador_token: Callable[[], str],
    reloj: Callable[[], datetime],
    ttl: timedelta = TTL_TOKEN_DEFECTO,
) -> None:
    """Si el email no existe (o es ambiguo entre entidades), no hace nada — el
    llamador HTTP responde igual en ambos casos (ADR-005 §2.2/§2.4)."""
    entidad = almacen_entidades.obtener_entidad_por_email(email)
    if entidad is None:
        return

    token = generador_token()
    almacen_tokens.crear_token(entidad.entidad_id, _hash_token(token), reloj() + ttl)

    try:
        enviador_email.enviar_enlace_acceso(entidad, token)
    except Exception:
        # Degrada limpio (CLAUDE.md): el enviador ya degrada por su cuenta,
        # esta es una red de seguridad adicional, igual patrón que
        # `_notificar_seguro` en servicios/propuestas.py.
        logger.warning(
            "Fallo enviando enlace de acceso (entidad=%s)", entidad.entidad_id, exc_info=True
        )


def validar_y_consumir_token(
    token: str,
    almacen_tokens: RepositorioTokensAcceso,
    reloj: Callable[[], datetime],
) -> str | None:
    return almacen_tokens.consumir_token(_hash_token(token), reloj())
