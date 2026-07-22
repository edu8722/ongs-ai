"""Read model de "Tus ayudas recurrentes" en el panel del tenant — bloque B
del prompt del arquitecto tras ADR-007 (2026-07-22, petición original del
operador). Solo lectura, SIEMPRE por `entidad_id` (aislamiento por tenant,
mismo criterio que `servicios/panel.py`). Traduce los datos honestos del
proactivo (`HistorialConcesion`/`ConvocatoriaEsperada`, ventana en meses,
confianza explícita, ciclo de estados propio) a lenguaje natural para
mostrar a la entidad — sin inventar fechas ni sugerir presentarse a
convocatorias nominativas (ADR-007 §3.5/§3.7).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ongs_ai.dominio.matching_estado import Match
from ongs_ai.proactivo.derivacion import ultimo_dia_mes
from ongs_ai.proactivo.modelo import Confianza, ConvocatoriaEsperada, EstadoEsperada, HistorialConcesion

_MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

ETIQUETA_UNA_EDICION = "una sola edición previa — sin patrón confirmado"
ETIQUETA_IRREGULAR = "irregular"
ETIQUETA_NOMINATIVA = "adjudicación directa — no se solicita en concurrencia"
MENSAJE_PUBLICADA = "¡ya está abierta!"
MENSAJE_NO_APARECIDA = "no ha aparecido en su ventana habitual — conviene revisarla manualmente"
BADGE_PENDIENTE_DE_PUBLICAR = "PENDIENTE DE PUBLICAR"
MENSAJE_SIN_HISTORIAL = "Aún no hay historial capturado."


def ventana_en_lenguaje_natural(mes_inicio: int, mes_fin: int) -> str:
    """Nunca una fecha exacta (ADR-007 §3.5): "en torno a <mes>" si todas las
    ediciones cayeron en el mismo mes, o el rango "<mes>–<mes>" en otro caso."""
    if mes_inicio == mes_fin:
        return f"en torno a {_MESES_ES[mes_inicio]}"
    return f"{_MESES_ES[mes_inicio]}–{_MESES_ES[mes_fin]}"


def etiqueta_honesta(esperada: ConvocatoriaEsperada) -> str | None:
    """Etiquetas honestas de ADR-007 §3.5 — nunca sugieren un patrón que los
    datos no respaldan. `None` si la esperada tiene ≥2 ediciones en meses
    agrupados (confianza MEDIA/ALTA "normal", sin matiz que añadir)."""
    if esperada.ediciones_previas == 1:
        return ETIQUETA_UNA_EDICION
    if esperada.ventana_mes_fin - esperada.ventana_mes_inicio > 3:
        return ETIQUETA_IRREGULAR
    return None


def _dentro_de_ventana(esperada: ConvocatoriaEsperada, fecha_referencia: date) -> bool:
    inicio = date(esperada.anio_esperado, esperada.ventana_mes_inicio, 1)
    fin = ultimo_dia_mes(esperada.anio_esperado, esperada.ventana_mes_fin)
    return inicio <= fecha_referencia <= fin


@dataclass(frozen=True)
class ItemHistorial:
    anio: int
    titulo: str
    organo: str | None
    importe_centimos: int | None


@dataclass(frozen=True)
class ItemEsperada:
    esperada: ConvocatoriaEsperada
    ventana_texto: str
    etiqueta: str | None
    es_nominativa: bool
    tiene_match_enlazado: bool
    convocatoria_titulo: str | None


@dataclass(frozen=True)
class ResumenRecurrentes:
    historial: tuple[ItemHistorial, ...]
    esperadas_vivas: tuple[ItemEsperada, ...]
    publicadas: tuple[ItemEsperada, ...]
    no_aparecidas: tuple[ItemEsperada, ...]
    aviso_ventana_proxima: tuple[ItemEsperada, ...]


def _organo_legible(historial: HistorialConcesion) -> str | None:
    partes = [p for p in (historial.organo_nivel1, historial.organo_nivel2, historial.organo_nivel3) if p]
    return " / ".join(partes) if partes else None


def resumen_recurrentes(entidad_id: str, almacen, fecha_referencia: date) -> ResumenRecurrentes:
    """`almacen` implementa `RepositorioHistorialConcesiones` +
    `RepositorioConvocatoriasEsperadas` + `RepositorioMatches` +
    `RepositorioConvocatorias` (mismo almacén físico que compone todos los
    puertos, ADR-007 §3.1) — mismo patrón que `resumen_panel`."""
    historial = sorted(
        almacen.listar_historial_por_entidad(entidad_id),
        key=lambda h: h.fecha_concesion, reverse=True,
    )
    items_historial = tuple(
        ItemHistorial(
            anio=h.fecha_concesion.year, titulo=h.titulo_convocatoria,
            organo=_organo_legible(h), importe_centimos=h.importe_centimos,
        )
        for h in historial
    )

    esperadas = almacen.listar_esperadas_por_entidad(entidad_id)
    matches_por_convocatoria: dict[str, Match] = {
        m.convocatoria_id: m for m in almacen.listar_matches_por_entidad(entidad_id)
    }

    def _item(esperada: ConvocatoriaEsperada) -> ItemEsperada:
        conv = (
            almacen.obtener_convocatoria(esperada.convocatoria_id_enlazada)
            if esperada.convocatoria_id_enlazada
            else None
        )
        return ItemEsperada(
            esperada=esperada,
            ventana_texto=ventana_en_lenguaje_natural(esperada.ventana_mes_inicio, esperada.ventana_mes_fin),
            etiqueta=etiqueta_honesta(esperada),
            es_nominativa=not esperada.accionable,
            tiene_match_enlazado=(
                esperada.convocatoria_id_enlazada in matches_por_convocatoria
                if esperada.convocatoria_id_enlazada
                else False
            ),
            convocatoria_titulo=conv.objeto if conv else None,
        )

    vivas = tuple(_item(e) for e in esperadas if e.estado is EstadoEsperada.ESPERADA)
    publicadas = tuple(_item(e) for e in esperadas if e.estado is EstadoEsperada.PUBLICADA_ENLAZADA)
    no_aparecidas = tuple(_item(e) for e in esperadas if e.estado is EstadoEsperada.NO_APARECIDA)

    aviso_ventana_proxima = tuple(
        _item(e)
        for e in esperadas
        if e.estado is EstadoEsperada.ESPERADA
        and e.accionable
        and e.confianza in (Confianza.MEDIA, Confianza.ALTA)
        and _dentro_de_ventana(e, fecha_referencia)
    )

    return ResumenRecurrentes(
        historial=items_historial,
        esperadas_vivas=vivas,
        publicadas=publicadas,
        no_aparecidas=no_aparecidas,
        aviso_ventana_proxima=aviso_ventana_proxima,
    )
