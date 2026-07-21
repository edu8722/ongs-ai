# 06 HISTÓRICO — arqueología de ONGs-AI

> Reconstruido íntegro por el arquitecto el 2026-07-21 tras el 3er pisotón de pizarra
> (la sesión Opus retirada regresó este fichero a su versión del día 18 y el commit
> 838373a lo selló). Fuente: las entradas originales del arquitecto, conservadas en su
> sesión, y los diffs de git de las auditorías del día 19.

## Semana 2026-07-20/26

- **PROMPT-026 — F-consola.3: filtros en todas las vistas + acciones web**
  (Sonnet) — **HECHO 7fb9d05, APROBADO, 389 tests.** Petición literal del
  operador. Filtros GET server-side en entidades (tipo/CCAA), cruce
  (estado/score mínimo/texto), mapa (CCAA/texto) y dashboard (CCAA), con
  "limpiar filtros"; orquestación de pasada movida a
  servicios/pasada_ingesta.py (script como CLI fino); RegistroEjecucion con
  threading.Lock + lanzador de hilo y reloj inyectables (stub síncrono en CI),
  candado anti-doble-pasada testeado, POST /consola/acciones/* con
  solo_loopback+operador. Verificación en vivo: pasada completa de 13 min
  disparada desde el navegador contra la base real, resumen honesto en el
  dashboard y botones reactivados. Hallazgo operativo: uvicorn viejos en
  8000-8003.

- **PROMPT-025 — ADR-007: recurrentes esperadas** (Opus) — **HECHO 077a8c4,
  APROBADO (auditoría íntegra del arquitecto), 372 tests, sin código.** Diseño
  del corazón proactivo a partir de la petición literal del operador y su PDF
  de Aniridia. Verificación en vivo decisiva: `nifCif` SÍ filtra en
  /concesiones/busqueda (76 con NIF real / 0 con NIF inexistente / 28,3M
  baseline; fechaDesde/Hasta dd/mm/yyyy combinables) — la fuente del historial
  queda resuelta sin fallback caro (fallback por numeroConvocatoria
  documentado). Decisiones clave: proactivo/ fuera del contrato (como
  Prospecto); ventana SIEMPRE rango/mes desde la APERTURA de ediciones previas
  (fechaConcesion solo proxy marcado); 1 edición → esperada confianza BAJA
  etiquetada, ≥2 → ventana [min,max], confianza ALTA/MEDIA/BAJA con
  degradación "irregular"; fingerprint determinista órgano+título sin tokens
  de año, degrada a MISS jamás a enlace falso, sin IA; esperada NUNCA crea
  Match — al publicarse la edición real se enlaza y el guardarraíl de F3
  decide; nominativas accionable=False; avisos por canales ADR-004 (email solo
  publicación real; ventana próxima solo panel, 1 vez, MEDIA/ALTA);
  NO_APARECIDA informativa; anti-fuga cross-tenant ampliado; reversible.
  Observación del arquitecto para F-proactivo.1: volatilidad de organo nivel3
  (renombres de consejerías) → calibrar fingerprint (nivel1+nivel2+título).
  Quedan las 6 preguntas de calibración §8 al operador (defaults razonables).

- **PROMPT-024b — consola ignora descartadas (rendimiento + señal)** (Sonnet) —
  **HECHO 6528a29, APROBADO, 372 tests.** (El mensaje del commit dice
  "PROMPT-025" por error de etiqueta de la sesión; corresponde a este 024b.)
  convocatorias_utiles(almacen) excluye DESCARTADA_POR_DOMINIO (~1.544 de
  ~1.561 tras la pasada del 024) del dashboard y el cruce; vista de
  convocatorias con descartadas ocultas por defecto + checkbox auditable con
  motivo de exclusión + contador de ocultas. Bug incidental hallado al
  verificar contra la base real: convocatorias sin fecha alguna (frecuentes
  entre descartadas) reventaban la vista con date-vs-None → fallback
  conservador date.max con test de regresión. Medidas reales (~1.561 conv ×
  513 perfiles): dashboard 29,3s→0,26s; cruce 0,43s→0,08s; convocatorias
  500→0,06s. Sin tocar scoring, matching, contrato ni ingesta.

- **PROMPT-024 — cobertura de ingesta: búsquedas dirigidas** (Sonnet) — **HECHO
  3947e11, APROBADO, 368 tests.** Origen: segundo hallazgo del operador (PDF
  histórico de concesiones de Aniridia 2022-2024) — la ingesta solo paginaba lo
  recién publicado, nunca buscaba. Batería versionada de 11 términos con
  justificación individual; `descripcion=` verificado por el arquitecto contra
  la API real (IRPF → 424); tope de páginas por búsqueda; freno IA y dedupe
  globales; resumen por búsqueda; `abierto=` comprobado en vivo como NO-filtro
  (documentado, no usado). Pasada real: 1.458 nuevas, 88 dedupe. Contraste con
  el histórico de Aniridia: IRPF estatal/CAM, ayuda mutua y asociacionismo
  municipal APARECEN (cerradas hoy → descartadas honestas); mantenimiento CAM
  aún sin publicar → confirma la necesidad de ADR-007 (vigilancia). Secuela
  operativa: base ~1.550 filas → PROMPT-024b (vistas ignoran descartadas).

- **PROMPT-023 — honestidad de la ingesta BDNS** (Sonnet) — **HECHO 36a95a3,
  APROBADO (auditoría contra repo real), 364 tests.** Origen: PRIMER hallazgo de
  producto del operador usando la consola (Aniridia vs "PARTICIPACIÓN DE CCOO
  ... FP CANARIA 2026", verificado por el arquitecto contra la API primaria).
  (A) NUTS1 con tabla cerrada de CCAA + normalizador del dominio; TOPE POR
  ÓRGANO como invariante (el ámbito jamás más amplio que el convocante — mata
  la clase); el replicado en requisitos hereda el valor corregido; fixture real
  920435 (ES7-CANARIAS/abierto=false/"Concesión directa - instrumental") como
  regresión. (B) descarte en ingesta de no-abiertas y concesiones directas como
  DESCARTADA_POR_DOMINIO con motivo (dato ausente nunca descarta — conservador);
  métricas nuevas en el resumen del runner. (C) reevaluar_ingesta.py (--simular
  por defecto, --aplicar explícito; orquestación testeada, 6 tests) — plan real:
  50/52 a descartar (cerradas/nominativas), honesto; demo-conv-* saltadas
  limpiamente. (D) badge "requisitos sin datos — revisar bases" en el cruce.
  Decisiones de sesión auditadas: fixtures 100002-100004 con abierto=true
  (relleno arbitrario que invalidaba aserciones) y mapear_convocatoria público
  para reutilización sin duplicar — ambas correctas.

- **PROMPT-022 — cliente CLI hermético + guardarraíl de arranque + enlace por
  POST** (Sonnet) — **HECHO 7822282, APROBADO (auditoría contra repo real), 339
  tests.** Cierra la SAGA DE LOS 400 y el fallo UTF-8: (A) subprocess con
  encoding utf-8/errors replace y frontera a prueba de None (el cp1252 de
  Windows reventaba el hilo lector con 0x8d → stdout None → TypeError escapaba
  al dominio y tumbaba la pasada entera — doble violación del contrato de
  PROMPT-018, reproducida fail-first); runner con IA envuelta y contador
  fallos_ia_inesperados. (B) GET /login/confirmar ya no consume (página+botón,
  POST consume, sin-CSRF documentado: el token de un solo uso es la prueba de
  posesión) — blindaje ante prefetch y escáneres de correo, con test de 5 GETs
  repetidos. (A6) arranque real aborta si ONGS_AI_ENV=test (causa REAL de los
  dos 400 del operador: variable fantasma en la consola del servidor,
  diagnosticada con script read-only en las dos consolas tras dos teorías
  erróneas del arquitecto — prefetch y "dos almacenes", esta última por lectura
  stale del mount). DEMO.md paso 1 completo (ONGS_AI_ENV= y PYTHONUTF8=1).
  Cronología completa de los 4 sospechosos del 400: (1) ENV=test original, (2)
  fechas ISO no-UTC (latente, arreglado en 021), (3) prefetch (teórico, ahora
  imposible por diseño), (4) ENV=test reincidente — confirmado y bloqueado.

- **PROMPT-021 — consola con diseño del prototipo + demo de un comando + fix del
  enlace** (Sonnet) — **HECHO 7f3e73f, APROBADO (auditoría del arquitecto contra el
  repo real), 331 tests. RESPUESTA AL FEEDBACK DURO DEL OPERADOR (3 demos
  decepcionantes).** (A) sistema visual del prototipo extraído a
  web/estaticos/consola.css, StaticFiles montado SOLO en /consola/estaticos; 5
  vistas Jinja cableadas a los servicios auditados (resumen+oportunidades,
  convocatorias con filtros, entidades unificada, cruce motivo a motivo con
  score-ring e importe-rango, mapa Leaflet/CDN por centroide de CCAA — excepción
  consciente, degrada limpio sin red, jamás inventa direcciones). (B)
  scripts/preparar_demo.py sustituye a los dos scripts desechables SIN TESTS del
  arquitecto (vector del fallo — nunca trackeados); orquestación preparar_demo()
  con 9 tests (idempotencia entidad/prospectos, ingesta condicional por umbral,
  degradación limpia); docs/DEMO.md camino único de 4 pasos. (C) el 400 del enlace:
  reproducción literal del camino funcionaba bien invocada; el bug REAL de la clase
  sospechada quedó probado — expira_en comparado como texto ISO crudo rompe el
  orden lexicográfico con offset no-UTC (23:00+02:00 > 22:00+00:00 como texto
  siendo ANTERIOR en UTC) o naive; fix = _normalizar_utc en la frontera de AMBOS
  almacenes, con test en rojo pre-fix + test de integración fichero-SQLite
  (siembra→app separada→303→panel→reuso 400) + cp1252 ("≥" crasheaba el print en
  Windows) cazado en la verificación de cierre. Observaciones no bloqueantes del
  arquitecto: teléfono público ABAIMAR ahora en git (decisión pendiente), POSTs de
  consola sin CSRF (backlog), coste del dashboard con 511 prospectos (medir).

- **PROMPT-020 — F-consola.1: consola del operador + prospectos + scoring** (Sonnet)
  — **HECHO f870150, APROBADO (auditoría del arquitecto), 308 tests. F-consola.1
  CERRADA.** `prospeccion/` (Prospecto + puerto + importador puro, verificado contra
  el CSV real: 511 filas, 0 descartes); `servicios/afinidad.py` (70/30, cap 44,
  mapa cerrado de palabras clave, importe como rango techo-teórico, señales aparte)
  con TEST DE ANCLAJE de equivalencia a evaluar_elegibilidad — que además cazó una
  divergencia real a mitad de vuelo (pendiente_de_dato no bloqueaba elegibilidad) y
  la sesión la corrigió; duplicación por-requisito elegida sobre el refactor
  (incompatibilidad estructural Entidad/Prospecto), documentada; rol operador con
  separación verificada por inspección de rutas, clave HMAC en tiempo constante,
  solo_loopback con 404 genérico (mejora sobre la spec); listar_convocatorias +
  RepositorioProspectos en ambos backends con test de contrato. Decisiones del
  arquitecto sobre sus preguntas: dato del maestro corregido (no special-case),
  web/tamano aprobados, fórmula de afinidad temática auditada y aprobada.
- **PROMPT-019 — ADR-006: consola del operador + candidatas + scoring** (Opus) —
  **HECHO 838373a, APROBADO (auditoría del arquitecto, 674 líneas leídas), 256 tests
  (sin código).** Rol operador separado POR CONSTRUCCIÓN (dependencias/sesión
  disjuntas del tenant, test estructural); auth v1 proporcional al riesgo (clave por
  entorno en tiempo constante + solo_loopback + bind 127.0.0.1); Prospecto FUERA del
  contrato en paquete propio (prospeccion/), importador puro, conversión explícita a
  Entidad en F-consola.2; scoring determinista 0-100 (cobertura de requisitos 70 +
  afinidad temática 30 por mapeo cerrado) que ORDENA y jamás decide — con TRES
  RECHAZOS DE HONESTIDAD a la hipótesis del prototipo (probabilidad de concesión
  inventada, capacidad de ejecución dentro del score, plazo como afinidad), importe
  como rango techo-teórico en céntimos int, "elegible sin importe publicado"
  informado, nunca omitido. Pregunta bloqueante §6.2 (mapeo de columnas del maestro)
  RESUELTA por el arquitecto (autor del maestro: cabeceras Nombre/Web/Email/Teléfono/
  Ámbito/CCAA/Enfermedad-Colectivo/Personas visibles/Tamaño/Fuentes/Notas; export CSV
  UTF-8 en investigacion/asociaciones_maestro.csv, 511 filas); resto de defaults §6
  aceptados en nombre del operador (corregibles). F-consola.1 → PROMPT-020.
- **PROMPT-018 — Adapter IA por suscripción (CLI headless) + runner de ingesta local**
  (Sonnet) — **HECHO 7ce0fd7, APROBADO (auditoría del arquitecto), 256 tests.**
  `ia/claude_cli.py` (ejecutor de subprocess inyectable, forma real del JSON del CLI
  documentada, toda vía de fallo degrada limpia con contador); ExplicadorClaudeCLI +
  factory; `ia/extraccion_requisitos.py` (IA propone campos de elegibilidad SOLO del
  texto presente, validación determinista — descarta typos y bool-como-int, jamás
  pisa dato existente); freno de plan compartido (default 25); puerto aditivo
  `listar_entidades` en ambos backends con test de contrato;
  `scripts/ejecutar_ingesta.py` (pipeline completo, orquestación testeada con stubs).
  PASADA REAL del cierre: 50 convocatorias BDNS nuevas ingestadas, 1 enriquecida por
  IA (3/3 llamadas, 13 sin IA por freno — degradación correcta), 29 no elegibles con
  motivo, **1 propuesta real generada y avisada**. La visión corre de punta a punta
  con datos vivos y la suscripción del operador.
- **PROMPT-017 — Fix SQLite multihilo bajo FastAPI** (Sonnet) — **HECHO 1336741,
  APROBADO (auditoría del arquitecto), 222 tests.** check_same_thread=False + Lock
  del almacén serializando toda operación (migración incluida). Regresión doble:
  hermético desde otro hilo + integración HTTP con AlmacenSQLite(':memory:') —
  el hueco que dejó pasar el bug queda tapado para siempre. Práctica ejemplar de la
  sesión: verificó que ambos tests FALLAN con el fix revertido antes de darlos por
  buenos. Bug original cazado por el operador en navegador real (2026-07-21).
- **PROMPT-016 — Empaquetado instalable + comando canónico** (Sonnet) — **HECHO
  8ebfb1d, APROBADO (auditoría del arquitecto), 220 tests.**
  `[tool.setuptools.packages.find] where=["src"]`; `pip install -e .` verificado
  (import fuera de pytest y sin PYTHONPATH); CLAUDE.md con `python -m uvicorn ...
  --port 8001`; demo_semilla_local.py y `*.egg-info/` gitignorados (la segunda,
  iniciativa estándar de la sesión, aprobada). NOTA DE PROCESO (2ª vez): la sesión
  ejecutó la versión del prompt ANTERIOR al último remate del arquitecto — el fix
  del bug SQLite multihilo NO se hizo (sqlite.py sin tocar, verificado) → reencolado
  como PROMPT-017. Regla nueva en recordatorios: copiar el prompt del 06 ACTUAL
  (tras el último aviso del arquitecto), no de un buffer viejo. El "puerto 8001
  ocupado" que reportó la sesión era el PROPIO uvicorn del operador aún corriendo.
- **PROMPT-015 — F-web.2: aceptar/descartar con CSRF + comando servidor** (Sonnet) —
  **HECHO 455de38, APROBADO (auditoría del arquitecto), 220 tests. F-web.2 CERRADA.**
  CSRF por token de sesión con comparación en tiempo constante (desviación aprobada:
  sin itsdangerous — la cookie ya va firmada); rutas/propuestas.py con propiedad del
  match resuelta SOLO dentro de listar_matches_por_entidad (ajeno = inexistente =
  mismo 404); TransicionIlegalError (doble submit) → redirect neutro sin asiento;
  botones solo en propuestas_pendientes; ajuste legítimo de 2 tests (el match_id
  PROPIO va en campo oculto del formulario; se mantiene la garantía: jamás ids
  ajenos). CLAUDE.md ganó el comando de servidor — PERO la sesión ejecutó la versión
  del prompt ANTERIOR a los remates del arquitecto: empaquetado y comando con
  python -m/--port 8001 quedaron fuera → reencolados como PROMPT-016.
- **PROMPT-014 — F-web.1: esqueleto web + auth magic link + panel** (Sonnet) —
  **HECHO 06418f3, APROBADO (auditoría del arquitecto), 214 tests. F-web.1 CERRADA.**
  Deps runtime primeras (fastapi 0.139.0, uvicorn 0.49.0, jinja2 3.1.6, itsdangerous
  2.2.0, python-multipart 0.0.32; httpx 0.28.1 dev). Puertos aditivos
  (obtener_entidad_por_email con dedupe→None+contador; RepositorioTokensAcceso
  atómico un-solo-uso) en ambos backends con tests de contrato;
  servicios/autenticacion.py (TTL 60 min, hash sha256, anti-enumeración);
  EnviadorEnlaceAccesoSMTP; web/ completo (app.py solo-includes con max_age 30 días
  y SECRET_KEY solo en composición; entidad_actual única fuente de tenant; rutas sin
  entidad_id; plantillas autoescape; filtro euros por divmod sin float). Anti-fuga
  cross-tenant a nivel HTTP (incl. intento por query param). Desviaciones aprobadas:
  app condicional a SECRET_KEY; ONGS_AI_APP_BASE_URL nueva variable; CLAUDE.md sin
  tocar (fuera de mandato — el comando de servidor lo fijó después PROMPT-015/016).
- **PROMPT-013 — ADR-005: esqueleto web + auth multi-tenant** (Opus) — **HECHO
  a4c80ab, APROBADO (auditoría del arquitecto, 447 líneas leídas), 184 tests (sin
  código).** FastAPI+uvicorn+Jinja2 SSR sin SPA; magic link sin contraseñas
  (tokens hasheados, un solo uso, consumo atómico, anti-enumeración); sesión en
  cookie firmada con SOLO entidad_id — `entidad_actual(request)` como ÚNICA fuente
  de tenant, ninguna ruta acepta entidad_id del cliente (aislamiento por
  construcción); autoescape como control de seguridad ante texto libre de IA;
  primeras dependencias runtime justificadas y acotadas; puertos aditivos
  (obtener_entidad_por_email + RepositorioTokensAcceso) sin tocar contrato.
  Decisiones del operador sobre §7 (2026-07-21): sesión 30 DÍAS, TTL del enlace
  1 HORA, hosting/TLS al captar piloto; resto de defaults aceptados (SECRET_KEY por
  entorno, recuperación manual, rutas en español). F-web.1 promovido como PROMPT-014.
- **PROMPT-012 — Remates F4.2 + scraper FEDER** (Sonnet) — **HECHO 6457682, APROBADO
  (auditoría del arquitecto), 184 tests.** Cubo `aceptadas` añadido al panel (orden
  espejo de la máquina de estados); gitignore corregido a
  `investigacion/*asociaciones*` (verificado con git check-ignore sobre los 4
  ficheros de datos); parser hermético en `adapters/captacion/feder.py` (fixtures
  sintéticas) + `scripts/scrape_feder.py` manual con pausa, UA identificable y
  salvaguarda anti-martilleo; xlsx writer stdlib para no meter la primera dependencia
  runtime. Ejecutado por la sesión con red real: **272 entidades (270 con email)** —
  y hallazgo de valor: el listado de FEDER sirve una capa de mapa Drupal/Geolocation
  idéntica en todas las páginas; su contador dice 476 pero ~204 entidades sin
  geocodificar son INALCANZABLES por esa vía (otra fuente o pedir censo a FEDER).
  El arquitecto fusionó el volcado en el maestro de prospección:
  `asociaciones_EERR_directorio_v3.xlsx` = **511 entidades** (147 nuevas, 20
  enriquecidas), fuera de git.
- **PROMPT-011 — F4.2: adapter de email SMTP real + read model del panel** (Sonnet) —
  **HECHO fb95b4a, APROBADO (auditoría del arquitecto), 176 tests. F4.2 CERRADA.**
  `adapters/avisos/email_smtp.py` (NotificadorEmailSMTP con cliente inyectado — cero
  sockets en tests; `construir_aviso_email` pura, texto plano, sin ids internos ni
  costes; degrada limpio con contadores enviados/omitidos/fallidos) + `factory.py`
  (config SOLO aquí vía ONGS_AI_SMTP_*; stub en entorno test) + `servicios/panel.py`
  (resumen_panel por tenant, 5 cubos, más-reciente-primero; DETECTADA-elegible
  transitoria se omite sin lanzar) + `scripts/smoke_email.py` manual fuera de CI.
  Remates a PROMPT-012 (detectados en el cierre): cubo ACEPTADA ausente (omisión del
  prompt del ARQUITECTO, no de la sesión) y patrón gitignore
  `investigacion/asociaciones*` que NO cubría `R2_asociaciones_*` (la sesión dejó ese
  fichero fuera del commit a mano — correcto).
- **PROMPT-010 — F4.1: persistencia de matches + propuesta automática y sobrevenida**
  (Sonnet) — **HECHO 9f8c732, APROBADO (auditoría del arquitecto, 2026-07-21, desde
  git), 155 tests. F4.1 CERRADA.** `servicios/propuestas.py` (detectar_y_proponer:
  pre-puerta VERIFICADA+plazo abierto, upsert por pareja Entidad×Convocatoria,
  detectada→propuesta con aviso — incluida elegibilidad sobrevenida —, terminales
  respetados sin resucitar, regresión de elegibilidad sin retroceso de estado ni
  re-aviso, contadores en ResumenPropuestas) + `servicios/notificacion.py` (Protocol
  Notificador + NotificadorStub; notificación SIEMPRE degrada limpio). Ids/reloj
  inyectados; sin cambio de contrato ni esquema, tal como exigía ADR-004. Nota: el
  cierre se registró el día 21 porque la pizarra del disco fue pisada por el mount
  con una copia del 18 (commit accidental 61d76a4) — recuperada desde 9f8c732;
  incidente y regla nueva (git = verdad de la pizarra, un solo arquitecto activo)
  fijados en el traspaso del 06.

## Semana 2026-07-13/19

- **PROMPT-009 — F2-fix: ámbito provincial (NUTS3) en el adapter BDNS** (Sonnet) —
  **HECHO 6a50af2, APROBADO (auditoría independiente del arquitecto del día 19,
  DESDE GIT), 133 tests. F2-fix CERRADA.** Bug destapado por el smoke test del
  operador contra la API viva: los códigos NUTS3 (provincia, "ES"+3 dígitos) se
  etiquetaban `ambito_geografico=AUTONOMICO` con la provincia en `region`.
  `_ambito_y_region_desde_regiones` pasa a devolver terna (ambito, region,
  provincia): 2 dígitos (NUTS2)→AUTONOMICO/region, 3 (NUTS3)→PROVINCIAL/provincia,
  resto→NACIONAL conservador. Sin tocar contrato ni esquema. +7 tests unitarios
  sobre la función pura. LECCIÓN: para auditar tras un commit reciente, `git show`,
  nunca el mount.
- **PROMPT-008 — F2: ingesta de convocatorias vía API BDNS** (Sonnet) — **HECHO
  5a52d27, APROBADO (auditoría independiente del arquitecto del día 19), 126 tests.
  F2 CERRADA.** `adapters/ingesta/base.py` (Protocol FuenteConvocatorias, transporte
  HTTP inyectable, FiltrosBusqueda como datos); `adapters/ingesta/bdns.py` (búsqueda
  paginada + detalle, mapeo determinista tipo/ámbito/región/dinero/plazos, dinero
  euros→céntimos vía Decimal HALF_UP, degradación limpia);
  `dominio/ingesta_estado.py` (promocionar_si_completa); puerto
  `obtener_por_url_origen` (dedupe portal+url_origen) en ambos adapters con ALTER
  TABLE idempotente; `adapters/ingesta/servicio.py` (ingestar con dedupe, doble
  pasada testeada); 6 fixtures JSON sintéticas + `scripts/smoke_bdns.py` manual.
  R1 commiteada y `.gitignore` ganó `investigacion/asociaciones*`. Smoke del
  operador contra la API viva: 5 convocatorias reales mapeadas de punta a punta.
- **PROMPT-007 — F3: guardarraíl determinista + capa IA explicativa** (Sonnet) —
  **HECHO fc04348, APROBADO (auditoría del arquitecto), 101 tests. F3 CERRADA.**
  `elegibilidad.py` (6 reglas puras, no-evaluable ⇒ no elegible, detalle línea a
  línea), `matching.py` (detectar_matches con ids/reloj inyectados, Protocol de
  dominio propio), `ia/explicacion_match.py` (Protocol + ExplicadorStub; la IA
  degrada limpia, jamás decide). Hallazgo de auditoría: redundancia de ámbito en el
  contrato (`ambito_geografico`+region/provincia vs `ambito_territorial_requerido`
  sin consumir) → candidato ADR-003. Nota de diseño para F4: detectar_matches crea
  Match para TODA pareja (literal del prompt) — la política de persistencia se
  decidió en ADR-004.
- **PROMPT-006 — ADR-002: Entidad gana forma jurídica y fecha de constitución**
  (Sonnet) — **HECHO e97baa5, APROBADO (auditoría del arquitecto), 63 tests.**
  Nota de proceso: la sesión escribió aquí "APROBADO" por su cuenta y sin hash antes
  de la auditoría — el veredicto real llegó después y coincidió; la regla "solo el
  arquitecto cierra y aprueba" quedó fijada en el preámbulo común a raíz de esto.
  ADR+código en una sola sesión (desviación autorizada: cambio pequeño y cerrado).
  `Entidad` gana `forma_juridica: FormaJuridicaDeclarada` (enum cerrado, descripcion
  obligatoria si OTRA) y `fecha_constitucion: date`, ambos obligatorios; la
  antigüedad no se almacena, se calcula contra fecha de referencia explícita.
  `normalizar_forma_juridica` en dominio puro (mapeo cerrado, sin LLM; OTRA nunca
  automático; sin mapeo → None, degrada limpio). Serialización SQLite, fixtures y
  round-trip de ambos adapters; CONTRATO CONGELADO referencia ADR-002.
- **PROMPT-004 + PROMPT-005 — F1: contrato + persistencia + tests** (Sonnet) —
  **HECHO 7db6c5d + 1dc7c44 (corrección), APROBADO, 48 tests. F1 CERRADA.**
  Contrato ADR-001 implementado en dominio puro; máquina de estados exacta con
  terminales; dinero/pb solo int (rechaza bool); factory memoria/SQLite; SQLite con
  `datos_json` interno pero puerto cumplido con objetos tipados (corrección de
  auditoría: 7db6c5d devolvía dicts y el anti-fuga solo corría en memoria);
  degradación limpia con `registros_omitidos_por_corrupcion`; tests de contrato y
  anti-fuga parametrizados sobre ambos adapters; Protocol runtime_checkable;
  CONTRATO CONGELADO fijado en CLAUDE.md. Primer push del ritual (origin activo).
- **PROMPT-003 — ADR-001 contrato de datos** (Opus) — **HECHO 6423f46, APROBADO**.
  `engineering/ADR-001-contrato-de-datos.md` (359 líneas): Entidad/Convocatoria/
  Actividad/Match, frontera IA-extrae/dominio-decide, alternativas (JSON libre,
  matching todo-IA) bien descartadas, fases F1–F5. Desviación aprobada: solo F1 con
  prompt completo; F2–F5 los redacta el arquitecto tras auditar la fase anterior.
  Refinamientos del arquitecto al encolar F1: `descartada`/`presentada` terminales;
  `porcentaje_max_financiable` en puntos básicos enteros.
- **PROMPT-002 — Higiene post-bootstrap** (Sonnet) — **HECHO 1f50ed8, APROBADO**.
  .gitattributes (EOL fijados, renormalización sin churn); pytest>=8 como dev-dep;
  versión única (`dynamic` → `ongs_ai.__version__`). Corrección de ritual: el commit
  original salió sin el nº de tests en el mensaje pese a que el resumen decía lo
  contrario — amend del operador antes de existir remoto. Lección: auditar siempre
  el mensaje real.
- **PROMPT-001 — Bootstrap del repo** (Sonnet) — **HECHO 2101890, APROBADO**.
  git init -b main; .gitignore; 06 → engineering/ + 06_HISTORICO creado;
  ux-reviewer → .claude/agents/; esqueleto Python (1 smoke test VERDE). Notas
  menores absorbidas en PROMPT-002.
