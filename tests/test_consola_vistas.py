"""Tests HTTP de las vistas nuevas de la consola (PROMPT-021 A): dashboard,
convocatorias, entidades unificadas, cruce y mapa. `TestClient`, hermético
(sin red, sin servidor real) — el CDN de Leaflet en `mapa.html` no se carga
en estos tests (jsdom/red ausentes), lo que además ancla la degradación
limpia sin red descrita en la plantilla.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    Convocatoria,
    Cuantias,
    DatosEconomicos,
    Entidad,
    EstadoIngesta,
    FormaJuridica,
    FormaJuridicaDeclarada,
    Fuente,
    Plazos,
    RequisitoFormal,
    RequisitosElegibilidad,
    TipoActividad,
    TipoFuente,
)
from ongs_ai.prospeccion.modelo import Prospecto
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)
HOY = date(2026, 7, 21)
CLAVE_TEST = "clave-operador-de-test-nunca-en-produccion"


def _entidad() -> Entidad:
    return Entidad(
        entidad_id="ent-consola-1",
        nombre_legal="Asociación Consola de Prueba",
        nif="B11111111",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 1, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.ATENCION_DIRECTA_A_FAMILIAS),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=5_000_000, gastos_centimos=4_800_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email="contacto@consola.example.org"),
        creado_en=T0,
        actualizado_en=T0,
        region="Región de Murcia",
        provincia="Murcia",
    )


def _convocatoria() -> Convocatoria:
    return Convocatoria(
        convocatoria_id="conv-consola-1",
        fuente=Fuente(portal="BDNS", url_origen="https://demo.example/conv-consola-1", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayudas a la atención directa a familias con enfermedades raras",
        beneficiarios_elegibles="Entidades sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=1_000_000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=T0,
        actualizado_en=T0,
    )


def _prospecto() -> Prospecto:
    return Prospecto(
        prospecto_id="prospecto-consola-1",
        nombre="Asociación Candidata de Prueba",
        region="Región de Murcia",
        enfermedad_o_colectivo="colectivo candidato",
        contacto=Contacto(email="candidata@example.org"),
        notas="C/ Ejemplo 1, 30001 Murcia",
    )


def _cliente_loopback(almacen) -> TestClient:
    app = crear_app(
        secret_key="clave-de-sesion-de-test",
        almacen=almacen,
        enviador_enlace=EnviadorEnlaceAccesoStub(),
        operador_clave=CLAVE_TEST,
        reloj=lambda: T0,
    )
    cliente = TestClient(app, client=("127.0.0.1", 12345))
    cliente.post("/consola/login", data={"clave": CLAVE_TEST})
    return cliente


def _almacen_poblado() -> AlmacenMemoria:
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    almacen.guardar_convocatoria(_convocatoria())
    almacen.guardar_prospecto(_prospecto())
    return almacen


def test_estatico_consola_css_se_sirve():
    cliente = _cliente_loopback(AlmacenMemoria())
    resp = cliente.get("/consola/estaticos/consola.css")
    assert resp.status_code == 200
    assert "--accent" in resp.text


def test_dashboard_muestra_metricas_y_oportunidad():
    cliente = _cliente_loopback(_almacen_poblado())
    resp = cliente.get("/consola")
    assert resp.status_code == 200
    assert "Candidatas" in resp.text
    assert "Ayudas a la atención directa a familias" in resp.text


def test_convocatorias_lista_y_filtra_por_texto():
    cliente = _cliente_loopback(_almacen_poblado())
    resp = cliente.get("/consola/convocatorias")
    assert resp.status_code == 200
    assert "atención directa a familias" in resp.text

    resp_filtrado = cliente.get("/consola/convocatorias", params={"texto": "no-existe-nada"})
    assert resp_filtrado.status_code == 200
    assert "Sin convocatorias que coincidan" in resp_filtrado.text

    resp_ambito = cliente.get("/consola/convocatorias", params={"ambito": "nacional"})
    assert "atención directa a familias" in resp_ambito.text


def test_entidades_unificada_muestra_captadas_y_candidatas():
    cliente = _cliente_loopback(_almacen_poblado())
    resp = cliente.get("/consola/entidades")
    assert resp.status_code == 200
    assert "Asociación Consola de Prueba" in resp.text
    assert "Asociación Candidata de Prueba" in resp.text

    resp_filtrado = cliente.get("/consola/entidades", params={"q": "Candidata"})
    assert "Asociación Candidata de Prueba" in resp_filtrado.text
    assert "Asociación Consola de Prueba" not in resp_filtrado.text


def test_cruce_por_defecto_y_por_perfil_explicito():
    almacen = _almacen_poblado()
    cliente = _cliente_loopback(almacen)

    resp = cliente.get("/consola/cruce")
    assert resp.status_code == 200
    assert "Ayudas a la atención directa a familias" in resp.text

    resp_prospecto = cliente.get("/consola/cruce", params={"perfil": "prospecto:prospecto-consola-1"})
    assert resp_prospecto.status_code == 200
    assert "Asociación Candidata de Prueba" in resp_prospecto.text
    assert "Candidata (prospecto)" in resp_prospecto.text


def test_cruce_sin_perfiles_no_revienta():
    cliente = _cliente_loopback(AlmacenMemoria())
    resp = cliente.get("/consola/cruce")
    assert resp.status_code == 200
    assert "Sin entidades ni candidatas" in resp.text


def test_mapa_lista_sedes_con_centroide_ccaa():
    cliente = _cliente_loopback(_almacen_poblado())
    resp = cliente.get("/consola/mapa")
    assert resp.status_code == 200
    assert "Asociación Candidata de Prueba" in resp.text
    assert "C/ Ejemplo 1, 30001 Murcia" in resp.text


def test_mapa_vacio_no_revienta():
    cliente = _cliente_loopback(AlmacenMemoria())
    resp = cliente.get("/consola/mapa")
    assert resp.status_code == 200
    assert "Sin prospectos importados" in resp.text


def test_rutas_nuevas_de_consola_exigen_loopback():
    almacen = _almacen_poblado()
    app = crear_app(
        secret_key="clave-de-sesion-de-test",
        almacen=almacen,
        enviador_enlace=EnviadorEnlaceAccesoStub(),
        operador_clave=CLAVE_TEST,
        reloj=lambda: T0,
    )
    cliente = TestClient(app)  # host "testclient", NO loopback
    for ruta in ("/consola", "/consola/convocatorias", "/consola/cruce", "/consola/mapa"):
        resp = cliente.get(ruta, follow_redirects=False)
        assert resp.status_code == 404, ruta
