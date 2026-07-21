"""Extracción IA de requisitos de elegibilidad — PROMPT-018 A3.

Dada una `Convocatoria` con `requisitos_elegibilidad` incompletos, pide al
CLI (`ClienteClaudeCLI`) que derive, SOLO del texto ya presente en el
contrato (`objeto` + `beneficiarios_elegibles` — nunca se hace fetch a bases
externas en esta fase), los requisitos que ese texto ya declara
explícitamente. La respuesta del CLI NUNCA entra al dominio sin pasar por
validación determinista aquí (regla de oro CLAUDE.md: la IA propone, el
dominio valida — enums/typos se descartan, jamás se inventa un valor).

`enriquecer_requisitos` solo rellena los campos de `RequisitosElegibilidad`
que estaban vacíos: nunca pisa un dato ya presente, ni siquiera si el CLI
"corrige" algo ya informado. Si el CLI degrada (timeout, sin binario, límite
de plan) o la salida no es JSON parseable, la convocatoria se devuelve
intacta — no es un error, es la cola de trabajo pendiente para la próxima
pasada.
"""
from __future__ import annotations

import dataclasses
import json
import logging

from ongs_ai.dominio.entidades import Convocatoria, RequisitoFormal, RequisitosElegibilidad
from ongs_ai.ia.claude_cli import ClienteClaudeCLI

logger = logging.getLogger(__name__)

_FLAGS_VALIDOS = {flag.value for flag in RequisitoFormal}


def _prompt_extraccion(convocatoria: Convocatoria) -> str:
    flags = ", ".join(sorted(_FLAGS_VALIDOS))
    return (
        "Eres un analista de subvenciones. A partir SOLO del siguiente texto "
        "(no uses conocimiento externo, no inventes nada que no esté aquí), "
        "extrae los requisitos de elegibilidad que declara EXPLÍCITAMENTE, en "
        "un único objeto JSON con exactamente estas claves:\n"
        '  "forma_juridica_requerida": texto libre con la forma jurídica '
        "exigida, o null si el texto no la menciona,\n"
        '  "antiguedad_minima_anios": número entero de años, o null si el '
        "texto no menciona una antigüedad mínima,\n"
        '  "requisitos_formales_requeridos": lista de cero o más de estos '
        f"valores EXACTOS (y solo estos): [{flags}] — inclúyelos solo si el "
        "texto los menciona explícitamente; nunca inventes otros valores.\n\n"
        f"Objeto de la convocatoria: {convocatoria.objeto}\n"
        f"Beneficiarios elegibles: {convocatoria.beneficiarios_elegibles}\n\n"
        "Responde SOLO con el JSON, sin explicación, sin markdown, sin bloque de código."
    )


def _despojar_bloque_markdown(texto: str) -> str:
    """El modelo a veces envuelve el JSON en ```json ... ``` pese a la
    instrucción de no hacerlo; se despoja de forma determinista."""
    texto = texto.strip()
    if not texto.startswith("```"):
        return texto
    texto = texto.strip("`").strip()
    if texto.lower().startswith("json"):
        texto = texto[4:].strip()
    return texto


def _parsear_json_extraccion(texto: str) -> dict | None:
    try:
        datos = json.loads(_despojar_bloque_markdown(texto))
    except (json.JSONDecodeError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _validar_forma_juridica_requerida(valor: object) -> str | None:
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def _validar_antiguedad_minima_anios(valor: object) -> int | None:
    if isinstance(valor, bool):  # bool es subclase de int — se descarta explícitamente
        return None
    if isinstance(valor, int) and valor >= 0:
        return valor
    return None


def _validar_requisitos_formales(valor: object) -> tuple[RequisitoFormal, ...]:
    if not isinstance(valor, list):
        return ()
    return tuple(
        RequisitoFormal(item) for item in valor if isinstance(item, str) and item in _FLAGS_VALIDOS
    )


def _requisitos_incompletos(requisitos: RequisitosElegibilidad) -> bool:
    return (
        requisitos.forma_juridica_requerida is None
        or requisitos.antiguedad_minima_anios is None
        or not requisitos.requisitos_formales_requeridos
    )


def enriquecer_requisitos(cliente: ClienteClaudeCLI, convocatoria: Convocatoria) -> Convocatoria:
    """Enriquece SOLO los campos vacíos de `requisitos_elegibilidad`. Ante
    cualquier degradación (CLI o salida no parseable) devuelve la
    convocatoria intacta."""
    requisitos_actuales = convocatoria.requisitos_elegibilidad
    if not _requisitos_incompletos(requisitos_actuales):
        return convocatoria

    texto = cliente.preguntar(_prompt_extraccion(convocatoria))
    if not texto:
        return convocatoria

    datos = _parsear_json_extraccion(texto)
    if datos is None:
        logger.warning(
            "extraccion_requisitos: salida no parseable para %s", convocatoria.convocatoria_id
        )
        return convocatoria

    forma_juridica_requerida = _validar_forma_juridica_requerida(datos.get("forma_juridica_requerida"))
    antiguedad_minima_anios = _validar_antiguedad_minima_anios(datos.get("antiguedad_minima_anios"))
    requisitos_formales_requeridos = _validar_requisitos_formales(
        datos.get("requisitos_formales_requeridos")
    )

    hay_algo_nuevo = (
        forma_juridica_requerida is not None
        or antiguedad_minima_anios is not None
        or requisitos_formales_requeridos
    )
    if not hay_algo_nuevo:
        return convocatoria

    nuevos_requisitos = dataclasses.replace(
        requisitos_actuales,
        forma_juridica_requerida=(
            requisitos_actuales.forma_juridica_requerida or forma_juridica_requerida
        ),
        antiguedad_minima_anios=(
            requisitos_actuales.antiguedad_minima_anios
            if requisitos_actuales.antiguedad_minima_anios is not None
            else antiguedad_minima_anios
        ),
        requisitos_formales_requeridos=(
            requisitos_actuales.requisitos_formales_requeridos or requisitos_formales_requeridos
        ),
    )
    return dataclasses.replace(convocatoria, requisitos_elegibilidad=nuevos_requisitos)
