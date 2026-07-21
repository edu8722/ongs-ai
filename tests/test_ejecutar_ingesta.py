"""Orquestación del runner de ingesta (`scripts/ejecutar_ingesta.ejecutar_pasada`)
— PROMPT-018 B2. Todo inyectado/stub: sin red (fuente stub), sin CLI real
(cliente IA stub), `AlmacenMemoria` en vez de SQLite. `scripts/` no es un
paquete instalado — se añade a `sys.path` igual que hacen los propios
scripts para importar `src/` (ver `scripts/ejecutar_ingesta.py`).
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ejecutar_ingesta import ejecutar_pasada  # noqa: E402

from ongs_ai.adapters.ingesta.bdns import (  # noqa: E402
    MOTIVO_CONCESION_DIRECTA,
    MOTIVO_NO_ABIERTA_EN_ORIGEN,
)
from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria  # noqa: E402
from ongs_ai.dominio.entidades import (  # noqa: E402
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
from ongs_ai.dominio.matching_estado import EstadoMatch  # noqa: E402
from ongs_ai.ia.explicacion_match import ExplicadorStub  # noqa: E402
from ongs_ai.servicios.notificacion import NotificadorStub  # noqa: E402

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)
HOY = date(2026, 7, 18)


class _FuenteStub:
    def __init__(self, convocatorias: list[Convocatoria]) -> None:
        self._convocatorias = convocatorias

    def buscar(self, filtros=None):
        return list(self._convocatorias)


class _ClienteIAStub:
    def __init__(self, respuestas: dict[str, str | None] | None = None, *, respuesta_defecto=None) -> None:
        self._respuestas = respuestas or {}
        self._respuesta_defecto = respuesta_defecto
        self.llamadas = 0
        self.fallos = 0
        self.preguntas: list[str] = []

    def preguntar(self, prompt: str) -> str | None:
        self.llamadas += 1
        self.preguntas.append(prompt)
        for clave, respuesta in self._respuestas.items():
            if clave in prompt:
                if respuesta is None:
                    self.fallos += 1
                return respuesta
        if self._respuesta_defecto is None:
            self.fallos += 1
        return self._respuesta_defecto


def _ids():
    contador = iter(range(1, 10_000))

    def siguiente() -> str:
        return f"id-{next(contador)}"

    return siguiente


def _reloj():
    return AHORA


def _entidad(entidad_id: str = "ent-1", **overrides) -> Entidad:
    base = dict(
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
    base.update(overrides)
    return Entidad(**base)


def _convocatoria_extraida(convocatoria_id: str = "bdns-1", **overrides) -> Convocatoria:
    base = dict(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="BDNS", url_origen=f"https://bdns.example/{convocatoria_id}", tipo=TipoFuente.PUBLICA_NACIONAL
        ),
        objeto="Ayudas a asociaciones sin ánimo de lucro",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.EXTRAIDA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    base.update(overrides)
    return Convocatoria(**base)


def test_pipeline_basico_ingesta_promociona_y_propone():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    fuente = _FuenteStub([_convocatoria_extraida()])
    notificador = NotificadorStub()
    cliente_ia = _ClienteIAStub()  # sin respuestas configuradas -> degrada, cuenta fallo

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=cliente_ia,
        generador_explicacion=ExplicadorStub(),
        max_llamadas_ia=25,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert resumen.ingestadas == 1
    assert resumen.ya_existentes == 0
    assert resumen.promovidas == 1
    assert resumen.propuestas_nuevas == 1
    assert resumen.avisos_intentados == 1
    assert len(notificador.avisos) == 1

    guardada = almacen.obtener_convocatoria("bdns-1")
    assert guardada.estado_ingesta == EstadoIngesta.VERIFICADA

    matches = almacen.listar_matches_por_entidad("ent-1")
    assert len(matches) == 1
    assert matches[0].estado_actual == EstadoMatch.PROPUESTA


def test_freno_de_llamadas_ia_detiene_extraccion_pero_la_pasada_sigue():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    convocatorias = [_convocatoria_extraida(f"bdns-{i}") for i in range(3)]
    fuente = _FuenteStub(convocatorias)
    notificador = NotificadorStub()
    cliente_ia = _ClienteIAStub()

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=cliente_ia,
        max_llamadas_ia=1,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert cliente_ia.llamadas == 1
    assert resumen.llamadas_ia_usadas == 1
    assert resumen.convocatorias_sin_ia_por_freno == 2
    # El freno de IA no bloquea la promoción determinista (campos_minimos_completos
    # no depende de requisitos_elegibilidad) ni la propuesta.
    assert resumen.promovidas == 3
    assert resumen.propuestas_nuevas == 3


def test_convocatoria_ya_existente_no_pisa_enriquecimiento_previo():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    ya_enriquecida = _convocatoria_extraida(
        requisitos_elegibilidad=RequisitosElegibilidad(forma_juridica_requerida="asociacion")
    )
    almacen.guardar_convocatoria(ya_enriquecida)

    # La fuente devuelve una versión "recién descargada" del mismo portal+url,
    # sin el enriquecimiento previo (como haría un nuevo mapeo determinista de BDNS).
    fetch_fresco = _convocatoria_extraida(requisitos_elegibilidad=RequisitosElegibilidad())
    fuente = _FuenteStub([fetch_fresco])
    notificador = NotificadorStub()
    cliente_ia = _ClienteIAStub(
        respuestas={
            "Ayudas a asociaciones": (
                '{"forma_juridica_requerida": null, "antiguedad_minima_anios": 5, '
                '"requisitos_formales_requeridos": []}'
            )
        }
    )

    ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=cliente_ia,
        max_llamadas_ia=25,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    guardada = almacen.obtener_convocatoria("bdns-1")
    assert guardada.requisitos_elegibilidad.forma_juridica_requerida == "asociacion"
    assert guardada.requisitos_elegibilidad.antiguedad_minima_anios == 5


class _GeneradorExplicacionQueUsaCliente:
    """Simula un `GeneradorExplicacion` real (como `ExplicadorClaudeCLI`) que
    consume el CLIENTE IA compartido en vez de responder de forma pura."""

    def __init__(self, cliente) -> None:
        self._cliente = cliente

    def generar(self, entidad, convocatoria, resultado) -> str:
        return self._cliente.preguntar(f"explica para {entidad.entidad_id}") or ""


def test_generador_explicacion_comparte_el_freno_con_la_extraccion():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad("ent-1"))
    almacen.guardar_entidad(_entidad("ent-2"))
    # Requisitos ya completos: la extracción NO llama al cliente, así que el
    # único consumo de freno lo hace la generación de explicación por match.
    convocatoria = _convocatoria_extraida(
        requisitos_elegibilidad=RequisitosElegibilidad(
            forma_juridica_requerida="asociacion",
            antiguedad_minima_anios=0,
            requisitos_formales_requeridos=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        )
    )
    fuente = _FuenteStub([convocatoria])
    notificador = NotificadorStub()
    cliente_ia = _ClienteIAStub(respuesta_defecto="explicación de prueba")

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=cliente_ia,
        generador_explicacion=_GeneradorExplicacionQueUsaCliente(cliente_ia),
        max_llamadas_ia=1,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert resumen.propuestas_nuevas == 2
    matches = [m for e in ("ent-1", "ent-2") for m in almacen.listar_matches_por_entidad(e)]
    explicaciones = [m.explicacion_ia for m in matches]
    assert explicaciones.count(None) == 1  # el segundo match se queda sin explicación por freno
    assert cliente_ia.llamadas == 1


class _ClienteIAQueLanza:
    """Simula un fallo inesperado del cliente IA (PROMPT-022 A3) — una
    excepción que se escapa de `preguntar` pese a las guardas de A1/A2
    (p. ej. un bug no contemplado). `ejecutar_pasada` NUNCA debe dejar que
    esto tumbe la pasada completa."""

    def __init__(self) -> None:
        self.llamadas = 0
        self.fallos = 0

    def preguntar(self, prompt: str) -> str | None:
        self.llamadas += 1
        raise RuntimeError("fallo inesperado del cliente IA")


def test_fallo_inesperado_del_cliente_ia_en_extraccion_no_tumba_la_pasada():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    fuente = _FuenteStub([_convocatoria_extraida()])
    notificador = NotificadorStub()
    cliente_ia = _ClienteIAQueLanza()

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=cliente_ia,
        max_llamadas_ia=25,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert resumen.fallos_ia_inesperados == 1
    assert resumen.enriquecidas_por_ia == 0
    # El resto de la pasada sigue: promoción determinista y propuesta no
    # dependen del enriquecimiento IA.
    assert resumen.promovidas == 1
    assert resumen.propuestas_nuevas == 1


class _GeneradorExplicacionQueLanza:
    def generar(self, entidad, convocatoria, resultado) -> str:
        raise RuntimeError("fallo inesperado del generador de explicación")


def test_fallo_inesperado_del_generador_de_explicacion_no_tumba_la_pasada():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    convocatoria = _convocatoria_extraida(
        requisitos_elegibilidad=RequisitosElegibilidad(
            forma_juridica_requerida="asociacion",
            antiguedad_minima_anios=0,
            requisitos_formales_requeridos=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        )
    )
    fuente = _FuenteStub([convocatoria])
    notificador = NotificadorStub()
    cliente_ia = _ClienteIAStub(respuesta_defecto="no debería usarse")

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=cliente_ia,
        generador_explicacion=_GeneradorExplicacionQueLanza(),
        max_llamadas_ia=25,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert resumen.fallos_ia_inesperados == 1
    assert resumen.propuestas_nuevas == 1
    matches = almacen.listar_matches_por_entidad("ent-1")
    assert matches[0].explicacion_ia is None


def test_sin_cliente_ia_la_pasada_completa_sin_ia():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    fuente = _FuenteStub([_convocatoria_extraida()])
    notificador = NotificadorStub()

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=None,
        generador_explicacion=None,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert resumen.llamadas_ia_usadas == 0
    assert resumen.promovidas == 1
    assert resumen.propuestas_nuevas == 1
    matches = almacen.listar_matches_por_entidad("ent-1")
    assert matches[0].explicacion_ia is None


def test_resumen_cuenta_descartadas_por_dominio_por_motivo():
    # PROMPT-023 B: la métrica cuenta por motivo (una convocatoria puede
    # llevar ambos a la vez, como el caso real numConv=920435).
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    no_abierta = _convocatoria_extraida(
        "bdns-no-abierta",
        estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO,
        requisitos_elegibilidad=RequisitosElegibilidad(exclusiones=(MOTIVO_NO_ABIERTA_EN_ORIGEN,)),
    )
    concesion_directa = _convocatoria_extraida(
        "bdns-concesion",
        estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO,
        requisitos_elegibilidad=RequisitosElegibilidad(exclusiones=(MOTIVO_CONCESION_DIRECTA,)),
    )
    ambos_motivos = _convocatoria_extraida(
        "bdns-ambos",
        estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO,
        requisitos_elegibilidad=RequisitosElegibilidad(
            exclusiones=(MOTIVO_NO_ABIERTA_EN_ORIGEN, MOTIVO_CONCESION_DIRECTA)
        ),
    )
    fuente = _FuenteStub([no_abierta, concesion_directa, ambos_motivos, _convocatoria_extraida()])
    notificador = NotificadorStub()

    resumen = ejecutar_pasada(
        fuente,
        almacen,
        notificador,
        HOY,
        cliente_ia=None,
        generador_explicacion=None,
        generador_ids=_ids(),
        reloj=_reloj,
    )

    assert resumen.descartadas_no_abiertas == 2
    assert resumen.descartadas_concesion_directa == 2
    # La descartada NUNCA se enriquece ni se promociona (no está EXTRAIDA).
    assert almacen.obtener_convocatoria("bdns-no-abierta").estado_ingesta == EstadoIngesta.DESCARTADA_POR_DOMINIO
