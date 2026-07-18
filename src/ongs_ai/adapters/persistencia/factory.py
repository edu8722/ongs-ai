"""Factory de persistencia por entorno — backend real por defecto, memoria en tests."""
from __future__ import annotations

import os

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import RUTA_DB_DEFECTO, AlmacenSQLite


def crear_almacen(entorno: str | None = None) -> AlmacenMemoria | AlmacenSQLite:
    """`entorno='test'` -> AlmacenMemoria; cualquier otro valor (incluida la
    ausencia) -> AlmacenSQLite anclado al repo. Si `entorno` es None se lee
    de la variable de entorno ONGS_AI_ENV.

    Los tests NUNCA deben depender de esta función leyendo el .env de la
    máquina: deben instanciar AlmacenMemoria directamente o pasar
    entorno='test' explícito.
    """
    if entorno is None:
        entorno = os.environ.get("ONGS_AI_ENV", "")
    if entorno == "test":
        return AlmacenMemoria()
    return AlmacenSQLite(RUTA_DB_DEFECTO)
