"""Adapter SQLite — backend real por defecto (ADR F1).

Ruta SIEMPRE anclada al repo (nunca relativa al CWD, para no crear bases
gemelas). Esquema versionado con CREATE TABLE IF NOT EXISTS / ALTER TABLE
idempotente. Los objetos de dominio se serializan a JSON en una columna
`datos_json`; las columnas reales (`entidad_id`, `convocatoria_id`,
`match_id`) existen para indexar y para el aislamiento por tenant.

El puerto (`puertos.py`) promete objetos de dominio tipados, no dicts: las
lecturas reconstruyen exactamente los dataclasses de `entidades.py` /
`matching_estado.py`. Si un `datos_json` almacenado no mapea al contrato
(dato feo — corrupción, versión antigua, edición manual), la lectura NO
lanza al dominio: omite el registro (None / fuera de la lista) y lo cuenta
en `registros_omitidos_por_corrupcion` — regla de oro "degrada limpio".
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from enum import Enum
from pathlib import Path

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
from ongs_ai.dominio.errores import ErrorDominio
from ongs_ai.dominio.matching_estado import (
    ActorAsiento,
    Asiento,
    EstadoMatch,
    Match,
    ResultadoElegibilidad,
)

RAIZ_REPO = Path(__file__).resolve().parents[4]
RUTA_DB_DEFECTO = RAIZ_REPO / "var" / "ongs_ai.sqlite3"

_SCHEMA_VERSION = 1

logger = logging.getLogger(__name__)


def _codificar_json(obj: object) -> str:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"No serializable a JSON: {type(obj)!r}")


# --- Deserialización JSON -> dataclasses tipados (contrato ADR-001) ------


def _actividad_desde_dict(d: dict) -> ActividadDeclarada:
    return ActividadDeclarada(tipo=TipoActividad(d["tipo"]), descripcion=d.get("descripcion"))


def _forma_juridica_desde_dict(d: dict) -> FormaJuridicaDeclarada:
    return FormaJuridicaDeclarada(tipo=FormaJuridica(d["tipo"]), descripcion=d.get("descripcion"))


def _entidad_desde_dict(d: dict) -> Entidad:
    datos_economicos = d["datos_economicos_ejercicio_anterior"]
    contacto = d["contacto"]
    return Entidad(
        entidad_id=d["entidad_id"],
        nombre_legal=d["nombre_legal"],
        nif=d["nif"],
        ambito_territorial=AmbitoTerritorial(d["ambito_territorial"]),
        forma_juridica=_forma_juridica_desde_dict(d["forma_juridica"]),
        fecha_constitucion=date.fromisoformat(d["fecha_constitucion"]),
        enfermedad_o_colectivo=d["enfermedad_o_colectivo"],
        actividades=tuple(_actividad_desde_dict(a) for a in d["actividades"]),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=datos_economicos["ingresos_centimos"],
            gastos_centimos=datos_economicos["gastos_centimos"],
            ejercicio=datos_economicos["ejercicio"],
        ),
        requisitos_formales_disponibles=tuple(
            RequisitoFormal(r) for r in d["requisitos_formales_disponibles"]
        ),
        contacto=Contacto(email=contacto.get("email"), telefono=contacto.get("telefono")),
        creado_en=datetime.fromisoformat(d["creado_en"]),
        actualizado_en=datetime.fromisoformat(d["actualizado_en"]),
        region=d.get("region"),
        provincia=d.get("provincia"),
    )


def _requisitos_elegibilidad_desde_dict(d: dict) -> RequisitosElegibilidad:
    ambito_requerido = d.get("ambito_territorial_requerido")
    return RequisitosElegibilidad(
        ambito_territorial_requerido=(
            AmbitoTerritorial(ambito_requerido) if ambito_requerido is not None else None
        ),
        forma_juridica_requerida=d.get("forma_juridica_requerida"),
        antiguedad_minima_anios=d.get("antiguedad_minima_anios"),
        requisitos_formales_requeridos=tuple(
            RequisitoFormal(r) for r in d.get("requisitos_formales_requeridos", ())
        ),
        exclusiones=tuple(d.get("exclusiones", ())),
    )


def _plazos_desde_dict(d: dict) -> Plazos:
    return Plazos(
        fecha_apertura=date.fromisoformat(d["fecha_apertura"]) if d.get("fecha_apertura") else None,
        fecha_cierre=date.fromisoformat(d["fecha_cierre"]) if d.get("fecha_cierre") else None,
        fecha_resolucion_estimada=(
            date.fromisoformat(d["fecha_resolucion_estimada"])
            if d.get("fecha_resolucion_estimada")
            else None
        ),
    )


def _convocatoria_desde_dict(d: dict) -> Convocatoria:
    fuente = d["fuente"]
    cuantias = d["cuantias"]
    return Convocatoria(
        convocatoria_id=d["convocatoria_id"],
        fuente=Fuente(
            portal=fuente["portal"], url_origen=fuente["url_origen"], tipo=TipoFuente(fuente["tipo"])
        ),
        objeto=d["objeto"],
        beneficiarios_elegibles=d["beneficiarios_elegibles"],
        requisitos_elegibilidad=_requisitos_elegibilidad_desde_dict(d["requisitos_elegibilidad"]),
        ambito_geografico=AmbitoTerritorial(d["ambito_geografico"]),
        plazos=_plazos_desde_dict(d["plazos"]),
        cuantias=Cuantias(
            importe_minimo_centimos=cuantias.get("importe_minimo_centimos"),
            importe_maximo_centimos=cuantias.get("importe_maximo_centimos"),
            porcentaje_max_financiable=cuantias.get("porcentaje_max_financiable"),
        ),
        estado_ingesta=EstadoIngesta(d["estado_ingesta"]),
        creado_en=datetime.fromisoformat(d["creado_en"]),
        actualizado_en=datetime.fromisoformat(d["actualizado_en"]),
        documento_origen_ref=d.get("documento_origen_ref"),
        region=d.get("region"),
        provincia=d.get("provincia"),
    )


def _asiento_desde_dict(d: dict) -> Asiento:
    de_estado = d.get("de_estado")
    return Asiento(
        transicion_id=d["transicion_id"],
        de_estado=EstadoMatch(de_estado) if de_estado is not None else None,
        a_estado=EstadoMatch(d["a_estado"]),
        motivo=d["motivo"],
        actor=ActorAsiento(d["actor"]),
        timestamp=datetime.fromisoformat(d["timestamp"]),
    )


def _match_desde_dict(d: dict) -> Match:
    resultado = d.get("resultado_elegibilidad_dura")
    return Match(
        match_id=d["match_id"],
        entidad_id=d["entidad_id"],
        convocatoria_id=d["convocatoria_id"],
        asientos=tuple(_asiento_desde_dict(a) for a in d["asientos"]),
        explicacion_ia=d.get("explicacion_ia"),
        resultado_elegibilidad_dura=(
            ResultadoElegibilidad(elegible=resultado["elegible"], detalle=resultado["detalle"])
            if resultado is not None
            else None
        ),
    )


_ERRORES_DATO_FEO = (KeyError, ValueError, TypeError, ErrorDominio)


class AlmacenSQLite:
    """Implementa RepositorioEntidades + RepositorioConvocatorias + RepositorioMatches."""

    def __init__(self, ruta_db: str | Path = RUTA_DB_DEFECTO) -> None:
        self._ruta_db = Path(ruta_db) if str(ruta_db) != ":memory:" else ruta_db
        if isinstance(self._ruta_db, Path):
            self._ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._ruta_db))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrar()
        self.registros_omitidos_por_corrupcion = 0

    def _migrar(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta ("
            "clave TEXT PRIMARY KEY, valor TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS entidades ("
            "entidad_id TEXT PRIMARY KEY, datos_json TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS convocatorias ("
            "convocatoria_id TEXT PRIMARY KEY, datos_json TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS matches ("
            "match_id TEXT PRIMARY KEY, "
            "entidad_id TEXT NOT NULL, "
            "convocatoria_id TEXT NOT NULL, "
            "datos_json TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_matches_entidad_id ON matches(entidad_id)"
        )
        cur.execute(
            "INSERT OR IGNORE INTO schema_meta (clave, valor) VALUES ('version', ?)",
            (str(_SCHEMA_VERSION),),
        )
        self._conn.commit()

    def cerrar(self) -> None:
        self._conn.close()

    def _decodificar(self, tipo_registro: str, identificador: str, constructor, datos: dict):
        try:
            return constructor(datos)
        except _ERRORES_DATO_FEO as exc:
            self.registros_omitidos_por_corrupcion += 1
            logger.warning(
                "Registro %s '%s' no mapea al contrato (dato feo), omitido: %s",
                tipo_registro,
                identificador,
                exc,
            )
            return None

    # Entidades ------------------------------------------------------
    def guardar_entidad(self, entidad: Entidad) -> None:
        payload = json.dumps(asdict(entidad), default=_codificar_json, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO entidades (entidad_id, datos_json) VALUES (?, ?) "
            "ON CONFLICT(entidad_id) DO UPDATE SET datos_json = excluded.datos_json",
            (entidad.entidad_id, payload),
        )
        self._conn.commit()

    def obtener_entidad(self, entidad_id: str) -> Entidad | None:
        fila = self._conn.execute(
            "SELECT datos_json FROM entidades WHERE entidad_id = ?", (entidad_id,)
        ).fetchone()
        if fila is None:
            return None
        return self._decodificar("entidad", entidad_id, _entidad_desde_dict, json.loads(fila[0]))

    # Convocatorias ----------------------------------------------------
    def guardar_convocatoria(self, convocatoria: Convocatoria) -> None:
        payload = json.dumps(
            asdict(convocatoria), default=_codificar_json, ensure_ascii=False
        )
        self._conn.execute(
            "INSERT INTO convocatorias (convocatoria_id, datos_json) VALUES (?, ?) "
            "ON CONFLICT(convocatoria_id) DO UPDATE SET datos_json = excluded.datos_json",
            (convocatoria.convocatoria_id, payload),
        )
        self._conn.commit()

    def obtener_convocatoria(self, convocatoria_id: str) -> Convocatoria | None:
        fila = self._conn.execute(
            "SELECT datos_json FROM convocatorias WHERE convocatoria_id = ?",
            (convocatoria_id,),
        ).fetchone()
        if fila is None:
            return None
        return self._decodificar(
            "convocatoria", convocatoria_id, _convocatoria_desde_dict, json.loads(fila[0])
        )

    # Matches — SIEMPRE filtrados por entidad_id ------------------------
    def guardar_match(self, match: Match) -> None:
        payload = json.dumps(asdict(match), default=_codificar_json, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO matches (match_id, entidad_id, convocatoria_id, datos_json) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(match_id) DO UPDATE SET datos_json = excluded.datos_json",
            (match.match_id, match.entidad_id, match.convocatoria_id, payload),
        )
        self._conn.commit()

    def listar_matches_por_entidad(self, entidad_id: str) -> list[Match]:
        filas = self._conn.execute(
            "SELECT match_id, datos_json FROM matches WHERE entidad_id = ?", (entidad_id,)
        ).fetchall()
        matches = []
        for match_id, datos_json in filas:
            match = self._decodificar("match", match_id, _match_desde_dict, json.loads(datos_json))
            if match is not None:
                matches.append(match)
        return matches
