"""GET /consola/cruce — "a qué puede presentarse, cuántos puntos y qué
importe" para el perfil seleccionado (PROMPT-021 A1). Perfil = Entidad
captada o Prospecto candidata (ADR-006 §2.6, evaluación degradada);
desglose motivo a motivo vía `evaluar_afinidad`, ya auditado.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ongs_ai.dominio.entidades import Entidad, RequisitoFormal
from ongs_ai.servicios.afinidad import EstadoRequisito, evaluar_afinidad
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback
from ongs_ai.web.rutas.consola._soporte import (
    clave_perfil,
    crear_plantillas,
    nombre_perfil,
    obtener_perfil_por_clave,
    todos_los_perfiles,
)

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_plantillas = crear_plantillas()


def _info_perfil(perfil) -> dict:
    if isinstance(perfil, Entidad):
        return {
            "es_entidad": True,
            "forma_juridica": perfil.forma_juridica.tipo,
            "antiguedad_conocida": True,
            "ingresos_centimos": perfil.datos_economicos_ejercicio_anterior.ingresos_centimos,
            "utilidad_publica": RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA in perfil.requisitos_formales_disponibles,
        }
    return {
        "es_entidad": False,
        "forma_juridica": perfil.forma_juridica,
        "antiguedad_conocida": False,
        "ingresos_centimos": None,
        "utilidad_publica": None,
    }


@router.get("/cruce")
def cruce(request: Request, perfil: str | None = None):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    perfiles = todos_los_perfiles(almacen)
    opciones = [{"clave": clave_perfil(p), "nombre": nombre_perfil(p)} for p in perfiles]

    perfil_actual = None
    if perfil:
        perfil_actual = obtener_perfil_por_clave(almacen, perfil)
    if perfil_actual is None and perfiles:
        perfil_actual = perfiles[0]

    if perfil_actual is None:
        return _plantillas.TemplateResponse(
            request,
            "consola/cruce.html",
            {
                "vista_activa": "cruce",
                "operador_autenticado": True,
                "opciones": opciones,
                "perfil_actual": None,
            },
        )

    convocatorias = almacen.listar_convocatorias()
    evaluaciones = []
    for c in convocatorias:
        resultado = evaluar_afinidad(perfil_actual, c, hoy)
        if resultado.elegible:
            estado_cruce = "elegible"
        elif any(d.estado is EstadoRequisito.PENDIENTE_DE_DATO for d in resultado.detalle_por_requisito):
            estado_cruce = "no_evaluable"
        else:
            estado_cruce = "no_elegible"
        evaluaciones.append({"convocatoria": c, "resultado": resultado, "estado_cruce": estado_cruce})
    evaluaciones.sort(key=lambda e: (not e["resultado"].elegible, -e["resultado"].score))

    return _plantillas.TemplateResponse(
        request,
        "consola/cruce.html",
        {
            "vista_activa": "cruce",
            "operador_autenticado": True,
            "opciones": opciones,
            "perfil_actual": perfil_actual,
            "clave_perfil_actual": clave_perfil(perfil_actual),
            "nombre_perfil_actual": nombre_perfil(perfil_actual),
            "info_perfil": _info_perfil(perfil_actual),
            "evaluaciones": evaluaciones,
        },
    )
