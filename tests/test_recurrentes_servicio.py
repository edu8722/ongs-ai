"""Orquestación del proactivo (`servicios/recurrentes.py`) — ADR-007 §3.4/§3.6/
§3.8: captura+dedupe+derivación, re-derivación sin red, enlace por serie
(NUNCA crea Match) y transición a NO_APARECIDA. Todo inyectado, sin red.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime, timezone
from pathlib import Path

from ongs_ai.adapters.ingesta.bdns_concesiones import URL_CONCESIONES_BDNS, FuenteConcesionesBDNS
from ongs_ai.adapters.ingesta.bdns import URL_DETALLE_BDNS
from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    Convocatoria,
    Cuantias,
    DatosEconomicos,
    Entidad,
    EstadoIngesta,
    FormaJuridica,
    FormaJuridicaDeclarada,
    Fuente,
    Plazos,
    RequisitoFormal,
    RequisitosElegibilidad,
    TipoActividad,
    TipoFuente,
)
from ongs_ai.proactivo.modelo import Confianza, EstadoEsperada
from ongs_ai.servicios.recurrentes import (
    capturar_y_derivar_entidad,
    reevaluar_entidad,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ingesta"
AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _cargar_fixture(nombre: str) -> dict:
    return json.loads((FIXTURES_DIR / nombre).read_text(encoding="utf-8"))


class _TransporteStub:
    def __init__(self, *, paginas: dict[int, dict], detalles: dict[str, dict]) -> None:
        self._paginas = paginas
        self._detalles = detalles

    def obtener_json(self, url: str, params: dict) -> dict:
        if url == URL_CONCESIONES_BDNS:
            return self._paginas[params["page"]]
        if url == URL_DETALLE_BDNS:
            return self._detalles[params["numConv"]]
        raise AssertionError(f"URL no esperada: {url}")


def _generador_id(prefijo: str):
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"{prefijo}-{next(contador)}"

    return siguiente


def _entidad(entidad_id: str = "ent-recurrentes-1", nif: str = "G00000001") -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal="Asociación de Prueba",
        nif=nif,
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 1, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email=f"{entidad_id}@example.org"),
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


def _fuente() -> FuenteConcesionesBDNS:
    transporte = _TransporteStub(
        paginas={0: _cargar_fixture("bdns_concesiones_pagina_0.json")},
        detalles={
            num: _cargar_fixture(f"bdns_detalle_{num}.json") for num in ("700001", "700002", "700003")
        },
    )
    return FuenteConcesionesBDNS(transporte, reloj=lambda: AHORA, generador_id=_generador_id("hist"))


# --- capturar_y_derivar_entidad ----------------------------------------------


def test_captura_persiste_historial_deduplicado_y_deriva_esperadas():
    almacen = AlmacenMemoria()
    entidad = _entidad()

    resumen = capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )

    assert resumen.concesiones_encontradas == 3
    assert resumen.concesiones_nuevas == 3
    assert resumen.concesiones_descartadas == 2
    assert len(almacen.listar_historial_por_entidad(entidad.entidad_id)) == 3
    # dos series: IRPF (700001+700002, agrupadas pese a nivel3 distinto) +
    # la concesión directa (700003) en su propia serie.
    assert resumen.series_detectadas == 2

    esperadas = almacen.listar_esperadas_por_entidad(entidad.entidad_id)
    assert len(esperadas) == 2
    directa = next(e for e in esperadas if e.accionable is False)
    assert directa.ediciones_previas == 1


def test_segunda_captura_no_duplica_historial_ya_persistido():
    almacen = AlmacenMemoria()
    entidad = _entidad()

    capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    resumen_2 = capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )

    assert resumen_2.concesiones_nuevas == 0
    assert len(almacen.listar_historial_por_entidad(entidad.entidad_id)) == 3


def test_captura_usa_el_nif_verificado_de_la_entidad_no_uno_ajeno():
    almacen = AlmacenMemoria()
    entidad = _entidad(nif="NIF-QUE-NO-EXISTE")

    class _FuenteQueVerificaNif(FuenteConcesionesBDNS):
        def buscar_por_nif(self, nif, entidad_id, **kwargs):
            assert nif == "NIF-QUE-NO-EXISTE"
            return iter(())

    fuente = _FuenteQueVerificaNif(
        _TransporteStub(paginas={}, detalles={}), reloj=lambda: AHORA, generador_id=_generador_id("hist")
    )

    resumen = capturar_y_derivar_entidad(
        entidad, fuente, almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    assert resumen.concesiones_encontradas == 0


# --- reevaluar_entidad: enlace por serie, NUNCA crea Match ------------------


def _convocatoria_irpf_2026() -> Convocatoria:
    return Convocatoria(
        convocatoria_id="bdns-800001",
        fuente=Fuente(portal="BDNS", url_origen="https://x/800001", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Convocatoria de subvenciones IRPF 0,7% estatal 2026",
        beneficiarios_elegibles="Asociaciones",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 5, 15), fecha_cierre=date(2026, 6, 15)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
        region=None,
    )


def test_reevaluar_entidad_enlaza_esperada_activa_con_convocatoria_de_la_misma_serie():
    almacen = AlmacenMemoria()
    entidad = _entidad()
    capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    esperadas_antes = almacen.listar_esperadas_por_entidad(entidad.entidad_id)
    irpf_antes = next(e for e in esperadas_antes if e.accionable and e.ediciones_previas == 2)
    assert irpf_antes.estado is EstadoEsperada.ESPERADA

    resumen = reevaluar_entidad(
        entidad.entidad_id, [_convocatoria_irpf_2026()], almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 1
    assert len(resumen.contextos_enlace) == 1
    assert resumen.contextos_enlace[0].convocatoria_id == "bdns-800001"
    assert resumen.contextos_enlace[0].entidad_id == entidad.entidad_id

    irpf_despues = almacen.obtener_esperada(entidad.entidad_id, irpf_antes.serie_fingerprint, irpf_antes.anio_esperado)
    assert irpf_despues.estado is EstadoEsperada.PUBLICADA_ENLAZADA
    assert irpf_despues.convocatoria_id_enlazada == "bdns-800001"


def test_reevaluar_entidad_no_toca_matches_ni_crea_ninguno():
    """§3.6 — invariante central: el enlace NUNCA crea Match. `almacen` no
    recibe ningún match tras `reevaluar_entidad`, aunque enlace ocurra."""
    almacen = AlmacenMemoria()
    entidad = _entidad()
    capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )

    reevaluar_entidad(
        entidad.entidad_id, [_convocatoria_irpf_2026()], almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )

    assert almacen.listar_matches_por_entidad(entidad.entidad_id) == []


def test_reevaluar_entidad_sin_convocatorias_nuevas_no_enlaza_nada():
    almacen = AlmacenMemoria()
    entidad = _entidad()
    capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )

    resumen = reevaluar_entidad(
        entidad.entidad_id, [], almacen, almacen, date(2026, 3, 1),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 0
    assert resumen.esperadas_no_aparecidas == 0
    assert resumen.contextos_enlace == ()


class _FuenteUnicaStub:
    """Stub mínimo (misma interfaz que `FuenteConcesionesBDNS`) que devuelve
    UN historial ya construido — para aislar un test de un único fingerprint
    sin depender de la fixture compartida de red."""

    def __init__(self, historial) -> None:
        self._historial = historial
        self.descartados = 0

    def buscar_por_nif(self, nif, entidad_id, **kwargs):
        return iter(self._historial)


def _historial_unico_serie() -> "HistorialConcesion":
    from ongs_ai.proactivo.modelo import HistorialConcesion

    return HistorialConcesion(
        historial_id="hist-unico-1",
        entidad_id="ent-recurrentes-1",
        cod_concesion="conc-unico-1",
        nif_beneficiario="G00000001",
        fecha_concesion=date(2024, 9, 15),
        importe_centimos=100_000,
        cod_bdns_convocatoria="900001",
        titulo_convocatoria="Ayuda anual ficticia única",
        organo_nivel1="ESTADO",
        organo_nivel2="MINISTERIO FICTICIO",
        organo_nivel3=None,
        es_concesion_directa=False,
        serie_fingerprint="estado::ayuda anual ficticia unica",
        apertura_convocatoria=date(2024, 5, 10),
        capturado_en=AHORA,
    )


def test_reevaluar_entidad_marca_no_aparecida_tras_ventana_mas_margen():
    """Aislada del resto de la fixture compartida (que también trae una
    serie de concesión directa con ventana mucho más temprana): se siembra
    UN único historial de una sola serie para poder acotar el límite
    ventana+margen sin ruido de otras series."""
    almacen = AlmacenMemoria()
    entidad = _entidad()
    historial = _historial_unico_serie()

    capturar_y_derivar_entidad(
        entidad, _FuenteUnicaStub([historial]), almacen, almacen, date(2025, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    esperada = almacen.listar_esperadas_por_entidad(entidad.entidad_id)[0]
    assert (esperada.ventana_mes_inicio, esperada.ventana_mes_fin) == (5, 5)
    # ventana termina en mayo; margen 2 meses -> límite fin de julio.
    fecha_dentro_margen = date(esperada.anio_esperado, 7, 15)
    fecha_fuera_margen = date(esperada.anio_esperado, 8, 15)

    resumen_dentro = reevaluar_entidad(
        entidad.entidad_id, [], almacen, almacen, fecha_dentro_margen,
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )
    assert resumen_dentro.esperadas_no_aparecidas == 0

    resumen_fuera = reevaluar_entidad(
        entidad.entidad_id, [], almacen, almacen, fecha_fuera_margen,
        generador_id=_generador_id("esp3"), reloj=lambda: AHORA,
    )
    assert resumen_fuera.esperadas_no_aparecidas == 1

    actualizada = almacen.obtener_esperada(entidad.entidad_id, esperada.serie_fingerprint, esperada.anio_esperado)
    assert actualizada.estado is EstadoEsperada.NO_APARECIDA


# --- Congruencia territorial en el enlace (corrección A1) ------------------


def _historial_serie_autonomica(
    *, entidad_id: str, cod_concesion: str, organo_nivel2: str, titulo: str
) -> "HistorialConcesion":
    from ongs_ai.proactivo.derivacion import construir_fingerprint_serie
    from ongs_ai.proactivo.modelo import HistorialConcesion

    return HistorialConcesion(
        historial_id=f"hist-{cod_concesion}",
        entidad_id=entidad_id,
        cod_concesion=cod_concesion,
        nif_beneficiario="G00000001",
        fecha_concesion=date(2024, 5, 15),
        importe_centimos=100_000,
        cod_bdns_convocatoria=f"conv-{cod_concesion}",
        titulo_convocatoria=titulo,
        organo_nivel1="AUTONOMICA",
        organo_nivel2=organo_nivel2,
        organo_nivel3=None,
        es_concesion_directa=False,
        serie_fingerprint=construir_fingerprint_serie(organo_nivel1="AUTONOMICA", titulo=titulo),
        apertura_convocatoria=date(2024, 5, 15),
        capturado_en=AHORA,
    )


def _convocatoria_autonomica_generica(*, convocatoria_id: str, region: str | None, titulo: str) -> Convocatoria:
    return Convocatoria(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(portal="BDNS", url_origen=f"https://x/{convocatoria_id}", tipo=TipoFuente.PUBLICA_AUTONOMICA),
        objeto=titulo,
        beneficiarios_elegibles="Asociaciones",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.AUTONOMICO,
        plazos=Plazos(fecha_apertura=date(2026, 5, 15), fecha_cierre=date(2026, 6, 15)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
        region=region,
    )


_TITULO_GENERICO = "Convocatoria de subvenciones para entidades sin animo de lucro"


def test_colision_de_territorios_con_titulo_generico_no_enlaza_y_esperada_sigue_esperada():
    """Corrección del arquitecto: dos territorios distintos con el mismo
    título genérico colisionan en el fingerprint (nivel2 fuera de él). La
    entidad recibió históricamente de Illes Balears; una convocatoria de
    Granada con el mismo título genérico NO debe consumir esa esperada."""
    almacen = AlmacenMemoria()
    entidad = _entidad()
    historial = _historial_serie_autonomica(
        entidad_id=entidad.entidad_id, cod_concesion="c1",
        organo_nivel2="ILLES BALEARS", titulo=_TITULO_GENERICO,
    )
    fuente = _FuenteUnicaStub([historial])
    capturar_y_derivar_entidad(
        entidad, fuente, almacen, almacen, date(2025, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    esperada_antes = almacen.listar_esperadas_por_entidad(entidad.entidad_id)[0]
    assert esperada_antes.estado is EstadoEsperada.ESPERADA

    convocatoria_granada = _convocatoria_autonomica_generica(
        convocatoria_id="bdns-granada-2026", region="Granada", titulo=_TITULO_GENERICO,
    )
    resumen = reevaluar_entidad(
        entidad.entidad_id, [convocatoria_granada], almacen, almacen, date(2025, 6, 1),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 0
    assert resumen.contextos_enlace == ()
    esperada_despues = almacen.obtener_esperada(
        entidad.entidad_id, esperada_antes.serie_fingerprint, esperada_antes.anio_esperado
    )
    assert esperada_despues.estado is EstadoEsperada.ESPERADA
    assert esperada_despues.convocatoria_id_enlazada is None


def test_territorio_ausente_en_el_historial_permite_enlazar():
    """Serie AUTONOMICA cuyo historial NO trae `organo_nivel2` (dato
    ausente) -> territorio desconocido en ese lado -> se permite el enlace
    (conservador con el dato ausente, no con el conocido)."""
    almacen = AlmacenMemoria()
    entidad = _entidad()
    historial = _historial_serie_autonomica(
        entidad_id=entidad.entidad_id, cod_concesion="c1",
        organo_nivel2="", titulo=_TITULO_GENERICO,
    )
    historial = dataclasses.replace(historial, organo_nivel2=None)
    fuente = _FuenteUnicaStub([historial])
    capturar_y_derivar_entidad(
        entidad, fuente, almacen, almacen, date(2025, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    esperada_antes = almacen.listar_esperadas_por_entidad(entidad.entidad_id)[0]

    convocatoria_granada = _convocatoria_autonomica_generica(
        convocatoria_id="bdns-granada-2026", region="Granada", titulo=_TITULO_GENERICO,
    )
    resumen = reevaluar_entidad(
        entidad.entidad_id, [convocatoria_granada], almacen, almacen, date(2025, 6, 1),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 1
    esperada_despues = almacen.obtener_esperada(
        entidad.entidad_id, esperada_antes.serie_fingerprint, esperada_antes.anio_esperado
    )
    assert esperada_despues.estado is EstadoEsperada.PUBLICADA_ENLAZADA


def test_reevaluar_entidad_no_resucita_esperada_terminal_en_re_derivacion():
    almacen = AlmacenMemoria()
    entidad = _entidad()
    capturar_y_derivar_entidad(
        entidad, _fuente(), almacen, almacen, date(2026, 1, 1),
        generador_id=_generador_id("esp"), reloj=lambda: AHORA,
    )
    reevaluar_entidad(
        entidad.entidad_id, [_convocatoria_irpf_2026()], almacen, almacen, date(2026, 7, 21),
        generador_id=_generador_id("esp2"), reloj=lambda: AHORA,
    )
    esperadas = almacen.listar_esperadas_por_entidad(entidad.entidad_id)
    irpf_enlazada = next(e for e in esperadas if e.estado is EstadoEsperada.PUBLICADA_ENLAZADA)

    # una re-derivación posterior (misma entidad, mismo historial) NUNCA
    # debe volver esta esperada a ESPERADA.
    reevaluar_entidad(
        entidad.entidad_id, [], almacen, almacen, date(2026, 8, 1),
        generador_id=_generador_id("esp3"), reloj=lambda: AHORA,
    )

    todavia = almacen.obtener_esperada(entidad.entidad_id, irpf_enlazada.serie_fingerprint, irpf_enlazada.anio_esperado)
    assert todavia.estado is EstadoEsperada.PUBLICADA_ENLAZADA
    assert todavia.esperada_id == irpf_enlazada.esperada_id
