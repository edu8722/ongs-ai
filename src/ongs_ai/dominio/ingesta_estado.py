"""Promoción determinista EXTRAIDA -> VERIFICADA — ADR-001 §1.2/§6, F2.

Única función de dominio que decide esta transición (los adapters de ingesta
nunca la deciden por sí mismos, solo mapean y llaman aquí). Campos mínimos
para promocionar: `objeto` no vacío, `plazos.fecha_cierre` informada,
`ambito_geografico` informado (siempre lo está — es un enum no-nulo del
contrato, se comprueba igualmente por completitud) y `beneficiarios_elegibles`
no vacío. Lo que no cumple se queda EXTRAIDA — no es un error, es la cola de
trabajo pendiente para la futura capa de extracción IA (que nunca decide
`estado_ingesta`, solo puede completar campos para que esta función vuelva a
evaluar).
"""
from __future__ import annotations

import dataclasses

from ongs_ai.dominio.entidades import Convocatoria, EstadoIngesta


def campos_minimos_completos(convocatoria: Convocatoria) -> bool:
    return bool(
        convocatoria.objeto
        and convocatoria.plazos.fecha_cierre is not None
        and convocatoria.ambito_geografico is not None
        and convocatoria.beneficiarios_elegibles
    )


def promocionar_si_completa(convocatoria: Convocatoria) -> Convocatoria:
    """EXTRAIDA -> VERIFICADA si `campos_minimos_completos`; si no, sin cambios.

    Solo actúa sobre `EstadoIngesta.EXTRAIDA` — otros estados (p. ej. ya
    VERIFICADA o DESCARTADA_POR_DOMINIO) se devuelven intactos.
    """
    if convocatoria.estado_ingesta is not EstadoIngesta.EXTRAIDA:
        return convocatoria
    if not campos_minimos_completos(convocatoria):
        return convocatoria
    return dataclasses.replace(convocatoria, estado_ingesta=EstadoIngesta.VERIFICADA)
