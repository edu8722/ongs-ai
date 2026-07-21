"""Modelos derivados del historial de concesiones — ADR-007 §3.1-§3.3.

`HistorialConcesion` (hecho, inmutable) y `ConvocatoriaEsperada` (estimación,
ciclo de estados propio) viven FUERA del contrato congelado (Entidad/
Convocatoria/Actividad/Match, ADR-001/ADR-002): son datos derivados y
calibrables (algoritmo de ventana, niveles de confianza), no las cuatro
entidades núcleo — congelarlos obligaría a un ADR nuevo por cada ajuste del
algoritmo (ADR-007 §3.1). Ninguna esperada crea Match (§3.6); `accionable`
es False para series de concesión directa/nominativa (§3.7). Dinero SIEMPRE
en céntimos int (regla de oro CLAUDE.md), nunca float.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class EstadoEsperada(str, Enum):
    """Ciclo de estados propio de una esperada (ADR-007 §3.3) — independiente
    de la máquina de estados de `Match` (`dominio/matching_estado.py`), no la
    toca. `ESPERADA` es el único estado vivo; los dos terminales cierran el
    ciclo de esa edición-año (la edición del año siguiente es una esperada
    NUEVA, nunca se "resucita" una terminal — mismo criterio que el
    reintento de un Match descartado, ADR-001 §1.4)."""

    ESPERADA = "esperada"
    PUBLICADA_ENLAZADA = "publicada_enlazada"
    NO_APARECIDA = "no_aparecida"


class Confianza(str, Enum):
    """Confianza explícita de la estimación de ventana (ADR-007 §3.5) — nunca
    una fecha exacta, siempre un rango/mes con su honestidad declarada."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


@dataclass(frozen=True)
class HistorialConcesion:
    """Una ayuda pasada de una entidad — HECHO, no estimación (ADR-007 §3.2).
    Mapeada 1:1 desde un registro de `/concesiones/busqueda` de la BDNS."""

    historial_id: str
    entidad_id: str  # FK a Entidad — aislamiento por tenant (ADR-007 §3.9)
    cod_concesion: str  # `codConcesion` BDNS — dedupe natural de la concesión
    nif_beneficiario: str  # parseado del prefijo de `beneficiario`
    fecha_concesion: date
    importe_centimos: int | None  # euros->céntimos (Decimal); None si ausente
    cod_bdns_convocatoria: str  # `numeroConvocatoria` (= `codigoBDNS` de la edición)
    titulo_convocatoria: str  # `convocatoria` — título de ESA edición
    organo_nivel1: str | None
    organo_nivel2: str | None
    organo_nivel3: str | None  # informativo — FUERA del fingerprint (ver derivacion.py)
    es_concesion_directa: bool  # True si la convocatoria de origen era no-concurrencia
    serie_fingerprint: str  # clave determinista de agrupación (§3.5), calculada, no de la BDNS
    apertura_convocatoria: date | None
    """Fecha de apertura de ESTA edición histórica (`fechaInicioSolicitud` del
    detalle de su convocatoria) — NO es un campo de la tabla del ADR-007 §3.2,
    es una decisión de implementación documentada aquí a propósito: capturarla
    una vez en la ingesta del historial evita que la re-derivación periódica
    (§5/§9, "tras cada pasada de ingesta") necesite red para recalcular la
    ventana cada vez, y evita que una apertura ya conocida se pierda/degrade
    entre pasadas. `None` si el detalle no la traía — `derivacion.py` usa
    entonces el mes de `fecha_concesion` como proxy tosco, marcado (baja la
    confianza), nunca presentado como fecha de apertura real. Justificado por
    ADR-007 §3.1: el modelo es derivado/calibrable, no el contrato congelado.
    """
    capturado_en: datetime


@dataclass(frozen=True)
class ConvocatoriaEsperada:
    """Edición anual prevista — ESTIMACIÓN honesta derivada de un grupo de
    `HistorialConcesion` de la misma serie (ADR-007 §3.3). Ventana en meses,
    JAMÁS fecha exacta; confianza explícita."""

    esperada_id: str
    entidad_id: str  # por entidad, NO global (ADR-007 §3.9)
    serie_fingerprint: str
    titulo_representativo: str  # título de la última edición observada
    organo: str | None
    ediciones_previas: int  # nº de ediciones históricas que la sustentan (>= 1)
    anios_observados: tuple[int, ...]
    ventana_mes_inicio: int  # 1-12
    ventana_mes_fin: int  # 1-12; == inicio si todas las ediciones caen en el mismo mes
    anio_esperado: int
    confianza: Confianza
    accionable: bool  # False si la serie es de concesión directa (§3.7)
    estado: EstadoEsperada
    convocatoria_id_enlazada: str | None
    creado_en: datetime
    actualizado_en: datetime
