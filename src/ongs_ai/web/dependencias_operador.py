"""Dependencias del rol OPERADOR — separadas por construcción del tenant
(ADR-006 §2.1/§2.2).

Regla dura simétrica a `web/dependencias.py::entidad_actual`: este fichero
JAMÁS se importa desde una ruta de tenant (`rutas/auth.py`, `rutas/panel.py`,
`rutas/propuestas.py`); `entidad_actual` JAMÁS se importa desde una ruta de
consola (`rutas/consola/*`). La separación es una propiedad verificable por
inspección de rutas (`tests/test_consola_estructura.py`), no disciplina de
cada handler.
"""
from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

CLAVE_SESION_OPERADOR = "operador_autenticado"


def solo_loopback(request: Request) -> None:
    """Rechaza con 404 GENÉRICO (ni siquiera revela que la ruta existe)
    cualquier petición cuyo `request.client.host` no sea localhost — defensa
    en profundidad junto al bind `--host 127.0.0.1` documentado (ADR §2.2):
    aunque alguien arranque mal el servidor, la consola no responde fuera de
    la máquina."""
    host = request.client.host if request.client is not None else None
    if host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=404)


def operador_actual(request: Request) -> None:
    """Única función que autoriza una ruta de consola. Lee EXCLUSIVAMENTE
    `session["operador_autenticado"]` — nunca `entidad_id`."""
    if not request.session.get(CLAVE_SESION_OPERADOR):
        raise HTTPException(status_code=303, headers={"Location": "/consola/login"})


def clave_operador_configurada(request: Request) -> str | None:
    """`ONGS_AI_OPERADOR_CLAVE` inyectada en `app.state` por `web/app.py`
    (única lectura del entorno, mismo patrón que `secret_key`). `None` si el
    proceso arrancó sin ella -- la consola entonces no autentica (ADR §2.2)."""
    return getattr(request.app.state, "operador_clave", None)


def comparar_clave_en_tiempo_constante(clave_configurada: str, clave_recibida: str) -> bool:
    return hmac.compare_digest(clave_configurada, clave_recibida)
