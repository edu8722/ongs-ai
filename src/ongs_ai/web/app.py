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
from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from ongs_ai.adapters.avisos.factory import crear_enviador_enlace_acceso
from ongs_ai.adapters.persistencia.factory import crear_almacen
from ongs_ai.web.rutas import auth, panel, propuestas
from ongs_ai.web.rutas.consola import auth as consola_auth
from ongs_ai.web.rutas.consola import convocatorias as consola_convocatorias
from ongs_ai.web.rutas.consola import cruce as consola_cruce
from ongs_ai.web.rutas.consola import entidades as consola_entidades
from ongs_ai.web.rutas.consola import mapa as consola_mapa
from ongs_ai.web.rutas.consola import panel as consola_panel
from ongs_ai.web.rutas.consola import prospectos as consola_prospectos

SEGUNDOS_SESION_30_DIAS = 60 * 60 * 24 * 30
TTL_TOKEN_DEFECTO = timedelta(minutes=60)
_RAIZ_ESTATICOS_CONSOLA = Path(__file__).resolve().parent / "estaticos"


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
    operador_clave: str | None = None,
) -> FastAPI:
    """`secret_key`/`almacen`/`enviador_enlace`/`generador_token`/`reloj`/
    `operador_clave` son inyectables (CLAUDE.md: ids/reloj siempre
    inyectados) — en producción se resuelven vía las factories por entorno o
    `ONGS_AI_OPERADOR_CLAVE`; en tests SIEMPRE se pasan explícitos
    (AlmacenMemoria, EnviadorEnlaceAccesoStub, reloj/token fijos, clave de
    operador de prueba)."""
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
    # ADR-006 §2.2: sin clave configurada, la consola del operador no autentica
    # (no rompe el arranque del tenant por ello) — leída SOLO aquí, como secret_key.
    app.state.operador_clave = (
        operador_clave if operador_clave is not None else os.environ.get("ONGS_AI_OPERADOR_CLAVE")
    )

    # StaticFiles SOLO para la consola (PROMPT-021 A1) — nunca montado bajo
    # una ruta de tenant.
    app.mount(
        "/consola/estaticos",
        StaticFiles(directory=str(_RAIZ_ESTATICOS_CONSOLA)),
        name="consola_estaticos",
    )

    app.include_router(auth.router)
    app.include_router(panel.router)
    app.include_router(propuestas.router)
    app.include_router(consola_auth.router)
    app.include_router(consola_panel.router)
    app.include_router(consola_prospectos.router)
    app.include_router(consola_entidades.router)
    app.include_router(consola_convocatorias.router)
    app.include_router(consola_cruce.router)
    app.include_router(consola_mapa.router)
    return app


def _app_produccion() -> FastAPI | None:
    """Solo construye la app real si el proceso arranca con `ONGS_AI_SECRET_KEY`
    ya en el entorno. Decisión conservadora documentada (F-web.1): evita que la
    mera importación de este módulo (p. ej. un test que solo necesita
    `crear_app`) dispare las factories reales (SQLite en disco, SMTP) sin que
    nadie lo haya pedido — los tests nunca dependen del .env de la máquina
    (CLAUDE.md). En despliegue real, el operador define `ONGS_AI_SECRET_KEY`
    (y el resto de variables `ONGS_AI_SMTP_*`/`ONGS_AI_APP_BASE_URL`) antes de
    arrancar uvicorn.

    Guardarraíl de arranque (A6, fallo real del operador -- dos veces): con
    `ONGS_AI_SECRET_KEY` puesta pero `ONGS_AI_ENV=test` colgando de una
    sesión anterior, `crear_almacen()` (factory) montaría un `AlmacenMemoria`
    VACÍO para un servidor que se cree en producción -- todo enlace mágico
    daría 400 porque la entidad/token que sembró otro proceso nunca llegó a
    esta base. Un servidor "real" con almacén de memoria es siempre un error
    del operador, jamás una intención; se aborta con mensaje accionable en
    vez de arrancar en un estado que solo confunde."""
    if "ONGS_AI_SECRET_KEY" not in os.environ:
        return None
    if os.environ.get("ONGS_AI_ENV") == "test":
        raise RuntimeError(
            "ONGS_AI_ENV=test detectado: el servidor real usaría un almacén de "
            "MEMORIA vacío y todos los enlaces darían 400. Ejecuta "
            "`set ONGS_AI_ENV=` y relanza."
        )
    return crear_app()


app = _app_produccion()
