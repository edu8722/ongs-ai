"""Batería de búsquedas dirigidas contra la BDNS — PROMPT-024 A1.

CONTEXTO: `ejecutar_ingesta` solo paginaba las publicaciones MÁS RECIENTES de
la búsqueda general de `/convocatorias/busqueda` (una ventana de decenas
sobre ~639k) — nunca BUSCABA. El operador aportó el histórico real de
concesiones de una asociación real (Aniridia, 2022-2024: 15 ayudas — IRPF
0,7% estatal y autonómico, mantenimiento de servicios CAM, fomento del
asociacionismo municipal, diputaciones...) y casi ninguna aparecía en la
base. El arquitecto verificó contra la API real (2026-07-22) que
`/convocatorias/busqueda` acepta `descripcion=` como filtro de texto REAL
(`descripcion=IRPF` -> 424 resultados reales, confirmado con
`totalElements`; NO es una lista de nombres de ONG — es vocabulario de
convocatoria pública).

Esta tabla es ESTRATEGIA DE BÚSQUEDA (config del producto: qué tipos de
convocatoria cubrir), no un dato de ONG/cliente concreto — el anti-hardcoding
de CLAUDE.md protege datos de entidades/cONGs reales, no la propia lógica de
cobertura de la plataforma (igual que la tabla cerrada de nombres de CCAA en
`adapters/ingesta/bdns.py` no es un dato de cliente). Cambiarla en el futuro
(añadir/quitar término) es una decisión de producto: documenta el motivo en
un comentario junto al término, nunca borres uno sin dejar rastro de por qué.

Cada término se envía tal cual como `FiltrosBusqueda.descripcion` (mismo
parámetro ya verificado, `FuenteBDNS._params_busqueda`) — el dedupe por
código BDNS (`ingestar`, clave natural portal+url_origen) evita duplicados
cuando dos términos traen la misma convocatoria.
"""
from __future__ import annotations

TERMINOS_BUSQUEDA_DIRIGIDA: tuple[str, ...] = (
    # La ayuda MÁS FRECUENTE en el histórico real de Aniridia (IRPF 0,7%
    # estatal y autonómico) — el término que motivó este hallazgo.
    "IRPF",
    # Cláusula habitual de convocatorias generalistas de acción social donde
    # caben asociaciones de enfermedades raras aunque la convocatoria no
    # nombre ninguna enfermedad concreta.
    "fines sociales",
    "interés general",
    # Categoría legal bajo la que la BDNS suele agrupar ayudas relacionadas
    # con enfermedades raras (discapacidad como paraguas administrativo).
    "discapacidad",
    "enfermedades raras",
    # Requisito/actividad habitual en las bases de este tipo de convocatoria
    # (ver `TipoActividad`/`RequisitoFormal` del dominio).
    "voluntariado",
    "asociacionismo",
    "entidades sin ánimo de lucro",
    "tercer sector",
    "ayuda mutua",
    "inclusión",
)
