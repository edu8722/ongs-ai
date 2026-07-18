"""Capa IA explicativa de Match — ADR-001 §1.4/§2, F3.

`GeneradorExplicacion` es un Protocol mockeable: cualquier implementación
(stub v1, proveedor LLM real más adelante) es intercambiable sin tocar
`ongs_ai.dominio.matching`. La IA nunca decide `resultado_elegibilidad_dura`
ni `estado_actual`; solo argumenta un match ya evaluado por el guardarraíl
determinista (`ongs_ai.dominio.elegibilidad`).
"""
from __future__ import annotations

from typing import Protocol

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import ResultadoElegibilidad


class GeneradorExplicacion(Protocol):
    def generar(
        self, entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
    ) -> str: ...


class ExplicadorStub:
    """Implementación v1: determinista, sin red, sin LLM real.

    El proveedor LLM real lo decide el arquitecto más adelante (ver
    engineering/ADR-001-contrato-de-datos.md, F3). Sirve para desbloquear el
    servicio de matching sin acoplarlo a ningún proveedor concreto.
    """

    def generar(
        self, entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
    ) -> str:
        return (
            f"{entidad.nombre_legal} encaja con la convocatoria "
            f'"{convocatoria.objeto}" ({convocatoria.fuente.portal}): {resultado.detalle}'
        )
