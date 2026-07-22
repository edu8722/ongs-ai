"""Tests HTTP del panel de solo lectura (`GET /panel`) — ADR-005 §2.3/§2.4/§6, F-web.1.

`TestClient` de FastAPI, SMTP siempre stub (CLAUDE.md: tests herméticos).
"""
from __future__ import annotations

import dataclasses
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
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    EstadoMatch,
    ResultadoElegibilidad,
    crear_match,
    transicionar,
)
from ongs_ai.proactivo.modelo import Confianza, ConvocatoriaEsperada, EstadoEsperada, HistorialConcesion
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app

T0 = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _entidad(entidad_id: str, email: str, nombre: str) -> Entidad:
    return Entidad(
        entidad_id=entidad_id,
        nombre_legal=nombre,
        nif="B44444444",
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


def _convocatoria(convocatoria_id: str, objeto: str) -> Convocatoria:
    return Convocatoria(
        convocatoria_id=convocatoria_id,
        fuente=Fuente(
            portal="portal-panel", url_origen=f"https://example.org/{convocatoria_id}",
            tipo=TipoFuente.PUBLICA_NACIONAL,
        ),
        objeto=objeto,
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=500_000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=T0,
        actualizado_en=T0,
    )


def _match_propuesta(match_id: str, entidad_id: str, convocatoria_id: str) -> object:
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=convocatoria_id,
        transicion_id=f"t0-{match_id}", motivo="detectada", actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    return transicionar(
        match, a_estado=EstadoMatch.PROPUESTA, transicion_id=f"t1-{match_id}",
        motivo="propuesta", actor=ActorAsiento.SISTEMA, timestamp=T0,
    )


def _match_no_elegible(match_id: str, entidad_id: str, convocatoria_id: str, detalle: str):
    match = crear_match(
        match_id=match_id, entidad_id=entidad_id, convocatoria_id=convocatoria_id,
        transicion_id=f"t0-{match_id}", motivo="detectada", actor=ActorAsiento.SISTEMA,
        timestamp=T0,
    )
    return dataclasses.replace(
        match, resultado_elegibilidad_dura=ResultadoElegibilidad(elegible=False, detalle=detalle)
    )


def _cliente_logueado(almacen: AlmacenMemoria, entidad: Entidad, *, reloj=lambda: T0) -> TestClient:
    enviador = EnviadorEnlaceAccesoStub()
    app = crear_app(
        secret_key="clave-de-test-nunca-en-produccion",
        almacen=almacen,
        enviador_enlace=enviador,
        generador_token=lambda: f"token-{entidad.entidad_id}",
        reloj=reloj,
    )
    client = TestClient(app)
    client.post("/login", data={"email": entidad.contacto.email})
    token = enviador.enlaces[0].token
    client.post("/login/confirmar", data={"token": token})
    return client


def test_panel_muestra_los_datos_de_la_propia_entidad():
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-1", "panel1@example.org", "Asociación del Panel")
    almacen.guardar_entidad(entidad)
    almacen.guardar_convocatoria(_convocatoria("panel-conv-1", "Ayudas de investigación rara"))
    almacen.guardar_match(_match_propuesta("panel-match-1", entidad.entidad_id, "panel-conv-1"))
    almacen.guardar_match(
        _match_no_elegible(
            "panel-match-2", entidad.entidad_id, "panel-conv-1", "ámbito territorial incompatible"
        )
    )

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert entidad.nombre_legal in resp.text
    assert "Ayudas de investigación rara" in resp.text
    assert "portal-panel" in resp.text
    assert "ámbito territorial incompatible" in resp.text


def test_panel_no_expone_ids_internos():
    # Match en un cubo SIN acciones (aceptar/descartar solo van en
    # propuestas_pendientes, F-web.2): ahí sí es necesario y legítimo que
    # match_id viaje como campo oculto del formulario de la propia entidad.
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-2", "panel2@example.org", "Fundación del Panel")
    almacen.guardar_entidad(entidad)
    almacen.guardar_convocatoria(_convocatoria("panel-conv-2", "Subvención de respiro familiar"))
    almacen.guardar_match(
        _match_no_elegible("panel-match-3", entidad.entidad_id, "panel-conv-2", "motivo interno")
    )

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert "panel-match-3" not in resp.text
    assert "panel-conv-2" not in resp.text
    assert entidad.entidad_id not in resp.text


def test_panel_sin_matches_muestra_cubos_vacios():
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-3", "panel3@example.org", "Liga del Panel")
    almacen.guardar_entidad(entidad)

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert entidad.nombre_legal in resp.text


def test_panel_convocatoria_no_disponible_degrada_limpio():
    almacen = AlmacenMemoria()
    entidad = _entidad("panel-ent-4", "panel4@example.org", "Red del Panel")
    almacen.guardar_entidad(entidad)
    # Match cuya convocatoria referenciada no está persistida (dato feo).
    almacen.guardar_match(_match_propuesta("panel-match-4", entidad.entidad_id, "conv-que-no-existe"))

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")  # no debe lanzar

    assert resp.status_code == 200
    assert "Convocatoria no disponible" in resp.text


# --- "Tus ayudas recurrentes" (bloque B) -------------------------------------


def _historial(entidad_id: str, historial_id: str, *, titulo: str, anio: int) -> HistorialConcesion:
    return HistorialConcesion(
        historial_id=historial_id,
        entidad_id=entidad_id,
        cod_concesion=f"cod-{historial_id}",
        nif_beneficiario="B44444444",
        fecha_concesion=date(anio, 9, 1),
        importe_centimos=320_000,
        cod_bdns_convocatoria=f"conv-{historial_id}",
        titulo_convocatoria=titulo,
        organo_nivel1="ESTADO",
        organo_nivel2="MINISTERIO DE PRUEBA",
        organo_nivel3=None,
        es_concesion_directa=False,
        serie_fingerprint=f"serie-{historial_id}",
        apertura_convocatoria=date(anio, 5, 10),
        capturado_en=T0,
    )


def _esperada(
    entidad_id: str,
    esperada_id: str,
    *,
    serie_fingerprint: str,
    titulo: str,
    ediciones_previas: int = 1,
    ventana: tuple[int, int] = (5, 5),
    anio_esperado: int = 2027,
    confianza: Confianza = Confianza.BAJA,
    accionable: bool = True,
    estado: EstadoEsperada = EstadoEsperada.ESPERADA,
    convocatoria_id_enlazada: str | None = None,
) -> ConvocatoriaEsperada:
    return ConvocatoriaEsperada(
        esperada_id=esperada_id,
        entidad_id=entidad_id,
        serie_fingerprint=serie_fingerprint,
        titulo_representativo=titulo,
        organo="Ministerio de Prueba",
        ediciones_previas=ediciones_previas,
        anios_observados=tuple(range(anio_esperado - ediciones_previas, anio_esperado)),
        ventana_mes_inicio=ventana[0],
        ventana_mes_fin=ventana[1],
        anio_esperado=anio_esperado,
        confianza=confianza,
        accionable=accionable,
        estado=estado,
        convocatoria_id_enlazada=convocatoria_id_enlazada,
        creado_en=T0,
        actualizado_en=T0,
    )


def test_panel_recurrentes_solo_muestra_historial_y_esperadas_de_la_propia_entidad():
    almacen = AlmacenMemoria()
    entidad_a = _entidad("rec-ent-a", "reca@example.org", "Entidad A")
    entidad_b = _entidad("rec-ent-b", "recb@example.org", "Entidad B")
    almacen.guardar_entidad(entidad_a)
    almacen.guardar_entidad(entidad_b)
    almacen.guardar_historial(_historial(entidad_a.entidad_id, "hist-a", titulo="Ayuda exclusiva de A", anio=2024))
    almacen.guardar_historial(_historial(entidad_b.entidad_id, "hist-b", titulo="Ayuda exclusiva de B", anio=2024))
    almacen.guardar_esperada(
        _esperada(entidad_a.entidad_id, "esp-a", serie_fingerprint="serie-a", titulo="Esperada exclusiva de A")
    )
    almacen.guardar_esperada(
        _esperada(entidad_b.entidad_id, "esp-b", serie_fingerprint="serie-b", titulo="Esperada exclusiva de B")
    )

    client = _cliente_logueado(almacen, entidad_a)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert "Ayuda exclusiva de A" in resp.text
    assert "Esperada exclusiva de A" in resp.text
    assert "Ayuda exclusiva de B" not in resp.text
    assert "Esperada exclusiva de B" not in resp.text


def test_panel_recurrentes_vacio_muestra_texto_neutro():
    almacen = AlmacenMemoria()
    entidad = _entidad("rec-ent-vacio", "recvacio@example.org", "Entidad Vacía")
    almacen.guardar_entidad(entidad)

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert "Aún no hay historial capturado" in resp.text
    assert "Tus ayudas recurrentes" in resp.text


def test_panel_recurrentes_etiquetas_honestas_por_estado():
    almacen = AlmacenMemoria()
    entidad = _entidad("rec-ent-estados", "recestados@example.org", "Entidad de Estados")
    almacen.guardar_entidad(entidad)

    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-una-edicion", serie_fingerprint="serie-1",
            titulo="Ayuda de una sola edición", ediciones_previas=1, confianza=Confianza.BAJA,
        )
    )
    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-irregular", serie_fingerprint="serie-2",
            titulo="Ayuda irregular", ediciones_previas=2, ventana=(1, 9), confianza=Confianza.BAJA,
        )
    )
    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-nominativa", serie_fingerprint="serie-3",
            titulo="Ayuda nominativa", ediciones_previas=1, accionable=False, confianza=Confianza.BAJA,
        )
    )
    almacen.guardar_convocatoria(_convocatoria("rec-conv-publicada", "Ya publicada este año"))
    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-publicada", serie_fingerprint="serie-4",
            titulo="Ayuda ya publicada", ediciones_previas=2, confianza=Confianza.ALTA,
            estado=EstadoEsperada.PUBLICADA_ENLAZADA, convocatoria_id_enlazada="rec-conv-publicada",
        )
    )
    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-no-aparecida", serie_fingerprint="serie-5",
            titulo="Ayuda no aparecida", ediciones_previas=2, confianza=Confianza.MEDIA,
            estado=EstadoEsperada.NO_APARECIDA,
        )
    )

    client = _cliente_logueado(almacen, entidad)
    resp = client.get("/panel")

    assert resp.status_code == 200
    assert "una sola edición previa — sin patrón confirmado" in resp.text
    assert "irregular" in resp.text
    assert "adjudicación directa — no se solicita en concurrencia" in resp.text
    assert "¡ya está abierta!" in resp.text
    assert "ha aparecido en su ventana habitual — conviene revisarla manualmente" in resp.text
    assert "PENDIENTE DE PUBLICAR" in resp.text
    # nominativa: sin botón ni sugerencia de presentarse.
    assert "esp-nominativa" not in resp.text


def test_panel_aviso_ventana_proxima_solo_dentro_de_ventana_y_confianza_media_alta():
    almacen = AlmacenMemoria()
    entidad = _entidad("rec-ent-ventana", "recventana@example.org", "Entidad Ventana")
    almacen.guardar_entidad(entidad)
    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-ventana-alta", serie_fingerprint="serie-alta",
            titulo="Ayuda con ventana cercana", ediciones_previas=3, ventana=(7, 7),
            anio_esperado=2026, confianza=Confianza.ALTA,
        )
    )
    # confianza BAJA (una sola edición) NO debe disparar el aviso aunque caiga en ventana.
    almacen.guardar_esperada(
        _esperada(
            entidad.entidad_id, "esp-ventana-baja", serie_fingerprint="serie-baja",
            titulo="Ayuda de confianza baja en ventana", ediciones_previas=1, ventana=(7, 7),
            anio_esperado=2026, confianza=Confianza.BAJA,
        )
    )

    # Dentro de la ventana (julio 2026, reloj de la app = fecha de referencia).
    cliente_dentro = _cliente_logueado(almacen, entidad, reloj=lambda: datetime(2026, 7, 15, tzinfo=timezone.utc))
    resp_dentro = cliente_dentro.get("/panel")
    assert "Se acerca la ventana estimada de <strong>Ayuda con ventana cercana</strong>" in resp_dentro.text
    # confianza BAJA nunca dispara el aviso, aunque caiga en su ventana:
    assert "Se acerca la ventana estimada de <strong>Ayuda de confianza baja en ventana</strong>" not in resp_dentro.text
    assert resp_dentro.text.count("Se acerca la ventana estimada") == 1

    # Fuera de la ventana (octubre 2026) -> sin aviso.
    cliente_fuera = _cliente_logueado(almacen, entidad, reloj=lambda: datetime(2026, 10, 15, tzinfo=timezone.utc))
    resp_fuera = cliente_fuera.get("/panel")
    assert "Se acerca la ventana estimada" not in resp_fuera.text
