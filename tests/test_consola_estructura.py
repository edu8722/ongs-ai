"""Test estructural de separación de roles — ADR-006 §2.1/§4.1.

Por inspección de las rutas MONTADAS (no de disciplina de cada handler):
ninguna ruta bajo `/consola` depende de `entidad_actual`, y ninguna ruta
fuera de `/consola` depende de `operador_actual`/`solo_loopback`. Se añade,
como red adicional, un test de import: ningún módulo de rutas de tenant
importa `dependencias_operador` y viceversa (mínimo sugerido por el ADR).
"""
from __future__ import annotations

import ast
from pathlib import Path

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria
from ongs_ai.servicios.autenticacion import EnviadorEnlaceAccesoStub
from ongs_ai.web.app import crear_app
from ongs_ai.web.dependencias import entidad_actual
from ongs_ai.web.dependencias_operador import operador_actual, solo_loopback

_RAIZ_RUTAS = Path(__file__).resolve().parents[1] / "src" / "ongs_ai" / "web" / "rutas"


def _todas_las_dependencias(dependant) -> set:
    encontradas = {dependant.call} if dependant.call is not None else set()
    for sub in dependant.dependencies:
        encontradas |= _todas_las_dependencias(sub)
    return encontradas


def _rutas_reales(routes) -> list:
    """FastAPI monta `include_router` como un wrapper `_IncludedRouter` sin
    `.path`/`.dependant` propios -- las `APIRoute` reales cuelgan de
    `original_router.routes`. Recorre recursivamente hasta encontrarlas."""
    encontradas = []
    for route in routes:
        if hasattr(route, "dependant"):
            encontradas.append(route)
        elif hasattr(route, "original_router"):
            encontradas.extend(_rutas_reales(route.original_router.routes))
    return encontradas


def _app_de_prueba():
    return crear_app(
        secret_key="clave-de-test",
        almacen=AlmacenMemoria(),
        enviador_enlace=EnviadorEnlaceAccesoStub(),
        operador_clave="clave-operador-de-test",
    )


def test_ninguna_ruta_de_consola_depende_de_entidad_actual():
    app = _app_de_prueba()
    rutas = _rutas_reales(app.routes)
    rutas_consola = [r for r in rutas if r.path.startswith("/consola")]
    assert rutas_consola, "No se montó ninguna ruta /consola — revisa app.py"

    for ruta in rutas_consola:
        dependencias = _todas_las_dependencias(ruta.dependant)
        assert entidad_actual not in dependencias, f"{ruta.path} depende de entidad_actual"


def test_ninguna_ruta_de_tenant_depende_de_operador_actual_ni_solo_loopback():
    app = _app_de_prueba()
    rutas = _rutas_reales(app.routes)
    rutas_tenant = [r for r in rutas if not r.path.startswith("/consola")]
    assert rutas_tenant, "No se montó ninguna ruta de tenant — revisa app.py"

    for ruta in rutas_tenant:
        dependencias = _todas_las_dependencias(ruta.dependant)
        assert operador_actual not in dependencias, f"{ruta.path} depende de operador_actual"
        assert solo_loopback not in dependencias, f"{ruta.path} depende de solo_loopback"


def _nombres_importados(ruta_fichero: Path) -> set[str]:
    arbol = ast.parse(ruta_fichero.read_text(encoding="utf-8"))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
        elif isinstance(nodo, ast.Import):
            for alias in nodo.names:
                nombres.add(alias.name)
    return nombres


def test_modulos_de_tenant_no_importan_dependencias_operador():
    ficheros_tenant = [
        _RAIZ_RUTAS / "auth.py",
        _RAIZ_RUTAS / "panel.py",
        _RAIZ_RUTAS / "propuestas.py",
    ]
    for fichero in ficheros_tenant:
        importados = _nombres_importados(fichero)
        assert not any("dependencias_operador" in nombre for nombre in importados), (
            f"{fichero} importa dependencias_operador — viola separación de roles (ADR-006 §2.1)"
        )


def test_modulos_de_consola_no_importan_dependencias_de_tenant():
    raiz_consola = _RAIZ_RUTAS / "consola"
    ficheros_consola = sorted(raiz_consola.glob("*.py"))
    assert ficheros_consola, "No se encontraron módulos de rutas de consola"

    for fichero in ficheros_consola:
        importados = _nombres_importados(fichero)
        assert not any(
            nombre == "ongs_ai.web.dependencias" for nombre in importados
        ), f"{fichero} importa web.dependencias (entidad_actual) — viola separación de roles (ADR-006 §2.1)"
