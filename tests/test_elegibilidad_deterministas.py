"""Guardarraíl determinista de elegibilidad — ADR-001 §2, F3.

Una batería por regla (cumple/incumple/no_evaluable), borde de aniversario
exacto, convocatoria sin verificar, OTRA nunca casa, exclusiones no bloquean
pero aparecen en el detalle.
"""
from datetime import date, datetime, timezone

import pytest

from ongs_ai.dominio.elegibilidad import evaluar_elegibilidad
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


# --- (a) estado_ingesta ---------------------------------------------------


def test_convocatoria_no_verificada_nunca_elegible():
    convocatoria = _convocatoria(estado_ingesta=EstadoIngesta.EXTRAIDA)
    resultado = evaluar_elegibilidad(_entidad(), convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "estado_ingesta: incumple" in resultado.detalle


def test_convocatoria_verificada_y_resto_ok_es_elegible():
    resultado = evaluar_elegibilidad(_entidad(), _convocatoria(), FECHA_REF)
    assert resultado.elegible is True
    assert "estado_ingesta: cumple" in resultado.detalle


# --- (b) ámbito territorial ------------------------------------------------


def test_ambito_nacional_acepta_cualquier_entidad():
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.NACIONAL)
    resultado = evaluar_elegibilidad(_entidad(region=None, provincia=None), convocatoria, FECHA_REF)
    assert resultado.elegible is True
    assert "ambito_territorial: cumple" in resultado.detalle


def test_ambito_autonomico_cumple_con_region_normalizada():
    entidad = _entidad(ambito_territorial=AmbitoTerritorial.AUTONOMICO, region="Andalucía")
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.AUTONOMICO, region="  andalucia  ")
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is True
    assert "ambito_territorial: cumple" in resultado.detalle


def test_ambito_autonomico_incumple_region_distinta():
    entidad = _entidad(ambito_territorial=AmbitoTerritorial.AUTONOMICO, region="Andalucía")
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.AUTONOMICO, region="Cataluña")
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "ambito_territorial: incumple" in resultado.detalle


def test_ambito_autonomico_sin_region_en_entidad_es_no_evaluable():
    entidad = _entidad(region=None)
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.AUTONOMICO, region="Andalucía")
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "ambito_territorial: no_evaluable" in resultado.detalle


def test_ambito_autonomico_sin_region_en_convocatoria_es_no_evaluable():
    entidad = _entidad(region="Andalucía")
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.AUTONOMICO, region=None)
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "ambito_territorial: no_evaluable" in resultado.detalle


def test_ambito_provincial_cumple_con_provincia_normalizada():
    entidad = _entidad(provincia="Sevilla")
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.PROVINCIAL, provincia="SEVILLA")
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is True


def test_ambito_provincial_incumple_provincia_distinta():
    entidad = _entidad(provincia="Sevilla")
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.PROVINCIAL, provincia="Cádiz")
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False


def test_ambito_provincial_sin_provincia_es_no_evaluable():
    entidad = _entidad(provincia=None)
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.PROVINCIAL, provincia="Cádiz")
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "ambito_territorial: no_evaluable" in resultado.detalle


def test_ambito_local_no_evaluable_en_v1():
    convocatoria = _convocatoria(ambito_geografico=AmbitoTerritorial.LOCAL)
    resultado = evaluar_elegibilidad(_entidad(), convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "ambito_territorial: no_evaluable" in resultado.detalle
    assert "municipio" in resultado.detalle


# --- (c) forma jurídica requerida ------------------------------------------


def test_forma_juridica_requerida_none_no_aplica():
    resultado = evaluar_elegibilidad(_entidad(), _convocatoria(), FECHA_REF)
    assert resultado.elegible is True
    assert "forma_juridica: cumple" in resultado.detalle


def test_forma_juridica_con_mapeo_cumple():
    entidad = _entidad(forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.FUNDACION))
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="Fundación")
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is True
    assert "forma_juridica: cumple" in resultado.detalle


def test_forma_juridica_con_mapeo_incumple_tipo_distinto():
    entidad = _entidad(forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION))
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="Fundación")
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "forma_juridica: incumple" in resultado.detalle


def test_forma_juridica_entidad_otra_nunca_casa_automaticamente():
    entidad = _entidad(
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.OTRA, descripcion="cooperativa social")
    )
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="asociación")
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "forma_juridica: incumple" in resultado.detalle


def test_forma_juridica_sin_mapeo_es_no_evaluable():
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="cooperativa")
    )
    resultado = evaluar_elegibilidad(_entidad(), convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "forma_juridica: no_evaluable" in resultado.detalle


# --- (d) antigüedad mínima --------------------------------------------------


def test_antiguedad_none_no_aplica():
    resultado = evaluar_elegibilidad(_entidad(), _convocatoria(), FECHA_REF)
    assert "antiguedad_minima_anios: cumple" in resultado.detalle


def test_antiguedad_borde_aniversario_exacto_cumple():
    entidad = _entidad(fecha_constitucion=date(2020, 7, 18))
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(antiguedad_minima_anios=6)
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, date(2026, 7, 18))
    assert resultado.elegible is True
    assert "antiguedad_minima_anios: cumple" in resultado.detalle


def test_antiguedad_un_dia_antes_del_aniversario_incumple():
    entidad = _entidad(fecha_constitucion=date(2020, 7, 18))
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(antiguedad_minima_anios=6)
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, date(2026, 7, 17))
    assert resultado.elegible is False
    assert "antiguedad_minima_anios: incumple" in resultado.detalle


def test_antiguedad_un_dia_despues_del_aniversario_cumple():
    entidad = _entidad(fecha_constitucion=date(2020, 7, 18))
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(antiguedad_minima_anios=6)
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, date(2026, 7, 19))
    assert resultado.elegible is True


# --- (e) requisitos formales -----------------------------------------------


def test_requisitos_formales_vacio_no_aplica():
    resultado = evaluar_elegibilidad(_entidad(), _convocatoria(), FECHA_REF)
    assert "requisitos_formales: cumple" in resultado.detalle


def test_requisitos_formales_subset_cumple():
    entidad = _entidad(
        requisitos_formales_disponibles=(
            RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,
            RequisitoFormal.CERTIFICADO_ESTAR_AL_CORRIENTE_AEAT,
        )
    )
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(
            requisitos_formales_requeridos=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,)
        )
    )
    resultado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF)
    assert resultado.elegible is True
    assert "requisitos_formales: cumple" in resultado.detalle


def test_requisitos_formales_falta_uno_incumple():
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(
            requisitos_formales_requeridos=(RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,)
        )
    )
    resultado = evaluar_elegibilidad(_entidad(), convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "requisitos_formales: incumple" in resultado.detalle
    assert "declarada_utilidad_publica" in resultado.detalle


# --- (f) exclusiones — nunca bloquean, aparecen en el detalle -------------


def test_exclusiones_no_bloquean_pero_aparecen_en_detalle():
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(
            exclusiones=("entidades con deuda tributaria pendiente",)
        )
    )
    resultado = evaluar_elegibilidad(_entidad(), convocatoria, FECHA_REF)
    assert resultado.elegible is True
    assert "exclusiones: revisar" in resultado.detalle
    assert "deuda tributaria pendiente" in resultado.detalle


def test_sin_exclusiones_detalle_lo_indica():
    resultado = evaluar_elegibilidad(_entidad(), _convocatoria(), FECHA_REF)
    assert "exclusiones: cumple" in resultado.detalle


# --- detalle línea a línea con todas las reglas -----------------------------


def test_detalle_incluye_las_seis_reglas():
    resultado = evaluar_elegibilidad(_entidad(), _convocatoria(), FECHA_REF)
    for etiqueta in (
        "estado_ingesta",
        "ambito_territorial",
        "forma_juridica",
        "antiguedad_minima_anios",
        "requisitos_formales",
        "exclusiones",
    ):
        assert etiqueta in resultado.detalle


# --- no_evaluable en cualquier regla implica no elegible --------------------


@pytest.mark.parametrize(
    "overrides_convocatoria",
    [
        dict(ambito_geografico=AmbitoTerritorial.LOCAL),
        dict(
            requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="cooperativa"),
        ),
    ],
)
def test_no_evaluable_en_cualquier_regla_hace_no_elegible(overrides_convocatoria):
    convocatoria = _convocatoria(**overrides_convocatoria)
    resultado = evaluar_elegibilidad(_entidad(), convocatoria, FECHA_REF)
    assert resultado.elegible is False
    assert "no_evaluable" in resultado.detalle
