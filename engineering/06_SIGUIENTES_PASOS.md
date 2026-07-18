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

- **2026-07-18 (noche) — F1 ejecutada (7db6c5d, 31 tests VERDES) y AUDITADA:
  CORRECCIONES, no cerrada.** Lo bueno: contrato calcado del ADR, máquina de estados
  exacta (terminales incluidos, `transicionar` inmutable), dinero/pb rechazando floats
  y bool, anti-fuga sobre matches+asientos+datos económicos, SQLite anclado a `var/`
  (gitignorado). La grieta: **AlmacenSQLite viola su puerto** — `puertos.py` promete
  objetos de dominio y SQLite devuelve dicts; el adapter real y el de tests tienen
  contratos DISTINTOS y el anti-fuga solo corre contra memoria (tests verdes ≠
  producción funciona). Corrección → PROMPT-005. El blob `datos_json` como formato
  interno del adapter se ACEPTA v1 (no viola ADR §3.1 mientras la evaluación use
  objetos tipados). PROMPT-004 viaja al histórico cuando 005 quede auditado.
- **Lección para el ritual** (sigue vigente, 2 casos ya): los resúmenes de sesión
  afirman cosas que el código desmiente — mensaje de commit en PROMPT-002, "decisión
  conservadora" que rompía el puerto en PROMPT-004. Auditar SIEMPRE el artefacto real.
- Fundación cerrada al histórico: PROMPT-001 (2101890), PROMPT-002 (1f50ed8),
  PROMPT-003/ADR-001 (6423f46). Stack Python/SQLite/pytest hermético.
- **2026-07-18 (noche) — ADR-001 ACEPTADO y AUDITADO (HECHO 6423f46)**: contrato
  Entidad/Convocatoria/Actividad/Match congelado en el ADR; CLAUDE.md se actualizará
  con nombre+ruta en F1 (paso 7 del prompt). Producto definido en `PROJECT_CONTEXT.md`.
  Fases F1–F5 pactadas; prompts F2–F5 los redacta el arquitecto tras auditar la fase
  anterior. F1 encolado como PROMPT-004 con dos refinamientos del arquitecto:
  `descartada`/`presentada` terminales (a `en_preparacion` solo desde `aceptada`;
  reintento = Match nuevo, ADR §6.4) y `porcentaje_max_financiable` en puntos básicos
  enteros (8000 = 80%), jamás float.
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
- Sin remoto git → el `git push` del ritual queda en "anótalo" hasta que exista.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-005 — Corrección F1: el puerto se cumple en TODOS los adapters · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: corrección de la auditoría de F1 (commit 7db6c5d) en ONGs-AI.
Contexto: `src/ongs_ai/dominio/puertos.py` promete objetos de dominio
(`Entidad | None`, `Convocatoria | None`, `list[Match]`) pero
`AlmacenSQLite` devuelve dicts decodificados del JSON. El adapter real y
el de tests tienen contratos distintos, y los tests de aislamiento solo
corren contra memoria. El formato interno `datos_json` NO se cambia — es
detalle aceptado del adapter; lo que se corrige es la frontera del puerto.

1. En `AlmacenSQLite`, reconstruye objetos de dominio TIPADOS en las
   lecturas: `obtener_entidad -> Entidad | None`,
   `obtener_convocatoria -> Convocatoria | None`,
   `listar_matches_por_entidad -> list[Match]`. Deserializa enums, fechas
   (date/datetime ISO), tuplas y objetos anidados exactamente a los
   dataclasses de `entidades.py`/`matching_estado.py`. Si el JSON
   almacenado no mapea al contrato (dato feo), NO lances al dominio:
   devuelve None / omite el registro marcándolo — degrada limpio (regla
   de oro; para F1 basta omitir con log/contador interno, documenta lo
   elegido).
2. Tests de CONTRATO parametrizados sobre AMBOS adapters
   (`AlmacenMemoria` y `AlmacenSQLite(':memory:')` — jamás fichero real
   en tests): round-trip de igualdad guardar→obtener para Entidad,
   Convocatoria y Match (incluidos asientos con sus enums y timestamps),
   y los DOS tests de `test_anti_fuga_tenant.py` corriendo sobre ambos
   (parametriza o factoriza la fixture; no dupliques el cuerpo).
3. Un test que verifique explícitamente que ambos adapters satisfacen los
   Protocol de `puertos.py` para los tres repositorios (p. ej.
   `isinstance(almacen, RepositorioEntidades)` con Protocol
   runtime_checkable, o llamada tipada equivalente).
4. Refresca el párrafo de cabecera de CLAUDE.md (líneas 1–6): el producto
   ya NO está "en descubrimiento" — una frase alineada con
   PROJECT_CONTEXT.md (técnico de subvenciones para entidades de
   enfermedades raras; multi-tenant). No toques las reglas de oro.
5. `python -m pytest -q` VERDE, herméticos.
6. Incluye en tu commit los cambios de `engineering/06_*` presentes en el
   working tree (auditoría de F1 por el arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (ni .env, ni var/, ni datos reales de entidad),
sin push si aún no hay remoto (anótalo).
```

### Bandeja del OPERADOR

- Pegar PROMPT-005 (corrección F1) en una sesión de Claude Code (Sonnet) y avisar al
  arquitecto al terminar para auditoría.
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
