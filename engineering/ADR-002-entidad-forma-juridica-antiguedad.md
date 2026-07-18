# ADR-002 — Entidad gana forma jurídica y fecha de constitución

- **Estado:** ACEPTADO (v1)
- **Fecha:** 2026-07-18
- **Regla de oro afectada:** CONTRATO CONGELADO (CLAUDE.md) — amplía ADR-001
  (`engineering/ADR-001-contrato-de-datos.md`); no lo sustituye ni lo edita.
- **Nota de proceso:** por excepción, este ADR se redacta E IMPLEMENTA en la misma
  sesión (autorizado expresamente por el arquitecto). Es un cambio pequeño y cerrado
  de dos campos obligatorios más su normalizador; separar ADR y código en dos
  sesiones no aporta nada aquí. La disciplina de "ADR primero, código después" sigue
  siendo la norma para cambios de contrato de mayor alcance.

## 1. Contexto

Auditoría de F1 (ADR-001) detectó una incoherencia interna del contrato:
`Convocatoria.requisitos_elegibilidad` permite exigir `antiguedad_minima_anios` y
`forma_juridica_requerida`, pero `Entidad` no tiene ningún campo del que derivar la
antigüedad ni la forma jurídica de la entidad. El guardarraíl determinista de F3
(`Entidad × Convocatoria → resultado_elegibilidad_dura`) no tendría, hoy, contra qué
evaluar esos dos requisitos.

## 2. Decisión

### 2.1 `Entidad.forma_juridica`

Sigue el precedente ya aceptado de `ActividadDeclarada` (ADR-001 §1.3): un value
object con enum cerrado + campo libre solo cuando el enum no basta.

- Enum cerrado `FormaJuridica` v1: `asociacion`, `fundacion`,
  `federacion_o_confederacion`, `otra`. Extensible SOLO por ADR (misma regla que
  `TipoActividad`).
- Value object `FormaJuridicaDeclarada(tipo: FormaJuridica, descripcion: str | None)`.
  `descripcion` es obligatoria cuando `tipo is FormaJuridica.OTRA` (mismo invariante
  que `ActividadDeclarada` con `TipoActividad.OTRO`), y opcional en el resto.
- Campo nuevo y **obligatorio**: `Entidad.forma_juridica: FormaJuridicaDeclarada`.

### 2.2 `Entidad.fecha_constitucion`

- Campo nuevo y **obligatorio**: `Entidad.fecha_constitucion: date`.
- La antigüedad de la entidad **nunca se almacena** como campo derivado (evitaría
  quedar desincronizada con el paso del tiempo). Se calcula, cuando F3 lo necesite,
  contra una fecha de referencia explícita pasada por parámetro a la función de
  cálculo — jamás un "ahora" implícito leído dentro del dominio (regla de oro ya
  vigente: el dominio no llama a relojes ni redes). La función de cálculo en sí
  (`Entidad.fecha_constitucion` + `fecha_referencia` → años) es responsabilidad de
  F3 (`elegibilidad.py`, guardarraíl determinista) y queda fuera del alcance de este
  ADR: aquí solo se congela el dato de origen que F3 va a necesitar.

### 2.3 Normalización `forma_juridica_requerida` (texto libre IA) → `FormaJuridica` (enum de Entidad)

`Convocatoria.requisitos_elegibilidad.forma_juridica_requerida` sigue siendo un
string libre poblado por extracción IA (ADR-001 §2 no cambia: la IA rellena, nunca
decide). Para que el guardarraíl de F3 pueda comparar ese string contra el enum de
`Entidad.forma_juridica.tipo`, se introduce una normalización **determinista**, en
dominio, sin LLM en el camino:

- Función `normalizar_forma_juridica(texto: str) -> FormaJuridica | None`.
- Algoritmo: minúsculas + eliminación de tildes + colapso de espacios, contra un
  **mapeo cerrado** de sinónimos frecuentes → miembro del enum (p. ej. "asociación",
  "asociacion sin animo de lucro" → `ASOCIACION`; "fundación" → `FUNDACION`;
  "federación", "confederación" → `FEDERACION_O_CONFEDERACION`).
- `FormaJuridica.OTRA` **nunca** es un resultado de la normalización automática: es
  una declaración humana de Entidad (con descripción obligatoria), no algo que un
  texto de convocatoria pueda mapear de forma fiable. Si el texto no coincide con
  ningún sinónimo cerrado, la función devuelve `None`.
- Consecuencia de `None` (no es código de este ADR, es contrato para quien
  implemente F3): el requisito queda **NO EVALUABLE** → el guardarraíl NO marca
  elegibilidad automática positiva y añade marca de revisión manual. Degrada limpio,
  nunca inventa (regla de oro ya vigente).
- El mapeo vive en dominio puro (mismo módulo o vecino de `entidades.py`), nunca en
  la capa de IA — la extracción IA no participa en esta normalización.

### 2.4 Obligatoriedad y datos existentes

- Ambos campos (`forma_juridica`, `fecha_constitucion`) son **obligatorios** en el
  contrato desde ya: no hay caso de negocio en el que una Entidad real carezca de
  ellos.
- No hay datos productivos todavía: la BD local (`var/ongs_ai.sqlite3`) es
  desechable y se regenera sin coste. Cualquier registro viejo en `var/` que no
  tenga estos campos caerá en la degradación limpia ya testeada del adapter
  (`AlmacenSQLite._decodificar`: dato feo → se omite, se cuenta en
  `registros_omitidos_por_corrupcion`, nunca se lanza al dominio) — no hace falta
  migración de datos, solo el `ALTER TABLE`/esquema idempotente ya existente sigue
  sirviendo porque la persistencia serializa el dataclass completo a `datos_json`.

## 3. Alternativas consideradas y por qué no

- **Guardar `antiguedad_anios` como campo derivado en vez de `fecha_constitucion`.**
  Descartada: un entero derivado se desincroniza con el tiempo real salvo que se
  reescriba periódicamente, lo que viola el patrón de "asientos inmutables, nunca
  reescrituras" y reintroduce un job de mantenimiento innecesario. La fecha fuente
  es el dato estable; el cálculo es una función pura, no un estado a mantener.
- **Dejar `forma_juridica_requerida` como string libre en ambos lados (Entidad y
  Convocatoria) y comparar por igualdad de string.** Descartada: dos textos
  equivalentes ("asociación" vs "Asociación sin ánimo de lucro") no serían iguales
  por comparación literal, lo que rompería el guardarraíl determinista de F3 con
  falsos negativos. Se necesita un enum cerrado en el lado de Entidad (dato
  verificado) y una normalización determinista en el lado de Convocatoria (dato
  extraído).
- **Que la IA decida la equivalencia semántica en tiempo de evaluación (p. ej.
  preguntarle "¿asociación sin ánimo de lucro es lo mismo que asociación?").**
  Descartada: viola la regla de oro "la IA propone, el dominio valida" (ya
  justificada en ADR-001 §3.2) — introduciría no-determinismo en una decisión de
  elegibilidad binaria y auditable.

## 4. Consecuencias

- CLAUDE.md, sección CONTRATO CONGELADO: se añade la referencia a este ADR junto a
  ADR-001.
- `Entidad` (`src/ongs_ai/dominio/entidades.py`) gana `forma_juridica` y
  `fecha_constitucion` como campos obligatorios; el normalizador determinista se
  añade en el mismo módulo de dominio.
- `AlmacenSQLite` (serialización/deserialización) y fixtures de test se actualizan
  para incluir los campos nuevos en ambos adapters (memoria, SQLite).
- F3 (matching determinista) queda desbloqueada para consumir estos campos; la
  función de cálculo de antigüedad y el uso del normalizador dentro del guardarraíl
  se implementan en el prompt de F3, no aquí.
- Ningún dato de negocio real se pierde: no hay entidad piloto captada todavía.
