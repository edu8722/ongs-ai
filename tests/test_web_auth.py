"""Tests HTTP de autenticación por magic link — ADR-005 §2.2/§2.4/§6, F-web.1.

`TestClient` de FastAPI (basado en httpx, en proceso — sin abrir socket real ni
servidor, CLAUDE.md: tests herméticos). SMTP siempre stub
(`EnviadorEnlaceAccesoStub`, sin red).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite
from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    DatosEconomicos,
    Entidad,
    FormaJuridica,
    FormaJuridicaDeclarada,
    RequisitoFormal,
    TipoActividad,
)
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)


class _RelojFijo:
    """Reloj mutable inyectable — permite simular el paso del tiempo entre la
    generación y la validación de un token, sin depender de `datetime.now()`."""

    def __init__(self, ahora: datetime) -> None:
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora


def _contador_tokens():
    contador = iter(f"token-fijo-{i}" for i in range(1, 1000))
    return lambda: next(contador)


def _entidad(entidad_id: str = "ent-web-1", email: str = "contacto@example.org") -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal="Asociación Web de Prueba",
        nif="B33333333",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 1, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email=email),
        creado_en=T0,
        actualizado_en=T0,
    )


def _cliente(almacen=None, enviador=None, reloj=None):
    almacen = almacen if almacen is not None else AlmacenMemoria()
    enviador = enviador if enviador is not None else EnviadorEnlaceAccesoStub()
    reloj = reloj if reloj is not None else _RelojFijo(T0)
    app = crear_app(
        secret_key="clave-de-test-nunca-en-produccion",
        almacen=almacen,
        enviador_enlace=enviador,
        generador_token=_contador_tokens(),
        reloj=reloj,
    )
    return TestClient(app), almacen, enviador, reloj


def test_login_feliz_completo():
    client, almacen, enviador, _reloj = _cliente()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)

    resp_login = client.post("/login", data={"email": entidad.contacto.email})
    assert resp_login.status_code == 200
    assert len(enviador.enlaces) == 1
    token = enviador.enlaces[0].token

    resp_confirmar = client.get(f"/login/confirmar?token={token}", follow_redirects=False)
    assert resp_confirmar.status_code == 303
    assert resp_confirmar.headers["location"] == "/panel"

    resp_panel = client.get("/panel")
    assert resp_panel.status_code == 200
    assert entidad.nombre_legal in resp_panel.text


def test_login_feliz_completo_con_almacen_sqlite():
    """Regresión (2026-07-21): TestClient ejecuta las rutas sync en un
    threadpool -- un hilo distinto al que crea el almacén. Los demás tests de
    este módulo usan AlmacenMemoria y no lo detectaron; este cubre el hueco
    con el backend real (AlmacenSQLite en :memory:)."""
    almacen = AlmacenSQLite(":memory:")
    try:
        client, _almacen, enviador, _reloj = _cliente(almacen=almacen)
        entidad = _entidad()
        almacen.guardar_entidad(entidad)

        resp_login = client.post("/login", data={"email": entidad.contacto.email})
        assert resp_login.status_code == 200
        assert len(enviador.enlaces) == 1
        token = enviador.enlaces[0].token

        resp_confirmar = client.get(f"/login/confirmar?token={token}", follow_redirects=False)
        assert resp_confirmar.status_code == 303
        assert resp_confirmar.headers["location"] == "/panel"

        resp_panel = client.get("/panel")
        assert resp_panel.status_code == 200
        assert entidad.nombre_legal in resp_panel.text
    finally:
        almacen.cerrar()


def test_email_inexistente_misma_respuesta_y_cero_envios():
    client, almacen, enviador, _reloj = _cliente()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)

    resp_existente = client.post("/login", data={"email": entidad.contacto.email})

    client2, almacen2, enviador2, _reloj2 = _cliente()
    almacen2.guardar_entidad(_entidad())
    resp_inexistente = client2.post("/login", data={"email": "no-registrado@example.org"})

    assert resp_inexistente.status_code == resp_existente.status_code == 200
    assert resp_inexistente.text == resp_existente.text
    assert len(enviador2.enlaces) == 0
    assert len(enviador.enlaces) == 1


def test_token_ya_usado_falla_sin_sesion():
    client, almacen, enviador, _reloj = _cliente()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    client.post("/login", data={"email": entidad.contacto.email})
    token = enviador.enlaces[0].token

    client.get(f"/login/confirmar?token={token}")  # primer uso: consumido, sesión creada

    # Segundo intento con el MISMO enlace, desde un cliente sin sesión previa
    # (p. ej. el destinatario reenvía/reabre el correo en otro navegador).
    otro_cliente = TestClient(client.app)
    resp = otro_cliente.get(f"/login/confirmar?token={token}", follow_redirects=False)

    assert resp.status_code == 400

    resp_panel = otro_cliente.get("/panel", follow_redirects=False)
    assert resp_panel.status_code == 303
    assert resp_panel.headers["location"] == "/login"


def test_token_caducado_falla():
    reloj = _RelojFijo(T0)
    client, almacen, enviador, reloj = _cliente(reloj=reloj)
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    client.post("/login", data={"email": entidad.contacto.email})
    token = enviador.enlaces[0].token

    reloj.ahora = T0 + timedelta(minutes=61)  # TTL por defecto = 60 minutos
    resp = client.get(f"/login/confirmar?token={token}", follow_redirects=False)

    assert resp.status_code == 400

    resp_panel = client.get("/panel", follow_redirects=False)
    assert resp_panel.status_code == 303
    assert resp_panel.headers["location"] == "/login"


def test_token_inventado_falla():
    client, _almacen, _enviador, _reloj = _cliente()

    resp = client.get("/login/confirmar?token=token-que-nunca-existio")

    assert resp.status_code == 400

    resp_panel = client.get("/panel", follow_redirects=False)
    assert resp_panel.status_code == 303
    assert resp_panel.headers["location"] == "/login"


def test_panel_sin_sesion_redirige_a_login():
    client, _almacen, _enviador, _reloj = _cliente()

    resp = client.get("/panel", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_logout_invalida_sesion():
    client, almacen, enviador, _reloj = _cliente()
    entidad = _entidad()
    almacen.guardar_entidad(entidad)
    client.post("/login", data={"email": entidad.contacto.email})
    token = enviador.enlaces[0].token
    client.get(f"/login/confirmar?token={token}")
    assert client.get("/panel").status_code == 200

    resp_logout = client.post("/logout", follow_redirects=False)
    assert resp_logout.status_code == 303
    assert resp_logout.headers["location"] == "/login"

    resp_panel = client.get("/panel", follow_redirects=False)
    assert resp_panel.status_code == 303
    assert resp_panel.headers["location"] == "/login"
