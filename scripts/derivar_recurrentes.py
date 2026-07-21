"""CLI manual — deriva convocatorias esperadas para las entidades captadas
(ADR-007 §3.4, F-proactivo.1 §9).

Hace red real (BDNS) — por eso NO corre en pytest ni en CI (regla de oro
CLAUDE.md: tests herméticos, sin red). La orquestación
(`servicios/recurrentes.py::capturar_y_derivar_entidad`) SÍ está testeada
(`tests/test_recurrentes_servicio.py`); este script es CLI fino sobre ella,
mismo patrón que `preparar_demo.py`.

Por defecto recorre TODAS las entidades captadas con NIF real (backend según
`ONGS_AI_ENV`, mismo que el resto de la plataforma): consulta
`nifCif`+fechas de los últimos N años (5 por defecto, ADR-007 §8.1), puebla
el historial, deriva esperadas, imprime resumen.

`--nif-prueba <NIF>` consulta y deriva EN MEMORIA (AlmacenMemoria, nunca la
base real) — smoke sin contaminar datos reales.

Uso:
    python scripts/derivar_recurrentes.py
    python scripts/derivar_recurrentes.py --nif-prueba P0704500H
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.ingesta.base import TransporteURLLib  # noqa: E402
from ongs_ai.adapters.ingesta.bdns_concesiones import FuenteConcesionesBDNS  # noqa: E402
from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria  # noqa: E402
from ongs_ai.dominio.entidades import (  # noqa: E402
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    DatosEconomicos,
    Entidad,
    FormaJuridica,
    FormaJuridicaDeclarada,
    TipoActividad,
)
from ongs_ai.servicios.recurrentes import (  # noqa: E402
    ANIOS_HISTORIAL_DEFECTO,
    ResumenCaptura,
    capturar_y_derivar_entidad,
)


def _reloj_utc() -> datetime:
    return datetime.now(timezone.utc)


def _generador_id_uuid() -> str:
    return str(uuid.uuid4())


def _ventana_fechas(anios: int, *, hoy: date) -> tuple[date, date]:
    return date(hoy.year - anios, hoy.month, 1), hoy


def _entidad_prueba(nif: str, *, ahora: datetime) -> Entidad:
    """Entidad mínima EN MEMORIA para `--nif-prueba` — nunca se persiste ni
    se guarda en ningún almacén real (smoke sin contaminar la base)."""
    return Entidad(
        entidad_id=f"prueba-{nif}",
        nombre_legal=f"Entidad de prueba ({nif})",
        nif=nif,
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.OTRA, descripcion="entidad de prueba (smoke)"),
        fecha_constitucion=date(2000, 1, 1),
        enfermedad_o_colectivo="smoke de prueba — no es un colectivo real",
        actividades=(ActividadDeclarada(tipo=TipoActividad.OTRO, descripcion="smoke de prueba"),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=0, gastos_centimos=0, ejercicio=ahora.year
        ),
        requisitos_formales_disponibles=(),
        contacto=Contacto(),
        creado_en=ahora,
        actualizado_en=ahora,
    )


def _imprimir_resumen(entidad: Entidad, resumen: ResumenCaptura) -> None:
    print(
        f"- {entidad.entidad_id} ({entidad.nif}): "
        f"capturadas={resumen.concesiones_encontradas} nuevas={resumen.concesiones_nuevas} "
        f"descartadas={resumen.concesiones_descartadas} series={resumen.series_detectadas} "
        f"esperadas[baja={resumen.esperadas_baja} media={resumen.esperadas_media} "
        f"alta={resumen.esperadas_alta}]"
    )


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nif-prueba",
        default=None,
        help="Consulta y deriva EN MEMORIA para este NIF, sin persistir (smoke sin tocar la base real)",
    )
    parser.add_argument(
        "--anios-historial",
        type=int,
        default=ANIOS_HISTORIAL_DEFECTO,
        help=f"Profundidad del historial en años (por defecto {ANIOS_HISTORIAL_DEFECTO}, ADR-007 §8.1)",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parsear_argumentos()
    ahora = _reloj_utc()
    fecha_desde, fecha_hasta = _ventana_fechas(args.anios_historial, hoy=ahora.date())

    if args.nif_prueba:
        print(f"=== Smoke EN MEMORIA para NIF {args.nif_prueba} (sin persistir) ===")
        almacen = AlmacenMemoria()
        entidad = _entidad_prueba(args.nif_prueba, ahora=ahora)
        fuente = FuenteConcesionesBDNS(TransporteURLLib(), reloj=_reloj_utc, generador_id=_generador_id_uuid)
        resumen = capturar_y_derivar_entidad(
            entidad,
            fuente,
            almacen,
            almacen,
            ahora.date(),
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            generador_id=_generador_id_uuid,
            reloj=_reloj_utc,
        )
        _imprimir_resumen(entidad, resumen)
        return

    from ongs_ai.adapters.persistencia.factory import crear_almacen

    almacen = crear_almacen()
    entidades_con_nif = [e for e in almacen.listar_entidades() if e.nif]
    if not entidades_con_nif:
        print("Sin entidades captadas con NIF — nada que derivar.")
        return

    print(
        f"=== Derivación de recurrentes ({len(entidades_con_nif)} entidad(es), "
        f"últimos {args.anios_historial} años) ==="
    )
    for entidad in entidades_con_nif:
        fuente = FuenteConcesionesBDNS(TransporteURLLib(), reloj=_reloj_utc, generador_id=_generador_id_uuid)
        try:
            resumen = capturar_y_derivar_entidad(
                entidad,
                fuente,
                almacen,
                almacen,
                ahora.date(),
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                generador_id=_generador_id_uuid,
                reloj=_reloj_utc,
            )
        except Exception as exc:  # degradación limpia (CLAUDE.md): una entidad no tumba el resto
            print(f"- {entidad.entidad_id} ({entidad.nif}): FALLO ({exc})")
            continue
        _imprimir_resumen(entidad, resumen)


if __name__ == "__main__":
    main()
