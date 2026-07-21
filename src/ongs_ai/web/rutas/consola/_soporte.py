"""Plumbing compartido de las rutas de consola (PROMPT-021 A) — plantillas
Jinja + filtros + helpers de perfil (Entidad | Prospecto). NO es un servicio
de dominio: cero reglas de negocio, solo composición de lo ya auditado
(`resumen_prospeccion`/`evaluar_afinidad`/`listar_*`). Nunca importa
`ongs_ai.web.dependencias` (ADR-006 §2.1, ancla `test_consola_estructura.py`).
"""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from datetime import date

from ongs_ai.dominio.entidades import AmbitoTerritorial, Convocatoria, Entidad, EstadoIngesta, FormaJuridica
from ongs_ai.prospeccion.modelo import Prospecto
from ongs_ai.servicios.afinidad import EstadoRequisito, ResultadoAfinidad, evaluar_afinidad

_RAIZ_PLANTILLAS = Path(__file__).resolve().parent.parent.parent / "plantillas"

AMBITO_LABEL = {
    AmbitoTerritorial.NACIONAL: "Nacional",
    AmbitoTerritorial.AUTONOMICO: "Autonómica",
    AmbitoTerritorial.PROVINCIAL: "Provincial",
    AmbitoTerritorial.LOCAL: "Local",
}

FORMA_LABEL = {
    FormaJuridica.ASOCIACION: "Asociación",
    FormaJuridica.FUNDACION: "Fundación",
    FormaJuridica.FEDERACION_O_CONFEDERACION: "Federación/confederación",
    FormaJuridica.OTRA: "Otra forma",
}

ESTADO_INGESTA_LABEL = {
    EstadoIngesta.DETECTADA: "Detectada",
    EstadoIngesta.EXTRAIDA: "Extraída",
    EstadoIngesta.VERIFICADA: "Verificada",
    EstadoIngesta.DESCARTADA_POR_DOMINIO: "Descartada",
}

REQUISITO_ICONO = {
    EstadoRequisito.CUMPLE: "ok",
    EstadoRequisito.INCUMPLE: "no",
    EstadoRequisito.PENDIENTE_DE_DATO: "warn",
}

REQUISITO_LABEL = {
    "estado_ingesta": "Estado de la convocatoria",
    "ambito_territorial": "Ámbito",
    "forma_juridica": "Forma jurídica",
    "antiguedad_minima_anios": "Antigüedad",
    "requisitos_formales": "Requisitos formales",
}

# Centroides aproximados de las comunidades autónomas (referencia geográfica
# pública, NO dato de ninguna entidad/ONG) — el mapa de sedes (A1) sitúa cada
# prospecto por su CCAA cuando no hay geocodificación real disponible; jamás
# se inventa una dirección exacta.
CENTROIDE_CCAA: dict[str, tuple[float, float]] = {
    "andalucia": (37.5443, -4.7278),
    "aragon": (41.6488, -0.8891),
    "principado de asturias": (43.3619, -5.8494),
    "asturias": (43.3619, -5.8494),
    "illes balears": (39.5696, 2.6502),
    "islas baleares": (39.5696, 2.6502),
    "canarias": (28.2916, -16.6291),
    "cantabria": (43.1828, -3.9878),
    "castilla y leon": (41.6523, -4.7286),
    "castilla-la mancha": (39.8628, -4.0273),
    "catalunya": (41.8204, 1.8676),
    "cataluna": (41.8204, 1.8676),
    "comunitat valenciana": (39.4840, -0.7532),
    "comunidad valenciana": (39.4840, -0.7532),
    "extremadura": (39.0921, -6.3730),
    "galicia": (42.7500, -7.8991),
    "comunidad de madrid": (40.4168, -3.7038),
    "madrid": (40.4168, -3.7038),
    "region de murcia": (37.9922, -1.1307),
    "comunidad foral de navarra": (42.6954, -1.6761),
    "navarra": (42.6954, -1.6761),
    "pais vasco": (42.9896, -2.6189),
    "euskadi": (42.9896, -2.6189),
    "la rioja": (42.2871, -2.5396),
    "ceuta": (35.8894, -5.3213),
    "melilla": (35.2937, -2.9383),
}


def crear_plantillas() -> Jinja2Templates:
    plantillas = Jinja2Templates(directory=str(_RAIZ_PLANTILLAS))
    plantillas.env.filters["euros"] = _euros
    plantillas.env.filters["ambito_label"] = lambda a: AMBITO_LABEL.get(a, a.value if a else "—")
    plantillas.env.filters["forma_label"] = lambda f: FORMA_LABEL.get(f, f.value if f else "—")
    plantillas.env.filters["estado_ingesta_label"] = lambda e: ESTADO_INGESTA_LABEL.get(e, e.value if e else "—")
    plantillas.env.filters["requisito_icono"] = lambda e: REQUISITO_ICONO.get(e, "warn")
    plantillas.env.filters["requisito_label"] = lambda r: REQUISITO_LABEL.get(r, r)
    return plantillas


def _euros(centimos: int | None) -> str:
    """Formatea céntimos como euros sin pasar por float (regla de oro dinero)."""
    if centimos is None:
        return "—"
    euros, resto = divmod(centimos, 100)
    return f"{euros:,}".replace(",", ".") + f",{resto:02d} €"


def clave_perfil(perfil: Entidad | Prospecto) -> str:
    if isinstance(perfil, Entidad):
        return f"entidad:{perfil.entidad_id}"
    return f"prospecto:{perfil.prospecto_id}"


def nombre_perfil(perfil: Entidad | Prospecto) -> str:
    return perfil.nombre_legal if isinstance(perfil, Entidad) else perfil.nombre


def region_perfil(perfil: Entidad | Prospecto) -> str | None:
    return perfil.region


def todos_los_perfiles(almacen) -> list[Entidad | Prospecto]:
    """Entidades captadas + Prospectos (candidatas), en ese orden — lectura
    GLOBAL propia del rol operador (ADR-006 §2.7), jamás filtrada por tenant."""
    return [*almacen.listar_entidades(), *almacen.listar_prospectos()]


def obtener_perfil_por_clave(almacen, clave: str) -> Entidad | Prospecto | None:
    tipo, _, identificador = clave.partition(":")
    if tipo == "entidad":
        return almacen.obtener_entidad(identificador)
    if tipo == "prospecto":
        return almacen.obtener_prospecto(identificador)
    return None


def convocatoria_vigente(convocatoria: Convocatoria, hoy: date) -> bool:
    """"Viva" = sin fecha de cierre publicada o con cierre todavía no pasado
    (no confunde con `elegible`: aquí solo mide si la convocatoria sigue
    abierta, con independencia de a quién le sirva)."""
    cierre = convocatoria.plazos.fecha_cierre
    return cierre is None or cierre >= hoy


def mejores_cruces(
    perfiles: list[Entidad | Prospecto], convocatorias: list[Convocatoria], hoy: date, *, limite: int = 4
) -> list[tuple[Entidad | Prospecto, Convocatoria, ResultadoAfinidad]]:
    """Todos los cruces (perfil × convocatoria) ELEGIBLES, ordenados por score
    desc — "Oportunidades más afines ahora" del dashboard (A1)."""
    resultados = []
    for perfil in perfiles:
        for convocatoria in convocatorias:
            resultado = evaluar_afinidad(perfil, convocatoria, hoy)
            if resultado.elegible:
                resultados.append((perfil, convocatoria, resultado))
    resultados.sort(key=lambda t: t[2].score, reverse=True)
    return resultados[:limite]
