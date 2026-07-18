"""Guardarraíl determinista de elegibilidad — ADR-001 §2, F3
(engineering/ADR-001-contrato-de-datos.md).

`evaluar_elegibilidad` es una función PURA: sin IA, sin red, sin reloj
implícito (`fecha_referencia` siempre inyectada por el llamador). La IA
propone (capa explicativa, `ongs_ai.ia.explicacion_match`), el dominio valida
— este módulo es la única fuente de `resultado_elegibilidad_dura`.

Nota de alcance: `Convocatoria.requisitos_elegibilidad.ambito_territorial_requerido`
no se consume aquí — la única comparación de ámbito con datos utilizables
(región/provincia) es `Convocatoria.ambito_geografico` + `Convocatoria.region`/
`Convocatoria.provincia`, tal como pide el prompt F3. Se deja anotado en vez de
inventar una segunda comparación redundante.
"""
from __future__ import annotations

from datetime import date

from ongs_ai.dominio.entidades import (
    AmbitoTerritorial,
    Convocatoria,
    Entidad,
    EstadoIngesta,
    normalizar_forma_juridica,
    normalizar_texto_comparacion,
)
from ongs_ai.dominio.matching_estado import ResultadoElegibilidad


def _anios_completos(fecha_constitucion: date, fecha_referencia: date) -> int:
    """Años completos entre dos fechas — el aniversario no alcanzado no cuenta."""
    anios = fecha_referencia.year - fecha_constitucion.year
    if (fecha_referencia.month, fecha_referencia.day) < (
        fecha_constitucion.month,
        fecha_constitucion.day,
    ):
        anios -= 1
    return anios


def _evaluar_estado_ingesta(convocatoria: Convocatoria) -> tuple[bool, str]:
    if convocatoria.estado_ingesta is not EstadoIngesta.VERIFICADA:
        return False, (
            f"estado_ingesta: incumple — convocatoria sin verificar "
            f"(estado_ingesta={convocatoria.estado_ingesta.value}); nunca elegible "
            "por defecto (ADR-001 §2)"
        )
    return True, "estado_ingesta: cumple — convocatoria verificada"


def _evaluar_ambito(entidad: Entidad, convocatoria: Convocatoria) -> tuple[bool, str]:
    ambito = convocatoria.ambito_geografico

    if ambito is AmbitoTerritorial.NACIONAL:
        return True, "ambito_territorial: cumple — convocatoria nacional, acepta cualquier entidad"

    if ambito is AmbitoTerritorial.AUTONOMICO:
        region_conv, region_ent = convocatoria.region, entidad.region
        if not region_conv or not region_ent:
            return False, (
                "ambito_territorial: no_evaluable — convocatoria autonómica sin "
                "`region` en convocatoria y/o entidad"
            )
        cumple = normalizar_texto_comparacion(region_conv) == normalizar_texto_comparacion(region_ent)
        estado = "cumple" if cumple else "incumple"
        return cumple, (
            f"ambito_territorial: {estado} — convocatoria autonómica ({region_conv}), "
            f"entidad en ({region_ent})"
        )

    if ambito is AmbitoTerritorial.PROVINCIAL:
        provincia_conv, provincia_ent = convocatoria.provincia, entidad.provincia
        if not provincia_conv or not provincia_ent:
            return False, (
                "ambito_territorial: no_evaluable — convocatoria provincial sin "
                "`provincia` en convocatoria y/o entidad"
            )
        cumple = normalizar_texto_comparacion(provincia_conv) == normalizar_texto_comparacion(provincia_ent)
        estado = "cumple" if cumple else "incumple"
        return cumple, (
            f"ambito_territorial: {estado} — convocatoria provincial ({provincia_conv}), "
            f"entidad en ({provincia_ent})"
        )

    # LOCAL: el contrato (ADR-001) no tiene `municipio` — no evaluable en v1.
    return False, (
        "ambito_territorial: no_evaluable — convocatoria local; el contrato no "
        "tiene `municipio` en v1"
    )


def _evaluar_forma_juridica(entidad: Entidad, convocatoria: Convocatoria) -> tuple[bool, str]:
    requerido = convocatoria.requisitos_elegibilidad.forma_juridica_requerida
    if requerido is None:
        return True, "forma_juridica: cumple — no aplica (convocatoria sin requisito de forma jurídica)"

    normalizada = normalizar_forma_juridica(requerido)
    if normalizada is None:
        return False, f"forma_juridica: no_evaluable — texto sin mapeo cerrado ({requerido!r})"

    cumple = entidad.forma_juridica.tipo is normalizada
    estado = "cumple" if cumple else "incumple"
    return cumple, (
        f"forma_juridica: {estado} — requerida {normalizada.value}, "
        f"entidad {entidad.forma_juridica.tipo.value}"
    )


def _evaluar_antiguedad(
    entidad: Entidad, convocatoria: Convocatoria, fecha_referencia: date
) -> tuple[bool, str]:
    minimo = convocatoria.requisitos_elegibilidad.antiguedad_minima_anios
    if minimo is None:
        return True, "antiguedad_minima_anios: cumple — no aplica (convocatoria sin requisito de antigüedad)"

    anios = _anios_completos(entidad.fecha_constitucion, fecha_referencia)
    cumple = anios >= minimo
    estado = "cumple" if cumple else "incumple"
    return cumple, (
        f"antiguedad_minima_anios: {estado} — requeridos {minimo}, "
        f"entidad tiene {anios} años completos"
    )


def _evaluar_requisitos_formales(entidad: Entidad, convocatoria: Convocatoria) -> tuple[bool, str]:
    requeridos = convocatoria.requisitos_elegibilidad.requisitos_formales_requeridos
    if not requeridos:
        return True, "requisitos_formales: cumple — no aplica (convocatoria sin requisitos formales)"

    disponibles = set(entidad.requisitos_formales_disponibles)
    faltantes = [r for r in requeridos if r not in disponibles]
    if not faltantes:
        return True, "requisitos_formales: cumple — entidad acredita todos los requisitos formales exigidos"

    faltantes_txt = ", ".join(r.value for r in faltantes)
    return False, f"requisitos_formales: incumple — faltan: {faltantes_txt}"


def _linea_exclusiones(convocatoria: Convocatoria) -> str:
    exclusiones = convocatoria.requisitos_elegibilidad.exclusiones
    if not exclusiones:
        return "exclusiones: cumple — no hay exclusiones declaradas"
    exclusiones_txt = "; ".join(exclusiones)
    return f"exclusiones: revisar — no se evalúan automáticamente en v1: {exclusiones_txt}"


def evaluar_elegibilidad(
    entidad: Entidad, convocatoria: Convocatoria, fecha_referencia: date
) -> ResultadoElegibilidad:
    """Guardarraíl determinista `Entidad × Convocatoria -> ResultadoElegibilidad`.

    Cualquier requisito NO EVALUABLE hace `elegible=False` (no elegible
    automático no es lo mismo que excluida — `detalle` lo distingue línea a
    línea). Las `exclusiones` (texto libre) nunca bloquean automáticamente;
    aparecen en `detalle` como "revisar manualmente".
    """
    ok_ingesta, linea_ingesta = _evaluar_estado_ingesta(convocatoria)
    ok_ambito, linea_ambito = _evaluar_ambito(entidad, convocatoria)
    ok_forma, linea_forma = _evaluar_forma_juridica(entidad, convocatoria)
    ok_antiguedad, linea_antiguedad = _evaluar_antiguedad(entidad, convocatoria, fecha_referencia)
    ok_formales, linea_formales = _evaluar_requisitos_formales(entidad, convocatoria)
    linea_exclusiones = _linea_exclusiones(convocatoria)

    elegible = ok_ingesta and ok_ambito and ok_forma and ok_antiguedad and ok_formales
    detalle = "\n".join(
        (linea_ingesta, linea_ambito, linea_forma, linea_antiguedad, linea_formales, linea_exclusiones)
    )
    return ResultadoElegibilidad(elegible=elegible, detalle=detalle)
