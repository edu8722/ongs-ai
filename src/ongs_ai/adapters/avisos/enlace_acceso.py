"""Adapter de envío del enlace de acceso (magic link) — ADR-005 §2.2/§5.

Reutiliza `ClienteSMTP`/`ConfiguracionSMTP` de `email_smtp.py`; NO reutiliza
`Notificador.notificar_propuesta` (concepto de negocio distinto). Plantilla
de texto plano propia, función PURA testeable, sin datos internos (ids de
sistema, costes). Degradado limpio (log + contador) si el envío SMTP falla —
mismo patrón que `NotificadorEmailSMTP`.
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from ongs_ai.adapters.avisos.email_smtp import ClienteSMTP, ConfiguracionSMTP, FabricaClienteSMTP
from ongs_ai.dominio.entidades import Entidad

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfiguracionEnlaceAcceso:
    """URL pública base de la app — nunca hardcodeada (CLAUDE.md)."""

    base_url: str
    ttl_minutos: int = 60


@dataclass(frozen=True)
class AvisoEnlaceAcceso:
    asunto: str
    cuerpo: str


def construir_enlace_acceso(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/login/confirmar?token={token}"


def construir_aviso_enlace_acceso(
    entidad: Entidad, enlace: str, ttl_minutos: int
) -> AvisoEnlaceAcceso:
    """Función PURA: solo el enlace de un solo uso y su caducidad — sin ids
    de sistema ni costes internos (ADR-005 §2.4)."""
    asunto = "Tu enlace de acceso a ONGs-AI"
    cuerpo = "\n".join(
        [
            f"Hola {entidad.nombre_legal},",
            "",
            "Hemos recibido una solicitud de acceso a tu panel de ONGs-AI.",
            f"Usa este enlace para entrar (caduca en {ttl_minutos} minutos y "
            "solo se puede usar una vez):",
            "",
            enlace,
            "",
            "Si no has solicitado este acceso, puedes ignorar este correo.",
            "",
            "-- ",
            "Aviso automático de ONGs-AI.",
        ]
    )
    return AvisoEnlaceAcceso(asunto=asunto, cuerpo=cuerpo)


class EnviadorEnlaceAccesoSMTP:
    """Envía el magic link por SMTP — mismo degradado limpio que `NotificadorEmailSMTP`."""

    def __init__(
        self,
        config_smtp: ConfiguracionSMTP,
        config_enlace: ConfiguracionEnlaceAcceso,
        *,
        fabrica_cliente: FabricaClienteSMTP | None = None,
    ) -> None:
        self._config_smtp = config_smtp
        self._config_enlace = config_enlace
        self._fabrica_cliente = fabrica_cliente or self._crear_cliente_real
        self.enviados = 0
        self.omitidos_sin_email = 0
        self.fallidos = 0

    def _crear_cliente_real(self) -> ClienteSMTP:
        return smtplib.SMTP(self._config_smtp.host, self._config_smtp.puerto, timeout=10)

    def enviar_enlace_acceso(self, entidad: Entidad, token: str) -> None:
        destinatario = entidad.contacto.email
        if not destinatario:
            self.omitidos_sin_email += 1
            logger.warning(
                "Entidad %s sin email de contacto: enlace de acceso omitido", entidad.entidad_id
            )
            return

        enlace = construir_enlace_acceso(self._config_enlace.base_url, token)
        aviso = construir_aviso_enlace_acceso(entidad, enlace, self._config_enlace.ttl_minutos)
        mensaje = EmailMessage()
        mensaje["Subject"] = aviso.asunto
        mensaje["From"] = self._config_smtp.remitente
        mensaje["To"] = destinatario
        mensaje.set_content(aviso.cuerpo)

        try:
            with self._fabrica_cliente() as cliente:
                if self._config_smtp.usar_starttls:
                    cliente.starttls()
                if self._config_smtp.usuario:
                    cliente.login(self._config_smtp.usuario, self._config_smtp.contrasena or "")
                cliente.send_message(mensaje)
        except Exception:
            self.fallidos += 1
            logger.warning(
                "Fallo SMTP enviando enlace de acceso (entidad=%s)",
                entidad.entidad_id,
                exc_info=True,
            )
            return

        self.enviados += 1
