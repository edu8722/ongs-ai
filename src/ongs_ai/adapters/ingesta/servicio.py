"""Orquestación de ingesta — conecta una `FuenteConvocatorias` con el almacén,
deduplicando por `portal`+`url_origen` (ADR-001 §6.5, clave natural elegida
para F2). No es dominio puro: compone un adapter (fuente) con un puerto de
persistencia, como el resto de `adapters/` (CLAUDE.md).
"""
from __future__ import annotations

from dataclasses import dataclass

from ongs_ai.adapters.ingesta.base import FiltrosBusqueda, FuenteConvocatorias
from ongs_ai.dominio.puertos import RepositorioConvocatorias


@dataclass(frozen=True)
class ResumenIngesta:
    nuevas: int
    ya_existentes: int


def ingestar(
    fuente: FuenteConvocatorias,
    almacen: RepositorioConvocatorias,
    filtros: FiltrosBusqueda | None = None,
) -> ResumenIngesta:
    """Idempotente: una convocatoria ya presente (mismo `portal`+`url_origen`) no
    se vuelve a guardar — re-ingestar la misma fuente en una segunda pasada no
    duplica nada en el almacén."""
    nuevas = 0
    ya_existentes = 0
    for convocatoria in fuente.buscar(filtros):
        existente = almacen.obtener_por_url_origen(
            convocatoria.fuente.portal, convocatoria.fuente.url_origen
        )
        if existente is not None:
            ya_existentes += 1
            continue
        almacen.guardar_convocatoria(convocatoria)
        nuevas += 1
    return ResumenIngesta(nuevas=nuevas, ya_existentes=ya_existentes)
