"""Factory de la capa IA por entorno — mismo patrón que
`adapters/persistencia/factory.py` y `adapters/avisos/factory.py`.

Los tests NUNCA deben depender de esta función leyendo el .env de la
máquina: deben instanciar `ExplicadorStub` directamente o pasar
`entorno='test'` explícito.
"""
from __future__ import annotations

import os

from ongs_ai.ia.claude_cli import ClienteClaudeCLI
from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI, ExplicadorStub, GeneradorExplicacion


def crear_generador_explicacion(entorno: str | None = None) -> GeneradorExplicacion:
    """`entorno='test'` -> `ExplicadorStub`; cualquier otro valor (incluida la
    ausencia) -> `ExplicadorClaudeCLI` sobre el CLI real (`ClienteClaudeCLI`,
    binario/timeout leídos de su propia configuración por entorno). Si
    `entorno` es None se lee de la variable ONGS_AI_ENV."""
    if entorno is None:
        entorno = os.environ.get("ONGS_AI_ENV", "")
    if entorno == "test":
        return ExplicadorStub()
    return ExplicadorClaudeCLI(ClienteClaudeCLI())
