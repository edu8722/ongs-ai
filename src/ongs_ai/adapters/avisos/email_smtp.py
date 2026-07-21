"""Notificador por email real — ADR-004 §2.6, F4.2.

Implementa el Protocol `Notificador` (`servicios/notificacion.py`) sobre
SMTP estándar (`smtplib` de stdlib, STARTTLS). El cliente SMTP se INYECTA vía
`fabrica_cliente` (mismo patrón que el backend de persistencia, CLAUDE.md):
en producción crea un `smtplib.SMTP` real; en tests, un stub que registra los
envíos sin abrir ningún socket. TODA la configuración (host, puerto,
credenciales, remitente) llega por `ConfiguracionSMTP` — este módulo nunca
lee variables de entorno ni hardcodea nada; eso es responsabilidad exclusiva
de la factory de composición (`factory.py`).

Destinatario: `entidad.contacto.email`. Si la entidad no tiene email, o si el
envío SMTP falla, se degrada limpio (log + contador, sin excepción — regla de
oro CLAUDE.md: nunca rompe la pasada de detección-y-propuesta).

La plantilla (`construir_aviso_email`) es una función PURA, testeable aparte
del envío: solo objeto de la convocatoria, portal, fecha de cierre, cuantías
(si existen) y la `explicacion_ia` del match (si existe) — nunca ids de
sistema ni costes internos.
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable, Protocol

from ongs_ai.dominio.entidades import Convocatoria, Cuantias, Entidad
from ongs_ai.dominio.matching_estado import Match

logger = logging.getLogger(__name__)


class ClienteSMTP(Protocol):
    """Superficie mínima de `smtplib.SMTP` que este adapter necesita."""

    def starttls(self) -> None: ...

    def login(self, usuario: str, contrasena: str) -> None: ...

    def send_message(self, mensaje: EmailMessage) -> None: ...

    def __enter__(self) -> "ClienteSMTP": ...

    def __exit__(self, *args: object) -> None: ...


FabricaClienteSMTP = Callable[[], ClienteSMTP]


@dataclass(frozen=True)
class ConfiguracionSMTP:
    """TODA la configuración de conexión — nunca hardcodeada (CLAUDE.md)."""

    host: str
    puerto: int
    remitente: str
    usuario: str | None = None
    contrasena: str | None = None
    usar_starttls: bool = True


@dataclass(frozen=True)
class AvisoEmail:
    asunto: str
    cuerpo: str


def _importe_desde_centimos(centimos: int) -> str:
    """Formatea céntimos como euros sin pasar por float (regla de oro dinero)."""
    euros, resto_centimos = divmod(centimos, 100)
    return f"{euros}.{resto_centimos:02d} €"


def _porcentaje_desde_puntos_basicos(puntos_basicos: int) -> str:
    """8000 puntos básicos -> "80%"; 8050 -> "80.50%" (sin float)."""
    entero, resto = divmod(puntos_basicos, 100)
    if resto:
        return f"{entero}.{resto:02d}%"
    return f"{entero}%"


def _lineas_cuantias(cuantias: Cuantias) -> list[str]:
    lineas: list[str] = []
    minimo = cuantias.importe_minimo_centimos
    maximo = cuantias.importe_maximo_centimos
    if minimo is not None and maximo is not None:
        lineas.append(
            f"Cuantía: entre {_importe_desde_centimos(minimo)} y {_importe_desde_centimos(maximo)}"
        )
    elif maximo is not None:
        lineas.append(f"Cuantía máxima: {_importe_desde_centimos(maximo)}")
    elif minimo is not None:
        lineas.append(f"Cuantía mínima: {_importe_desde_centimos(minimo)}")
    if cuantias.porcentaje_max_financiable is not None:
        lineas.append(
            f"Financiación máxima: {_porcentaje_desde_puntos_basicos(cuantias.porcentaje_max_financiable)}"
        )
    return lineas


def construir_aviso_email(entidad: Entidad, convocatoria: Convocatoria, match: Match) -> AvisoEmail:
    """Función PURA: plantilla de texto plano, testeable sin enviar nada.

    Sin datos internos (ids de sistema, costes de la plataforma) — solo lo
    que le sirve a la entidad para decidir (ADR-004 §2.5, canal email).
    """
    asunto = f"Nueva propuesta de subvención: {convocatoria.objeto}"

    fecha_cierre = convocatoria.plazos.fecha_cierre
    lineas = [
        f"Hola {entidad.nombre_legal},",
        "",
        "Hemos detectado una convocatoria compatible con tu entidad:",
        "",
        f"Convocatoria: {convocatoria.objeto}",
        f"Portal: {convocatoria.fuente.portal}",
        f"Fecha de cierre: {fecha_cierre.isoformat() if fecha_cierre else 'no especificada'}",
    ]
    lineas.extend(_lineas_cuantias(convocatoria.cuantias))
    if match.explicacion_ia:
        lineas.extend(["", match.explicacion_ia])
    lineas.extend(["", "-- ", "Aviso automático de ONGs-AI."])

    return AvisoEmail(asunto=asunto, cuerpo="\n".join(lineas))


class NotificadorEmailSMTP:
    """`Notificador` (Protocol) real sobre SMTP — ADR-004 §2.6, F4.2."""

    def __init__(
        self,
        config: ConfiguracionSMTP,
        *,
        fabrica_cliente: FabricaClienteSMTP | None = None,
    ) -> None:
        self._config = config
        self._fabrica_cliente = fabrica_cliente or self._crear_cliente_real
        self.enviados = 0
        self.omitidos_sin_email = 0
        self.fallidos = 0

    def _crear_cliente_real(self) -> ClienteSMTP:
        return smtplib.SMTP(self._config.host, self._config.puerto, timeout=10)

    def notificar_propuesta(self, entidad: Entidad, convocatoria: Convocatoria, match: Match) -> None:
        destinatario = entidad.contacto.email
        if not destinatario:
            self.omitidos_sin_email += 1
            logger.warning(
                "Entidad %s sin email de contacto: aviso de propuesta omitido", entidad.entidad_id
            )
            return

        aviso = construir_aviso_email(entidad, convocatoria, match)
        mensaje = EmailMessage()
        mensaje["Subject"] = aviso.asunto
        mensaje["From"] = self._config.remitente
        mensaje["To"] = destinatario
        mensaje.set_content(aviso.cuerpo)

        try:
            with self._fabrica_cliente() as cliente:
                if self._config.usar_starttls:
                    cliente.starttls()
                if self._config.usuario:
                    cliente.login(self._config.usuario, self._config.contrasena or "")
                cliente.send_message(mensaje)
        except Exception:
            self.fallidos += 1
            logger.warning(
                "Fallo SMTP notificando propuesta (match=%s, entidad=%s)",
                match.match_id,
                entidad.entidad_id,
                exc_info=True,
            )
            return

        self.enviados += 1
