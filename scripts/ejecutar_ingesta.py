"""CLI de la pasada de ingesta de punta a punta — PROMPT-018 B1, adelgazado a
CLI fino en PROMPT-026 B1 (la orquestación real vive en
`ongs_ai.servicios.pasada_ingesta`, mismo patrón que `preparar_demo`).

Hace red real (BDNS) y puede invocar el CLI real de `claude` (consume la
SUSCRIPCIÓN del operador, no una API de pago por token) — por eso NO corre
en pytest ni en CI (regla de oro CLAUDE.md: tests herméticos, sin red). Lo
ejecuta el OPERADOR a mano (o programado, p. ej. Programador de tareas de
Windows).

Pipeline por pasada:
    FuenteBDNS.buscar (filtros + tope de páginas)
      -> ingestar (dedupe por portal+url_origen)
      -> extracción IA de requisitos (con freno de llamadas)
      -> promocionar_si_completa
      -> detectar_y_proponer (explicación IA + aviso por email si hay SMTP,
         o aviso por consola si no)
      -> resumen impreso

MODO POR DEFECTO (PROMPT-024, cobertura): recorre la batería VERSIONADA de
búsquedas dirigidas (`adapters/ingesta/busquedas_dirigidas.TERMINOS_BUSQUEDA_
DIRIGIDA`) — la búsqueda general paginada por fecha de publicación NUNCA
encuentra el histórico de una entidad (IRPF, fines sociales...), solo las
convocatorias más recientes. `--texto` sigue disponible para UNA búsqueda ad
hoc puntual (p. ej. probar un término nuevo antes de sumarlo a la batería).
El tope de páginas (`--paginas-max`) aplica POR BÚSQUEDA en ambos modos; el
dedupe por código BDNS (portal+url_origen) evita duplicados entre búsquedas
de la misma pasada, y el freno de llamadas IA (`--max-llamadas-ia`) es
GLOBAL a toda la pasada (todas las búsquedas comparten la misma suscripción).

Esta misma pasada por batería (modo por defecto) es la que lanza también el
botón "Actualizar convocatorias" de la consola web (PROMPT-026 B3), vía
`ongs_ai.servicios.pasada_ingesta.crear_ejecutor_pasada_completa` — NUNCA
duplicada, solo reutilizada.

Uso:
    python scripts/ejecutar_ingesta.py [--paginas-max N] [--page-size N] [--max-llamadas-ia N]
    python scripts/ejecutar_ingesta.py --texto TEXTO [--fecha-desde AAAA-MM-DD]
        [--fecha-hasta AAAA-MM-DD] [--paginas-max N] [--page-size N]
        [--max-llamadas-ia N]

Variables de entorno para aviso por email real (opcionales — sin ellas, el
aviso sale por consola): ONGS_AI_SMTP_HOST, ONGS_AI_SMTP_REMITENTE,
ONGS_AI_SMTP_PUERTO, ONGS_AI_SMTP_USUARIO, ONGS_AI_SMTP_CONTRASENA.
Para el CLI de IA: ONGS_AI_CLAUDE_CLI (ruta del binario, por defecto "claude").
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.ingesta.base import FiltrosBusqueda, TransporteURLLib  # noqa: E402
from ongs_ai.adapters.ingesta.bdns import FuenteBDNS  # noqa: E402
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite, RUTA_DB_DEFECTO  # noqa: E402
from ongs_ai.ia.claude_cli import ClienteClaudeCLI  # noqa: E402
from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI  # noqa: E402
from ongs_ai.servicios.pasada_ingesta import (  # noqa: E402
    MAX_LLAMADAS_IA_DEFECTO,
    PAGE_SIZE_DEFECTO,
    PAGINAS_MAX_DEFECTO,
    ResumenBusqueda,
    ResumenPasada,
    construir_notificador,
    crear_ejecutor_pasada_completa,
    ejecutar_pasada,
    ejecutar_pasada_bateria,
)

# Re-exportados para no romper `from ejecutar_ingesta import ...` en llamadores
# existentes (`scripts/preparar_demo.py`) — la implementación vive en
# `ongs_ai.servicios.pasada_ingesta`.
_construir_notificador = construir_notificador

__all__ = [
    "MAX_LLAMADAS_IA_DEFECTO",
    "PAGE_SIZE_DEFECTO",
    "PAGINAS_MAX_DEFECTO",
    "ResumenBusqueda",
    "ResumenPasada",
    "ejecutar_pasada",
    "ejecutar_pasada_bateria",
    "main",
]


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--texto", default=None, help="Filtro de descripción de la búsqueda BDNS")
    parser.add_argument("--fecha-desde", default=None, help="AAAA-MM-DD")
    parser.add_argument("--fecha-hasta", default=None, help="AAAA-MM-DD")
    parser.add_argument("--paginas-max", type=int, default=PAGINAS_MAX_DEFECTO)
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE_DEFECTO)
    parser.add_argument("--max-llamadas-ia", type=int, default=MAX_LLAMADAS_IA_DEFECTO)
    return parser.parse_args(argv)


def main() -> None:
    args = _parsear_argumentos()

    almacen = AlmacenSQLite(RUTA_DB_DEFECTO)

    if args.texto is not None:
        # `--texto`: búsqueda ad hoc única (probar un término antes de sumarlo
        # a la batería versionada, o repetir la pasada de una entidad concreta)
        # — cableado propio, no lo necesita la consola web (B3 solo relanza la
        # batería completa).
        def reloj() -> datetime:
            return datetime.now(timezone.utc)

        def generador_ids() -> str:
            return str(uuid.uuid4())

        fuente = FuenteBDNS(TransporteURLLib(), reloj=reloj, page_size=args.page_size)
        cliente_ia = ClienteClaudeCLI()
        generador_explicacion = ExplicadorClaudeCLI(cliente_ia)
        notificador = construir_notificador()
        limite_por_busqueda = args.paginas_max * args.page_size

        filtros = FiltrosBusqueda(
            descripcion=args.texto,
            fecha_desde=date.fromisoformat(args.fecha_desde) if args.fecha_desde else None,
            fecha_hasta=date.fromisoformat(args.fecha_hasta) if args.fecha_hasta else None,
        )
        resumen = ejecutar_pasada(
            fuente,
            almacen,
            notificador,
            date.today(),
            filtros=filtros,
            limite_convocatorias=limite_por_busqueda,
            cliente_ia=cliente_ia,
            generador_explicacion=generador_explicacion,
            max_llamadas_ia=args.max_llamadas_ia,
            generador_ids=generador_ids,
            reloj=reloj,
        )
    else:
        # Modo por defecto (PROMPT-024): batería completa de búsquedas
        # dirigidas — MISMO cableado que la acción web "Actualizar convocatorias".
        ejecutor = crear_ejecutor_pasada_completa(
            almacen,
            paginas_max=args.paginas_max,
            page_size=args.page_size,
            max_llamadas_ia=args.max_llamadas_ia,
        )
        resumen = ejecutor()

    print()
    print("=== Resumen de la pasada ===")
    if resumen.por_busqueda:
        print("--- Por búsqueda ---")
        for r in resumen.por_busqueda:
            print(
                f"  [{r.termino}] encontradas={r.encontradas} ingestadas={r.ingestadas} "
                f"ya_existentes={r.ya_existentes} "
                f"descartadas_no_abiertas={r.descartadas_no_abiertas} "
                f"descartadas_concesion_directa={r.descartadas_concesion_directa}"
            )
        print()
    print(f"Convocatorias ingestadas (nuevas): {resumen.ingestadas}")
    print(f"Convocatorias ya existentes (deduplicadas): {resumen.ya_existentes}")
    print(f"Enriquecidas por IA: {resumen.enriquecidas_por_ia}")
    print(f"Promovidas a VERIFICADA: {resumen.promovidas}")
    print(f"Propuestas nuevas: {resumen.propuestas_nuevas}")
    print(f"Propuestas sobrevenidas (re-detección): {resumen.propuestas_sobrevenidas}")
    print(f"Avisos intentados: {resumen.avisos_intentados}")
    print(f"Detectadas no elegibles (persistidas): {resumen.no_elegibles_persistidas}")
    print(f"Saltadas por pre-puerta (sin verificar/plazo cerrado): {resumen.saltadas_pre_puerta}")
    print(f"Llamadas IA usadas: {resumen.llamadas_ia_usadas} (tope: {args.max_llamadas_ia})")
    print(f"Convocatorias sin IA por freno de plan: {resumen.convocatorias_sin_ia_por_freno}")
    print(f"Fallos IA inesperados (degradados, la pasada siguió): {resumen.fallos_ia_inesperados}")
    print(f"Descartadas por dominio (no abiertas en origen): {resumen.descartadas_no_abiertas}")
    print(f"Descartadas por dominio (concesión directa): {resumen.descartadas_concesion_directa}")


if __name__ == "__main__":
    main()
