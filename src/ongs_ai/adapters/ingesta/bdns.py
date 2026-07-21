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
- `ambito_geografico` + `region`/`provincia` se derivan de `regiones` a partir
  del código NUTS que precede a " - " en la descripción de la ÚNICA región
  (cuando hay exactamente una): parte numérica vacía tras "ES" (código == "ES")
  -> nacional; exactamente 1 dígito (NUTS1) cuyo nombre coincida (normalizado,
  `normalizar_texto_comparacion` del dominio) con una CCAA de la tabla cerrada
  `_NOMBRES_CCAA_NUTS1` -> autonomico con esa `region` (caso real verificado
  numConv=920435: "ES7 - CANARIAS" -> autonomico/"CANARIAS"; el mismo dígito
  sin nombre de CCAA reconocible sigue cayendo a nacional); exactamente 2
  dígitos (NUTS2, CCAA) -> autonomico, con `region` = el nombre tras el guion
  ("ES51 - CATALUÑA" -> "CATALUÑA"); exactamente 3 dígitos (NUTS3, provincia)
  -> provincial, con `provincia` = el nombre tras el guion ("ES616 - Jaén" ->
  "Jaén"); cualquier otra cosa (código que no empieza por "ES", parte no
  numérica, u otro número de dígitos) -> nacional, sin `region` ni
  `provincia`. Cero regiones o más de una -> nacional. Derivar la CCAA a
  partir de un código NUTS3 (tabla NUTS3->NUTS2) queda fuera de alcance de
  este adapter — candidato a ADR futuro si el matching provincial de F3 lo
  necesita en la práctica (nota ya existente en `dominio/elegibilidad.py`
  sobre el mismo hueco para `local`/`municipio`).
- TOPE POR ÓRGANO (`_aplicar_tope_por_organo`, invariante nuevo tras el
  hallazgo numConv=920435 — el ámbito derivado de `regiones` JAMÁS puede ser
  más amplio que el órgano convocante): `organo.nivel1 == "AUTONOMICA"` ->
  ámbito como mucho autonomico (si `regiones` no dio nombre, `region` cae a
  `organo.nivel2` cuando existe); `organo.nivel1 == "LOCAL"` -> ámbito como
  mucho provincial (sin nombre de respaldo — `organo.nivel2` en LOCAL es el
  ente local, no una provincia; conservador con el dato ausente). Con
  `"ESTADO"` (o cualquier otro valor, p. ej. "OTROS") se mantiene el ámbito ya
  derivado. Se aplica SIEMPRE después del parseo de `regiones`, incluidas las
  convocatorias descartadas por dominio (B).
- `presupuestoTotal` (euros, puede llegar como float) -> se convierte a
  `cuantias.importe_maximo_centimos` en céntimos enteros con redondeo
  determinista vía `Decimal` (regla de oro: dinero nunca float hacia el
  dominio).
- `objeto` combina `descripcion` (título específico de la convocatoria) y
  `descripcionFinalidad` (categoría) cuando ambos existen — el prompt pide
  mapear ambos campos y ninguno por separado captura el dato completo.
- `requisitos_elegibilidad` lleva el ámbito ya calculado (replicado en
  `ambito_territorial_requerido`, YA con el tope por órgano aplicado — nunca
  puede contradecir a `ambito_geografico`) y, si la convocatoria se descarta
  por dominio (ver abajo), los motivos en `exclusiones`; forma jurídica,
  antigüedad y requisitos formales quedan vacíos para la futura capa de
  extracción IA.
- DESCARTE POR DOMINIO (`_motivos_descarte_dominio`, campos REALES del
  detalle BDNS, verificados contra numConv=920435 — ver
  `tests/fixtures/ingesta/bdns_detalle_920435.json`): `abierto` (bool) — si es
  `false` en el momento de la ingesta, la convocatoria NO se ofrece como
  oportunidad (motivo "no abierta en origen"); `tipoConvocatoria` (texto
  libre, p. ej. "Concesión directa - instrumental" para ayudas nominativas
  sin concurrencia) — si contiene "concesión directa" (normalizado), ídem
  (motivo "concesión directa (no concurrencia)"). Cualquiera de los dos
  motivos -> `estado_ingesta = DESCARTADA_POR_DOMINIO` directamente (nunca
  pasa por EXTRAIDA/VERIFICADA) y el/los motivo(s) quedan en
  `requisitos_elegibilidad.exclusiones` (así el resumen de la pasada puede
  contar `descartadas_no_abiertas`/`descartadas_concesion_directa` sin un
  campo nuevo en el contrato congelado). Campo AUSENTE en el detalle -> nunca
  se descarta por ese criterio (conservador: jamás se adivina por el título).
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
    normalizar_texto_comparacion,
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

# Tabla CERRADA (A1): los 19 nombres oficiales de CCAA (17 + Ceuta y Melilla)
# más los alias ya usados en consola (`web/rutas/consola/_soporte.CENTROIDE_CCAA`
# — mismo conjunto de claves normalizadas, duplicado a propósito: este adapter
# no debe depender de una ruta web; el normalizador SÍ se reutiliza, nunca se
# reimplementa). Claves ya normalizadas con `normalizar_texto_comparacion`.
_NOMBRES_CCAA_NUTS1: frozenset[str] = frozenset(
    {
        "andalucia",
        "aragon",
        "principado de asturias",
        "asturias",
        "illes balears",
        "islas baleares",
        "canarias",
        "cantabria",
        "castilla y leon",
        "castilla-la mancha",
        "catalunya",
        "cataluna",
        "comunitat valenciana",
        "comunidad valenciana",
        "extremadura",
        "galicia",
        "comunidad de madrid",
        "madrid",
        "region de murcia",
        "comunidad foral de navarra",
        "navarra",
        "pais vasco",
        "euskadi",
        "la rioja",
        "ceuta",
        "melilla",
    }
)

# B — motivos deterministas de descarte por dominio (ver docstring del módulo).
MOTIVO_NO_ABIERTA_EN_ORIGEN = "no abierta en origen"
MOTIVO_CONCESION_DIRECTA = "concesión directa (no concurrencia)"

_ANCHURA_AMBITO: dict[AmbitoTerritorial, int] = {
    AmbitoTerritorial.NACIONAL: 0,
    AmbitoTerritorial.AUTONOMICO: 1,
    AmbitoTerritorial.PROVINCIAL: 2,
    AmbitoTerritorial.LOCAL: 3,
}


def _url_origen_bdns(codigo_bdns: str) -> str:
    """Clave natural de dedupe (ADR-001 §6.5): URL de detalle con el código BDNS."""
    return f"{URL_DETALLE_BDNS}?numConv={codigo_bdns}"


def _tipo_fuente_desde_nivel1(nivel1: str | None) -> TipoFuente:
    return _MAPA_NIVEL1_TIPO_FUENTE.get(nivel1 or "", TipoFuente.PUBLICA_LOCAL)


def _ambito_y_region_desde_regiones(
    regiones: list[dict],
) -> tuple[AmbitoTerritorial, str | None, str | None]:
    """Deriva (ambito_geografico, region, provincia) a partir del código NUTS de
    la ÚNICA región (cuando hay exactamente una); ver regla completa en la
    nota del docstring del módulo. NO aplica el tope por órgano (A2) — eso lo
    hace `_aplicar_tope_por_organo`, siempre después de esta función."""
    descripciones = [
        (r.get("descripcion") or "").strip() for r in (regiones or []) if r.get("descripcion")
    ]
    if len(descripciones) != 1:
        return AmbitoTerritorial.NACIONAL, None, None
    codigo, _, nombre = descripciones[0].partition(" - ")
    codigo = codigo.strip()
    nombre = nombre.strip()
    if not nombre or not codigo.startswith("ES"):
        return AmbitoTerritorial.NACIONAL, None, None
    digitos = codigo[2:]
    if not digitos.isdigit():
        return AmbitoTerritorial.NACIONAL, None, None
    if len(digitos) == 1:
        if normalizar_texto_comparacion(nombre) in _NOMBRES_CCAA_NUTS1:
            return AmbitoTerritorial.AUTONOMICO, nombre, None
        return AmbitoTerritorial.NACIONAL, None, None
    if len(digitos) == 2:
        return AmbitoTerritorial.AUTONOMICO, nombre, None
    if len(digitos) == 3:
        return AmbitoTerritorial.PROVINCIAL, None, nombre
    return AmbitoTerritorial.NACIONAL, None, None


def _aplicar_tope_por_organo(
    ambito: AmbitoTerritorial,
    region: str | None,
    provincia: str | None,
    organo: dict,
) -> tuple[AmbitoTerritorial, str | None, str | None]:
    """A2 — el ámbito derivado JAMÁS puede ser más amplio que el órgano
    convocante (invariante nuevo tras el hallazgo numConv=920435: sin este
    tope, un fallo de parseo de `regiones` puede sobre-prometer una
    convocatoria autonómica/local como nacional). Ver regla completa en el
    docstring del módulo."""
    nivel1 = organo.get("nivel1")
    if nivel1 == "AUTONOMICA":
        tope = AmbitoTerritorial.AUTONOMICO
        if _ANCHURA_AMBITO[ambito] < _ANCHURA_AMBITO[tope]:
            nivel2 = (organo.get("nivel2") or "").strip() or None
            return tope, region or nivel2, None
        return ambito, region, provincia
    if nivel1 == "LOCAL":
        tope = AmbitoTerritorial.PROVINCIAL
        if _ANCHURA_AMBITO[ambito] < _ANCHURA_AMBITO[tope]:
            return tope, None, None
        return ambito, region, provincia
    return ambito, region, provincia


def _motivos_descarte_dominio(detalle: dict) -> tuple[str, ...]:
    """B1/B2 — motivos deterministas de descarte a partir de campos REALES del
    detalle BDNS; ver docstring del módulo. Dato ausente -> nunca se descarta
    por ese criterio."""
    motivos: list[str] = []
    if detalle.get("abierto") is False:
        motivos.append(MOTIVO_NO_ABIERTA_EN_ORIGEN)
    tipo_convocatoria = detalle.get("tipoConvocatoria")
    if tipo_convocatoria and "concesion directa" in normalizar_texto_comparacion(tipo_convocatoria):
        motivos.append(MOTIVO_CONCESION_DIRECTA)
    return tuple(motivos)


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


def mapear_convocatoria(detalle: dict, *, ahora: datetime) -> Convocatoria:
    organo = detalle.get("organo") or {}
    codigo_bdns = str(detalle["codigoBDNS"])
    ambito_geografico, region, provincia = _ambito_y_region_desde_regiones(
        detalle.get("regiones") or []
    )
    ambito_geografico, region, provincia = _aplicar_tope_por_organo(
        ambito_geografico, region, provincia, organo
    )

    motivos_descarte = _motivos_descarte_dominio(detalle)
    estado_ingesta = (
        EstadoIngesta.DESCARTADA_POR_DOMINIO if motivos_descarte else EstadoIngesta.EXTRAIDA
    )

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
            exclusiones=motivos_descarte,
        ),
        ambito_geografico=ambito_geografico,
        plazos=Plazos(
            fecha_apertura=_fecha_desde_iso(detalle.get("fechaInicioSolicitud")),
            fecha_cierre=_fecha_desde_iso(detalle.get("fechaFinSolicitud")),
        ),
        cuantias=Cuantias(importe_maximo_centimos=_euros_a_centimos(detalle.get("presupuestoTotal"))),
        estado_ingesta=estado_ingesta,
        creado_en=ahora,
        actualizado_en=ahora,
        documento_origen_ref=detalle.get("urlBasesReguladoras"),
        region=region,
        provincia=provincia,
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
                    convocatoria = mapear_convocatoria(detalle, ahora=self._reloj())
                except Exception as exc:  # una convocatoria feo/caída no tumba las demás
                    logger.warning(
                        "Fallo de transporte/mapeo en detalle BDNS numConv=%s: %s", num_conv, exc
                    )
                    continue
                yield convocatoria

            if respuesta.get("last", True):
                return
            page += 1
