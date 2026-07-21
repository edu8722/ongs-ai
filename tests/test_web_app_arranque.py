"""Guardarraíl de arranque de `_app_produccion` — PROMPT-022 A6.

Nunca arranca uvicorn real; solo llama a `_app_produccion()` con el entorno
monkeypatcheado (CLAUDE.md: tests herméticos, sin depender del .env de la
máquina). El caso sin `ONGS_AI_ENV=test` monkeypatchea `crear_app` para no
disparar las factories reales (SQLite en disco, SMTP).
"""
from __future__ import annotations

import pytest

from ongs_ai.web import app as app_modulo


def test_sin_secret_key_no_construye_nada(monkeypatch):
    monkeypatch.delenv("ONGS_AI_SECRET_KEY", raising=False)
    monkeypatch.delenv("ONGS_AI_ENV", raising=False)

    assert app_modulo._app_produccion() is None


def test_ongs_ai_env_test_con_secret_key_aborta_con_mensaje_accionable(monkeypatch):
    """Fail-first (fallo real del operador, dos veces): un `ONGS_AI_ENV=test`
    colgando de una sesión anterior no debe dejar arrancar un servidor "real"
    con almacén de memoria vacío."""
    monkeypatch.setenv("ONGS_AI_SECRET_KEY", "clave-de-test")
    monkeypatch.setenv("ONGS_AI_ENV", "test")

    with pytest.raises(RuntimeError, match="ONGS_AI_ENV=test"):
        app_modulo._app_produccion()


def test_sin_ongs_ai_env_test_construye_la_app_real(monkeypatch):
    monkeypatch.setenv("ONGS_AI_SECRET_KEY", "clave-de-test")
    monkeypatch.delenv("ONGS_AI_ENV", raising=False)
    llamada = {}

    def _crear_app_stub(**kwargs):
        llamada["ok"] = True
        return "app-sentinela"

    monkeypatch.setattr(app_modulo, "crear_app", _crear_app_stub)

    resultado = app_modulo._app_produccion()

    assert resultado == "app-sentinela"
    assert llamada == {"ok": True}
