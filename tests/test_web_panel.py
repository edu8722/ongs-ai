"""Tests HTTP del panel de solo lectura (`GET /panel`) — ADR-005 §2.3/§2.4/§6, F-web.1.

`TestClient` de FastAPI, SMTP siempre stub (CLAUDE.md: tests herméticos).
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
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
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    EstadoMatch,
    ResultadoElegibilidad,
    crear_match,
    transicionar,
)
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _entidad(entidad_id: str, email: str, nombre: str) -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal=nombre,
        nif="B44444444",
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


def _convocatoria(convocatoria_id: str, objeto: str) -> Convocatoria:
    return Convocatoria(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="portal-panel", url_origen=f"https://example.org/{convocatoria_id}",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto=objeto,
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=500_000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=T0,
        actualizado_en=T0,
    )


def _match_propuesta(match_id: str, entidad_id: str, convocatoria_id: str) -> object:
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=convocatoria_id,
        transicion_id=f"t0-{match_id}", motivo="detectada", actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    return transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id=f"t1-{match_id}",
        motivo="propuesta", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )


def _match_no_elegible(match_id: str, entidad_id: str, convocatoria_id: str, detalle: str):
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=convocatoria_id,
        transicion_id=f"t0-{match_id}", motivo="detectada", actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    return dataclasses.replace(
        match, resultado_elegibilidad_dura=ResultadoElegibilidad(elegible=False, detalle=detalle)
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


def test_panel_muestra_los_datos_de_la_propia_entidad():
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-1", "panel1@example.org", "Asociación del Panel")
    almacen.guardar_entidad(entidad)
    almacen.guardar_convocatoria(_convocatoria("panel-conv-1", "Ayudas de investigación rara"))
    almacen.guardar_match(_match_propuesta("panel-match-1", entidad.entidad_id, "panel-conv-1"))
    almacen.guardar_match(
        _match_no_elegible(
            "panel-match-2", entidad.entidad_id, "panel-conv-1", "ámbito territorial incompatible"
        )
    )

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert entidad.nombre_legal in resp.text
    assert "Ayudas de investigación rara" in resp.text
    assert "portal-panel" in resp.text
    assert "ámbito territorial incompatible" in resp.text


def test_panel_no_expone_ids_internos():
    # Match en un cubo SIN acciones (aceptar/descartar solo van en
    # propuestas_pendientes, F-web.2): ahí sí es necesario y legítimo que
    # match_id viaje como campo oculto del formulario de la propia entidad.
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-2", "panel2@example.org", "Fundación del Panel")
    almacen.guardar_entidad(entidad)
    almacen.guardar_convocatoria(_convocatoria("panel-conv-2", "Subvención de respiro familiar"))
    almacen.guardar_match(
        _match_no_elegible("panel-match-3", entidad.entidad_id, "panel-conv-2", "motivo interno")
    )

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert "panel-match-3" not in resp.text
    assert "panel-conv-2" not in resp.text
    assert entidad.entidad_id not in resp.text


def test_panel_sin_matches_muestra_cubos_vacios():
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-3", "panel3@example.org", "Liga del Panel")
    almacen.guardar_entidad(entidad)

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert entidad.nombre_legal in resp.text


def test_panel_convocatoria_no_disponible_degrada_limpio():
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-4", "panel4@example.org", "Red del Panel")
    almacen.guardar_entidad(entidad)
    # Match cuya convocatoria referenciada no está persistida (dato feo).
    almacen.guardar_match(_match_propuesta("panel-match-4", entidad.entidad_id, "conv-que-no-existe"))

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")  # no debe lanzar

    assert resp.status_code == 200
    assert "Convocatoria no disponible" in resp.text
