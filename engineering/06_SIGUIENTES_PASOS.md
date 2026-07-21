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

- **2026-07-21 — F4.2 CERRADA Y AUDITADA: APROBADO, HECHO fb95b4a, 176 tests,
  pushed.** Email SMTP real (cliente inyectado, plantilla pura sin datos internos,
  config solo en factory) + read model del panel por tenant + smoke manual. Detalle
  → histórico. Dos remates van en PROMPT-012: cubo ACEPTADA del panel (omisión del
  prompt del arquitecto) y patrón gitignore que no cubría `R2_asociaciones_*`.
  **Estado de fases: F1 ✔ · ADR-002 ✔ · F3 ✔ · F2 ✔ · F2-fix ✔ · F4.1 ✔ · F4.2 ✔ ·
  SIGUIENTE: PROMPT-012 (scraper FEDER + remates) · Después: esqueleto app / F5.**
- F4.1 cerrada y auditada (HECHO 9f8c732, 155 tests) — detalle en histórico.
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
- **ADR-004 (2026-07-19) rige F4** — decisiones del operador: persistir todo match
  dentro de un catálogo relevante (pre-puerta), elegibilidad sobrevenida = avisar
  como nueva propuesta. Email solo elegibles; panel muestra todo. Email real y read
  model → F4.2 (en cola). UI del panel → esqueleto app (backlog).
- **Investigaciones:** R1 entregada y commiteada (`investigacion/R1_*` — BDNS como
  fuente única del sector público, verificado 3-0). **R2 consolidada en
  `asociaciones_EERR_directorio_v2.xlsx` (2026-07-21): 364 entidades** (maestro
  anterior + 96 del listado web de FEDER, 29 nuevas tras dedupe por nombre y email;
  candidatas a piloto señaladas en el informe: GERNA, PERA, ARER, ASERCA, ABAIMAR,
  red ASEM). Techo de la vía web: el conversor corta el HTML largo de FEDER
  (~96/476) → la extracción COMPLETA va por script con red real en la máquina del
  operador = **PROMPT-012 en cola**. Enriquecimiento con personas visibles: SOLO
  sobre las asociaciones que se vayan a contactar (decisión del operador vigente).
  ⚠ Dato personal: fuera de git, responsable = operador, no difundir.
- **Lección del ritual** (4 casos): resúmenes/acciones de sesiones exceden lo real —
  mensaje de commit (P-002), "decisión conservadora" que rompía el puerto (P-004),
  auto-cierre "APROBADO" (P-006), y pizarra pisada por el mount (2026-07-21).
  Auditar SIEMPRE el artefacto real; veredicto solo del arquitecto; pizarra desde git.
- **Duele:** sigue SIN ENTIDAD PILOTO (hay candidatas con contacto en R2 — falta
  decidir y contactar; el arquitecto ofrece redactar el mensaje). Anti-hardcoding
  sigue siendo canario débil. Sin `municipio` → ámbito LOCAL no evaluable (ADR si
  hace falta). Redundancia de ámbito en contrato → candidato ADR-003.
- **Remoto git ACTIVO**: origin = github.com/edu8722/ongs-ai (privado). Tras cada
  cambio de pizarra: commit de docs (ver traspaso).

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-011 — F4.2: adapter de email real + read model del panel · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: F4.2 del ADR-004 (léelo: engineering/ADR-004-persistencia-matches-
y-aviso-proactivo.md, §6) — el aviso por email real y el modelo de lectura
que alimentará el panel. NO toques el contrato ni la máquina de estados.

1. Adapter de email — `src/ongs_ai/adapters/avisos/email_smtp.py`
   (+ `__init__.py`): implementación del Protocol `Notificador`
   (servicios/notificacion.py) sobre SMTP estándar (smtplib de stdlib,
   STARTTLS). TODA la configuración llega por parámetros/objeto de config
   (host, puerto, credenciales, remitente) leída de variables de entorno
   SOLO en la factory de composición — jamás en el adapter, jamás
   hardcodeada, jamás en git (.env ya está gitignorado). Destinatario:
   `entidad.contacto.email`; si la entidad no tiene email, degrada limpio
   (log + contador, sin excepción). Contenido del aviso: asunto y cuerpo
   de TEXTO PLANO con objeto de la convocatoria, portal, fecha_cierre,
   cuantías si existen y la explicacion_ia si el match la lleva — sin
   datos internos (ids de sistema, costes) — plantilla como función pura
   testeable aparte del envío.
2. En tests NUNCA se abre un socket: el cliente SMTP se INYECTA (factory
   por entorno como en persistencia); stub que registra los envíos.
   Testea: plantilla (contenido correcto, sin campos internos), envío
   feliz, entidad sin email → degrada limpio, SMTP que lanza → degrada
   limpio sin romper la pasada (mismo patrón try/except de F4.1).
3. Read model del panel — `src/ongs_ai/servicios/panel.py`: consultas de
   SOLO LECTURA sobre el puerto de matches, POR ENTIDAD (aislamiento por
   tenant, jamás cross-tenant): `resumen_panel(entidad_id, almacen)` →
   listas de matches agrupadas por estado (propuestas pendientes,
   en_preparacion, presentadas, descartadas, detectadas no elegibles con
   su motivo) ordenadas por fecha del último asiento. Pura composición de
   lo existente; si necesitas una consulta nueva en el puerto, añade lo
   MÍNIMO y cúmplelo en ambos adapters con test de contrato parametrizado.
   El test anti-fuga cross-tenant DEBE cubrir el read model (entidad A no
   ve nada de B).
4. `scripts/smoke_email.py`: script MANUAL fuera de CI (documenta que hace
   red) que envía UN email de prueba leyendo config del entorno — lo
   ejecutará el operador cuando tenga credenciales SMTP; el prompt NO
   necesita credenciales para cerrarse (los tests van con stub).
5. `python -m pytest -q` VERDE, herméticos. Incluye los cambios de
   `engineering/06_*` del working tree tal cual (cierre de F4.1 por el
   arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add, `git push` al terminar.
```

#### PROMPT-012 — Utilidad: extracción completa FEDER + remates de auditoría F4.2 · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: dos remates de la auditoría de F4.2 + utilidad de captación (script
manual que extrae el directorio COMPLETO de entidades asociadas de FEDER,
~476, para el fichero de prospección del operador).

0a. REMATE PANEL: añade el cubo `aceptadas` (EstadoMatch.ACEPTADA) a
   `ResumenPanel` y `resumen_panel` en `src/ongs_ai/servicios/panel.py`
   (mismo orden más-reciente-primero) + test. Era omisión del prompt de
   F4.2, no decisión de diseño.
0b. REMATE GITIGNORE: el patrón `investigacion/asociaciones*` NO cubre
   `investigacion/R2_asociaciones_eerr_tanda1.xlsx`. Sustitúyelo por
   `investigacion/*asociaciones*` y verifica con `git check-ignore` que
   cubre TODOS los ficheros de datos presentes en investigacion/ que
   contengan "asociaciones" (los R1_* del catálogo siguen trackeados).

1. `scripts/scrape_feder.py` — script MANUAL con red real (documenta en el
   docstring que hace red y NO corre en CI): recorre la paginación real de
   https://www.enfermedades-raras.org/movimiento-asociativo/entidades-asociadas
   (descubre el parámetro de paginación del HTML real: enlace "página
   siguiente" / ?page=N), con pausa de 1-2 s entre peticiones y User-Agent
   identificable. De cada entidad del listado extrae: nombre, dirección,
   teléfono(s), email(s), web y provincia/CCAA si constan. Sé robusto a
   ficheros de ficha incompletos (dato ausente = vacío, jamás inventado).
2. Salida: `investigacion/asociaciones_feder_completo.xlsx` y `.csv`
   (comprueba con `git check-ignore` que el patrón
   `investigacion/asociaciones*` los cubre — los DATOS JAMÁS se commitean).
   Imprime al final un resumen: nº entidades, nº con email, nº con
   teléfono, nº de páginas recorridas.
3. La función de PARSEO (HTML → registros) va separada del transporte y se
   testea HERMÉTICAMENTE con un fixture HTML pequeño y sintético en
   tests/fixtures/ (estructura real, datos ficticios) — pytest sin red.
4. `python -m pytest -q` VERDE. El commit lleva script + test + fixture,
   NUNCA los datos extraídos. Incluye los cambios de engineering/06_* del
   working tree tal cual.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add, `git push`. Tras el commit, EJECUTA el script
una vez (tú tienes red), verifica el resumen impreso contra el contador
del directorio (~476) y repórtalo — los ficheros de datos quedan en
investigacion/, sin commitear.
```

### Bandeja del OPERADOR

- Pegar PROMPT-012 en Claude Code (Sonnet) y avisar para auditoría. Al cerrarse,
  EJECUTAR `python scripts/scrape_feder.py` (red real, lo pide el propio prompt) y
  reportar el resumen.
- `python scripts/smoke_email.py` cuando tengas buzón/credenciales SMTP (variables
  ONGS_AI_SMTP_*) — verifica el aviso por email real. Puede esperar.
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

- Máquina Windows: `python -m pytest -q`; rutas `C:\dev\ongs-ai`.
- Mount sandbox↔host: ver regla del traspaso (git = verdad de la pizarra).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
- `investigacion/asociaciones*` JAMÁS a git (datos personales; gitignorado).
