"""Puerto de persistencia de Prospecto — NO vive en `dominio/puertos.py`
(ADR-006 §2.3): el dominio congelado no depende de un concepto de fuera de
contrato. `Prospecto` es un modelo de datos nuevo, no un hash como
`RepositorioTokensAcceso`.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ongs_ai.prospeccion.modelo import Prospecto


@runtime_checkable
class RepositorioProspectos(Protocol):
    def guardar_prospecto(self, prospecto: Prospecto) -> None: ...

    def obtener_prospecto(self, prospecto_id: str) -> Prospecto | None: ...

    def listar_prospectos(self) -> list[Prospecto]: ...
