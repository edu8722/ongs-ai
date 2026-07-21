"""Tests HTTP de las acciones aceptar/descartar sobre propuestas del panel
(`POST /panel/propuestas/{aceptar,descartar}`) — ADR-005 §6, F-web.2.

`TestClient` de FastAPI, SMTP siempre stub (CLAUDE.md: tests herméticos).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
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
from ongs_ai.dominio.matching_estado import ActorAsiento, EstadoMatch, crear_match, transicionar
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _entidad(entidad_id: str, email: str, nombre: str) -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal=nombre,
        nif="B55555555",
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
        creado_en=T0,
        actualizado_en=T0,
    )


def _match_propuesta(match_id: str, entidad_id: str, convocatoria_id: str):
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=convocatoria_id,
        transicion_id=f"t0-{match_id}", motivo="detectada", actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    return transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id=f"t1-{match_id}",
        motivo="propuesta", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )


def _cliente_logueado(almacen: AlmacenMemoria, entidad: Entidad) -> TestClient:
    enviador = EnviadorEnlaceAccesoStub()
    app = crear_app(
        secret_key="clave-de-test-nunca-en-produccion",
        almacen=almacen,
        enviador_enlace=enviador,
        generador_token=lambda: f"token-{entidad.entidad_id}",
        reloj=lambda: T0,
    )
    client = TestClient(app)
    client.post("/login", data={"email": entidad.contacto.email})
    token = enviador.enlaces[0].token
    client.post("/login/confirmar", data={"token": token})
    return client


def _csrf_de(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "token CSRF no encontrado en el panel"
    return match.group(1)


def _match_de(almacen: AlmacenMemoria, entidad_id: str, match_id: str):
    for match in almacen.listar_matches_por_entidad(entidad_id):
        if match.match_id == match_id:
            return match
    return None


def test_aceptar_propuesta_feliz():
    almacen = AlmacenMemoria()
    entidad = _entidad("prop-ent-1", "prop1@example.org", "Asociación Uno")
    almacen.guardar_entidad(entidad)
    almacen.guardar_match(_match_propuesta("prop-match-1", entidad.entidad_id, "conv-1"))

    client = _cliente_logueado(almacen, entidad)
    csrf = _csrf_de(client.get("/panel").text)

    resp = client.post(
        "/panel/propuestas/aceptar",
        data={"match_id": "prop-match-1", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/panel"

    panel = client.get("/panel").text
    assert "Propuestas pendientes (0)" in panel
    assert "Aceptadas (1)" in panel
    assert _match_de(almacen, entidad.entidad_id, "prop-match-1").estado_actual == EstadoMatch.ACEPTADA


def test_descartar_propuesta_feliz():
    almacen = AlmacenMemoria()
    entidad = _entidad("prop-ent-2", "prop2@example.org", "Asociación Dos")
    almacen.guardar_entidad(entidad)
    almacen.guardar_match(_match_propuesta("prop-match-2", entidad.entidad_id, "conv-2"))

    client = _cliente_logueado(almacen, entidad)
    csrf = _csrf_de(client.get("/panel").text)

    resp = client.post(
        "/panel/propuestas/descartar",
        data={"match_id": "prop-match-2", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/panel"

    panel = client.get("/panel").text
    assert "Propuestas pendientes (0)" in panel
    assert "Descartadas (1)" in panel
    assert (
        _match_de(almacen, entidad.entidad_id, "prop-match-2").estado_actual
        == EstadoMatch.DESCARTADA
    )


def test_post_sin_csrf_403():
    almacen = AlmacenMemoria()
    entidad = _entidad("prop-ent-3", "prop3@example.org", "Asociación Tres")
    almacen.guardar_entidad(entidad)
    almacen.guardar_match(_match_propuesta("prop-match-3", entidad.entidad_id, "conv-3"))

    client = _cliente_logueado(almacen, entidad)
    client.get("/panel")  # asegura que la sesión ya tiene un token CSRF asignado

    resp_sin_campo = client.post(
        "/panel/propuestas/aceptar", data={"match_id": "prop-match-3"}
    )
    assert resp_sin_campo.status_code == 403

    resp_invalido = client.post(
        "/panel/propuestas/aceptar",
        data={"match_id": "prop-match-3", "csrf_token": "token-que-no-es"},
    )
    assert resp_invalido.status_code == 403

    assert (
        _match_de(almacen, entidad.entidad_id, "prop-match-3").estado_actual
        == EstadoMatch.PROPUESTA
    )


def test_match_de_otra_entidad_404_identico_a_inexistente():
    almacen = AlmacenMemoria()
    entidad_a = _entidad("prop-ent-4a", "prop4a@example.org", "Asociación A")
    entidad_b = _entidad("prop-ent-4b", "prop4b@example.org", "Asociación B")
    almacen.guardar_entidad(entidad_a)
    almacen.guardar_entidad(entidad_b)
    almacen.guardar_match(_match_propuesta("prop-match-4", entidad_b.entidad_id, "conv-4"))
    # Match propio de A, solo para que su panel renderice un formulario (y por
    # tanto un token CSRF) del que extraer un token válido para su sesión.
    almacen.guardar_match(_match_propuesta("prop-match-4a", entidad_a.entidad_id, "conv-4a"))

    client = _cliente_logueado(almacen, entidad_a)
    csrf = _csrf_de(client.get("/panel").text)

    resp_ajeno = client.post(
        "/panel/propuestas/aceptar",
        data={"match_id": "prop-match-4", "csrf_token": csrf},
    )
    resp_inventado = client.post(
        "/panel/propuestas/aceptar",
        data={"match_id": "match-que-no-existe", "csrf_token": csrf},
    )

    assert resp_ajeno.status_code == resp_inventado.status_code == 404
    assert resp_ajeno.text == resp_inventado.text
    assert (
        _match_de(almacen, entidad_b.entidad_id, "prop-match-4").estado_actual
        == EstadoMatch.PROPUESTA
    )


def test_doble_submit_transicion_ilegal_redirige_sin_reventar():
    almacen = AlmacenMemoria()
    entidad = _entidad("prop-ent-5", "prop5@example.org", "Asociación Cinco")
    almacen.guardar_entidad(entidad)
    almacen.guardar_match(_match_propuesta("prop-match-5", entidad.entidad_id, "conv-5"))

    client = _cliente_logueado(almacen, entidad)
    csrf = _csrf_de(client.get("/panel").text)

    client.post(
        "/panel/propuestas/aceptar", data={"match_id": "prop-match-5", "csrf_token": csrf}
    )
    match_tras_primera = _match_de(almacen, entidad.entidad_id, "prop-match-5")
    assert match_tras_primera.estado_actual == EstadoMatch.ACEPTADA
    asientos_tras_primera = len(match_tras_primera.asientos)

    resp_doble = client.post(
        "/panel/propuestas/aceptar",
        data={"match_id": "prop-match-5", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp_doble.status_code == 303
    assert resp_doble.headers["location"] == "/panel?aviso=1"

    match_tras_segunda = _match_de(almacen, entidad.entidad_id, "prop-match-5")
    assert len(match_tras_segunda.asientos) == asientos_tras_primera
    assert match_tras_segunda.estado_actual == EstadoMatch.ACEPTADA

    panel_con_aviso = client.get("/panel?aviso=1").text
    assert "No se ha podido completar la acción" in panel_con_aviso


def test_get_no_muta_estado():
    almacen = AlmacenMemoria()
    entidad = _entidad("prop-ent-6", "prop6@example.org", "Asociación Seis")
    almacen.guardar_entidad(entidad)
    almacen.guardar_match(_match_propuesta("prop-match-6", entidad.entidad_id, "conv-6"))

    client = _cliente_logueado(almacen, entidad)

    resp = client.get("/panel/propuestas/aceptar")
    assert resp.status_code == 405
    assert (
        _match_de(almacen, entidad.entidad_id, "prop-match-6").estado_actual
        == EstadoMatch.PROPUESTA
    )
