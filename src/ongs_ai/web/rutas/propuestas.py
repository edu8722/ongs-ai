"""Acciones de la entidad sobre sus propias propuestas — aceptar/descartar
(ADR-005 §6, F-web.2). Solo LLAMA a `matching_estado.transicionar`; nunca la
modifica ni el contrato congelado.

PROPIEDAD DEL MATCH — crítico: el match se resuelve EXCLUSIVAMENTE dentro de
`almacen.listar_matches_por_entidad(entidad.entidad_id)`, jamás por un acceso
global por `match_id`. Si no aparece ahí (no existe O es de otra entidad) la
respuesta es la MISMA página 404 genérica en ambos casos — no confirma a un
atacante que el id existe.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ongs_ai.dominio.entidades import Entidad
from ongs_ai.dominio.errores import TransicionIlegalError
from ongs_ai.dominio.matching_estado import ActorAsiento, EstadoMatch, Match, transicionar
from ongs_ai.web.dependencias import entidad_actual, verificar_csrf

router = APIRouter()

_RAIZ_PLANTILLAS = Path(__file__).resolve().parent.parent / "plantillas"
_plantillas = Jinja2Templates(directory=str(_RAIZ_PLANTILLAS))

MENSAJE_MATCH_NO_DISPONIBLE = "La propuesta indicada no está disponible."


def _match_propio(request: Request, entidad: Entidad, match_id: str) -> Match | None:
    almacen = request.app.state.almacen
    for match in almacen.listar_matches_por_entidad(entidad.entidad_id):
        if match.match_id == match_id:
            return match
    return None


def _aplicar_transicion(
    request: Request, entidad: Entidad, match_id: str, a_estado: EstadoMatch, motivo: str
):
    match = _match_propio(request, entidad, match_id)
    if match is None:
        return _plantillas.TemplateResponse(
            request, "error.html", {"mensaje": MENSAJE_MATCH_NO_DISPONIBLE}, status_code=404
        )

    estado = request.app.state
    try:
        nuevo_match = transicionar(
            match,
            a_estado=a_estado,
            transicion_id=estado.generador_token(),
            motivo=motivo,
            actor=ActorAsiento.ENTIDAD,
            timestamp=estado.reloj(),
        )
    except TransicionIlegalError:
        return RedirectResponse(url="/panel?aviso=1", status_code=303)

    estado.almacen.guardar_match(nuevo_match)
    return RedirectResponse(url="/panel", status_code=303)


@router.post("/panel/propuestas/aceptar")
def aceptar_propuesta(
    request: Request,
    entidad: Entidad = Depends(entidad_actual),
    match_id: str = Form(...),
    _csrf: None = Depends(verificar_csrf),
):
    return _aplicar_transicion(
        request, entidad, match_id, EstadoMatch.ACEPTADA, "aceptada por la entidad desde el panel"
    )


@router.post("/panel/propuestas/descartar")
def descartar_propuesta(
    request: Request,
    entidad: Entidad = Depends(entidad_actual),
    match_id: str = Form(...),
    _csrf: None = Depends(verificar_csrf),
):
    return _aplicar_transicion(
        request,
        entidad,
        match_id,
        EstadoMatch.DESCARTADA,
        "descartada por la entidad desde el panel",
    )
