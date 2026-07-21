"""Orquestación de `scripts/reevaluar_ingesta.reevaluar_pasada` — PROMPT-023 C.
Todo inyectado/stub: sin red (transporte stub), `AlmacenMemoria` en vez de
SQLite. `scripts/` no es un paquete instalado — se añade a `sys.path` igual
que `tests/test_ejecutar_ingesta.py`.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from reevaluar_ingesta import reevaluar_pasada  # noqa: E402

from ongs_ai.adapters.ingesta.bdns import (  # noqa: E402
    MOTIVO_CONCESION_DIRECTA,
    MOTIVO_NO_ABIERTA_EN_ORIGEN,
    URL_DETALLE_BDNS,
)
from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria  # noqa: E402
from ongs_ai.dominio.entidades import (  # noqa: E402
    AmbitoTerritorial,
    Convocatoria,
    Cuantias,
    EstadoIngesta,
    Fuente,
    Plazos,
    RequisitosElegibilidad,
    TipoFuente,
)

AHORA = datetime(2026, 7, 22, tzinfo=timezone.utc)


class _TransporteStub:
    def __init__(self, detalles: dict[str, dict], *, fallos: frozenset[str] = frozenset()) -> None:
        self._detalles = detalles
        self._fallos = fallos
        self.llamadas: list[dict] = []

    def obtener_json(self, url: str, params: dict) -> dict:
        assert url == URL_DETALLE_BDNS
        self.llamadas.append(dict(params))
        num_conv = params["numConv"]
        if num_conv in self._fallos:
            raise RuntimeError(f"fallo simulado de red re-consultando numConv={num_conv}")
        return self._detalles[num_conv]


def _convocatoria_vieja(convocatoria_id: str = "bdns-920435", **overrides) -> Convocatoria:
    base = dict(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="BDNS",
            url_origen=f"{URL_DETALLE_BDNS}?numConv={convocatoria_id.removeprefix('bdns-')}",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto="PARTICIPACIÓN DE CCOO PROGRAMA DE SENSIBILIZACIÓN PRL EN FP CANARIA 2026",
        beneficiarios_elegibles="PERSONAS JURÍDICAS QUE NO DESARROLLAN ACTIVIDAD ECONÓMICA",
        requisitos_elegibilidad=RequisitosElegibilidad(ambito_territorial_requerido=AmbitoTerritorial.NACIONAL),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 6, 4), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=10_000_000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
        region=None,
        provincia=None,
    )
    base.update(overrides)
    return Convocatoria(**base)


def _detalle_920435(**overrides) -> dict:
    base = {
        "organo": {"nivel1": "AUTONOMICA", "nivel2": "CANARIAS"},
        "codigoBDNS": "920435",
        "regiones": [{"descripcion": "ES7 - CANARIAS"}],
        "abierto": False,
        "tipoConvocatoria": "Concesión directa - instrumental",
    }
    base.update(overrides)
    return base


def test_corrige_ambito_mal_mapeado_y_no_escribe_en_modo_simular():
    almacen = AlmacenMemoria()
    almacen.guardar_convocatoria(_convocatoria_vieja())
    transporte = _TransporteStub({"920435": _detalle_920435()})

    resumen, cambios = reevaluar_pasada(almacen, transporte, ahora=AHORA, aplicar=False)

    assert resumen.revisadas == 1
    assert resumen.con_cambios == 1
    assert resumen.fallos_transporte == 0
    assert resumen.aplicado is False

    assert len(cambios) == 1
    cambio = cambios[0]
    assert cambio.hay_cambio is True
    assert cambio.ambito_antes is AmbitoTerritorial.NACIONAL
    assert cambio.ambito_despues is AmbitoTerritorial.AUTONOMICO
    assert cambio.region_despues == "CANARIAS"
    assert cambio.estado_antes is EstadoIngesta.VERIFICADA
    assert cambio.estado_despues is EstadoIngesta.DESCARTADA_POR_DOMINIO

    # Simular: el almacén NO cambia.
    intacta = almacen.obtener_convocatoria("bdns-920435")
    assert intacta.ambito_geografico is AmbitoTerritorial.NACIONAL
    assert intacta.estado_ingesta is EstadoIngesta.VERIFICADA


def test_aplicar_persiste_ambito_region_y_descarte_conservando_enriquecimiento_ia():
    almacen = AlmacenMemoria()
    # Enriquecimiento IA previo: debe sobrevivir a la reevaluación.
    vieja = _convocatoria_vieja(
        requisitos_elegibilidad=RequisitosElegibilidad(
            ambito_territorial_requerido=AmbitoTerritorial.NACIONAL,
            forma_juridica_requerida="asociacion",
            antiguedad_minima_anios=2,
        )
    )
    almacen.guardar_convocatoria(vieja)
    transporte = _TransporteStub({"920435": _detalle_920435()})

    resumen, _ = reevaluar_pasada(almacen, transporte, ahora=AHORA, aplicar=True)

    assert resumen.con_cambios == 1
    actualizada = almacen.obtener_convocatoria("bdns-920435")
    assert actualizada.ambito_geografico is AmbitoTerritorial.AUTONOMICO
    assert actualizada.region == "CANARIAS"
    assert actualizada.provincia is None
    assert actualizada.estado_ingesta is EstadoIngesta.DESCARTADA_POR_DOMINIO
    assert actualizada.requisitos_elegibilidad.ambito_territorial_requerido is AmbitoTerritorial.AUTONOMICO
    assert actualizada.requisitos_elegibilidad.exclusiones == (
        MOTIVO_NO_ABIERTA_EN_ORIGEN,
        MOTIVO_CONCESION_DIRECTA,
    )
    # El enriquecimiento IA previo NO se pisa.
    assert actualizada.requisitos_elegibilidad.forma_juridica_requerida == "asociacion"
    assert actualizada.requisitos_elegibilidad.antiguedad_minima_anios == 2


def test_sin_cambios_no_cuenta_como_cambio():
    almacen = AlmacenMemoria()
    ya_correcta = _convocatoria_vieja(
        ambito_geografico=AmbitoTerritorial.AUTONOMICO,
        region="CANARIAS",
        estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO,
        requisitos_elegibilidad=RequisitosElegibilidad(
            ambito_territorial_requerido=AmbitoTerritorial.AUTONOMICO,
            exclusiones=(MOTIVO_NO_ABIERTA_EN_ORIGEN, MOTIVO_CONCESION_DIRECTA),
        ),
    )
    almacen.guardar_convocatoria(ya_correcta)
    transporte = _TransporteStub({"920435": _detalle_920435()})

    resumen, cambios = reevaluar_pasada(almacen, transporte, ahora=AHORA, aplicar=True)

    assert resumen.con_cambios == 0
    assert cambios[0].hay_cambio is False


def test_ya_descartada_nunca_se_rescata():
    almacen = AlmacenMemoria()
    descartada = _convocatoria_vieja(
        ambito_geografico=AmbitoTerritorial.AUTONOMICO,
        region="CANARIAS",
        estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO,
        requisitos_elegibilidad=RequisitosElegibilidad(
            ambito_territorial_requerido=AmbitoTerritorial.AUTONOMICO,
            exclusiones=(MOTIVO_NO_ABIERTA_EN_ORIGEN,),
        ),
    )
    almacen.guardar_convocatoria(descartada)
    # La BDNS "reabre" la convocatoria — la reevaluación NUNCA la rescata.
    transporte = _TransporteStub({"920435": _detalle_920435(abierto=True, tipoConvocatoria="Concurrencia competitiva")})

    resumen, cambios = reevaluar_pasada(almacen, transporte, ahora=AHORA, aplicar=True)

    assert resumen.con_cambios == 0
    assert cambios[0].estado_antes is EstadoIngesta.DESCARTADA_POR_DOMINIO
    assert cambios[0].estado_despues is EstadoIngesta.DESCARTADA_POR_DOMINIO


def test_fallo_de_transporte_degrada_limpio_y_sigue():
    almacen = AlmacenMemoria()
    almacen.guardar_convocatoria(_convocatoria_vieja("bdns-1"))
    almacen.guardar_convocatoria(_convocatoria_vieja("bdns-2", ambito_geografico=AmbitoTerritorial.AUTONOMICO, region="CANARIAS"))
    transporte = _TransporteStub(
        {"2": _detalle_920435(codigoBDNS="2")},
        fallos=frozenset({"1"}),
    )

    resumen, cambios = reevaluar_pasada(almacen, transporte, ahora=AHORA, aplicar=False)

    assert resumen.revisadas == 2
    assert resumen.fallos_transporte == 1
    assert len(cambios) == 1
    assert cambios[0].convocatoria_id == "bdns-2"


def test_solo_revisa_convocatorias_del_portal_bdns():
    almacen = AlmacenMemoria()
    otra_fuente = _convocatoria_vieja(
        "otra-1",
        fuente=Fuente(portal="OTRO_PORTAL", url_origen="https://otro.example/1", tipo=TipoFuente.PRIVADA),
    )
    almacen.guardar_convocatoria(otra_fuente)
    transporte = _TransporteStub({})

    resumen, cambios = reevaluar_pasada(almacen, transporte, ahora=AHORA, aplicar=False)

    assert resumen.revisadas == 0
    assert cambios == []
