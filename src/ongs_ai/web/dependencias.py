"""Única función autorizada a producir un `entidad_id` desde una `Request`
(ADR-005 §2.3) — la fuente exclusiva de tenant para toda ruta de dominio.

Regla dura: cualquier ruta que necesite el tenant declara
`entidad: Entidad = Depends(entidad_actual)` y usa `entidad.entidad_id`.
Ninguna ruta acepta un `entidad_id` como parámetro de query/path/form/cabecera.
Sesión ausente, corrupta, caducada o entidad inexistente -> redirect a /login,
nunca un fallback silencioso.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from ongs_ai.dominio.entidades import Entidad


def entidad_actual(request: Request) -> Entidad:
    entidad_id = request.session.get("entidad_id")
    if not entidad_id:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    almacen = request.app.state.almacen
    entidad = almacen.obtener_entidad(entidad_id)
    if entidad is None:
        request.session.clear()
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    return entidad
