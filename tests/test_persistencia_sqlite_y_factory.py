"""Adapter SQLite y factory por entorno — herméticos: `:memory:`, nunca disco compartido."""
from datetime import datetime, timezone

from ongs_ai.adapters.persistencia.factory import crear_almacen
from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.adapters.persistencia.sqlite import AlmacenSQLite
from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    DatosEconomicos,
    Entidad,
    RequisitoFormal,
    TipoActividad,
)
from ongs_ai.dominio.matching_estado import ActorAsiento, crear_match

T0 = datetime(2026, 7, 18, tzinfo=timezone.utc)


def _entidad() -> Entidad:
    return Entidad(
        entidad_id="ent-sqlite-1",
        nombre_legal="Asociación SQLite",
        nif="B12345678",
        ambito_territorial=AmbitoTerritorial.AUTONOMICO,
        enfermedad_o_colectivo="colectivo de prueba sqlite",
        actividades=(ActividadDeclarada(tipo=TipoActividad.FORMACION),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=50_000, gastos_centimos=40_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.DECLARADA_UTILIDAD_PUBLICA,),
        contacto=Contacto(email="sqlite@example.org"),
        creado_en=T0,
        actualizado_en=T0,
        region="Madrid",
    )


def test_almacen_sqlite_en_memoria_guarda_y_lee_entidad():
    almacen = AlmacenSQLite(":memory:")
    try:
        entidad = _entidad()
        almacen.guardar_entidad(entidad)
        leida = almacen.obtener_entidad(entidad.entidad_id)
        assert leida is not None
        assert leida["entidad_id"] == "ent-sqlite-1"
        assert leida["datos_economicos_ejercicio_anterior"]["ingresos_centimos"] == 50_000
    finally:
        almacen.cerrar()


def test_almacen_sqlite_en_memoria_filtra_matches_por_entidad():
    almacen = AlmacenSQLite(":memory:")
    try:
        match_a = crear_match(
            match_id="m-a", entidad_id="ent-A", convocatoria_id="conv-1",
            transicion_id="t0", motivo="detectada", actor=ActorAsiento.SISTEMA, timestamp=T0,
        )
        match_b = crear_match(
            match_id="m-b", entidad_id="ent-B", convocatoria_id="conv-1",
            transicion_id="t0", motivo="detectada", actor=ActorAsiento.SISTEMA, timestamp=T0,
        )
        almacen.guardar_match(match_a)
        almacen.guardar_match(match_b)

        resultado = almacen.listar_matches_por_entidad("ent-A")
        assert len(resultado) == 1
        assert resultado[0]["match_id"] == "m-a"
    finally:
        almacen.cerrar()


def test_factory_entorno_test_devuelve_almacen_memoria():
    almacen = crear_almacen(entorno="test")
    assert isinstance(almacen, AlmacenMemoria)


def test_factory_por_defecto_ancla_ruta_al_repo_no_al_cwd(tmp_path, monkeypatch):
    import ongs_ai.adapters.persistencia.factory as factory_mod
    import ongs_ai.adapters.persistencia.sqlite as sqlite_mod

    ruta_aislada = tmp_path / "ongs_ai_test.sqlite3"
    monkeypatch.setattr(sqlite_mod, "RUTA_DB_DEFECTO", ruta_aislada)
    monkeypatch.setattr(factory_mod, "RUTA_DB_DEFECTO", ruta_aislada)
    monkeypatch.delenv("ONGS_AI_ENV", raising=False)

    almacen = crear_almacen(entorno="produccion")
    try:
        assert isinstance(almacen, AlmacenSQLite)
        assert ruta_aislada.exists()
    finally:
        almacen.cerrar()
