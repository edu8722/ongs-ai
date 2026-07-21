"""FuenteConcesionesBDNS — adapter de ingesta del historial de concesiones
contra `/concesiones/busqueda` de la BDNS (ADR-007 §2, §3.2, §3.4).

Mapeo DETERMINISTA de un registro de concesión a `HistorialConcesion`, análogo
a `adapters/ingesta/bdns.py::mapear_convocatoria`; mismo `TransporteHTTP`
inyectable, misma paginación, misma degradación limpia de transporte (un fallo
se registra y se corta/salta, nunca propaga al dominio).

`nifCif` filtra server-side (verificado en vivo, ADR-007 §2.3) — es el filtro
usado, nunca "traer todo y filtrar en cliente" (28M de registros, inviable).
`fechaDesde`/`fechaHasta` (`dd/mm/yyyy`, igual formato que `bdns.py`) acotan la
ventana temporal del historial.

Cada registro de concesión trae ya `nivel1`/`nivel2`/`nivel3` y el título de
ESA edición (`convocatoria`) — suficiente para el fingerprint de serie (§3.5)
SIN una petición adicional. Pero `es_concesion_directa` (§3.7) y la fecha de
APERTURA de esa edición (§3.5 — no `fechaConcesion`, que es posterior) solo
están en el DETALLE de la convocatoria (`/convocatorias?numConv=<cod>`, la
misma URL que ya consulta `bdns.py`): se reutiliza esa fuente de verdad
(`MOTIVO_CONCESION_DIRECTA`/`_motivos_descarte_dominio` de `bdns.py`, nunca
reimplementada) con una petición de detalle POR CONVOCATORIA distinta
encontrada en la página (cacheada dentro de una misma llamada a
`buscar_por_nif`, por si dos concesiones comparten convocatoria).

Degradación:
- registro sin `beneficiario` parseable, sin `numeroConvocatoria`, sin
  `codConcesion` o sin `fechaConcesion` -> se descarta y se cuenta
  (`self.descartados`), nunca se inventa.
- fallo de transporte en la búsqueda paginada -> se registra y se corta ahí
  (se devuelve lo ya obtenido).
- fallo de transporte en el DETALLE de una convocatoria histórica concreta ->
  se registra, `es_concesion_directa` cae a `False` (conservador: ausente ->
  concurrencia, igual que en `bdns.py` §3.7) y la apertura queda `None`
  (`derivacion.py` usará el proxy de `fecha_concesion`, marcado) — la
  concesión en sí NO se descarta por esto.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Iterator

from ongs_ai.adapters.ingesta.bdns import (
    MOTIVO_CONCESION_DIRECTA,
    URL_DETALLE_BDNS,
    _motivos_descarte_dominio,
)
from ongs_ai.adapters.ingesta.base import TransporteHTTP
from ongs_ai.proactivo.derivacion import construir_fingerprint_serie
from ongs_ai.proactivo.modelo import HistorialConcesion

logger = logging.getLogger(__name__)

URL_BASE_BDNS = "https://www.infosubvenciones.es/bdnstrans/api"
URL_CONCESIONES_BDNS = f"{URL_BASE_BDNS}/concesiones/busqueda"


def _euros_a_centimos(valor: float | int | None) -> int | None:
    if valor is None:
        return None
    return int(Decimal(str(valor)).scaleb(2).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _fecha_desde_iso(valor: str | None) -> date | None:
    if not valor:
        return None
    return date.fromisoformat(valor)


def _parsear_beneficiario(beneficiario: str | None) -> tuple[str, str] | None:
    """`"P0704500H AJUNTAMENT DE PUIGPUNYENT"` -> (nif, nombre) — el NIF es el
    primer token (ADR-007 §2.1). Sin NIF parseable -> None (descarta, cuenta)."""
    if not beneficiario:
        return None
    partes = beneficiario.strip().split(" ", 1)
    if len(partes) < 2 or not partes[0]:
        return None
    return partes[0], partes[1].strip()


def _es_concesion_directa_desde_detalle(detalle: dict | None) -> bool:
    """Ausente o fallo de transporte -> conservador: se asume concurrencia
    (accionable), nunca al revés (mismo criterio que `bdns.py` §3.7)."""
    if detalle is None:
        return False
    return MOTIVO_CONCESION_DIRECTA in _motivos_descarte_dominio(detalle)


def _apertura_desde_detalle(detalle: dict | None) -> date | None:
    if detalle is None:
        return None
    return _fecha_desde_iso(detalle.get("fechaInicioSolicitud"))


def _params_busqueda(
    nif: str, *, fecha_desde: date | None, fecha_hasta: date | None, page: int, page_size: int
) -> dict[str, object]:
    params: dict[str, object] = {"page": page, "pageSize": page_size, "nifCif": nif}
    if fecha_desde:
        params["fechaDesde"] = fecha_desde.strftime("%d/%m/%Y")
    if fecha_hasta:
        params["fechaHasta"] = fecha_hasta.strftime("%d/%m/%Y")
    return params


class FuenteConcesionesBDNS:
    """`buscar_por_nif` -> `Iterator[HistorialConcesion]`. Tras agotar el
    iterador quedan disponibles `self.descartados` (concesiones sin forma
    reconocible) y `self.aperturas` (`cod_bdns_convocatoria -> fecha_apertura
    | None`, útil para diagnóstico/tests; `HistorialConcesion.
    apertura_convocatoria` ya la lleva incorporada)."""

    def __init__(
        self,
        transporte: TransporteHTTP,
        *,
        reloj: Callable[[], datetime],
        generador_id: Callable[[], str],
        page_size: int = 50,
    ) -> None:
        self._transporte = transporte
        self._reloj = reloj
        self._generador_id = generador_id
        self._page_size = page_size
        self.descartados = 0
        self.aperturas: dict[str, date | None] = {}

    def _obtener_detalle(self, cod_convocatoria: str, cache: dict[str, dict | None]) -> dict | None:
        if cod_convocatoria in cache:
            return cache[cod_convocatoria]
        try:
            detalle = self._transporte.obtener_json(URL_DETALLE_BDNS, {"numConv": cod_convocatoria})
        except Exception as exc:  # degrada limpio (CLAUDE.md) — nunca propaga
            logger.warning(
                "Fallo de transporte en detalle de convocatoria histórica numConv=%s: %s",
                cod_convocatoria,
                exc,
            )
            detalle = None
        cache[cod_convocatoria] = detalle
        return detalle

    def _mapear(
        self, item: dict, entidad_id: str, cache: dict[str, dict | None], *, ahora: datetime
    ) -> HistorialConcesion | None:
        parsed = _parsear_beneficiario(item.get("beneficiario"))
        cod_concesion = item.get("codConcesion")
        cod_convocatoria = item.get("numeroConvocatoria")
        fecha_concesion = _fecha_desde_iso(item.get("fechaConcesion"))
        if parsed is None or not cod_concesion or not cod_convocatoria or fecha_concesion is None:
            return None
        nif_beneficiario, _nombre = parsed
        cod_convocatoria = str(cod_convocatoria)

        detalle = self._obtener_detalle(cod_convocatoria, cache)
        apertura = _apertura_desde_detalle(detalle)
        self.aperturas[cod_convocatoria] = apertura

        titulo = (item.get("convocatoria") or "").strip()
        fingerprint = construir_fingerprint_serie(organo_nivel1=item.get("nivel1"), titulo=titulo)

        return HistorialConcesion(
            historial_id=self._generador_id(),
            entidad_id=entidad_id,
            cod_concesion=str(cod_concesion),
            nif_beneficiario=nif_beneficiario,
            fecha_concesion=fecha_concesion,
            importe_centimos=_euros_a_centimos(item.get("importe")),
            cod_bdns_convocatoria=cod_convocatoria,
            titulo_convocatoria=titulo,
            organo_nivel1=item.get("nivel1"),
            organo_nivel2=item.get("nivel2"),
            organo_nivel3=item.get("nivel3"),
            es_concesion_directa=_es_concesion_directa_desde_detalle(detalle),
            serie_fingerprint=fingerprint,
            apertura_convocatoria=apertura,
            capturado_en=ahora,
        )

    def buscar_por_nif(
        self,
        nif: str,
        entidad_id: str,
        *,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> Iterator[HistorialConcesion]:
        cache_detalles: dict[str, dict | None] = {}
        page = 0
        while True:
            params = _params_busqueda(
                nif, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, page=page, page_size=self._page_size
            )
            try:
                respuesta = self._transporte.obtener_json(URL_CONCESIONES_BDNS, params)
            except Exception as exc:  # degrada limpio: se corta, se devuelve lo ya obtenido
                logger.warning("Fallo de transporte en búsqueda de concesiones (page=%s): %s", page, exc)
                return

            contenido = respuesta.get("content") or []
            for item in contenido:
                historial = self._mapear(item, entidad_id, cache_detalles, ahora=self._reloj())
                if historial is None:
                    self.descartados += 1
                    continue
                yield historial

            if respuesta.get("last", True):
                return
            page += 1
