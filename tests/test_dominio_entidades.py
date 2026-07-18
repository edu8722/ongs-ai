from datetime import date, datetime, timezone

import pytest

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
    normalizar_forma_juridica,
)
from ongs_ai.dominio.errores import DineroInvalidoError, ErrorDominio

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)


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


def test_crea_entidad_con_campos_del_adr():
    entidad = _entidad()
    assert entidad.entidad_id == "ent-1"
    assert entidad.ambito_territorial is AmbitoTerritorial.NACIONAL
    assert entidad.actividades[0].tipo is TipoActividad.VOLUNTARIADO


def test_actividad_otro_exige_descripcion():
    with pytest.raises(ErrorDominio):
        ActividadDeclarada(tipo=TipoActividad.OTRO)
    # con descripcion es válida
    actividad = ActividadDeclarada(tipo=TipoActividad.OTRO, descripcion="algo no previsto")
    assert actividad.descripcion == "algo no previsto"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(ingresos_centimos=100.0, gastos_centimos=90_000, ejercicio=2025),
        dict(ingresos_centimos=100_000, gastos_centimos=90.5, ejercicio=2025),
    ],
)
def test_datos_economicos_rechaza_floats(kwargs):
    with pytest.raises(DineroInvalidoError):
        DatosEconomicos(**kwargs)


def test_datos_economicos_acepta_enteros():
    datos = DatosEconomicos(ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025)
    assert datos.ingresos_centimos == 100_000


def _convocatoria(**overrides) -> Convocatoria:
    base = dict(
        convocatoria_id="conv-1",
        fuente=Fuente(portal="portal-x", url_origen="https://example.org/conv-1", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayudas a asociaciones",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(
            ambito_territorial_requerido=AmbitoTerritorial.NACIONAL,
            requisitos_formales_requeridos=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        ),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 3, 1)),
        cuantias=Cuantias(
            importe_minimo_centimos=100_000,
            importe_maximo_centimos=1_000_000,
            porcentaje_max_financiable=8000,
        ),
        estado_ingesta=EstadoIngesta.EXTRAIDA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def test_crea_convocatoria_con_campos_del_adr():
    convocatoria = _convocatoria()
    assert convocatoria.cuantias.porcentaje_max_financiable == 8000
    assert convocatoria.estado_ingesta is EstadoIngesta.EXTRAIDA


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(importe_minimo_centimos=100.0),
        dict(importe_maximo_centimos=1_000_000.5),
        dict(porcentaje_max_financiable=80.0),
    ],
)
def test_cuantias_rechaza_floats(kwargs):
    with pytest.raises(DineroInvalidoError):
        Cuantias(**kwargs)


def test_porcentaje_max_financiable_es_puntos_basicos_enteros():
    # 8000 = 80%, nunca 0.8 ni 80.0
    cuantias = Cuantias(porcentaje_max_financiable=8000)
    assert cuantias.porcentaje_max_financiable == 8000
    assert isinstance(cuantias.porcentaje_max_financiable, int)


# --- ADR-002: forma jurídica + fecha de constitución ---------------------


def test_entidad_exige_forma_juridica_y_fecha_constitucion():
    entidad = _entidad()
    assert entidad.forma_juridica.tipo is FormaJuridica.ASOCIACION
    assert entidad.fecha_constitucion == date(2010, 5, 1)


def test_forma_juridica_declarada_otra_exige_descripcion():
    with pytest.raises(ErrorDominio):
        FormaJuridicaDeclarada(tipo=FormaJuridica.OTRA)
    declarada = FormaJuridicaDeclarada(tipo=FormaJuridica.OTRA, descripcion="cooperativa social")
    assert declarada.descripcion == "cooperativa social"


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("asociacion", FormaJuridica.ASOCIACION),
        ("Asociación", FormaJuridica.ASOCIACION),
        ("ASOCIACIÓN SIN ÁNIMO DE LUCRO", FormaJuridica.ASOCIACION),
        ("fundación", FormaJuridica.FUNDACION),
        ("Fundaciones", FormaJuridica.FUNDACION),
        ("federación", FormaJuridica.FEDERACION_O_CONFEDERACION),
        ("confederación", FormaJuridica.FEDERACION_O_CONFEDERACION),
        ("  federacion o confederacion  ", FormaJuridica.FEDERACION_O_CONFEDERACION),
    ],
)
def test_normalizar_forma_juridica_mapea_sinonimos_frecuentes(texto, esperado):
    assert normalizar_forma_juridica(texto) is esperado


@pytest.mark.parametrize("texto", ["", "cooperativa", "sociedad limitada", "otra", "xyz"])
def test_normalizar_forma_juridica_texto_no_mapeable_devuelve_none(texto):
    assert normalizar_forma_juridica(texto) is None
