"""Degradación limpia de la capa IA explicativa — ADR-001 §2, F3.

La IA nunca lanza al dominio: si el generador lanza excepción o devuelve
vacío, el llamador sigue con `explicacion_ia=None`.
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
from ongs_ai.dominio.matching_estado import ResultadoElegibilidad
from ongs_ai.ia.explicacion_match import ExplicadorStub

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)
FECHA_REF = date(2026, 7, 18)


def _entidad(**overrides) -> Entidad:
    base = dict(
        entidad_id="ent-1",
        nombre_legal="Asociación de Prueba",
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


def _convocatoria(**overrides) -> Convocatoria:
    base = dict(
        convocatoria_id="conv-1",
        fuente=Fuente(
            portal="portal-x", url_origen="https://example.org/conv-1", tipo=TipoFuente.PUBLICA_NACIONAL
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


class _GeneradorQueLanza:
    def generar(self, entidad, convocatoria, resultado):
        raise RuntimeError("proveedor LLM caído")


class _GeneradorQueDevuelveVacio:
    def generar(self, entidad, convocatoria, resultado):
        return ""


def _ids():
    contador = iter(range(1, 1000))

    def siguiente() -> str:
        return f"id-{next(contador)}"

    return siguiente


def _reloj_fijo():
    return AHORA


def test_explicador_stub_genera_texto_determinista_y_no_vacio():
    entidad = _entidad()
    convocatoria = _convocatoria()
    resultado = ResultadoElegibilidad(elegible=True, detalle="todo cumple")
    stub = ExplicadorStub()

    texto_1 = stub.generar(entidad, convocatoria, resultado)
    texto_2 = stub.generar(entidad, convocatoria, resultado)

    assert texto_1 == texto_2
    assert entidad.nombre_legal in texto_1
    assert convocatoria.objeto in texto_1


def test_generador_que_lanza_produce_match_valido_sin_explicacion():
    matches = detectar_matches(
        [_entidad()],
        [_convocatoria()],
        FECHA_REF,
        generador_ids=_ids(),
        reloj=_reloj_fijo,
        generador_explicacion=_GeneradorQueLanza(),
    )
    assert len(matches) == 1
    match = matches[0]
    assert match.resultado_elegibilidad_dura.elegible is True
    assert match.explicacion_ia is None


def test_generador_que_devuelve_vacio_produce_match_sin_explicacion():
    matches = detectar_matches(
        [_entidad()],
        [_convocatoria()],
        FECHA_REF,
        generador_ids=_ids(),
        reloj=_reloj_fijo,
        generador_explicacion=_GeneradorQueDevuelveVacio(),
    )
    assert matches[0].explicacion_ia is None


def test_sin_generador_explicacion_match_sin_explicacion():
    matches = detectar_matches(
        [_entidad()],
        [_convocatoria()],
        FECHA_REF,
        generador_ids=_ids(),
        reloj=_reloj_fijo,
    )
    assert matches[0].explicacion_ia is None
    assert matches[0].resultado_elegibilidad_dura is not None


def test_explicador_stub_rellena_explicacion_solo_si_elegible():
    convocatoria_no_elegible = _convocatoria(
        convocatoria_id="conv-2", estado_ingesta=EstadoIngesta.EXTRAIDA
    )
    matches = detectar_matches(
        [_entidad()],
        [_convocatoria(), convocatoria_no_elegible],
        FECHA_REF,
        generador_ids=_ids(),
        reloj=_reloj_fijo,
        generador_explicacion=ExplicadorStub(),
    )
    por_convocatoria = {m.convocatoria_id: m for m in matches}
    assert por_convocatoria["conv-1"].resultado_elegibilidad_dura.elegible is True
    assert por_convocatoria["conv-1"].explicacion_ia is not None

    no_elegible = [m for m in matches if m.resultado_elegibilidad_dura.elegible is False]
    assert no_elegible
    assert all(m.explicacion_ia is None for m in no_elegible)
