"""Tests de `NotificadorEmailSMTP` — ADR-004 §2.6, F4.2.

El cliente SMTP se INYECTA (`fabrica_cliente`): NUNCA se abre un socket real
(CLAUDE.md: tests herméticos, sin red). Cubre: la plantilla pura (contenido
correcto, sin campos internos), el envío feliz, la entidad sin email
(degrada limpio) y el SMTP que lanza (degrada limpio sin romper la pasada).
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

from ongs_ai.adapters.avisos.email_smtp import (
    ConfiguracionSMTP,
    NotificadorEmailSMTP,
    construir_aviso_email,
)
from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    Convocatoria,
    Cuantias,
    DatosEconomicos,
    Entidad,
    EstadoIngesta,
    FormaJuridica,
    FormaJuridicaDeclarada,
    Fuente,
    Plazos,
    RequisitoFormal,
    RequisitosElegibilidad,
    TipoActividad,
    TipoFuente,
)
from ongs_ai.dominio.matching_estado import ActorAsiento, crear_match, transicionar, EstadoMatch

AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)


class _ClienteSMTPStub:
    """Nunca abre socket: registra llamadas o lanza si se pide (para el test
    de degradación limpia)."""

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
        if self._fallar_en == "login":
            raise RuntimeError("fallo simulado login")
        self.login_llamado_con = (usuario, contrasena)

    def send_message(self, mensaje) -> None:
        if self._fallar_en == "send_message":
            raise RuntimeError("fallo simulado envío")
        self.mensajes_enviados.append(mensaje)


def _entidad(email: str | None = "contacto@example.org") -> Entidad:
    return Entidad(
        entidad_id="ent-email-1",
        nombre_legal="Asociación de Prueba de Email",
        nif="B11111111",
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


def _convocatoria(**overrides) -> Convocatoria:
    base = dict(
        convocatoria_id="conv-email-1",
        fuente=Fuente(
            portal="portal-email", url_origen="https://example.org/conv-email-1",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto="Ayudas de prueba para email",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(
            importe_minimo_centimos=50_000, importe_maximo_centimos=1_000_050,
            porcentaje_max_financiable=8050,
        ),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def _match_propuesta(*, explicacion_ia: str | None = "Esta entidad encaja porque...") -> object:
    match = crear_match(
        match_id="match-email-1",
        entidad_id="ent-email-1",
        convocatoria_id="conv-email-1",
        transicion_id="t0",
        motivo="detectada",
        actor=ActorAsiento.SISTEMA,
        timestamp=AHORA,
    )
    match = transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta automática", actor=ActorAsiento.SISTEMA, timestamp=AHORA,
    )
    if explicacion_ia is not None:
        match = dataclasses.replace(match, explicacion_ia=explicacion_ia)
    return match


def _config() -> ConfiguracionSMTP:
    return ConfiguracionSMTP(
        host="smtp.example.org", puerto=587, remitente="avisos@ongs-ai.example",
        usuario="avisos@ongs-ai.example", contrasena="secreto-de-test",
    )


# --- Plantilla (función pura) --------------------------------------------


def test_plantilla_incluye_datos_relevantes_y_explicacion_ia():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta()

    aviso = construir_aviso_email(entidad, convocatoria, match)

    assert convocatoria.objeto in aviso.asunto
    assert convocatoria.objeto in aviso.cuerpo
    assert convocatoria.fuente.portal in aviso.cuerpo
    assert "2026-12-31" in aviso.cuerpo
    assert "500.00" in aviso.cuerpo or "500.00 €" in aviso.cuerpo  # 50_000 centimos
    assert "10000.50" in aviso.cuerpo  # 1_000_050 centimos
    assert "80.50%" in aviso.cuerpo
    assert match.explicacion_ia in aviso.cuerpo


def test_plantilla_sin_explicacion_ia_no_falla_y_omite_seccion():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta(explicacion_ia=None)

    aviso = construir_aviso_email(entidad, convocatoria, match)

    assert convocatoria.objeto in aviso.cuerpo


def test_plantilla_sin_cuantias_no_incluye_lineas_de_cuantia():
    entidad = _entidad()
    convocatoria = _convocatoria(cuantias=Cuantias())
    match = _match_propuesta()

    aviso = construir_aviso_email(entidad, convocatoria, match)

    assert "Cuantía" not in aviso.cuerpo
    assert "Financiación máxima" not in aviso.cuerpo


def test_plantilla_no_expone_ids_de_sistema_ni_costes_internos():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta()

    aviso = construir_aviso_email(entidad, convocatoria, match)
    texto_completo = aviso.asunto + "\n" + aviso.cuerpo

    assert match.match_id not in texto_completo
    assert entidad.entidad_id not in texto_completo
    assert convocatoria.convocatoria_id not in texto_completo
    assert "coste" not in texto_completo.lower()
    assert "costo" not in texto_completo.lower()


# --- Envío (cliente SMTP inyectado, sin red) ------------------------------


def test_envio_feliz_llama_starttls_login_y_send_message():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta()
    cliente = _ClienteSMTPStub()
    notificador = NotificadorEmailSMTP(_config(), fabrica_cliente=lambda: cliente)

    notificador.notificar_propuesta(entidad, convocatoria, match)

    assert cliente.starttls_llamado is True
    assert cliente.login_llamado_con == ("avisos@ongs-ai.example", "secreto-de-test")
    assert len(cliente.mensajes_enviados) == 1
    mensaje = cliente.mensajes_enviados[0]
    assert mensaje["To"] == entidad.contacto.email
    assert mensaje["From"] == "avisos@ongs-ai.example"
    assert notificador.enviados == 1
    assert notificador.omitidos_sin_email == 0
    assert notificador.fallidos == 0


def test_entidad_sin_email_degrada_limpio_sin_llamar_al_cliente():
    entidad = _entidad(email=None)
    convocatoria = _convocatoria()
    match = _match_propuesta()
    cliente = _ClienteSMTPStub()
    notificador = NotificadorEmailSMTP(_config(), fabrica_cliente=lambda: cliente)

    notificador.notificar_propuesta(entidad, convocatoria, match)  # no debe lanzar

    assert notificador.omitidos_sin_email == 1
    assert notificador.enviados == 0
    assert cliente.mensajes_enviados == []


def test_smtp_que_lanza_degrada_limpio_sin_propagar_excepcion():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta()
    cliente = _ClienteSMTPStub(fallar_en="send_message")
    notificador = NotificadorEmailSMTP(_config(), fabrica_cliente=lambda: cliente)

    notificador.notificar_propuesta(entidad, convocatoria, match)  # no debe lanzar

    assert notificador.fallidos == 1
    assert notificador.enviados == 0


def test_smtp_que_lanza_en_starttls_degrada_limpio():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta()
    cliente = _ClienteSMTPStub(fallar_en="starttls")
    notificador = NotificadorEmailSMTP(_config(), fabrica_cliente=lambda: cliente)

    notificador.notificar_propuesta(entidad, convocatoria, match)

    assert notificador.fallidos == 1


def test_sin_usuario_configurado_no_llama_a_login():
    entidad = _entidad()
    convocatoria = _convocatoria()
    match = _match_propuesta()
    cliente = _ClienteSMTPStub()
    config_sin_credenciales = ConfiguracionSMTP(
        host="smtp.example.org", puerto=587, remitente="avisos@ongs-ai.example",
    )
    notificador = NotificadorEmailSMTP(config_sin_credenciales, fabrica_cliente=lambda: cliente)

    notificador.notificar_propuesta(entidad, convocatoria, match)

    assert cliente.login_llamado_con is None
    assert notificador.enviados == 1
