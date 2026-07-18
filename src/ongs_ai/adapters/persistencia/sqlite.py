"""Adapter SQLite — backend real por defecto (ADR F1).

Ruta SIEMPRE anclada al repo (nunca relativa al CWD, para no crear bases
gemelas). Esquema versionado con CREATE TABLE IF NOT EXISTS / ALTER TABLE
idempotente. Los objetos de dominio se serializan a JSON en una columna
`datos_json`; las columnas reales (`entidad_id`, `convocatoria_id`,
`match_id`) existen para indexar y para el aislamiento por tenant.

v1: la lectura devuelve el dict decodificado del JSON (no reconstruye los
dataclasses tipados) — reconstrucción completa se añade cuando un
consumidor real la necesite; evita deserialización especulativa sin uso.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import Match

RAIZ_REPO = Path(__file__).resolve().parents[4]
RUTA_DB_DEFECTO = RAIZ_REPO / "var" / "ongs_ai.sqlite3"

_SCHEMA_VERSION = 1


def _codificar_json(obj: object) -> str:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"No serializable a JSON: {type(obj)!r}")


class AlmacenSQLite:
    """Implementa RepositorioEntidades + RepositorioConvocatorias + RepositorioMatches."""

    def __init__(self, ruta_db: str | Path = RUTA_DB_DEFECTO) -> None:
        self._ruta_db = Path(ruta_db) if str(ruta_db) != ":memory:" else ruta_db
        if isinstance(self._ruta_db, Path):
            self._ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._ruta_db))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrar()

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

    # Entidades ------------------------------------------------------
    def guardar_entidad(self, entidad: Entidad) -> None:
        payload = json.dumps(asdict(entidad), default=_codificar_json, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO entidades (entidad_id, datos_json) VALUES (?, ?) "
            "ON CONFLICT(entidad_id) DO UPDATE SET datos_json = excluded.datos_json",
            (entidad.entidad_id, payload),
        )
        self._conn.commit()

    def obtener_entidad(self, entidad_id: str) -> dict | None:
        fila = self._conn.execute(
            "SELECT datos_json FROM entidades WHERE entidad_id = ?", (entidad_id,)
        ).fetchone()
        return json.loads(fila[0]) if fila else None

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

    def obtener_convocatoria(self, convocatoria_id: str) -> dict | None:
        fila = self._conn.execute(
            "SELECT datos_json FROM convocatorias WHERE convocatoria_id = ?",
            (convocatoria_id,),
        ).fetchone()
        return json.loads(fila[0]) if fila else None

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

    def listar_matches_por_entidad(self, entidad_id: str) -> list[dict]:
        filas = self._conn.execute(
            "SELECT datos_json FROM matches WHERE entidad_id = ?", (entidad_id,)
        ).fetchall()
        return [json.loads(fila[0]) for fila in filas]
