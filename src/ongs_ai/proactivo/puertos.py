"""Puertos de persistencia del proactivo — ADR-007 §3.1/§3.9.

NO viven en `dominio/puertos.py` (el dominio congelado no depende de un
concepto fuera de contrato) — mismo patrón que `prospeccion/puertos.py`
(ADR-006 §2.3). Toda lectura/escritura exige `entidad_id`: aislamiento por
tenant idéntico al de `RepositorioMatches` (ADR-001 §4.2, regla de oro).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ongs_ai.proactivo.modelo import ConvocatoriaEsperada, HistorialConcesion


@runtime_checkable
class RepositorioHistorialConcesiones(Protocol):
    def guardar_historial(self, historial: HistorialConcesion) -> None: ...

    def obtener_historial_por_cod_concesion(
        self, entidad_id: str, cod_concesion: str
    ) -> HistorialConcesion | None:
        """Clave natural de dedupe (ADR-007 §3.4): `entidad_id` + `cod_concesion`."""
        ...

    def listar_historial_por_entidad(self, entidad_id: str) -> list[HistorialConcesion]: ...


@runtime_checkable
class RepositorioConvocatoriasEsperadas(Protocol):
    def guardar_esperada(self, esperada: ConvocatoriaEsperada) -> None: ...

    def obtener_esperada(
        self, entidad_id: str, serie_fingerprint: str, anio_esperado: int
    ) -> ConvocatoriaEsperada | None:
        """Clave natural de upsert (ADR-007 §3.4): `(entidad_id, serie_fingerprint,
        anio_esperado)`."""
        ...

    def listar_esperadas_por_entidad(self, entidad_id: str) -> list[ConvocatoriaEsperada]: ...
