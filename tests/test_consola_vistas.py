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
from ongs_ai.servicios.afinidad import evaluar_afinidad
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


def _convocatoria_descartada() -> Convocatoria:
    return Convocatoria(
        convocatoria_id="conv-descartada-1",
        fuente=Fuente(portal="BDNS", url_origen="https://demo.example/conv-descartada-1", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayuda nominativa descartada de la prueba",
        beneficiarios_elegibles="Entidades sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(exclusiones=("concesión directa (no concurrencia)",)),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=9_000_000),
        estado_ingesta=EstadoIngesta.DESCARTADA_POR_DOMINIO,
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


def test_convocatorias_sin_ninguna_fecha_no_revienta_el_orden():
    # Bug preexistente hallado al verificar contra la base real (~1.550
    # convocatorias): con fecha_apertura Y fecha_cierre ausentes, la clave de
    # orden comparaba date con None y reventaba. La proyección jamás lanza
    # por un dato feo (regla de oro) -> se ordena al final.
    almacen = _almacen_poblado()
    almacen.guardar_convocatoria(
        Convocatoria(
            convocatoria_id="conv-sin-fechas",
            fuente=Fuente(portal="BDNS", url_origen="https://demo.example/conv-sin-fechas", tipo=TipoFuente.PUBLICA_NACIONAL),
            objeto="Ayuda sin fechas publicadas",
            beneficiarios_elegibles="Entidades sin ánimo de lucro",
            requisitos_elegibilidad=RequisitosElegibilidad(),
            ambito_geografico=AmbitoTerritorial.NACIONAL,
            plazos=Plazos(),
            cuantias=Cuantias(),
            estado_ingesta=EstadoIngesta.EXTRAIDA,
            creado_en=T0,
            actualizado_en=T0,
        )
    )
    cliente = _cliente_loopback(almacen)

    resp = cliente.get("/consola/convocatorias")
    assert resp.status_code == 200
    assert "Ayuda sin fechas publicadas" in resp.text


def test_convocatorias_oculta_descartadas_por_defecto_y_las_muestra_bajo_demanda():
    # PROMPT-025 A2: filtro de estado con tres variantes.
    almacen = _almacen_poblado()
    almacen.guardar_convocatoria(_convocatoria_descartada())
    cliente = _cliente_loopback(almacen)

    # 1) por defecto (sin filtro de estado) -> descartadas ocultas
    resp = cliente.get("/consola/convocatorias")
    assert resp.status_code == 200
    assert "atención directa a familias" in resp.text
    assert "Ayuda nominativa descartada" not in resp.text
    assert "1 descartadas ocultas" in resp.text

    # 2) "ver también descartadas" -> aparece, con motivo visible
    resp_incluir = cliente.get("/consola/convocatorias", params={"incluir_descartadas": "1"})
    assert resp_incluir.status_code == 200
    assert "atención directa a familias" in resp_incluir.text
    assert "Ayuda nominativa descartada" in resp_incluir.text
    assert "concesión directa (no concurrencia)" in resp_incluir.text

    # 3) filtro de estado explícito "descartada_por_dominio" -> solo descartadas
    resp_estado = cliente.get("/consola/convocatorias", params={"estado": "descartada_por_dominio"})
    assert resp_estado.status_code == 200
    assert "Ayuda nominativa descartada" in resp_estado.text
    assert "atención directa a familias" not in resp_estado.text
    assert "concesión directa (no concurrencia)" in resp_estado.text


def test_dashboard_no_evalua_ni_muestra_descartadas():
    almacen = _almacen_poblado()
    almacen.guardar_convocatoria(_convocatoria_descartada())
    cliente = _cliente_loopback(almacen)

    resp = cliente.get("/consola")
    assert resp.status_code == 200
    assert "Ayudas a la atención directa a familias" in resp.text
    assert "Ayuda nominativa descartada" not in resp.text


def test_cruce_no_evalua_ni_ofrece_descartadas():
    almacen = _almacen_poblado()
    almacen.guardar_convocatoria(_convocatoria_descartada())
    cliente = _cliente_loopback(almacen)

    resp = cliente.get("/consola/cruce")
    assert resp.status_code == 200
    assert "Ayudas a la atención directa a familias" in resp.text
    assert "Ayuda nominativa descartada" not in resp.text


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


def test_cruce_muestra_badge_requisitos_sin_datos_cuando_no_hay_nada_estructurado():
    # PROMPT-023 D: `_convocatoria()` tiene `RequisitosElegibilidad()` vacía
    # (más allá del ámbito) -> el 70% de cobertura no debe leerse como certeza.
    almacen = _almacen_poblado()
    cliente = _cliente_loopback(almacen)

    resp = cliente.get("/consola/cruce")
    assert resp.status_code == 200
    assert "requisitos sin datos — revisar bases" in resp.text


def test_cruce_no_muestra_badge_cuando_hay_requisitos_estructurados():
    almacen = AlmacenMemoria()
    almacen.guardar_entidad(_entidad())
    convocatoria_con_requisitos = Convocatoria(
        convocatoria_id="conv-con-requisitos",
        fuente=Fuente(portal="BDNS", url_origen="https://demo.example/conv-con-requisitos", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayudas con requisitos estructurados",
        beneficiarios_elegibles="Entidades sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(antiguedad_minima_anios=2),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=1_000_000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=T0,
        actualizado_en=T0,
    )
    almacen.guardar_convocatoria(convocatoria_con_requisitos)
    cliente = _cliente_loopback(almacen)

    resp = cliente.get("/consola/cruce")
    assert resp.status_code == 200
    assert "requisitos sin datos — revisar bases" not in resp.text


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


# --- PROMPT-026 A: filtros server-side en todas las vistas ---


def test_entidades_filtra_por_tipo_captadas_candidatas_o_todas():
    cliente = _cliente_loopback(_almacen_poblado())

    resp_captadas = cliente.get("/consola/entidades", params={"tipo": "captadas"})
    assert "Asociación Consola de Prueba" in resp_captadas.text
    assert "Asociación Candidata de Prueba" not in resp_captadas.text

    resp_candidatas = cliente.get("/consola/entidades", params={"tipo": "candidatas"})
    assert "Asociación Candidata de Prueba" in resp_candidatas.text
    assert "Asociación Consola de Prueba" not in resp_candidatas.text

    resp_todas = cliente.get("/consola/entidades", params={"tipo": ""})
    assert "Asociación Consola de Prueba" in resp_todas.text
    assert "Asociación Candidata de Prueba" in resp_todas.text


def test_entidades_filtro_que_vacia_muestra_mensaje_correcto():
    cliente = _cliente_loopback(_almacen_poblado())

    resp = cliente.get("/consola/entidades", params={"q": "no-existe-nada"})
    assert resp.status_code == 200
    assert "Sin entidades captadas que coincidan con el filtro." in resp.text
    assert "Sin candidatas que coincidan con el filtro." in resp.text


def test_entidades_combina_texto_ccaa_y_tipo():
    cliente = _cliente_loopback(_almacen_poblado())

    # Combinación que acierta: la candidata SÍ está en Murcia.
    resp = cliente.get(
        "/consola/entidades", params={"q": "Candidata", "ccaa": "Murcia", "tipo": "candidatas"}
    )
    assert "Asociación Candidata de Prueba" in resp.text

    # Misma combinación pidiendo "captadas" -> la candidata queda fuera por tipo.
    resp_sin_tipo = cliente.get(
        "/consola/entidades", params={"q": "Candidata", "ccaa": "Murcia", "tipo": "captadas"}
    )
    assert "Asociación Candidata de Prueba" not in resp_sin_tipo.text


def test_cruce_filtra_por_estado_score_minimo_y_texto():
    almacen = _almacen_poblado()
    cliente = _cliente_loopback(almacen)
    resultado_real = evaluar_afinidad(_entidad(), _convocatoria(), HOY)
    assert resultado_real.elegible  # ancla la asunción de la que parte el resto del test

    base = {"perfil": "entidad:ent-consola-1"}

    # Estado: acierta con "elegible", vacía con "no_elegible".
    resp_elegible = cliente.get("/consola/cruce", params={**base, "estado": "elegible"})
    assert "atención directa a familias" in resp_elegible.text

    resp_no_elegible = cliente.get("/consola/cruce", params={**base, "estado": "no_elegible"})
    assert "Sin convocatorias que coincidan con el filtro." in resp_no_elegible.text
    assert "atención directa a familias" not in resp_no_elegible.text

    # Texto sobre el objeto: acierta / vacía.
    resp_texto = cliente.get("/consola/cruce", params={**base, "texto": "atención directa"})
    assert "atención directa a familias" in resp_texto.text
    resp_texto_vacio = cliente.get("/consola/cruce", params={**base, "texto": "zzz-no-existe"})
    assert "Sin convocatorias que coincidan con el filtro." in resp_texto_vacio.text

    # Score mínimo: el score real siempre pasa el propio umbral, y nunca
    # pasa un umbral un punto por encima (clamp 0-100 incluido).
    resp_score_ok = cliente.get("/consola/cruce", params={**base, "score_min": str(resultado_real.score)})
    assert "atención directa a familias" in resp_score_ok.text
    if resultado_real.score < 100:
        resp_score_alto = cliente.get(
            "/consola/cruce", params={**base, "score_min": str(resultado_real.score + 1)}
        )
        assert "Sin convocatorias que coincidan con el filtro." in resp_score_alto.text

    # Combinación acierta + combinación que vacía.
    resp_combinada = cliente.get(
        "/consola/cruce", params={**base, "estado": "elegible", "texto": "atención directa"}
    )
    assert "atención directa a familias" in resp_combinada.text
    resp_combinada_vacia = cliente.get(
        "/consola/cruce", params={**base, "estado": "elegible", "texto": "zzz-no-existe"}
    )
    assert "Sin convocatorias que coincidan con el filtro." in resp_combinada_vacia.text

    # Score inválido (no numérico) se ignora en vez de reventar.
    resp_score_invalido = cliente.get("/consola/cruce", params={**base, "score_min": "no-es-un-numero"})
    assert resp_score_invalido.status_code == 200
    assert "atención directa a familias" in resp_score_invalido.text


def test_mapa_filtra_por_ccaa_y_texto():
    cliente = _cliente_loopback(_almacen_poblado())

    resp_ccaa_ok = cliente.get("/consola/mapa", params={"ccaa": "Murcia"})
    assert "Asociación Candidata de Prueba" in resp_ccaa_ok.text

    resp_ccaa_vacio = cliente.get("/consola/mapa", params={"ccaa": "Cataluña"})
    assert "Sin candidatas que coincidan con el filtro." in resp_ccaa_vacio.text
    assert "Asociación Candidata de Prueba" not in resp_ccaa_vacio.text

    resp_texto_ok = cliente.get("/consola/mapa", params={"texto": "Candidata"})
    assert "Asociación Candidata de Prueba" in resp_texto_ok.text

    resp_texto_vacio = cliente.get("/consola/mapa", params={"texto": "zzz-no-existe"})
    assert "Sin candidatas que coincidan con el filtro." in resp_texto_vacio.text

    resp_combinado = cliente.get("/consola/mapa", params={"ccaa": "Murcia", "texto": "Candidata"})
    assert "Asociación Candidata de Prueba" in resp_combinado.text
    resp_combinado_vacio = cliente.get("/consola/mapa", params={"ccaa": "Murcia", "texto": "zzz-no-existe"})
    assert "Sin candidatas que coincidan con el filtro." in resp_combinado_vacio.text


def test_dashboard_filtra_oportunidades_por_ccaa_sin_tocar_metricas_globales():
    cliente = _cliente_loopback(_almacen_poblado())

    resp_ccaa_ok = cliente.get("/consola", params={"ccaa": "Murcia"})
    assert "Ayudas a la atención directa a familias" in resp_ccaa_ok.text

    resp_ccaa_vacio = cliente.get("/consola", params={"ccaa": "Cataluña"})
    assert "Sin oportunidades que coincidan con el filtro de CCAA." in resp_ccaa_vacio.text
    assert "Ayudas a la atención directa a familias" not in resp_ccaa_vacio.text
    # Las métricas agregadas (candidatas/entidades) NO dependen del filtro.
    assert "Candidatas" in resp_ccaa_vacio.text


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
