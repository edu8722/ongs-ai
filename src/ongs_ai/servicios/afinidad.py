"""Scoring de afinidad + importe potencial — ADR-006 §2.5/§2.6, F-consola.1.

Solo lectura, determinista, **SIN LLM en el número** (regla de oro: la IA
propone, el dominio valida — aquí ni siquiera propone). Opera sobre una pareja
`(perfil, convocatoria)` donde `perfil` es una `Entidad` **o** un `Prospecto`
(evaluación degradada, ADR §2.6). El score NUNCA decide elegibilidad: eso lo
sigue haciendo, intacto, `dominio.elegibilidad.evaluar_elegibilidad` — este
servicio ordena y comunica sobre lo que el guardarraíl ya dictaminaría.

Nota de reutilización (ADR-006 §2.6, "nota de reutilización" — decisión
documentada aquí, elegida la alternativa conservadora): se **duplica** la
lógica por-requisito de `dominio/elegibilidad.py` en vez de refactorizarla
para aceptar `Entidad` y `Prospecto` con una forma común. Motivo: las dos
formas de perfil son estructuralmente distintas donde más importa
(`Entidad.forma_juridica` es `FormaJuridicaDeclarada`, `Prospecto.forma_juridica`
es `FormaJuridica` a secas; `Entidad.fecha_constitucion` y
`requisitos_formales_disponibles` son obligatorios, en `Prospecto` no existen)
y `tests/test_elegibilidad_deterministas.py` fija literalmente el texto
"no_evaluable" del guardarraíl — un refactor a una forma común arriesgaba esa
batería de 342 tests por un beneficio marginal de reutilización. La
equivalencia para el caso `Entidad` completa queda ANCLADA por
`tests/test_afinidad.py::test_anclaje_equivalencia_con_evaluar_elegibilidad`.

Vocabulario de esta capa (distinto, a propósito, del "no_evaluable" del
guardarraíl): cada requisito cae en `cumple` / `incumple` / `pendiente_de_dato`
— un prospecto con datos faltantes muestra "pendiente_de_dato", nunca se
inventa ni cuenta a favor ni en contra (ADR §2.6).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from ongs_ai.dominio.entidades import (
    AmbitoTerritorial,
    Convocatoria,
    DatosEconomicos,
    Entidad,
    EstadoIngesta,
    FormaJuridica,
    RequisitoFormal,
    TipoActividad,
    normalizar_forma_juridica,
    normalizar_texto_comparacion,
)
from ongs_ai.prospeccion.modelo import Prospecto

PESO_COBERTURA_REQUISITOS = 70
PESO_AFINIDAD_TEMATICA = 30
CAP_SCORE_NO_ELEGIBLE = 44  # como el prototipo (ADR §2.5, §6.4 CONFORME)

# Mapeo cerrado y testeable palabra-clave -> TipoActividad (ADR §2.5: "NADA de
# regex que puntúe sola" — mismo patrón que `_MAPA_FORMA_JURIDICA`, ADR-002).
_MAPA_PALABRA_CLAVE_ACTIVIDAD: dict[str, TipoActividad] = {
    "voluntariado": TipoActividad.VOLUNTARIADO,
    "voluntario": TipoActividad.VOLUNTARIADO,
    "voluntarios": TipoActividad.VOLUNTARIADO,
    "encuentro": TipoActividad.ENCUENTRO_DE_PACIENTES,
    "encuentros": TipoActividad.ENCUENTRO_DE_PACIENTES,
    "paciente": TipoActividad.ENCUENTRO_DE_PACIENTES,
    "pacientes": TipoActividad.ENCUENTRO_DE_PACIENTES,
    "charla": TipoActividad.CHARLAS_Y_SENSIBILIZACION,
    "charlas": TipoActividad.CHARLAS_Y_SENSIBILIZACION,
    "sensibilizacion": TipoActividad.CHARLAS_Y_SENSIBILIZACION,
    "formacion": TipoActividad.FORMACION,
    "curso": TipoActividad.FORMACION,
    "cursos": TipoActividad.FORMACION,
    "investigacion": TipoActividad.INVESTIGACION_Y_ESTUDIOS,
    "estudio": TipoActividad.INVESTIGACION_Y_ESTUDIOS,
    "estudios": TipoActividad.INVESTIGACION_Y_ESTUDIOS,
    "atencion": TipoActividad.ATENCION_DIRECTA_A_FAMILIAS,
    "familia": TipoActividad.ATENCION_DIRECTA_A_FAMILIAS,
    "familias": TipoActividad.ATENCION_DIRECTA_A_FAMILIAS,
}


class EstadoRequisito(str, Enum):
    CUMPLE = "cumple"
    INCUMPLE = "incumple"
    PENDIENTE_DE_DATO = "pendiente_de_dato"


@dataclass(frozen=True)
class DetalleRequisito:
    requisito: str
    estado: EstadoRequisito
    explicacion: str


@dataclass(frozen=True)
class ResultadoAfinidad:
    """Salida de solo lectura de `evaluar_afinidad` — explicable motivo a motivo."""

    score: int
    elegible: bool
    detalle_por_requisito: tuple[DetalleRequisito, ...]
    afinidad_tematica: int
    importe_potencial_minimo_centimos: int | None
    importe_potencial_maximo_centimos: int | None
    importe_no_publicado: bool
    capacidad_ejecucion: str | None = None
    dias_hasta_cierre: int | None = None


@dataclass(frozen=True)
class ResumenProspeccion:
    """Agregado por perfil sobre varias convocatorias (ADR §2.5)."""

    perfil_id: str
    numero_elegibles: int
    importe_potencial_minimo_centimos: int
    importe_potencial_maximo_centimos: int
    numero_elegibles_sin_importe_publicado: int


# --- Sub-evaluaciones por requisito (duplicado deliberado, ver docstring) --


def _anios_completos(fecha_constitucion: date, fecha_referencia: date) -> int:
    anios = fecha_referencia.year - fecha_constitucion.year
    if (fecha_referencia.month, fecha_referencia.day) < (
        fecha_constitucion.month,
        fecha_constitucion.day,
    ):
        anios -= 1
    return anios


def _evaluar_estado_ingesta(convocatoria: Convocatoria) -> DetalleRequisito:
    if convocatoria.estado_ingesta is not EstadoIngesta.VERIFICADA:
        return DetalleRequisito(
            "estado_ingesta",
            EstadoRequisito.INCUMPLE,
            f"convocatoria sin verificar (estado_ingesta={convocatoria.estado_ingesta.value})",
        )
    return DetalleRequisito("estado_ingesta", EstadoRequisito.CUMPLE, "convocatoria verificada")


def _evaluar_ambito(
    convocatoria: Convocatoria, *, region_perfil: str | None, provincia_perfil: str | None
) -> DetalleRequisito:
    ambito = convocatoria.ambito_geografico

    if ambito is AmbitoTerritorial.NACIONAL:
        return DetalleRequisito(
            "ambito_territorial", EstadoRequisito.CUMPLE,
            "convocatoria nacional, acepta cualquier perfil",
        )

    if ambito is AmbitoTerritorial.AUTONOMICO:
        region_conv = convocatoria.region
        if not region_conv or not region_perfil:
            return DetalleRequisito(
                "ambito_territorial", EstadoRequisito.PENDIENTE_DE_DATO,
                "convocatoria autonómica sin `region` en convocatoria y/o perfil",
            )
        cumple = normalizar_texto_comparacion(region_conv) == normalizar_texto_comparacion(region_perfil)
        estado = EstadoRequisito.CUMPLE if cumple else EstadoRequisito.INCUMPLE
        return DetalleRequisito(
            "ambito_territorial", estado,
            f"convocatoria autonómica ({region_conv}), perfil en ({region_perfil})",
        )

    if ambito is AmbitoTerritorial.PROVINCIAL:
        provincia_conv = convocatoria.provincia
        if not provincia_conv or not provincia_perfil:
            return DetalleRequisito(
                "ambito_territorial", EstadoRequisito.PENDIENTE_DE_DATO,
                "convocatoria provincial sin `provincia` en convocatoria y/o perfil",
            )
        cumple = normalizar_texto_comparacion(provincia_conv) == normalizar_texto_comparacion(provincia_perfil)
        estado = EstadoRequisito.CUMPLE if cumple else EstadoRequisito.INCUMPLE
        return DetalleRequisito(
            "ambito_territorial", estado,
            f"convocatoria provincial ({provincia_conv}), perfil en ({provincia_perfil})",
        )

    # LOCAL: el contrato no tiene `municipio` en v1 (mismo alcance que F3).
    return DetalleRequisito(
        "ambito_territorial", EstadoRequisito.PENDIENTE_DE_DATO,
        "convocatoria local; el contrato no tiene `municipio` en v1",
    )


def _evaluar_forma_juridica(
    convocatoria: Convocatoria, *, forma_perfil: FormaJuridica | None
) -> DetalleRequisito:
    requerido = convocatoria.requisitos_elegibilidad.forma_juridica_requerida
    if requerido is None:
        return DetalleRequisito(
            "forma_juridica", EstadoRequisito.CUMPLE,
            "no aplica (convocatoria sin requisito de forma jurídica)",
        )

    normalizada = normalizar_forma_juridica(requerido)
    if normalizada is None:
        return DetalleRequisito(
            "forma_juridica", EstadoRequisito.PENDIENTE_DE_DATO,
            f"texto sin mapeo cerrado ({requerido!r})",
        )

    if forma_perfil is None:
        return DetalleRequisito(
            "forma_juridica", EstadoRequisito.PENDIENTE_DE_DATO,
            "perfil sin forma jurídica declarada",
        )

    cumple = forma_perfil is normalizada
    estado = EstadoRequisito.CUMPLE if cumple else EstadoRequisito.INCUMPLE
    return DetalleRequisito(
        "forma_juridica", estado,
        f"requerida {normalizada.value}, perfil {forma_perfil.value}",
    )


def _evaluar_antiguedad(
    convocatoria: Convocatoria, fecha_referencia: date, *, fecha_constitucion: date | None
) -> DetalleRequisito:
    minimo = convocatoria.requisitos_elegibilidad.antiguedad_minima_anios
    if minimo is None:
        return DetalleRequisito(
            "antiguedad_minima_anios", EstadoRequisito.CUMPLE,
            "no aplica (convocatoria sin requisito de antigüedad)",
        )

    if fecha_constitucion is None:
        return DetalleRequisito(
            "antiguedad_minima_anios", EstadoRequisito.PENDIENTE_DE_DATO,
            "perfil sin fecha de constitución conocida",
        )

    anios = _anios_completos(fecha_constitucion, fecha_referencia)
    cumple = anios >= minimo
    estado = EstadoRequisito.CUMPLE if cumple else EstadoRequisito.INCUMPLE
    return DetalleRequisito(
        "antiguedad_minima_anios", estado,
        f"requeridos {minimo}, perfil tiene {anios} años completos",
    )


def _evaluar_requisitos_formales(
    convocatoria: Convocatoria, *, disponibles: frozenset[RequisitoFormal] | None
) -> DetalleRequisito:
    requeridos = convocatoria.requisitos_elegibilidad.requisitos_formales_requeridos
    if not requeridos:
        return DetalleRequisito(
            "requisitos_formales", EstadoRequisito.CUMPLE,
            "no aplica (convocatoria sin requisitos formales)",
        )

    if disponibles is None:
        return DetalleRequisito(
            "requisitos_formales", EstadoRequisito.PENDIENTE_DE_DATO,
            "perfil sin datos de requisitos formales acreditados",
        )

    faltantes = [r for r in requeridos if r not in disponibles]
    if not faltantes:
        return DetalleRequisito(
            "requisitos_formales", EstadoRequisito.CUMPLE,
            "perfil acredita todos los requisitos formales exigidos",
        )

    faltantes_txt = ", ".join(r.value for r in faltantes)
    return DetalleRequisito(
        "requisitos_formales", EstadoRequisito.INCUMPLE, f"faltan: {faltantes_txt}"
    )


def _evaluar_requisitos(
    convocatoria: Convocatoria,
    fecha_referencia: date,
    *,
    region_perfil: str | None,
    provincia_perfil: str | None,
    forma_perfil: FormaJuridica | None,
    fecha_constitucion: date | None,
    requisitos_formales_disponibles: frozenset[RequisitoFormal] | None,
) -> tuple[DetalleRequisito, ...]:
    return (
        _evaluar_estado_ingesta(convocatoria),
        _evaluar_ambito(convocatoria, region_perfil=region_perfil, provincia_perfil=provincia_perfil),
        _evaluar_forma_juridica(convocatoria, forma_perfil=forma_perfil),
        _evaluar_antiguedad(convocatoria, fecha_referencia, fecha_constitucion=fecha_constitucion),
        _evaluar_requisitos_formales(convocatoria, disponibles=requisitos_formales_disponibles),
    )


def _cobertura(detalles: tuple[DetalleRequisito, ...]) -> int:
    """Cobertura = cumplidos/evaluables (§2.5). `pendiente_de_dato` no cuenta
    ni a favor ni en contra en el SCORE (0-100)."""
    evaluables = [d for d in detalles if d.estado is not EstadoRequisito.PENDIENTE_DE_DATO]
    if not evaluables:
        return 0
    cumplidos = sum(1 for d in evaluables if d.estado is EstadoRequisito.CUMPLE)
    return round(100 * cumplidos / len(evaluables))


def _es_elegible(detalles: tuple[DetalleRequisito, ...]) -> bool:
    """`elegible=True` exige TODOS los requisitos en `cumple` -- ni un
    `incumple` ni un `pendiente_de_dato` cuelan como elegible (mismo criterio
    que el guardarraíl: "no elegible automático no es lo mismo que excluida",
    dominio/elegibilidad.py). Es lo que ancla la equivalencia con
    `evaluar_elegibilidad` para el caso Entidad completa (donde nunca hay
    pendientes) y lo que evita prometer una elegibilidad que un Prospecto con
    datos faltantes no puede confirmar."""
    return all(d.estado is EstadoRequisito.CUMPLE for d in detalles)


def _afinidad_tematica(actividades_perfil: tuple[TipoActividad, ...], convocatoria: Convocatoria) -> int:
    """Solape determinista actividades del perfil <-> señales del texto de la
    convocatoria. Sin señales detectadas o perfil sin actividades -> afinidad
    neutra baja (0), nunca penalización inventada (ADR §2.5)."""
    if not actividades_perfil:
        return 0
    texto = normalizar_texto_comparacion(f"{convocatoria.objeto} {convocatoria.beneficiarios_elegibles}")
    palabras = set(texto.split())
    tipos_detectados = {
        tipo for palabra, tipo in _MAPA_PALABRA_CLAVE_ACTIVIDAD.items() if palabra in palabras
    }
    if not tipos_detectados:
        return 0
    solape = len(set(actividades_perfil) & tipos_detectados)
    return round(100 * solape / len(tipos_detectados))


def _combinar_score(cobertura: int, afinidad_tematica: int, elegible: bool) -> int:
    bruto = round(
        (PESO_COBERTURA_REQUISITOS * cobertura + PESO_AFINIDAD_TEMATICA * afinidad_tematica) / 100
    )
    if not elegible:
        return min(bruto, CAP_SCORE_NO_ELEGIBLE)
    return bruto


def _describir_capacidad(datos: DatosEconomicos, importe_maximo_centimos: int) -> str:
    """Señal APARTE (nunca en el score, ADR §2.5) — solo se calcula cuando hay
    datos_economicos, es decir, para una Entidad ya captada."""
    if importe_maximo_centimos <= 0:
        return "sin importe máximo de referencia"
    return (
        f"ingresos ejercicio {datos.ejercicio}: {datos.ingresos_centimos} céntimos "
        f"frente a un importe máximo de {importe_maximo_centimos} céntimos "
        "(informativa, no entra en el score)"
    )


def _valores_perfil(
    perfil: Entidad | Prospecto,
) -> tuple[
    str | None,
    str | None,
    FormaJuridica | None,
    date | None,
    frozenset[RequisitoFormal] | None,
    tuple[TipoActividad, ...],
    DatosEconomicos | None,
]:
    if isinstance(perfil, Entidad):
        return (
            perfil.region,
            perfil.provincia,
            perfil.forma_juridica.tipo,
            perfil.fecha_constitucion,
            frozenset(perfil.requisitos_formales_disponibles),
            tuple(a.tipo for a in perfil.actividades),
            perfil.datos_economicos_ejercicio_anterior,
        )
    # Prospecto (perfil parcial, ADR §2.6): antigüedad y requisitos formales
    # SIEMPRE pendiente_de_dato -- el maestro no los trae.
    return (
        perfil.region,
        perfil.provincia,
        perfil.forma_juridica,
        None,
        None,
        perfil.actividades,
        None,
    )


def _perfil_id(perfil: Entidad | Prospecto) -> str:
    return perfil.entidad_id if isinstance(perfil, Entidad) else perfil.prospecto_id


def evaluar_afinidad(
    perfil: Entidad | Prospecto, convocatoria: Convocatoria, fecha_referencia: date
) -> ResultadoAfinidad:
    """Scoring determinista `(Entidad | Prospecto) × Convocatoria -> ResultadoAfinidad`.

    NO decide elegibilidad (eso es `dominio.elegibilidad.evaluar_elegibilidad`,
    intacto) -- ordena y comunica sobre el mismo criterio duro.
    """
    (
        region, provincia, forma, fecha_constitucion, formales_disponibles, actividades, datos_economicos,
    ) = _valores_perfil(perfil)

    detalles = _evaluar_requisitos(
        convocatoria,
        fecha_referencia,
        region_perfil=region,
        provincia_perfil=provincia,
        forma_perfil=forma,
        fecha_constitucion=fecha_constitucion,
        requisitos_formales_disponibles=formales_disponibles,
    )
    cobertura = _cobertura(detalles)
    elegible = _es_elegible(detalles)
    afinidad = _afinidad_tematica(actividades, convocatoria)
    score = _combinar_score(cobertura, afinidad, elegible)

    importe_min = importe_max = None
    importe_no_publicado = False
    if elegible:
        importe_max = convocatoria.cuantias.importe_maximo_centimos
        importe_min = convocatoria.cuantias.importe_minimo_centimos
        if importe_max is None:
            importe_no_publicado = True

    capacidad = None
    if datos_economicos is not None and convocatoria.cuantias.importe_maximo_centimos:
        capacidad = _describir_capacidad(datos_economicos, convocatoria.cuantias.importe_maximo_centimos)

    dias_hasta_cierre = None
    if convocatoria.plazos.fecha_cierre is not None:
        dias_hasta_cierre = (convocatoria.plazos.fecha_cierre - fecha_referencia).days

    return ResultadoAfinidad(
        score=score,
        elegible=elegible,
        detalle_por_requisito=detalles,
        afinidad_tematica=afinidad,
        importe_potencial_minimo_centimos=importe_min,
        importe_potencial_maximo_centimos=importe_max,
        importe_no_publicado=importe_no_publicado,
        capacidad_ejecucion=capacidad,
        dias_hasta_cierre=dias_hasta_cierre,
    )


def resumen_prospeccion(
    perfil: Entidad | Prospecto, convocatorias: list[Convocatoria], fecha_referencia: date
) -> ResumenProspeccion:
    """Agregado de `evaluar_afinidad` sobre varias convocatorias (ADR §2.5):
    importe potencial en RANGO [suma mínimos, suma máximos] SOLO de las
    elegibles, etiquetado techo teórico por el llamador (nunca predicción)."""
    resultados = [evaluar_afinidad(perfil, convocatoria, fecha_referencia) for convocatoria in convocatorias]
    elegibles = [r for r in resultados if r.elegible]
    return ResumenProspeccion(
        perfil_id=_perfil_id(perfil),
        numero_elegibles=len(elegibles),
        importe_potencial_minimo_centimos=sum(r.importe_potencial_minimo_centimos or 0 for r in elegibles),
        importe_potencial_maximo_centimos=sum(r.importe_potencial_maximo_centimos or 0 for r in elegibles),
        numero_elegibles_sin_importe_publicado=sum(1 for r in elegibles if r.importe_no_publicado),
    )
