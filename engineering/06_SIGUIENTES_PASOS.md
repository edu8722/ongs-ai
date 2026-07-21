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

- **2026-07-22 — PRIMER VEREDICTO DE PRODUCTO DEL OPERADOR (la demo YA SE USA):
  hallazgo REAL confirmado contra la fuente primaria.** El operador detectó que
  a la asociación de Aniridia (ámbito nacional) se le ofrece "PARTICIPACIÓN DE
  CCOO PROGRAMA DE SENSIBILIZACIÓN PRL EN FP CANARIA 2026" etiquetada como
  NACIONAL. Auditado contra la API real de la BDNS (numConv=920435): el fallo
  es TRIPLE. (1) La BDNS da regiones=`ES7 - CANARIAS` (NUTS1, 1 dígito): nuestro
  mapeo solo contempla ES/NUTS2/NUTS3 y su default para lo no reconocido es
  NACIONAL — default expansivo (sobre-promete), inconsistente con el criterio
  conservador que sí usamos para tipo_fuente; el ámbito erróneo se replica
  además en requisitos.ambito_territorial_requerido (misma raíz, bdns.py:156),
  y por eso "cumple" para una entidad nacional. (2) La convocatoria real lleva
  `abierto: false` — no está abierta y aun así está VERIFICADA y listada como
  oportunidad. (3) Es "Concesión directa - instrumental" NOMINATIVA a CCOO:
  nadie más puede pedirla; jamás debió entrar como oportunidad. La propia fila
  contiene la contradicción visible (fuente publica_autonomica + ámbito
  nacional). ARREGLO: PROMPT-023 (en cola, DESPUÉS del 022). El caso 920435 se
  graba como fixture real de regresión.
- **2026-07-22 — SEGUNDO 400 RESUELTO CON EVIDENCIA (diagnostico_demo.py en las
  dos consolas):** la consola del servidor tenía `ONGS_AI_ENV='test'` fantasma →
  uvicorn arrancaba con AlmacenMemoria vacío → todo enlace 400 SIEMPRE. La base
  real del repo está perfecta (53 convocatorias/37 verificadas, 511 prospectos,
  token vigente sin usar). Arreglo del operador: `set ONGS_AI_ENV=` y relanzar.
  Queda pendiente comprobar si la variable está grabada permanente en Windows
  (setx) — el operador lo verifica en consola nueva. Teorías intermedias del
  arquitecto (prefetch, dos almacenes) RETIRADAS: la segunda fue una lectura
  obsoleta del fichero staged por el mount (la lección "el mount miente" aplica
  también a las bases de datos, no solo a la pizarra). BLINDAJE AÑADIDO A
  PROMPT-022 (A6): el arranque de servidor real ABORTA con mensaje claro si
  ONGS_AI_ENV=test — esta clase de fallo no debe poder repetirse.
- **2026-07-22 — DEMO paso 2, incidencia UTF-8 (PROMPT-022 A):** causa raíz en
  ia/claude_cli.py (text=True sin encoding en Windows → cp1252 revienta →
  stdout=None → TypeError escapa al dominio y tumba la pasada). Mitigado con
  PYTHONUTF8=1; el fix de código va en PROMPT-022 A. Detalle → histórico al
  cierre del 022.
- **2026-07-21 — PROMPT-021 CERRADO: APROBADO, HECHO 7f3e73f, 331 tests, pushed.
  LA HERRAMIENTA DE CAPTACIÓN EXISTE CON EL DISEÑO DEL PROTOTIPO.** Auditado contra
  el repo real: (A) consola.css extraído del prototipo, servido SOLO bajo
  /consola/estaticos; 5 vistas Jinja (resumen con métricas y "oportunidades más
  afines", convocatorias con filtros GET, entidades unificada captadas+candidatas,
  cruce con desglose motivo a motivo y rango de importe, mapa Leaflet por centroide
  de CCAA con degradación limpia sin red) — TODAS leyendo de los servicios ya
  auditados, nada hardcodeado, loopback+clave verificados por test. (B)
  scripts/preparar_demo.py con orquestación testeada (9 tests con stubs:
  idempotencia, ingesta condicional, degradación); los dos scripts desechables del
  arquitecto RETIRADOS. docs/DEMO.md = camino único de 4 pasos. (C) el 400: la
  sesión reprodujo el camino literal (funcionaba con invocación correcta) y encontró
  el bug REAL de la clase sospechada — comparación de expira_en como texto ISO rompe
  con offset no-UTC (+02:00 Madrid) o datetime naive; evidencia con test en rojo
  pre-fix; normalizado a UTC-aware en la frontera de AMBOS almacenes + test de
  integración fichero-SQLite del camino siembra→HTTP→confirmar→panel→reuso-400.
  Verificado por la sesión de punta a punta contra uvicorn real.
  **Observaciones del arquitecto (no bloqueantes):** (1) el perfil demo lleva el
  teléfono público de ABAIMAR ahora COMMITEADO (repo privado, dato público de su
  web, marcado SUPUESTO el resto) — decisión del operador si sustituirlo por
  placeholder; (2) los POST de login/logout de consola van sin token CSRF —
  riesgo mínimo (loopback + solo cierra sesión), anotado en backlog; (3) el
  dashboard evalúa perfiles×convocatorias en cada carga: con los 511 prospectos
  importados puede tardar unos segundos — es cómputo honesto, no un fallo; si
  molesta, F-consola.2+ lo precalcula.
  **SIGUIENTE PASO: el operador ejecuta docs/DEMO.md y da su veredicto.** Ese
  feedback decide F-consola.2 (conversión Prospecto→Entidad) / F-consola.3 (pulido
  de vistas) / F5. SIN PROMPTS EN COLA.
- **2026-07-22 — FEEDBACK DURO DEL OPERADOR (asumido, ya respondido con el 021):**
  tres demos decepcionantes; causas reconocidas: consola sin el diseño esperado,
  scripts de demo del arquitecto sin tests (vector del 400), instrucciones de demo
  dispersas. El replanteamiento completo se ejecutó como PROMPT-021 (ver arriba).
- **2026-07-21 — PROMPT-020 / F-consola.1 CERRADO: APROBADO, HECHO f870150, 308
  tests.** Consola funcional + prospeccion/ + scoring determinista con anclaje.
  Detalle → histórico.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-022 — Fix UTF-8 del CLI de IA + enlace mágico inmune a prefetch (confirmar por POST) · MODELO: Sonnet · ORDEN: 1º (nada en paralelo) · URGENTE

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda
de implementación, elige la opción más conservadora/reversible y DOCUMENTA
la decisión en el resumen final; ante ambigüedad de alcance, implementa lo
literal del prompt y anota lo que dejaste fuera; jamás inventes datos ni
mediciones. Reglas de oro de CLAUDE.md por encima de todo. Antes de tocar
un fichero grande, Grep al símbolo y lee el rango. La pizarra
(engineering/06_*) la mantiene SOLO el arquitecto: no cierres items, no te
declares APROBADO — limítate a incluir en tu commit los cambios de
engineering/06_* que ya estén en el working tree, tal cual estén.

CONTEXTO (fallo real del operador, Windows, Python 3.14): al ejecutar
scripts/preparar_demo.py, el hilo lector de subprocess murió con
UnicodeDecodeError ('charmap'/cp1252, byte 0x8d) al leer la salida del CLI
de Claude, dejando stdout=None; json.loads(None) lanzó TypeError, que NO
está en el except de ClienteClaudeCLI.preguntar, la excepción escapó y
TUMBÓ LA PASADA DE INGESTA COMPLETA (el resumen imprimió: "Fallo la pasada
de ingesta (the JSON object must be str, bytes or bytearray, not
NoneType)"). Doble violación del contrato del cliente (PROMPT-018 A1):
decodificación dependiente del locale y excepción hacia el dominio.

A1. `src/ongs_ai/ia/claude_cli.py` — EjecutorSubprocesoReal: añade
   `encoding="utf-8", errors="replace"` al subprocess.run (la salida del
   CLI es UTF-8; jamás depender del locale de la máquina). Además blinda
   la frontera: si stdout/stderr llegan como None (hilo lector muerto u
   otro fallo), ResultadoProceso los normaliza a "" — su tipo declarado
   ya es str y hoy se viola.
A2. ClienteClaudeCLI.preguntar: que NINGUNA excepción pueda escapar por
   datos raros — añade TypeError al except del json.loads (o valida
   isinstance(str) antes) y trata stdout vacío como fallo con contador,
   como el resto. EVIDENCIA fail-first: test con ejecutor stub que
   devuelve ResultadoProceso(0, None, None) — hoy debe reproducir el
   TypeError escapando — y test de ejecutor que lanza UnicodeDecodeError:
   ambos deben acabar en degradación limpia (None + fallos+1), rojo antes
   del fix, verde después.
A3. Cinturón y tirantes en el runner (`scripts/ejecutar_ingesta.py`): las
   llamadas a IA (extracción y explicación) van envueltas de forma que un
   fallo inesperado del cliente NUNCA tumbe la pasada — degradación con
   contador en el resumen (convocatoria sigue sin enriquecer). Test de la
   función de orquestación con un cliente stub que lanza.
A4. Barrido: Grep de subprocess/text=True en todo src/ y scripts/ — si hay
   otros call sites sin encoding explícito, mismo tratamiento.
A5. docs/DEMO.md paso 1: añade `set PYTHONUTF8=1` a las variables (con una
   línea de porqué: salida UTF-8 del CLI y acentos en consola Windows).
A6. GUARDARRAÍL DE ARRANQUE (fallo real del operador, dos veces): en
   `web/app.py`, `_app_produccion` ABORTA con mensaje claro y accionable
   (SystemExit o RuntimeError: "ONGS_AI_ENV=test detectado: el servidor
   real usaría un almacén de MEMORIA vacío y todos los enlaces darían
   400. Ejecuta `set ONGS_AI_ENV=` y relanza") si ONGS_AI_ENV=test está
   en el entorno. Un servidor de producción con almacén de memoria es
   siempre un error del operador, jamás una intención. Test del guard
   (monkeypatch del entorno, sin arrancar uvicorn). docs/DEMO.md paso 1
   añade `set ONGS_AI_ENV=` a las variables, con el porqué en una línea.


B. ENLACE MÁGICO INMUNE A PREFETCH/ESCÁNERES (evidencia del operador: sus
   tokens aparecen CONSUMIDOS en la base mientras su pestaña ve "enlace no
   válido" — una petición especulativa del navegador gasta el GET de un
   solo uso antes que la navegación real; con SMTP real los escáneres de
   correo harán lo mismo). Cambio de contrato de la ruta, NO del almacén:
B1. GET /login/confirmar?token=... DEJA DE CONSUMIR. Ahora valida SOLO
   presencia del parámetro y devuelve 200 con una página mínima (plantilla
   del panel existente): "Entrar en tu panel" + <form method="post"
   action="/login/confirmar"> con el token en <input type="hidden">. Sin
   tocar la base en el GET (los prefetchers solo hacen GET y no envían
   formularios). No confirmes en el GET ni siquiera si el token es
   inválido: la página es la misma (anti-enumeración, como el /login).
B2. POST /login/confirmar (token en el body del form): aquí vive TODO lo
   que hoy hace el GET — consumir_token atómico, crear sesión, 303 a
   /panel; token inválido/caducado/usado → el 400 actual. El POST viene de
   nuestra propia página del B1 con la sesión de formulario aún inexistente:
   NO exijas token CSRF de sesión aquí (no hay sesión todavía; el token de
   un solo uso ES la prueba de posesión — documenta esta decisión en el
   código).
B3. Tests: actualiza el test de integración de PROMPT-021 (ahora GET →
   200 con formulario; POST → 303/panel; segundo POST → 400) y AÑADE el
   test que reproduce el fallo real del operador: GET repetido N veces NO
   consume (el token sigue utilizable), luego POST único sí. El resto de
   tests de auth que asuman el GET-consume se actualizan con el mismo
   criterio.
B4. Los enlaces impresos/enviados NO cambian de forma (siguen siendo el
   mismo GET con token) — preparar_demo y el email real no se tocan salvo
   textos si procede. docs/DEMO.md paso 4: una línea explicando que el
   enlace abre una página con botón "Entrar".

C0. Retira `scripts/diagnostico_demo.py` (herramienta temporal de solo
   lectura del arquitecto, sin tests — no debe quedar en el repo).

C. `python -m pytest -q` VERDE con el nº REAL de tests. NO toques contrato,
   máquina de estados ni las vistas de consola.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (JAMÁS los CSV/xlsx de investigacion/), git push.
```


#### PROMPT-023 — Honestidad de la ingesta BDNS: ámbito NUTS1, abierto=false y concesiones directas · MODELO: Sonnet · ORDEN: 2º (DESPUÉS de cerrar PROMPT-022, nada en paralelo)

```
POLÍTICA DE DECISIÓN (evita preguntar salvo bloqueo real): ante una duda
de implementación, elige la opción más conservadora/reversible y DOCUMENTA
la decisión en el resumen final; ante ambigüedad de alcance, implementa lo
literal del prompt y anota lo que dejaste fuera; jamás inventes datos ni
mediciones. Reglas de oro de CLAUDE.md por encima de todo. Antes de tocar
un fichero grande, Grep al símbolo y lee el rango. La pizarra
(engineering/06_*) la mantiene SOLO el arquitecto: no cierres items, no te
declares APROBADO — limítate a incluir en tu commit los cambios de
engineering/06_* que ya estén en el working tree, tal cual estén.

CONTEXTO (hallazgo real del operador en la consola, verificado por el
arquitecto contra la API primaria, numConv=920435): la convocatoria
"PARTICIPACIÓN DE CCOO ... FP CANARIA 2026" está en la base como NACIONAL
y VERIFICADA cuando la BDNS real dice regiones=`ES7 - CANARIAS` (NUTS1),
`abierto: false` y tipo "Concesión directa - instrumental" (nominativa a
CCOO). Triple fallo de honestidad de datos en la ingesta. Regla de oro:
jamás sobre-prometer.

A. ÁMBITO — arregla `_ambito_y_region_desde_regiones` (adapters/ingesta/
   bdns.py) con fixture REAL grabada: descarga tú el detalle de
   numConv=920435 (una sola petición manual, fuera de tests) y grábalo en
   tests/fixtures/ingesta/bdns_detalle_920435.json. Fail-first: test con
   esa fixture que hoy devuelve NACIONAL y debe devolver AUTONOMICO/
   "CANARIAS". Reglas nuevas, deterministas y documentadas:
A1. Código NUTS1 (1 dígito tras ES): si el nombre tras " - " coincide
   (normalizado) con una CCAA de una tabla CERRADA de nombres de CCAA →
   AUTONOMICO con esa region. La tabla vive en el ADAPTER (no en dominio)
   y cubre los 19 nombres oficiales (17 CCAA + Ceuta y Melilla) más los
   alias ya usados en consola (_soporte.CENTROIDE_CCAA usa las mismas
   claves normalizadas — NO dupliques el normalizador: usa
   normalizar_texto_comparacion del dominio).
A2. TOPE POR ÓRGANO (invariante nuevo, la parte que mata la CLASE de
   bug): el ámbito derivado JAMÁS puede ser más amplio que el órgano
   convocante — organo.nivel1 AUTONOMICA → como mucho AUTONOMICO (si las
   regiones no dieron nombre, region = organo.nivel2 si existe); LOCAL →
   como mucho PROVINCIAL. Con ESTADO se mantiene lo derivado. Aplica el
   tope SIEMPRE tras el parseo de regiones. Tests de las combinaciones.
A3. El replicado en requisitos.ambito_territorial_requerido (bdns.py:156)
   hereda el valor ya corregido — verifica con test que la contradicción
   "fuente autonómica + ámbito nacional" ya no puede producirse desde la
   ingesta.
B. ABIERTO Y CONCESIONES DIRECTAS — en el detalle real de la BDNS
   descubre los nombres EXACTOS de los campos (en la fixture de A los
   verás: `abierto` y el campo del tipo/procedimiento de concesión;
   documenta ambos en el docstring del módulo):
B1. `abierto: false` en el momento de la ingesta → la convocatoria NO se
   ingesta como oportunidad: se persiste como DESCARTADA_POR_DOMINIO con
   motivo "no abierta en origen" (así el dedupe evita re-procesarla cada
   pasada) y cuenta en el resumen (nueva métrica descartadas_no_abiertas).
B2. Tipo de convocatoria "Concesión directa" (instrumental/nominativa) →
   ídem: DESCARTADA_POR_DOMINIO con motivo "concesión directa (no
   concurrencia)", métrica descartadas_concesion_directa. Si el campo no
   viene en el detalle, no se descarta por este criterio (conservador con
   el dato ausente, jamás adivinar por el título).
C. LIMPIEZA DE LO YA INGERIDO — `scripts/reevaluar_ingesta.py` (misma
   estructura que ejecutar_ingesta: orquestación pura testeada con stubs +
   main con red real): recorre las convocatorias bdns-* existentes,
   re-consulta su detalle real, re-aplica el mapeo y filtros nuevos y (a)
   corrige ámbito/region/requisitos si cambiaron, (b) marca
   DESCARTADA_POR_DOMINIO las no abiertas/concesiones directas. Flag
   --simular que imprime el plan SIN escribir (default: simular; escribir
   exige --aplicar). Imprime resumen de cambios. El operador lo ejecuta
   tras el commit y pega el resultado.
D. HONESTIDAD VISUAL EN EL CRUCE — cuando una convocatoria no tiene NINGÚN
   requisito estructurado más allá del ámbito (forma jurídica, antigüedad
   y requisitos formales todos vacíos), la vista de cruce muestra un badge
   "requisitos sin datos — revisar bases" en vez de dejar que el 70% de
   cobertura vacíamente satisfecha parezca certeza. SOLO presentación
   (plantilla + dato derivado en la ruta): NO toques el modelo de score ni
   ADR-006.

E. `python -m pytest -q` VERDE con el nº REAL de tests. NO toques
   contrato (los campos de Convocatoria no cambian), ni máquina de
   estados, ni el scoring.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (JAMÁS los CSV/xlsx de investigacion/), git push.
Tras el commit: ejecuta scripts/reevaluar_ingesta.py --simular contra la
base real y pega el plan impreso (el operador decidirá aplicar).
```

### Bandeja del OPERADOR

- **AHORA — en la consola del servidor:** `set ONGS_AI_ENV=` y relanza
  `python -m uvicorn ongs_ai.web.app:app --reload --port 8001`. Abre el último
  enlace impreso (ventana normal) → panel ABAIMAR; `/consola` con tu clave.
  **Y comprueba en una consola NUEVA:** `echo %ONGS_AI_ENV%` — si sale `test`,
  está grabada permanente en Windows: Configuración → "Editar las variables de
  entorno" → eliminar ONGS_AI_ENV (si sale vacío, no hay nada más que hacer).
  Después: tu VEREDICTO de las dos pantallas — es lo que decide el siguiente
  prompt.
- **Pegar PROMPT-022 AMPLIADO (Sonnet) — COPIA la versión ACTUAL del 06** (fix
  UTF-8 del CLI + enlace confirmable por POST + guardarraíl anti-ENV=test).
  scripts/diagnostico_demo.py se retira en ese mismo commit (era temporal).
- **Después, PROMPT-023 (Sonnet), EN SERIE:** honestidad de la ingesta — tu
  hallazgo de Aniridia/CCOO-Canarias (ámbito NUTS1 mal mapeado, convocatoria
  cerrada en origen y concesión directa nominativa listada como oportunidad).
  Incluye script de limpieza de lo ya ingerido (--simular primero).
- Sigue usando la consola y apunta TODO lo raro que veas — este hallazgo tuyo
  ha destapado una clase entera de bugs. Tu lista = la spec de F-consola.3.
- Nota: la primera carga de /consola con los 511 prospectos puede tardar unos
  segundos (evalúa todos los cruces en vivo). No es un cuelgue.
- Commit de docs cuando quieras:
  `git add engineering/ && git commit -m "Pizarra (docs)" && git push`
- Decisión pendiente (sin prisa): el teléfono público de ABAIMAR está commiteado
  en scripts/preparar_demo.py (repo privado). ¿Lo dejamos o placeholder?
- En espera (tras tu veredicto de la demo): entidad piloto, SMTP real +
  smoke_email, programación diaria de la ingesta, censo completo FEDER.

### Backlog

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
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
- `investigacion/asociaciones*` JAMÁS a git (datos personales; gitignorado).
