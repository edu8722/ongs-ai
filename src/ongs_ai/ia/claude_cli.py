"""Cliente genérico del CLI de Claude Code en headless — PROMPT-018 A1.

Invoca la SUSCRIPCIÓN de Claude del operador (`claude -p "<prompt>"
--output-format json`), no una API de pago por token (decisión de producto
2026-07-21, `engineering/06_SIGUIENTES_PASOS.md`). Forma de la salida JSON
verificada en este entorno (2026-07-21, `claude 2.1.206` en Windows,
`claude -p "Responde solo con la palabra: ok" --output-format json`):

    {"type":"result","subtype":"success","is_error":false,"result":"ok",
     "duration_ms":..., "session_id":..., "total_cost_usd":..., "usage":{...}}

Los campos relevantes para este cliente son `is_error` (bool) y `result`
(el texto de respuesta del modelo); el resto (coste, tokens, sesión) no se
consume aquí. Si el formato real difiriera en otro entorno, este módulo
degrada limpio igualmente (no asume más forma de la necesaria).

Cualquier fallo — binario ausente, timeout, código de salida != 0, salida
no-JSON, `is_error=true`, `result` ausente/vacío (incl. límite de plan de
suscripción agotado) — degrada limpio: log + contador, JAMÁS excepción
hacia el dominio (regla de oro CLAUDE.md: la IA propone, el dominio
valida). En pytest el ejecutor de subproceso SIEMPRE es un stub inyectado;
el binario real nunca se invoca desde un test.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS_DEFECTO = 120.0


@dataclass(frozen=True)
class ResultadoProceso:
    codigo_salida: int
    stdout: str
    stderr: str


class EjecutorSubproceso(Protocol):
    def ejecutar(self, comando: list[str], *, timeout_segundos: float) -> ResultadoProceso: ...


class EjecutorSubprocesoReal:
    """Único ejecutor que lanza un proceso real — nunca se instancia en tests."""

    def ejecutar(self, comando: list[str], *, timeout_segundos: float) -> ResultadoProceso:
        # encoding="utf-8" explícito (A1): la salida del CLI de Claude es
        # UTF-8; decodificarla con el locale de la máquina (p. ej. cp1252 en
        # Windows) revienta con UnicodeDecodeError ante cualquier acento o
        # símbolo. errors="replace" para que un byte suelto raro jamás tumbe
        # la ingesta — degrada el carácter, no el proceso.
        proceso = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_segundos,
        )
        # Blindaje de frontera (A1): si el hilo lector de subprocess muere u
        # otro fallo deja stdout/stderr a None, el tipo declarado de
        # ResultadoProceso (str) no debe violarse nunca.
        return ResultadoProceso(
            codigo_salida=proceso.returncode,
            stdout=proceso.stdout if proceso.stdout is not None else "",
            stderr=proceso.stderr if proceso.stderr is not None else "",
        )


class ClienteClaudeCLI:
    """Invoca `claude -p "<prompt>" --output-format json` en headless.

    Todo inyectable: `binario` (si no se pasa, lee `ONGS_AI_CLAUDE_CLI` del
    entorno, con "claude" como último recurso — igual que
    `adapters/persistencia/factory.crear_almacen` con `ONGS_AI_ENV`),
    `timeout_segundos` (defecto 120 s) y `ejecutor` (defecto: subproceso
    real; los tests SIEMPRE pasan un stub).
    """

    def __init__(
        self,
        *,
        binario: str | None = None,
        timeout_segundos: float | None = None,
        ejecutor: EjecutorSubproceso | None = None,
    ) -> None:
        self._binario = (
            binario if binario is not None else os.environ.get("ONGS_AI_CLAUDE_CLI", "claude")
        )
        self._timeout_segundos = (
            timeout_segundos if timeout_segundos is not None else TIMEOUT_SEGUNDOS_DEFECTO
        )
        self._ejecutor = ejecutor or EjecutorSubprocesoReal()
        self.llamadas = 0
        self.fallos = 0

    def preguntar(self, prompt: str) -> str | None:
        """Devuelve el texto de `result`, o `None` si cualquier paso falla."""
        self.llamadas += 1
        comando = [self._binario, "-p", prompt, "--output-format", "json"]

        try:
            resultado = self._ejecutor.ejecutar(comando, timeout_segundos=self._timeout_segundos)
        except subprocess.TimeoutExpired:
            logger.warning("claude CLI: timeout tras %ss", self._timeout_segundos)
            self.fallos += 1
            return None
        except OSError as exc:
            logger.warning("claude CLI: binario '%s' no ejecutable: %s", self._binario, exc)
            self.fallos += 1
            return None
        except UnicodeDecodeError as exc:
            # A2: cinturón y tirantes — con el ejecutor real esto ya no debería
            # ocurrir (encoding="utf-8", errors="replace" en A1), pero ningún
            # fallo de decodificación de un ejecutor (incl. uno inyectado en
            # tests) puede escapar hacia el dominio.
            logger.warning("claude CLI: fallo de decodificación de la salida: %s", exc)
            self.fallos += 1
            return None

        if resultado.codigo_salida != 0:
            logger.warning(
                "claude CLI: código de salida %s — stderr: %s",
                resultado.codigo_salida,
                (resultado.stderr or "").strip()[:500],
            )
            self.fallos += 1
            return None

        # A2: `resultado.stdout` está tipado como `str`, pero un hilo lector
        # muerto (fallo real del operador) puede dejarlo en `None` pese al
        # tipo declarado — nunca confiar ciegamente en el tipo de un valor
        # que cruza la frontera del proceso.
        if not isinstance(resultado.stdout, str) or not resultado.stdout.strip():
            logger.warning("claude CLI: stdout ausente o vacío")
            self.fallos += 1
            return None

        try:
            datos = json.loads(resultado.stdout)
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("claude CLI: salida no-JSON: %s", resultado.stdout.strip()[:500])
            self.fallos += 1
            return None

        if not isinstance(datos, dict):
            logger.warning("claude CLI: JSON de salida no es un objeto")
            self.fallos += 1
            return None

        if datos.get("is_error"):
            logger.warning("claude CLI: is_error=true — %s", str(datos.get("result"))[:500])
            self.fallos += 1
            return None

        texto = datos.get("result")
        if not isinstance(texto, str) or not texto.strip():
            logger.warning("claude CLI: 'result' ausente o vacío en la respuesta")
            self.fallos += 1
            return None

        return texto
