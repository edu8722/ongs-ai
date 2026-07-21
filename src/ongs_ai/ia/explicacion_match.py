"""Capa IA explicativa de Match — ADR-001 §1.4/§2, F3.

`GeneradorExplicacion` es un Protocol mockeable: cualquier implementación
(stub v1, proveedor LLM real más adelante) es intercambiable sin tocar
`ongs_ai.dominio.matching`. La IA nunca decide `resultado_elegibilidad_dura`
ni `estado_actual`; solo argumenta un match ya evaluado por el guardarraíl
determinista (`ongs_ai.dominio.elegibilidad`).
"""
from __future__ import annotations

from typing import Protocol

from ongs_ai.dominio.entidades import Convocatoria, Entidad
from ongs_ai.dominio.matching_estado import ResultadoElegibilidad
from ongs_ai.ia.claude_cli import ClienteClaudeCLI


class GeneradorExplicacion(Protocol):
    def generar(
        self, entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
    ) -> str: ...


class ExplicadorStub:
    """Implementación v1: determinista, sin red, sin LLM real.

    El proveedor LLM real lo decide el arquitecto más adelante (ver
    engineering/ADR-001-contrato-de-datos.md, F3). Sirve para desbloquear el
    servicio de matching sin acoplarlo a ningún proveedor concreto.
    """

    def generar(
        self, entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
    ) -> str:
        return (
            f"{entidad.nombre_legal} encaja con la convocatoria "
            f'"{convocatoria.objeto}" ({convocatoria.fuente.portal}): {resultado.detalle}'
        )


def _prompt_explicacion(
    entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
) -> str:
    """Prompt corto en castellano, SOLO con los campos ya presentes en
    `entidad`/`convocatoria`/`resultado` — nunca inventa datos que no se le
    pasan (PROMPT-018 A2)."""
    return (
        "Eres un técnico de subvenciones para entidades de enfermedades raras. "
        "Explica en 2-4 frases, en castellano y en texto plano (sin markdown, "
        "sin encabezados), por qué esta convocatoria encaja con esta entidad. "
        "Usa SOLO los datos siguientes, no inventes nada más:\n"
        f"- Entidad: {entidad.nombre_legal}, forma jurídica "
        f"{entidad.forma_juridica.tipo.value}, ámbito {entidad.ambito_territorial.value}, "
        f"colectivo/enfermedad: {entidad.enfermedad_o_colectivo}.\n"
        f"- Convocatoria: {convocatoria.objeto} (portal {convocatoria.fuente.portal}), "
        f"beneficiarios elegibles: {convocatoria.beneficiarios_elegibles}.\n"
        f"- Resultado de elegibilidad (ya evaluado, no lo decidas tú): {resultado.detalle}\n\n"
        "Responde solo con el texto de la explicación."
    )


class ExplicadorClaudeCLI:
    """Implementación real de `GeneradorExplicacion` sobre `ClienteClaudeCLI`
    (PROMPT-018 A2) — consume la suscripción del operador vía CLI headless.

    Si el CLI degrada (timeout, sin binario, límite de plan, salida rara),
    devuelve `""`: el llamador (`dominio.matching.detectar_matches` /
    `servicios.propuestas.detectar_y_proponer`) ya trata cualquier texto
    vacío igual que una excepción — `explicacion_ia` queda `None`.
    """

    def __init__(self, cliente: ClienteClaudeCLI) -> None:
        self._cliente = cliente

    def generar(
        self, entidad: Entidad, convocatoria: Convocatoria, resultado: ResultadoElegibilidad
    ) -> str:
        texto = self._cliente.preguntar(_prompt_explicacion(entidad, convocatoria, resultado))
        return texto or ""
