"""Tests deterministas del scoring de afinidad — ADR-006 §2.5/§2.6/§4.1.

Cubre: determinismo, no-elegible -> score capado e importe no agregado,
elegible sin importe_maximo -> cuenta sin sumar, prospecto con datos
faltantes -> pendiente_de_dato (nunca inventado), y el test de ANCLAJE que
ancla la equivalencia con `evaluar_elegibilidad` para el caso Entidad
completa (decisión de "duplicar en vez de refactorizar", ADR §2.6).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

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
from ongs_ai.prospeccion.modelo import Prospecto
from ongs_ai.servicios.afinidad import EstadoRequisito, evaluar_afinidad, resumen_prospeccion

AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)
FECHA_REF = date(2026, 7, 21)


def _entidad(**overrides) -> Entidad:
    base = dict(
        entidad_id="ent-afinidad-1",
        nombre_legal="Asociación de Afinidad",
        nif="B11111111",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 5, 1),
        enfermedad_o_colectivo="colectivo de afinidad",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email="afinidad@example.org"),
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Entidad(**base)


def _convocatoria(**overrides) -> Convocatoria:
    base = dict(
        convocatoria_id="conv-afinidad-1",
        fuente=Fuente(
            portal="portal-afinidad", url_origen="https://example.org/conv-afinidad-1",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto="Ayudas para voluntariado y encuentros de pacientes",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 9, 30)),
        cuantias=Cuantias(importe_minimo_centimos=100_000, importe_maximo_centimos=1_000_000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def _prospecto(**overrides) -> Prospecto:
    base = dict(prospecto_id="prospecto-afinidad-1", nombre="Prospecto de Afinidad")
    base.update(overrides)
    return Prospecto(**base)


# --- Determinismo -----------------------------------------------------------


def test_mismo_input_mismo_score_siempre():
    entidad = _entidad()
    convocatoria = _convocatoria()

    r1 = evaluar_afinidad(entidad, convocatoria, FECHA_REF)
    r2 = evaluar_afinidad(entidad, convocatoria, FECHA_REF)

    assert r1 == r2


# --- No elegible -> score capado e importe NO agregado ----------------------


def test_no_elegible_por_incumplimiento_capa_score_y_no_agrega_importe():
    entidad = _entidad(forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION))
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="Fundación")
    )

    resultado = evaluar_afinidad(entidad, convocatoria, FECHA_REF)

    assert resultado.elegible is False
    assert resultado.score <= 44
    assert resultado.importe_potencial_minimo_centimos is None
    assert resultado.importe_potencial_maximo_centimos is None
    assert resultado.importe_no_publicado is False


def test_convocatoria_no_verificada_no_elegible_score_capado():
    resultado = evaluar_afinidad(_entidad(), _convocatoria(estado_ingesta=EstadoIngesta.EXTRAIDA), FECHA_REF)

    assert resultado.elegible is False
    assert resultado.score <= 44


# --- Elegible sin importe_maximo -> cuenta pero no suma ---------------------


def test_elegible_sin_importe_maximo_cuenta_pero_no_suma():
    convocatoria = _convocatoria(cuantias=Cuantias(importe_minimo_centimos=None, importe_maximo_centimos=None))

    resultado = evaluar_afinidad(_entidad(), convocatoria, FECHA_REF)

    assert resultado.elegible is True
    assert resultado.importe_no_publicado is True
    assert resultado.importe_potencial_maximo_centimos is None

    resumen = resumen_prospeccion(_entidad(), [convocatoria], FECHA_REF)
    assert resumen.numero_elegibles == 1
    assert resumen.numero_elegibles_sin_importe_publicado == 1
    assert resumen.importe_potencial_maximo_centimos == 0
    assert resumen.importe_potencial_minimo_centimos == 0


# --- Prospecto con datos faltantes -> pendiente_de_dato, nunca inventado ----


def test_prospecto_sin_datos_produce_pendientes_no_inventados():
    prospecto = _prospecto()  # solo prospecto_id y nombre
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(
            antiguedad_minima_anios=3,
            requisitos_formales_requeridos=(RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,),
        )
    )

    resultado = evaluar_afinidad(prospecto, convocatoria, FECHA_REF)

    por_requisito = {d.requisito: d.estado for d in resultado.detalle_por_requisito}
    assert por_requisito["antiguedad_minima_anios"] is EstadoRequisito.PENDIENTE_DE_DATO
    assert por_requisito["requisitos_formales"] is EstadoRequisito.PENDIENTE_DE_DATO
    # Nunca elegible=True inventando datos ausentes como cumplidos.
    assert resultado.elegible is False


def test_prospecto_con_ambito_autonomico_y_region_declarada_es_evaluable():
    prospecto = _prospecto(ambito_territorial=AmbitoTerritorial.AUTONOMICO, region="Andalucía")
    convocatoria = _convocatoria(
        ambito_geografico=AmbitoTerritorial.AUTONOMICO, region="andalucia"
    )

    resultado = evaluar_afinidad(prospecto, convocatoria, FECHA_REF)

    por_requisito = {d.requisito: d.estado for d in resultado.detalle_por_requisito}
    assert por_requisito["ambito_territorial"] is EstadoRequisito.CUMPLE


def test_prospecto_sin_forma_juridica_es_pendiente_cuando_convocatoria_la_exige():
    prospecto = _prospecto()
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="asociacion")
    )

    resultado = evaluar_afinidad(prospecto, convocatoria, FECHA_REF)

    por_requisito = {d.requisito: d.estado for d in resultado.detalle_por_requisito}
    assert por_requisito["forma_juridica"] is EstadoRequisito.PENDIENTE_DE_DATO


def test_prospecto_capacidad_ejecucion_nunca_se_calcula_sin_datos_economicos():
    prospecto = _prospecto()
    resultado = evaluar_afinidad(prospecto, _convocatoria(), FECHA_REF)
    assert resultado.capacidad_ejecucion is None


def test_entidad_con_datos_economicos_muestra_capacidad_aparte_del_score():
    entidad = _entidad()
    resultado = evaluar_afinidad(entidad, _convocatoria(), FECHA_REF)
    assert resultado.capacidad_ejecucion is not None


# --- Afinidad temática --------------------------------------------------


def test_afinidad_tematica_cero_si_perfil_sin_actividades():
    prospecto = _prospecto()  # actividades=() por defecto
    resultado = evaluar_afinidad(prospecto, _convocatoria(), FECHA_REF)
    assert resultado.afinidad_tematica == 0


def test_afinidad_tematica_positiva_cuando_hay_solape():
    entidad = _entidad(actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),))
    resultado = evaluar_afinidad(entidad, _convocatoria(), FECHA_REF)
    assert resultado.afinidad_tematica > 0


# --- ANCLAJE: equivalencia con evaluar_elegibilidad para Entidad completa ---


def _casos_anclaje():
    entidad_completa = _entidad()
    return [
        (entidad_completa, _convocatoria()),
        (entidad_completa, _convocatoria(estado_ingesta=EstadoIngesta.EXTRAIDA)),
        (
            entidad_completa,
            _convocatoria(
                requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="Fundación")
            ),
        ),
        (entidad_completa, _convocatoria(ambito_geografico=AmbitoTerritorial.LOCAL)),
        (
            _entidad(fecha_constitucion=date(2024, 1, 1)),
            _convocatoria(
                requisitos_elegibilidad=RequisitosElegibilidad(antiguedad_minima_anios=5)
            ),
        ),
        (
            entidad_completa,
            _convocatoria(
                requisitos_elegibilidad=RequisitosElegibilidad(
                    requisitos_formales_requeridos=(RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,)
                )
            ),
        ),
        (
            _entidad(ambito_territorial=AmbitoTerritorial.AUTONOMICO, region="Andalucía"),
            _convocatoria(ambito_geografico=AmbitoTerritorial.AUTONOMICO, region="Cataluña"),
        ),
    ]


def test_anclaje_equivalencia_con_evaluar_elegibilidad():
    """Para una Entidad completa, `evaluar_afinidad(...).elegible` debe
    coincidir SIEMPRE con `evaluar_elegibilidad(...).elegible` — una sola
    fuente de verdad para el criterio duro, aunque la implementación esté
    duplicada (ADR-006 §2.6, decisión documentada en servicios/afinidad.py)."""
    for entidad, convocatoria in _casos_anclaje():
        esperado = evaluar_elegibilidad(entidad, convocatoria, FECHA_REF).elegible
        obtenido = evaluar_afinidad(entidad, convocatoria, FECHA_REF).elegible
        assert obtenido == esperado, (entidad.entidad_id, convocatoria.convocatoria_id)
