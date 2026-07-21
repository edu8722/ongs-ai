"""F2 — FuenteBDNS: mapeo determinista, paginación, filtros como datos y
degradación limpia ante fallos de transporte (CLAUDE.md — reglas de oro).

El transporte SIEMPRE es un stub con fixtures grabadas bajo
`tests/fixtures/ingesta/` — cero peticiones de red reales.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from ongs_ai.adapters.ingesta.base import FiltrosBusqueda
from ongs_ai.adapters.ingesta.bdns import (
    MOTIVO_CONCESION_DIRECTA,
    MOTIVO_NO_ABIERTA_EN_ORIGEN,
    URL_BUSQUEDA_BDNS,
    URL_DETALLE_BDNS,
    FuenteBDNS,
    _aplicar_tope_por_organo,
    _ambito_y_region_desde_regiones,
    mapear_convocatoria,
    _motivos_descarte_dominio,
)
from ongs_ai.dominio.entidades import AmbitoTerritorial, EstadoIngesta, TipoFuente

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ingesta"
AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)


def _cargar_fixture(nombre: str) -> dict:
    return json.loads((FIXTURES_DIR / nombre).read_text(encoding="utf-8"))


class _TransporteStub:
    """Transporte inyectable de test — nunca hace red, solo devuelve fixtures."""

    def __init__(
        self,
        *,
        paginas: dict[int, dict],
        detalles: dict[str, dict],
        fallos_detalle: frozenset[str] = frozenset(),
        fallo_busqueda_en_pagina: int | None = None,
    ) -> None:
        self._paginas = paginas
        self._detalles = detalles
        self._fallos_detalle = fallos_detalle
        self._fallo_busqueda_en_pagina = fallo_busqueda_en_pagina
        self.llamadas_busqueda: list[dict] = []
        self.llamadas_detalle: list[dict] = []

    def obtener_json(self, url: str, params: dict) -> dict:
        if url == URL_BUSQUEDA_BDNS:
            self.llamadas_busqueda.append(dict(params))
            page = params["page"]
            if page == self._fallo_busqueda_en_pagina:
                raise RuntimeError("fallo simulado de red en búsqueda BDNS")
            return self._paginas[page]
        if url == URL_DETALLE_BDNS:
            self.llamadas_detalle.append(dict(params))
            num_conv = params["numConv"]
            if num_conv in self._fallos_detalle:
                raise RuntimeError(f"fallo simulado de red en detalle BDNS numConv={num_conv}")
            return self._detalles[num_conv]
        raise AssertionError(f"URL no esperada en el stub de transporte: {url}")


def _paginas_completas() -> dict[int, dict]:
    return {
        0: _cargar_fixture("bdns_busqueda_pagina_0.json"),
        1: _cargar_fixture("bdns_busqueda_pagina_1.json"),
    }


def _detalles_completos() -> dict[str, dict]:
    return {
        num: _cargar_fixture(f"bdns_detalle_{num}.json")
        for num in ("100001", "100002", "100003", "100004")
    }


def _fuente(transporte: _TransporteStub, page_size: int = 3) -> FuenteBDNS:
    return FuenteBDNS(transporte, reloj=lambda: AHORA, page_size=page_size)


# --- Mapeo determinista --------------------------------------------------


def test_mapeo_convocatoria_estatal_nacional_dinero_con_decimales():
    transporte = _TransporteStub(paginas=_paginas_completas(), detalles=_detalles_completos())
    convocatorias = {c.convocatoria_id: c for c in _fuente(transporte).buscar()}

    c = convocatorias["bdns-100001"]
    assert c.fuente.portal == "BDNS"
    assert c.fuente.url_origen == f"{URL_DETALLE_BDNS}?numConv=100001"
    assert c.fuente.tipo is TipoFuente.PUBLICA_NACIONAL
    assert c.ambito_geografico is AmbitoTerritorial.NACIONAL
    assert c.region is None
    assert c.provincia is None
    assert c.requisitos_elegibilidad.ambito_territorial_requerido is AmbitoTerritorial.NACIONAL
    assert c.objeto == (
        "Convocatoria ficticia estatal de subvenciones para entidades del tercer "
        "sector de acción social (Finalidad: Servicios Sociales y Promoción Social)"
    )
    assert c.beneficiarios_elegibles == "PERSONAS JURÍDICAS QUE NO DESARROLLAN ACTIVIDAD ECONÓMICA"
    assert c.plazos.fecha_apertura == date(2026, 5, 20)
    assert c.plazos.fecha_cierre == date(2026, 6, 18)
    # 500000.5 EUR -> 50_000_050 céntimos, entero, jamás float hacia el dominio.
    assert c.cuantias.importe_maximo_centimos == 50_000_050
    assert isinstance(c.cuantias.importe_maximo_centimos, int)
    assert c.documento_origen_ref == "https://www.example-ficticio.gob.es/bases-reguladoras"
    assert c.estado_ingesta is EstadoIngesta.VERIFICADA


def test_mapeo_convocatoria_autonomica_dinero_entero_y_region_separada():
    transporte = _TransporteStub(paginas=_paginas_completas(), detalles=_detalles_completos())
    convocatorias = {c.convocatoria_id: c for c in _fuente(transporte).buscar()}

    c = convocatorias["bdns-100002"]
    assert c.fuente.tipo is TipoFuente.PUBLICA_AUTONOMICA
    assert c.ambito_geografico is AmbitoTerritorial.AUTONOMICO
    assert c.region == "CATALUÑA"
    assert c.provincia is None
    assert c.beneficiarios_elegibles == (
        "PERSONAS JURÍDICAS QUE NO DESARROLLAN ACTIVIDAD ECONÓMICA; "
        "ASOCIACIONES DECLARADAS DE UTILIDAD PÚBLICA"
    )
    # 250000 EUR (int) -> 25_000_000 céntimos.
    assert c.cuantias.importe_maximo_centimos == 25_000_000
    assert c.estado_ingesta is EstadoIngesta.VERIFICADA


def test_convocatoria_local_sin_fecha_cierre_no_se_promociona():
    transporte = _TransporteStub(paginas=_paginas_completas(), detalles=_detalles_completos())
    convocatorias = {c.convocatoria_id: c for c in _fuente(transporte).buscar()}

    c = convocatorias["bdns-100003"]
    assert c.fuente.tipo is TipoFuente.PUBLICA_LOCAL
    # La región de la convocatoria LOCAL trae un código NUTS3 (provincia), así
    # que el ambito_geografico calculado es PROVINCIAL — tipo (jerarquía) y
    # ambito_geografico (regiones) se derivan de campos distintos y pueden diferir.
    assert c.ambito_geografico is AmbitoTerritorial.PROVINCIAL
    assert c.provincia == "Córdoba"
    assert c.region is None
    assert c.cuantias.importe_maximo_centimos == 1_500_075
    assert c.plazos.fecha_cierre is None
    assert c.estado_ingesta is EstadoIngesta.EXTRAIDA


def test_convocatoria_otros_nivel1_usa_tipo_conservador_y_varias_regiones_es_nacional():
    transporte = _TransporteStub(paginas=_paginas_completas(), detalles=_detalles_completos())
    convocatorias = {c.convocatoria_id: c for c in _fuente(transporte).buscar()}

    c = convocatorias["bdns-100004"]
    # nivel1="OTROS" no tiene mapeo claro -> valor más conservador: publica_local.
    assert c.fuente.tipo is TipoFuente.PUBLICA_LOCAL
    # Varias regiones -> nacional, sin region ni provincia.
    assert c.ambito_geografico is AmbitoTerritorial.NACIONAL
    assert c.region is None
    assert c.provincia is None
    assert c.beneficiarios_elegibles == ""
    assert c.cuantias.importe_maximo_centimos is None
    assert c.estado_ingesta is EstadoIngesta.EXTRAIDA


# --- _ambito_y_region_desde_regiones (unidad) -------------------------------


def test_ambito_region_sin_regiones_es_nacional():
    assert _ambito_y_region_desde_regiones([]) == (AmbitoTerritorial.NACIONAL, None, None)


def test_ambito_region_multiples_regiones_es_nacional():
    regiones = [{"descripcion": "ES51 - CATALUÑA"}, {"descripcion": "ES52 - COMUNIDAD FICTICIA"}]
    assert _ambito_y_region_desde_regiones(regiones) == (AmbitoTerritorial.NACIONAL, None, None)


def test_ambito_region_es_sola_espana_es_nacional():
    assert _ambito_y_region_desde_regiones([{"descripcion": "ES - ESPAÑA"}]) == (
        AmbitoTerritorial.NACIONAL,
        None,
        None,
    )


def test_ambito_region_nuts2_dos_digitos_es_autonomico():
    assert _ambito_y_region_desde_regiones([{"descripcion": "ES51 - CATALUÑA"}]) == (
        AmbitoTerritorial.AUTONOMICO,
        "CATALUÑA",
        None,
    )


def test_ambito_region_nuts3_tres_digitos_es_provincial():
    assert _ambito_y_region_desde_regiones([{"descripcion": "ES613 - Córdoba"}]) == (
        AmbitoTerritorial.PROVINCIAL,
        None,
        "Córdoba",
    )


def test_ambito_region_codigo_no_es_es_nacional():
    assert _ambito_y_region_desde_regiones([{"descripcion": "XXXX - TODO EL MUNDO"}]) == (
        AmbitoTerritorial.NACIONAL,
        None,
        None,
    )


def test_ambito_region_codigo_no_numerico_es_nacional():
    assert _ambito_y_region_desde_regiones([{"descripcion": "ESAB - RARO"}]) == (
        AmbitoTerritorial.NACIONAL,
        None,
        None,
    )


def test_ambito_region_nuts1_un_digito_con_ccaa_reconocida_es_autonomico():
    # Caso real verificado (hallazgo del operador, numConv=920435): 1 dígito
    # tras "ES" con nombre de CCAA reconocido -> autonómico, NUNCA nacional.
    assert _ambito_y_region_desde_regiones([{"descripcion": "ES7 - CANARIAS"}]) == (
        AmbitoTerritorial.AUTONOMICO,
        "CANARIAS",
        None,
    )


def test_ambito_region_nuts1_un_digito_sin_ccaa_reconocida_es_nacional():
    assert _ambito_y_region_desde_regiones([{"descripcion": "ES9 - COMUNIDAD FICTICIA"}]) == (
        AmbitoTerritorial.NACIONAL,
        None,
        None,
    )


# --- Tope por órgano (A2) ---------------------------------------------------


def test_tope_organo_autonomica_reduce_nacional_a_autonomico_con_nivel2():
    organo = {"nivel1": "AUTONOMICA", "nivel2": "CANARIAS"}
    assert _aplicar_tope_por_organo(AmbitoTerritorial.NACIONAL, None, None, organo) == (
        AmbitoTerritorial.AUTONOMICO,
        "CANARIAS",
        None,
    )


def test_tope_organo_autonomica_no_pisa_region_ya_derivada():
    organo = {"nivel1": "AUTONOMICA", "nivel2": "CANARIAS"}
    assert _aplicar_tope_por_organo(AmbitoTerritorial.AUTONOMICO, "CATALUÑA", None, organo) == (
        AmbitoTerritorial.AUTONOMICO,
        "CATALUÑA",
        None,
    )


def test_tope_organo_autonomica_no_ensancha_provincial():
    organo = {"nivel1": "AUTONOMICA"}
    assert _aplicar_tope_por_organo(AmbitoTerritorial.PROVINCIAL, None, "Jaén", organo) == (
        AmbitoTerritorial.PROVINCIAL,
        None,
        "Jaén",
    )


def test_tope_organo_local_reduce_nacional_a_provincial_sin_nombre():
    organo = {"nivel1": "LOCAL"}
    assert _aplicar_tope_por_organo(AmbitoTerritorial.NACIONAL, None, None, organo) == (
        AmbitoTerritorial.PROVINCIAL,
        None,
        None,
    )


def test_tope_organo_local_reduce_autonomico_a_provincial_y_limpia_region():
    organo = {"nivel1": "LOCAL"}
    assert _aplicar_tope_por_organo(AmbitoTerritorial.AUTONOMICO, "CATALUÑA", None, organo) == (
        AmbitoTerritorial.PROVINCIAL,
        None,
        None,
    )


def test_tope_organo_estado_mantiene_lo_derivado():
    organo = {"nivel1": "ESTADO"}
    assert _aplicar_tope_por_organo(AmbitoTerritorial.NACIONAL, None, None, organo) == (
        AmbitoTerritorial.NACIONAL,
        None,
        None,
    )


# --- Descarte por dominio (B) -----------------------------------------------


def test_motivos_descarte_abierto_false_da_motivo_no_abierta():
    assert _motivos_descarte_dominio({"abierto": False}) == (MOTIVO_NO_ABIERTA_EN_ORIGEN,)


def test_motivos_descarte_abierto_true_no_descarta():
    assert _motivos_descarte_dominio({"abierto": True}) == ()


def test_motivos_descarte_abierto_ausente_no_descarta_por_ese_criterio():
    assert _motivos_descarte_dominio({}) == ()


def test_motivos_descarte_concesion_directa_da_motivo():
    assert _motivos_descarte_dominio(
        {"tipoConvocatoria": "Concesión directa - instrumental"}
    ) == (MOTIVO_CONCESION_DIRECTA,)


def test_motivos_descarte_concurrencia_competitiva_no_descarta():
    assert _motivos_descarte_dominio({"tipoConvocatoria": "Concurrencia competitiva - canónica"}) == ()


def test_motivos_descarte_tipo_convocatoria_ausente_no_descarta_por_ese_criterio():
    assert _motivos_descarte_dominio({}) == ()


def test_motivos_descarte_ambos_criterios_da_los_dos_motivos():
    detalle = {"abierto": False, "tipoConvocatoria": "Concesión directa - instrumental"}
    assert _motivos_descarte_dominio(detalle) == (
        MOTIVO_NO_ABIERTA_EN_ORIGEN,
        MOTIVO_CONCESION_DIRECTA,
    )


# --- Caso real numConv=920435 (hallazgo del operador) -----------------------
#
# Fixture grabada de una petición manual real (fuera de tests) contra
# https://www.infosubvenciones.es/bdnstrans/api/convocatorias?numConv=920435
# el 2026-07-22: "PARTICIPACIÓN DE CCOO ... FP CANARIA 2026", órgano
# AUTONOMICA/CANARIAS, regiones=[{"descripcion": "ES7 - CANARIAS"}],
# abierto=false, tipoConvocatoria="Concesión directa - instrumental". Antes
# de A/B esta convocatoria se mapeaba como NACIONAL y VERIFICADA — triple
# fallo de honestidad de datos (ver engineering/06_SIGUIENTES_PASOS.md,
# PROMPT-023).


def test_caso_real_920435_ambito_autonomico_canarias_y_descartada_por_dominio():
    detalle = _cargar_fixture("bdns_detalle_920435.json")
    c = mapear_convocatoria(detalle, ahora=AHORA)

    assert c.convocatoria_id == "bdns-920435"
    assert c.fuente.tipo is TipoFuente.PUBLICA_AUTONOMICA
    assert c.ambito_geografico is AmbitoTerritorial.AUTONOMICO
    assert c.region == "CANARIAS"
    assert c.provincia is None
    assert c.requisitos_elegibilidad.ambito_territorial_requerido is AmbitoTerritorial.AUTONOMICO

    assert c.estado_ingesta is EstadoIngesta.DESCARTADA_POR_DOMINIO
    assert c.requisitos_elegibilidad.exclusiones == (
        MOTIVO_NO_ABIERTA_EN_ORIGEN,
        MOTIVO_CONCESION_DIRECTA,
    )


# --- Paginación ------------------------------------------------------------


def test_paginacion_recorre_todas_las_paginas_hasta_last_true():
    transporte = _TransporteStub(paginas=_paginas_completas(), detalles=_detalles_completos())
    convocatorias = list(_fuente(transporte).buscar())

    assert [c.convocatoria_id for c in convocatorias] == [
        "bdns-100001",
        "bdns-100002",
        "bdns-100003",
        "bdns-100004",
    ]
    assert [llamada["page"] for llamada in transporte.llamadas_busqueda] == [0, 1]


# --- Degradación limpia ante fallos de transporte --------------------------


def test_fallo_de_transporte_en_busqueda_degrada_limpio_sin_excepcion():
    transporte = _TransporteStub(
        paginas=_paginas_completas(),
        detalles=_detalles_completos(),
        fallo_busqueda_en_pagina=0,
    )
    convocatorias = list(_fuente(transporte).buscar())
    assert convocatorias == []


def test_fallo_de_transporte_en_detalle_salta_esa_convocatoria_y_sigue():
    transporte = _TransporteStub(
        paginas=_paginas_completas(),
        detalles=_detalles_completos(),
        fallos_detalle=frozenset({"100002"}),
    )
    convocatorias = list(_fuente(transporte).buscar())
    assert [c.convocatoria_id for c in convocatorias] == [
        "bdns-100001",
        "bdns-100003",
        "bdns-100004",
    ]


# --- Filtros como datos, nunca hardcodeados --------------------------------


def test_filtros_de_busqueda_se_envian_como_parametros_de_la_llamada():
    pagina_vacia = {"content": [], "last": True}
    transporte = _TransporteStub(paginas={0: pagina_vacia}, detalles={})
    filtros = FiltrosBusqueda(
        descripcion="sindrome-ficticio-de-test",
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
    )

    list(_fuente(transporte).buscar(filtros))

    assert transporte.llamadas_busqueda == [
        {
            "page": 0,
            "pageSize": 3,
            "descripcion": "sindrome-ficticio-de-test",
            "fechaDesde": "01/01/2026",
            "fechaHasta": "31/01/2026",
        }
    ]


def test_sin_filtros_no_envia_parametros_de_texto_ni_fecha():
    pagina_vacia = {"content": [], "last": True}
    transporte = _TransporteStub(paginas={0: pagina_vacia}, detalles={})

    list(_fuente(transporte).buscar())

    assert transporte.llamadas_busqueda == [{"page": 0, "pageSize": 3}]
