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

`ejecutar_pasada` es la función de orquestación, testeada con todo
inyectado/stub (B2, sin red ni CLI real; ver tests/test_ejecutar_ingesta.py).
`main()` es el cableado real y NO se testea (igual que scripts/smoke_bdns.py).

Uso:
    python scripts/ejecutar_ingesta.py [--texto TEXTO] [--fecha-desde AAAA-MM-DD]
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
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.ingesta.base import (  # noqa: E402
    FiltrosBusqueda,
    FuenteConvocatorias,
    TransporteURLLib,
)
from ongs_ai.adapters.ingesta.bdns import FuenteBDNS  # noqa: E402
from ongs_ai.adapters.ingesta.servicio import ingestar  # noqa: E402
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite, RUTA_DB_DEFECTO  # noqa: E402
from ongs_ai.dominio.entidades import Convocatoria, EstadoIngesta  # noqa: E402
from ongs_ai.dominio.ingesta_estado import promocionar_si_completa  # noqa: E402
from ongs_ai.ia.claude_cli import ClienteClaudeCLI  # noqa: E402
from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI, GeneradorExplicacion  # noqa: E402
from ongs_ai.ia.extraccion_requisitos import enriquecer_requisitos  # noqa: E402
from ongs_ai.servicios.notificacion import Notificador  # noqa: E402
from ongs_ai.servicios.propuestas import detectar_y_proponer  # noqa: E402

PAGINAS_MAX_DEFECTO = 1
PAGE_SIZE_DEFECTO = 50
MAX_LLAMADAS_IA_DEFECTO = 25


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


class _FuenteMaterializada:
    """Envoltorio local: `ingestar()` espera una `FuenteConvocatorias` (llama
    a `.buscar()` ella misma); esto evita que la red real de BDNS se golpee
    dos veces (una para recolectar la lista con tope de páginas, otra dentro
    de `ingestar`) — aquí ya no hay red, solo la lista en memoria."""

    def __init__(self, convocatorias: list[Convocatoria]) -> None:
        self._convocatorias = convocatorias

    def buscar(self, filtros: FiltrosBusqueda | None = None) -> list[Convocatoria]:
        return list(self._convocatorias)


class _GeneradorExplicacionConFreno:
    """Envuelve un `GeneradorExplicacion` real para que respete el mismo tope
    de llamadas IA que la extracción de requisitos (A4) — ambas consumen la
    misma suscripción del operador, así que comparten un único freno."""

    def __init__(
        self, generador: GeneradorExplicacion, cliente: ClienteClaudeCLI, max_llamadas: int
    ) -> None:
        self._generador = generador
        self._cliente = cliente
        self._max_llamadas = max_llamadas

    def generar(self, entidad, convocatoria, resultado) -> str:
        if self._cliente.llamadas >= self._max_llamadas:
            return ""
        return self._generador.generar(entidad, convocatoria, resultado)


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
    """Orquesta una pasada completa. `almacen` implementa RepositorioEntidades
    + RepositorioConvocatorias + RepositorioMatches (p. ej. AlmacenSQLite /
    AlmacenMemoria en tests). Testeable de punta a punta con todo inyectado:
    sin red real (fuente/notificador stub) ni CLI real (cliente_ia stub o
    None) — ver tests/test_ejecutar_ingesta.py (B2).
    """
    convocatorias_encontradas = fuente.buscar(filtros)
    if limite_convocatorias is not None:
        convocatorias_encontradas = itertools.islice(convocatorias_encontradas, limite_convocatorias)
    convocatorias_fetch = list(convocatorias_encontradas)

    resumen_ingesta = ingestar(_FuenteMaterializada(convocatorias_fetch), almacen, filtros)

    convocatorias_procesadas: list[Convocatoria] = []
    enriquecidas = 0
    promovidas = 0
    sin_ia_por_freno = 0
    claves_vistas: set[tuple[str, str]] = set()

    for convocatoria_fetch in convocatorias_fetch:
        clave = (convocatoria_fetch.fuente.portal, convocatoria_fetch.fuente.url_origen)
        if clave in claves_vistas:
            continue  # la propia fuente podría repetir un item en una misma pasada
        claves_vistas.add(clave)

        # Versión canónica en el almacén: para una convocatoria YA existente
        # (dedupe), puede llevar enriquecimiento de una pasada anterior que
        # el texto recién descargado no tiene — nunca se pisa con el fetch.
        convocatoria = almacen.obtener_por_url_origen(*clave) or convocatoria_fetch

        actualizada = convocatoria
        if (
            cliente_ia is not None
            and actualizada.estado_ingesta is EstadoIngesta.EXTRAIDA
        ):
            if cliente_ia.llamadas < max_llamadas_ia:
                enriquecida = enriquecer_requisitos(cliente_ia, actualizada)
                if enriquecida is not actualizada:
                    actualizada = enriquecida
                    enriquecidas += 1
            else:
                sin_ia_por_freno += 1

        promovida = promocionar_si_completa(actualizada)
        if promovida.estado_ingesta != actualizada.estado_ingesta:
            promovidas += 1
        actualizada = promovida

        if actualizada is not convocatoria:
            almacen.guardar_convocatoria(actualizada)

        convocatorias_procesadas.append(actualizada)

    generador_explicacion_efectivo = generador_explicacion
    if generador_explicacion is not None and cliente_ia is not None:
        generador_explicacion_efectivo = _GeneradorExplicacionConFreno(
            generador_explicacion, cliente_ia, max_llamadas_ia
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
        enriquecidas_por_ia=enriquecidas,
        promovidas=promovidas,
        propuestas_nuevas=resumen_propuestas.nuevas_propuestas,
        propuestas_sobrevenidas=resumen_propuestas.propuestas_sobrevenidas,
        avisos_intentados=(
            resumen_propuestas.nuevas_propuestas + resumen_propuestas.propuestas_sobrevenidas
        ),
        no_elegibles_persistidas=resumen_propuestas.no_elegibles_persistidas,
        saltadas_pre_puerta=resumen_propuestas.saltadas_pre_puerta,
        llamadas_ia_usadas=cliente_ia.llamadas if cliente_ia is not None else 0,
        convocatorias_sin_ia_por_freno=sin_ia_por_freno,
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
    filtros = FiltrosBusqueda(
        descripcion=args.texto,
        fecha_desde=date.fromisoformat(args.fecha_desde) if args.fecha_desde else None,
        fecha_hasta=date.fromisoformat(args.fecha_hasta) if args.fecha_hasta else None,
    )

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

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        fecha_referencia,
        filtros=filtros,
        limite_convocatorias=args.paginas_max * args.page_size,
        cliente_ia=cliente_ia,
        generador_explicacion=generador_explicacion,
        max_llamadas_ia=args.max_llamadas_ia,
        generador_ids=generador_ids,
        reloj=reloj,
    )

    print()
    print("=== Resumen de la pasada ===")
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


if __name__ == "__main__":
    main()
