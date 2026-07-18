"""Test anti-hardcoding (CLAUDE.md — regla de oro, ver ADR §4.3).

`enfermedad_o_colectivo` es un valor de DATO de Entidad, nunca un enum ni una
constante de plataforma. Este test crea una enfermedad rara inventada por el
propio test y comprueba que ningún fichero de `src/ongs_ai/` la menciona ni
depende de su valor literal.
"""
from datetime import date, datetime, timezone
from pathlib import Path

from ongs_ai.dominio.entidades import (
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    DatosEconomicos,
    Entidad,
    FormaJuridica,
    FormaJuridicaDeclarada,
    RequisitoFormal,
    TipoActividad,
)

RAIZ_SRC = Path(__file__).resolve().parents[1] / "src" / "ongs_ai"

ENFERMEDAD_INVENTADA = "sindrome-ficticio-xk47-testeria-nunca-real"


def test_enfermedad_inventada_no_esta_hardcodeada_en_la_plataforma():
    entidad = Entidad(
        entidad_id="ent-anti-hardcoding",
        nombre_legal="Asociación de Prueba Anti-Hardcoding",
        nif="B99999999",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2005, 6, 15),
        enfermedad_o_colectivo=ENFERMEDAD_INVENTADA,
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=1_000, gastos_centimos=500, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email="prueba@example.org"),
        creado_en=datetime(2026, 7, 18, tzinfo=timezone.utc),
        actualizado_en=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )
    assert entidad.enfermedad_o_colectivo == ENFERMEDAD_INVENTADA

    ficheros_py = list(RAIZ_SRC.rglob("*.py"))
    assert ficheros_py, "No se encontraron ficheros fuente bajo src/ongs_ai/"

    for fichero in ficheros_py:
        contenido = fichero.read_text(encoding="utf-8")
        assert ENFERMEDAD_INVENTADA not in contenido, (
            f"{fichero} menciona/depende de un valor de dato de Entidad "
            "(enfermedad_o_colectivo) — viola anti-hardcoding"
        )
