"""`RegistroEjecucion`/`EstadoPasada` (PROMPT-026 B2) en aislamiento — sin
HTTP, sin hilos reales: `lanzador_hilo` inyectado controla exactamente cuándo
"termina" el trabajo, para poder testear el CANDADO de forma determinista
(sin condiciones de carrera de un hilo real en pytest).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ongs_ai.servicios.estado_ejecucion import (
    ESTADO_EN_CURSO,
    ESTADO_FALLIDO,
    ESTADO_INACTIVO,
    ESTADO_TERMINADO,
    RegistroEjecucion,
)

T0 = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 7, 21, 10, 5, tzinfo=timezone.utc)


def _reloj_secuencial(*instantes):
    it = iter(instantes)

    def reloj():
        return next(it)

    return reloj


def _lanzador_sincrono(trabajo) -> None:
    trabajo()


class _LanzadorGrabador:
    """Guarda la función de trabajo SIN ejecutarla — simula un hilo real que
    sigue vivo hasta que el test decide "completarlo" a mano."""

    def __init__(self) -> None:
        self.trabajos = []

    def __call__(self, trabajo) -> None:
        self.trabajos.append(trabajo)


def test_estado_inicial_es_inactivo():
    registro = RegistroEjecucion()
    assert registro.estado_actual.estado == ESTADO_INACTIVO
    assert not registro.en_curso()


def test_lanzar_con_hilo_sincrono_termina_y_guarda_resumen():
    registro = RegistroEjecucion()

    lanzado = registro.lanzar(
        "actualizar_convocatorias",
        lambda: "resumen-fake",
        lanzador_hilo=_lanzador_sincrono,
        reloj=_reloj_secuencial(T0, T1),
    )

    assert lanzado is True
    assert registro.estado_actual.estado == ESTADO_TERMINADO
    assert registro.estado_actual.tipo == "actualizar_convocatorias"
    assert registro.estado_actual.inicio == T0
    assert registro.estado_actual.fin == T1
    assert registro.estado_actual.resumen == "resumen-fake"
    assert not registro.en_curso()


def test_lanzar_cuando_el_ejecutor_falla_queda_fallido_con_motivo():
    registro = RegistroEjecucion()

    def ejecutor_que_falla():
        raise RuntimeError("sin red")

    lanzado = registro.lanzar(
        "recalcular_revisiones",
        ejecutor_que_falla,
        lanzador_hilo=_lanzador_sincrono,
        reloj=_reloj_secuencial(T0, T1),
    )

    assert lanzado is True
    assert registro.estado_actual.estado == ESTADO_FALLIDO
    assert registro.estado_actual.motivo_fallo == "sin red"
    assert registro.estado_actual.resumen is None


def test_candado_rechaza_segundo_lanzamiento_mientras_hay_uno_en_curso():
    registro = RegistroEjecucion()
    lanzador = _LanzadorGrabador()

    primero = registro.lanzar(
        "actualizar_convocatorias",
        lambda: "resumen-1",
        lanzador_hilo=lanzador,
        reloj=_reloj_secuencial(T0, T1),  # T0=inicio (ya); T1=fin (al completar el hilo, más abajo)
    )
    assert primero is True
    assert registro.en_curso()

    # El "hilo" del primero no ha completado (lanzador solo lo grabó) -> el
    # segundo disparo debe rechazarse sin tocar nada.
    llamadas_al_segundo_ejecutor = []
    segundo = registro.lanzar(
        "recalcular_revisiones",
        lambda: llamadas_al_segundo_ejecutor.append(1),
        lanzador_hilo=lanzador,
        reloj=_reloj_secuencial(T1),
    )

    assert segundo is False
    assert llamadas_al_segundo_ejecutor == []  # el segundo ejecutor NUNCA se invoca
    assert registro.estado_actual.tipo == "actualizar_convocatorias"  # sigue siendo el primero
    assert len(lanzador.trabajos) == 1  # solo se registró el hilo del primero

    # Al completar el primer "hilo", el candado se libera y un tercer
    # lanzamiento sí procede.
    lanzador.trabajos[0]()
    assert registro.estado_actual.estado == ESTADO_TERMINADO

    tercero = registro.lanzar(
        "recalcular_revisiones",
        lambda: "resumen-3",
        lanzador_hilo=_lanzador_sincrono,
        reloj=_reloj_secuencial(T1, T1),
    )
    assert tercero is True
    assert registro.estado_actual.resumen == "resumen-3"
