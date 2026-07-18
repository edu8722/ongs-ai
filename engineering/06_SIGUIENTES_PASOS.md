# 06. SIGUIENTES PASOS — pizarra viva

> **Regla:** aquí vive SOLO lo pendiente y el estado reciente. Lo cerrado → `06_HISTORICO.md`
> en el mismo commit. El histórico no se lee salvo arqueología.

## TRASPASO DEL ARQUITECTO — cómo trabaja este proyecto

DOS papeles: **el arquitecto** (una sesión de chat que audita, escribe los prompts y
mantiene este documento) y **los empleados** (sesiones de Claude Code que ejecutan un
prompt cada una y commitean con el ritual de CLAUDE.md).

### Prompt de arranque del arquitecto (pégalo literal en la sesión nueva)

```
Asume el rol de ARQUITECTO y asesor de startup del proyecto
ONGs-AI (C:\dev\ongs-ai). Antes de opinar, lee en este orden: CLAUDE.md
(reglas de oro innegociables) y engineering/06_SIGUIENTES_PASOS.md COMPLETO
(traspaso, estado vivo y cola). Tu papel NO es escribir código de
producción: es (1) auditar cada commit de las sesiones empleadas leyendo el
CÓDIGO REAL del repo (nunca fiarte solo del resumen de la sesión),
(2) escribir los prompts listos para lanzar con el preámbulo de política de
decisión del 06, (3) actualizar el 06 EN EL MISMO TURNO en que cambies algo
del plan, (4) convertir mi feedback de producto en specs, y (5) decirme el
orden de la cola cuando lo pregunte. Empieza: dime el estado actual y la
siguiente acción según este documento.
```

### Contrato de comportamiento del arquitecto

- **Evidencia antes que hipótesis**: audita abriendo los ficheros tocados; ante un bug,
  pide consola/trazas antes de teorizar; asume que su propia hipótesis puede estar mal.
- **Medir antes de optimizar**; re-medir al aterrizar.
- **Veredicto explícito**: APROBADO o lista de correcciones; HECHO <hash> en la pizarra.
- **El 06 se actualiza en el mismo turno.** Prompt nuevo = item en cola + texto completo
  (con su MODELO en la cabecera: Sonnet para specs cerradas, Opus para diseño/ADRs).
- **Diseños grandes = ADR primero** (con Opus, sin código): decisión, alternativas,
  consecuencias, fases con prompts completos y preguntas al operador con default.
- **Paralelismo**: solo ficheros REALMENTE disjuntos; el fichero central lo decide — una
  línea compartida = SERIE. Ante duda: serie.
- **Fricciones del entorno Cowork** (misma máquina): el mount sandbox↔host miente con
  ficheros recién editados — el HOST es la verdad; desde sandbox solo `git log`/`git show`
  (jamás status/diff: dejan index.lock huérfanos); JSONs/salidas grandes SIEMPRE como
  archivo, jamás pegadas al chat; Lighthouse lo mide el operador.

### Preámbulo común de política de decisión (copiar al inicio de todo prompt)

> POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda
> de implementación, elige la opción más conservadora/reversible y DOCUMENTA
> la decisión en el resumen final; ante ambigüedad de alcance, implementa lo
> literal del prompt y anota lo que dejaste fuera; jamás inventes datos ni
> mediciones (si necesitas un dato que no tienes, esa sí es pregunta
> legítima); las preguntas no bloqueantes van AGRUPADAS al final del
> trabajo, no en medio. Reglas de oro de CLAUDE.md por encima de todo — si
> el prompt y CLAUDE.md chocan, gana CLAUDE.md y me lo señalas. Antes de
> tocar un fichero grande, Grep al símbolo y lee el rango — nunca el
> fichero entero.

---

## ESTADO VIVO

- **2026-07-18 (noche) — F1 CERRADA Y APROBADA (7db6c5d + corrección 1dc7c44,
  48 tests, pushed).** Contrato ADR-001 implementado, puerto cumplido en ambos
  adapters, anti-fuga y round-trip parametrizados, degradación limpia. Detalle en
  histórico. Estado de fases: F1 ✔ · F2 bloqueada (lista de portales) · F3 siguiente
  tras ADR-002 · F4/F5 lejos.
- **PROMPT-006/ADR-002 CERRADA (2026-07-18):** `Entidad` gana `forma_juridica`
  (`FormaJuridicaDeclarada` + enum `FormaJuridica`) y `fecha_constitucion` (`date`),
  ambos obligatorios, más `normalizar_forma_juridica` (mapeo cerrado determinista,
  sin LLM) para casar `Convocatoria.requisitos_elegibilidad.forma_juridica_requerida`
  contra el enum — cierra la grieta de contrato que dejaba a F3 sin datos contra los
  que evaluar antigüedad/forma jurídica. Detalle en histórico. **F3 (PROMPT-007) es
  la siguiente acción** — lo redacta el arquitecto tras auditar este cierre.
- **2026-07-18 — NUEVO ENCARGO DE PRODUCTO (feedback del operador → spec):** la
  plataforma capta proactivamente. Dos investigaciones profundas DEL ARQUITECTO (no
  son prompts de código): **R1 — catálogo de fuentes de subvenciones** (estatales/
  autonómicas/locales/privadas: URL, cómo se consulta, qué elegibilidad publican) →
  sustituye la "lista de portales" pendiente del operador y desbloquea la spec de F2;
  **R2 — directorio de asociaciones de EERR en España** con contacto público → nutre
  captación y candidatas a piloto. Decisiones del operador: R1 primero; R2 INCLUYE
  personas visibles públicamente (⚠ dato personal: el fichero de prospección se trata
  fuera de git — `investigacion/asociaciones*` gitignorado; responsable del
  tratamiento: el operador); formato Excel + informe. R1 EN CURSO por el arquitecto.
- **Lección para el ritual** (sigue vigente, 2 casos): los resúmenes de sesión
  afirman cosas que el código desmiente — mensaje de commit en PROMPT-002, "decisión
  conservadora" que rompía el puerto en PROMPT-004. Auditar SIEMPRE el artefacto real.
- Cerrado al histórico: PROMPT-001 (2101890), 002 (1f50ed8), 003/ADR-001 (6423f46),
  004+005/F1 (7db6c5d+1dc7c44), 006/ADR-002 (63 tests). Stack Python/SQLite/pytest
  hermético.
- **Decisiones del operador (2026-07-18) sobre ADR §6 — cerradas:** (1) módulo
  `src/ongs_ai/dominio/` ✔; (2) **F5 AMPLIADO sobre el default**: no solo memoria
  narrativa — análisis de TODO lo que la entidad necesita para poder presentarse
  (checklist de requisitos documentales con gap: qué tiene / qué le falta) + borrador
  de TODOS los documentos entregables a partir de los datos que la entidad facilite
  (probable ADR de ampliación de contrato al llegar F5: entidad DocumentoRequerido);
  (3) aviso F4 = **email + panel** en la plataforma (el panel adelanta la necesidad
  del esqueleto web — subir en backlog); (4) Match nuevo tras descartada ✔;
  (5) dedupe `portal`+`url_origen` ✔.
- **Duele:** sin lista concreta de portales/fuentes (bloquea el prompt de F2) y sin
  entidad piloto. Test anti-hardcoding v1 es canario débil — endurecer en F3+.
- **Remoto git ACTIVO** (2026-07-18): `origin` = github.com/edu8722/ongs-ai (privado);
  `origin/main` = 7db6c5d. El `git push` del ritual ya es OBLIGATORIO en cada cierre
  de sesión empleada — se acabó el "anótalo".

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

- Ninguno listo para copiar todavía: PROMPT-007 (F3 — matching determinista + capa
  IA explicativa) lo redacta el arquitecto tras auditar el cierre de PROMPT-006/ADR-002.

### Bandeja del OPERADOR

- **Avisar al arquitecto** de que PROMPT-006 (ADR-002) está cerrado para auditoría.
  Tras su visto bueno: PROMPT-007 = F3 (matching determinista + capa IA
  explicativa), lo redacta el arquitecto.
- **Lista de portales/fuentes de subvenciones** que usabas (nacional, regional,
  local + privadas) — bloquea el prompt de F2.
- **Captar entidad piloto** (acceso + ingresos/gastos del ejercicio anterior +
  lista de actividades).

### Backlog

- F2 ingesta (bloqueada por lista de portales) · F3 matching+IA explicativa ·
  F4 propuesta/aviso · F5 preparación asistida — el arquitecto redacta cada prompt
  al quedar AUDITADA la fase anterior (pactado en ADR-001 §5).
- Endurecer el test anti-hardcoding (el canario del ADR pasa por construcción) — F3+.
- Esqueleto de la app (fija el comando de servidor local en CLAUDE.md) — tras F1.
- Modelo de negocio (las entidades objetivo tienen pocos recursos) — conversación
  de producto, sin prisa técnica.
- Ajustar la "vara de medir" de ux-reviewer.md cuando exista sistema visual propio.

### Recordatorios operativos

- Máquina Windows: comandos como `python -m pytest -q` (no rutas unix); rutas con `C:\dev\ongs-ai`.
- Mount sandbox↔host miente con ficheros recién editados — el HOST es la verdad.
- Git desde sandbox: SOLO `git log`/`git show`; jamás status/diff (index.lock huérfanos).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
