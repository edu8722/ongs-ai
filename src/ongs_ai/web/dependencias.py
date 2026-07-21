"""Única función autorizada a producir un `entidad_id` desde una `Request`
(ADR-005 §2.3) — la fuente exclusiva de tenant para toda ruta de dominio.

Regla dura: cualquier ruta que necesite el tenant declara
`entidad: Entidad = Depends(entidad_actual)` y usa `entidad.entidad_id`.
Ninguna ruta acepta un `entidad_id` como parámetro de query/path/form/cabecera.
Sesión ausente, corrupta, caducada o entidad inexistente -> redirect a /login,
nunca un fallback silencioso.

También vive aquí el helper CSRF (ADR-005 §4/§6, F-web.2): token aleatorio
ligado a la sesión (no a itsdangerous — la cookie de sesión ya va firmada por
`SessionMiddleware`; un segundo secreto no aporta nada aquí), comparado en
tiempo constante. Todo POST que mute estado de negocio lo exige vía
`Depends(verificar_csrf)`.
"""
from __future__ import annotations

import hmac
import secrets

from fastapi import Form, HTTPException, Request

from ongs_ai.dominio.entidades import Entidad

CAMPO_CSRF = "csrf_token"


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


def token_csrf(request: Request) -> str:
    """Genera (la primera vez) o reutiliza el token CSRF de la sesión activa.
    Se embebe como campo oculto en toda plantilla con un formulario que mute
    estado de negocio."""
    token = request.session.get(CAMPO_CSRF)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CAMPO_CSRF] = token
    return token


def verificar_csrf(request: Request, csrf_token: str | None = Form(default=None)) -> None:
    """Dependencia para todo POST que mute estado de negocio. Campo ausente o
    con valor que no coincide (comparación en tiempo constante) con el token
    de la sesión -> 403 genérico."""
    esperado = request.session.get(CAMPO_CSRF)
    if not esperado or not csrf_token or not hmac.compare_digest(esperado, csrf_token):
        raise HTTPException(status_code=403, detail="No autorizado")
