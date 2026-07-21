"""Extractor IA de requisitos de elegibilidad — PROMPT-018 A3.

Ejecutor de subproceso/CLI SIEMPRE stub — cero red, cero binario real
(regla de oro CLAUDE.md). Casos grabados: válida, basura, campos
desconocidos, degradación del cliente (timeout/error).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from ongs_ai.dominio.entidades import (
    AmbitoTerritorial,
    Convocatoria,
    Cuantias,
    EstadoIngesta,
    Fuente,
    Plazos,
    RequisitoFormal,
    RequisitosElegibilidad,
    TipoFuente,
)
from ongs_ai.ia.extraccion_requisitos import enriquecer_requisitos

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)


class _ClienteStub:
    def __init__(self, respuesta: str | None) -> None:
        self._respuesta = respuesta
        self.preguntas: list[str] = []

    def preguntar(self, prompt: str) -> str | None:
        self.preguntas.append(prompt)
        return self._respuesta


def _convocatoria(**overrides) -> Convocatoria:
    base = dict(
        convocatoria_id="conv-1",
        fuente=Fuente(portal="BDNS", url_origen="https://example.org/conv-1", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayudas a asociaciones de utilidad pública con más de 3 años de antigüedad",
        beneficiarios_elegibles="Asociaciones declaradas de utilidad pública, inscritas en el registro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 3, 1)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.EXTRAIDA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def test_respuesta_valida_enriquece_los_tres_campos():
    respuesta = (
        '{"forma_juridica_requerida": "asociacion", "antiguedad_minima_anios": 3, '
        '"requisitos_formales_requeridos": ["declarada_utilidad_publica", '
        '"inscrita_registro_asociaciones"]}'
    )
    cliente = _ClienteStub(respuesta)
    convocatoria = _convocatoria()

    resultado = enriquecer_requisitos(cliente, convocatoria)

    assert resultado.requisitos_elegibilidad.forma_juridica_requerida == "asociacion"
    assert resultado.requisitos_elegibilidad.antiguedad_minima_anios == 3
    assert resultado.requisitos_elegibilidad.requisitos_formales_requeridos == (
        RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,
        RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,
    )


def test_respuesta_envuelta_en_bloque_markdown_se_parsea_igual():
    respuesta = (
        '```json\n{"forma_juridica_requerida": "fundacion", '
        '"antiguedad_minima_anios": null, "requisitos_formales_requeridos": []}\n```'
    )
    cliente = _ClienteStub(respuesta)

    resultado = enriquecer_requisitos(cliente, _convocatoria())

    assert resultado.requisitos_elegibilidad.forma_juridica_requerida == "fundacion"


def test_respuesta_basura_no_parseable_devuelve_convocatoria_intacta():
    cliente = _ClienteStub("esto no es JSON en absoluto")
    convocatoria = _convocatoria()

    resultado = enriquecer_requisitos(cliente, convocatoria)

    assert resultado == convocatoria


def test_campos_desconocidos_en_requisitos_formales_se_descartan():
    respuesta = (
        '{"forma_juridica_requerida": null, "antiguedad_minima_anios": null, '
        '"requisitos_formales_requeridos": ["declarada_utilidad_publica", '
        '"flag_inventado_que_no_existe"]}'
    )
    cliente = _ClienteStub(respuesta)

    resultado = enriquecer_requisitos(cliente, _convocatoria())

    assert resultado.requisitos_elegibilidad.requisitos_formales_requeridos == (
        RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,
    )


def test_antiguedad_minima_no_entera_se_descarta():
    respuesta = '{"forma_juridica_requerida": null, "antiguedad_minima_anios": "tres", "requisitos_formales_requeridos": []}'
    cliente = _ClienteStub(respuesta)

    resultado = enriquecer_requisitos(cliente, _convocatoria())

    assert resultado.requisitos_elegibilidad.antiguedad_minima_anios is None


def test_cliente_degradado_timeout_devuelve_convocatoria_intacta():
    cliente = _ClienteStub(None)
    convocatoria = _convocatoria()

    resultado = enriquecer_requisitos(cliente, convocatoria)

    assert resultado == convocatoria
    assert len(cliente.preguntas) == 1


def test_nunca_pisa_un_campo_ya_presente():
    respuesta = (
        '{"forma_juridica_requerida": "fundacion", "antiguedad_minima_anios": 10, '
        '"requisitos_formales_requeridos": ["declarada_utilidad_publica"]}'
    )
    cliente = _ClienteStub(respuesta)
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(
            forma_juridica_requerida="asociacion",
            antiguedad_minima_anios=None,
            requisitos_formales_requeridos=(),
        )
    )

    resultado = enriquecer_requisitos(cliente, convocatoria)

    # forma_juridica_requerida ya estaba informada -> nunca se pisa
    assert resultado.requisitos_elegibilidad.forma_juridica_requerida == "asociacion"
    # antiguedad_minima_anios estaba vacía -> se enriquece
    assert resultado.requisitos_elegibilidad.antiguedad_minima_anios == 10
    assert resultado.requisitos_elegibilidad.requisitos_formales_requeridos == (
        RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,
    )


def test_convocatoria_con_todos_los_campos_ya_completos_no_llama_al_cliente():
    cliente = _ClienteStub("no debería usarse")
    convocatoria = _convocatoria(
        requisitos_elegibilidad=RequisitosElegibilidad(
            forma_juridica_requerida="asociacion",
            antiguedad_minima_anios=2,
            requisitos_formales_requeridos=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        )
    )

    resultado = enriquecer_requisitos(cliente, convocatoria)

    assert resultado == convocatoria
    assert cliente.preguntas == []
