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
import threading
from dataclasses import asdict
from datetime import date, datetime, timezone
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
from ongs_ai.proactivo.modelo import Confianza, ConvocatoriaEsperada, EstadoEsperada, HistorialConcesion
from ongs_ai.prospeccion.modelo import Prospecto

RAIZ_REPO = Path(__file__).resolve().parents[4]
RUTA_DB_DEFECTO = RAIZ_REPO / "var" / "ongs_ai.sqlite3"

_SCHEMA_VERSION = 1

logger = logging.getLogger(__name__)


def _migrar_columna_si_falta(cur: sqlite3.Cursor, tabla: str, columna: str, tipo_sql: str) -> None:
    """ALTER TABLE idempotente (arquitectura CLAUDE.md): añade `columna` a `tabla`
    solo si una base ya existente (creada antes de este cambio) no la tiene."""
    columnas = {fila[1] for fila in cur.execute(f"PRAGMA table_info({tabla})").fetchall()}
    if columna not in columnas:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo_sql}")


def _normalizar_utc(momento: datetime) -> datetime:
    """Frontera del almacén (PROMPT-021 C1): `expira_en`/`ahora` se comparan
    como TEXTO ISO-8601 en SQL (`expira_en > ?`), correcto SOLO si ambos lados
    llevan siempre el mismo offset. Un `datetime` naive (sin tzinfo) se asume
    UTC -- el mismo huso que usa todo el resto de la app (`reloj()` siempre
    devuelve `datetime.now(timezone.utc)`) -- para que nunca se compare un ISO
    sin sufijo de zona contra uno con `+00:00`."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


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


def _prospecto_desde_dict(d: dict) -> Prospecto:
    contacto = d.get("contacto")
    ambito = d.get("ambito_territorial")
    forma = d.get("forma_juridica")
    return Prospecto(
        prospecto_id=d["prospecto_id"],
        nombre=d["nombre"],
        web=d.get("web"),
        ambito_territorial=AmbitoTerritorial(ambito) if ambito is not None else None,
        region=d.get("region"),
        provincia=d.get("provincia"),
        enfermedad_o_colectivo=d.get("enfermedad_o_colectivo"),
        actividades=tuple(TipoActividad(a) for a in d.get("actividades", ())),
        forma_juridica=FormaJuridica(forma) if forma is not None else None,
        contacto=(
            Contacto(email=contacto.get("email"), telefono=contacto.get("telefono"))
            if contacto is not None
            else None
        ),
        contacto_personal_nota=d.get("contacto_personal_nota"),
        tamano=d.get("tamano"),
        fuente_maestro=d.get("fuente_maestro", ""),
        notas=d.get("notas"),
    )


def _historial_desde_dict(d: dict) -> HistorialConcesion:
    apertura = d.get("apertura_convocatoria")
    return HistorialConcesion(
        historial_id=d["historial_id"],
        entidad_id=d["entidad_id"],
        cod_concesion=d["cod_concesion"],
        nif_beneficiario=d["nif_beneficiario"],
        fecha_concesion=date.fromisoformat(d["fecha_concesion"]),
        importe_centimos=d.get("importe_centimos"),
        cod_bdns_convocatoria=d["cod_bdns_convocatoria"],
        titulo_convocatoria=d["titulo_convocatoria"],
        organo_nivel1=d.get("organo_nivel1"),
        organo_nivel2=d.get("organo_nivel2"),
        organo_nivel3=d.get("organo_nivel3"),
        es_concesion_directa=d["es_concesion_directa"],
        serie_fingerprint=d["serie_fingerprint"],
        apertura_convocatoria=date.fromisoformat(apertura) if apertura else None,
        capturado_en=datetime.fromisoformat(d["capturado_en"]),
    )


def _esperada_desde_dict(d: dict) -> ConvocatoriaEsperada:
    return ConvocatoriaEsperada(
        esperada_id=d["esperada_id"],
        entidad_id=d["entidad_id"],
        serie_fingerprint=d["serie_fingerprint"],
        titulo_representativo=d["titulo_representativo"],
        organo=d.get("organo"),
        ediciones_previas=d["ediciones_previas"],
        anios_observados=tuple(d.get("anios_observados", ())),
        ventana_mes_inicio=d["ventana_mes_inicio"],
        ventana_mes_fin=d["ventana_mes_fin"],
        anio_esperado=d["anio_esperado"],
        confianza=Confianza(d["confianza"]),
        accionable=d["accionable"],
        estado=EstadoEsperada(d["estado"]),
        convocatoria_id_enlazada=d.get("convocatoria_id_enlazada"),
        creado_en=datetime.fromisoformat(d["creado_en"]),
        actualizado_en=datetime.fromisoformat(d["actualizado_en"]),
    )


_ERRORES_DATO_FEO = (KeyError, ValueError, TypeError, ErrorDominio)


class AlmacenSQLite:
    """Implementa RepositorioEntidades + RepositorioConvocatorias + RepositorioMatches
    + RepositorioTokensAcceso + RepositorioProspectos + RepositorioHistorialConcesiones
    + RepositorioConvocatoriasEsperadas (ADR-007 §3.1 — proactivo, fuera de contrato)."""

    def __init__(self, ruta_db: str | Path = RUTA_DB_DEFECTO) -> None:
        # FastAPI ejecuta las rutas sync en un threadpool (nunca el hilo que
        # crea el almacén): check_same_thread=False + un lock propio que
        # serializa TODA operación es el arreglo conservador — SQLite ya
        # serializa escrituras internamente y el volumen v1 es mínimo; nada
        # de pooling ni de una conexión por hilo.
        self._lock = threading.Lock()
        self._ruta_db = Path(ruta_db) if str(ruta_db) != ":memory:" else ruta_db
        if isinstance(self._ruta_db, Path):
            self._ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._ruta_db), check_same_thread=False)
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._migrar()
        self.registros_omitidos_por_corrupcion = 0
        self.entidades_duplicadas_por_email = 0

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
        _migrar_columna_si_falta(cur, "entidades", "email", "TEXT")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_entidades_email ON entidades(email)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tokens_acceso ("
            "token_hash TEXT PRIMARY KEY, entidad_id TEXT NOT NULL, "
            "expira_en TEXT NOT NULL, usado_en TEXT NULL)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_tokens_acceso_entidad_id ON tokens_acceso(entidad_id)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS convocatorias ("
            "convocatoria_id TEXT PRIMARY KEY, portal TEXT, url_origen TEXT, "
            "datos_json TEXT NOT NULL)"
        )
        _migrar_columna_si_falta(cur, "convocatorias", "portal", "TEXT")
        _migrar_columna_si_falta(cur, "convocatorias", "url_origen", "TEXT")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_convocatorias_portal_url_origen "
            "ON convocatorias(portal, url_origen)"
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
            "CREATE TABLE IF NOT EXISTS prospectos ("
            "prospecto_id TEXT PRIMARY KEY, datos_json TEXT NOT NULL)"
        )
        # ADR-007 §3.1/§6.1 — proactivo, fuera del contrato congelado, mismo
        # patrón idempotente. SIEMPRE indexado por entidad_id (aislamiento).
        cur.execute(
            "CREATE TABLE IF NOT EXISTS historial_concesiones ("
            "historial_id TEXT PRIMARY KEY, entidad_id TEXT NOT NULL, "
            "cod_concesion TEXT NOT NULL, datos_json TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_historial_entidad_id "
            "ON historial_concesiones(entidad_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_historial_entidad_cod_concesion "
            "ON historial_concesiones(entidad_id, cod_concesion)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS convocatorias_esperadas ("
            "esperada_id TEXT PRIMARY KEY, entidad_id TEXT NOT NULL, "
            "serie_fingerprint TEXT NOT NULL, anio_esperado INTEGER NOT NULL, "
            "datos_json TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_esperadas_entidad_id "
            "ON convocatorias_esperadas(entidad_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_esperadas_entidad_serie_anio "
            "ON convocatorias_esperadas(entidad_id, serie_fingerprint, anio_esperado)"
        )
        cur.execute(
            "INSERT OR IGNORE INTO schema_meta (clave, valor) VALUES ('version', ?)",
            (str(_SCHEMA_VERSION),),
        )
        self._conn.commit()

    def cerrar(self) -> None:
        with self._lock:
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
        with self._lock:
            self._conn.execute(
                "INSERT INTO entidades (entidad_id, email, datos_json) VALUES (?, ?, ?) "
                "ON CONFLICT(entidad_id) DO UPDATE SET "
                "email = excluded.email, datos_json = excluded.datos_json",
                (entidad.entidad_id, entidad.contacto.email, payload),
            )
            self._conn.commit()

    def obtener_entidad(self, entidad_id: str) -> Entidad | None:
        with self._lock:
            fila = self._conn.execute(
                "SELECT datos_json FROM entidades WHERE entidad_id = ?", (entidad_id,)
            ).fetchone()
        if fila is None:
            return None
        return self._decodificar("entidad", entidad_id, _entidad_desde_dict, json.loads(fila[0]))

    def obtener_entidad_por_email(self, email: str) -> Entidad | None:
        """Login por email (ADR-005 §5). Email duplicado entre entidades =
        login ambiguo: decisión conservadora, devuelve None y lo cuenta —
        nunca elige una entidad al azar entre coincidencias."""
        with self._lock:
            filas = self._conn.execute(
                "SELECT entidad_id, datos_json FROM entidades WHERE email = ?", (email,)
            ).fetchall()
        if len(filas) != 1:
            if len(filas) > 1:
                self.entidades_duplicadas_por_email += 1
            return None
        entidad_id, datos_json = filas[0]
        return self._decodificar(
            "entidad", entidad_id, _entidad_desde_dict, json.loads(datos_json)
        )

    def listar_entidades(self) -> list[Entidad]:
        with self._lock:
            filas = self._conn.execute("SELECT entidad_id, datos_json FROM entidades").fetchall()
        entidades = []
        for entidad_id, datos_json in filas:
            entidad = self._decodificar(
                "entidad", entidad_id, _entidad_desde_dict, json.loads(datos_json)
            )
            if entidad is not None:
                entidades.append(entidad)
        return entidades

    # Convocatorias ----------------------------------------------------
    def guardar_convocatoria(self, convocatoria: Convocatoria) -> None:
        payload = json.dumps(
            asdict(convocatoria), default=_codificar_json, ensure_ascii=False
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO convocatorias (convocatoria_id, portal, url_origen, datos_json) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(convocatoria_id) DO UPDATE SET "
                "portal = excluded.portal, url_origen = excluded.url_origen, "
                "datos_json = excluded.datos_json",
                (
                    convocatoria.convocatoria_id,
                    convocatoria.fuente.portal,
                    convocatoria.fuente.url_origen,
                    payload,
                ),
            )
            self._conn.commit()

    def obtener_convocatoria(self, convocatoria_id: str) -> Convocatoria | None:
        with self._lock:
            fila = self._conn.execute(
                "SELECT datos_json FROM convocatorias WHERE convocatoria_id = ?",
                (convocatoria_id,),
            ).fetchone()
        if fila is None:
            return None
        return self._decodificar(
            "convocatoria", convocatoria_id, _convocatoria_desde_dict, json.loads(fila[0])
        )

    def obtener_por_url_origen(self, portal: str, url_origen: str) -> Convocatoria | None:
        """Clave natural de dedupe (ADR-001 §6.5): `portal`+`url_origen`."""
        with self._lock:
            fila = self._conn.execute(
                "SELECT convocatoria_id, datos_json FROM convocatorias "
                "WHERE portal = ? AND url_origen = ?",
                (portal, url_origen),
            ).fetchone()
        if fila is None:
            return None
        convocatoria_id, datos_json = fila
        return self._decodificar(
            "convocatoria", convocatoria_id, _convocatoria_desde_dict, json.loads(datos_json)
        )

    def listar_convocatorias(self) -> list[Convocatoria]:
        with self._lock:
            filas = self._conn.execute(
                "SELECT convocatoria_id, datos_json FROM convocatorias"
            ).fetchall()
        convocatorias = []
        for convocatoria_id, datos_json in filas:
            convocatoria = self._decodificar(
                "convocatoria", convocatoria_id, _convocatoria_desde_dict, json.loads(datos_json)
            )
            if convocatoria is not None:
                convocatorias.append(convocatoria)
        return convocatorias

    # Matches — SIEMPRE filtrados por entidad_id ------------------------
    def guardar_match(self, match: Match) -> None:
        payload = json.dumps(asdict(match), default=_codificar_json, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT INTO matches (match_id, entidad_id, convocatoria_id, datos_json) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(match_id) DO UPDATE SET datos_json = excluded.datos_json",
                (match.match_id, match.entidad_id, match.convocatoria_id, payload),
            )
            self._conn.commit()

    def listar_matches_por_entidad(self, entidad_id: str) -> list[Match]:
        with self._lock:
            filas = self._conn.execute(
                "SELECT match_id, datos_json FROM matches WHERE entidad_id = ?", (entidad_id,)
            ).fetchall()
        matches = []
        for match_id, datos_json in filas:
            match = self._decodificar("match", match_id, _match_desde_dict, json.loads(datos_json))
            if match is not None:
                matches.append(match)
        return matches

    # Tokens de acceso (magic link) — ADR-005 §5 ------------------------
    def crear_token(self, entidad_id: str, token_hash: str, expira_en: datetime) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO tokens_acceso (token_hash, entidad_id, expira_en, usado_en) "
                "VALUES (?, ?, ?, NULL) "
                "ON CONFLICT(token_hash) DO UPDATE SET "
                "entidad_id = excluded.entidad_id, expira_en = excluded.expira_en, usado_en = NULL",
                (token_hash, entidad_id, _normalizar_utc(expira_en).isoformat()),
            )
            self._conn.commit()

    def consumir_token(self, token_hash: str, ahora: datetime) -> str | None:
        """UPDATE atómico (check-and-mark-used en una sola sentencia SQL): solo
        marca usado si existía, no había expirado y no se había usado ya."""
        ahora_iso = _normalizar_utc(ahora).isoformat()
        with self._lock:
            cur = self._conn.execute(
                "UPDATE tokens_acceso SET usado_en = ? "
                "WHERE token_hash = ? AND usado_en IS NULL AND expira_en > ?",
                (ahora_iso, token_hash, ahora_iso),
            )
            self._conn.commit()
            if cur.rowcount != 1:
                return None
            fila = self._conn.execute(
                "SELECT entidad_id FROM tokens_acceso WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            return fila[0] if fila else None

    # Prospectos (ADR-006 §2.3/§2.7 — fuera del contrato congelado) ----
    def guardar_prospecto(self, prospecto: Prospecto) -> None:
        payload = json.dumps(asdict(prospecto), default=_codificar_json, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT INTO prospectos (prospecto_id, datos_json) VALUES (?, ?) "
                "ON CONFLICT(prospecto_id) DO UPDATE SET datos_json = excluded.datos_json",
                (prospecto.prospecto_id, payload),
            )
            self._conn.commit()

    def obtener_prospecto(self, prospecto_id: str) -> Prospecto | None:
        with self._lock:
            fila = self._conn.execute(
                "SELECT datos_json FROM prospectos WHERE prospecto_id = ?", (prospecto_id,)
            ).fetchone()
        if fila is None:
            return None
        return self._decodificar(
            "prospecto", prospecto_id, _prospecto_desde_dict, json.loads(fila[0])
        )

    def listar_prospectos(self) -> list[Prospecto]:
        with self._lock:
            filas = self._conn.execute(
                "SELECT prospecto_id, datos_json FROM prospectos"
            ).fetchall()
        prospectos = []
        for prospecto_id, datos_json in filas:
            prospecto = self._decodificar(
                "prospecto", prospecto_id, _prospecto_desde_dict, json.loads(datos_json)
            )
            if prospecto is not None:
                prospectos.append(prospecto)
        return prospectos

    # Historial de concesiones (ADR-007 §3.1 — fuera del contrato congelado,
    # SIEMPRE filtrado por entidad_id, aislamiento por tenant §3.9) --------
    def guardar_historial(self, historial: HistorialConcesion) -> None:
        payload = json.dumps(asdict(historial), default=_codificar_json, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT INTO historial_concesiones "
                "(historial_id, entidad_id, cod_concesion, datos_json) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(historial_id) DO UPDATE SET "
                "entidad_id = excluded.entidad_id, cod_concesion = excluded.cod_concesion, "
                "datos_json = excluded.datos_json",
                (historial.historial_id, historial.entidad_id, historial.cod_concesion, payload),
            )
            self._conn.commit()

    def obtener_historial_por_cod_concesion(
        self, entidad_id: str, cod_concesion: str
    ) -> HistorialConcesion | None:
        with self._lock:
            fila = self._conn.execute(
                "SELECT historial_id, datos_json FROM historial_concesiones "
                "WHERE entidad_id = ? AND cod_concesion = ?",
                (entidad_id, cod_concesion),
            ).fetchone()
        if fila is None:
            return None
        historial_id, datos_json = fila
        return self._decodificar(
            "historial_concesion", historial_id, _historial_desde_dict, json.loads(datos_json)
        )

    def listar_historial_por_entidad(self, entidad_id: str) -> list[HistorialConcesion]:
        with self._lock:
            filas = self._conn.execute(
                "SELECT historial_id, datos_json FROM historial_concesiones WHERE entidad_id = ?",
                (entidad_id,),
            ).fetchall()
        historial = []
        for historial_id, datos_json in filas:
            item = self._decodificar(
                "historial_concesion", historial_id, _historial_desde_dict, json.loads(datos_json)
            )
            if item is not None:
                historial.append(item)
        return historial

    # Convocatorias esperadas (ADR-007 §3.1 — SIEMPRE filtrado por entidad_id) -
    def guardar_esperada(self, esperada: ConvocatoriaEsperada) -> None:
        payload = json.dumps(asdict(esperada), default=_codificar_json, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT INTO convocatorias_esperadas "
                "(esperada_id, entidad_id, serie_fingerprint, anio_esperado, datos_json) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(esperada_id) DO UPDATE SET "
                "entidad_id = excluded.entidad_id, serie_fingerprint = excluded.serie_fingerprint, "
                "anio_esperado = excluded.anio_esperado, datos_json = excluded.datos_json",
                (
                    esperada.esperada_id,
                    esperada.entidad_id,
                    esperada.serie_fingerprint,
                    esperada.anio_esperado,
                    payload,
                ),
            )
            self._conn.commit()

    def obtener_esperada(
        self, entidad_id: str, serie_fingerprint: str, anio_esperado: int
    ) -> ConvocatoriaEsperada | None:
        with self._lock:
            fila = self._conn.execute(
                "SELECT esperada_id, datos_json FROM convocatorias_esperadas "
                "WHERE entidad_id = ? AND serie_fingerprint = ? AND anio_esperado = ?",
                (entidad_id, serie_fingerprint, anio_esperado),
            ).fetchone()
        if fila is None:
            return None
        esperada_id, datos_json = fila
        return self._decodificar(
            "esperada", esperada_id, _esperada_desde_dict, json.loads(datos_json)
        )

    def listar_esperadas_por_entidad(self, entidad_id: str) -> list[ConvocatoriaEsperada]:
        with self._lock:
            filas = self._conn.execute(
                "SELECT esperada_id, datos_json FROM convocatorias_esperadas WHERE entidad_id = ?",
                (entidad_id,),
            ).fetchall()
        esperadas = []
        for esperada_id, datos_json in filas:
            item = self._decodificar(
                "esperada", esperada_id, _esperada_desde_dict, json.loads(datos_json)
            )
            if item is not None:
                esperadas.append(item)
        return esperadas
