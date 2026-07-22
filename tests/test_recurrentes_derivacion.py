"""Derivación determinista historial -> esperadas — ADR-007 §3.5. Sin LLM,
sin red: mismo historial produce siempre las mismas esperadas."""
from __future__ import annotations

from datetime import date, datetime, timezone

from ongs_ai.proactivo.derivacion import (
    congruencia_territorial,
    construir_fingerprint_serie,
    derivar_esperadas_de_entidad,
    fingerprint_desde_convocatoria,
    sumar_meses,
    territorio_convocatoria,
    territorio_serie_desde_historial,
    ultimo_dia_mes,
)
from ongs_ai.proactivo.modelo import Confianza, EstadoEsperada, HistorialConcesion
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

ENTIDAD_ID = "ent-derivacion-1"
AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _generador_id():
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"esp-{next(contador)}"

    return siguiente


def _historial(
    *,
    cod_concesion: str,
    cod_bdns_convocatoria: str,
    fecha_concesion: date,
    apertura: date | None,
    fingerprint: str = "estado|ministerio x::irpf",
    es_concesion_directa: bool = False,
    titulo: str = "IRPF 0,7% estatal",
) -> HistorialConcesion:
    return HistorialConcesion(
        historial_id=f"hist-{cod_concesion}",
        entidad_id=ENTIDAD_ID,
        cod_concesion=cod_concesion,
        nif_beneficiario="G00000001",
        fecha_concesion=fecha_concesion,
        importe_centimos=100_000,
        cod_bdns_convocatoria=cod_bdns_convocatoria,
        titulo_convocatoria=titulo,
        organo_nivel1="ESTADO",
        organo_nivel2="MINISTERIO X",
        organo_nivel3="DIRECCION GENERAL X" if apertura else "DIRECCION GENERAL Y",
        es_concesion_directa=es_concesion_directa,
        serie_fingerprint=fingerprint,
        apertura_convocatoria=apertura,
        capturado_en=AHORA,
    )


# --- Fingerprint ------------------------------------------------------------


def test_fingerprint_estable_para_misma_serie_distinto_anio():
    f1 = construir_fingerprint_serie(organo_nivel1="ESTADO", titulo="IRPF 2024")
    f2 = construir_fingerprint_serie(organo_nivel1="ESTADO", titulo="IRPF 2025")
    assert f1 == f2


def test_fingerprint_distinto_para_organo_distinto():
    f1 = construir_fingerprint_serie(organo_nivel1="ESTADO", titulo="IRPF")
    f2 = construir_fingerprint_serie(organo_nivel1="AUTONOMICA", titulo="IRPF")
    assert f1 != f2


# --- 1 edición -> BAJA -------------------------------------------------------


def test_una_sola_edicion_crea_esperada_confianza_baja():
    historial = [
        _historial(
            cod_concesion="c1", cod_bdns_convocatoria="conv-1",
            fecha_concesion=date(2024, 9, 15), apertura=date(2024, 5, 10),
        )
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    assert len(esperadas) == 1
    esperada = esperadas[0]
    assert esperada.ediciones_previas == 1
    assert esperada.confianza is Confianza.BAJA
    assert esperada.ventana_mes_inicio == esperada.ventana_mes_fin == 5
    assert esperada.anios_observados == (2024,)
    assert esperada.estado is EstadoEsperada.ESPERADA
    assert esperada.convocatoria_id_enlazada is None
    assert esperada.accionable is True


# --- >=2 ediciones agrupadas -> ALTA/MEDIA -----------------------------------


def test_tres_ediciones_meses_agrupados_confianza_alta():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2022, 8, 1), apertura=date(2022, 5, 10)),
        _historial(cod_concesion="c2", cod_bdns_convocatoria="conv-2",
                    fecha_concesion=date(2023, 8, 1), apertura=date(2023, 5, 20)),
        _historial(cod_concesion="c3", cod_bdns_convocatoria="conv-3",
                    fecha_concesion=date(2024, 8, 1), apertura=date(2024, 6, 1)),
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    assert len(esperadas) == 1
    esperada = esperadas[0]
    assert esperada.ediciones_previas == 3
    assert esperada.confianza is Confianza.ALTA
    assert (esperada.ventana_mes_inicio, esperada.ventana_mes_fin) == (5, 6)
    assert esperada.anios_observados == (2022, 2023, 2024)


def test_dos_ediciones_confianza_media_ventana_rango():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2023, 8, 1), apertura=date(2023, 5, 1)),
        _historial(cod_concesion="c2", cod_bdns_convocatoria="conv-2",
                    fecha_concesion=date(2024, 8, 1), apertura=date(2024, 6, 1)),
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    esperada = esperadas[0]
    assert esperada.confianza is Confianza.MEDIA
    assert (esperada.ventana_mes_inicio, esperada.ventana_mes_fin) == (5, 6)


def test_meses_dispersos_confianza_baja_ventana_ampliada():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2023, 3, 1), apertura=date(2023, 1, 1)),
        _historial(cod_concesion="c2", cod_bdns_convocatoria="conv-2",
                    fecha_concesion=date(2024, 9, 1), apertura=date(2024, 7, 1)),
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    esperada = esperadas[0]
    assert esperada.confianza is Confianza.BAJA
    assert (esperada.ventana_mes_inicio, esperada.ventana_mes_fin) == (1, 7)


# --- Apertura ausente -> proxy marcado, degrada confianza --------------------


def test_apertura_ausente_usa_proxy_de_fecha_concesion_y_degrada_confianza():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2022, 5, 1), apertura=date(2022, 5, 1)),
        _historial(cod_concesion="c2", cod_bdns_convocatoria="conv-2",
                    fecha_concesion=date(2023, 5, 1), apertura=date(2023, 5, 1)),
        _historial(cod_concesion="c3", cod_bdns_convocatoria="conv-3",
                    fecha_concesion=date(2024, 6, 1), apertura=None),  # proxy: mes=6 (fecha_concesion)
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    esperada = esperadas[0]
    # sin degradar sería ALTA (3 ediciones, meses 5,5,6 -> rango 1) — el
    # proxy la baja un nivel.
    assert esperada.confianza is Confianza.MEDIA


# --- Concesión directa -> no accionable --------------------------------------


def test_serie_concesion_directa_no_es_accionable():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2024, 3, 1), apertura=None, es_concesion_directa=True),
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    assert esperadas[0].accionable is False


# --- Series distintas nunca se fusionan (miss, no falso positivo) -----------


def test_fingerprints_distintos_producen_esperadas_separadas_nunca_fusionadas():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2024, 5, 1), apertura=date(2024, 5, 1),
                    fingerprint="serie-a"),
        _historial(cod_concesion="c2", cod_bdns_convocatoria="conv-2",
                    fecha_concesion=date(2024, 6, 1), apertura=date(2024, 6, 1),
                    fingerprint="serie-b"),
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    assert len(esperadas) == 2
    assert {e.ediciones_previas for e in esperadas} == {1}


# --- Misma convocatoria con 2 concesiones cuenta como 1 edición -------------


def test_dos_concesiones_de_la_misma_convocatoria_cuentan_una_sola_edicion():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2024, 5, 1), apertura=date(2024, 5, 1)),
        _historial(cod_concesion="c2", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2024, 5, 2), apertura=date(2024, 5, 1)),
    ]

    esperadas = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )

    assert len(esperadas) == 1
    assert esperadas[0].ediciones_previas == 1


# --- anio_esperado: determinista desde fecha_referencia INYECTADA ----------


def test_anio_esperado_avanza_cuando_ventanas_ya_pasaron():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2024, 8, 1), apertura=date(2024, 6, 1)),
    ]

    esperada_pronto = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2025, 1, 1),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )[0]
    esperada_tarde = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2026, 7, 21),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )[0]

    assert esperada_pronto.anio_esperado == 2025  # ventana de 2025 (mes 6) no ha pasado aún
    # a 2026-07-21 las ventanas de 2025 y 2026 (fin en junio) YA pasaron sin
    # aparecer -> el primer año pendiente es 2027.
    assert esperada_tarde.anio_esperado == 2027


def test_anio_esperado_nunca_usa_reloj_del_sistema_es_puro_de_fecha_referencia():
    historial = [
        _historial(cod_concesion="c1", cod_bdns_convocatoria="conv-1",
                    fecha_concesion=date(2020, 8, 1), apertura=date(2020, 6, 1)),
    ]

    esperada = derivar_esperadas_de_entidad(
        historial, fecha_referencia=date(2021, 1, 1),
        generador_id=_generador_id(), reloj=lambda: AHORA,
    )[0]

    assert esperada.anio_esperado == 2021


# --- Fingerprint de enlace desde una Convocatoria ya ingerida ---------------


def _convocatoria(
    *,
    tipo: TipoFuente,
    region: str | None,
    objeto: str,
    ambito: AmbitoTerritorial = AmbitoTerritorial.NACIONAL,
) -> Convocatoria:
    return Convocatoria(
        convocatoria_id="bdns-999",
        fuente=Fuente(portal="BDNS", url_origen="https://x", tipo=tipo),
        objeto=objeto,
        beneficiarios_elegibles="Asociaciones",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=ambito,
        plazos=Plazos(fecha_cierre=date(2026, 6, 1)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
        region=region,
    )


def test_fingerprint_desde_convocatoria_coincide_con_fingerprint_de_historial_nacional():
    """Caso insignia del ADR (IRPF estatal): `Convocatoria` nunca lleva
    `region` para ámbito nacional (`bdns.py`), así que el fingerprint de
    enlace NO puede exigir nivel2 — si lo exigiera, este caso jamás
    enlazaría (calibración documentada en `derivacion.py`)."""
    fp_historial = construir_fingerprint_serie(organo_nivel1="ESTADO", titulo="IRPF 0,7% estatal 2024")
    convocatoria = _convocatoria(
        tipo=TipoFuente.PUBLICA_NACIONAL, region=None, objeto="IRPF 0,7% estatal 2025"
    )

    assert fingerprint_desde_convocatoria(convocatoria) == fp_historial


# --- Congruencia territorial en el enlace (corrección A1) -------------------


def _historial_territorial(
    *, organo_nivel1: str, organo_nivel2: str | None, cod_concesion: str = "c1"
) -> HistorialConcesion:
    return HistorialConcesion(
        historial_id=f"hist-{cod_concesion}",
        entidad_id=ENTIDAD_ID,
        cod_concesion=cod_concesion,
        nif_beneficiario="G00000001",
        fecha_concesion=date(2024, 5, 1),
        importe_centimos=100_000,
        cod_bdns_convocatoria=f"conv-{cod_concesion}",
        titulo_convocatoria="Convocatoria de subvenciones para entidades sin animo de lucro",
        organo_nivel1=organo_nivel1,
        organo_nivel2=organo_nivel2,
        organo_nivel3=None,
        es_concesion_directa=False,
        serie_fingerprint="irrelevante-en-este-test",
        apertura_convocatoria=date(2024, 5, 1),
        capturado_en=AHORA,
    )


def test_territorio_serie_conocido_solo_para_autonomica_con_nivel2():
    serie = [_historial_territorial(organo_nivel1="AUTONOMICA", organo_nivel2="ILLES BALEARS")]
    assert territorio_serie_desde_historial(serie) == "illes balears"


def test_territorio_serie_desconocido_para_estado_aunque_nivel2_tenga_valor():
    """nivel2 en ESTADO es un ministerio, no una región (bdns.py) — nunca
    territorio comparable, ni siquiera con valor no vacío."""
    serie = [_historial_territorial(organo_nivel1="ESTADO", organo_nivel2="MINISTERIO FICTICIO")]
    assert territorio_serie_desde_historial(serie) is None


def test_territorio_serie_desconocido_para_local():
    serie = [_historial_territorial(organo_nivel1="LOCAL", organo_nivel2="VILAFICTICIA")]
    assert territorio_serie_desde_historial(serie) is None


def test_territorio_serie_desconocido_si_nivel2_ausente():
    serie = [_historial_territorial(organo_nivel1="AUTONOMICA", organo_nivel2=None)]
    assert territorio_serie_desde_historial(serie) is None


def test_territorio_convocatoria_nacional_es_territorio_conocido():
    conv = _convocatoria(tipo=TipoFuente.PUBLICA_NACIONAL, region=None, objeto="x")
    assert territorio_convocatoria(conv) == "nacional"


def test_territorio_convocatoria_autonomica_usa_region():
    conv = _convocatoria(
        tipo=TipoFuente.PUBLICA_AUTONOMICA, region="Granada", objeto="x",
        ambito=AmbitoTerritorial.AUTONOMICO,
    )
    assert territorio_convocatoria(conv) == "granada"


def test_congruencia_territorial_permite_si_cualquier_lado_desconocido():
    assert congruencia_territorial(None, "granada") is True
    assert congruencia_territorial("illes balears", None) is True
    assert congruencia_territorial(None, None) is True


def test_congruencia_territorial_bloquea_solo_cuando_ambos_conocidos_y_distintos():
    assert congruencia_territorial("illes balears", "granada") is False
    assert congruencia_territorial("illes balears", "illes balears") is True


# --- Helpers de fecha --------------------------------------------------------


def test_ultimo_dia_mes():
    assert ultimo_dia_mes(2024, 2) == date(2024, 2, 29)  # bisiesto
    assert ultimo_dia_mes(2025, 2) == date(2025, 2, 28)


def test_sumar_meses_cruza_anio():
    assert sumar_meses(date(2024, 11, 30), 3) == date(2025, 2, 28)
