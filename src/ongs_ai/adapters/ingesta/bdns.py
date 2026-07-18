"""FuenteBDNS — adapter de ingesta contra la API pública de la BDNS (F2, ADR-001).

Mapeo DETERMINISTA (sin IA: la API de la BDNS ya da datos estructurados) de la
respuesta de detalle (`/bdnstrans/api/convocatorias?numConv=<códigoBDNS>`) al
contrato `Convocatoria`. Decisiones documentadas (verificadas contra la API
real en 2026-07-18, ver `investigacion/R1_informe.md`):

- `tipo` (TipoFuente) se deriva de `organo.nivel1`: ESTADO -> publica_nacional,
  AUTONOMICA -> publica_autonomica, LOCAL -> publica_local; cualquier otro
  valor observado en la API (p. ej. "OTROS" — universidades, entes sin encaje
  claro en la jerarquía) usa el valor más conservador, `publica_local` (el
  ámbito más restrictivo, para no sobre-prometer una convocatoria nacional a
  una entidad fuera de su alcance real).
- `ambito_geografico` + `region` se derivan de `regiones`: una única región
  con código que empieza por "ES" y no es exactamente "ES" -> autonomico, con
  `region` = el nombre tras el guion ("ES51 - CATALUÑA" -> "CATALUÑA"); cero
  regiones, más de una, o código no-"ES" (p. ej. "ES - ESPAÑA",
  "XXXX - TODO EL MUNDO") -> nacional, sin `region`. Simplificación conocida y
  deliberada: la BDNS mezcla códigos NUTS2 (autonómico) y NUTS3 (provincial,
  p. ej. "ES616 - Jaén" en una convocatoria LOCAL de una diputación) bajo el
  mismo campo `regiones`, sin que la API distinga el nivel de forma fiable
  desde este único campo — este adapter no intenta desambiguar y siempre usa
  `autonomico` cuando hay una única región con código "ES*"; afinar el nivel
  provincial queda anotado como candidato a ADR futuro si el matching
  provincial de F3 lo necesita en la práctica (nota ya existente en
  `dominio/elegibilidad.py` sobre el mismo hueco para `local`/`municipio`).
- `presupuestoTotal` (euros, puede llegar como float) -> se convierte a
  `cuantias.importe_maximo_centimos` en céntimos enteros con redondeo
  determinista vía `Decimal` (regla de oro: dinero nunca float hacia el
  dominio).
- `objeto` combina `descripcion` (título específico de la convocatoria) y
  `descripcionFinalidad` (categoría) cuando ambos existen — el prompt pide
  mapear ambos campos y ninguno por separado captura el dato completo.
- `requisitos_elegibilidad` solo lleva lo derivable determinista (el ámbito ya
  calculado, replicado en `ambito_territorial_requerido`); forma jurídica,
  antigüedad, requisitos formales y exclusiones quedan vacíos para la futura
  capa de extracción IA.
- Fallos de transporte degradan limpio (nunca lanzan hacia el dominio): si
  falla la petición de búsqueda paginada, se registra y se corta ahí
  (se devuelve lo ya obtenido); si falla el detalle de una convocatoria
  concreta (transporte o mapeo), se registra, se salta esa convocatoria y se
  sigue con las demás de la página.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Iterator

from ongs_ai.adapters.ingesta.base import FiltrosBusqueda, TransporteHTTP
from ongs_ai.dominio.entidades import (
    AmbitoTerritorial,
    Convocatoria,
    Cuantias,
    EstadoIngesta,
    Fuente,
    Plazos,
    RequisitosElegibilidad,
    TipoFuente,
)
from ongs_ai.dominio.ingesta_estado import promocionar_si_completa

logger = logging.getLogger(__name__)

URL_BASE_BDNS = "https://www.infosubvenciones.es/bdnstrans/api"
URL_BUSQUEDA_BDNS = f"{URL_BASE_BDNS}/convocatorias/busqueda"
URL_DETALLE_BDNS = f"{URL_BASE_BDNS}/convocatorias"

_MAPA_NIVEL1_TIPO_FUENTE: dict[str, TipoFuente] = {
    "ESTADO": TipoFuente.PUBLICA_NACIONAL,
    "AUTONOMICA": TipoFuente.PUBLICA_AUTONOMICA,
    "LOCAL": TipoFuente.PUBLICA_LOCAL,
}


def _url_origen_bdns(codigo_bdns: str) -> str:
    """Clave natural de dedupe (ADR-001 §6.5): URL de detalle con el código BDNS."""
    return f"{URL_DETALLE_BDNS}?numConv={codigo_bdns}"


def _tipo_fuente_desde_nivel1(nivel1: str | None) -> TipoFuente:
    return _MAPA_NIVEL1_TIPO_FUENTE.get(nivel1 or "", TipoFuente.PUBLICA_LOCAL)


def _ambito_y_region_desde_regiones(regiones: list[dict]) -> tuple[AmbitoTerritorial, str | None]:
    descripciones = [
        (r.get("descripcion") or "").strip() for r in (regiones or []) if r.get("descripcion")
    ]
    if len(descripciones) != 1:
        return AmbitoTerritorial.NACIONAL, None
    codigo, _, nombre = descripciones[0].partition(" - ")
    codigo = codigo.strip()
    nombre = nombre.strip()
    if not nombre or not codigo.startswith("ES") or codigo == "ES":
        return AmbitoTerritorial.NACIONAL, None
    return AmbitoTerritorial.AUTONOMICO, nombre


def _beneficiarios_desde_lista(tipos_beneficiarios: list[dict]) -> str:
    descripciones = [
        (t.get("descripcion") or "").strip() for t in (tipos_beneficiarios or []) if t.get("descripcion")
    ]
    return "; ".join(descripciones)


def _euros_a_centimos(valor: float | int | None) -> int | None:
    if valor is None:
        return None
    return int(Decimal(str(valor)).scaleb(2).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _fecha_desde_iso(valor: str | None) -> date | None:
    if not valor:
        return None
    return date.fromisoformat(valor)


def _objeto_desde_detalle(detalle: dict) -> str:
    descripcion = (detalle.get("descripcion") or "").strip()
    finalidad = (detalle.get("descripcionFinalidad") or "").strip()
    if finalidad and descripcion:
        return f"{descripcion} (Finalidad: {finalidad})"
    return finalidad or descripcion


def _mapear_convocatoria(detalle: dict, *, ahora: datetime) -> Convocatoria:
    organo = detalle.get("organo") or {}
    codigo_bdns = str(detalle["codigoBDNS"])
    ambito_geografico, region = _ambito_y_region_desde_regiones(detalle.get("regiones") or [])

    convocatoria = Convocatoria(
        convocatoria_id=f"bdns-{codigo_bdns}",
        fuente=Fuente(
            portal="BDNS",
            url_origen=_url_origen_bdns(codigo_bdns),
            tipo=_tipo_fuente_desde_nivel1(organo.get("nivel1")),
        ),
        objeto=_objeto_desde_detalle(detalle),
        beneficiarios_elegibles=_beneficiarios_desde_lista(detalle.get("tiposBeneficiarios") or []),
        requisitos_elegibilidad=RequisitosElegibilidad(
            ambito_territorial_requerido=ambito_geografico,
        ),
        ambito_geografico=ambito_geografico,
        plazos=Plazos(
            fecha_apertura=_fecha_desde_iso(detalle.get("fechaInicioSolicitud")),
            fecha_cierre=_fecha_desde_iso(detalle.get("fechaFinSolicitud")),
        ),
        cuantias=Cuantias(importe_maximo_centimos=_euros_a_centimos(detalle.get("presupuestoTotal"))),
        estado_ingesta=EstadoIngesta.EXTRAIDA,
        creado_en=ahora,
        actualizado_en=ahora,
        documento_origen_ref=detalle.get("urlBasesReguladoras"),
        region=region,
    )
    return promocionar_si_completa(convocatoria)


def _params_busqueda(filtros: FiltrosBusqueda, *, page: int, page_size: int) -> dict[str, object]:
    params: dict[str, object] = {"page": page, "pageSize": page_size}
    if filtros.descripcion:
        params["descripcion"] = filtros.descripcion
    if filtros.fecha_desde:
        params["fechaDesde"] = filtros.fecha_desde.strftime("%d/%m/%Y")
    if filtros.fecha_hasta:
        params["fechaHasta"] = filtros.fecha_hasta.strftime("%d/%m/%Y")
    if filtros.tipo_beneficiario:
        # Nombre de parámetro no verificado contra el Swagger real (no accesible
        # en esta sesión, ver resumen final); si la API no lo reconoce, Spring
        # ignora el parámetro desconocido y simplemente no filtra — degrada limpio.
        params["tipoBeneficiario"] = filtros.tipo_beneficiario
    return params


class FuenteBDNS:
    """`FuenteConvocatorias` contra la API pública de la BDNS (busqueda paginada +
    detalle por convocatoria)."""

    def __init__(
        self,
        transporte: TransporteHTTP,
        *,
        reloj: Callable[[], datetime],
        page_size: int = 50,
    ) -> None:
        self._transporte = transporte
        self._reloj = reloj
        self._page_size = page_size

    def buscar(self, filtros: FiltrosBusqueda | None = None) -> Iterator[Convocatoria]:
        filtros = filtros or FiltrosBusqueda()
        page = 0
        while True:
            params = _params_busqueda(filtros, page=page, page_size=self._page_size)
            try:
                respuesta = self._transporte.obtener_json(URL_BUSQUEDA_BDNS, params)
            except Exception as exc:  # transporte que falla: degrada limpio, no propaga
                logger.warning("Fallo de transporte en búsqueda BDNS (page=%s): %s", page, exc)
                return

            contenido = respuesta.get("content") or []
            for item in contenido:
                num_conv = item.get("numeroConvocatoria")
                if not num_conv:
                    continue
                try:
                    detalle = self._transporte.obtener_json(URL_DETALLE_BDNS, {"numConv": num_conv})
                    convocatoria = _mapear_convocatoria(detalle, ahora=self._reloj())
                except Exception as exc:  # una convocatoria feo/caída no tumba las demás
                    logger.warning(
                        "Fallo de transporte/mapeo en detalle BDNS numConv=%s: %s", num_conv, exc
                    )
                    continue
                yield convocatoria

            if respuesta.get("last", True):
                return
            page += 1
