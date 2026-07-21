"""GET /consola/prospectos — lectura de prospectos con su cruce de scoring
(ADR-006 §2.7). Lectura GLOBAL (todos los prospectos, todas las
convocatorias) -- es el propósito del rol operador; JAMÁS usa `entidad_actual`.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from ongs_ai.servicios.afinidad import resumen_prospeccion
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_RAIZ_PLANTILLAS = Path(__file__).resolve().parent.parent.parent / "plantillas"
_plantillas = Jinja2Templates(directory=str(_RAIZ_PLANTILLAS))


def _euros(centimos: int) -> str:
    """Formatea céntimos como euros sin pasar por float (regla de oro dinero)."""
    euros, resto = divmod(centimos, 100)
    return f"{euros},{resto:02d} €"


_plantillas.env.filters["euros"] = _euros


@router.get("/prospectos")
def listar_prospectos(request: Request):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    prospectos = almacen.listar_prospectos()
    convocatorias = almacen.listar_convocatorias()
    resumenes = {
        prospecto.prospecto_id: resumen_prospeccion(prospecto, convocatorias, hoy)
        for prospecto in prospectos
    }

    return _plantillas.TemplateResponse(
        request,
        "consola/prospectos.html",
        {"prospectos": prospectos, "resumenes": resumenes},
    )
