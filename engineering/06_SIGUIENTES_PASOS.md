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

- **2026-07-18 — Repo bootstrapeado y AUDITADO: PROMPT-001 APROBADO, HECHO 2101890**
  (detalle en histórico). Repo git en `main`, esqueleto Python, 1 test VERDE, nada
  sensible commiteado. Tres notas menores de la auditoría van absorbidas en PROMPT-002
  (higiene): pytest sin declarar como dependencia dev, line endings sin fijar en el repo
  (aviso LF→CRLF de la config global de Windows), versión duplicada en pyproject +
  `__init__.py`. La excepción `!.claude/agents/` del .gitignore es hoy inerte (nada
  ignora `.claude/`) — se deja por si un ignore futuro la necesita.
- Decisiones fundacionales del 2026-07-18: producto = **SaaS multi-tenant para ONGs**
  (alcance en descubrimiento); stack = **Python heredado** (SQLite, pytest hermético).
  CLAUDE.md v1 con regla de oro nueva: aislamiento por tenant con test anti-fuga.
- **Duele:** definición de producto vacía. ADR-001 (contrato de datos tenant/ONG)
  bloqueado hasta que el operador responda las preguntas de producto (bandeja).
- Sin remoto git → el `git push` del ritual queda en "anótalo" hasta que exista.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-002 — Higiene post-bootstrap · MODELO: Sonnet · ORDEN: 1º (puede lanzarse YA; nada en paralelo)

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda
de implementación, elige la opción más conservadora/reversible y DOCUMENTA
la decisión en el resumen final; ante ambigüedad de alcance, implementa lo
literal del prompt y anota lo que dejaste fuera; jamás inventes datos ni
mediciones (si necesitas un dato que no tienes, esa sí es pregunta
legítima); las preguntas no bloqueantes van AGRUPADAS al final del
trabajo, no en medio. Reglas de oro de CLAUDE.md por encima de todo — si
el prompt y CLAUDE.md chocan, gana CLAUDE.md y me lo señalas. Antes de
tocar un fichero grande, Grep al símbolo y lee el rango — nunca el
fichero entero.

TAREA: higiene post-bootstrap del repo ONGs-AI (C:\dev\ongs-ai), tres
correcciones menores de la auditoría de PROMPT-001:

1. Crea `.gitattributes` en raíz fijando line endings en el repo (independiente
   de la config global de Windows del usuario):
     * text=auto
     *.py text eol=lf
     *.md text eol=lf
     *.toml text eol=lf
   Tras crearlo, renormaliza (`git add --renormalize .`) y revisa qué cambia.
2. Declara pytest como dependencia de desarrollo en pyproject.toml:
   `[project.optional-dependencies]` con `dev = ["pytest>=8"]`.
3. Única fuente de versión: en `[project]` pon `dynamic = ["version"]` y añade
   `[tool.setuptools.dynamic]` con `version = {attr = "ongs_ai.__version__"}`,
   eliminando la clave `version` estática. `__init__.py` queda como única verdad.
4. Comprueba `python -m pytest -q` VERDE.
5. El working tree contiene cambios del arquitecto en `engineering/06_*`
   (cierre de PROMPT-001 en la pizarra): inclúyelos en el MISMO commit.
6. Ritual de cierre completo de CLAUDE.md; UN commit con el nº REAL de tests;
   sin remoto aún → anótalo en vez de push.
```

### Bandeja del OPERADOR

- Pegar PROMPT-002 en una sesión de Claude Code (terminal) y avisar al arquitecto
  al terminar para auditoría del código real.
- **Preguntas de producto** (desbloquean ADR-001; responder al arquitecto en chat):
  1. ¿Qué hace ONGs-AI por una ONG en su primer mes de uso? ¿Cuál es el primer
     módulo de valor: socios/cuotas, donaciones, subvenciones/memorias, otro?
  2. ¿Quién es el primer usuario real (una ONG concreta con nombre, o hipotética)?
  3. ¿Dónde entra la IA en ese primer módulo (redacción, clasificación, extracción…)?
- Decidir si se crea remoto git (GitHub/otro) para poder cumplir el `git push` del ritual.

### Backlog

- ADR-001 (Opus): contrato de datos central tenant/ONG — bloqueado por preguntas de producto.
- Esqueleto de la app (fija el comando de servidor local en CLAUDE.md) — tras ADR-001.
- PROJECT_CONTEXT.md: visión y dominio, tras las respuestas de producto.
- Ajustar la "vara de medir" de ux-reviewer.md cuando exista sistema visual propio.

### Recordatorios operativos

- Máquina Windows: comandos como `python -m pytest -q` (no rutas unix); rutas con `C:\dev\ongs-ai`.
- Mount sandbox↔host miente con ficheros recién editados — el HOST es la verdad.
- Git desde sandbox: SOLO `git log`/`git show`; jamás status/diff (index.lock huérfanos).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
