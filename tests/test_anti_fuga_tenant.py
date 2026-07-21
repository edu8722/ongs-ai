"""Test anti-fuga cross-tenant (CLAUDE.md — regla de oro AISLAMIENTO POR TENANT).

Dos Entidades, un Match de cada una: una consulta con `entidad_id` de la
primera nunca debe devolver Match, asientos ni datos económicos de la segunda.
Corre sobre AMBOS adapters (memoria, sqlite ':memory:') — el aislamiento es una
garantía del puerto, no de un adapter concreto.

Amplía el aislamiento a nivel HTTP (ADR-005 §2.3/§6, F-web.1): entidad A
logueada con matches sembrados de A y B, `/panel` de A no debe mostrar nada de
B, y ninguna ruta acepta un `entidad_id` ajeno como parámetro.
"""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite
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

T0 = datetime(2026, 7, 18, tzinfo=timezone.utc)


@pytest.fixture(params=["memoria", "sqlite"])
def almacen(request):
    instancia = AlmacenMemoria() if request.param == "memoria" else AlmacenSQLite(":memory:")
    yield instancia
    cerrar = getattr(instancia, "cerrar", None)
    if cerrar is not None:
        cerrar()


def _entidad(entidad_id: str, ingresos_centimos: int) -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal=f"Asociación {entidad_id}",
        nif=f"B{entidad_id}",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2012, 1, 1),
        enfermedad_o_colectivo=f"colectivo de {entidad_id}",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=ingresos_centimos, gastos_centimos=1_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email=f"{entidad_id}@example.org"),
        creado_en=T0,
        actualizado_en=T0,
    )


def test_consulta_por_entidad_a_no_devuelve_matches_de_entidad_b(almacen):
    entidad_a = _entidad("ent-A", ingresos_centimos=111_111)
    entidad_b = _entidad("ent-B", ingresos_centimos=222_222)
    almacen.guardar_entidad(entidad_a)
    almacen.guardar_entidad(entidad_b)

    match_a = crear_match(
        match_id="match-A", entidad_id=entidad_a.entidad_id, convocatoria_id="conv-1",
        transicion_id="t0-a", motivo="detectada para A", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )
    match_b = crear_match(
        match_id="match-B", entidad_id=entidad_b.entidad_id, convocatoria_id="conv-1",
        transicion_id="t0-b", motivo="detectada para B", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )
    almacen.guardar_match(match_a)
    almacen.guardar_match(match_b)

    matches_de_a = almacen.listar_matches_por_entidad(entidad_a.entidad_id)

    assert [m.match_id for m in matches_de_a] == ["match-A"]
    assert all(m.entidad_id == entidad_a.entidad_id for m in matches_de_a)

    ids_de_b = {match_b.match_id, entidad_b.entidad_id}
    for match in matches_de_a:
        assert match.match_id not in ids_de_b
        assert match.entidad_id not in ids_de_b
        for asiento in match.asientos:
            assert asiento.transicion_id != "t0-b"


def test_consulta_por_entidad_a_no_expone_datos_economicos_de_entidad_b(almacen):
    entidad_a = _entidad("ent-A", ingresos_centimos=111_111)
    entidad_b = _entidad("ent-B", ingresos_centimos=222_222)
    almacen.guardar_entidad(entidad_a)
    almacen.guardar_entidad(entidad_b)

    obtenida = almacen.obtener_entidad(entidad_a.entidad_id)

    assert obtenida is not None
    assert obtenida.datos_economicos_ejercicio_anterior.ingresos_centimos == 111_111
    assert obtenida.datos_economicos_ejercicio_anterior.ingresos_centimos != 222_222


# --- Anti-fuga a nivel HTTP (ADR-005 §2.3/§6, F-web.1) ---------------------


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


def test_http_entidad_a_logueada_no_ve_matches_de_b_ni_via_query_param():
    entidad_a = _entidad("ent-http-A", ingresos_centimos=111_111)
    entidad_b = _entidad("ent-http-B", ingresos_centimos=222_222)
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(entidad_a)
    almacen.guardar_entidad(entidad_b)
    almacen.guardar_match(_match_propuesta("match-http-A", entidad_a.entidad_id, "conv-http-1"))
    almacen.guardar_match(_match_propuesta("match-http-B", entidad_b.entidad_id, "conv-http-1"))

    enviador = EnviadorEnlaceAccesoStub()
    app = crear_app(
        secret_key="clave-de-test-nunca-en-produccion",
        almacen=almacen,
        enviador_enlace=enviador,
        generador_token=lambda: "token-http-A",
        reloj=lambda: T0,
    )
    client = TestClient(app)
    client.post("/login", data={"email": entidad_a.contacto.email})
    token = enviador.enlaces[0].token
    client.get(f"/login/confirmar?token={token}")

    # Ninguna ruta acepta un entidad_id ajeno como parámetro: un query param
    # `entidad_id` debe ser ignorado por completo, el tenant sale SOLO de la
    # sesión (ADR-005 §2.3).
    resp = client.get("/panel", params={"entidad_id": entidad_b.entidad_id})

    assert resp.status_code == 200
    assert "match-http-B" not in resp.text
    assert entidad_b.entidad_id not in resp.text
    assert "match-http-A" not in resp.text  # tampoco se exponen ids internos propios
