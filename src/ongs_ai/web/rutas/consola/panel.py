"""GET /consola — dashboard del operador (PROMPT-021 A1): métricas agregadas +
"Oportunidades más afines ahora". Lectura GLOBAL vía los servicios ya
auditados (`resumen_prospeccion`/`evaluar_afinidad`/`listar_*`) — nada
hardcodeado, nada sintético.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ongs_ai.dominio.entidades import normalizar_texto_comparacion
from ongs_ai.servicios.afinidad import resumen_prospeccion
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback
from ongs_ai.web.rutas.consola._soporte import (
    clave_perfil,
    coincide_texto,
    convocatoria_vigente,
    convocatorias_utiles,
    crear_plantillas,
    mejores_cruces,
    nombre_perfil,
)

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_plantillas = crear_plantillas()


@router.get("")
def dashboard(request: Request, ccaa: str | None = None):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    entidades = almacen.listar_entidades()
    prospectos = almacen.listar_prospectos()
    convocatorias_todas = almacen.listar_convocatorias()
    convocatorias = convocatorias_utiles(almacen)
    numero_descartadas = len(convocatorias_todas) - len(convocatorias)
    perfiles = [*entidades, *prospectos]

    resumenes = [resumen_prospeccion(perfil, convocatorias, hoy) for perfil in perfiles]
    importe_potencial_agregado = sum(r.importe_potencial_maximo_centimos for r in resumenes)
    convocatorias_vivas = sum(1 for c in convocatorias if convocatoria_vigente(c, hoy))

    # A4: el filtro de CCAA solo afecta a "oportunidades más afines" — las
    # métricas agregadas de arriba siguen siendo GLOBALES.
    ccaa_norm = normalizar_texto_comparacion(ccaa) if ccaa else None
    perfiles_para_oportunidades = [p for p in perfiles if coincide_texto(p.region, ccaa_norm)]

    cruces = mejores_cruces(perfiles_para_oportunidades, convocatorias, hoy, limite=6)
    oportunidades = [
        {
            "perfil_nombre": nombre_perfil(perfil),
            "clave_perfil": clave_perfil(perfil),
            "convocatoria": convocatoria,
            "resultado": resultado,
        }
        for perfil, convocatoria, resultado in cruces
    ]

    return _plantillas.TemplateResponse(
        request,
        "consola/panel.html",
        {
            "vista_activa": "resumen",
            "operador_autenticado": True,
            "numero_candidatas": len(prospectos),
            "numero_entidades": len(entidades),
            "convocatorias_vivas": convocatorias_vivas,
            "importe_potencial_agregado": importe_potencial_agregado,
            "oportunidades": oportunidades,
            "numero_descartadas": numero_descartadas,
            "filtro_ccaa": ccaa or "",
            "estado_ejecucion": request.app.state.registro_ejecucion.estado_actual,
        },
    )
