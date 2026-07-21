"""GET /consola/entidades — lectura GLOBAL de todas las entidades captadas y
su cruce de scoring (ADR-006 §2.7). Esta es exactamente la lectura que un
tenant NUNCA debe recibir (`entidad_actual` no aparece en este módulo).
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
    euros, resto = divmod(centimos, 100)
    return f"{euros},{resto:02d} €"


_plantillas.env.filters["euros"] = _euros


@router.get("/entidades")
def listar_entidades(request: Request):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    entidades = almacen.listar_entidades()
    convocatorias = almacen.listar_convocatorias()
    resumenes = {
        entidad.entidad_id: resumen_prospeccion(entidad, convocatorias, hoy) for entidad in entidades
    }

    return _plantillas.TemplateResponse(
        request,
        "consola/entidades.html",
        {"entidades": entidades, "resumenes": resumenes},
    )
