"""Orquestación del proactivo — ADR-007 §3.4/§3.6/§3.8: captura del historial
de concesiones de una entidad, persistencia con dedupe, derivación
determinista de esperadas, enlace con la ingesta ya existente y transición a
`NO_APARECIDA`. Compone puertos, no dominio puro (mismo criterio que
`servicios/propuestas.py`); ids y reloj SIEMPRE inyectados (CLAUDE.md).

Una esperada NUNCA crea Match ni notifica por sí misma (§3.6): el enlace solo
transiciona su estado y guarda `convocatoria_id_enlazada`; el flujo normal de
ADR-004 (`detectar_y_proponer`, ya con la convocatoria en el catálogo) decide
elegibilidad y aviso. El aviso "ventana próxima" (§3.8.2) es SOLO panel y su
vista es F-proactivo.2 — aquí solo se materializa el dato (`ConvocatoriaEsperada`
con estado `ESPERADA` y su ventana), sin disparar ningún canal.
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Sequence

from ongs_ai.adapters.ingesta.bdns_concesiones import FuenteConcesionesBDNS
from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.proactivo.derivacion import (
    derivar_esperadas_de_entidad,
    fingerprint_desde_convocatoria,
    sumar_meses,
    ultimo_dia_mes,
)
from ongs_ai.proactivo.modelo import ConvocatoriaEsperada, EstadoEsperada
from ongs_ai.proactivo.puertos import RepositorioConvocatoriasEsperadas, RepositorioHistorialConcesiones

logger = logging.getLogger(__name__)

# ADR-007 §8.4 — default aceptado por el operador, calibrable sin ADR.
MARGEN_NO_APARECIDA_MESES_DEFECTO = 2
# ADR-007 §8.1 — default aceptado: últimos 5 años (2-4 ediciones de una
# anual sin traer ruido antiguo).
ANIOS_HISTORIAL_DEFECTO = 5


@dataclass(frozen=True)
class ResumenCaptura:
    """Resultado de `capturar_y_derivar_entidad` (§3.4, §9 — usado por
    `scripts/derivar_recurrentes.py`)."""

    concesiones_encontradas: int
    concesiones_nuevas: int
    concesiones_descartadas: int
    series_detectadas: int
    esperadas_baja: int
    esperadas_media: int
    esperadas_alta: int


@dataclass(frozen=True)
class ResumenReevaluacion:
    """Resultado de `reevaluar_entidad` (§5/§9 — enganche a la pasada de
    ingesta, SIN red: re-derivación desde el historial ya persistido +
    enlace con las convocatorias recién procesadas + revisión de ventanas)."""

    esperadas_enlazadas: int
    esperadas_no_aparecidas: int
    contextos_enlace: tuple["ContextoEnlace", ...] = ()


@dataclass(frozen=True)
class ContextoEnlace:
    """Una esperada enlazada esta pasada — usado por `pasada_ingesta.py` para
    enriquecer con UNA línea de contexto el aviso de propuesta existente
    (§3.8.1), sin crear un canal nuevo ni duplicar el aviso."""

    entidad_id: str
    convocatoria_id: str
    anio_recibido_antes: int


def _upsert_esperada(
    repo_esperadas: RepositorioConvocatoriasEsperadas,
    nueva: ConvocatoriaEsperada,
    *,
    reloj: Callable[[], datetime],
) -> None:
    """Upsert por `(entidad_id, serie_fingerprint, anio_esperado)` (§3.4).
    Una esperada TERMINAL (`PUBLICADA_ENLAZADA`/`NO_APARECIDA`) nunca se
    resucita a `ESPERADA` por una re-derivación — mismo criterio que el
    reintento de un Match descartado (ADR-001 §1.4): el año siguiente es una
    esperada NUEVA, no esta reescrita."""
    existente = repo_esperadas.obtener_esperada(nueva.entidad_id, nueva.serie_fingerprint, nueva.anio_esperado)
    if existente is None:
        repo_esperadas.guardar_esperada(nueva)
        return
    if existente.estado is not EstadoEsperada.ESPERADA:
        return
    repo_esperadas.guardar_esperada(
        dataclasses.replace(
            nueva, esperada_id=existente.esperada_id, creado_en=existente.creado_en, actualizado_en=reloj()
        )
    )


def _derivar_y_persistir(
    entidad_id: str,
    repo_historial: RepositorioHistorialConcesiones,
    repo_esperadas: RepositorioConvocatoriasEsperadas,
    fecha_referencia: date,
    *,
    generador_id: Callable[[], str],
    reloj: Callable[[], datetime],
) -> list[ConvocatoriaEsperada]:
    """Deriva desde el historial YA persistido y hace upsert — compartido por
    `capturar_y_derivar_entidad` y `reevaluar_entidad`. `anio_esperado_activo_por_serie`
    ancla el año de cualquier esperada YA activa (ver nota en `derivacion.py`)
    para que una re-derivación posterior NUNCA salte a un año más nuevo
    mientras la actual siga viva — solo la refina in-place."""
    historial = repo_historial.listar_historial_por_entidad(entidad_id)
    activos = {
        e.serie_fingerprint: e.anio_esperado
        for e in repo_esperadas.listar_esperadas_por_entidad(entidad_id)
        if e.estado is EstadoEsperada.ESPERADA
    }
    esperadas = derivar_esperadas_de_entidad(
        historial,
        fecha_referencia=fecha_referencia,
        generador_id=generador_id,
        reloj=reloj,
        anio_esperado_activo_por_serie=activos,
    )
    for esperada in esperadas:
        _upsert_esperada(repo_esperadas, esperada, reloj=reloj)
    return esperadas


def capturar_y_derivar_entidad(
    entidad: Entidad,
    fuente: FuenteConcesionesBDNS,
    repo_historial: RepositorioHistorialConcesiones,
    repo_esperadas: RepositorioConvocatoriasEsperadas,
    fecha_referencia: date,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    generador_id: Callable[[], str],
    reloj: Callable[[], datetime],
) -> ResumenCaptura:
    """Captura->persistencia(dedupe)->derivación->persistencia para UNA
    entidad ya captada (ADR-007 §3.4). Usa `entidad.nif` — dato VERIFICADO
    del tenant, nunca un NIF ajeno ni inventado (§3.9). La derivación usa el
    historial COMPLETO ya persistido (no solo lo nuevo de esta captura), para
    que ediciones de pasadas anteriores sigan sustentando la serie."""
    encontradas = 0
    nuevas = 0
    for historial in fuente.buscar_por_nif(
        entidad.nif, entidad.entidad_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    ):
        encontradas += 1
        if repo_historial.obtener_historial_por_cod_concesion(entidad.entidad_id, historial.cod_concesion):
            continue
        repo_historial.guardar_historial(historial)
        nuevas += 1

    esperadas = _derivar_y_persistir(
        entidad.entidad_id, repo_historial, repo_esperadas, fecha_referencia,
        generador_id=generador_id, reloj=reloj,
    )
    conteo = {"baja": 0, "media": 0, "alta": 0}
    for esperada in esperadas:
        conteo[esperada.confianza.value] += 1

    return ResumenCaptura(
        concesiones_encontradas=encontradas,
        concesiones_nuevas=nuevas,
        concesiones_descartadas=fuente.descartados,
        series_detectadas=len(esperadas),
        esperadas_baja=conteo["baja"],
        esperadas_media=conteo["media"],
        esperadas_alta=conteo["alta"],
    )


def _enlazar_convocatorias_nuevas(
    esperadas_activas: Sequence[ConvocatoriaEsperada],
    convocatorias: Sequence[Convocatoria],
    *,
    reloj: Callable[[], datetime],
) -> list[ConvocatoriaEsperada]:
    """Al PRIMER match de serie (§3.6): compara el fingerprint de cada
    convocatoria recién procesada contra las esperadas `ESPERADA` activas de
    la entidad. Nunca crea Match — solo transiciona la esperada."""
    por_fingerprint = {e.serie_fingerprint: e for e in esperadas_activas}
    enlazadas: list[ConvocatoriaEsperada] = []
    ya_enlazadas: set[str] = set()

    for convocatoria in convocatorias:
        fingerprint = fingerprint_desde_convocatoria(convocatoria)
        esperada = por_fingerprint.get(fingerprint)
        if esperada is None or fingerprint in ya_enlazadas:
            continue
        enlazadas.append(
            dataclasses.replace(
                esperada,
                estado=EstadoEsperada.PUBLICADA_ENLAZADA,
                convocatoria_id_enlazada=convocatoria.convocatoria_id,
                actualizado_en=reloj(),
            )
        )
        ya_enlazadas.add(fingerprint)

    return enlazadas


def _marcar_no_aparecida_si_procede(
    esperada: ConvocatoriaEsperada,
    fecha_referencia: date,
    *,
    margen_meses: int,
    reloj: Callable[[], datetime],
) -> ConvocatoriaEsperada | None:
    if esperada.estado is not EstadoEsperada.ESPERADA:
        return None
    limite = sumar_meses(ultimo_dia_mes(esperada.anio_esperado, esperada.ventana_mes_fin), margen_meses)
    if fecha_referencia <= limite:
        return None
    return dataclasses.replace(esperada, estado=EstadoEsperada.NO_APARECIDA, actualizado_en=reloj())


def reevaluar_entidad(
    entidad_id: str,
    convocatorias_procesadas: Sequence[Convocatoria],
    repo_historial: RepositorioHistorialConcesiones,
    repo_esperadas: RepositorioConvocatoriasEsperadas,
    fecha_referencia: date,
    *,
    margen_no_aparecida_meses: int = MARGEN_NO_APARECIDA_MESES_DEFECTO,
    generador_id: Callable[[], str],
    reloj: Callable[[], datetime],
) -> ResumenReevaluacion:
    """§5/§9 — enganche a CADA pasada de ingesta, SIN red (re-deriva desde el
    historial YA persistido, nunca vuelve a consultar la BDNS de concesiones):
    (1) re-deriva esperadas (ventana/confianza pueden refinarse con el mismo
    historial; `anio_esperado` de una esperada ya activa NUNCA salta hacia
    adelante mientras siga viva, ver `derivacion.py`); (2) enlaza las
    esperadas `ESPERADA` con las convocatorias de ESTA pasada por fingerprint
    de serie; (3) transiciona a `NO_APARECIDA` las que superaron ventana+margen
    sin aparecer. Para UNA entidad — el llamador (`pasada_ingesta.py`) itera
    las entidades captadas y agrega los contadores, con degradación limpia
    por entidad (un fallo aquí nunca tumba la pasada completa)."""
    _derivar_y_persistir(
        entidad_id, repo_historial, repo_esperadas, fecha_referencia,
        generador_id=generador_id, reloj=reloj,
    )

    esperadas_activas = [
        e for e in repo_esperadas.listar_esperadas_por_entidad(entidad_id) if e.estado is EstadoEsperada.ESPERADA
    ]

    enlazadas = _enlazar_convocatorias_nuevas(esperadas_activas, convocatorias_procesadas, reloj=reloj)
    contextos = []
    for enlazada in enlazadas:
        repo_esperadas.guardar_esperada(enlazada)
        contextos.append(
            ContextoEnlace(
                entidad_id=entidad_id,
                convocatoria_id=enlazada.convocatoria_id_enlazada,
                anio_recibido_antes=max(enlazada.anios_observados),
            )
        )
    ids_enlazadas = {e.esperada_id for e in enlazadas}

    no_aparecidas = 0
    for esperada in esperadas_activas:
        if esperada.esperada_id in ids_enlazadas:
            continue
        actualizada = _marcar_no_aparecida_si_procede(
            esperada, fecha_referencia, margen_meses=margen_no_aparecida_meses, reloj=reloj
        )
        if actualizada is not None:
            repo_esperadas.guardar_esperada(actualizada)
            no_aparecidas += 1

    return ResumenReevaluacion(
        esperadas_enlazadas=len(enlazadas),
        esperadas_no_aparecidas=no_aparecidas,
        contextos_enlace=tuple(contextos),
    )
