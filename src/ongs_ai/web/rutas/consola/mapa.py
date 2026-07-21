"""GET /consola/mapa — mapa de sedes de las candidatas (Prospectos) de
captación (PROMPT-021 A1). EXCEPCIÓN CONSCIENTE autorizada por el
arquitecto: Leaflet/OSM vía CDN, solo en esta plantilla de consola: degrada
limpio sin red. Las direcciones salen del campo `notas` del Prospecto si
existen; la ubicación en el mapa es el CENTROIDE de su CCAA (referencia
geográfica pública, nunca una dirección exacta inventada ni geocodificada).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request

from ongs_ai.dominio.entidades import normalizar_texto_comparacion
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback
from ongs_ai.web.rutas.consola._soporte import CENTROIDE_CCAA, coincide_texto, crear_plantillas

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback), Depends(operador_actual)])

_plantillas = crear_plantillas()


def _centroide(region: str | None) -> tuple[float, float] | None:
    if not region:
        return None
    return CENTROIDE_CCAA.get(normalizar_texto_comparacion(region))


@router.get("/mapa")
def mapa(request: Request, ccaa: str | None = None, texto: str | None = None):
    almacen = request.app.state.almacen

    ccaa_norm = normalizar_texto_comparacion(ccaa) if ccaa else None
    texto_norm = normalizar_texto_comparacion(texto) if texto else None
    prospectos = [
        p
        for p in almacen.listar_prospectos()
        if coincide_texto(p.region, ccaa_norm) and coincide_texto(p.nombre, texto_norm)
    ]

    sedes = []
    for p in prospectos:
        coordenadas = _centroide(p.region)
        sedes.append(
            {
                "prospecto_id": p.prospecto_id,
                "nombre": p.nombre,
                "region": p.region,
                "direccion_nota": p.notas,
                "web": p.web,
                "email": p.contacto.email if p.contacto else None,
                "telefono": p.contacto.telefono if p.contacto else None,
                "lat": coordenadas[0] if coordenadas else None,
                "lon": coordenadas[1] if coordenadas else None,
            }
        )

    sedes_con_ubicacion = [s for s in sedes if s["lat"] is not None]
    sedes_json = json.dumps(
        [
            {
                "id": s["prospecto_id"],
                "nombre": s["nombre"],
                "direccion_nota": s["direccion_nota"],
                "web": s["web"],
                "email": s["email"],
                "telefono": s["telefono"],
                "lat": s["lat"],
                "lon": s["lon"],
            }
            for s in sedes_con_ubicacion
        ],
        ensure_ascii=False,
    )

    return _plantillas.TemplateResponse(
        request,
        "consola/mapa.html",
        {
            "vista_activa": "mapa",
            "operador_autenticado": True,
            "sedes": sedes,
            "sedes_con_ubicacion": sedes_con_ubicacion,
            "sedes_json": sedes_json,
            "filtro_ccaa": ccaa or "",
            "filtro_texto": texto or "",
        },
    )
