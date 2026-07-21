"""Tests HTTP de la consola del operador — ADR-006 §2.2/§4.1.

`TestClient` de FastAPI, hermético (sin red, sin servidor real). El host del
cliente de pruebas por defecto es `testclient` (NO loopback) — se usa
deliberadamente para probar el rechazo, y se fija `client=("127.0.0.1", N)`
para probar el camino feliz de `solo_loopback`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)

CLAVE_TEST = "clave-operador-de-test-nunca-en-produccion"


def _app(operador_clave: str | None = CLAVE_TEST, almacen=None):
    return crear_app(
        secret_key="clave-de-sesion-de-test",
        almacen=almacen if almacen is not None else AlmacenMemoria(),
        enviador_enlace=EnviadorEnlaceAccesoStub(),
        operador_clave=operador_clave,
        reloj=lambda: T0,
    )


def _cliente_loopback(app) -> TestClient:
    return TestClient(app, client=("127.0.0.1", 12345))


# --- solo_loopback -----------------------------------------------------


def test_no_loopback_recibe_404_generico_en_login():
    app = _app()
    cliente = TestClient(app)  # host por defecto "testclient", NO loopback

    resp = cliente.get("/consola/login")

    assert resp.status_code == 404


def test_no_loopback_recibe_404_en_prospectos_aunque_no_este_autenticado():
    app = _app()
    cliente = TestClient(app)

    resp = cliente.get("/consola/prospectos", follow_redirects=False)

    assert resp.status_code == 404


def test_loopback_ve_el_formulario_de_login():
    app = _app()
    cliente = _cliente_loopback(app)

    resp = cliente.get("/consola/login")

    assert resp.status_code == 200


# --- auth: sin clave / clave ok / clave incorrecta ----------------------


def test_sin_clave_configurada_la_consola_no_autentica():
    app = _app(operador_clave=None)
    cliente = _cliente_loopback(app)

    resp_login = cliente.get("/consola/login")
    assert resp_login.status_code == 404

    resp_post = cliente.post("/consola/login", data={"clave": "cualquiera"}, follow_redirects=False)
    assert resp_post.status_code == 401


def test_clave_correcta_da_acceso():
    app = _app()
    cliente = _cliente_loopback(app)

    resp = cliente.post("/consola/login", data={"clave": CLAVE_TEST}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/consola"

    resp_dashboard = cliente.get("/consola")
    assert resp_dashboard.status_code == 200


def test_clave_incorrecta_da_error_generico_sin_acceso():
    app = _app()
    cliente = _cliente_loopback(app)

    resp = cliente.post("/consola/login", data={"clave": "clave-equivocada"}, follow_redirects=False)

    assert resp.status_code == 401

    resp_prospectos = cliente.get("/consola/prospectos", follow_redirects=False)
    assert resp_prospectos.status_code == 303
    assert resp_prospectos.headers["location"] == "/consola/login"


def test_prospectos_sin_autenticar_redirige_a_login():
    app = _app()
    cliente = _cliente_loopback(app)

    resp = cliente.get("/consola/prospectos", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/consola/login"


def test_entidades_sin_autenticar_redirige_a_login():
    app = _app()
    cliente = _cliente_loopback(app)

    resp = cliente.get("/consola/entidades", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/consola/login"


def test_logout_invalida_la_sesion_de_operador():
    app = _app()
    cliente = _cliente_loopback(app)
    cliente.post("/consola/login", data={"clave": CLAVE_TEST})
    assert cliente.get("/consola/prospectos").status_code == 200

    resp_logout = cliente.post("/consola/logout", follow_redirects=False)
    assert resp_logout.status_code == 303
    assert resp_logout.headers["location"] == "/consola/login"

    resp_prospectos = cliente.get("/consola/prospectos", follow_redirects=False)
    assert resp_prospectos.status_code == 303


# --- la consola muestra el cruce (prospectos + entidades) ---------------


def test_prospectos_lista_los_prospectos_del_almacen():
    from ongs_ai.prospeccion.modelo import Prospecto

    almacen = AlmacenMemoria()
    almacen.guardar_prospecto(Prospecto(prospecto_id="prospecto-1", nombre="Asociación Consola"))
    app = _app(almacen=almacen)
    cliente = _cliente_loopback(app)
    cliente.post("/consola/login", data={"clave": CLAVE_TEST})

    resp = cliente.get("/consola/prospectos")

    assert resp.status_code == 200
    assert "Asociación Consola" in resp.text
