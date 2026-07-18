"""Servicio `detectar_matches` — ADR-001 §1.4, F3.

Produce Matches `detectada` correctos (uno por pareja Entidad×Convocatoria),
con `resultado_elegibilidad_dura` siempre informado y `estado_actual` inicial
`detectada` con asiento `actor=sistema`. La transición a `propuesta` es F4 y
no se cubre aquí.
"""
from datetime import date, datetime, timezone

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
from ongs_ai.dominio.matching import detectar_matches
from ongs_ai.dominio.matching_estado import ActorAsiento, EstadoMatch

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)
FECHA_REF = date(2026, 7, 18)


def _entidad(entidad_id="ent-1", **overrides) -> Entidad:
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


def _convocatoria(convocatoria_id="conv-1", **overrides) -> Convocatoria:
    base = dict(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="portal-x",
            url_origen=f"https://example.org/{convocatoria_id}",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto="Ayudas a asociaciones",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 3, 1)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def _ids():
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"id-{next(contador)}"

    return siguiente


def _reloj_fijo():
    return AHORA


def test_detectar_matches_produce_un_match_por_pareja():
    entidades = [_entidad("ent-1"), _entidad("ent-2")]
    convocatorias = [_convocatoria("conv-1"), _convocatoria("conv-2")]

    matches = detectar_matches(
        entidades, convocatorias, FECHA_REF, generador_ids=_ids(), reloj=_reloj_fijo
    )

    assert len(matches) == 4
    pares = {(m.entidad_id, m.convocatoria_id) for m in matches}
    assert pares == {
        ("ent-1", "conv-1"), ("ent-1", "conv-2"),
        ("ent-2", "conv-1"), ("ent-2", "conv-2"),
    }


def test_matches_arrancan_en_detectada_con_asiento_de_sistema():
    matches = detectar_matches(
        [_entidad()], [_convocatoria()], FECHA_REF, generador_ids=_ids(), reloj=_reloj_fijo
    )
    match = matches[0]
    assert match.estado_actual is EstadoMatch.DETECTADA
    assert len(match.asientos) == 1
    assert match.asientos[0].actor is ActorAsiento.SISTEMA
    assert match.asientos[0].timestamp == AHORA


def test_match_ids_son_unicos_por_pareja():
    entidades = [_entidad("ent-1"), _entidad("ent-2")]
    convocatorias = [_convocatoria("conv-1")]

    matches = detectar_matches(
        entidades, convocatorias, FECHA_REF, generador_ids=_ids(), reloj=_reloj_fijo
    )

    assert len({m.match_id for m in matches}) == len(matches)


def test_resultado_elegibilidad_dura_siempre_informado():
    convocatoria_no_verificada = _convocatoria("conv-no-verificada", estado_ingesta=EstadoIngesta.EXTRAIDA)

    matches = detectar_matches(
        [_entidad()], [_convocatoria(), convocatoria_no_verificada],
        FECHA_REF, generador_ids=_ids(), reloj=_reloj_fijo,
    )

    for match in matches:
        assert match.resultado_elegibilidad_dura is not None

    por_convocatoria = {m.convocatoria_id: m for m in matches}
    assert por_convocatoria["conv-1"].resultado_elegibilidad_dura.elegible is True
    assert por_convocatoria["conv-no-verificada"].resultado_elegibilidad_dura.elegible is False


def test_detectar_matches_sin_parejas_devuelve_lista_vacia():
    matches = detectar_matches([], [], FECHA_REF, generador_ids=_ids(), reloj=_reloj_fijo)
    assert matches == []
