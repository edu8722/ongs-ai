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

- **2026-07-18 — Fundación completa y AUDITADA**: PROMPT-001 (bootstrap, HECHO 2101890)
  y PROMPT-002 (higiene, HECHO 1f50ed8 tras amend) cerrados al histórico. Repo en
  `main`, 2 commits, 1 test VERDE, EOL fijados, versión única, nada sensible.
  Nota: la excepción `!.claude/agents/` del .gitignore es hoy inerte — se deja.
- **Lección para el ritual:** las sesiones empleadas pueden afirmar en el resumen pasos
  del ritual que no hicieron (pasó con el mensaje de commit de PROMPT-002). La
  auditoría SIEMPRE verifica el mensaje de commit real (`git log -1 --format=%s`),
  no el resumen.
- Decisiones fundacionales del 2026-07-18: producto = **SaaS multi-tenant para ONGs**
  (alcance en descubrimiento); stack = **Python heredado** (SQLite, pytest hermético).
  CLAUDE.md v1 con regla de oro nueva: aislamiento por tenant con test anti-fuga.
- **2026-07-18 (noche) — ADR-001 ACEPTADO y AUDITADO (HECHO 6423f46)**: contrato
  Entidad/Convocatoria/Actividad/Match congelado en el ADR; CLAUDE.md se actualizará
  con nombre+ruta en F1 (paso 7 del prompt). Producto definido en `PROJECT_CONTEXT.md`.
  Fases F1–F5 pactadas; prompts F2–F5 los redacta el arquitecto tras auditar la fase
  anterior. F1 encolado como PROMPT-004 con dos refinamientos del arquitecto:
  `descartada`/`presentada` terminales (a `en_preparacion` solo desde `aceptada`;
  reintento = Match nuevo, ADR §6.4) y `porcentaje_max_financiable` en puntos básicos
  enteros (8000 = 80%), jamás float.
- Supuestos vigentes del ADR §6 (defaults, corregibles por el operador): módulo en
  `src/ongs_ai/dominio/`; F5 = borrador de memoria narrativa; aviso F4 = email;
  Match nuevo tras descartada; dedupe ingesta por `portal`+`url_origen`.
- **Duele:** sin lista concreta de portales/fuentes (bloquea el prompt de F2) y sin
  entidad piloto. Test anti-hardcoding v1 es canario débil — endurecer en F3+.
- Sin remoto git → el `git push` del ritual queda en "anótalo" hasta que exista.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-004 — F1: contrato + persistencia + tests fundacionales · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: implementar el contrato de datos de ADR-001
(engineering/ADR-001-contrato-de-datos.md) — léelo completo primero, es la
fuente congelada — para el proyecto ONGs-AI.

1. Modela `Entidad`, `Convocatoria`, `Actividad` (enum cerrado v1 tal cual
   §1.3 del ADR) y `Match` (con sus asientos inmutables) exactamente con
   los campos de las tablas del ADR, en dominio puro (sin dependencias de
   framework web ni de IA).
2. Dinero SIEMPRE en céntimos enteros (int), nunca float — valida esto con
   un test explícito que rechace floats en esos campos.
   `porcentaje_max_financiable` se almacena como ENTERO en puntos básicos
   (8000 = 80%), jamás float — mismo test.
3. Persistencia con factory por entorno: adapter real (SQLite, ALTER TABLE
   idempotente si hace falta versionar el esquema, ruta SIEMPRE anclada al
   repo o absoluta — jamás relativa al CWD) por defecto, adapter en
   memoria (`:memory:` o estructura Python pura) para tests. Los tests
   jamás tocan red ni fichero real de SQLite en disco compartido.
4. Test anti-fuga cross-tenant: crea dos Entidades, un Match de cada una,
   y comprueba que una consulta con `entidad_id` de la primera nunca
   devuelve datos (Match, asientos, datos económicos) de la segunda.
5. Test anti-hardcoding: crea una Entidad con una enfermedad rara
   inventada por el test (no una real) y comprueba que ningún fichero de
   `src/ongs_ai/` la menciona ni depende de su valor literal.
6. Máquina de estados de Match — PRECISIÓN sobre el ADR (§1.4 + §6.4):
   transiciones legales EXACTAS: `detectada → propuesta`,
   `propuesta → aceptada`, `propuesta → descartada`,
   `aceptada → en_preparacion`, `en_preparacion → presentada`.
   `descartada` y `presentada` son estados TERMINALES: ninguna transición
   sale de ellos. El reintento tras `descartada` es un Match NUEVO para la
   misma Entidad+Convocatoria (el histórico del anterior no se toca).
   Cada transición crea un asiento nuevo, nunca reescribe uno existente
   (comprueba inmutabilidad con test: estructura solo-añadir o excepción
   al intentar mutar un asiento pasado). Testea también que las
   transiciones ilegales (p. ej. `descartada → en_preparacion`,
   `detectada → aceptada`) lanzan error de dominio.
7. Actualiza CLAUDE.md, sección CONTRATO CONGELADO: fija el nombre
   ("Entidad/Convocatoria/Actividad/Match, ADR-001") y la ruta real de los
   ficheros de dominio que hayas creado en el paso 1.
8. `python -m pytest -q` VERDE (herméticos: sin red, sin depender de
   .env de la máquina).
9. Incluye en tu commit los cambios de `engineering/06_*` presentes en el
   working tree (cierre de PROMPT-003 por el arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (ni .env, ni var/, ni datos reales de entidad),
sin push si aún no hay remoto (anótalo).
```

### Bandeja del OPERADOR

- Pegar PROMPT-004 (F1) en una sesión de Claude Code (Sonnet) y avisar al arquitecto
  al terminar para auditoría.
- Validar (o corregir) los 5 defaults del ADR §6 — en especial la 2 (alcance F5:
  borrador de memoria narrativa) y la 3 (aviso F4: email), que condicionan los
  prompts de F4/F5.
- **Lista de portales/fuentes de subvenciones** que usabas (nacional, regional,
  local + privadas) — bloquea el prompt de F2.
- **Captar entidad piloto** (acceso + ingresos/gastos del ejercicio anterior +
  lista de actividades).
- Decidir si se crea remoto git (GitHub/otro) para poder cumplir el `git push` del ritual.

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
