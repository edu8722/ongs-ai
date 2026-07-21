"""Cliente del CLI de Claude Code en headless — PROMPT-018 A1.

El ejecutor de subproceso SIEMPRE es un stub inyectado: cero invocaciones al
binario `claude` real (regla de oro CLAUDE.md — tests herméticos, sin red).
"""
from __future__ import annotations

import subprocess

import pytest

from ongs_ai.ia.claude_cli import ClienteClaudeCLI, ResultadoProceso


class _EjecutorStub:
    def __init__(self, resultado=None, *, excepcion: Exception | None = None) -> None:
        self._resultado = resultado
        self._excepcion = excepcion
        self.comandos: list[list[str]] = []

    def ejecutar(self, comando: list[str], *, timeout_segundos: float) -> ResultadoProceso:
        self.comandos.append(comando)
        if self._excepcion is not None:
            raise self._excepcion
        return self._resultado


def _json_exitoso(texto: str) -> str:
    return f'{{"type":"result","subtype":"success","is_error":false,"result":"{texto}"}}'


def test_respuesta_exitosa_devuelve_el_texto_de_result():
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=_json_exitoso("ok"), stderr=""))
    cliente = ClienteClaudeCLI(binario="claude", ejecutor=ejecutor)

    texto = cliente.preguntar("hola")

    assert texto == "ok"
    assert cliente.llamadas == 1
    assert cliente.fallos == 0
    assert ejecutor.comandos == [["claude", "-p", "hola", "--output-format", "json"]]


def test_binario_ausente_degrada_limpio_sin_lanzar():
    ejecutor = _EjecutorStub(excepcion=FileNotFoundError("no existe el binario"))
    cliente = ClienteClaudeCLI(binario="claude-inexistente", ejecutor=ejecutor)

    texto = cliente.preguntar("hola")

    assert texto is None
    assert cliente.fallos == 1


def test_timeout_degrada_limpio_sin_lanzar():
    ejecutor = _EjecutorStub(excepcion=subprocess.TimeoutExpired(cmd="claude", timeout=1))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor, timeout_segundos=1)

    texto = cliente.preguntar("hola")

    assert texto is None
    assert cliente.fallos == 1


def test_codigo_salida_no_cero_degrada_limpio():
    ejecutor = _EjecutorStub(
        ResultadoProceso(codigo_salida=1, stdout="", stderr="límite de plan agotado")
    )
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    assert cliente.preguntar("hola") is None
    assert cliente.fallos == 1


def test_salida_no_json_degrada_limpio():
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout="esto no es json", stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    assert cliente.preguntar("hola") is None
    assert cliente.fallos == 1


def test_is_error_true_degrada_limpio():
    stdout = '{"type":"result","subtype":"error","is_error":true,"result":"límite agotado"}'
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=stdout, stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    assert cliente.preguntar("hola") is None
    assert cliente.fallos == 1


def test_result_ausente_degrada_limpio():
    stdout = '{"type":"result","subtype":"success","is_error":false}'
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=stdout, stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    assert cliente.preguntar("hola") is None
    assert cliente.fallos == 1


def test_result_vacio_degrada_limpio():
    stdout = '{"type":"result","subtype":"success","is_error":false,"result":"   "}'
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=stdout, stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    assert cliente.preguntar("hola") is None
    assert cliente.fallos == 1


def test_binario_por_defecto_lee_env_ongs_ai_claude_cli(monkeypatch):
    monkeypatch.setenv("ONGS_AI_CLAUDE_CLI", "claude-personalizado")
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=_json_exitoso("ok"), stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    cliente.preguntar("hola")

    assert ejecutor.comandos[0][0] == "claude-personalizado"


def test_binario_explicito_ignora_la_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("ONGS_AI_CLAUDE_CLI", "claude-del-entorno")
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=_json_exitoso("ok"), stderr=""))
    cliente = ClienteClaudeCLI(binario="claude-explicito", ejecutor=ejecutor)

    cliente.preguntar("hola")

    assert ejecutor.comandos[0][0] == "claude-explicito"


def test_sin_env_ni_binario_explicito_usa_claude_por_defecto(monkeypatch):
    monkeypatch.delenv("ONGS_AI_CLAUDE_CLI", raising=False)
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=_json_exitoso("ok"), stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    cliente.preguntar("hola")

    assert ejecutor.comandos[0][0] == "claude"


def test_cada_llamada_incrementa_el_contador_de_llamadas():
    ejecutor = _EjecutorStub(ResultadoProceso(codigo_salida=0, stdout=_json_exitoso("ok"), stderr=""))
    cliente = ClienteClaudeCLI(ejecutor=ejecutor)

    cliente.preguntar("uno")
    cliente.preguntar("dos")

    assert cliente.llamadas == 2
    assert cliente.fallos == 0
