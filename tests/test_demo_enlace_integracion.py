"""Test de integración del camino EXACTO reportado como roto por el operador
(PROMPT-021 C1): sembrar entidad+token contra `AlmacenSQLite` en FICHERO
TEMPORAL (no `:memory:`, que oculta cualquier problema de concurrencia o
persistencia real) usando la MISMA función de orquestación que usará
`scripts/preparar_demo.py`, levantar la app apuntando a ese fichero (una
`AlmacenSQLite` distinta, como hará uvicorn en un proceso separado) y hacer
`GET /login/confirmar?token=...` -- debe crear sesión (303 a /panel + panel
accesible después).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from preparar_demo import ENTIDAD_DEMO_ID, preparar_demo  # noqa: E402

from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite  # noqa: E402
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub  # noqa: E402
from ongs_ai.web.app import crear_app  # noqa: E402

AHORA = datetime(2026, 7, 21, 18, 30, tzinfo=timezone.utc)


@pytest.fixture
def ruta_db_temporal(tmp_path):
    return tmp_path / "demo_integracion.sqlite3"


def _contador_tokens():
    contador = iter(f"token-demo-{i}" for i in range(1, 1000))
    return lambda: next(contador)


def test_enlace_de_preparar_demo_crea_sesion_contra_sqlite_en_fichero(ruta_db_temporal):
    almacen_siembra = AlmacenSQLite(ruta_db_temporal)
    resumen = preparar_demo(
        almacen_siembra,
        email_operador="operador@example.org",
        reloj=lambda: AHORA,
        generador_token=_contador_tokens(),
        base_url="http://localhost:8001",
    )
    token = resumen.token
    assert resumen.entidad_id == ENTIDAD_DEMO_ID

    # Proceso "servidor" separado: su PROPIA conexión AlmacenSQLite al MISMO
    # fichero -- justo lo que hace uvicorn tras salir el script de preparación.
    almacen_app = AlmacenSQLite(ruta_db_temporal)
    app = crear_app(
        secret_key="clave-de-test-nunca-en-produccion",
        almacen=almacen_app,
        enviador_enlace=EnviadorEnlaceAccesoStub(),
        reloj=lambda: AHORA,
    )
    client = TestClient(app)

    # PROMPT-022 B: el GET (el que imprime/envía el enlace) ya NO consume --
    # esto es justo lo que reproduce el fallo real del operador (un
    # prefetch/escáner especulativo hacía este mismo GET y gastaba el token).
    resp_get = client.get(f"/login/confirmar?token={token}")
    assert resp_get.status_code == 200

    resp_confirmar = client.post("/login/confirmar", data={"token": token}, follow_redirects=False)
    assert resp_confirmar.status_code == 303
    assert resp_confirmar.headers["location"] == "/panel"

    resp_panel = client.get("/panel")
    assert resp_panel.status_code == 200
    assert "ABAIMAR" in resp_panel.text

    # Un solo uso: repetir el mismo enlace (vía POST, que es lo que consume) ya no debe funcionar.
    resp_segunda_vez = client.post(
        "/login/confirmar", data={"token": token}, follow_redirects=False
    )
    assert resp_segunda_vez.status_code == 400
