"""Tests HTTP de las acciones del operador desde la web (PROMPT-026 B):
POST /consola/acciones/actualizar-convocatorias y /recalcular-revisiones.
`lanzador_hilo`/`ejecutor_pasada_completa`/`ejecutor_recalculo` SIEMPRE
inyectados como stubs síncronos (B5) — ningún test real toca red, CLI ni
hilos de verdad.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.servicios.pasada_ingesta import ResumenPasada
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)
CLAVE_TEST = "clave-operador-de-test-nunca-en-produccion"


def _resumen_fake(**overrides) -> ResumenPasada:
    base = dict(
        ingestadas=5,
        ya_existentes=2,
        enriquecidas_por_ia=3,
        promovidas=1,
        esperadas_enlazadas=0,
        esperadas_no_aparecidas=0,
        propuestas_nuevas=4,
        propuestas_sobrevenidas=0,
        avisos_intentados=4,
        no_elegibles_persistidas=0,
        saltadas_pre_puerta=0,
        llamadas_ia_usadas=3,
        convocatorias_sin_ia_por_freno=0,
        fallos_ia_inesperados=0,
        descartadas_no_abiertas=0,
        descartadas_concesion_directa=0,
    )
    base.update(overrides)
    return ResumenPasada(**base)


class _LanzadorGrabador:
    """No ejecuta el trabajo — lo guarda para que el test decida cuándo
    "termina el hilo" (permite testear el candado sin condiciones de carrera)."""

    def __init__(self) -> None:
        self.trabajos = []

    def __call__(self, trabajo) -> None:
        self.trabajos.append(trabajo)


def _lanzador_sincrono(trabajo) -> None:
    trabajo()


def _app(*, ejecutor_pasada_completa=None, ejecutor_recalculo=None, lanzador_hilo=None):
    return crear_app(
        secret_key="clave-de-sesion-de-test",
        almacen=AlmacenMemoria(),
        enviador_enlace=EnviadorEnlaceAccesoStub(),
        operador_clave=CLAVE_TEST,
        reloj=lambda: T0,
        ejecutor_pasada_completa=ejecutor_pasada_completa or (lambda: _resumen_fake()),
        ejecutor_recalculo=ejecutor_recalculo or (lambda: _resumen_fake(ingestadas=0)),
        lanzador_hilo=lanzador_hilo or _lanzador_sincrono,
    )


def _cliente_loopback(app) -> TestClient:
    cliente = TestClient(app, client=("127.0.0.1", 12345))
    cliente.post("/consola/login", data={"clave": CLAVE_TEST})
    return cliente


def test_actualizar_convocatorias_lanza_y_el_dashboard_muestra_el_resumen():
    app = _app(ejecutor_pasada_completa=lambda: _resumen_fake(ingestadas=7, propuestas_nuevas=2))
    cliente = _cliente_loopback(app)

    resp = cliente.post("/consola/acciones/actualizar-convocatorias", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/consola"

    resp_dashboard = cliente.get("/consola")
    assert resp_dashboard.status_code == 200
    assert "Actualizar convocatorias" in resp_dashboard.text
    assert "Terminado en" in resp_dashboard.text


def test_recalcular_revisiones_llama_al_ejecutor_de_recalculo_no_al_de_ingesta():
    llamadas_ingesta = []
    llamadas_recalculo = []
    app = _app(
        ejecutor_pasada_completa=lambda: (llamadas_ingesta.append(1), _resumen_fake())[1],
        ejecutor_recalculo=lambda: (llamadas_recalculo.append(1), _resumen_fake(ingestadas=0))[1],
    )
    cliente = _cliente_loopback(app)

    resp = cliente.post("/consola/acciones/recalcular-revisiones", follow_redirects=False)
    assert resp.status_code == 303

    assert llamadas_recalculo == [1]
    assert llamadas_ingesta == []
    assert app.state.registro_ejecucion.estado_actual.tipo == "recalcular_revisiones"


def test_candado_rechaza_segunda_accion_mientras_la_primera_sigue_en_curso():
    lanzador = _LanzadorGrabador()
    llamadas_recalculo = []
    app = _app(
        ejecutor_recalculo=lambda: (llamadas_recalculo.append(1), _resumen_fake())[1],
        lanzador_hilo=lanzador,
    )
    cliente = _cliente_loopback(app)

    resp1 = cliente.post("/consola/acciones/actualizar-convocatorias", follow_redirects=False)
    assert resp1.status_code == 303
    assert app.state.registro_ejecucion.en_curso()

    # Segundo disparo (de la OTRA acción) mientras el primero sigue "en curso"
    # (el hilo grabado aún no se ha ejecutado) -> rechazado sin tocar nada.
    resp2 = cliente.post("/consola/acciones/recalcular-revisiones", follow_redirects=False)
    assert resp2.status_code == 303  # redirige igual — el dashboard sigue mostrando "en curso"
    assert llamadas_recalculo == []  # el ejecutor de recálculo NUNCA se invocó
    assert app.state.registro_ejecucion.estado_actual.tipo == "actualizar_convocatorias"
    assert len(lanzador.trabajos) == 1

    resp_dashboard = cliente.get("/consola")
    assert "En curso" in resp_dashboard.text

    # Al completar el primer "hilo", el candado se libera y un tercer disparo
    # sí procede (`lanzador_hilo` sigue siendo el grabador para toda la app —
    # se completa "a mano" igual que el primero).
    lanzador.trabajos[0]()
    resp3 = cliente.post("/consola/acciones/recalcular-revisiones", follow_redirects=False)
    assert resp3.status_code == 303
    assert len(lanzador.trabajos) == 2
    lanzador.trabajos[1]()
    assert llamadas_recalculo == [1]


def test_acciones_exigen_loopback():
    app = _app()
    cliente = TestClient(app)  # host "testclient", NO loopback

    resp = cliente.post("/consola/acciones/actualizar-convocatorias", follow_redirects=False)
    assert resp.status_code == 404


def test_acciones_exigen_operador_autenticado():
    app = _app()
    cliente = TestClient(app, client=("127.0.0.1", 12345))  # loopback, SIN login

    resp = cliente.post("/consola/acciones/recalcular-revisiones", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/consola/login"
