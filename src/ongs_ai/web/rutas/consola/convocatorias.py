"""GET /consola/convocatorias — listado real de convocatorias ingeridas con
filtros GET server-side (texto/ámbito/estado) — PROMPT-021 A1.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ongs_ai.dominio.entidades import AmbitoTerritorial, EstadoIngesta, normalizar_texto_comparacion
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback
from ongs_ai.web.rutas.consola._soporte import convocatoria_vigente, crear_plantillas

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_plantillas = crear_plantillas()


def _filtrar(convocatorias, *, texto: str | None, ambito: str | None, estado: str | None):
    if texto:
        texto_norm = normalizar_texto_comparacion(texto)
        convocatorias = [
            c for c in convocatorias
            if texto_norm in normalizar_texto_comparacion(c.objeto)
            or texto_norm in normalizar_texto_comparacion(c.beneficiarios_elegibles)
        ]
    if ambito:
        try:
            ambito_enum = AmbitoTerritorial(ambito)
        except ValueError:
            ambito_enum = None
        if ambito_enum is not None:
            convocatorias = [c for c in convocatorias if c.ambito_geografico is ambito_enum]
    if estado:
        try:
            estado_enum = EstadoIngesta(estado)
        except ValueError:
            estado_enum = None
        if estado_enum is not None:
            convocatorias = [c for c in convocatorias if c.estado_ingesta is estado_enum]
    return convocatorias


@router.get("/convocatorias")
def listar(request: Request, texto: str | None = None, ambito: str | None = None, estado: str | None = None):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    convocatorias = _filtrar(almacen.listar_convocatorias(), texto=texto, ambito=ambito, estado=estado)
    convocatorias = sorted(
        convocatorias,
        key=lambda c: (c.plazos.fecha_cierre is None, c.plazos.fecha_cierre or c.plazos.fecha_apertura),
    )

    filas = [
        {
            "convocatoria": c,
            "vigente": convocatoria_vigente(c, hoy),
            "dias_hasta_cierre": (c.plazos.fecha_cierre - hoy).days if c.plazos.fecha_cierre else None,
        }
        for c in convocatorias
    ]

    return _plantillas.TemplateResponse(
        request,
        "consola/convocatorias.html",
        {
            "vista_activa": "convocatorias",
            "operador_autenticado": True,
            "filas": filas,
            "ambitos": list(AmbitoTerritorial),
            "estados": list(EstadoIngesta),
            "filtro_texto": texto or "",
            "filtro_ambito": ambito or "",
            "filtro_estado": estado or "",
        },
    )
