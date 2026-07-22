"""GET /panel — panel de solo lectura sobre `servicios/panel.py::resumen_panel`
(ADR-005 §2.3/§5). El `entidad_id` sale EXCLUSIVAMENTE de `Depends(entidad_actual)`
— ningún parámetro de ruta/query/form acepta un entidad_id.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from ongs_ai.dominio.entidades import Entidad
from ongs_ai.servicios.panel import resumen_panel
from ongs_ai.servicios.panel_recurrentes import resumen_recurrentes
from ongs_ai.web.dependencias import entidad_actual, token_csrf

router = APIRouter()

_RAIZ_PLANTILLAS = Path(__file__).resolve().parent.parent / "plantillas"
_plantillas = Jinja2Templates(directory=str(_RAIZ_PLANTILLAS))

MENSAJE_AVISO_TRANSICION = (
    "No se ha podido completar la acción; es posible que ya estuviera procesada."
)


def _euros(centimos: int) -> str:
    """Formatea céntimos como euros sin pasar por float (regla de oro dinero)."""
    euros, resto = divmod(centimos, 100)
    return f"{euros},{resto:02d} €"


_plantillas.env.filters["euros"] = _euros


@router.get("/panel")
def panel(request: Request, entidad: Entidad = Depends(entidad_actual), aviso: str | None = None):
    almacen = request.app.state.almacen
    resumen = resumen_panel(entidad.entidad_id, almacen)
    recurrentes = resumen_recurrentes(entidad.entidad_id, almacen, request.app.state.reloj().date())

    cubos = (
        resumen.propuestas_pendientes,
        resumen.aceptadas,
        resumen.en_preparacion,
        resumen.presentadas,
        resumen.descartadas,
        resumen.detectadas_no_elegibles,
    )
    convocatorias = {
        match.convocatoria_id: almacen.obtener_convocatoria(match.convocatoria_id)
        for cubo in cubos
        for match in cubo
    }

    return _plantillas.TemplateResponse(
        request,
        "panel.html",
        {
            "entidad": entidad,
            "resumen": resumen,
            "recurrentes": recurrentes,
            "convocatorias": convocatorias,
            "csrf_token": token_csrf(request),
            "mensaje_aviso": MENSAJE_AVISO_TRANSICION if aviso else None,
        },
    )
