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
- **UN SOLO ARQUITECTO ACTIVO a la vez.** El traspaso entre sesiones de arquitecto se
  hace por el 06 COMMITEADO (git), nunca por el working tree. El arquitecto que retoma
  relee el 06 COMPLETO desde `git show HEAD:` ANTES de mirar el log de commits — el
  orden inverso hace alucinar violaciones (pasó el 2026-07-21).
- **Fricciones del entorno Cowork** (misma máquina): el mount sandbox↔host MIENTE con
  ficheros recién editados EN AMBOS SENTIDOS — puede servir lecturas viejas y llegar a
  PISAR la pizarra en disco con una copia obsoleta (pasó el 2026-07-21: se recuperó
  desde git). El HOST es la verdad para código; GIT es la verdad para la pizarra.
  Desde sandbox solo `git log`/`git show` (jamás status/diff: dejan index.lock
  huérfanos); JSONs/salidas grandes SIEMPRE como archivo; Lighthouse lo mide el
  operador. Tras cada cambio de pizarra del arquitecto: commit de docs cuanto antes
  (lo arrastra el siguiente prompt o lo commitea el operador suelto).

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
> fichero entero. La pizarra (engineering/06_*) la mantiene SOLO el
> arquitecto: no cierres items, no te declares APROBADO, no muevas nada al
> histórico — limítate a incluir en tu commit los cambios de
> engineering/06_* que ya estén en el working tree, tal cual estén.

---

## ESTADO VIVO

- **2026-07-21 — PROMPT-016 CERRADO (HECHO 8ebfb1d, APROBADO, 220 tests):** proyecto
  instalable (`pip install -e .`, ya sin PYTHONPATH), comando canónico en CLAUDE.md
  (`python -m uvicorn ... --port 8001`), demo y egg-info gitignorados. PERO (2ª vez)
  la sesión ejecutó el prompt SIN el último remate → **el bug SQLite multihilo sigue
  VIVO** (sqlite.py sin tocar, verificado) → **PROMPT-017 en cola (solo el fix)**.
  La demo del operador seguirá dando 500 hasta cerrarlo.
- F-web.2 CERRADA (455de38, 220 t): aceptar/descartar con CSRF, propiedad de match
  a prueba de ajenos. LA APP ESTÁ COMPLETA PARA DEMO (pendiente solo PROMPT-017).
  **Fases: F1 ✔ · ADR-002 ✔ · F3 ✔ · F2+fix ✔ · F4 ✔ · ADR-005 ✔ · F-web.1 ✔ ·
  F-web.2 ✔ · empaquetado ✔ · SIGUIENTE: PROMPT-017 (fix SQLite) · Después: F5.**
- F-web.1 (06418f3, 214 t) cerrada — detalle en histórico. Variables producción:
  ONGS_AI_SECRET_KEY, ONGS_AI_APP_BASE_URL, ONGS_AI_SMTP_*.
- ADR-005 (a4c80ab) aceptado con decisiones del operador: sesión 30 días · enlace
  1 h · hosting/TLS al captar piloto. PROMPT-012 (6457682): scraper FEDER, techo
  ~272/476; **maestro de prospección v3 = 511 entidades** (fuera de git). Histórico.
- **2026-07-21 — INCIDENTE DE PIZARRA, resuelto:** el mount pisó el 06 del disco con
  una copia del día 18 (commiteada sin querer en 61d76a4). Recuperado desde
  `9f8c732` + cierre de F4.1. Consecuencia: regla nueva de gobernanza en el
  traspaso (un solo arquitecto activo; git = verdad de la pizarra). Los cierres de
  F2 (5a52d27), F2-fix/PROMPT-009 (6a50af2) y sus auditorías del arquitecto del
  día 19 están íntegros en el histórico.
- **Smoke test F2 (operador, 2026-07-19): API BDNS viva OK** — 5 convocatorias
  reales mapeadas de punta a punta; campos confirmados; dinero en céntimos int;
  nominativas sin plazo quedan `extraida` (guardarraíl OK). Pendiente menor: el
  parámetro `tipoBeneficiario` aún sin ejercer con filtro real.
- **Investigaciones:** R1 commiteada (BDNS = fuente única del sector público,
  verificado 3-0). R2: **maestro de prospección v3 = 511 entidades** (fuera de git;
  candidatas a piloto: GERNA, PERA, ARER, ASERCA, ABAIMAR, red ASEM). Enriquecer
  personas visibles SOLO de las que se vayan a contactar. Censo FEDER completo:
  pedirlo a FEDER cuando haya relación (~204 entidades no salen por web).
- **Lección del ritual** (4 casos): resúmenes/acciones de sesiones exceden lo real —
  mensaje de commit (P-002), "decisión conservadora" que rompía el puerto (P-004),
  auto-cierre "APROBADO" (P-006), y pizarra pisada por el mount (2026-07-21).
  Auditar SIEMPRE el artefacto real; veredicto solo del arquitecto; pizarra desde git.
- **Lección de verificación humana (2026-07-21):** la demo del operador en navegador
  real cazó un bug de producción invisible para 220 tests herméticos (SQLite
  monohilo vs threadpool de FastAPI — la web solo se testeaba con AlmacenMemoria).
  Confirma la regla del kit: el operador verifica en navegador/dispositivo real lo
  que las sesiones no pueden. Fix + test de integración SQLite-por-HTTP en PROMPT-016.
- **Duele:** sigue SIN ENTIDAD PILOTO (hay candidatas con contacto en R2 — falta
  decidir y contactar; el arquitecto ofrece redactar el mensaje). Anti-hardcoding
  sigue siendo canario débil. Sin `municipio` → ámbito LOCAL no evaluable (ADR si
  hace falta). Redundancia de ámbito en contrato → candidato ADR-003.
- **Remoto git ACTIVO**: origin = github.com/edu8722/ongs-ai (privado). Tras cada
  cambio de pizarra: commit de docs (ver traspaso).

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-017 — Fix: SQLite multihilo bajo FastAPI · MODELO: Sonnet · ORDEN: 1º (corto)

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
fichero entero. La pizarra (engineering/06_*) la mantiene SOLO el
arquitecto: no cierres items, no te declares APROBADO, no muevas nada al
histórico — limítate a incluir en tu commit los cambios de
engineering/06_* que ya estén en el working tree, tal cual estén.

TAREA (corta y única): arreglar el bug de producción cazado por el
operador en navegador real (traza del 2026-07-21):
`sqlite3.ProgrammingError: SQLite objects created in a thread can only be
used in that same thread` — la conexión de `AlmacenSQLite` se crea en el
hilo de arranque y FastAPI ejecuta las rutas sync en un threadpool.

1. Arreglo conservador en `adapters/persistencia/sqlite.py`:
   `sqlite3.connect(..., check_same_thread=False)` + un `threading.Lock`
   propio del almacén que serializa TODA operación (execute/commit).
   Documenta: SQLite ya serializa escrituras y el volumen v1 es mínimo;
   nada de pooling ni conexiones por hilo.
2. Tests de regresión: (a) hermético — `AlmacenSQLite(':memory:')` usado
   desde un `threading.Thread` distinto al creador (reproduce el bug tal
   cual); (b) integración HTTP — UN test con TestClient cuyo almacén
   inyectado sea `AlmacenSQLite(':memory:')` en vez de AlmacenMemoria
   (login+panel felices) — cubre el hueco que dejó pasar esto.
3. `python -m pytest -q` VERDE con el nº REAL de tests. Incluye
   engineering/06_* del working tree tal cual (cierre de PROMPT-016 por
   el arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add, `git push` al terminar.
```

### Bandeja del OPERADOR

- **VER LA APP (5 min):** `cd C:\dev\ongs-ai` → `set ONGS_AI_ENV=test` →
  `set ONGS_AI_SECRET_KEY=prueba-local` → `set PYTHONPATH=src` →
  `python -m uvicorn ongs_ai.web.app:app --reload --port 8001` → abrir
  http://localhost:8001/login. (Modo test: memoria + SMTP stub, el enlace sale en la
  consola. PYTHONPATH temporal hasta que PROMPT-015 arregle el empaquetado.)
- Pegar PROMPT-017 (fix SQLite, Sonnet) — COPIA LA VERSION ACTUAL de este 06.
  Al cerrarse: repetir la demo (semilla + servidor 8001 + enlace nuevo) — deberia
  abrir el panel. Antes: cierra el uvicorn viejo que dejaste corriendo (el «8001 ocupado»
  era tu propio servidor de la prueba anterior — Ctrl+C en su ventana).
- `python scripts/smoke_email.py` cuando tengas buzón/credenciales SMTP (variables
  ONGS_AI_SMTP_*) — verifica el aviso por email real. Puede esperar.
- Cuando haya relación con FEDER (p. ej. vía piloto): pedirles el censo completo de
  entidades asociadas — el listado web solo expone ~272 de 476 (hallazgo PROMPT-012).
- **Entidad piloto:** elegir 2-3 candidatas del informe R2 (GERNA, PERA, ARER,
  ASERCA, ABAIMAR, red ASEM…) y pedir al arquitecto el mensaje de propuesta.
- Decidir si continúa como arquitecto esta sesión o la del día 19 — UNA sola activa
  (regla del traspaso). Esta sesión está al día a fecha 2026-07-21.

### Backlog

- Esqueleto de la app (servidor local en CLAUDE.md; UI del panel sobre el read model
  de F4.2) — tras F4.2.
- F5 preparación asistida (alcance AMPLIADO por el operador: checklist documental con
  gap + borradores de todos los entregables; probable ADR DocumentoRequerido).
- ADR-003: redundancia de ámbito en el contrato (`ambito_geografico`+region/provincia
  vs `ambito_territorial_requerido` sin consumir) — limpiar.
- Enriquecimiento de personas visibles: solo de las asociaciones a contactar (tras
  elegir candidatas; la extracción FEDER completa ya está en cola como PROMPT-012).
- Adapters privados de ingesta (FEDER, la Caixa, ONCE) + agregador SolucionesONG.
- Proveedor LLM real para la capa IA (hoy ExplicadorStub) — decisión del arquitecto.
- Endurecer test anti-hardcoding. · Filtro `tipoBeneficiario` de BDNS sin ejercer.
- Verificación adversarial pendiente de R1 (22 claims, 0 refutadas) — opcional.
- Modelo de negocio (entidades con pocos recursos) — conversación de producto.

### Recordatorios operativos

- ANTES de pegar un prompt: copialo del 06 ACTUAL, tras el ultimo aviso del
  arquitecto — dos prompts ya se ejecutaron en version vieja (015 y 016).

- Máquina Windows: SIEMPRE `python -m ...` (pytest, uvicorn — los .exe de Scripts no
  están en PATH); rutas `C:\dev\ongs-ai`. **Puerto 8000 OCUPADO por otro proyecto →
  ONGs-AI usa el 8001.** Hasta que PROMPT-015 arregle el empaquetado: `set
  PYTHONPATH=src` antes de arrancar uvicorn (pytest no lo necesita).
- Mount sandbox↔host: ver regla del traspaso (git = verdad de la pizarra).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
- `investigacion/asociaciones*` JAMÁS a git (datos personales; gitignorado).
