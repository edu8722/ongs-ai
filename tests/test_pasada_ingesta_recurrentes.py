"""Enganche del proactivo a la pasada de ingesta (ADR-007 §5/§9) —
`servicios/pasada_ingesta.py`: para cada entidad captada, enlace +
re-derivación SIN red al final de la pasada; contadores
`esperadas_enlazadas`/`esperadas_no_aparecidas`; el aviso de propuesta
existente gana una línea de contexto cuando la convocatoria acaba de
enlazarse (§3.8.1) — sin canal nuevo ni aviso duplicado; NotificadorStub
verifica que una esperada dentro de su ventana pero SIN convocatoria
enlazada NUNCA dispara un aviso.
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

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
from ongs_ai.ia.explicacion_match import ExplicadorStub
from ongs_ai.proactivo.modelo import EstadoEsperada, HistorialConcesion
from ongs_ai.servicios.notificacion import NotificadorStub
from ongs_ai.servicios.pasada_ingesta import ejecutar_pasada

AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)
HOY = date(2026, 7, 21)


def _ids():
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"id-{next(contador)}"

    return siguiente


def _entidad(entidad_id: str = "ent-1") -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal="Asociación de Prueba",
        nif="B00000000",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 5, 1),
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


def _historial_irpf(entidad_id: str) -> HistorialConcesion:
    return HistorialConcesion(
        historial_id="hist-irpf-1",
        entidad_id=entidad_id,
        cod_concesion="conc-irpf-1",
        nif_beneficiario="B00000000",
        fecha_concesion=date(2025, 9, 1),
        importe_centimos=100_000,
        cod_bdns_convocatoria="700099",
        titulo_convocatoria="Ayudas a asociaciones sin ánimo de lucro 2025",
        organo_nivel1="ESTADO",
        organo_nivel2="MINISTERIO FICTICIO",
        organo_nivel3=None,
        es_concesion_directa=False,
        serie_fingerprint="estado::ayudas a asociaciones sin animo de lucro",
        apertura_convocatoria=date(2025, 5, 1),
        capturado_en=AHORA,
    )


def _convocatoria_nueva(convocatoria_id: str = "bdns-nueva-1") -> Convocatoria:
    """Mismo fingerprint que `_historial_irpf` (nivel1=ESTADO + título tras
    quitar años), representando la edición 2026 recién ingerida."""
    return Convocatoria(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="BDNS", url_origen=f"https://bdns.example/{convocatoria_id}", tipo=TipoFuente.PUBLICA_NACIONAL
        ),
        objeto="Ayudas a asociaciones sin ánimo de lucro 2026",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 5, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.EXTRAIDA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


class _FuenteStub:
    def __init__(self, convocatorias: list[Convocatoria]) -> None:
        self._convocatorias = convocatorias

    def buscar(self, filtros=None):
        return list(self._convocatorias)


def test_pasada_sin_historial_no_enlaza_nada_y_contadores_a_cero():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    fuente = _FuenteStub([_convocatoria_nueva()])
    notificador = NotificadorStub()

    resumen = ejecutar_pasada(
        fuente, almacen, notificador, HOY, generador_ids=_ids(), reloj=lambda: AHORA
    )

    assert resumen.esperadas_enlazadas == 0
    assert resumen.esperadas_no_aparecidas == 0


def test_pasada_enlaza_esperada_activa_con_convocatoria_de_la_misma_serie():
    almacen = AlmacenMemoria()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    almacen.guardar_historial(_historial_irpf(entidad.entidad_id))

    resumen = ejecutar_pasada(
        _FuenteStub([_convocatoria_nueva()]), almacen, NotificadorStub(), HOY,
        generador_ids=_ids(), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 1
    esperadas = almacen.listar_esperadas_por_entidad(entidad.entidad_id)
    assert len(esperadas) == 1
    assert esperadas[0].estado is EstadoEsperada.PUBLICADA_ENLAZADA
    assert esperadas[0].convocatoria_id_enlazada == "bdns-nueva-1"


def test_pasada_nunca_crea_match_por_la_via_del_enlace():
    """§3.6 — el enlace NUNCA crea Match por sí mismo: una convocatoria SIN
    `fecha_cierre` se enlaza igualmente (el fingerprint no depende de
    plazos) pero NUNCA pasa la pre-puerta de `detectar_y_proponer` (exige
    `VERIFICADA` + plazo) — cero Match, pese al enlace."""
    almacen = AlmacenMemoria()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    almacen.guardar_historial(_historial_irpf(entidad.entidad_id))
    convocatoria_incompleta = dataclasses.replace(_convocatoria_nueva(), plazos=Plazos())

    resumen = ejecutar_pasada(
        _FuenteStub([convocatoria_incompleta]), almacen, NotificadorStub(), HOY,
        generador_ids=_ids(), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 1
    esperadas = almacen.listar_esperadas_por_entidad(entidad.entidad_id)
    assert esperadas[0].estado is EstadoEsperada.PUBLICADA_ENLAZADA

    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 0


def test_aviso_de_propuesta_gana_linea_de_contexto_cuando_la_convocatoria_esta_enlazada():
    almacen = AlmacenMemoria()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    almacen.guardar_historial(_historial_irpf(entidad.entidad_id))
    notificador = NotificadorStub()

    # convocatoria completa (con fecha_cierre futura) para que SÍ pase la
    # pre-puerta y llegue a detectar_y_proponer -> match+aviso reales.
    convocatoria = _convocatoria_nueva()

    resumen = ejecutar_pasada(
        _FuenteStub([convocatoria]), almacen, notificador, HOY,
        generador_explicacion=ExplicadorStub(), generador_ids=_ids(), reloj=lambda: AHORA,
    )

    assert resumen.esperadas_enlazadas == 1
    matches = almacen.listar_matches_por_entidad(entidad.entidad_id)
    assert len(matches) == 1
    assert matches[0].explicacion_ia is not None
    assert "ya está abierta de nuevo" in matches[0].explicacion_ia
    assert "2025" in matches[0].explicacion_ia
    assert len(notificador.avisos) == 1


def test_esperada_dentro_de_su_ventana_sin_convocatoria_enlazada_nunca_dispara_aviso():
    """§3.8.2 — el aviso de "ventana próxima" es SOLO panel (F-proactivo.2,
    fuera de alcance aquí): NADA en esta pasada debe enviar un aviso solo
    porque una esperada esté dentro de su ventana estimada sin una
    convocatoria real enlazada."""
    almacen = AlmacenMemoria()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    almacen.guardar_historial(_historial_irpf(entidad.entidad_id))
    notificador = NotificadorStub()

    # ninguna convocatoria nueva esta pasada -> la esperada sigue activa,
    # dentro de su ventana (mayo), sin enlazar.
    resumen = ejecutar_pasada(
        _FuenteStub([]), almacen, notificador, date(2026, 5, 15), generador_ids=_ids(), reloj=lambda: AHORA
    )

    assert resumen.esperadas_enlazadas == 0
    assert notificador.avisos == []
    esperadas = almacen.listar_esperadas_por_entidad(entidad.entidad_id)
    assert esperadas[0].estado is EstadoEsperada.ESPERADA


def test_fallo_reevaluando_una_entidad_degrada_limpio_y_la_pasada_sigue():
    class _AlmacenQueFallaEnHistorial(AlmacenMemoria):
        def listar_historial_por_entidad(self, entidad_id: str):
            if entidad_id == "ent-rota":
                raise RuntimeError("fallo simulado en repo de historial")
            return super().listar_historial_por_entidad(entidad_id)

    almacen = _AlmacenQueFallaEnHistorial()
    almacen.guardar_entidad(_entidad("ent-rota"))
    almacen.guardar_entidad(_entidad("ent-sana"))
    almacen.guardar_historial(_historial_irpf("ent-sana"))

    resumen = ejecutar_pasada(
        _FuenteStub([_convocatoria_nueva()]), almacen, NotificadorStub(), HOY,
        generador_ids=_ids(), reloj=lambda: AHORA,
    )

    # ent-rota falla y se salta; ent-sana igualmente enlaza — la pasada no se cae.
    assert resumen.esperadas_enlazadas == 1
