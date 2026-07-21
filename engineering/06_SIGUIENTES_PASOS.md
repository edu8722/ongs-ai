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

- **2026-07-22 — DEFAULTS §8 DEL ADR-007 ACEPTADOS EN BLOQUE POR EL OPERADOR
  ("defaults OK"):** historial 5 años · 1 edición basta (BAJA) · ventana
  próxima solo panel · NO_APARECIDA a +2 meses · nominativas sin "preséntate" ·
  re-derivación tras cada ingesta. Servidores viejos cerrados por el operador y
  commit de docs hecho. **PROMPT-027 (F-proactivo.1) REDACTADO Y EN COLA** —
  incluye la calibración del fingerprint decidida por el arquitecto en la
  auditoría del ADR (nivel1+nivel2+título; nivel3 fuera por renombres de
  consejerías) y un smoke real sin contaminar la base (--nif-prueba con el NIF
  público ya usado en la verificación del ADR).
- **2026-07-22 — PROMPT-026 / F-consola.3 CERRADO: APROBADO, HECHO 7fb9d05, 389
  tests, pushed. EL OPERADOR YA NO NECESITA LA TERMINAL.** Auditado: filtros GET
  en todas las vistas (entidades tipo/CCAA, cruce estado/score-mín/texto, mapa
  CCAA/texto, dashboard CCAA) con "limpiar filtros"; orquestación movida a
  servicios/pasada_ingesta.py (script = CLI fino); acciones web con
  RegistroEjecucion (threading.Lock, hilo/reloj inyectables, stub síncrono en
  CI), candado testeado, rutas con solo_loopback+operador. Verificación en
  vivo de la sesión: click en "Actualizar convocatorias" → "En curso" con
  botones deshabilitados → 13 min de pasada real (BDNS + CLI Claude) →
  resumen honesto en dashboard (1 nueva, 1.545 dedupe, 1.400 no-abiertas,
  657 concesión directa, 13 llamadas IA) → botones reactivados.
  NOTA OPERATIVA de la sesión: uvicorn VIEJOS colgando en puertos 8000-8003 —
  el del 8001 puede servir código antiguo; matar y relanzar (bandeja).
  NOTA DEL ENTORNO del arquitecto: su sandbox recicló estado y su copia local
  de la pizarra retrocedió; recuperada desde el disco del operador (git/disco
  = verdad, confirmado una vez más).
  **COLA VACÍA. SIGUIENTE: F-proactivo.1 — se redacta EN CUANTO el operador
  conteste los 6 defaults del §8 del ADR-007 (o diga "defaults OK").**
- **2026-07-22 — PROMPT-025 / ADR-007 CERRADO: APROBADO, HECHO 077a8c4 (372
  tests, sin código).** Leído íntegro (568 líneas) y auditado contra método y
  contrato: verificación en vivo ejemplar (nifCif SÍ filtra: 76/0/28M con
  fechas dd/mm/yyyy combinables; descripcionBeneficiario confirmado inútil;
  enlace numeroConvocatoria==codigoBDNS verificado; fallback documentado);
  HistorialConcesion (hecho) y ConvocatoriaEsperada (estimación) en proactivo/
  FUERA del contrato; ventana SIEMPRE rango/mes desde la APERTURA de ediciones
  previas (no la concesión — matiz de honestidad excelente); 1 edición →
  confianza BAJA etiquetada (honra el "en base al año pasado" literal); ≥2 →
  ventana [min,max] con confianza; fingerprint determinista que degrada a MISS
  (jamás esperada falsa, sin IA); esperada NUNCA crea Match (enlaza al
  publicarse y el guardarraíl intacto decide); concesión directa →
  accionable=False; anti-fuga ampliado; todo aditivo y reversible.
  **OBSERVACIÓN del arquitecto para F-proactivo.1 (no bloquea):** el
  fingerprint incluye organo nivel3 (consejería) y las consejerías se
  RENOMBRAN entre años (el propio histórico de Aniridia lo muestra: "Familia,
  Juventud y Asuntos Sociales" antes "Políticas Sociales") → misses evitables;
  calibrar en implementación (p. ej. fingerprint por nivel1+nivel2+título, con
  nivel3 solo como desempate) manteniendo la degradación a miss.
  **PENDIENTE DEL OPERADOR: las 6 preguntas de calibración del §8 del ADR
  (todas con default razonable — puede aceptarlas en bloque).**
  **SIGUIENTE EN COLA: PROMPT-026 (F-consola.3, Sonnet). F-proactivo.1 lo
  redacta el arquitecto al cerrar el 026, con las respuestas del §8.**
- **2026-07-22 — PROMPT-024b CERRADO: APROBADO, HECHO 6528a29, 372 tests,
  pushed.** convocatorias_utiles excluye descartadas en dashboard/cruce;
  /consola/convocatorias las oculta por defecto con checkbox auditable (motivo
  de exclusión visible) y aviso "N descartadas ocultas". Bug incidental cazado
  contra la base real y arreglado con regresión: convocatorias sin ninguna
  fecha reventaban la vista (date vs None). MEDIDO con la base real (~1.561 ×
  513): dashboard 29,3s→0,26s · cruce 0,43s→0,08s · convocatorias 500→0,06s.
  NOTA DE REGISTRO: el mensaje del commit dice "PROMPT-025" por error de
  etiqueta de la sesión — corresponde al 024b; el 025 de la cola sigue siendo
  el ADR-007. **SIGUIENTE: pegar PROMPT-025 (ADR-007, OPUS — solo diseño).**
- **2026-07-22 — PROMPT-024 CERRADO: APROBADO, HECHO 3947e11, 368 tests, pushed.
  LA COBERTURA EXISTE.** Auditado: batería versionada de 11 términos con
  justificación por término (config de producto, no dato de ONG — documentado),
  parámetro `descripcion` verificado, tope de páginas POR búsqueda, freno IA y
  dedupe GLOBALES a la pasada, resumen por búsqueda, 4 tests de batería;
  verificado en vivo y documentado que `abierto=` NO filtra en servidor (no se
  usa). Pasada real: 1.458 ingestadas / 88 ya existentes. CONTRASTE CON EL
  HISTÓRICO DE ANIRIDIA: IRPF 0,7% estatal, IRPF CAM, ayuda mutua CAM y
  asociacionismo municipal APARECEN (todas con plazo ya cerrado hoy →
  descartadas honestas); mantenimiento CAM no publicado aún. Conclusión: la
  búsqueda funciona; lo que falta es VIGILANCIA de ediciones (ADR-007) — la
  tesis del operador confirmada con datos.
  **CONSECUENCIA OPERATIVA INMEDIATA: la base pasó de ~50 a ~1.550
  convocatorias (mayoría DESCARTADAS persistidas para dedupe). Las vistas de
  consola evalúan TODAS × 512 perfiles → consola lenta y cruce enterrado en
  descartadas. Remiendo pequeño encolado como PROMPT-024b, ANTES del ADR.**
- **2026-07-22 — TERCER PAQUETE DE FEEDBACK DE PRODUCTO DEL OPERADOR (voz del
  producto, convertido a spec):** (1) convocatorias ESPERADAS: en base a años
  anteriores, mostrar a cuáles podría presentarse cada asociación aunque la
  edición de este año aún no exista, con estado "pendiente de publicar" y FECHA
  ESTIMADA de publicación derivada de las fechas de ediciones previas → entra
  como requisito de primer nivel en ADR-007 (vigilancia de recurrentes). (2)
  FILTROS EN TODAS LAS PANTALLAS de la consola → F-consola.3. (3) ACCIONES
  DESDE LA WEB: botones para relanzar la actualización de convocatorias
  (ingesta) y recalcular a qué puede presentarse cada asociación, sin tocar la
  terminal → F-consola.3, con diseño conservador (ejecución en segundo plano
  con candado anti-doble-pasada y estado visible de la última ejecución; el
  detalle lo fija el prompt del arquitecto). ORDEN DE COLA CONFIRMADO:
  PROMPT-024 (cobertura, YA EN COLA — sin cambios, pégalo cuando quieras) →
  ADR-007 (Opus, diseño de recurrentes con lo de arriba) → F-consola.3
  (filtros + acciones web) → F-recurrentes.1 (implementación del ADR). Si
  prefieres ver antes los filtros/botones que las recurrentes, dímelo y
  intercambio ADR-007 y F-consola.3.
- **2026-07-22 — SEGUNDO HALLAZGO DE PRODUCTO DEL OPERADOR: COBERTURA. Faltan
  convocatorias (IRPF estatal/autonómico, etc.).** Evidencia aportada: PDF del
  histórico real de concesiones de Aniridia 2022-2024 (15 ayudas: CAM IRPF 0,7%
  y mantenimiento, Ayto. Madrid/Moncloa-Aravaca, diputaciones Castellón/Granada/
  Alicante, Ministerio de Educación). Diagnóstico del arquitecto, verificado
  contra la API real: la ingesta solo pagina las publicaciones MÁS RECIENTES
  (ventana de decenas sobre ~639k) — nunca hemos BUSCADO. Verificado sin usar:
  (1) /convocatorias/busqueda acepta `descripcion=` (IRPF → 424 resultados
  reales, estatal 0,7% incluida); (2) existe /concesiones/busqueda paginado (la
  fuente del propio PDF). Dos piezas: PROMPT-024 (cobertura por búsquedas
  dirigidas, EN COLA) y ADR-007 (vigilancia de recurrentes + historial por NIF
  — muchas ayudas del PDF son ediciones pasadas cuya edición 2026 aún no está
  publicada; hay que avisar cuando aparezca, no buscarla antes de que exista).
  El PDF del operador NO viaja a git (guardar como
  investigacion/aniridia_concesiones_2022_2024.pdf, untracked).
- **2026-07-22 — PROMPT-023 CERRADO: APROBADO, HECHO 36a95a3, 364 tests, pushed.**
  Auditado contra el repo real: tabla cerrada NUTS1→CCAA + tope por órgano
  (invariante que impide ámbito más amplio que el convocante), descarte en
  ingesta de abierto=false y concesiones directas (dato ausente nunca descarta),
  fixture REAL del caso Aniridia/CCOO (920435) como regresión permanente,
  scripts/reevaluar_ingesta.py con --simular por defecto, badge "requisitos sin
  datos" en el cruce. Decisiones de la sesión auditadas y correctas (fixtures
  100002-100004 a abierto=true para no invalidar sus aserciones;
  mapear_convocatoria público para reutilizar la lógica testeada).
  **El plan --simular dice 50 de 52 → DESCARTADA (mayoría por cerradas en
  origen): es el resultado HONESTO — la base actual se ingirió sin estos
  filtros. Tras --aplicar la consola quedará casi vacía de convocatorias:
  el paso siguiente inmediato es una pasada de ingesta nueva, que ya solo
  traerá abiertas de verdad.** Las 2 saltadas son demo-conv-* (ficticias del
  antiguo script del arquitecto) — limpiar antes de cualquier demo a una
  asociación real (anotado en bandeja).
  **SIN PROMPTS EN COLA — el siguiente lo decide el veredicto del operador
  usando la consola con datos ya honestos.**
- **2026-07-22 — PROMPT-022 CERRADO: APROBADO, HECHO 7822282, 339 tests, pushed.**
  Auditado contra el repo real: (A) EjecutorSubprocesoReal con encoding="utf-8"/
  errors="replace" + frontera blindada a None; preguntar() ya no deja escapar
  TypeError/UnicodeDecodeError (ambos con test fail-first que reproduce el fallo
  real de Windows, incl. el byte 0x8d); runner con las llamadas IA envueltas y
  contador fallos_ia_inesperados. (B) GET /login/confirmar YA NO CONSUME (página
  con botón; el POST consume; decisión sin-CSRF documentada en código) + test
  del caso real: 5 GETs repetidos no gastan el token, el POST sí. (A6) el
  servidor real ABORTA con mensaje accionable si ONGS_AI_ENV=test. DEMO.md paso
  1 incluye ya ONGS_AI_ENV= y PYTHONUTF8=1 con su porqué. diagnostico_demo.py
  retirado. Nota de la sesión: investigacion/demo_real_guion.md dejado fuera del
  commit a propósito (correcto — investigacion/ no viaja).
  **La saga completa de los 400 queda cerrada** (nº1: ONGS_AI_ENV=test; nº2:
  ídem, reincidente; el de fechas era latente y cayó en el 021; el de prefetch
  era teórico y ahora es estructuralmente imposible). Detalle → histórico.
  **SIGUIENTE: PROMPT-023 (ya en cola, ORDEN 1º) — honestidad de la ingesta
  (hallazgo Aniridia/CCOO-Canarias del operador).**
- **2026-07-22 — PRIMER VEREDICTO DE PRODUCTO DEL OPERADOR (la demo YA SE USA):
  hallazgo real confirmado contra la BDNS primaria (numConv=920435): ámbito
  NUTS1 mal mapeado a NACIONAL + convocatoria con abierto=false listada +
  concesión directa nominativa (CCOO) ofrecida como oportunidad. → PROMPT-023.**

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-027 — F-proactivo.1: historial por NIF + convocatorias esperadas (implementa ADR-007) · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda,
elige la opción más conservadora/reversible y DOCUMENTA la decisión; lo
literal del prompt y anota lo excluido; jamás inventes datos ni
mediciones. Reglas de oro de CLAUDE.md por encima de todo. Antes de tocar
un fichero grande, Grep al símbolo y lee el rango. La pizarra
(engineering/06_*) la mantiene SOLO el arquitecto: no cierres items, no te
declares APROBADO — incluye en tu commit los cambios de engineering/06_*
del working tree tal cual.

TAREA: implementar engineering/ADR-007-recurrentes-esperadas.md (LÉELO
ENTERO ANTES: es la spec; este prompt fija calibraciones y orden). Los
defaults del §8 están ACEPTADOS por el operador: historial 5 años · 1
edición basta (confianza BAJA etiquetada) · aviso de ventana próxima SOLO
panel (aquí solo se materializa el dato; la vista es F-proactivo.2) ·
NO_APARECIDA a los 2 meses de cerrar la ventana · nominativas
accionable=False · re-derivación tras cada pasada de ingesta.

A. `src/ongs_ai/proactivo/` (ADR-007 §3.1-§3.3): modelo.py
   (HistorialConcesion, ConvocatoriaEsperada, EstadoEsperada, Confianza —
   dataclasses frozen, dinero en céntimos int), puertos.py (2 repos
   Protocol runtime_checkable; TODA lectura/escritura exige entidad_id),
   derivacion.py (DETERMINISTA, sin LLM):
A1. Fingerprint de serie — CALIBRACIÓN DEL ARQUITECTO (auditoría del ADR,
   difiere del §3.5 en un punto): se construye con organo nivel1 + nivel2
   + título normalizado sin tokens de año/edición; nivel3 (consejería/
   dirección general) QUEDA FUERA del fingerprint porque se renombra entre
   legislaturas (el histórico real de Aniridia lo evidencia) y produciría
   misses evitables. nivel3 se conserva como dato informativo en el
   modelo. Documenta esta decisión en derivacion.py citando ADR-007 y esta
   calibración. Degradación intacta: si no agrupa → MISS, jamás esperada
   falsa.
A2. Ventana desde las APERTURAS de las ediciones previas (§3.5): el
   servicio consulta el detalle de cada convocatoria histórica ya conocido
   por bdns.py; si falta apertura → mes de fechaConcesion como proxy
   MARCADO (baja confianza). Confianza ALTA/MEDIA/BAJA y ventana [min,max]
   exactamente como §3.5. anio_esperado desde fecha_referencia INYECTADA.
B. `adapters/ingesta/bdns_concesiones.py` (§3.4): FuenteConcesionesBDNS
   sobre el TransporteHTTP existente; buscar_por_nif(nif, fecha_desde,
   fecha_hasta) con nifCif + fechaDesde/fechaHasta (dd/mm/yyyy, VERIFICADO
   en §2.3); paginación como FuenteBDNS; mapeo §3.2 con contadores de
   descartados/ausentes; fallo de transporte degrada limpio. Fixtures
   SINTÉTICAS con la forma real de §2.1 — JAMÁS el histórico real de
   investigacion/ ni NIFs de asociaciones reales en tests.
C. Persistencia: ambos almacenes ganan los 2 repos (CREATE TABLE IF NOT
   EXISTS idempotente, datos_json como el resto); tests de contrato
   parametrizados memoria+SQLite; test ANTI-FUGA cross-tenant AMPLIADO a
   historial y esperadas (entidad A jamás lee de B); anti-hardcoding
   vigila también src/ongs_ai/proactivo/.
D. `servicios/recurrentes.py` (§3.4/§3.6/§3.8): orquesta captura →
   persistencia historial (dedupe por cod_concesion) → derivación →
   upsert de esperadas por (entidad_id, serie_fingerprint, anio_esperado);
   enlace tras ingesta: compara lo recién ingerido contra las esperadas
   ESPERADA por fingerprint → PUBLICADA_ENLAZADA con
   convocatoria_id_enlazada (y JAMÁS crea Match — el flujo normal de
   ADR-004 decide); NO_APARECIDA cuando fecha_referencia > fin de ventana
   + 2 meses. El aviso de propuesta existente, cuando la convocatoria del
   Match esté enlazada a una esperada de esa entidad, gana UNA línea de
   contexto ("la ayuda que recibiste en <año> ya está abierta") — no se
   crea canal nuevo ni aviso duplicado; NotificadorStub verifica que la
   ventana estimada NO dispara email.
E. Enganche a la pasada (default 6 aceptado): al final de la orquestación
   de servicios/pasada_ingesta.py, para cada entidad captada se ejecuta
   enlace + re-derivación con degradación limpia y contadores en el
   resumen (esperadas_enlazadas, esperadas_no_aparecidas). El botón del
   dashboard hereda esto sin tocarlo.
F. `scripts/derivar_recurrentes.py`: CLI fino sobre orquestación testeada
   (patrón preparar_demo): por defecto recorre las entidades captadas con
   NIF real (consulta nifCif últimos 5 años, puebla, deriva, imprime
   resumen: capturadas/descartadas/series/esperadas por confianza).
   Flag --nif-prueba <NIF>: consulta y deriva EN MEMORIA sin persistir
   (smoke sin contaminar la base). NO corre en CI.

G. `python -m pytest -q` VERDE con el nº REAL de tests. NO toques
   contrato congelado, máquina de estados de Match, guardarraíl,
   scoring ni vistas web (la vista del panel es F-proactivo.2).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (JAMÁS investigacion/ ni NIFs reales en
fixtures), git push. Tras el commit, DOS verificaciones reales pegadas:
(1) `python scripts/derivar_recurrentes.py --nif-prueba P0704500H`
(NIF público del ayuntamiento usado en la verificación del ADR-007 §2.3,
76 concesiones) — smoke del pipeline completo en memoria; (2) la pasada
sobre la entidad demo (NIF ficticio) — debe degradar limpio con 0
concesiones sin romper nada.
```


### Bandeja del OPERADOR

- **Pegar PROMPT-027 (F-proactivo.1, Sonnet) — COPIA la versión ACTUAL del
  06.** Al cerrar y auditar: F-proactivo.2 (la vista del panel con historial +
  esperadas "pendiente de publicar" y su ventana estimada — lo que pediste).
- Commit de docs cuando quieras:
  `git add engineering/ && git commit -m "Pizarra (docs)" && git push`
- Decisión pendiente (sin prisa): teléfono público de ABAIMAR en
  scripts/preparar_demo.py. ¿Lo dejamos o placeholder?
- En espera: retirar demo-conv-1/2/3, entidad piloto (para el historial real
  necesitaremos su NIF verdadero al captarla), SMTP real, programación diaria,
  censo FEDER.

### Backlog

- **F-consola.3 (tras ADR-007, intercambiable en orden si el operador lo pide):
  filtros + acciones web.** (a) Filtros en TODAS las pantallas de la consola
  (dashboard, entidades, cruce, mapa — convocatorias ya los tiene): texto,
  ámbito/CCAA, estado, score mínimo en cruce; GET puro, sin JS nuevo. (b)
  Botones de acción del operador desde la web: "Actualizar convocatorias"
  (relanza la pasada de ingesta con la batería del 024) y "Recalcular
  revisiones" (matching/propuestas) SIN terminal — diseño conservador:
  ejecución en hilo de fondo con candado anti-doble-pasada, estado visible
  (en curso / último resumen / errores degradados), solo rol operador,
  localhost. Redactado: YA EN COLA como PROMPT-026.

- **ADR-007 (Opus) — SIGUIENTE tras cerrar PROMPT-024: vigilancia de
  recurrentes + historial por NIF + convocatorias esperadas.** Nueva fuente
  /concesiones/busqueda de la BDNS (descubrir el parámetro real de filtro por
  beneficiario/NIF — `descripcionBeneficiario` NO filtra, verificado):
  historial de subvenciones de una entidad (el PDF de Aniridia, automatizado).
  REQUISITOS DEL OPERADOR (2026-07-22, literales): derivar "convocatorias
  esperadas" de ediciones anuales recurrentes; mostrarlas con estado tipo
  "PENDIENTE DE PUBLICAR" aunque la edición del año no exista aún; estimar la
  FECHA en torno a la cual debería salir a partir de las fechas de ediciones de
  años anteriores (estimación honesta: rango/mes, jamás certeza); avisar al
  publicarse la edición real y enlazarla con la esperada. Toca dominio
  (probable ConvocatoriaEsperada/HistorialConcesion, relación con Match) →
  ADR obligatorio. El prompt lo redacta el arquitecto al llegarle el turno.
- F5 preparación asistida (alcance AMPLIADO por el operador: checklist documental con
  gap + borradores de todos los entregables; probable ADR DocumentoRequerido).
- ADR-003: redundancia de ámbito en el contrato (`ambito_geografico`+region/provincia
  vs `ambito_territorial_requerido` sin consumir) — limpiar.
- Enriquecimiento de personas visibles: solo de las asociaciones a contactar (tras
  elegir candidatas; la extracción FEDER completa ya está en cola como PROMPT-012).
- Adapters privados de ingesta (FEDER, la Caixa, ONCE) + agregador SolucionesONG.
- Endurecer test anti-hardcoding. · Filtro `tipoBeneficiario` de BDNS sin ejercer.
- CSRF en los POST de login/logout de la consola (riesgo mínimo, loopback-only).
- Rendimiento del dashboard de consola con 511 prospectos (precálculo/caché) —
  medir primero en la demo real.
- Verificación adversarial pendiente de R1 (22 claims, 0 refutadas) — opcional.
- Modelo de negocio (entidades con pocos recursos) — conversación de producto.

- `engineering/12_SISTEMA_VISUAL.md` (paleta/tokens de ONGs-AI) cuando el diseño del
  prototipo se dé por bueno; ajustar entonces la vara del ux-reviewer.

### Recordatorios operativos

- Consola de Windows muestra acentos como � (cp1252): cosmético; `chcp 65001` lo
  arregla por sesión. El dato subyacente es UTF-8 correcto.
- ANTES de pegar un prompt: copialo del 06 ACTUAL, tras el ultimo aviso del
  arquitecto — dos prompts ya se ejecutaron en version vieja (015 y 016).

- Máquina Windows: SIEMPRE `python -m ...` (pytest, uvicorn — los .exe de Scripts no
  están en PATH); rutas `C:\dev\ongs-ai`. **Puerto 8000 OCUPADO por otro proyecto →
  ONGs-AI usa el 8001.** `set PYTHONPATH=src` antes de uvicorn sigue en DEMO.md
  como cinturón y tirantes (el paquete ya es instalable desde PROMPT-016).
- Mount sandbox↔host: ver regla del traspaso (git = verdad de la pizarra).
  AMPLIADO: re-stagear un fichero YA stageado sirve contenido VIEJO dentro del
  mismo turno (le pasó al arquitecto con la BD y con ficheros de código);
  workaround verificado: stagear con variante de mayúsculas en la ruta Windows
  (case-insensitive) → ruta local nueva sin caché.
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
- `investigacion/asociaciones*` JAMÁS a git (datos personales; gitignorado).
