"""Smoke test MANUAL contra la API pública real de la BDNS.

Hace red real (peticiones HTTP a infosubvenciones.es) — por eso NO se ejecuta
en pytest ni en CI (regla de oro CLAUDE.md: tests herméticos, sin red). Lo
ejecuta el OPERADOR a mano para verificar que la API sigue viva y que la
forma de sus campos no ha cambiado.

Uso:
    python scripts/smoke_bdns.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.ingesta.base import TransporteURLLib  # noqa: E402
from ongs_ai.adapters.ingesta.bdns import FuenteBDNS  # noqa: E402

LIMITE_CONVOCATORIAS = 5


def main() -> None:
    fuente = FuenteBDNS(
        TransporteURLLib(),
        reloj=lambda: datetime.now(timezone.utc),
        page_size=LIMITE_CONVOCATORIAS,
    )

    convocatorias = []
    for convocatoria in fuente.buscar():
        convocatorias.append(convocatoria)
        if len(convocatorias) >= LIMITE_CONVOCATORIAS:
            break

    print(f"Convocatorias mapeadas: {len(convocatorias)}")
    for convocatoria in convocatorias:
        print(
            f"- {convocatoria.convocatoria_id} | {convocatoria.fuente.tipo.value} | "
            f"{convocatoria.ambito_geografico.value} ({convocatoria.region or 'sin region'}) | "
            f"estado_ingesta={convocatoria.estado_ingesta.value} | "
            f"cuantia_max_centimos={convocatoria.cuantias.importe_maximo_centimos} | "
            f"{convocatoria.objeto[:80]}"
        )


if __name__ == "__main__":
    main()
