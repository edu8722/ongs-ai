"""GET /consola/cruce — "a qué puede presentarse, cuántos puntos y qué
importe" para el perfil seleccionado (PROMPT-021 A1). Perfil = Entidad
captada o Prospecto candidata (ADR-006 §2.6, evaluación degradada);
desglose motivo a motivo vía `evaluar_afinidad`, ya auditado.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ongs_ai.dominio.entidades import Entidad, RequisitoFormal, normalizar_texto_comparacion
from ongs_ai.servicios.afinidad import EstadoRequisito, evaluar_afinidad
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback
from ongs_ai.web.rutas.consola._soporte import (
    clave_perfil,
    coincide_texto,
    convocatorias_utiles,
    crear_plantillas,
    nombre_perfil,
    obtener_perfil_por_clave,
    todos_los_perfiles,
)

ESTADOS_CRUCE = ("elegible", "no_evaluable", "no_elegible")

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_plantillas = crear_plantillas()


def _requisitos_sin_datos(convocatoria) -> bool:
    """PROMPT-023 D — honestidad visual: sin NINGÚN requisito estructurado más
    allá del ámbito (forma jurídica, antigüedad, requisitos formales todos
    vacíos), el 70% de cobertura del scoring queda vacíamente satisfecho y
    puede leerse como certeza que no existe. Solo presentación: no cambia el
    modelo de score ni la elegibilidad (ADR-006)."""
    req = convocatoria.requisitos_elegibilidad
    return (
        req.forma_juridica_requerida is None
        and req.antiguedad_minima_anios is None
        and not req.requisitos_formales_requeridos
    )


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


def _score_min_valido(valor: str | None) -> int | None:
    """La proyección jamás lanza por un dato feo (regla de oro): un score
    mínimo no numérico o fuera de 0-100 se ignora en vez de reventar."""
    if not valor:
        return None
    try:
        numero = int(valor)
    except ValueError:
        return None
    return max(0, min(100, numero))


@router.get("/cruce")
def cruce(
    request: Request,
    perfil: str | None = None,
    estado: str | None = None,
    score_min: str | None = None,
    texto: str | None = None,
):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    perfiles = todos_los_perfiles(almacen)
    opciones = [{"clave": clave_perfil(p), "nombre": nombre_perfil(p)} for p in perfiles]

    perfil_actual = None
    if perfil:
        perfil_actual = obtener_perfil_por_clave(almacen, perfil)
    if perfil_actual is None and perfiles:
        perfil_actual = perfiles[0]

    score_min_valido = _score_min_valido(score_min)
    texto_norm = normalizar_texto_comparacion(texto) if texto else None
    filtro_activo = bool((estado and estado in ESTADOS_CRUCE) or score_min_valido is not None or texto_norm)

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

    convocatorias = convocatorias_utiles(almacen)
    evaluaciones = []
    for c in convocatorias:
        resultado = evaluar_afinidad(perfil_actual, c, hoy)
        if resultado.elegible:
            estado_cruce = "elegible"
        elif any(d.estado is EstadoRequisito.PENDIENTE_DE_DATO for d in resultado.detalle_por_requisito):
            estado_cruce = "no_evaluable"
        else:
            estado_cruce = "no_elegible"

        if estado and estado in ESTADOS_CRUCE and estado_cruce != estado:
            continue
        if score_min_valido is not None and resultado.score < score_min_valido:
            continue
        if not coincide_texto(c.objeto, texto_norm):
            continue

        evaluaciones.append(
            {
                "convocatoria": c,
                "resultado": resultado,
                "estado_cruce": estado_cruce,
                "requisitos_sin_datos": _requisitos_sin_datos(c),
            }
        )
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
            "filtro_estado": estado or "",
            "filtro_score_min": score_min or "",
            "filtro_texto": texto or "",
            "filtro_activo": filtro_activo,
        },
    )
