"""Promoción EXTRAIDA -> VERIFICADA (`dominio/ingesta_estado.py`) — F2, ADR-001."""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

from ongs_ai.dominio.entidades import (
    AmbitoTerritorial,
    Convocatoria,
    Cuantias,
    EstadoIngesta,
    Fuente,
    Plazos,
    RequisitosElegibilidad,
    TipoFuente,
)
from ongs_ai.dominio.ingesta_estado import campos_minimos_completos, promocionar_si_completa

T0 = datetime(2026, 7, 18, tzinfo=timezone.utc)


def _convocatoria_extraida(**overrides) -> Convocatoria:
    base = dict(
        convocatoria_id="conv-promocion-1",
        fuente=Fuente(portal="BDNS", url_origen="https://bdns.example/1", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Objeto de prueba",
        beneficiarios_elegibles="Asociaciones",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_cierre=date(2026, 6, 1)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.EXTRAIDA,
        creado_en=T0,
        actualizado_en=T0,
    )
    base.update(overrides)
    return Convocatoria(**base)


def test_campos_minimos_completos_promociona_a_verificada():
    convocatoria = _convocatoria_extraida()
    assert campos_minimos_completos(convocatoria) is True

    promocionada = promocionar_si_completa(convocatoria)

    assert promocionada.estado_ingesta is EstadoIngesta.VERIFICADA
    # El resto de campos no cambia — solo se toca estado_ingesta.
    assert dataclasses.replace(promocionada, estado_ingesta=EstadoIngesta.EXTRAIDA) == convocatoria


def test_sin_fecha_cierre_no_promociona():
    convocatoria = _convocatoria_extraida(plazos=Plazos(fecha_cierre=None))
    assert campos_minimos_completos(convocatoria) is False
    assert promocionar_si_completa(convocatoria).estado_ingesta is EstadoIngesta.EXTRAIDA


def test_sin_objeto_no_promociona():
    convocatoria = _convocatoria_extraida(objeto="")
    assert campos_minimos_completos(convocatoria) is False
    assert promocionar_si_completa(convocatoria).estado_ingesta is EstadoIngesta.EXTRAIDA


def test_sin_beneficiarios_no_promociona():
    convocatoria = _convocatoria_extraida(beneficiarios_elegibles="")
    assert campos_minimos_completos(convocatoria) is False
    assert promocionar_si_completa(convocatoria).estado_ingesta is EstadoIngesta.EXTRAIDA


def test_convocatoria_ya_verificada_no_se_toca():
    convocatoria = _convocatoria_extraida(
        estado_ingesta=EstadoIngesta.VERIFICADA, plazos=Plazos(fecha_cierre=None)
    )
    assert promocionar_si_completa(convocatoria) == convocatoria


def test_convocatoria_descartada_no_se_toca():
    convocatoria = _convocatoria_extraida(estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO)
    assert promocionar_si_completa(convocatoria) == convocatoria
