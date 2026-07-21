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

- **2026-07-22 — FEEDBACK DURO DEL OPERADOR (asumido por el arquitecto):** tres
  demos seguidas fallidas o decepcionantes. Causas reconocidas: (1) la consola de
  F-consola.1 es funcional pero SIN el diseño del prototipo, que era la expectativa
  explícita; (2) los scripts de demo del ARQUITECTO eran desechables sin tests —
  violando el espíritu del ritual — y el enlace mágico de semilla da 400 (sospecha:
  formato de fechas script-vs-app en la comparación SQL; se confirmará con test, no
  con hipótesis); (3) demasiadas instrucciones de demo dispersas en la pizarra.
  REPLANTEAMIENTO: **MÁXIMA PRIORIDAD = PROMPT-021** — consola con el diseño del
  prototipo + demo de UN comando testeada + fix del 400 con evidencia. Los bloques
  de demo dispersos se RETIRAN de esta pizarra; los scripts desechables del
  arquitecto (demo_semilla_local.py, demo_entidad_real.py) se retiran en el 021.
  F5 y F-consola.3 esperan.
- **2026-07-21 — PROMPT-020 / F-consola.1 CERRADO: APROBADO, HECHO f870150, 308
  tests, pushed. LA CONSOLA DEL OPERADOR EXISTE:** prospeccion/ + importador
  (verificado contra el CSV real: 511 filas, 0 descartes), scoring determinista con
  test de ANCLAJE a evaluar_elegibilidad, rol operador con separación verificada por
  inspección de rutas, solo_loopback con 404 (mejora sobre spec). Respuestas del
  arquitecto a las preguntas de la sesión: (1) "nacional (sede Murcia)" → corregido
  EN EL DATO del maestro CSV (no special-case en código); (2) web/tamano en
  Prospecto: APROBADO (aditivo, fuera de contrato); (3) fórmula de afinidad
  temática: auditada y APROBADA (solape sobre tipos detectados, neutral sin señal).
  **SIN PROMPTS EN COLA. Siguientes prompts al llegarles el turno: F-consola.2
  (conversión Prospecto→Entidad, tras usar la consola) · F-consola.3 (resto de
  vistas) · F5 (tras la demo real del operador).**
- **2026-07-21 — PROMPT-019 / ADR-006 CERRADO: APROBADO, HECHO 838373a.** Consola
  del operador con separación por construcción, Prospecto fuera del contrato,
  scoring determinista honesto (tres rechazos a la hipótesis del prototipo: sin
  probabilidad inventada, sin capacidad-de-ejecución en el score, plazo aparte).
  Pregunta bloqueante del mapeo de columnas RESUELTA por el arquitecto (autor del
  maestro) + export listo: `investigacion/asociaciones_maestro.csv` (UTF-8, 511
  filas, cabeceras Nombre/Web/Email/Teléfono/Ámbito/CCAA/Enfermedad-Colectivo/
  Personas visibles (cargo)/Tamaño/Fuente(s)/Notas). Defaults §6 aceptados en nombre
  del operador (clave por entorno, CSV, pesos 70/30, rango techo-teórico, señales
  aparte, sin hosting) — corregibles. **SIGUIENTE: PROMPT-020 (F-consola.1) EN COLA.**
- **2026-07-21 — 3er PISOTÓN DE PIZARRA (histórico), resuelto:** el clobber de la
  sesión Opus alcanzó también a 06_HISTORICO.md (regresó al día 18) y el commit
  838373a lo selló en git. RECONSTRUIDO ÍNTEGRO por el arquitecto (19 entradas,
  PROMPT-001→019) desde sus registros de sesión y los diffs de git. Pendiente:
  commit de docs del operador para sellar la reconstrucción.
- **2026-07-21 — PROMPT-018 CERRADO: APROBADO, HECHO 7ce0fd7, 256 tests, pushed.
  LA VISIÓN CORRE CON DATOS REALES:** pasada real = 50 convocatorias BDNS nuevas,
  extracción IA con la suscripción del operador (freno de plan funcionando),
  29 no elegibles con motivo, **1 propuesta real generada y avisada**. Detalle →
  histórico. **DESBLOQUEADO: la demo real del guion (bandeja) ya es ejecutable.**
  **SIGUIENTE EN COLA: PROMPT-019 (ADR-006, Opus) — consola del operador +
  candidatas + scoring.** F5 espera el feedback de la demo.
- **2026-07-21 — PROMPT-017 CERRADO: APROBADO, HECHO 1336741, 222 tests, pushed.**
  Fix SQLite multihilo verificado (Lock + check_same_thread; la sesión comprobó que
  los tests de regresión fallan con el fix revertido — práctica ejemplar).
  **EL PLAN TÉCNICO ORIGINAL ESTÁ COMPLETO SALVO F5.** La demo local del operador
  debería funcionar ya de punta a punta (semilla → magic link → panel → aceptar).
  **Fases: TODAS ✔ salvo F5 (preparación asistida) · SIN PROMPTS EN COLA — el de F5
  se redacta tras la demo del operador (su feedback de producto alimenta la spec).**
- **2026-07-21 — DECISIÓN DE PRODUCTO/ARQUITECTURA (operador + arquitecto):** v1
  opera como PROCESO LOCAL en el PC del operador (sin hosting aún) y la capa IA usa
  la SUSCRIPCIÓN de Claude del operador vía CLI de Claude Code en headless
  (`claude -p`), no API de pago por token. Reversible por diseño (Protocol de la
  capa IA); consume límites del plan → el adapter lleva tope de llamadas por pasada.
  Sin ADR (sin cambio de contrato); spec en PROMPT-018.
- **2026-07-21 — 2º PISOTÓN DE PIZARRA, resuelto:** la sesión Opus (arquitecto del
  día 19, aún activa) sobrescribió este 06 con su versión antigua al entregar el
  prototipo. Fusionado por Fable: estado del día 21 + las notas del prototipo.
  REGLA REFORZADA: un solo arquitecto ACTIVO; la sesión Opus queda RETIRADA — sus
  entregas futuras, solo vía ficheros en el repo + nota, como hizo esta vez.
- **PROTOTIPO VISUAL entregado por la sesión Opus (2026-07-19→21) — maqueta, NO
  plataforma.** `prototipos/ongs-ai-prototipo.html` (autocontenido, datos SINTÉTICOS;
  el mapa Leaflet/OSM pide red para teselas). Vistas: explorador de convocatorias,
  entidades, **cruce entidad×subvención con puntuación de afinidad + importe
  potencial** (HIPÓTESIS de producto — el dominio hoy solo decide elegible sí/no →
  si se adopta, ADR-006) y mapa de sedes. Revisado con Web Interface Guidelines +
  ux-reviewer (AA, teclado, reduced-motion). Decisión de método heredada: prototipo
  primero, cablear después. **El operador quiere cablear el "paso previo": encontrar
  candidatas → consola del OPERADOR sobre datos reales (spec en ADR-006, tras
  PROMPT-018).**
- PROMPT-016 (8ebfb1d): instalable + comando canónico. F-web.2 (455de38): acciones
  con CSRF. Detalle en histórico.
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

#### PROMPT-018 — Proceso local de ingesta + adapter IA "Claude por suscripción" (CLI headless) · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: v1 operativa como proceso local. Dos piezas: (A) adapter IA que usa
la suscripción de Claude del operador vía CLI headless, (B) runner de
ingesta local de punta a punta. La regla de oro manda: la IA propone, el
dominio valida — NADA de lo que devuelva el CLI entra al dominio sin pasar
el guardarraíl existente.

A1. `src/ongs_ai/ia/claude_cli.py`: cliente genérico que invoca el binario
   `claude` en headless: subprocess con `claude -p "<prompt>"
   --output-format json` (descubre la forma exacta de la salida JSON
   ejecutándolo tú una vez y documéntala; si el formato de tu entorno
   difiere, adapta y documenta). Inyectable TODO: ruta del binario (env
   ONGS_AI_CLAUDE_CLI, default "claude"), timeout (default 120 s),
   ejecutor de subprocess (para tests). Errores (binario ausente, timeout,
   salida no-JSON, límite de plan agotado) → degradación limpia con log +
   contador, JAMÁS excepción al dominio. En pytest NUNCA se invoca el
   binario real: ejecutor stub SIEMPRE.
A2. Implementación real de `GeneradorExplicacion` sobre ese cliente
   (`ExplicadorClaudeCLI`): prompt corto en castellano que pide UNA
   explicación de por qué la convocatoria encaja con la entidad (texto
   plano, 2-4 frases, sin inventar datos: solo los campos que le pasas).
   Factory por entorno junto a las demás (test → ExplicadorStub).
A3. Extractor IA de requisitos — `src/ongs_ai/ia/extraccion_requisitos.py`:
   dada una Convocatoria EXTRAIDA, pide al CLI que derive, SOLO del texto
   ya presente (objeto + beneficiarios_elegibles; NO fetchees bases
   externas en esta fase), un JSON con forma_juridica_requerida (texto),
   antiguedad_minima_anios (int o null) y requisitos_formales_requeridos
   (lista de los flags cerrados; los desconocidos se descartan). El
   RESULTADO pasa por validación determinista (enums/typos → descartar
   campo, jamás inventar) y produce una Convocatoria nueva con
   requisitos_elegibilidad enriquecidos SOLO donde estaban vacíos (nunca
   pisa un dato ya presente). Salida no parseable → convocatoria intacta +
   contador. Tests con ejecutor stub (respuestas grabadas: válida,
   basura, campos desconocidos, timeout).
A4. FRENO DE PLAN: parámetro max_llamadas_ia por pasada (default 25) en el
   runner — al agotarse, el resto de convocatorias se procesa SIN IA y se
   informa en el resumen. Los límites de suscripción ya nos han cortado
   dos veces: el proceso nunca debe morir por ello.

B1. `scripts/ejecutar_ingesta.py` — runner MANUAL/programable con red real
   (documenta que NO corre en CI): pipeline completo → FuenteBDNS.buscar
   (filtros por parámetros CLI: texto, fechas, páginas máx) → ingestar con
   dedupe → extracción IA (A3, con freno) → promocionar_si_completa →
   detectar_y_proponer (con ExplicadorClaudeCLI y NotificadorEmailSMTP
   reales si hay env SMTP; si no, stub con aviso en consola) → imprime
   resumen (ingestadas, deduplicadas, enriquecidas por IA, promovidas,
   propuestas nuevas, avisos, llamadas IA usadas). Fecha de referencia =
   hoy explícito en el entrypoint (fuera del dominio).
B2. Tests del runner: SOLO de su función de orquestación con todo stub
   (sin red, sin CLI); el script en sí es manual como smoke_bdns.

C. `python -m pytest -q` VERDE con el nº REAL de tests. Incluye
   engineering/06_* del working tree tal cual. NO toques contrato ni
   máquina de estados.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add, `git push` al terminar. Tras el commit,
EJECUTA una pasada real corta (páginas máx=1, max_llamadas_ia=3) y pega el
resumen impreso — verificación humana del pipeline completo con tu
suscripción.
```

#### PROMPT-021 — Consola con el diseño del prototipo + demo de UN comando + fix del enlace · MODELO: Sonnet · ORDEN: 1º (nada en paralelo) · MÁXIMA PRIORIDAD

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

CONTEXTO: el operador ha probado la consola y las demos y el veredicto es
"no es lo que espero ver". Este prompt lo arregla ENTERO o no vale: al
cerrar, UN comando debe dejar TODO listo y la consola debe parecerse al
prototipo. Tres bloques, los tres obligatorios:

A. LA CONSOLA CON EL DISEÑO DEL PROTOTIPO
A1. `prototipos/ongs-ai-prototipo.html` es la SPEC VISUAL (léelo entero:
   paleta, tipografía, tarjetas, claro/oscuro, estructura de pantallas).
   Extrae su CSS a un estático de la consola
   (`web/estaticos/consola.css`, servido por la app — monta StaticFiles
   SOLO para la consola) y replica en plantillas Jinja reales:
   - Dashboard (/consola): métrica arriba (nº candidatas, nº
     convocatorias vivas, importe potencial agregado) + "Oportunidades
     más afines ahora" (top cruces por score, tarjetas como el prototipo).
   - /consola/convocatorias: listado real (BDNS ya ingestada) con
     filtros básicos por texto/ámbito/estado (GET, server-side).
   - /consola/entidades: candidatas (Prospectos) + entidades captadas,
     buscables por nombre/CCAA.
   - /consola/cruce: la matriz "a qué puede presentarse, cuántos puntos y
     qué importe" — por perfil seleccionado, sus convocatorias ordenadas
     por score con el desglose motivo a motivo (cumple/incumple/
     pendiente_de_dato) y el rango de importe techo-teórico.
   - Mapa de sedes: EXCEPCIÓN CONSCIENTE autorizada por el arquitecto —
     Leaflet/OSM vía CDN SOLO en plantillas de consola (localhost,
     operador); degrada limpio sin red (la página funciona sin mapa).
     Las direcciones salen del campo de notas del Prospecto si existen.
   Los datos SIEMPRE de los almacenes reales vía los servicios ya
   auditados (resumen_prospeccion, evaluar_afinidad, listar_*): NADA
   hardcodeado, NADA sintético en la consola.
A2. Accesibilidad como el prototipo: foco visible, contraste AA,
   reduced-motion. Autoescape intacto.

B. DEMO DE UN COMANDO, TESTEADA
B1. `scripts/preparar_demo.py` — deja TODO listo e imprime el resultado:
   1) si la BD tiene <20 convocatorias VERIFICADAS y hay red, ejecuta una
   pasada de ingesta corta (reutiliza ejecutar_ingesta con flags
   conservadores; sin red o si falla → sigue con lo que haya, avisando);
   2) siembra/actualiza la entidad demo (perfil ABAIMAR con supuestos
   marcados, email del operador por argumento) usando LAS MISMAS factorías
   y relojes de la app — ni un timestamp fabricado a mano;
   3) importa los prospectos del CSV si existe y aún no están;
   4) genera enlace mágico de entidad Y deja instrucción de acceso de
   operador, e IMPRIME en un bloque final claro: URL del panel de entidad
   (enlace confirmable), URL de la consola, la clave de operador que debe
   estar en el entorno, y el comando uvicorn exacto.
   La ORQUESTACIÓN es una función testeada con stubs en CI (como
   ejecutar_ingesta); el script es el envoltorio con red/disco.
B2. RETIRA `scripts/demo_semilla_local.py` y `scripts/demo_entidad_real.py`
   (desechables del arquitecto, sin tests — sustituidos por esto).
B3. Sección nueva y ÚNICA de demo en README o docs/DEMO.md: los 4 pasos
   exactos (variables de entorno → preparar_demo → uvicorn → abrir URLs).

C. EL 400 DEL ENLACE, CON EVIDENCIA
C1. Test de integración que reproduce el camino EXACTO que falla: sembrar
   entidad+token contra AlmacenSQLite en fichero temporal (no :memory:)
   con el MISMO código que usará preparar_demo, levantar la app con ese
   almacén, GET /login/confirmar?token=... → debe crear sesión. Hazlo
   fallar primero si el bug existe (sospecha del arquitecto: formato/zona
   de fechas entre el sembrado y el reloj de la app en la comparación SQL
   de expira_en — verifica leyendo consumir_token y los ISO reales), luego
   arregla la CAUSA en el sitio correcto (probablemente normalizar
   fechas a UTC-aware en la frontera del almacén) y deja el test verde.
C2. Suite completa VERDE con el nº REAL de tests.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (JAMÁS los CSV/xlsx de investigacion/), git push.
Tras el commit, EJECUTA tú mismo la secuencia completa de docs/DEMO.md de
punta a punta (tú tienes red y navegador headless no hace falta: verifica
al menos que preparar_demo imprime URLs y que GET /consola y el enlace de
entidad devuelven 200/303 vía TestClient o curl) y pega el resultado.
```

### Bandeja del OPERADOR

- **Pegar PROMPT-021 (Sonnet) — COPIA la versión ACTUAL del 06.** Es LA prioridad;
  no hay más demos que probar hasta que cierre. Al cerrar: seguir docs/DEMO.md
  (4 pasos, un comando de preparación) y dar el veredicto.
- Commit de docs pendiente cuando quieras:
  `git add engineering/ && git commit -m "Pizarra (docs)" && git push`
- En espera (sin acción tuya hasta después del 021): entidad piloto (candidatas en
  la consola cuando la veas bien), SMTP real, programación diaria de la ingesta,
  censo completo FEDER.

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

- **ADR-006 (Opus) — SIGUIENTE tras auditar PROMPT-018:** consola del OPERADOR
  cableada al dominio real (las vistas del prototipo: convocatorias ingeridas,
  entidades/candidatas, cruce con elegibilidad motivo a motivo) + modelo de
  puntuación de afinidad e importe potencial (hoy hipótesis del prototipo; amplía el
  guardarraíl binario con scoring SIN tocar su determinismo) + cómo cargar candidatas
  del maestro de prospección sin violar el contrato (campos obligatorios que un
  prospecto no tiene → probable estado/almacén de prospectos). Referencia de diseño:
  el prototipo. El prompt lo redacta el arquitecto al llegarle el turno.
- `engineering/12_SISTEMA_VISUAL.md` (paleta/tokens de ONGs-AI) cuando el diseño del
  prototipo se dé por bueno; ajustar entonces la vara del ux-reviewer.

### Recordatorios operativos

- Consola de Windows muestra acentos como � (cp1252): cosmético; `chcp 65001` lo
  arregla por sesión. El dato subyacente es UTF-8 correcto.
- ANTES de pegar un prompt: copialo del 06 ACTUAL, tras el ultimo aviso del
  arquitecto — dos prompts ya se ejecutaron en version vieja (015 y 016).

- Máquina Windows: SIEMPRE `python -m ...` (pytest, uvicorn — los .exe de Scripts no
  están en PATH); rutas `C:\dev\ongs-ai`. **Puerto 8000 OCUPADO por otro proyecto →
  ONGs-AI usa el 8001.** Hasta que PROMPT-015 arregle el empaquetado: `set
  PYTHONPATH=src` antes de arrancar uvicorn (pytest no lo necesita).
- Mount sandbox↔host: ver regla del traspaso (git = verdad de la pizarra).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
- `investigacion/asociaciones*` JAMÁS a git (datos personales; gitignorado).
