"""`ExplicadorClaudeCLI` — PROMPT-018 A2. Sin red, sin CLI real: el cliente IA
siempre es un stub inyectado (regla de oro CLAUDE.md).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

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
from ongs_ai.dominio.matching_estado import ResultadoElegibilidad
from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI, ExplicadorStub, _prompt_explicacion
from ongs_ai.ia.factory import crear_generador_explicacion

AHORA = datetime(2026, 7, 18, tzinfo=timezone.utc)


class _ClienteStub:
    def __init__(self, respuesta: str | None) -> None:
        self._respuesta = respuesta
        self.prompts: list[str] = []

    def preguntar(self, prompt: str) -> str | None:
        self.prompts.append(prompt)
        return self._respuesta


def _entidad() -> Entidad:
    return Entidad(
        entidad_id="ent-1",
        nombre_legal="Asociación de Prueba",
        nif="B00000000",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 5, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=100_000, gastos_centimos=90_000, ejercicio=2025
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email="test@example.org"),
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


def _convocatoria() -> Convocatoria:
    return Convocatoria(
        convocatoria_id="conv-1",
        fuente=Fuente(portal="portal-x", url_origen="https://example.org/conv-1", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayudas a asociaciones",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 3, 1)),
        cuantias=Cuantias(),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


def test_generar_devuelve_el_texto_del_cliente():
    cliente = _ClienteStub("La entidad encaja porque cumple los requisitos.")
    explicador = ExplicadorClaudeCLI(cliente)
    resultado = ResultadoElegibilidad(elegible=True, detalle="todo cumple")

    texto = explicador.generar(_entidad(), _convocatoria(), resultado)

    assert texto == "La entidad encaja porque cumple los requisitos."
    assert len(cliente.prompts) == 1


def test_cliente_degradado_produce_cadena_vacia_no_excepcion():
    cliente = _ClienteStub(None)
    explicador = ExplicadorClaudeCLI(cliente)
    resultado = ResultadoElegibilidad(elegible=True, detalle="todo cumple")

    texto = explicador.generar(_entidad(), _convocatoria(), resultado)

    assert texto == ""


def test_prompt_solo_contiene_datos_ya_presentes_en_los_argumentos():
    entidad = _entidad()
    convocatoria = _convocatoria()
    resultado = ResultadoElegibilidad(elegible=True, detalle="ambito_territorial: cumple")

    prompt = _prompt_explicacion(entidad, convocatoria, resultado)

    assert entidad.nombre_legal in prompt
    assert entidad.enfermedad_o_colectivo in prompt
    assert convocatoria.objeto in prompt
    assert convocatoria.beneficiarios_elegibles in prompt
    assert resultado.detalle in prompt


def test_factory_entorno_test_devuelve_explicador_stub():
    assert isinstance(crear_generador_explicacion(entorno="test"), ExplicadorStub)


def test_factory_entorno_no_test_devuelve_explicador_claude_cli():
    assert isinstance(crear_generador_explicacion(entorno="produccion"), ExplicadorClaudeCLI)
