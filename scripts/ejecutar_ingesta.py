"""Runner MANUAL/programable de ingesta de punta a punta — PROMPT-018 B1.

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

`ejecutar_pasada` (una única búsqueda) y `ejecutar_pasada_bateria` (la
batería completa, resumen POR BÚSQUEDA) son las funciones de orquestación,
testeadas con todo inyectado/stub (B2, sin red ni CLI real; ver
tests/test_ejecutar_ingesta.py). `main()` es el cableado real y NO se testea
(igual que scripts/smoke_bdns.py).

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
import itertools
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.ingesta.base import (  # noqa: E402
    FiltrosBusqueda,
    FuenteConvocatorias,
    TransporteURLLib,
)
from ongs_ai.adapters.ingesta.bdns import (  # noqa: E402
    MOTIVO_CONCESION_DIRECTA,
    MOTIVO_NO_ABIERTA_EN_ORIGEN,
    FuenteBDNS,
)
from ongs_ai.adapters.ingesta.busquedas_dirigidas import TERMINOS_BUSQUEDA_DIRIGIDA  # noqa: E402
from ongs_ai.adapters.ingesta.servicio import ingestar  # noqa: E402
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite, RUTA_DB_DEFECTO  # noqa: E402
from ongs_ai.dominio.entidades import Convocatoria, EstadoIngesta  # noqa: E402
from ongs_ai.dominio.ingesta_estado import promocionar_si_completa  # noqa: E402
from ongs_ai.ia.claude_cli import ClienteClaudeCLI  # noqa: E402
from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI, GeneradorExplicacion  # noqa: E402
from ongs_ai.ia.extraccion_requisitos import enriquecer_requisitos  # noqa: E402
from ongs_ai.servicios.notificacion import Notificador  # noqa: E402
from ongs_ai.servicios.propuestas import detectar_y_proponer  # noqa: E402

logger = logging.getLogger(__name__)

# A3: conservador a propósito — cada búsqueda de la batería es una petición
# de red real distinta; con 11 términos, 3 páginas de 50 ya son hasta 1650
# convocatorias/detalles por pasada.
PAGINAS_MAX_DEFECTO = 3
PAGE_SIZE_DEFECTO = 50
MAX_LLAMADAS_IA_DEFECTO = 25


@dataclass(frozen=True)
class ResumenBusqueda:
    """A3 — resultado de UNA búsqueda dentro de una pasada por batería (o de
    la única búsqueda de una pasada `--texto`)."""

    termino: str
    encontradas: int
    ingestadas: int
    ya_existentes: int
    descartadas_no_abiertas: int
    descartadas_concesion_directa: int


@dataclass(frozen=True)
class ResumenPasada:
    ingestadas: int
    ya_existentes: int
    enriquecidas_por_ia: int
    promovidas: int
    propuestas_nuevas: int
    propuestas_sobrevenidas: int
    avisos_intentados: int
    no_elegibles_persistidas: int
    saltadas_pre_puerta: int
    llamadas_ia_usadas: int
    convocatorias_sin_ia_por_freno: int
    fallos_ia_inesperados: int
    descartadas_no_abiertas: int
    descartadas_concesion_directa: int
    # A3: vacío en una pasada de una sola búsqueda (`ejecutar_pasada`); con
    # el detalle por término en una pasada por batería (`ejecutar_pasada_bateria`).
    por_busqueda: tuple[ResumenBusqueda, ...] = ()


class _FuenteMaterializada:
    """Envoltorio local: `ingestar()` espera una `FuenteConvocatorias` (llama
    a `.buscar()` ella misma); esto evita que la red real de BDNS se golpee
    dos veces (una para recolectar la lista con tope de páginas, otra dentro
    de `ingestar`) — aquí ya no hay red, solo la lista en memoria."""

    def __init__(self, convocatorias: list[Convocatoria]) -> None:
        self._convocatorias = convocatorias

    def buscar(self, filtros: FiltrosBusqueda | None = None) -> list[Convocatoria]:
        return list(self._convocatorias)


class _ContadorMutable:
    """Caja mutable simple para compartir un contador entre el bucle de
    enriquecimiento y `_GeneradorExplicacionConFreno` (A3) — ambos pueden
    incrementarlo, y su valor final viaja al resumen de la pasada."""

    def __init__(self) -> None:
        self.valor = 0

    def incrementar(self) -> None:
        self.valor += 1


def _enriquecer_seguro(
    cliente_ia: ClienteClaudeCLI, convocatoria: Convocatoria
) -> tuple[Convocatoria, bool]:
    """Cinturón y tirantes (A3, fallo real del operador): `enriquecer_requisitos`
    ya degrada limpio ante cualquier fallo QUE `ClienteClaudeCLI.preguntar`
    reconoce (A1/A2), pero un fallo inesperado del cliente (excepción que se
    escapa de `preguntar` pese a esas guardas) NUNCA debe tumbar la pasada de
    ingesta completa — se trata como si esa convocatoria simplemente no se
    hubiera podido enriquecer esta vez."""
    try:
        return enriquecer_requisitos(cliente_ia, convocatoria), False
    except Exception:
        logger.warning(
            "ejecutar_pasada: fallo inesperado del cliente IA enriqueciendo %s",
            convocatoria.convocatoria_id,
            exc_info=True,
        )
        return convocatoria, True


class _GeneradorExplicacionConFreno:
    """Envuelve un `GeneradorExplicacion` real para que respete el mismo tope
    de llamadas IA que la extracción de requisitos (A4) — ambas consumen la
    misma suscripción del operador, así que comparten un único freno.

    También cinturón y tirantes (A3): `servicios.propuestas._generar_explicacion`
    ya atrapa cualquier excepción del generador, pero esta capa la cuenta
    aparte para que quede visible en el resumen de la pasada."""

    def __init__(
        self,
        generador: GeneradorExplicacion,
        cliente: ClienteClaudeCLI,
        max_llamadas: int,
        contador_fallos_inesperados: _ContadorMutable,
    ) -> None:
        self._generador = generador
        self._cliente = cliente
        self._max_llamadas = max_llamadas
        self._contador_fallos_inesperados = contador_fallos_inesperados

    def generar(self, entidad, convocatoria, resultado) -> str:
        if self._cliente.llamadas >= self._max_llamadas:
            return ""
        try:
            return self._generador.generar(entidad, convocatoria, resultado)
        except Exception:
            logger.warning(
                "ejecutar_pasada: fallo inesperado del generador de explicación (%s/%s)",
                entidad.entidad_id,
                convocatoria.convocatoria_id,
                exc_info=True,
            )
            self._contador_fallos_inesperados.incrementar()
            return ""


class _StatsProcesado:
    """Caja mutable de contadores acumulados por `_procesar_convocatorias_fetch`
    — un objeto propio (no un dict) para que los nombres sean explícitos en
    ambos llamadores (`ejecutar_pasada` y `ejecutar_pasada_bateria`, A4: el
    mismo pipeline, nunca duplicado)."""

    def __init__(self) -> None:
        self.enriquecidas = 0
        self.promovidas = 0
        self.sin_ia_por_freno = 0
        self.descartadas_no_abiertas = 0
        self.descartadas_concesion_directa = 0


def _procesar_convocatorias_fetch(
    convocatorias_fetch: list[Convocatoria],
    almacen,
    claves_vistas: set[tuple[str, str]],
    cliente_ia: ClienteClaudeCLI | None,
    max_llamadas_ia: int,
    contador_fallos_inesperados: _ContadorMutable,
    stats: _StatsProcesado,
) -> list[Convocatoria]:
    """A4 — pipeline ÚNICO de dedupe-en-pasada + enriquecimiento IA + promoción
    para un lote ya descargado (una búsqueda completa, dirigida o ad hoc); lo
    reutilizan `ejecutar_pasada` (una búsqueda) y `ejecutar_pasada_bateria`
    (la batería completa, un lote por término) para no duplicar los mismos
    criterios de descarte/promoción del PROMPT-023. `claves_vistas` y `stats`
    son compartidos entre llamadas sucesivas de una misma pasada por batería
    (dedupe y contadores GLOBALES a la pasada, no solo a esta búsqueda)."""
    convocatorias_procesadas: list[Convocatoria] = []

    for convocatoria_fetch in convocatorias_fetch:
        clave = (convocatoria_fetch.fuente.portal, convocatoria_fetch.fuente.url_origen)
        if clave in claves_vistas:
            continue  # ya vista en esta pasada (esta búsqueda u otra de la batería)
        claves_vistas.add(clave)

        # Versión canónica en el almacén: para una convocatoria YA existente
        # (dedupe), puede llevar enriquecimiento de una pasada anterior que
        # el texto recién descargado no tiene — nunca se pisa con el fetch.
        convocatoria = almacen.obtener_por_url_origen(*clave) or convocatoria_fetch

        if convocatoria.estado_ingesta is EstadoIngesta.DESCARTADA_POR_DOMINIO:
            exclusiones = convocatoria.requisitos_elegibilidad.exclusiones
            if MOTIVO_NO_ABIERTA_EN_ORIGEN in exclusiones:
                stats.descartadas_no_abiertas += 1
            if MOTIVO_CONCESION_DIRECTA in exclusiones:
                stats.descartadas_concesion_directa += 1

        actualizada = convocatoria
        if (
            cliente_ia is not None
            and actualizada.estado_ingesta is EstadoIngesta.EXTRAIDA
        ):
            if cliente_ia.llamadas < max_llamadas_ia:
                enriquecida, fallo_inesperado = _enriquecer_seguro(cliente_ia, actualizada)
                if fallo_inesperado:
                    contador_fallos_inesperados.incrementar()
                elif enriquecida is not actualizada:
                    actualizada = enriquecida
                    stats.enriquecidas += 1
            else:
                stats.sin_ia_por_freno += 1

        promovida = promocionar_si_completa(actualizada)
        if promovida.estado_ingesta != actualizada.estado_ingesta:
            stats.promovidas += 1
        actualizada = promovida

        if actualizada is not convocatoria:
            almacen.guardar_convocatoria(actualizada)

        convocatorias_procesadas.append(actualizada)

    return convocatorias_procesadas


def _generador_explicacion_con_freno(
    generador_explicacion: GeneradorExplicacion | None,
    cliente_ia: ClienteClaudeCLI | None,
    max_llamadas_ia: int,
    contador_fallos_inesperados: _ContadorMutable,
) -> GeneradorExplicacion | None:
    if generador_explicacion is not None and cliente_ia is not None:
        return _GeneradorExplicacionConFreno(
            generador_explicacion, cliente_ia, max_llamadas_ia, contador_fallos_inesperados
        )
    return generador_explicacion


def ejecutar_pasada(
    fuente: FuenteConvocatorias,
    almacen,
    notificador: Notificador,
    fecha_referencia: date,
    *,
    filtros: FiltrosBusqueda | None = None,
    limite_convocatorias: int | None = None,
    cliente_ia: ClienteClaudeCLI | None = None,
    generador_explicacion: GeneradorExplicacion | None = None,
    max_llamadas_ia: int = MAX_LLAMADAS_IA_DEFECTO,
    generador_ids: Callable[[], str],
    reloj: Callable[[], datetime],
) -> ResumenPasada:
    """Orquesta una pasada de UNA búsqueda (la de `filtros`, o la búsqueda
    general si es `None`). `almacen` implementa RepositorioEntidades +
    RepositorioConvocatorias + RepositorioMatches (p. ej. AlmacenSQLite /
    AlmacenMemoria en tests). Testeable de punta a punta con todo inyectado:
    sin red real (fuente/notificador stub) ni CLI real (cliente_ia stub o
    None) — ver tests/test_ejecutar_ingesta.py (B2).
    """
    convocatorias_encontradas = fuente.buscar(filtros)
    if limite_convocatorias is not None:
        convocatorias_encontradas = itertools.islice(convocatorias_encontradas, limite_convocatorias)
    convocatorias_fetch = list(convocatorias_encontradas)

    resumen_ingesta = ingestar(_FuenteMaterializada(convocatorias_fetch), almacen, filtros)

    claves_vistas: set[tuple[str, str]] = set()
    contador_fallos_inesperados = _ContadorMutable()
    stats = _StatsProcesado()
    convocatorias_procesadas = _procesar_convocatorias_fetch(
        convocatorias_fetch,
        almacen,
        claves_vistas,
        cliente_ia,
        max_llamadas_ia,
        contador_fallos_inesperados,
        stats,
    )

    generador_explicacion_efectivo = _generador_explicacion_con_freno(
        generador_explicacion, cliente_ia, max_llamadas_ia, contador_fallos_inesperados
    )

    entidades = almacen.listar_entidades()

    resumen_propuestas = detectar_y_proponer(
        entidades,
        convocatorias_procesadas,
        fecha_referencia,
        almacen,
        notificador,
        generador_ids=generador_ids,
        reloj=reloj,
        generador_explicacion=generador_explicacion_efectivo,
    )

    return ResumenPasada(
        ingestadas=resumen_ingesta.nuevas,
        ya_existentes=resumen_ingesta.ya_existentes,
        enriquecidas_por_ia=stats.enriquecidas,
        promovidas=stats.promovidas,
        propuestas_nuevas=resumen_propuestas.nuevas_propuestas,
        propuestas_sobrevenidas=resumen_propuestas.propuestas_sobrevenidas,
        avisos_intentados=(
            resumen_propuestas.nuevas_propuestas + resumen_propuestas.propuestas_sobrevenidas
        ),
        no_elegibles_persistidas=resumen_propuestas.no_elegibles_persistidas,
        saltadas_pre_puerta=resumen_propuestas.saltadas_pre_puerta,
        llamadas_ia_usadas=cliente_ia.llamadas if cliente_ia is not None else 0,
        convocatorias_sin_ia_por_freno=stats.sin_ia_por_freno,
        fallos_ia_inesperados=contador_fallos_inesperados.valor,
        descartadas_no_abiertas=stats.descartadas_no_abiertas,
        descartadas_concesion_directa=stats.descartadas_concesion_directa,
    )


def ejecutar_pasada_bateria(
    fuente: FuenteConvocatorias,
    almacen,
    notificador: Notificador,
    fecha_referencia: date,
    terminos: Sequence[str],
    *,
    limite_convocatorias_por_busqueda: int | None = None,
    cliente_ia: ClienteClaudeCLI | None = None,
    generador_explicacion: GeneradorExplicacion | None = None,
    max_llamadas_ia: int = MAX_LLAMADAS_IA_DEFECTO,
    generador_ids: Callable[[], str],
    reloj: Callable[[], datetime],
) -> ResumenPasada:
    """A3 — orquesta una pasada que recorre TODA la batería de búsquedas
    dirigidas (`terminos`, una por elemento, como `FiltrosBusqueda.descripcion`).
    `limite_convocatorias_por_busqueda` es el tope de páginas POR BÚSQUEDA (no
    global). El dedupe por código BDNS (`claves_vistas`) y el freno de
    llamadas IA (`max_llamadas_ia`, sobre el mismo `cliente_ia`) son
    GLOBALES a la pasada — compartidos entre todas las búsquedas de la
    batería, para no gastar dos veces la misma suscripción del operador ni
    reprocesar una convocatoria que ya trajo una búsqueda anterior. La
    detección de propuestas corre UNA sola vez al final, sobre el conjunto
    ya deduplicado de todas las búsquedas (evita proponer el mismo match dos
    veces si dos términos traen la misma convocatoria en pasadas distintas
    de la misma ejecución).
    """
    claves_vistas: set[tuple[str, str]] = set()
    contador_fallos_inesperados = _ContadorMutable()
    stats_totales = _StatsProcesado()
    convocatorias_procesadas: list[Convocatoria] = []
    resumenes_busqueda: list[ResumenBusqueda] = []
    ingestadas_totales = 0
    ya_existentes_totales = 0

    for termino in terminos:
        filtros = FiltrosBusqueda(descripcion=termino)
        convocatorias_encontradas = fuente.buscar(filtros)
        if limite_convocatorias_por_busqueda is not None:
            convocatorias_encontradas = itertools.islice(
                convocatorias_encontradas, limite_convocatorias_por_busqueda
            )
        convocatorias_fetch = list(convocatorias_encontradas)

        resumen_ingesta = ingestar(_FuenteMaterializada(convocatorias_fetch), almacen, filtros)
        ingestadas_totales += resumen_ingesta.nuevas
        ya_existentes_totales += resumen_ingesta.ya_existentes

        stats_busqueda = _StatsProcesado()
        procesadas = _procesar_convocatorias_fetch(
            convocatorias_fetch,
            almacen,
            claves_vistas,
            cliente_ia,
            max_llamadas_ia,
            contador_fallos_inesperados,
            stats_busqueda,
        )
        convocatorias_procesadas.extend(procesadas)

        stats_totales.enriquecidas += stats_busqueda.enriquecidas
        stats_totales.promovidas += stats_busqueda.promovidas
        stats_totales.sin_ia_por_freno += stats_busqueda.sin_ia_por_freno
        stats_totales.descartadas_no_abiertas += stats_busqueda.descartadas_no_abiertas
        stats_totales.descartadas_concesion_directa += stats_busqueda.descartadas_concesion_directa

        resumenes_busqueda.append(
            ResumenBusqueda(
                termino=termino,
                encontradas=len(convocatorias_fetch),
                ingestadas=resumen_ingesta.nuevas,
                ya_existentes=resumen_ingesta.ya_existentes,
                descartadas_no_abiertas=stats_busqueda.descartadas_no_abiertas,
                descartadas_concesion_directa=stats_busqueda.descartadas_concesion_directa,
            )
        )

    generador_explicacion_efectivo = _generador_explicacion_con_freno(
        generador_explicacion, cliente_ia, max_llamadas_ia, contador_fallos_inesperados
    )

    entidades = almacen.listar_entidades()

    resumen_propuestas = detectar_y_proponer(
        entidades,
        convocatorias_procesadas,
        fecha_referencia,
        almacen,
        notificador,
        generador_ids=generador_ids,
        reloj=reloj,
        generador_explicacion=generador_explicacion_efectivo,
    )

    return ResumenPasada(
        ingestadas=ingestadas_totales,
        ya_existentes=ya_existentes_totales,
        enriquecidas_por_ia=stats_totales.enriquecidas,
        promovidas=stats_totales.promovidas,
        propuestas_nuevas=resumen_propuestas.nuevas_propuestas,
        propuestas_sobrevenidas=resumen_propuestas.propuestas_sobrevenidas,
        avisos_intentados=(
            resumen_propuestas.nuevas_propuestas + resumen_propuestas.propuestas_sobrevenidas
        ),
        no_elegibles_persistidas=resumen_propuestas.no_elegibles_persistidas,
        saltadas_pre_puerta=resumen_propuestas.saltadas_pre_puerta,
        llamadas_ia_usadas=cliente_ia.llamadas if cliente_ia is not None else 0,
        convocatorias_sin_ia_por_freno=stats_totales.sin_ia_por_freno,
        fallos_ia_inesperados=contador_fallos_inesperados.valor,
        descartadas_no_abiertas=stats_totales.descartadas_no_abiertas,
        descartadas_concesion_directa=stats_totales.descartadas_concesion_directa,
        por_busqueda=tuple(resumenes_busqueda),
    )


class _NotificadorConsola:
    """Sin SMTP configurado: imprime el aviso en vez de enviarlo (B1 — "si no,
    stub con aviso en consola")."""

    def __init__(self) -> None:
        self.avisos = 0

    def notificar_propuesta(self, entidad, convocatoria, match) -> None:
        self.avisos += 1
        print(
            f"  [SIN SMTP] Propuesta para {entidad.nombre_legal}: {convocatoria.objeto} "
            f"(match {match.match_id})"
        )


def _construir_notificador() -> Notificador:
    if "ONGS_AI_SMTP_HOST" in os.environ and "ONGS_AI_SMTP_REMITENTE" in os.environ:
        from ongs_ai.adapters.avisos.factory import crear_notificador

        return crear_notificador(entorno="produccion")
    print("Aviso: sin ONGS_AI_SMTP_HOST/ONGS_AI_SMTP_REMITENTE — avisos por consola.")
    return _NotificadorConsola()


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

    def reloj() -> datetime:
        return datetime.now(timezone.utc)

    def generador_ids() -> str:
        return str(uuid.uuid4())

    fecha_referencia = date.today()  # explícito aquí, fuera del dominio

    almacen = AlmacenSQLite(RUTA_DB_DEFECTO)
    fuente = FuenteBDNS(TransporteURLLib(), reloj=reloj, page_size=args.page_size)
    cliente_ia = ClienteClaudeCLI()
    generador_explicacion = ExplicadorClaudeCLI(cliente_ia)
    notificador = _construir_notificador()
    limite_por_busqueda = args.paginas_max * args.page_size

    if args.texto is not None:
        # `--texto`: búsqueda ad hoc única (probar un término antes de sumarlo
        # a la batería versionada, o repetir la pasada de una entidad concreta).
        filtros = FiltrosBusqueda(
            descripcion=args.texto,
            fecha_desde=date.fromisoformat(args.fecha_desde) if args.fecha_desde else None,
            fecha_hasta=date.fromisoformat(args.fecha_hasta) if args.fecha_hasta else None,
        )
        resumen = ejecutar_pasada(
            fuente,
            almacen,
            notificador,
            fecha_referencia,
            filtros=filtros,
            limite_convocatorias=limite_por_busqueda,
            cliente_ia=cliente_ia,
            generador_explicacion=generador_explicacion,
            max_llamadas_ia=args.max_llamadas_ia,
            generador_ids=generador_ids,
            reloj=reloj,
        )
    else:
        # Modo por defecto (PROMPT-024): batería completa de búsquedas dirigidas.
        resumen = ejecutar_pasada_bateria(
            fuente,
            almacen,
            notificador,
            fecha_referencia,
            TERMINOS_BUSQUEDA_DIRIGIDA,
            limite_convocatorias_por_busqueda=limite_por_busqueda,
            cliente_ia=cliente_ia,
            generador_explicacion=generador_explicacion,
            max_llamadas_ia=args.max_llamadas_ia,
            generador_ids=generador_ids,
            reloj=reloj,
        )

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
