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

#### PROMPT-024b — Las vistas de consola ignoran las descartadas (rendimiento + señal) · MODELO: Sonnet · ORDEN: 1º, PEQUEÑO — pegar ANTES del ADR si vas a usar la consola

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda,
elige la opción más conservadora/reversible y DOCUMENTA la decisión; lo
literal del prompt y anota lo excluido; jamás inventes datos. Reglas de
oro de CLAUDE.md por encima de todo. Grep antes de leer ficheros grandes.
La pizarra (engineering/06_*) la mantiene SOLO el arquitecto: no cierres
items, no te declares APROBADO — incluye en tu commit los cambios de
engineering/06_* del working tree tal cual.

CONTEXTO: tras PROMPT-024 la base tiene ~1.550 convocatorias, la mayoría
DESCARTADA_POR_DOMINIO (cerradas en origen / concesión directa,
persistidas a propósito para el dedupe). Las vistas de consola evalúan
TODAS contra ~512 perfiles en cada carga (cruce, dashboard) → lentitud
severa y listados enterrados en descartadas que por definición no son
oportunidades.

A1. Nueva función en el módulo de soporte de consola (o servicio si
   encaja mejor): convocatorias_utiles(almacen) = todas MENOS las
   DESCARTADA_POR_DOMINIO. El dashboard (métricas, importe agregado,
   "oportunidades más afines") y /consola/cruce evalúan SOLO esas.
   El mapa no cambia (va de prospectos).
A2. /consola/convocatorias: filtro de estado nuevo con defecto
   "no descartadas"; opción explícita "ver también descartadas" (con su
   motivo de exclusiones visible — el dato ya existe) para auditar por
   qué algo se descartó. La cuenta del dashboard dice cuántas descartadas
   hay ("N descartadas ocultas — verlas en Convocatorias").
A3. Tests: cruce y dashboard con una base que mezcla verificadas y
   descartadas — las descartadas NO aparecen ni se evalúan (asértalo con
   un almacén stub que cuente llamadas o con el contenido renderizado);
   filtro de convocatorias en sus tres variantes.
A4. NO toques el scoring, el matching de fondo (detectar_y_proponer ya
   exige VERIFICADA), el contrato ni la ingesta. Es un cambio de LECTURA
   en las vistas.

C. python -m pytest -q VERDE con el nº REAL de tests.

Ritual de cierre: commit ÚNICO con nº real de tests, git status antes del
add (JAMÁS investigacion/), push. Tras el commit: abre /consola y
/consola/cruce con la base real (~1.550) y reporta el tiempo de carga
percibido antes/después.
```

#### PROMPT-025 — ADR-007: vigilancia de recurrentes, historial por NIF y convocatorias esperadas · MODELO: Opus · ORDEN: 2º (SOLO tras cerrar PROMPT-024; nada en paralelo)

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda,
elige la opción más conservadora/reversible y DOCUMENTA la decisión; ante
ambigüedad de alcance, lo literal del prompt y anota lo excluido; jamás
inventes datos ni mediciones. Reglas de oro de CLAUDE.md por encima de
todo. La pizarra (engineering/06_*) la mantiene SOLO el arquitecto: no
cierres items, no te declares APROBADO — incluye en tu commit los cambios
de engineering/06_* que ya estén en el working tree, tal cual.

TAREA: SOLO DISEÑO — escribe engineering/ADR-007-recurrentes-esperadas.md.
CERO código de producción. Este ADR define el corazón proactivo del
producto, pedido por el operador con evidencia real (histórico de
concesiones de Aniridia 2022-2024: 15 ayudas, la mayoría ediciones
anuales recurrentes — IRPF 0,7%% estatal y CAM, mantenimiento de
servicios CAM, ayuda mutua Sanidad CAM, asociacionismo municipal,
diputaciones).

REQUISITOS DEL OPERADOR (literales, 2026-07-22): "en base al año pasado
debería informar de a qué convocatorias se podrían intentar presentar y
que tengan un estado de pendiente de publicar o algo así y en base a las
fechas de otros años marque en torno a qué fecha debería salir la
convocatoria".

El ADR debe decidir, como mínimo:
1. FUENTE HISTORIAL: /concesiones/busqueda de la BDNS. VERIFICA contra la
   API real (peticiones manuales, documentadas en el ADR — mismo método
   que ADR-001..006) el parámetro REAL de filtro por beneficiario/NIF:
   el arquitecto ya comprobó que `descripcionBeneficiario` NO filtra
   (devuelve los 28M de registros). Si no existe filtro server-side
   utilizable, decide la alternativa (p. ej. búsqueda por convocatoria
   conocida + filtrado cliente) y su coste.
2. MODELO DE DOMINIO: HistorialConcesion (ayuda pasada de una entidad) y
   ConvocatoriaEsperada (edición anual prevista). ¿Viven dentro del
   contrato congelado (ampliación vía este ADR) o en paquete aparte como
   Prospecto? ¿Esperada es global o por entidad? ¿Relación con Match?
   (propuesta conservadora a evaluar: una esperada NUNCA crea Match — al
   publicarse la edición real se enlaza esperada→convocatoria y el
   matching normal hace el resto; la esperada tiene ciclo propio:
   ESPERADA → PUBLICADA_ENLAZADA | NO_APARECIDA).
3. ESTIMACIÓN DE FECHA honesta: derivada de las fechas de ediciones
   previas; SIEMPRE como rango/mes ("suele publicarse en mayo-junio"),
   jamás fecha exacta; ¿cuántas ediciones previas exigen derivar una
   esperada (1, 2)? ¿cómo se degrada con datos irregulares? Mismo
   criterio de honestidad que el importe techo-teórico de ADR-006.
4. AVISOS: al publicarse la edición real de una esperada (la ingesta del
   024 la traerá), enlazar y avisar por los canales existentes (email +
   panel). ¿Aviso también de "se acerca la ventana estimada"? Decide.
5. TENANCY Y PII: el historial se consulta por NIF de la entidad (dato
   del tenant); las concesiones son públicas en la BDNS. Reglas de
   aislamiento por tenant para historial y esperadas por entidad.
6. QUÉ QUEDA FUERA (anti-sobre-ingeniería): sin predicciones de importe,
   sin probabilidad de concesión (rechazado ya en ADR-006), sin
   scraping de bases; solo BDNS estructurada en esta fase.

Método: lee ADR-001/002/005/006 y el contrato real en
src/ongs_ai/dominio/ antes de decidir; cada decisión con alternativas
consideradas y por qué NO. Caso de contraste obligatorio: el histórico
real de Aniridia (el operador lo tiene en investigacion/, NO lo copies a
git — referencia sus patrones: IRPF anual con ventana ~mayo-junio,
mantenimiento CAM otoño, asociacionismo octubre).

Cierre: python -m pytest -q VERDE (sin código nuevo, el nº real de tests
no cambia), commit ÚNICO "ADR-007: ... (N tests, sin código)", git status
antes del add, push. Preguntas no bloqueantes AGRUPADAS al final.
```

#### PROMPT-026 — F-consola.3: filtros en todas las pantallas + acciones desde la web · MODELO: Sonnet · ORDEN: 3º (tras cerrar el ADR-007; nada en paralelo)

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda,
elige la opción más conservadora/reversible y DOCUMENTA la decisión; ante
ambigüedad de alcance, lo literal del prompt y anota lo excluido; jamás
inventes datos ni mediciones. Reglas de oro de CLAUDE.md por encima de
todo. Antes de tocar un fichero grande, Grep al símbolo y lee el rango.
La pizarra (engineering/06_*) la mantiene SOLO el arquitecto: no cierres
items, no te declares APROBADO — incluye en tu commit los cambios de
engineering/06_* que ya estén en el working tree, tal cual.

TAREA (petición literal del operador): "en todas las pantallas debería
existir filtros y desde la propia web debería poderse invocar a
recalcular o reejecutar comandos para actualizar las convocatorias y
hacer la revisión de a qué convocatorias se puede presentar cada
asociación". Dos bloques:

A. FILTROS EN TODAS LAS VISTAS DE CONSOLA (GET puro, server-side, mismo
   patrón que /consola/convocatorias; SIN JavaScript nuevo):
A1. /consola/entidades: además del texto actual, filtro por CCAA y por
   tipo (captadas / candidatas / todas).
A2. /consola/cruce: filtro por estado del cruce (elegible / no evaluable /
   no elegible / todos), score mínimo (número entero 0-100) y texto sobre
   el objeto de la convocatoria.
A3. /consola/mapa: filtro por CCAA y texto sobre nombre.
A4. /consola (dashboard): las "oportunidades más afines" ganan filtro por
   CCAA del perfil. Formularios con method="get", valores actuales
   preservados en los inputs, y enlace "limpiar filtros" en cada vista.
A5. Tests HTTP por vista: con filtro que acierta, filtro que vacía (y
   mensaje de vacío correcto), y combinación de filtros.

B. ACCIONES DEL OPERADOR DESDE LA WEB (sin terminal):
B1. Prepara la reutilización: mueve la función de orquestación de la
   pasada de ingesta de scripts/ejecutar_ingesta.py a un módulo
   importable del paquete (p. ej. src/ongs_ai/servicios/pasada_ingesta.py)
   — MOVIMIENTO mecánico con sus tests detrás; el script queda como CLI
   fino que importa de ahí (mismo patrón que preparar_demo). Nada de
   duplicar lógica.
B2. Registro de ejecución en app.state (dataclass en memoria, v1 local
   monopuesto): estado (inactivo / en curso desde T / terminado en T con
   resumen / fallido con motivo degradado), y CANDADO: si hay una pasada
   en curso, un segundo disparo responde "ya hay una pasada en curso" sin
   lanzar nada (threading.Lock, no cola de trabajos — anti-sobre-
   ingeniería, documenta la decisión).
B3. POST /consola/acciones/actualizar-convocatorias: lanza EN HILO DE
   FONDO la pasada completa (batería del 024 + filtros del 023 + matching
   y propuestas, lo mismo que el CLI). POST
   /consola/acciones/recalcular-revisiones: solo la fase de matching/
   propuestas sobre lo ya ingerido (sin red). Ambas rutas con las MISMAS
   dependencias de consola (solo_loopback + operador_actual).
B4. UI en el dashboard: sección "Estado de la plataforma" con los dos
   botones, el estado actual y el resumen de la última ejecución
   (métricas del runner tal cual, incluidas descartadas del 023 y
   fallos IA). Mientras hay pasada en curso los botones se deshabilitan
   (atributo disabled según estado; el refresco es recargar la página —
   documenta que v1 no lleva polling).
B5. EJECUTOR INYECTABLE: las rutas reciben el ejecutor de pasadas vía
   app.state (factory por entorno) — en tests SIEMPRE un stub síncrono
   (sin hilos ni red ni CLI: el hilo real solo existe en producción).
   Tests: candado (segundo POST con pasada en curso), estado renderizado
   en el dashboard, acción de recalcular llama al stub correcto, y las
   rutas exigen loopback+operador (404/redirect como el resto).
B6. La ingesta desde la web usa la suscripción Claude del operador igual
   que el CLI (freno de plan intacto); si el CLI no está disponible en el
   entorno del servidor, degradación limpia ya existente — verifica que
   el resumen la refleja, no la ocultes.

C. python -m pytest -q VERDE con el nº REAL de tests. NO toques contrato,
   máquina de estados, scoring ni la ingesta en sí (solo la mueves).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (JAMÁS investigacion/), git push. Tras el
commit: arranca el servidor real, dispara "Actualizar convocatorias"
desde el navegador, espera el final y pega el estado/resumen que muestra
el dashboard — verificación humana del ciclo completo sin terminal.
```

### Bandeja del OPERADOR

- **Orden de pegado actualizado: 024b (pequeño, consola usable con la base
  grande) → 025/ADR-007 (OPUS, diseño) → 026/F-consola.3.** De uno en uno,
  copiando del 06 ACTUAL, esperando mi auditoría entre uno y otro.
- Aviso mientras no cierre 024b: /consola y /consola/cruce pueden tardar
  MUCHO con las ~1.550 convocatorias — no es un cuelgue; usa los filtros de
  /consola/convocatorias, que es la vista que mejor aguanta.
- Sigue apuntando lo raro que veas — tus hallazgos están dirigiendo la cola.
- Commit de docs cuando quieras:
  `git add engineering/ && git commit -m "Pizarra (docs)" && git push`
- Decisión pendiente (sin prisa): teléfono público de ABAIMAR en
  scripts/preparar_demo.py (repo privado). ¿Lo dejamos o placeholder?
- En espera: retirar demo-conv-1/2/3, entidad piloto, SMTP real,
  programación diaria, censo FEDER.

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
