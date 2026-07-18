"""Test anti-fuga cross-tenant (CLAUDE.md — regla de oro AISLAMIENTO POR TENANT).

Dos Entidades, un Match de cada una: una consulta con `entidad_id` de la
primera nunca debe devolver Match, asientos ni datos económicos de la segunda.
Corre sobre AMBOS adapters (memoria, sqlite ':memory:') — el aislamiento es una
garantía del puerto, no de un adapter concreto.
"""
from datetime import date, datetime, timezone

import pytest

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
from ongs_ai.dominio.matching_estado import ActorAsiento, crear_match

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
