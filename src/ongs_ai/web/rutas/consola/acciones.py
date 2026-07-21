"""POST /consola/acciones/* — el operador relanza la ingesta o recalcula
matching/propuestas SIN terminal (PROMPT-026 B3). Mismas dependencias que el
resto de la consola (`solo_loopback` + `operador_actual`). El candado
anti-doble-pasada vive en `RegistroEjecucion` (B2); aquí solo se pide el
lanzamiento y se redirige al dashboard, que siempre refleja el estado actual
(en curso / terminado / fallido) — v1 sin mensaje flash: el propio dashboard
ya comunica si el disparo fue aceptado o rechazado por el candado.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ongs_ai.servicios.estado_ejecucion import TIPO_ACTUALIZAR_CONVOCATORIAS, TIPO_RECALCULAR_REVISIONES
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback

router = APIRouter(
    prefix="/consola/acciones",
    dependencies=[Depends(solo_loopback), Depends(operador_actual)],
)


def _lanzar(request: Request, tipo: str, ejecutor) -> None:
    registro = request.app.state.registro_ejecucion
    registro.lanzar(
        tipo,
        ejecutor,
        lanzador_hilo=request.app.state.lanzador_hilo,
        reloj=request.app.state.reloj,
    )


@router.post("/actualizar-convocatorias")
def actualizar_convocatorias(request: Request):
    _lanzar(request, TIPO_ACTUALIZAR_CONVOCATORIAS, request.app.state.ejecutor_pasada_completa)
    return RedirectResponse("/consola", status_code=303)


@router.post("/recalcular-revisiones")
def recalcular_revisiones(request: Request):
    _lanzar(request, TIPO_RECALCULAR_REVISIONES, request.app.state.ejecutor_recalculo)
    return RedirectResponse("/consola", status_code=303)
