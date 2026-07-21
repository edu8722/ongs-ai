"""Reevaluación de ingesta YA HECHA — PROMPT-023 C (limpieza tras el
hallazgo numConv=920435: ámbito NUTS1 mal mapeado, `abierto=false` y
concesiones directas ofrecidos como oportunidad, ver
`engineering/06_SIGUIENTES_PASOS.md`).

Recorre las convocatorias `bdns-*` YA en el almacén, re-consulta su detalle
REAL contra la BDNS y re-aplica el mapeo/filtros ya corregidos en
`adapters/ingesta/bdns.py` (`_ambito_y_region_desde_regiones` +
`_aplicar_tope_por_organo` para el ámbito, `_motivos_descarte_dominio` para
`abierto`/`tipoConvocatoria`): (a) corrige `ambito_geografico`/`region`/
`provincia`/`requisitos_elegibilidad.ambito_territorial_requerido` si
cambiaron: (b) escala a `DESCARTADA_POR_DOMINIO` las que ahora califican
(nunca al revés — una convocatoria ya descartada no se reevalúa para
"rescatarla"). El resto de `requisitos_elegibilidad` (enriquecimiento IA
previo: forma jurídica, antigüedad, requisitos formales) se conserva intacto.

`reevaluar_pasada` es la orquestación, testeada con todo inyectado/stub (sin
red, sin disco) — ver `tests/test_reevaluar_ingesta.py`. `main()` es el
cableado real (transporte HTTP real + `AlmacenSQLite`) y NO se testea (mismo
patrón que `scripts/ejecutar_ingesta.py`).

Por defecto SIMULA: imprime el plan de cambios sin escribir nada. Escribir
exige `--aplicar`.

Uso:
    python scripts/reevaluar_ingesta.py             # simula (por defecto)
    python scripts/reevaluar_ingesta.py --simular    # explícito, igual que el defecto
    python scripts/reevaluar_ingesta.py --aplicar    # persiste los cambios
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.ingesta.base import TransporteHTTP, TransporteURLLib  # noqa: E402
from ongs_ai.adapters.ingesta.bdns import (  # noqa: E402
    URL_DETALLE_BDNS,
    _ambito_y_region_desde_regiones,
    _aplicar_tope_por_organo,
    _motivos_descarte_dominio,
)
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite, RUTA_DB_DEFECTO  # noqa: E402
from ongs_ai.dominio.entidades import AmbitoTerritorial, Convocatoria, EstadoIngesta  # noqa: E402

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class CambioReevaluacion:
    """Una fila del plan — legible por el operador ANTES de aplicar nada."""

    convocatoria_id: str
    hay_cambio: bool
    ambito_antes: AmbitoTerritorial
    ambito_despues: AmbitoTerritorial
    region_antes: str | None
    region_despues: str | None
    provincia_antes: str | None
    provincia_despues: str | None
    estado_antes: EstadoIngesta
    estado_despues: EstadoIngesta


@dataclasses.dataclass(frozen=True)
class ResumenReevaluacion:
    revisadas: int
    con_cambios: int
    fallos_transporte: int
    aplicado: bool


def _convocatoria_reevaluada(
    vieja: Convocatoria, detalle: dict, *, ahora: datetime
) -> tuple[Convocatoria, CambioReevaluacion]:
    """Recalcula ámbito (A) y descarte por dominio (B) a partir del detalle
    REAL re-consultado; nunca toca el resto de `requisitos_elegibilidad`
    (enriquecimiento IA previo) ni degrada un estado ya DESCARTADA_POR_DOMINIO."""
    organo = detalle.get("organo") or {}
    ambito, region, provincia = _ambito_y_region_desde_regiones(detalle.get("regiones") or [])
    ambito, region, provincia = _aplicar_tope_por_organo(ambito, region, provincia, organo)
    motivos = _motivos_descarte_dominio(detalle)

    estado_nuevo = vieja.estado_ingesta
    exclusiones_nuevas = vieja.requisitos_elegibilidad.exclusiones
    if motivos and vieja.estado_ingesta is not EstadoIngesta.DESCARTADA_POR_DOMINIO:
        estado_nuevo = EstadoIngesta.DESCARTADA_POR_DOMINIO
        exclusiones_nuevas = motivos

    hay_cambio = (
        ambito != vieja.ambito_geografico
        or region != vieja.region
        or provincia != vieja.provincia
        or estado_nuevo != vieja.estado_ingesta
    )

    cambio = CambioReevaluacion(
        convocatoria_id=vieja.convocatoria_id,
        hay_cambio=hay_cambio,
        ambito_antes=vieja.ambito_geografico,
        ambito_despues=ambito,
        region_antes=vieja.region,
        region_despues=region,
        provincia_antes=vieja.provincia,
        provincia_despues=provincia,
        estado_antes=vieja.estado_ingesta,
        estado_despues=estado_nuevo,
    )

    if not hay_cambio:
        return vieja, cambio

    nueva = dataclasses.replace(
        vieja,
        ambito_geografico=ambito,
        region=region,
        provincia=provincia,
        estado_ingesta=estado_nuevo,
        requisitos_elegibilidad=dataclasses.replace(
            vieja.requisitos_elegibilidad,
            ambito_territorial_requerido=ambito,
            exclusiones=exclusiones_nuevas,
        ),
        actualizado_en=ahora,
    )
    return nueva, cambio


def reevaluar_pasada(
    almacen, transporte: TransporteHTTP, *, ahora: datetime, aplicar: bool
) -> tuple[ResumenReevaluacion, list[CambioReevaluacion]]:
    """Orquesta la reevaluación completa. `almacen` implementa
    `RepositorioConvocatorias` (AlmacenSQLite/AlmacenMemoria). Fallo de
    transporte en una convocatoria concreta degrada limpio: se registra, se
    salta y se sigue con las demás (mismo patrón que `FuenteBDNS.buscar`)."""
    revisadas = 0
    con_cambios = 0
    fallos_transporte = 0
    cambios: list[CambioReevaluacion] = []

    for vieja in almacen.listar_convocatorias():
        if vieja.fuente.portal != "BDNS":
            continue
        codigo_bdns = vieja.convocatoria_id.removeprefix("bdns-")
        revisadas += 1
        try:
            detalle = transporte.obtener_json(URL_DETALLE_BDNS, {"numConv": codigo_bdns})
        except Exception as exc:  # transporte que falla: degrada limpio, no propaga
            logger.warning(
                "reevaluar_pasada: fallo de transporte re-consultando %s: %s",
                vieja.convocatoria_id,
                exc,
            )
            fallos_transporte += 1
            continue

        nueva, cambio = _convocatoria_reevaluada(vieja, detalle, ahora=ahora)
        cambios.append(cambio)
        if cambio.hay_cambio:
            con_cambios += 1
            if aplicar:
                almacen.guardar_convocatoria(nueva)

    resumen = ResumenReevaluacion(
        revisadas=revisadas,
        con_cambios=con_cambios,
        fallos_transporte=fallos_transporte,
        aplicado=aplicar,
    )
    return resumen, cambios


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--simular",
        action="store_true",
        help="Imprime el plan de cambios SIN escribir nada (comportamiento por defecto).",
    )
    grupo.add_argument(
        "--aplicar",
        action="store_true",
        help="Persiste los cambios detectados en el almacén.",
    )
    return parser.parse_args(argv)


def _imprimir_cambio(cambio: CambioReevaluacion) -> None:
    print(f"- {cambio.convocatoria_id}:")
    if cambio.ambito_antes != cambio.ambito_despues:
        print(f"    ambito_geografico: {cambio.ambito_antes.value} -> {cambio.ambito_despues.value}")
    if cambio.region_antes != cambio.region_despues:
        print(f"    region: {cambio.region_antes!r} -> {cambio.region_despues!r}")
    if cambio.provincia_antes != cambio.provincia_despues:
        print(f"    provincia: {cambio.provincia_antes!r} -> {cambio.provincia_despues!r}")
    if cambio.estado_antes != cambio.estado_despues:
        print(f"    estado_ingesta: {cambio.estado_antes.value} -> {cambio.estado_despues.value}")


def main() -> None:
    args = _parsear_argumentos()
    aplicar = bool(args.aplicar)

    def reloj() -> datetime:
        return datetime.now(timezone.utc)

    almacen = AlmacenSQLite(RUTA_DB_DEFECTO)
    transporte = TransporteURLLib()

    resumen, cambios = reevaluar_pasada(almacen, transporte, ahora=reloj(), aplicar=aplicar)

    print()
    print(f"=== Plan de reevaluación ({'APLICADO' if aplicar else 'SIMULADO — nada escrito'}) ===")
    cambios_reales = [c for c in cambios if c.hay_cambio]
    if not cambios_reales:
        print("Sin cambios respecto al mapeo/filtros actuales.")
    for cambio in cambios_reales:
        _imprimir_cambio(cambio)

    print()
    print("=== Resumen ===")
    print(f"Convocatorias BDNS revisadas: {resumen.revisadas}")
    print(f"Con cambios detectados: {resumen.con_cambios}")
    print(f"Fallos de transporte (saltadas): {resumen.fallos_transporte}")
    if not aplicar:
        print("Modo SIMULAR: nada se ha escrito. Repite con --aplicar para persistir estos cambios.")


if __name__ == "__main__":
    main()
