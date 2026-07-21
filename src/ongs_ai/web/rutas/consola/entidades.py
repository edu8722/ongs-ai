"""GET /consola/entidades — candidatas (Prospectos) + entidades captadas,
buscables por nombre/CCAA (PROMPT-021 A1). Lectura GLOBAL de todas las
entidades/prospectos y su cruce de scoring (ADR-006 §2.7) — exactamente la
lectura que un tenant NUNCA debe recibir (`entidad_actual` no aparece aquí).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ongs_ai.dominio.entidades import Entidad, normalizar_texto_comparacion
from ongs_ai.servicios.afinidad import resumen_prospeccion
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback
from ongs_ai.web.rutas.consola._soporte import clave_perfil, crear_plantillas

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_plantillas = crear_plantillas()


def _coincide(perfil, *, q_norm: str | None, ccaa_norm: str | None) -> bool:
    nombre = perfil.nombre_legal if isinstance(perfil, Entidad) else perfil.nombre
    if q_norm and q_norm not in normalizar_texto_comparacion(nombre):
        return False
    if ccaa_norm:
        region = perfil.region or ""
        if ccaa_norm not in normalizar_texto_comparacion(region):
            return False
    return True


@router.get("/entidades")
def listar_entidades(request: Request, q: str | None = None, ccaa: str | None = None):
    almacen = request.app.state.almacen
    hoy = request.app.state.reloj().date()

    q_norm = normalizar_texto_comparacion(q) if q else None
    ccaa_norm = normalizar_texto_comparacion(ccaa) if ccaa else None

    entidades = [e for e in almacen.listar_entidades() if _coincide(e, q_norm=q_norm, ccaa_norm=ccaa_norm)]
    prospectos = [p for p in almacen.listar_prospectos() if _coincide(p, q_norm=q_norm, ccaa_norm=ccaa_norm)]
    convocatorias = almacen.listar_convocatorias()

    filas_entidades = [
        {
            "perfil": e,
            "clave_perfil": clave_perfil(e),
            "nombre": e.nombre_legal,
            "resumen": resumen_prospeccion(e, convocatorias, hoy),
        }
        for e in entidades
    ]
    filas_prospectos = [
        {
            "perfil": p,
            "clave_perfil": clave_perfil(p),
            "nombre": p.nombre,
            "resumen": resumen_prospeccion(p, convocatorias, hoy),
        }
        for p in prospectos
    ]

    return _plantillas.TemplateResponse(
        request,
        "consola/entidades.html",
        {
            "vista_activa": "entidades",
            "operador_autenticado": True,
            "filas_entidades": filas_entidades,
            "filas_prospectos": filas_prospectos,
            "filtro_q": q or "",
            "filtro_ccaa": ccaa or "",
        },
    )
