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
- **2026-07-18 (tarde) — PRODUCTO DEFINIDO** (notas de voz del operador, transcritas):
  técnico de subvenciones para entidades de enfermedades raras sin personal — cartera
  de entidades + vigilante de convocatorias (público/privado, nacional→local) +
  matching con aviso/propuesta + preparación asistida de solicitudes. Visión completa
  en `PROJECT_CONTEXT.md` (raíz). ADR-001 desbloqueado → PROMPT-003 (Opus) en cola.
  Supuestos por defecto del arquitecto (corregibles): ámbito España/castellano; v1 SIN
  datos de pacientes (solo datos de entidad); "desarrollar la solicitud" = borradores
  de documentos, presenta la entidad.
- **Duele:** sin lista concreta de portales/fuentes y sin entidad piloto — no bloquean
  el ADR (el contrato se diseña igual), pero sí bloquearán la ingesta real.
- Sin remoto git → el `git push` del ritual queda en "anótalo" hasta que exista.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-003 — ADR-001: contrato de datos central · MODELO: Opus · ORDEN: 1º (nada en paralelo) · SIN CÓDIGO

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

TAREA: escribir el ADR-001 del proyecto ONGs-AI. SOLO documentación — ni
una línea de código de producción. Lee primero PROJECT_CONTEXT.md (raíz;
puede estar sin commitear: el working tree es la verdad e inclúyelo en tu
commit) y CLAUDE.md.

Producto en una frase: SaaS multi-tenant que vigila convocatorias de
subvenciones (públicas y privadas, nacional→local, España) y las casa con
asociaciones de enfermedades raras sin personal, avisa, propone y ayuda a
preparar la solicitud.

Escribe `engineering/ADR-001-contrato-de-datos.md` con:

1. DECISIÓN: el contrato de datos central congelable. Como mínimo las
   entidades: Entidad (el tenant: perfil, ámbito territorial, actividades,
   datos económicos del ejercicio anterior — dinero en CÉNTIMOS enteros),
   Convocatoria (fuente, objeto, beneficiarios, ámbito, plazos, cuantías,
   requisitos duros de elegibilidad como datos estructurados), Actividad
   (tipología cerrada: voluntariado, encuentro de pacientes, charlas… —
   enum cerrado y extensible SOLO por ADR), Match/Propuesta (estados:
   detectada → propuesta → aceptada/descartada → en preparación →
   presentada; asientos inmutables para todo cambio de estado).
2. Para cada campo: ¿lo llena la IA (extracción) o el dominio (dato
   verificado)? Los requisitos de elegibilidad DUROS se evalúan
   deterministas sobre datos estructurados — la IA jamás decide
   elegibilidad, solo extrae y explica (regla de oro).
3. ALTERNATIVAS consideradas y por qué no (mínimo: schema libre por JSON
   vs contrato tipado; matching todo-IA vs híbrido).
4. CONSECUENCIAS: qué se congela en CLAUDE.md (nombre y ruta del
   contrato), implicaciones de aislamiento por tenant y anti-hardcoding
   (nada de una enfermedad o entidad concreta en el schema — todo llega
   como datos), PII (v1 SIN datos de pacientes; datos económicos de
   entidad = sensibles, fuera de git).
5. FASES de implementación (sin código): fase → objetivo → ficheros
   previstos → 1 prompt completo por fase con este mismo preámbulo.
   Orientación: F1 contrato+persistencia+tests anti-fuga/anti-hardcoding;
   F2 ingesta de convocatorias (adapters por portal, red inyectable,
   apagada en tests); F3 matching determinista + capa IA explicativa;
   F4 propuesta/aviso; F5 preparación asistida.
6. PREGUNTAS AL OPERADOR con default cada una (agrupadas al final).

Ritual de cierre: commit ÚNICO (ADR + PROJECT_CONTEXT.md + cambios de
engineering/06_* presentes en el working tree), pytest VERDE con el nº
REAL de tests en el mensaje, git status antes del add, sin push (sin
remoto — anótalo).
```

### Bandeja del OPERADOR

- Pegar PROMPT-003 en una sesión de Claude Code con **Opus** y avisar al arquitecto
  al terminar para auditoría.
- **Lista de portales/fuentes de subvenciones** que usabas (nacional, regional,
  local + privadas) — bloquea la fase de ingesta, no el ADR.
- **Captar entidad piloto** (acceso + ingresos/gastos del ejercicio anterior +
  lista de actividades).
- Validar (o corregir) los 3 supuestos por defecto del arquitecto: España/castellano;
  v1 sin datos de pacientes; "desarrollar" = borradores, presenta la entidad.
- Decidir si se crea remoto git (GitHub/otro) para poder cumplir el `git push` del ritual.

### Backlog

- Fases F1–F5 del ADR-001 (los prompts los trae el propio ADR; el arquitecto los
  audita y los sube a esta cola por orden).
- Esqueleto de la app (fija el comando de servidor local en CLAUDE.md) — tras F1.
- Modelo de negocio (las entidades objetivo tienen pocos recursos) — conversación
  de producto, sin prisa técnica.
- Ajustar la "vara de medir" de ux-reviewer.md cuando exista sistema visual propio.

### Recordatorios operativos

- Máquina Windows: comandos como `python -m pytest -q` (no rutas unix); rutas con `C:\dev\ongs-ai`.
- Mount sandbox↔host miente con ficheros recién editados — el HOST es la verdad.
- Git desde sandbox: SOLO `git log`/`git show`; jamás status/diff (index.lock huérfanos).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
