"""Orquestación de la pasada de ingesta de punta a punta — movida desde
`scripts/ejecutar_ingesta.py` a un módulo importable del paquete (PROMPT-026
B1: "MOVIMIENTO mecánico con sus tests detrás; el script queda como CLI fino
que importa de ahí, mismo patrón que preparar_demo"). Necesario para que la
consola web (PROMPT-026 B3) pueda lanzar la MISMA lógica que el CLI sin
duplicarla — la única razón del movimiento.

Hace red real (BDNS) y puede invocar el CLI real de `claude` (consume la
SUSCRIPCIÓN del operador, no una API de pago por token) — por eso NO corre
en pytest ni en CI (regla de oro CLAUDE.md: tests herméticos, sin red).
`ejecutar_pasada`/`ejecutar_pasada_bateria`/`ejecutar_pasada_recalculo` son la
orquestación PURA, testeada con todo inyectado/stub (ver
tests/test_pasada_ingesta.py); `crear_ejecutor_pasada_completa`/
`crear_ejecutor_recalculo` son las factories de cableado REAL (red/CLI/disco)
que reutilizan tanto `scripts/ejecutar_ingesta.py:main()` como la consola web
— NO se testean (mismo patrón que `main()`).
"""
from __future__ import annotations

import itertools
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Sequence

from ongs_ai.adapters.ingesta.base import FiltrosBusqueda, FuenteConvocatorias, TransporteURLLib
from ongs_ai.adapters.ingesta.bdns import (
    MOTIVO_CONCESION_DIRECTA,
    MOTIVO_NO_ABIERTA_EN_ORIGEN,
    FuenteBDNS,
)
from ongs_ai.adapters.ingesta.busquedas_dirigidas import TERMINOS_BUSQUEDA_DIRIGIDA
from ongs_ai.adapters.ingesta.servicio import ingestar
from ongs_ai.dominio.entidades import Convocatoria, EstadoIngesta
from ongs_ai.dominio.ingesta_estado import promocionar_si_completa
from ongs_ai.ia.claude_cli import ClienteClaudeCLI
from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI, GeneradorExplicacion
from ongs_ai.ia.extraccion_requisitos import enriquecer_requisitos
from ongs_ai.servicios.notificacion import Notificador
from ongs_ai.servicios.propuestas import detectar_y_proponer

logger = logging.getLogger(__name__)

# A3 (PROMPT-024): conservador a propósito — cada búsqueda de la batería es una
# petición de red real distinta; con 11 términos, 3 páginas de 50 ya son hasta
# 1650 convocatorias/detalles por pasada.
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
    # A3: vacío en una pasada de una sola búsqueda (`ejecutar_pasada`) o de
    # recálculo (`ejecutar_pasada_recalculo`); con el detalle por término en
    # una pasada por batería (`ejecutar_pasada_bateria`).
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
    None) — ver tests/test_pasada_ingesta.py (B2).
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


def ejecutar_pasada_recalculo(
    almacen,
    notificador: Notificador,
    fecha_referencia: date,
    *,
    generador_ids: Callable[[], str],
    reloj: Callable[[], datetime],
    generador_explicacion: GeneradorExplicacion | None = None,
) -> ResumenPasada:
    """PROMPT-026 B3 — SOLO la fase de matching/propuestas sobre lo YA
    ingerido (sin red, sin fetch, sin enriquecimiento IA de requisitos):
    reutiliza `detectar_y_proponer` sobre el estado actual del almacén, tal
    cual hacen `ejecutar_pasada`/`ejecutar_pasada_bateria` al final de su
    pipeline (mismo guardarraíl de elegibilidad, nunca duplicado). Es la
    acción "Recalcular revisiones" de la consola web — el operador puede
    lanzarla sin esperar a una pasada de ingesta completa, p. ej. tras editar
    la cartera de una entidad."""
    convocatorias = almacen.listar_convocatorias()
    entidades = almacen.listar_entidades()

    resumen_propuestas = detectar_y_proponer(
        entidades,
        convocatorias,
        fecha_referencia,
        almacen,
        notificador,
        generador_ids=generador_ids,
        reloj=reloj,
        generador_explicacion=generador_explicacion,
    )

    return ResumenPasada(
        ingestadas=0,
        ya_existentes=0,
        enriquecidas_por_ia=0,
        promovidas=0,
        propuestas_nuevas=resumen_propuestas.nuevas_propuestas,
        propuestas_sobrevenidas=resumen_propuestas.propuestas_sobrevenidas,
        avisos_intentados=(
            resumen_propuestas.nuevas_propuestas + resumen_propuestas.propuestas_sobrevenidas
        ),
        no_elegibles_persistidas=resumen_propuestas.no_elegibles_persistidas,
        saltadas_pre_puerta=resumen_propuestas.saltadas_pre_puerta,
        llamadas_ia_usadas=0,
        convocatorias_sin_ia_por_freno=0,
        fallos_ia_inesperados=0,
        descartadas_no_abiertas=0,
        descartadas_concesion_directa=0,
    )


class _NotificadorConsola:
    """Sin SMTP configurado: imprime el aviso en vez de enviarlo ("si no,
    stub con aviso en consola")."""

    def __init__(self) -> None:
        self.avisos = 0

    def notificar_propuesta(self, entidad, convocatoria, match) -> None:
        self.avisos += 1
        print(
            f"  [SIN SMTP] Propuesta para {entidad.nombre_legal}: {convocatoria.objeto} "
            f"(match {match.match_id})"
        )


def construir_notificador() -> Notificador:
    if "ONGS_AI_SMTP_HOST" in os.environ and "ONGS_AI_SMTP_REMITENTE" in os.environ:
        from ongs_ai.adapters.avisos.factory import crear_notificador

        return crear_notificador(entorno="produccion")
    print("Aviso: sin ONGS_AI_SMTP_HOST/ONGS_AI_SMTP_REMITENTE — avisos por consola.")
    return _NotificadorConsola()


def _reloj_utc() -> datetime:
    return datetime.now(timezone.utc)


def _generador_ids_uuid() -> str:
    return str(uuid.uuid4())


def crear_ejecutor_pasada_completa(
    almacen,
    *,
    paginas_max: int = PAGINAS_MAX_DEFECTO,
    page_size: int = PAGE_SIZE_DEFECTO,
    max_llamadas_ia: int = MAX_LLAMADAS_IA_DEFECTO,
) -> Callable[[], ResumenPasada]:
    """Cableado REAL (red BDNS + CLI de Claude) de la pasada completa por
    batería — lo comparten `scripts/ejecutar_ingesta.py:main()` (modo por
    defecto) y la acción "Actualizar convocatorias" de la consola web
    (PROMPT-026 B3/B6: la web usa la MISMA suscripción del operador que el
    CLI, con la misma degradación limpia si el CLI no está disponible). NO se
    testea (red/disco/subproceso reales, igual que `main()`)."""

    def ejecutar() -> ResumenPasada:
        fuente = FuenteBDNS(TransporteURLLib(), reloj=_reloj_utc, page_size=page_size)
        cliente_ia = ClienteClaudeCLI()
        generador_explicacion = ExplicadorClaudeCLI(cliente_ia)
        notificador = construir_notificador()
        limite_por_busqueda = paginas_max * page_size

        return ejecutar_pasada_bateria(
            fuente,
            almacen,
            notificador,
            date.today(),
            TERMINOS_BUSQUEDA_DIRIGIDA,
            limite_convocatorias_por_busqueda=limite_por_busqueda,
            cliente_ia=cliente_ia,
            generador_explicacion=generador_explicacion,
            max_llamadas_ia=max_llamadas_ia,
            generador_ids=_generador_ids_uuid,
            reloj=_reloj_utc,
        )

    return ejecutar


def crear_ejecutor_recalculo(
    almacen,
    *,
    max_llamadas_ia: int = MAX_LLAMADAS_IA_DEFECTO,
) -> Callable[[], ResumenPasada]:
    """Cableado REAL de "Recalcular revisiones" (PROMPT-026 B3): sin red
    (nada de `FuenteBDNS`), pero SÍ con el mismo CLI de Claude que la ingesta
    para regenerar explicaciones de las propuestas nuevas/sobrevenidas (B6:
    misma suscripción, mismo freno de llamadas). NO se testea (subproceso
    real, igual que `crear_ejecutor_pasada_completa`)."""

    def ejecutar() -> ResumenPasada:
        cliente_ia = ClienteClaudeCLI()
        generador_explicacion = ExplicadorClaudeCLI(cliente_ia)
        notificador = construir_notificador()

        return ejecutar_pasada_recalculo(
            almacen,
            notificador,
            date.today(),
            generador_ids=_generador_ids_uuid,
            reloj=_reloj_utc,
            generador_explicacion=_GeneradorExplicacionConFreno(
                generador_explicacion, cliente_ia, max_llamadas_ia, _ContadorMutable()
            ),
        )

    return ejecutar
