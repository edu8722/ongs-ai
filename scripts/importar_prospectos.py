"""Importador MANUAL del maestro de prospección — ADR-006 §2.4/§6.2/§6.3/§7.

NO corre en CI (mismo patrón que `scripts/ejecutar_ingesta.py`). Lee un CSV
UTF-8 del maestro SIEMPRE fuera de git (`investigacion/` está gitignorada) y
puebla `RepositorioProspectos` a través del importador puro
(`ongs_ai.prospeccion.importador`). NUNCA imprime el contacto personal
(⚠ PII, columna "Personas visibles (cargo)") ni ningún dato de fila — solo el
resumen agregado.

Uso:
    python scripts/importar_prospectos.py investigacion/asociaciones_maestro.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ongs_ai.adapters.persistencia.factory import crear_almacen  # noqa: E402
from ongs_ai.prospeccion.importador import importar_prospectos  # noqa: E402


def _generador_id() -> str:
    return f"prospecto-{uuid.uuid4().hex[:12]}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa el maestro de prospección (CSV UTF-8) a RepositorioProspectos."
    )
    parser.add_argument("ruta_csv", help="Ruta al CSV UTF-8 del maestro (SIEMPRE fuera de git)")
    args = parser.parse_args()

    ruta = Path(args.ruta_csv)
    with ruta.open(encoding="utf-8-sig", newline="") as fichero:
        filas = list(csv.DictReader(fichero))

    resultado = importar_prospectos(filas, generador_id=_generador_id)

    almacen = crear_almacen()
    for prospecto in resultado.prospectos:
        almacen.guardar_prospecto(prospecto)

    print(f"Filas leídas: {len(filas)}")
    print(f"Prospectos importados: {len(resultado.prospectos)}")
    print(f"Descartadas (sin nombre): {resultado.filas_descartadas_sin_nombre}")
    print(f"Valores de Ámbito no mapeados: {resultado.valores_ambito_no_mapeados}")


if __name__ == "__main__":
    main()
