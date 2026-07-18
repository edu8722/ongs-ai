"""Ingesta de convocatorias — puerto de fuente + transporte HTTP inyectable (F2).

`FuenteConvocatorias` es el Protocol que cualquier fuente de convocatorias
(BDNS, futuros adapters privados) debe cumplir. `TransporteHTTP` desacopla la
llamada de red real: los tests SIEMPRE inyectan un stub con fixtures grabadas
(regla de oro CLAUDE.md — red apagada en tests, cero peticiones reales).
`TransporteURLLib` es la única implementación que hace red real (stdlib
`urllib`, sin dependencias nuevas); solo se usa desde `scripts/smoke_bdns.py`
(fuera de pytest).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Protocol, runtime_checkable

from ongs_ai.dominio.entidades import Convocatoria


@dataclass(frozen=True)
class FiltrosBusqueda:
    """Filtros de búsqueda de convocatorias — SIEMPRE datos de entrada, nunca una
    enfermedad/entidad hardcodeada en la plataforma (regla de oro CLAUDE.md)."""

    descripcion: str | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    tipo_beneficiario: str | None = None


@runtime_checkable
class FuenteConvocatorias(Protocol):
    def buscar(self, filtros: FiltrosBusqueda | None = None) -> Iterable[Convocatoria]: ...


@runtime_checkable
class TransporteHTTP(Protocol):
    def obtener_json(self, url: str, params: Mapping[str, object]) -> dict: ...


class TransporteURLLib:
    """Transporte real contra una API JSON pública — SOLO para uso manual fuera de
    pytest (`scripts/smoke_bdns.py`). Nunca se instancia en tests.
    """

    def __init__(self, timeout_segundos: float = 15.0) -> None:
        self._timeout_segundos = timeout_segundos

    def obtener_json(self, url: str, params: Mapping[str, object]) -> dict:
        query = urllib.parse.urlencode(
            {clave: valor for clave, valor in params.items() if valor is not None}
        )
        url_completa = f"{url}?{query}" if query else url
        peticion = urllib.request.Request(url_completa, headers={"Accept": "application/json"})
        with urllib.request.urlopen(peticion, timeout=self._timeout_segundos) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
