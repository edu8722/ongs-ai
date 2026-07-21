"""Factory de notificación por entorno — email real por defecto, stub en tests.

Mismo patrón que `adapters/persistencia/factory.py`: la config SMTP solo se
lee de variables de entorno AQUÍ (nunca en `email_smtp.py`, nunca
hardcodeada). Los tests NUNCA deben depender de esta función leyendo el .env
de la máquina: deben instanciar `NotificadorStub` directamente o pasar
`entorno='test'` explícito.
"""
from __future__ import annotations

import os

from ongs_ai.adapters.avisos.email_smtp import ConfiguracionSMTP, NotificadorEmailSMTP
from ongs_ai.servicios.notificacion import Notificador, NotificadorStub


def _configuracion_desde_entorno() -> ConfiguracionSMTP:
    return ConfiguracionSMTP(
        host=os.environ["ONGS_AI_SMTP_HOST"],
        puerto=int(os.environ.get("ONGS_AI_SMTP_PUERTO", "587")),
        remitente=os.environ["ONGS_AI_SMTP_REMITENTE"],
        usuario=os.environ.get("ONGS_AI_SMTP_USUARIO"),
        contrasena=os.environ.get("ONGS_AI_SMTP_CONTRASENA"),
    )


def crear_notificador(entorno: str | None = None) -> Notificador:
    """`entorno='test'` -> `NotificadorStub`; cualquier otro valor (incluida
    la ausencia) -> `NotificadorEmailSMTP` con config leída del entorno. Si
    `entorno` es None se lee de la variable ONGS_AI_ENV."""
    if entorno is None:
        entorno = os.environ.get("ONGS_AI_ENV", "")
    if entorno == "test":
        return NotificadorStub()
    return NotificadorEmailSMTP(_configuracion_desde_entorno())
