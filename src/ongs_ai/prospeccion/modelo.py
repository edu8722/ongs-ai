"""Prospecto — candidata de prospección fuera del contrato congelado (ADR-006 §2.3).

NO es `Entidad`: solo `prospecto_id` y `nombre` son obligatorios; el resto
refleja lo que el maestro de prospección trae, parcial y desigual. Reutiliza
los enums/value objects de `dominio.entidades` como VALORES (sin crear
dependencia inversa dominio -> prospeccion).

Un `Prospecto` NUNCA lleva `nif`, `datos_economicos_ejercicio_anterior` ni
`fecha_constitucion` — son datos verificados que solo existen tras la
conversión explícita a `Entidad` (F-consola.2, aún sin prompt).

`contacto_personal_nota` (columna "Personas visibles (cargo)" del maestro) es
**dato personal (⚠ PII)**: se guarda aquí pero JAMÁS debe aparecer en logs ni
en fixtures de test (usar valores sintéticos genéricos en tests).
"""
from __future__ import annotations

from dataclasses import dataclass

from ongs_ai.dominio.entidades import AmbitoTerritorial, Contacto, FormaJuridica, TipoActividad


@dataclass(frozen=True)
class Prospecto:
    prospecto_id: str
    nombre: str
    web: str | None = None
    ambito_territorial: AmbitoTerritorial | None = None
    region: str | None = None
    provincia: str | None = None
    enfermedad_o_colectivo: str | None = None
    actividades: tuple[TipoActividad, ...] = ()
    forma_juridica: FormaJuridica | None = None
    contacto: Contacto | None = None
    contacto_personal_nota: str | None = None  # ⚠ PII — nunca en logs/fixtures
    tamano: str | None = None
    fuente_maestro: str = ""
    notas: str | None = None
