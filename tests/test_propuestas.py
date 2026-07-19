"""Tests de `detectar_y_proponer` — ADR-004 §5/§6 (F4.1), persistencia + aviso.

Parametrizados sobre AMBOS almacenes (memoria, sqlite `:memory:`), herméticos
(sin red) como el resto de tests de persistencia (`test_contrato_persistencia.py`).
"""
from __future__ import annotations

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
from ongs_ai.servicios.notificacion import NotificadorStub
from ongs_ai.servicios.propuestas import detectar_y_proponer

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)
FECHA_REF = date(2026, 7, 18)


@pytest.fixture(params=["memoria", "sqlite"])
def almacen(request):
    instancia = AlmacenMemoria() if request.param == "memoria" else AlmacenSQLite(":memory:")
    yield instancia
    cerrar = getattr(instancia, "cerrar", None)
    if cerrar is not None:
        cerrar()


def _entidad(entidad_id: str = "ent-1", **overrides) -> Entidad:
    base = dict(
        entidad_id=entidad_id,
        nombre_legal=f"Asociación {entidad_id}",
        nif="B00000000",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 5, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email="test@example.org"),
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Entidad(**base)


def _convocatoria(
    convocatoria_id: str = "conv-1",
    *,
    elegible: bool = True,
    estado_ingesta: EstadoIngesta = EstadoIngesta.VERIFICADA,
    fecha_cierre: date | None = date(2026, 12, 31),
    **overrides,
) -> Convocatoria:
    """`elegible=False` exige `forma_juridica_requerida="fundacion"` — la
    entidad por defecto (`_entidad`) es ASOCIACION, así que incumple SOLO ese
    requisito (el resto de la pareja es compatible), dejando el resultado
    determinista y fácil de razonar en los tests."""
    requisitos = (
        RequisitosElegibilidad()
        if elegible
        else RequisitosElegibilidad(forma_juridica_requerida="fundacion")
    )
    base = dict(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="portal-x",
            url_origen=f"https://example.org/{convocatoria_id}",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto="Ayudas a asociaciones",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=requisitos,
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=fecha_cierre),
        cuantias=Cuantias(),
        estado_ingesta=estado_ingesta,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def _ids(prefijo: str = "id"):
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"{prefijo}-{next(contador)}"

    return siguiente


def _reloj_fijo():
    return AHORA


class _NotificadorQueLanza:
    def notificar_propuesta(self, entidad, convocatoria, match) -> None:
        raise RuntimeError("fallo simulado del canal de notificación")


def test_convocatoria_elegible_primera_deteccion_crea_propuesta_y_avisa(almacen):
    entidad = _entidad()
    convocatoria = _convocatoria(elegible=True)
    notificador = NotificadorStub()

    resumen = detectar_y_proponer(
        [entidad], [convocatoria], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    assert resumen.nuevas_propuestas == 1
    assert resumen.propuestas_sobrevenidas == 0
    assert resumen.no_elegibles_persistidas == 0
    assert resumen.ya_existentes_sin_cambio == 0
    assert resumen.saltadas_pre_puerta == 0

    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 1
    assert matches[0].estado_actual == EstadoMatch.PROPUESTA
    assert matches[0].resultado_elegibilidad_dura.elegible is True

    assert len(notificador.avisos) == 1
    assert notificador.avisos[0].match_id == matches[0].match_id


def test_convocatoria_no_elegible_crea_match_detectada_sin_aviso(almacen):
    entidad = _entidad()
    convocatoria = _convocatoria(elegible=False)
    notificador = NotificadorStub()

    resumen = detectar_y_proponer(
        [entidad], [convocatoria], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    assert resumen.no_elegibles_persistidas == 1
    assert resumen.nuevas_propuestas == 0

    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 1
    assert matches[0].estado_actual == EstadoMatch.DETECTADA
    assert matches[0].resultado_elegibilidad_dura.elegible is False
    assert notificador.avisos == []


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"estado_ingesta": EstadoIngesta.EXTRAIDA}, id="no-verificada"),
        pytest.param({"fecha_cierre": date(2026, 1, 1)}, id="plazo-cerrado"),
        pytest.param({"fecha_cierre": None}, id="plazo-none"),
    ],
)
def test_pre_puerta_ignora_convocatorias_no_verificadas_o_cerradas(almacen, kwargs):
    entidad = _entidad()
    convocatoria = _convocatoria(elegible=True, **kwargs)
    notificador = NotificadorStub()

    resumen = detectar_y_proponer(
        [entidad], [convocatoria], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    assert resumen.saltadas_pre_puerta == 1
    assert almacen.listar_matches_por_entidad(entidad.entidad_id) == []
    assert notificador.avisos == []


def test_segunda_pasada_idempotente_no_duplica_ni_reavisa(almacen):
    entidad = _entidad()
    conv_elegible = _convocatoria("conv-elegible", elegible=True)
    conv_no_elegible = _convocatoria("conv-no-elegible", elegible=False)
    notificador = NotificadorStub()

    resumen_1 = detectar_y_proponer(
        [entidad], [conv_elegible, conv_no_elegible], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )
    assert resumen_1.nuevas_propuestas == 1
    assert resumen_1.no_elegibles_persistidas == 1
    assert len(notificador.avisos) == 1

    resumen_2 = detectar_y_proponer(
        [entidad], [conv_elegible, conv_no_elegible], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    assert resumen_2.nuevas_propuestas == 0
    assert resumen_2.propuestas_sobrevenidas == 0
    assert resumen_2.ya_existentes_sin_cambio == 1  # el elegible, ya en PROPUESTA
    assert resumen_2.no_elegibles_persistidas == 1  # el no elegible, sin cambios

    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 2  # ninguna fila nueva en la 2ª pasada
    assert len(notificador.avisos) == 1  # sin re-aviso


def test_elegibilidad_sobrevenida_transiciona_a_propuesta_y_avisa(almacen):
    entidad = _entidad()
    conv_no_elegible_aun = _convocatoria("conv-sobrevenida", elegible=False)
    notificador = NotificadorStub()

    resumen_1 = detectar_y_proponer(
        [entidad], [conv_no_elegible_aun], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )
    assert resumen_1.no_elegibles_persistidas == 1
    assert notificador.avisos == []

    match_antes = almacen.listar_matches_por_entidad(entidad.entidad_id)[0]
    assert match_antes.estado_actual == EstadoMatch.DETECTADA

    # La misma pareja (mismo convocatoria_id) ahora cumple forma jurídica.
    conv_ahora_elegible = _convocatoria("conv-sobrevenida", elegible=True)
    resumen_2 = detectar_y_proponer(
        [entidad], [conv_ahora_elegible], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    assert resumen_2.propuestas_sobrevenidas == 1
    assert resumen_2.nuevas_propuestas == 0
    assert len(notificador.avisos) == 1

    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 1  # sigue siendo EL MISMO match (upsert), no uno nuevo
    assert matches[0].match_id == match_antes.match_id
    assert matches[0].estado_actual == EstadoMatch.PROPUESTA
    assert matches[0].resultado_elegibilidad_dura.elegible is True


@pytest.mark.parametrize("estado_terminal", [EstadoMatch.DESCARTADA, EstadoMatch.PRESENTADA])
def test_respeta_match_terminal_no_crea_nuevo_ni_avisa(almacen, estado_terminal):
    entidad = _entidad()
    convocatoria = _convocatoria("conv-terminal", elegible=True)

    match = crear_match(
        match_id="match-terminal-1",
        entidad_id=entidad.entidad_id,
        convocatoria_id=convocatoria.convocatoria_id,
        transicion_id="t0",
        motivo="detectada por el vigilante",
        actor=ActorAsiento.SISTEMA,
        timestamp=AHORA,
    )
    match = transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id="t1",
        motivo="propuesta", actor=ActorAsiento.SISTEMA, timestamp=AHORA,
    )
    if estado_terminal == EstadoMatch.DESCARTADA:
        match = transicionar(
            match, a_estado=EstadoMatch.DESCARTADA, transicion_id="t2",
            motivo="descartada por la entidad", actor=ActorAsiento.ENTIDAD, timestamp=AHORA,
        )
    else:
        match = transicionar(match, a_estado=EstadoMatch.ACEPTADA, transicion_id="t2",
                              motivo="aceptada", actor=ActorAsiento.ENTIDAD, timestamp=AHORA)
        match = transicionar(match, a_estado=EstadoMatch.EN_PREPARACION, transicion_id="t3",
                              motivo="en preparación", actor=ActorAsiento.ENTIDAD, timestamp=AHORA)
        match = transicionar(match, a_estado=EstadoMatch.PRESENTADA, transicion_id="t4",
                              motivo="presentada", actor=ActorAsiento.ENTIDAD, timestamp=AHORA)
    almacen.guardar_match(match)

    notificador = NotificadorStub()
    resumen = detectar_y_proponer(
        [entidad], [convocatoria], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    assert resumen.nuevas_propuestas == 0
    assert resumen.propuestas_sobrevenidas == 0
    assert resumen.ya_existentes_sin_cambio == 1

    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 1
    assert matches[0].match_id == "match-terminal-1"
    assert matches[0].estado_actual == estado_terminal
    assert notificador.avisos == []


def test_notificador_que_lanza_degrada_limpio_y_sigue_con_las_demas(almacen):
    entidad_1 = _entidad("ent-1")
    entidad_2 = _entidad("ent-2")
    conv_1 = _convocatoria("conv-1", elegible=True)
    conv_2 = _convocatoria("conv-2", elegible=True)
    notificador = _NotificadorQueLanza()

    resumen = detectar_y_proponer(
        [entidad_1, entidad_2], [conv_1, conv_2], FECHA_REF, almacen, notificador,
        generador_ids=_ids(), reloj=_reloj_fijo,
    )

    # 2 entidades x 2 convocatorias, todas elegibles.
    assert resumen.nuevas_propuestas == 4

    for entidad in (entidad_1, entidad_2):
        matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
        assert len(matches) == 2
        assert all(m.estado_actual == EstadoMatch.PROPUESTA for m in matches)


def test_reloj_e_ids_inyectados_verificables(almacen):
    entidad = _entidad()
    convocatoria = _convocatoria(elegible=True)
    notificador = NotificadorStub()
    ids = _ids(prefijo="det-id")

    detectar_y_proponer(
        [entidad], [convocatoria], FECHA_REF, almacen, notificador,
        generador_ids=ids, reloj=_reloj_fijo,
    )

    match = almacen.listar_matches_por_entidad(entidad.entidad_id)[0]
    assert match.match_id.startswith("det-id-")
    assert all(a.transicion_id.startswith("det-id-") for a in match.asientos)
    assert len({a.transicion_id for a in match.asientos}) == len(match.asientos)
    assert all(a.timestamp == AHORA for a in match.asientos)
