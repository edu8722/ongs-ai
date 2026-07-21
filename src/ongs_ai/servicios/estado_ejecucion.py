"""Registro en memoria de la última pasada de ingesta/recálculo lanzada desde
la consola web (PROMPT-026 B2) — v1 LOCAL MONOPUESTO: un único candado
(`threading.Lock`) compartido por las dos acciones ("actualizar convocatorias"
y "recalcular revisiones"), NO una cola de trabajos. Decisión documentada
aquí (anti-sobre-ingeniería): un solo operador, un solo proceso, las dos
acciones tocan el mismo almacén — no tiene sentido correrlas en paralelo ni
encolar una tercera petición mientras la primera sigue viva. Si esto deja de
ser cierto (multi-operador, multi-proceso), esto se rediseña con una cola de
verdad — no antes.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

ESTADO_INACTIVO = "inactivo"
ESTADO_EN_CURSO = "en_curso"
ESTADO_TERMINADO = "terminado"
ESTADO_FALLIDO = "fallido"

TIPO_ACTUALIZAR_CONVOCATORIAS = "actualizar_convocatorias"
TIPO_RECALCULAR_REVISIONES = "recalcular_revisiones"


@dataclass(frozen=True)
class EstadoPasada:
    """Snapshot inmutable del estado de la última pasada lanzada — cada
    transición crea una instancia nueva (nunca se muta in place, para que un
    lector concurrente de `RegistroEjecucion.estado_actual` nunca vea un
    estado a medio escribir)."""

    estado: str = ESTADO_INACTIVO
    tipo: str | None = None
    inicio: datetime | None = None
    fin: datetime | None = None
    resumen: object | None = None  # ResumenPasada — tipado laxo: no acopla este módulo de infraestructura al de dominio de ingesta
    motivo_fallo: str | None = None


class RegistroEjecucion:
    """Candado + estado compartido. `lanzar` es la única forma de arrancar una
    pasada: bajo el candado, o arranca y devuelve `True`, o (si ya hay una en
    curso) no toca nada y devuelve `False` (CANDADO, B2).

    `lanzador_hilo` es INYECTABLE (B5): en producción hace `threading.Thread`
    real; en tests recibe una función de prueba (p. ej. que solo registra la
    función de trabajo para que el propio test decida cuándo "termina" el
    hilo) — así el candado se testea de punta a punta sin condiciones de
    carrera ni hilos reales en pytest."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.estado_actual = EstadoPasada()

    def en_curso(self) -> bool:
        return self.estado_actual.estado == ESTADO_EN_CURSO

    def lanzar(
        self,
        tipo: str,
        ejecutor: Callable[[], object],
        *,
        lanzador_hilo: Callable[[Callable[[], None]], None],
        reloj: Callable[[], datetime],
    ) -> bool:
        if not self._lock.acquire(blocking=False):
            return False  # ya hay una pasada en curso — no se lanza nada más

        inicio = reloj()
        self.estado_actual = EstadoPasada(estado=ESTADO_EN_CURSO, tipo=tipo, inicio=inicio)

        def _trabajo() -> None:
            try:
                resumen = ejecutor()
                self.estado_actual = EstadoPasada(
                    estado=ESTADO_TERMINADO, tipo=tipo, inicio=inicio, fin=reloj(), resumen=resumen
                )
            except Exception as exc:  # degradación limpia (CLAUDE.md) — nunca tumba el hilo
                self.estado_actual = EstadoPasada(
                    estado=ESTADO_FALLIDO, tipo=tipo, inicio=inicio, fin=reloj(), motivo_fallo=str(exc)
                )
            finally:
                self._lock.release()

        lanzador_hilo(_trabajo)
        return True


def lanzador_hilo_produccion(trabajo: Callable[[], None]) -> None:
    """Único cableado real (B5): hilo de fondo de verdad, `daemon=True` para
    no bloquear el apagado del proceso si queda una pasada a medias."""
    threading.Thread(target=trabajo, daemon=True).start()
