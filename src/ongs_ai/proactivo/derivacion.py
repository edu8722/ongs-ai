"""Derivación determinista historial -> esperadas — ADR-007 §3.5. SIN LLM: la
IA no participa en el número ni en la fecha (regla de oro). Todo aquí es
puro/testeable; degrada SIEMPRE hacia el miss (ninguna esperada creada o
ventana equivocada), jamás hacia una esperada falsa o una fecha exacta.

**Fingerprint de serie — CALIBRACIÓN DEL ARQUITECTO** (auditoría de ADR-007,
difiere de §3.5 en DOS puntos, documentados aquí):

1. **nivel3 (consejería/dirección general) QUEDA FUERA** del fingerprint —
   decisión original de la auditoría: se renombra entre legislaturas (el
   histórico real de Aniridia lo evidencia) y produciría misses evitables si
   dos ediciones de la MISMA serie cayeran bajo un nivel3 distinto. `nivel3`
   se conserva como dato informativo en `HistorialConcesion`, nunca entra en
   el fingerprint.
2. **nivel2 TAMBIÉN queda fuera** — hallazgo de implementación (§3.6): el
   fingerprint de ENLACE se reconstruye desde una `Convocatoria` YA
   INGERIDA, y el contrato congelado NO preserva nivel2 en bruto (solo
   `region`, derivada de `regiones`/tope-por-órgano en `bdns.py`). Para
   convocatorias de ámbito NACIONAL (nivel1=ESTADO) — el propio ejemplo
   insignia del ADR, "IRPF 0,7% estatal" — `region` es SIEMPRE `None`
   (`bdns.py` nunca la rellena para nacional), así que un fingerprint que
   exigiera nivel2 NUNCA podría enlazar una serie estatal: el caso motivador
   del ADR quedaría permanentemente en miss. Incluir nivel1 (amplio:
   ESTADO/AUTONOMICA/LOCAL) + título ya normalizado es suficiente dentro del
   universo pequeño de series de UNA sola entidad (el enlace nunca compara
   contra otras entidades); el riesgo de colisión entre dos programas
   distintos de la misma entidad con título post-normalización idéntico es
   bajo y, si ocurriera, el resultado es como mucho un enlace ANTICIPADO a
   una convocatoria real (que igual pasa por el guardarraíl de F3 antes de
   cualquier Match/aviso) — nunca una esperada o un Match fabricados sobre
   algo inexistente, que es el riesgo que este ADR realmente prohíbe (§3.6).

**Tokens de año/edición eliminados del título** (§3.5: "años de 4 dígitos
20XX, ordinales romanos de edición, y números sueltos que denoten
ejercicio") — lectura CONSERVADORA de "números sueltos que denoten
ejercicio": se eliminan años de 4 dígitos y marcadores de edición
inequívocos (ordinal con sufijo "ª"/"º", o un numeral romano PEGADO a una
palabra de edición/convocatoria/ejercicio/campaña/curso). Se eliminan
deliberadamente NO los números sueltos genéricos (p. ej. "IRPF 0,7%", el
propio ejemplo real citado en el ADR §22): un número aislado sin contexto de
edición es contenido real de la convocatoria, no un marcador de ejercicio, y
eliminarlo a ciegas arriesgaría fusionar series distintas o corromper el
título — peor que el miss que la degradación conservadora busca evitar.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Mapping, Sequence

from ongs_ai.dominio.entidades import AmbitoTerritorial, Convocatoria, TipoFuente, normalizar_texto_comparacion
from ongs_ai.proactivo.modelo import Confianza, ConvocatoriaEsperada, EstadoEsperada, HistorialConcesion

# --- Tokens de año/edición (ver docstring del módulo) ---------------------

_TOKEN_ANIO = re.compile(r"\b20\d{2}\b")
_TOKEN_ORDINAL_SUFIJO = re.compile(r"\b\d{1,2}\s*[ªºo]\b", re.IGNORECASE)

_PALABRAS_EDICION = r"(?:edici[oó]n|convocatoria|ejercicio|campa[nñ]a|curso)"
_ROMANO = r"[ivxlcdmIVXLCDM]{1,7}"
_ROMANO_TRAS_PALABRA = re.compile(rf"\b{_PALABRAS_EDICION}\s+({_ROMANO})\b", re.IGNORECASE)
_ROMANO_ANTES_PALABRA = re.compile(rf"\b({_ROMANO})\s+{_PALABRAS_EDICION}\b", re.IGNORECASE)


def _quitar_tokens_anio_y_edicion(texto: str) -> str:
    texto = _TOKEN_ANIO.sub(" ", texto)
    texto = _TOKEN_ORDINAL_SUFIJO.sub(" ", texto)
    texto = _ROMANO_TRAS_PALABRA.sub(lambda m: m.group(0)[: -len(m.group(1))].rstrip(), texto)
    texto = _ROMANO_ANTES_PALABRA.sub(lambda m: m.group(0)[len(m.group(1)) :].lstrip(), texto)
    return texto


def construir_fingerprint_serie(*, organo_nivel1: str | None, titulo: str) -> str:
    """Clave estable que agrupa ediciones del mismo programa a través de los
    años (ADR-007 §3.5, CALIBRACIÓN del módulo: nivel2 y nivel3 fuera, ver
    docstring). Reutiliza `normalizar_texto_comparacion` del dominio (nunca
    se reimplementa, ADR-002)."""
    organo = normalizar_texto_comparacion(organo_nivel1 or "")
    titulo_normalizado = normalizar_texto_comparacion(_quitar_tokens_anio_y_edicion(titulo or ""))
    return f"{organo}::{titulo_normalizado}"


# --- Fingerprint de ENLACE desde una Convocatoria ya ingerida (ADR-007 §3.6) -


_NIVEL1_PROXY_DESDE_TIPO_FUENTE: dict[TipoFuente, str | None] = {
    TipoFuente.PUBLICA_NACIONAL: "ESTADO",
    TipoFuente.PUBLICA_AUTONOMICA: "AUTONOMICA",
    TipoFuente.PUBLICA_LOCAL: "LOCAL",
    TipoFuente.PRIVADA: None,
}


def fingerprint_desde_convocatoria(convocatoria: Convocatoria) -> str:
    """Fingerprint de enlace (§3.6) reconstruido a partir de lo que el
    contrato congelado SÍ preserva de una `Convocatoria` ya ingerida —
    `Convocatoria` no guarda nivel1 en bruto (sería un campo nuevo en el
    contrato, fuera de alcance de este ADR). Usa `fuente.tipo` (que ya
    deriva de nivel1 en `bdns.py`) como proxy. Es intencionadamente la MISMA
    fórmula que `construir_fingerprint_serie` (ver docstring del módulo)."""
    nivel1_proxy = _NIVEL1_PROXY_DESDE_TIPO_FUENTE.get(convocatoria.fuente.tipo)
    return construir_fingerprint_serie(organo_nivel1=nivel1_proxy, titulo=convocatoria.objeto)


# --- Congruencia territorial en el enlace (corrección del arquitecto tras la
#     auditoría de PROMPT-027 — cierra un miss disfrazado) ------------------
#
# El fingerprint de enlace (arriba) usa SOLO nivel1+título — nivel2/nivel3
# quedan fuera a propósito (ver docstring del módulo). Eso significa que dos
# series de la MISMA entidad con el mismo nivel1 y un título genérico
# idéntico ("Convocatoria de subvenciones para entidades sin ánimo de
# lucro") COLISIONAN en el mismo fingerprint aunque sean de territorios
# distintos (p. ej. dos comunidades autónomas). Como el enlace consume la
# esperada al PRIMER match (§3.6), una convocatoria de un territorio ajeno
# la enlazaría igual — dejando la edición verdadera, cuando por fin
# aparezca, SIN esperada viva que la enlace: un miss disfrazado de acierto.
#
# Arreglo: antes de aceptar un enlace por fingerprint, se exige congruencia
# territorial ENTRE el territorio de la serie (derivado de su historial) y
# el de la convocatoria candidata — pero SOLO cuando `organo_nivel2` es
# geográficamente fiable. `adapters/ingesta/bdns.py::_aplicar_tope_por_organo`
# ya documenta que eso ocurre ÚNICAMENTE cuando `nivel1 == "AUTONOMICA"`
# (ahí `region` cae a `nivel2` si `regiones` no dio nombre): para "ESTADO"
# `nivel2` es un ministerio, para "LOCAL" es el ente local — ninguno de los
# dos es territorio comparable, y tratarlos como tal rompería el caso
# insignia del ADR (la serie estatal del IRPF, cuyo `nivel2` es un
# ministerio, no una región). Fuera de AUTONOMICA el territorio de la serie
# se considera SIEMPRE desconocido -> conservador, permite el enlace.


def territorio_serie_desde_historial(historial_serie: Sequence[HistorialConcesion]) -> str | None:
    """Territorio conocido de una serie (ver nota arriba): normalizado de
    `organo_nivel2` cuando TODAS las ediciones que sustentan la serie son
    `organo_nivel1 == "AUTONOMICA"` (nivel2 geográfico, único caso fiable) y
    coinciden en el mismo valor. Cualquier otra situación -> `None`
    (desconocido, conservador: permite el enlace, nunca lo bloquea por un
    dato que no se conoce con certeza)."""
    valores = {
        normalizar_texto_comparacion(h.organo_nivel2)
        for h in historial_serie
        if h.organo_nivel1 == "AUTONOMICA" and h.organo_nivel2
    }
    if len(valores) == 1 and all(h.organo_nivel1 == "AUTONOMICA" for h in historial_serie):
        return next(iter(valores))
    return None


_TERRITORIO_NACIONAL = "nacional"


def territorio_convocatoria(convocatoria: Convocatoria) -> str | None:
    """Territorio conocido de una `Convocatoria` candidata: NACIONAL es en sí
    mismo un territorio conocido (no hay un territorio más amplio posible);
    AUTONOMICO/PROVINCIAL/LOCAL solo si `region`/`provincia` trae nombre —
    ausente -> `None` (desconocido, conservador)."""
    if convocatoria.ambito_geografico is AmbitoTerritorial.NACIONAL:
        return _TERRITORIO_NACIONAL
    nombre = convocatoria.region or convocatoria.provincia
    return normalizar_texto_comparacion(nombre) if nombre else None


def congruencia_territorial(territorio_serie: str | None, territorio_convocatoria_candidata: str | None) -> bool:
    """`True` = SE PERMITE el enlace. Si cualquiera de los dos lados
    desconoce su territorio, se permite (conservador con el dato ausente,
    ADR-007 §1); si ambos lo conocen, deben coincidir tras
    `normalizar_texto_comparacion`."""
    if territorio_serie is None or territorio_convocatoria_candidata is None:
        return True
    return territorio_serie == territorio_convocatoria_candidata


# --- Fechas: aritmética de meses sin dependencias nuevas -------------------


def ultimo_dia_mes(anio: int, mes: int) -> date:
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def sumar_meses(fecha: date, meses: int) -> date:
    mes_total = fecha.month - 1 + meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


# --- Confianza (ADR-007 §3.5) ----------------------------------------------

_ORDEN_CONFIANZA = (Confianza.ALTA, Confianza.MEDIA, Confianza.BAJA)


def _degradar_confianza(confianza: Confianza) -> Confianza:
    indice = _ORDEN_CONFIANZA.index(confianza)
    return _ORDEN_CONFIANZA[min(indice + 1, len(_ORDEN_CONFIANZA) - 1)]


def _confianza_base(n_ediciones: int, rango_meses: int) -> Confianza:
    """`rango_meses` = max(mes) - min(mes) SIN circularidad (dic/ene se trata
    como 11 meses de separación) — simplificación conservadora documentada:
    en el peor caso EMPEORA la confianza, nunca la mejora falsamente."""
    if n_ediciones == 1:
        return Confianza.BAJA
    if rango_meses > 3:
        return Confianza.BAJA
    if n_ediciones >= 3 and rango_meses <= 2:
        return Confianza.ALTA
    return Confianza.MEDIA


# --- Año esperado (ADR-007 §3.5) -------------------------------------------


def _anio_esperado(anio_ultima_edicion: int, mes_fin_ventana: int, fecha_referencia: date) -> int:
    """Determinista desde `fecha_referencia` INYECTADA (regla de oro: nunca un
    `datetime.now()` implícito) — el primer año posterior a la última
    edición observada cuya ventana aún no haya pasado."""
    anio = anio_ultima_edicion + 1
    while fecha_referencia > ultimo_dia_mes(anio, mes_fin_ventana):
        anio += 1
    return anio


# --- Agrupación de historial por serie + edición única ---------------------


@dataclass(frozen=True)
class _DatosEdicion:
    anio: int
    mes: int
    es_proxy: bool
    representante: HistorialConcesion


def _ediciones_unicas_por_convocatoria(items: Sequence[HistorialConcesion]) -> list[_DatosEdicion]:
    """Una MISMA convocatoria (edición) puede aportar más de un
    `HistorialConcesion` (varias concesiones bajo la misma llamada) — cuenta
    como UNA edición, no como N (§3.5: "ediciones previas", no "concesiones
    previas"). Se queda con el representante de fecha_concesion más
    reciente por código de convocatoria."""
    por_codigo: dict[str, HistorialConcesion] = {}
    for item in items:
        actual = por_codigo.get(item.cod_bdns_convocatoria)
        if actual is None or item.fecha_concesion > actual.fecha_concesion:
            por_codigo[item.cod_bdns_convocatoria] = item

    datos = []
    for representante in por_codigo.values():
        if representante.apertura_convocatoria is not None:
            anio, mes, es_proxy = (
                representante.apertura_convocatoria.year,
                representante.apertura_convocatoria.month,
                False,
            )
        else:
            anio, mes, es_proxy = (
                representante.fecha_concesion.year,
                representante.fecha_concesion.month,
                True,
            )
        datos.append(_DatosEdicion(anio=anio, mes=mes, es_proxy=es_proxy, representante=representante))
    return datos


def _organo_legible(historial: HistorialConcesion) -> str | None:
    partes = [p for p in (historial.organo_nivel1, historial.organo_nivel2, historial.organo_nivel3) if p]
    return " / ".join(partes) if partes else None


def _derivar_una_serie(
    serie_fingerprint: str,
    ediciones: list[_DatosEdicion],
    *,
    entidad_id: str,
    fecha_referencia: date,
    generador_id: Callable[[], str],
    reloj: Callable[[], datetime],
    anio_esperado_activo: int | None,
) -> ConvocatoriaEsperada:
    ediciones_ordenadas = sorted(ediciones, key=lambda d: (d.anio, d.mes))
    ultima = ediciones_ordenadas[-1]

    meses = [d.mes for d in ediciones]
    anios_observados = tuple(sorted(d.anio for d in ediciones))
    proxy_usado = any(d.es_proxy for d in ediciones)

    ventana_mes_inicio = min(meses)
    ventana_mes_fin = max(meses)
    rango_meses = ventana_mes_fin - ventana_mes_inicio

    confianza = _confianza_base(len(ediciones), rango_meses)
    if proxy_usado:
        confianza = _degradar_confianza(confianza)

    # Si YA hay una esperada ACTIVA (no terminal) para esta serie, su
    # anio_esperado se respeta tal cual (nunca se recalcula hacia adelante
    # mientras siga viva) — si no, se recalcula libre de raíz. Sin esto, una
    # re-derivación posterior a que la ventana original avance (§5, "tras
    # cada pasada de ingesta") saltaría a un año más nuevo cada vez que pasa
    # el tiempo, dejando huérfana la esperada activa anterior en vez de
    # refinarla in-place (ediciones/ventana/confianza) — el año siguiente
    # solo debe nacer como esperada NUEVA cuando la anterior ya es terminal
    # (enlazada o no aparecida), igual que el reintento de un Match
    # descartado es un Match nuevo (ADR-001 §1.4).
    anio_esperado = (
        anio_esperado_activo
        if anio_esperado_activo is not None
        else _anio_esperado(max(anios_observados), ventana_mes_fin, fecha_referencia)
    )
    accionable = not any(d.representante.es_concesion_directa for d in ediciones)

    ahora = reloj()
    return ConvocatoriaEsperada(
        esperada_id=generador_id(),
        entidad_id=entidad_id,
        serie_fingerprint=serie_fingerprint,
        titulo_representativo=ultima.representante.titulo_convocatoria,
        organo=_organo_legible(ultima.representante),
        ediciones_previas=len(ediciones),
        anios_observados=anios_observados,
        ventana_mes_inicio=ventana_mes_inicio,
        ventana_mes_fin=ventana_mes_fin,
        anio_esperado=anio_esperado,
        confianza=confianza,
        accionable=accionable,
        estado=EstadoEsperada.ESPERADA,
        convocatoria_id_enlazada=None,
        creado_en=ahora,
        actualizado_en=ahora,
    )


def derivar_esperadas_de_entidad(
    historial: Sequence[HistorialConcesion],
    *,
    fecha_referencia: date,
    generador_id: Callable[[], str],
    reloj: Callable[[], datetime],
    anio_esperado_activo_por_serie: Mapping[str, int] | None = None,
) -> list[ConvocatoriaEsperada]:
    """Historial completo de UNA entidad -> una `ConvocatoriaEsperada` por
    serie detectada (ADR-007 §3.5). Determinista: mismo historial (y mismo
    `anio_esperado_activo_por_serie`) siempre produce las mismas esperadas
    (salvo `esperada_id`/`creado_en`/`actualizado_en`, inyectados). Series
    que no agrupan (fingerprints distintos) simplemente producen esperadas
    de 1 edición cada una — NUNCA una esperada fusionada falsa.

    `anio_esperado_activo_por_serie` (opcional): `serie_fingerprint ->
    anio_esperado` de la esperada YA ACTIVA (estado `ESPERADA`) de esa serie
    en el almacén, si la hay — ver nota en `_derivar_una_serie` sobre por qué
    esto es necesario para una re-derivación correcta."""
    por_serie: dict[str, list[HistorialConcesion]] = {}
    for item in historial:
        por_serie.setdefault(item.serie_fingerprint, []).append(item)

    activos = anio_esperado_activo_por_serie or {}
    esperadas = []
    for serie_fingerprint, items in por_serie.items():
        entidad_id = items[0].entidad_id
        ediciones = _ediciones_unicas_por_convocatoria(items)
        esperadas.append(
            _derivar_una_serie(
                serie_fingerprint,
                ediciones,
                entidad_id=entidad_id,
                fecha_referencia=fecha_referencia,
                generador_id=generador_id,
                reloj=reloj,
                anio_esperado_activo=activos.get(serie_fingerprint),
            )
        )
    return esperadas
