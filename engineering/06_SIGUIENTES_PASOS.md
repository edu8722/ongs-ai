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
> fichero entero. La pizarra (engineering/06_*) la mantiene SOLO el
> arquitecto: no cierres items, no te declares APROBADO, no muevas nada al
> histórico — limítate a incluir en tu commit los cambios de
> engineering/06_* que ya estén en el working tree, tal cual estén.

---

## ESTADO VIVO

- **2026-07-19 — F2 CERRADA Y AUDITADA — APROBADO (`5a52d27`, 126 tests, pushed).**
  Adapter de ingesta contra la API pública de la BDNS. Auditoría INDEPENDIENTE del
  arquitecto (no solo el resumen de la sesión): leído el código real de todos los
  ficheros tocados + reproducción parcial en sandbox (sin pytest/PyPI: 0 fallos de
  import en `src`, **99 casos ejecutados en verde y 0 rojos** — 71 sin fixture + 28
  del contrato de persistencia/dedupe corridos sobre `memoria` y `sqlite :memory:`—,
  con las rutas de degradación limpia comprobadas). Todas las reglas de oro se
  respetan: dinero euros→céntimos `int` vía `Decimal` (nunca float al dominio),
  filtros como datos (nada hardcodeado), transporte inyectable con red apagada en
  tests, dedupe idempotente `portal`+`url_origen` (nuevo puerto
  `obtener_por_url_origen` cumplido en AMBOS adapters), degradación limpia, promoción
  `EXTRAIDA→VERIFICADA` como función de dominio pura. Detalle → histórico.
  **Estado de fases: F1 ✔ · ADR-002 ✔ · F3 ✔ · F2 ✔ (con corrección PROMPT-009
  pendiente) · PROMPT-009 (F2-fix ámbito provincial) SIGUIENTE · F4 después · F5 lejos.**
- **Smoke test de F2 EJECUTADO por el operador (2026-07-19) — API viva OK.** 5
  convocatorias reales mapeadas de punta a punta: nombres de campo
  (`numeroConvocatoria`/`content`/`last`, `codigoBDNS`, `numConv`, `presupuestoTotal`,
  `regiones`, `organo.nivel1`) CONFIRMADOS contra la API real; dinero cae bien en
  céntimos int; `estado_ingesta` extraida/verificada correcto (las nominativas/
  convenios sin plazo de solicitud quedan `extraida` — guardarraíl funcionando, no
  fallo). El parámetro `tipoBeneficiario` no se ejerció (búsqueda sin filtro) —
  seguirá pendiente hasta que se use un filtro por beneficiario.
- **BUG CONFIRMADO EN VIVO por el smoke → corrección PROMPT-009 (F2-fix).** El adapter
  etiqueta los códigos NUTS3 (provincia, `ES`+3 dígitos: Bizkaia, Pontevedra, Córdoba)
  como `ambito_geografico=autonomico` con la provincia en `region`, cuando el contrato
  YA admite `AmbitoTerritorial.PROVINCIAL` y `Convocatoria.provincia`. NO es cambio de
  contrato: es que el mapeo de `bdns.py` no usa esos valores. Y NO es caso borde — las
  locales/provinciales son una fracción enorme de la BDNS, así que rompe el matching
  territorial de F3 (que consume `ambito_geografico`). Corrección de adapter, SIN ADR.
  Prompt listo en la cola (ORDEN 1º, antes de F4).
- **R1 (catálogo de fuentes) ENTREGADA (`investigacion/R1_*`)**, commiteada en
  `5a52d27` (xlsx + informe, sin datos personales). Hallazgo clave: BDNS = una sola
  API cubre todo el sector público → por eso F2 fue un único adapter. Verificación
  adversarial de las 22 fuentes de R1 quedó incompleta (0 refutadas): re-pasada
  OPCIONAL, backlog.
- **R2 (directorio asociaciones EERR) — 1ª PASADA ENTREGADA por el ARQUITECTO
  (2026-07-19).** La sesión Fable la había lanzado (18-jul ~23:30) pero se quedó sin
  tokens antes de producir fichero; se rehízo de cero. Entregables FUERA de git
  (gitignore `investigacion/asociaciones*` verificado con `git check-ignore`):
  `investigacion/asociaciones_EERR_directorio.xlsx` (hojas Léeme/Asociaciones/
  Directorios) + `asociaciones_EERR_informe.md`. Contenido: **9 directorios
  agregadores mapeados con veredicto de scrapeabilidad** (FEDER 476 y Somos Pacientes
  —incl. PDF de 171 EERR— = scrapeabilidad ALTA, las vías para la extracción
  sistemática) + **81 asociaciones concretas con contacto público**, mayoría pequeñas
  (cliente objetivo), de casi todas las CCAA. Método: 3 investigaciones web en
  paralelo (FEDER / Somos Pacientes+POP / federaciones autonómicas), dato tomado
  literal de fuente (vacío = no encontrado, nunca inventado), solapes consolidados.
  ⚠ Dato personal: responsable del tratamiento = el operador; no difundir.
  Expectativa honesta cumplida: NO es el censo (~476 solo FEDER) — es mapa + 1ª tanda;
  la extracción completa = 2ª pasada sistemática (o feature de la plataforma).
  El informe propone candidatas a piloto (GERNA, PERA, ARER, ASERCA, ABAIMAR, red
  ASEM regional) → el arquitecto ofrece redactar el mensaje de propuesta.
- **Lección del ritual** (sigue vigente, 3 casos + este 4º refuerzo): los resúmenes
  de las sesiones exceden o desmienten lo real — mensaje de commit (PROMPT-002),
  "decisión conservadora" que rompía el puerto (PROMPT-004), auto-cierre "APROBADO"
  antes de auditar (PROMPT-006). En F2 el resumen sí coincidió con lo real, pero se
  auditó igual leyendo el código y reproduciendo tests. Auditar SIEMPRE el artefacto.
- **Duele:** sigue sin entidad piloto. Test anti-hardcoding v1 es canario débil —
  endurecer en F4+. Contrato sin `municipio` en Entidad → ámbito LOCAL no evaluable
  automáticamente (ADR si el matching local lo pide).
- **Remoto git ACTIVO**: `origin` = github.com/edu8722/ongs-ai (privado), al día
  (`origin/main` = `5a52d27`). El `git push` del ritual es OBLIGATORIO en cada cierre.
- **Nota de sincronía de pizarra:** los cambios de este 06 (cierre de F2) están en el
  working tree pero AÚN SIN COMMIT — los arrastra el próximo commit de empleado
  (el de F4), según el modelo. Si tardara, el operador puede commitearlos sueltos.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-009 — F2-fix: ámbito provincial (NUTS3) en el adapter BDNS · MODELO: Sonnet · ORDEN: 1º (antes de F4; nada en paralelo)

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

TAREA: corrección de F2 (adapter BDNS). Bug CONFIRMADO con la API viva
(smoke test del operador): las convocatorias con una única región cuyo
código es NUTS3 (provincia, "ES"+3 dígitos, p. ej. "ES213 - Bizkaia",
"ES114 - Pontevedra", "ES613 - Córdoba") se mapean como
ambito_geografico=AUTONOMICO con la provincia metida en `region`. El
contrato (dominio/entidades.py) YA admite AmbitoTerritorial.PROVINCIAL y el
campo Convocatoria.provincia — NO hay cambio de contrato, solo el mapeo de
bdns.py no los usa. NO toques el contrato ni ningún ADR.

Alcance EXACTO — solo `_ambito_y_region_desde_regiones` (y su docstring) en
src/ongs_ai/adapters/ingesta/bdns.py, más fixtures/tests. La función pasa a
devolver una TERNA (ambito, region, provincia) — o refactor equivalente — y
`_mapear_convocatoria` rellena `region`/`provincia` en consecuencia. Regla
determinista, a partir del código que precede a " - " en la descripción de
la ÚNICA región (cuando hay exactamente una):
  - parte numérica tras "ES":
    - vacía (código == "ES") → NACIONAL, region=None, provincia=None.
    - EXACTAMENTE 2 dígitos (NUTS2, CCAA) → AUTONOMICO, region=nombre,
      provincia=None. (comportamiento actual, se conserva)
    - EXACTAMENTE 3 dígitos (NUTS3, provincia) → PROVINCIAL, provincia=nombre,
      region=None. (NUEVO — derivar la CCAA desde el NUTS3 queda FUERA de
      alcance: no montes tabla NUTS3→NUTS2, déjalo anotado como mejora futura)
    - cualquier otra cosa (no empieza por "ES", parte no numérica, etc.) →
      NACIONAL, region=None, provincia=None. (default conservador actual)
  - cero regiones o más de una → NACIONAL, region=None, provincia=None.
    (se conserva)
NO uses `organo.nivel1`/`tipo` para decidir el ámbito: `tipo` (nivel
administrativo de la fuente) y `ambito_geografico` (granularidad geográfica
de `regiones`) son ortogonales y pueden diferir — ya está así documentado y
testeado; mantenlo. No intentes distinguir municipal de provincial (la BDNS
no da municipio en `regiones`): NUTS3 → PROVINCIAL es lo máximo determinista.

Sigue mirroreando `requisitos_elegibilidad.ambito_territorial_requerido =
ambito_geografico` como hasta ahora (ahora también podrá ser PROVINCIAL).

Actualiza la docstring del módulo/función: sustituye la nota de
"simplificación conocida: no desambigua NUTS2/NUTS3" por la regla nueva.

FIXTURES/TESTS:
  - Ajusta el fixture de la convocatoria LOCAL (detalle_100003): su región
    debe llevar un código NUTS3 real de 3 dígitos (p. ej. "ES613 - Córdoba");
    el test pasa a esperar ambito_geografico=PROVINCIAL, provincia="Córdoba",
    region=None (y tipo sigue PUBLICA_LOCAL — sigue demostrando que tipo y
    ámbito difieren, ahora bien).
  - Conserva un caso NUTS2 (ES+2 dígitos) → AUTONOMICO con region.
  - Conserva el caso multi-región / "ES - ESPAÑA" → NACIONAL.
  - Añade un caso de código raro (no-ES o no numérico) → NACIONAL.
  - Verifica que la promoción EXTRAIDA→VERIFICADA sigue igual (ambito_geografico
    nunca es None, así que los campos mínimos no cambian).
  - `python -m pytest -q` VERDE y HERMÉTICO (sin red). Chequeo sintáctico de
    cada fichero tocado.

Incluye en tu commit los cambios de engineering/06_* que ya estén en el
working tree, tal cual estén (cierre de F2 + entrega de R2 por el arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add (ni .env, ni var/, ni investigacion/asociaciones*),
`git push` al terminar.
```

### Bandeja del OPERADOR

- **F2 — smoke test HECHO (2026-07-19):** API viva OK; destapó el bug de ámbito
  provincial → corrección en PROMPT-009.
- **Pegar PROMPT-009 (F2-fix)** en una sesión de Claude Code (Sonnet) y avisarme al
  terminar para auditoría. Es la siguiente acción de código (antes de F4).
- Revisar el Excel de R1 y decirme si falta algún portal de los que usabas.
- **Captar entidad piloto** (acceso + ingresos/gastos del ejercicio anterior +
  lista de actividades). Te ofrezco redactar el mensaje de propuesta cuando quieras
  — R2 nos dará candidatas.
- Decidir conmigo la política de persistencia de matches no elegibles (entra en F4).

### Backlog

- **F4 propuesta/aviso** (email + panel; el panel adelanta la necesidad del esqueleto
  web — subir prioridad). Decisión abierta a cerrar antes de redactar el prompt: NO
  persistir el Match de cada pareja no elegible a escala BDNS (hoy `detectar_matches`
  crea Match para toda pareja — literal del prompt de F3). Candidato a mini-ADR.
- **F5 preparación asistida** (alcance ampliado por el operador: checklist de
  requisitos documentales con gap qué-tiene/qué-falta + borrador de TODOS los
  documentos entregables; probable ADR de ampliación de contrato — entidad
  `DocumentoRequerido`). Prompt al quedar auditada F4 (ADR-001 §5).
- **ADR-003 candidato**: redundancia de ámbito en el contrato (`ambito_geografico`+
  region/provincia vs `ambito_territorial_requerido` sin consumir) — limpiar. (La
  desambiguación NUTS2/NUTS3 se resuelve ya en PROMPT-009, no espera al ADR.)
- Derivar CCAA (`region`) desde el código NUTS3 provincial — tabla NUTS3→NUTS2;
  mejora futura, fuera del alcance de PROMPT-009.
- Adapters privados de ingesta (FEDER, la Caixa, ONCE) + agregador SolucionesONG —
  tras F2 (ya desbloqueado).
- Proveedor LLM real para la capa IA (hoy `ExplicadorStub`) — decisión del arquitecto.
- Endurecer el test anti-hardcoding (el canario del ADR pasa por construcción).
- Re-pasada de verificación adversarial de R1 (22 fuentes, 0 refutadas) — opcional.
- **R2 2ª pasada** (extracción sistemática Somos Pacientes/FEDER/ASEM/FEGEREC hasta
  varios cientos) + cruce de personas/cargo solo para la lista corta de piloto +
  verificación de vigencia de webs/emails antes de un envío real — opcional/cuando
  toque captación en volumen.
- Esqueleto de la app (fija el comando de servidor local en CLAUDE.md).
- Modelo de negocio (las entidades objetivo tienen pocos recursos) — conversación
  de producto, sin prisa técnica.
- Ajustar la "vara de medir" de ux-reviewer.md cuando exista sistema visual propio.

### Recordatorios operativos

- Máquina Windows: comandos como `python -m pytest -q` (no rutas unix); rutas con `C:\dev\ongs-ai`.
- Mount sandbox↔host miente con ficheros recién editados — el HOST es la verdad.
- Git desde sandbox: SOLO `git log`/`git show`; jamás status/diff (index.lock huérfanos).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
