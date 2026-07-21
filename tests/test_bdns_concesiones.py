"""FuenteConcesionesBDNS — ADR-007 §2/§3.2/§3.4: mapeo determinista de
concesiones históricas, `nifCif`+fechas como filtros de servidor, reutilización
del detalle de convocatoria (`bdns.py`) para `es_concesion_directa`/apertura,
y degradación limpia ante fallos de transporte. Fixtures SINTÉTICAS bajo
`tests/fixtures/ingesta/` — jamás el histórico real ni NIFs reales.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from ongs_ai.adapters.ingesta.bdns import URL_DETALLE_BDNS
from ongs_ai.adapters.ingesta.bdns_concesiones import URL_CONCESIONES_BDNS, FuenteConcesionesBDNS

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ingesta"
AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)
ENTIDAD_ID = "ent-concesiones-1"


def _cargar_fixture(nombre: str) -> dict:
    return json.loads((FIXTURES_DIR / nombre).read_text(encoding="utf-8"))


class _TransporteStub:
    def __init__(
        self,
        *,
        paginas: dict[int, dict],
        detalles: dict[str, dict],
        fallo_busqueda_en_pagina: int | None = None,
        fallos_detalle: frozenset[str] = frozenset(),
    ) -> None:
        self._paginas = paginas
        self._detalles = detalles
        self._fallo_busqueda_en_pagina = fallo_busqueda_en_pagina
        self._fallos_detalle = fallos_detalle
        self.llamadas_busqueda: list[dict] = []
        self.llamadas_detalle: list[dict] = []

    def obtener_json(self, url: str, params: dict) -> dict:
        if url == URL_CONCESIONES_BDNS:
            self.llamadas_busqueda.append(dict(params))
            page = params["page"]
            if page == self._fallo_busqueda_en_pagina:
                raise RuntimeError("fallo simulado de red en búsqueda de concesiones")
            return self._paginas[page]
        if url == URL_DETALLE_BDNS:
            self.llamadas_detalle.append(dict(params))
            num_conv = params["numConv"]
            if num_conv in self._fallos_detalle:
                raise RuntimeError(f"fallo simulado de red en detalle numConv={num_conv}")
            return self._detalles[num_conv]
        raise AssertionError(f"URL no esperada: {url}")


def _paginas() -> dict[int, dict]:
    return {0: _cargar_fixture("bdns_concesiones_pagina_0.json")}


def _detalles() -> dict[str, dict]:
    return {
        num: _cargar_fixture(f"bdns_detalle_{num}.json") for num in ("700001", "700002", "700003")
    }


def _generador_id():
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"hist-{next(contador)}"

    return siguiente


def _fuente(transporte: _TransporteStub) -> FuenteConcesionesBDNS:
    return FuenteConcesionesBDNS(transporte, reloj=lambda: AHORA, generador_id=_generador_id())


def test_mapeo_basico_y_filtros_de_servidor_nif_y_fechas():
    transporte = _TransporteStub(paginas=_paginas(), detalles=_detalles())
    fuente = _fuente(transporte)

    resultado = list(
        fuente.buscar_por_nif(
            "G00000001",
            ENTIDAD_ID,
            fecha_desde=date(2021, 1, 1),
            fecha_hasta=date(2026, 12, 31),
        )
    )

    assert transporte.llamadas_busqueda[0]["nifCif"] == "G00000001"
    assert transporte.llamadas_busqueda[0]["fechaDesde"] == "01/01/2021"
    assert transporte.llamadas_busqueda[0]["fechaHasta"] == "31/12/2026"

    por_cod = {h.cod_concesion: h for h in resultado}
    assert set(por_cod) == {"CONC-9000001", "CONC-9000002", "CONC-9000003"}

    h1 = por_cod["CONC-9000001"]
    assert h1.entidad_id == ENTIDAD_ID
    assert h1.nif_beneficiario == "G00000001"
    assert h1.fecha_concesion == date(2024, 9, 15)
    assert h1.importe_centimos == 300_050  # 3000.5 EUR -> céntimos enteros
    assert isinstance(h1.importe_centimos, int)
    assert h1.cod_bdns_convocatoria == "700001"
    assert h1.organo_nivel1 == "ESTADO"
    assert h1.es_concesion_directa is False
    assert h1.apertura_convocatoria == date(2024, 5, 10)
    assert h1.capturado_en == AHORA


def test_registros_sin_forma_reconocible_se_descartan_y_se_cuentan():
    transporte = _TransporteStub(paginas=_paginas(), detalles=_detalles())
    fuente = _fuente(transporte)

    resultado = list(fuente.buscar_por_nif("G00000001", ENTIDAD_ID))

    assert len(resultado) == 3  # de los 5 registros de la fixture
    assert fuente.descartados == 2  # sin codConcesion / sin NIF parseable


def test_fingerprint_agrupa_misma_serie_pese_a_nivel3_distinto():
    """CALIBRACIÓN del arquitecto (derivacion.py): nivel3 se renombra entre
    legislaturas y queda FUERA del fingerprint — las ediciones 2024/2025 de
    la fixture llevan nivel3 distinto a propósito."""
    transporte = _TransporteStub(paginas=_paginas(), detalles=_detalles())
    fuente = _fuente(transporte)

    por_cod = {h.cod_concesion: h for h in fuente.buscar_por_nif("G00000001", ENTIDAD_ID)}

    assert (
        por_cod["CONC-9000001"].serie_fingerprint == por_cod["CONC-9000002"].serie_fingerprint
    )
    assert por_cod["CONC-9000001"].organo_nivel3 != por_cod["CONC-9000002"].organo_nivel3


def test_concesion_directa_desde_detalle_y_apertura_ausente_usa_proxy_none():
    transporte = _TransporteStub(paginas=_paginas(), detalles=_detalles())
    fuente = _fuente(transporte)

    por_cod = {h.cod_concesion: h for h in fuente.buscar_por_nif("G00000001", ENTIDAD_ID)}

    directa = por_cod["CONC-9000003"]
    assert directa.es_concesion_directa is True
    assert directa.apertura_convocatoria is None  # detalle sin fechaInicioSolicitud


def test_fallo_transporte_en_busqueda_degrada_limpio():
    transporte = _TransporteStub(paginas=_paginas(), detalles=_detalles(), fallo_busqueda_en_pagina=0)
    fuente = _fuente(transporte)

    resultado = list(fuente.buscar_por_nif("G00000001", ENTIDAD_ID))

    assert resultado == []


def test_fallo_transporte_en_detalle_no_descarta_la_concesion_y_degrada_conservador():
    transporte = _TransporteStub(
        paginas=_paginas(), detalles=_detalles(), fallos_detalle=frozenset({"700001"})
    )
    fuente = _fuente(transporte)

    por_cod = {h.cod_concesion: h for h in fuente.buscar_por_nif("G00000001", ENTIDAD_ID)}

    assert "CONC-9000001" in por_cod
    afectada = por_cod["CONC-9000001"]
    assert afectada.es_concesion_directa is False  # conservador: ausente -> concurrencia
    assert afectada.apertura_convocatoria is None


def test_detalle_de_convocatoria_se_pide_una_sola_vez_por_codigo():
    """Cache dentro de una misma llamada a `buscar_por_nif` (dos concesiones
    de la misma convocatoria no deberían darse en esta fixture, pero el
    contrato de caching se ancla igualmente pidiendo cada numConv una vez)."""
    transporte = _TransporteStub(paginas=_paginas(), detalles=_detalles())
    fuente = _fuente(transporte)

    list(fuente.buscar_por_nif("G00000001", ENTIDAD_ID))

    nums_pedidos = [l["numConv"] for l in transporte.llamadas_detalle]
    assert len(nums_pedidos) == len(set(nums_pedidos))
