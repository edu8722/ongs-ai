"""Tests de CONTRATO — el puerto (`puertos.py`) promete objetos de dominio tipados y
AMBOS adapters (memoria, sqlite) deben cumplirlo igual (corrección post-auditoría F1).
"""
from datetime import date, datetime, timezone

import pytest

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite
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
from ongs_ai.dominio.matching_estado import ActorAsiento, EstadoMatch, crear_match, transicionar
from ongs_ai.dominio.puertos import RepositorioConvocatorias, RepositorioEntidades, RepositorioMatches

T0 = datetime(2026, 7, 18, tzinfo=timezone.utc)


@pytest.fixture(params=["memoria", "sqlite"])
def almacen(request):
    instancia = AlmacenMemoria() if request.param == "memoria" else AlmacenSQLite(":memory:")
    yield instancia
    cerrar = getattr(instancia, "cerrar", None)
    if cerrar is not None:
        cerrar()


def _entidad(entidad_id: str = "ent-contrato-1") -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal="Asociación de Contrato",
        nif="B87654321",
        ambito_territorial=AmbitoTerritorial.PROVINCIAL,
        forma_juridica=FormaJuridicaDeclarada(
            tipo=FormaJuridica.OTRA, descripcion="cooperativa social de contrato"
        ),
        fecha_constitucion=date(2015, 3, 20),
        enfermedad_o_colectivo="colectivo de contrato",
        actividades=(
            ActividadDeclarada(tipo=TipoActividad.FORMACION),
            ActividadDeclarada(tipo=TipoActividad.OTRO, descripcion="taller de respiro"),
        ),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=75_000, gastos_centimos=60_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(
            RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,
            RequisitoFormal.CERTIFICADO_ESTAR_AL_CORRIENTE_AEAT,
        ),
        contacto=Contacto(email="contrato@example.org", telefono="600111222"),
        creado_en=T0,
        actualizado_en=T0,
        region="Andalucía",
        provincia="Sevilla",
    )


def _convocatoria(convocatoria_id: str = "conv-contrato-1") -> Convocatoria:
    return Convocatoria(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(portal="BOE", url_origen="https://boe.example/x", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Subvención de contrato",
        beneficiarios_elegibles="Asociaciones inscritas",
        requisitos_elegibilidad=RequisitosElegibilidad(
            ambito_territorial_requerido=AmbitoTerritorial.NACIONAL,
            forma_juridica_requerida="asociacion",
            antiguedad_minima_anios=2,
            requisitos_formales_requeridos=(RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,),
            exclusiones=("empresas con animo de lucro",),
        ),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(
            fecha_apertura=date(2026, 1, 1),
            fecha_cierre=date(2026, 3, 31),
            fecha_resolucion_estimada=date(2026, 6, 30),
        ),
        cuantias=Cuantias(
            importe_minimo_centimos=100_000,
            importe_maximo_centimos=5_000_000,
            porcentaje_max_financiable=8000,
        ),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=T0,
        actualizado_en=T0,
        documento_origen_ref="doc-123",
        region="Madrid",
        provincia="Madrid",
    )


def test_roundtrip_entidad(almacen):
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    obtenida = almacen.obtener_entidad(entidad.entidad_id)
    assert obtenida == entidad
    # ADR-002: forma_juridica (con descripcion, caso OTRA) y fecha_constitucion
    # deben sobrevivir la serialización/deserialización sin cambios.
    assert obtenida.forma_juridica == entidad.forma_juridica
    assert obtenida.forma_juridica.tipo is FormaJuridica.OTRA
    assert obtenida.forma_juridica.descripcion == "cooperativa social de contrato"
    assert obtenida.fecha_constitucion == entidad.fecha_constitucion == date(2015, 3, 20)


def test_obtener_entidad_inexistente_devuelve_none(almacen):
    assert almacen.obtener_entidad("no-existe") is None


def test_roundtrip_convocatoria(almacen):
    convocatoria = _convocatoria()
    almacen.guardar_convocatoria(convocatoria)
    assert almacen.obtener_convocatoria(convocatoria.convocatoria_id) == convocatoria


def test_obtener_convocatoria_inexistente_devuelve_none(almacen):
    assert almacen.obtener_convocatoria("no-existe") is None


def test_obtener_por_url_origen_roundtrip(almacen):
    convocatoria = _convocatoria()
    almacen.guardar_convocatoria(convocatoria)

    encontrada = almacen.obtener_por_url_origen(
        convocatoria.fuente.portal, convocatoria.fuente.url_origen
    )

    assert encontrada == convocatoria


def test_obtener_por_url_origen_inexistente_devuelve_none(almacen):
    assert almacen.obtener_por_url_origen("BOE", "https://no-existe.example") is None


def test_obtener_por_url_origen_no_confunde_portales_distintos(almacen):
    convocatoria = _convocatoria()
    almacen.guardar_convocatoria(convocatoria)

    assert almacen.obtener_por_url_origen("OTRO_PORTAL", convocatoria.fuente.url_origen) is None


def test_roundtrip_match_con_asientos_y_transiciones(almacen):
    match = crear_match(
        match_id="match-contrato-1",
        entidad_id="ent-contrato-1",
        convocatoria_id="conv-contrato-1",
        transicion_id="t0",
        motivo="detectada por el vigilante",
        actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    match = transicionar(
        match,
        a_estado=EstadoMatch.PROPUESTA,
        transicion_id="t1",
        motivo="propuesta a la entidad",
        actor=ActorAsiento.IA,
        timestamp=T0,
    )
    almacen.guardar_match(match)

    obtenidos = almacen.listar_matches_por_entidad(match.entidad_id)

    assert obtenidos == [match]
    assert obtenidos[0].estado_actual == EstadoMatch.PROPUESTA
    assert [a.a_estado for a in obtenidos[0].asientos] == [
        EstadoMatch.DETECTADA,
        EstadoMatch.PROPUESTA,
    ]


def test_listar_matches_por_entidad_sin_matches_devuelve_lista_vacia(almacen):
    assert almacen.listar_matches_por_entidad("ent-sin-matches") == []


def test_almacen_satisface_los_protocolos_de_puertos(almacen):
    assert isinstance(almacen, RepositorioEntidades)
    assert isinstance(almacen, RepositorioConvocatorias)
    assert isinstance(almacen, RepositorioMatches)
