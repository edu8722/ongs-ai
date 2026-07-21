"""Tests de `EnviadorEnlaceAccesoSMTP` — ADR-005 §2.2/§5.

Mismo patrón que `test_notificador_email.py`: el cliente SMTP se INYECTA, NUNCA
se abre un socket real (CLAUDE.md: tests herméticos). Cubre la plantilla pura
(sin campos internos) y el envío/degradación (sin email, SMTP que lanza).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from ongs_ai.adapters.avisos.email_smtp import ConfiguracionSMTP
from ongs_ai.adapters.avisos.enlace_acceso import (
    ConfiguracionEnlaceAcceso,
    EnviadorEnlaceAccesoSMTP,
    construir_aviso_enlace_acceso,
    construir_enlace_acceso,
)
from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    DatosEconomicos,
    Entidad,
    FormaJuridica,
    FormaJuridicaDeclarada,
    RequisitoFormal,
    TipoActividad,
)

AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)


class _ClienteSMTPStub:
    def __init__(self, *, fallar_en: str | None = None) -> None:
        self._fallar_en = fallar_en
        self.starttls_llamado = False
        self.login_llamado_con: tuple[str, str] | None = None
        self.mensajes_enviados: list = []

    def __enter__(self) -> "_ClienteSMTPStub":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self) -> None:
        if self._fallar_en == "starttls":
            raise RuntimeError("fallo simulado STARTTLS")
        self.starttls_llamado = True

    def login(self, usuario: str, contrasena: str) -> None:
        self.login_llamado_con = (usuario, contrasena)

    def send_message(self, mensaje) -> None:
        if self._fallar_en == "send_message":
            raise RuntimeError("fallo simulado envío")
        self.mensajes_enviados.append(mensaje)


def _entidad(email: str | None = "contacto@example.org") -> Entidad:
    return Entidad(
        entidad_id="ent-enlace-1",
        nombre_legal="Asociación de Prueba de Enlace",
        nif="B22222222",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 1, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email=email),
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


def _config_smtp() -> ConfiguracionSMTP:
    return ConfiguracionSMTP(
        host="smtp.example.org", puerto=587, remitente="avisos@ongs-ai.example",
        usuario="avisos@ongs-ai.example", contrasena="secreto-de-test",
    )


def _config_enlace() -> ConfiguracionEnlaceAcceso:
    return ConfiguracionEnlaceAcceso(base_url="https://app.ongs-ai.example", ttl_minutos=60)


# --- Plantilla (función pura) ---------------------------------------------


def test_construir_enlace_acceso_forma_url_correcta():
    assert (
        construir_enlace_acceso("https://app.ongs-ai.example", "tok-abc")
        == "https://app.ongs-ai.example/login/confirmar?token=tok-abc"
    )
    # Sin barra final duplicada si base_url ya la trae.
    assert (
        construir_enlace_acceso("https://app.ongs-ai.example/", "tok-abc")
        == "https://app.ongs-ai.example/login/confirmar?token=tok-abc"
    )


def test_plantilla_incluye_enlace_y_caducidad():
    entidad = _entidad()
    enlace = construir_enlace_acceso("https://app.ongs-ai.example", "tok-xyz")

    aviso = construir_aviso_enlace_acceso(entidad, enlace, ttl_minutos=60)

    assert entidad.nombre_legal in aviso.cuerpo
    assert enlace in aviso.cuerpo
    assert "60" in aviso.cuerpo


def test_plantilla_no_expone_ids_de_sistema():
    entidad = _entidad()
    enlace = construir_enlace_acceso("https://app.ongs-ai.example", "tok-xyz")

    aviso = construir_aviso_enlace_acceso(entidad, enlace, ttl_minutos=60)
    texto_completo = aviso.asunto + "\n" + aviso.cuerpo

    assert entidad.entidad_id not in texto_completo
    assert "coste" not in texto_completo.lower()
    assert "costo" not in texto_completo.lower()


# --- Envío (cliente SMTP inyectado, sin red) -------------------------------


def test_envio_feliz_llama_starttls_login_y_send_message():
    entidad = _entidad()
    cliente = _ClienteSMTPStub()
    enviador = EnviadorEnlaceAccesoSMTP(
        _config_smtp(), _config_enlace(), fabrica_cliente=lambda: cliente
    )

    enviador.enviar_enlace_acceso(entidad, "tok-envio-feliz")

    assert cliente.starttls_llamado is True
    assert len(cliente.mensajes_enviados) == 1
    mensaje = cliente.mensajes_enviados[0]
    assert mensaje["To"] == entidad.contacto.email
    assert "tok-envio-feliz" in mensaje.get_content()
    assert enviador.enviados == 1
    assert enviador.fallidos == 0


def test_entidad_sin_email_degrada_limpio_sin_llamar_al_cliente():
    entidad = _entidad(email=None)
    cliente = _ClienteSMTPStub()
    enviador = EnviadorEnlaceAccesoSMTP(
        _config_smtp(), _config_enlace(), fabrica_cliente=lambda: cliente
    )

    enviador.enviar_enlace_acceso(entidad, "tok-sin-email")  # no debe lanzar

    assert enviador.omitidos_sin_email == 1
    assert enviador.enviados == 0
    assert cliente.mensajes_enviados == []


def test_smtp_que_lanza_degrada_limpio_sin_propagar_excepcion():
    entidad = _entidad()
    cliente = _ClienteSMTPStub(fallar_en="send_message")
    enviador = EnviadorEnlaceAccesoSMTP(
        _config_smtp(), _config_enlace(), fabrica_cliente=lambda: cliente
    )

    enviador.enviar_enlace_acceso(entidad, "tok-fallo")  # no debe lanzar

    assert enviador.fallidos == 1
    assert enviador.enviados == 0
