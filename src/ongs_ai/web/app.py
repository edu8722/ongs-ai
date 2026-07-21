"""App FastAPI — ÚNICO fichero central (CLAUDE.md: "fichero central solo gana
includes"). Crea la app, monta el middleware de sesión, incluye los routers de
cada feature. SIN lógica de negocio.

`ONGS_AI_SECRET_KEY` se lee SOLO aquí, nunca en un adapter/servicio. En tests
se inyecta explícita vía `crear_app(secret_key=...)`, nunca del .env de la
máquina. Sesión: cookie firmada (itsdangerous vía SessionMiddleware),
`max_age` = 30 días (decisión del operador, ADR-005 §7).
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from ongs_ai.adapters.avisos.factory import crear_enviador_enlace_acceso
from ongs_ai.adapters.persistencia.factory import crear_almacen
from ongs_ai.web.rutas import auth, panel

SEGUNDOS_SESION_30_DIAS = 60 * 60 * 24 * 30
TTL_TOKEN_DEFECTO = timedelta(minutes=60)


def _reloj_utc() -> datetime:
    return datetime.now(timezone.utc)


def _generador_token_defecto() -> str:
    return secrets.token_urlsafe(32)


def crear_app(
    *,
    secret_key: str | None = None,
    almacen=None,
    enviador_enlace=None,
    generador_token: Callable[[], str] | None = None,
    reloj: Callable[[], datetime] | None = None,
    ttl_token: timedelta = TTL_TOKEN_DEFECTO,
) -> FastAPI:
    """`secret_key`/`almacen`/`enviador_enlace`/`generador_token`/`reloj` son
    inyectables (CLAUDE.md: ids/reloj siempre inyectados) — en producción se
    resuelven vía las factories por entorno; en tests SIEMPRE se pasan
    explícitos (AlmacenMemoria, EnviadorEnlaceAccesoStub, reloj/token fijos)."""
    clave = secret_key if secret_key is not None else os.environ["ONGS_AI_SECRET_KEY"]

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key=clave, max_age=SEGUNDOS_SESION_30_DIAS)

    app.state.almacen = almacen if almacen is not None else crear_almacen()
    app.state.enviador_enlace = (
        enviador_enlace if enviador_enlace is not None else crear_enviador_enlace_acceso()
    )
    app.state.generador_token = generador_token or _generador_token_defecto
    app.state.reloj = reloj or _reloj_utc
    app.state.ttl_token = ttl_token

    app.include_router(auth.router)
    app.include_router(panel.router)
    return app


def _app_produccion() -> FastAPI | None:
    """Solo construye la app real si el proceso arranca con `ONGS_AI_SECRET_KEY`
    ya en el entorno. Decisión conservadora documentada (F-web.1): evita que la
    mera importación de este módulo (p. ej. un test que solo necesita
    `crear_app`) dispare las factories reales (SQLite en disco, SMTP) sin que
    nadie lo haya pedido — los tests nunca dependen del .env de la máquina
    (CLAUDE.md). En despliegue real, el operador define `ONGS_AI_SECRET_KEY`
    (y el resto de variables `ONGS_AI_SMTP_*`/`ONGS_AI_APP_BASE_URL`) antes de
    arrancar uvicorn."""
    if "ONGS_AI_SECRET_KEY" not in os.environ:
        return None
    return crear_app()


app = _app_produccion()
