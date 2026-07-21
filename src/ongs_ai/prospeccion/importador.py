"""Importador puro del maestro de prospección — ADR-006 §2.4/§6.2/§6.3/§7.

Función PURA `filas(dict) -> list[Prospecto]`: sin I/O (el parseo del CSV real
vive en `scripts/importar_prospectos.py`, manual, fuera de CI). Degradación
limpia (CLAUDE.md): fila sin `nombre` se descarta y cuenta; valor de
`Ámbito` no mapeable queda `None` y se cuenta; nada se inventa jamás.

Mapeo de columnas CERRADO Y DOCUMENTADO, resuelto por el operador/arquitecto
(pregunta bloqueante §6.2 del ADR-006, RESUELTA — fichero
`investigacion/asociaciones_maestro.csv`, CSV UTF-8, 511 filas):

    "Nombre"                      -> nombre
    "Web"                         -> web
    "Email"                       -> contacto.email (varios separados por
                                      ';' -> se coge el primero)
    "Teléfono"                    -> contacto.telefono
    "Ámbito"                      -> ambito_territorial (nacional/autonomico/
                                      provincial/local; normalizado con el
                                      criterio de ADR-002 -- sin mapeo -> None,
                                      contado)
    "CCAA"                        -> region (texto libre; "(sin CCAA)" o
                                      vacío -> None)
    "Enfermedad / Colectivo"      -> enfermedad_o_colectivo
    "Personas visibles (cargo)"   -> contacto_personal_nota (⚠ dato personal)
    "Tamaño"                      -> tamano (descriptivo libre)
    "Fuente(s)"                   -> fuente_maestro (procedencia del dato)
    "Notas"                       -> notas

`prospecto_id` es un id opaco, NUNCA derivado del nombre (CLAUDE.md: "claves
por id de entidad, nunca por nombre") -- se inyecta un generador (mismo patrón
que `generador_token` en `servicios/autenticacion.py`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ongs_ai.dominio.entidades import AmbitoTerritorial, Contacto, normalizar_texto_comparacion
from ongs_ai.prospeccion.modelo import Prospecto

_MAPA_AMBITO: dict[str, AmbitoTerritorial] = {
    "nacional": AmbitoTerritorial.NACIONAL,
    "autonomico": AmbitoTerritorial.AUTONOMICO,
    "provincial": AmbitoTerritorial.PROVINCIAL,
    "local": AmbitoTerritorial.LOCAL,
}

_CCAA_VACIA = normalizar_texto_comparacion("(sin CCAA)")


@dataclass(frozen=True)
class ResultadoImportacion:
    prospectos: tuple[Prospecto, ...]
    filas_descartadas_sin_nombre: int = 0
    valores_ambito_no_mapeados: int = 0


def _o_none(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def _mapear_ambito(valor_bruto: str | None) -> tuple[AmbitoTerritorial | None, bool]:
    """Devuelve (ambito, no_mapeable). `no_mapeable=True` solo cuenta cuando
    había un valor no vacío que no casó con el mapeo cerrado -- un campo
    simplemente vacío no es un error de mapeo."""
    texto = _o_none(valor_bruto)
    if texto is None:
        return None, False
    ambito = _MAPA_AMBITO.get(normalizar_texto_comparacion(texto))
    return ambito, ambito is None


def _mapear_region(valor_bruto: str | None) -> str | None:
    texto = _o_none(valor_bruto)
    if texto is None:
        return None
    if normalizar_texto_comparacion(texto) == _CCAA_VACIA:
        return None
    return texto


def _mapear_email(valor_bruto: str | None) -> str | None:
    texto = _o_none(valor_bruto)
    if texto is None:
        return None
    primero = texto.split(";")[0].strip()
    return primero or None


def _fila_a_prospecto(fila: dict[str, str], *, prospecto_id: str) -> tuple[Prospecto, bool]:
    ambito, ambito_no_mapeado = _mapear_ambito(fila.get("Ámbito"))
    email = _mapear_email(fila.get("Email"))
    telefono = _o_none(fila.get("Teléfono"))
    contacto = Contacto(email=email, telefono=telefono) if (email or telefono) else None

    prospecto = Prospecto(
        prospecto_id=prospecto_id,
        nombre=fila["Nombre"].strip(),
        web=_o_none(fila.get("Web")),
        ambito_territorial=ambito,
        region=_mapear_region(fila.get("CCAA")),
        enfermedad_o_colectivo=_o_none(fila.get("Enfermedad / Colectivo")),
        contacto=contacto,
        contacto_personal_nota=_o_none(fila.get("Personas visibles (cargo)")),
        tamano=_o_none(fila.get("Tamaño")),
        fuente_maestro=_o_none(fila.get("Fuente(s)")) or "",
        notas=_o_none(fila.get("Notas")),
    )
    return prospecto, ambito_no_mapeado


def importar_prospectos(
    filas: Iterable[dict[str, str]],
    *,
    generador_id: Callable[[], str],
) -> ResultadoImportacion:
    """Filas (dict columna->valor, ya parseadas por el llamador) -> Prospectos.

    Fila sin `Nombre` (ausente, vacío o solo espacios) se descarta y cuenta.
    Nunca lanza por un dato feo (CLAUDE.md: "la proyección jamás lanza por un
    dato feo").
    """
    prospectos: list[Prospecto] = []
    descartadas_sin_nombre = 0
    ambito_no_mapeados = 0

    for fila in filas:
        if not (fila.get("Nombre") or "").strip():
            descartadas_sin_nombre += 1
            continue
        prospecto, no_mapeado = _fila_a_prospecto(fila, prospecto_id=generador_id())
        prospectos.append(prospecto)
        if no_mapeado:
            ambito_no_mapeados += 1

    return ResultadoImportacion(
        prospectos=tuple(prospectos),
        filas_descartadas_sin_nombre=descartadas_sin_nombre,
        valores_ambito_no_mapeados=ambito_no_mapeados,
    )
