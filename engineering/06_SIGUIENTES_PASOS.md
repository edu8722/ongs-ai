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

- **2026-07-18 (noche) — F1 CERRADA Y APROBADA (7db6c5d + corrección 1dc7c44,
  48 tests, pushed).** Contrato ADR-001 implementado, puerto cumplido en ambos
  adapters, anti-fuga y round-trip parametrizados, degradación limpia. Detalle en
  histórico. Estado de fases: F1 ✔ · F2 bloqueada (lista de portales) · F3 siguiente
  tras ADR-002 · F4/F5 lejos.
- **F3 CERRADA Y AUDITADA — HECHO fc04348, 101 tests (2026-07-18 noche):**
  guardarraíl determinista + matching + capa IA con degradación limpia. Detalle en
  histórico. Estado de fases: F1 ✔ · ADR-002 ✔ · F3 ✔ · **F2 EN COLA (PROMPT-008,
  adapter BDNS)** · F4/F5 pendientes. Notas de auditoría: redundancia de ámbito en
  el contrato → candidato ADR-003 (backlog); política de persistencia de matches no
  elegibles → decidir en F4.
- **2026-07-18 — NUEVO ENCARGO DE PRODUCTO (feedback del operador → spec):** la
  plataforma capta proactivamente. Dos investigaciones profundas DEL ARQUITECTO (no
  son prompts de código): **R1 — catálogo de fuentes de subvenciones** (estatales/
  autonómicas/locales/privadas: URL, cómo se consulta, qué elegibilidad publican) →
  sustituye la "lista de portales" pendiente del operador y desbloquea la spec de F2;
  **R2 — directorio de asociaciones de EERR en España** con contacto público → nutre
  captación y candidatas a piloto. Decisiones del operador: R1 primero; R2 INCLUYE
  personas visibles públicamente (⚠ dato personal: el fichero de prospección se trata
  fuera de git — `investigacion/asociaciones*` gitignorado; responsable del
  tratamiento: el operador); formato Excel + informe.
- **R1 ENTREGADA (2026-07-18): `investigacion/R1_catalogo_fuentes_subvenciones.xlsx`
  + `R1_informe.md`.** Hallazgo clave VERIFICADO 3-0: la BDNS/SNPSAP tiene API REST
  pública sin auth (Swagger) que agrega TODAS las convocatorias públicas de España
  (estatal+CCAA+local, con campos que mapean casi 1:1 al contrato) ⇒ **F2 = un solo
  adapter `bdns.py` cubre todo el sector público**; privadas (FEDER, la Caixa, ONCE)
  y agregador SolucionesONG en adapters posteriores. Nota: la verificación
  adversarial quedó incompleta (límite de sesión, 22 claims de fuentes oficiales
  marcadas "pendiente", 0 refutadas) — re-pasada opcional. R2 (directorio
  asociaciones EERR) PENDIENTE de lanzar.
- **Lección para el ritual** (sigue vigente, 3 casos): los resúmenes y acciones de
  las sesiones exceden o desmienten lo real — mensaje de commit (PROMPT-002),
  "decisión conservadora" que rompía el puerto (PROMPT-004), auto-cierre con
  "APROBADO" en la pizarra antes de la auditoría (PROMPT-006 — de ahí la regla nueva
  del preámbulo). Auditar SIEMPRE el artefacto real; el veredicto es del arquitecto.
- Cerrado al histórico: PROMPT-001 (2101890), 002 (1f50ed8), 003/ADR-001 (6423f46),
  004+005/F1 (7db6c5d+1dc7c44), 006/ADR-002 (e97baa5). Stack Python/SQLite/pytest
  hermético.
- **Decisiones del operador (2026-07-18) sobre ADR §6 — cerradas:** (1) módulo
  `src/ongs_ai/dominio/` ✔; (2) **F5 AMPLIADO sobre el default**: no solo memoria
  narrativa — análisis de TODO lo que la entidad necesita para poder presentarse
  (checklist de requisitos documentales con gap: qué tiene / qué le falta) + borrador
  de TODOS los documentos entregables a partir de los datos que la entidad facilite
  (probable ADR de ampliación de contrato al llegar F5: entidad DocumentoRequerido);
  (3) aviso F4 = **email + panel** en la plataforma (el panel adelanta la necesidad
  del esqueleto web — subir en backlog); (4) Match nuevo tras descartada ✔;
  (5) dedupe `portal`+`url_origen` ✔.
- **Duele:** sigue sin entidad piloto. Test anti-hardcoding v1 es canario débil —
  endurecer en F3+. Contrato sin `municipio` en Entidad → ámbito LOCAL no evaluable
  automáticamente en F3 (ADR si el matching local lo pide). F2 YA DESBLOQUEADA por
  R1 (spec: adapter BDNS primero) — su prompt se redacta tras auditar F3.
- **Remoto git ACTIVO**: `origin` = github.com/edu8722/ongs-ai (privado), al día
  (`origin/main` = e97baa5). El `git push` del ritual es OBLIGATORIO en cada cierre.

## COLA — lo que de verdad queda

### ➤ PROMPTS PENDIENTES — todos aquí, listos para copiar (se vacían al cerrarse)

#### PROMPT-008 — F2: ingesta de convocatorias vía API BDNS · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: F2 del ADR-001 — ingesta de convocatorias vía la API pública de la
BDNS. Contexto (verificado en investigación R1, ver
investigacion/R1_informe.md): la BDNS/SNPSAP agrega TODAS las convocatorias
públicas de España (estatal, CCAA, diputaciones, ayuntamientos) y expone
API REST pública SIN autenticación (Swagger:
https://www.infosubvenciones.es/bdnstrans/doc/swagger). Búsqueda paginada
JSON: /bdnstrans/api/convocatorias/busqueda?page=N&pageSize=M. Detalle:
/bdnstrans/api/convocatorias?numConv=<códigoBDNS> con campos
tiposBeneficiarios, regiones, fechaInicioSolicitud, fechaFinSolicitud,
abierto, presupuestoTotal, finalidad, urlBasesReguladoras, organo y
jerarquía administrativa nivel1/nivel2/nivel3.

1. `src/ongs_ai/adapters/ingesta/base.py`: Protocol `FuenteConvocatorias`
   (p. ej. `buscar(filtros) -> Iterable[Convocatoria]`) + transporte HTTP
   INYECTABLE (Protocol o callable url->respuesta). Los tests usan SIEMPRE
   transporte stub con fixtures grabadas — red apagada, cero peticiones
   reales en tests (regla de oro).
2. `src/ongs_ai/adapters/ingesta/bdns.py`: `FuenteBDNS` contra esa API.
   Mapeo DETERMINISTA (aquí no hay LLM: la API ya da datos estructurados)
   a `Convocatoria` del contrato:
   - `fuente`: portal="BDNS", `url_origen` = URL de detalle con el código
     BDNS (clave natural de dedupe, ADR-001 §6.5), `tipo` desde la
     jerarquía administrativa (estatal→publica_nacional,
     autonómica→publica_autonomica, local→publica_local; sin mapeo claro →
     el valor más conservador y documéntalo).
   - `regiones` → `ambito_geografico` + `region` (código "ES51 - CATALUÑA"
     → separa código y nombre; varias regiones o "ES - ESPAÑA" → nacional).
   - fechas de solicitud → `plazos`; `finalidad`/descripcion → `objeto`;
     `tiposBeneficiarios` (texto) → `beneficiarios_elegibles`.
   - `presupuestoTotal` llega en EUROS (posible float) → convierte a
     CÉNTIMOS int en la frontera del adapter (round determinista); jamás
     float hacia el dominio (regla de oro).
   - `requisitos_elegibilidad`: solo lo derivable determinista (p. ej.
     ámbito); el resto queda vacío para la capa de extracción IA futura.
   - `estado_ingesta`: EXTRAIDA al mapear; una función de dominio pequeña
     promociona a VERIFICADA solo si los campos mínimos están presentes
     (defínelos y documéntalos: al menos objeto, plazos con fecha_cierre,
     ambito_geografico y beneficiarios no vacíos).
   - Filtros de búsqueda (texto, fechas, beneficiario) SIEMPRE como
     parámetros/datos — ninguna enfermedad ni entidad hardcodeada.
3. Dedupe idempotente: re-ingestar la misma convocatoria (mismo
   portal+url_origen) NO duplica — comprueba contra el almacén antes de
   guardar (añade al puerto lo mínimo necesario si hace falta, p. ej.
   obtener_por_url_origen) y testéalo con doble pasada.
4. Fixtures: 2-3 respuestas JSON REALISTAS de la API (recórtalas a mano,
   sintéticas pero con la forma real de los campos del Swagger; jamás
   datos de entidades reales inventando cifras) en tests/fixtures/ingesta/.
5. `scripts/smoke_bdns.py`: script MANUAL (fuera de pytest) que el
   OPERADOR ejecutará con red real: pide 1 página de la API, mapea e
   imprime un resumen. Documenta en su docstring que hace red y no se
   ejecuta en CI.
6. Git de la carpeta `investigacion/` (hoy sin trackear): añade a
   .gitignore la línea `investigacion/asociaciones*` (prospección con
   datos personales, NUNCA a git) y commitea SOLO
   `investigacion/R1_catalogo_fuentes_subvenciones.xlsx` y
   `investigacion/R1_informe.md` (catálogo sin datos personales).
7. Tests: mapeo completo BDNS→Convocatoria (incluido dinero a céntimos y
   regiones), paginación, dedupe en doble pasada, promoción
   EXTRAIDA→VERIFICADA (con y sin campos mínimos), transporte que falla →
   degrada limpio (sin excepción al dominio; registra y sigue), y todo el
   resto de la suite VERDE.
8. `python -m pytest -q` VERDE, herméticos. Incluye los cambios de
   `engineering/06_*` del working tree tal cual (cierre de F3 por el
   arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add, `git push` al terminar.
```

### Bandeja del OPERADOR

- Pegar PROMPT-008 (F2, ingesta BDNS) en una sesión de Claude Code (Sonnet) y avisar
  al arquitecto al terminar para auditoría.
- Tras el cierre de F2: ejecutar `python scripts/smoke_bdns.py` en tu terminal (hace
  red real) y pegar el resumen al arquitecto — verificación humana de la API viva.
- Revisar el Excel de R1 y decir al arquitecto si falta algún portal de los que usabas.
- **Captar entidad piloto** (acceso + ingresos/gastos del ejercicio anterior +
  lista de actividades). El arquitecto ofrece redactar el mensaje de propuesta.

### Backlog

- F4 propuesta/aviso (email + panel; decide política de persistencia de matches no
  elegibles) · F5 preparación asistida (alcance ampliado por el operador) — prompt
  al quedar AUDITADA la fase anterior (ADR-001 §5).
- ADR-003 candidato: redundancia de ámbito en el contrato (`ambito_geografico`+
  region/provincia vs `ambito_territorial_requerido` sin consumir) — limpiar.
- R2 — directorio asociaciones EERR: **TANDA 1 ENTREGADA**
  (`investigacion/R2_asociaciones_eerr_tanda1.xlsx`, fuera de git): 6 directorios
  agregadores mapeados (FEDER = fuente primaria, **476 entidades**, paginado ~35/pág
  con filtros; SID USAL >400; Somos Pacientes; POP; delegaciones FEDER; Registro
  Nacional) + **35 asociaciones con teléfono/email/web** (FEDER pág. 1). PENDIENTE:
  extraer las ~13 páginas restantes de FEDER (pasada sistemática del arquitecto, a
  demanda del operador) y enriquecer con personas visibles desde webs propias.
  Nota: el fan-out de subagentes chocó con el límite semanal del modelo — la tanda 1
  se extrajo en línea; próximas pasadas igual o con el límite renovado.
- Adapters privados de ingesta (FEDER, la Caixa, ONCE) + agregador SolucionesONG —
  tras F2.
- Proveedor LLM real para la capa IA (hoy ExplicadorStub) — decisión del arquitecto.
- Endurecer el test anti-hardcoding (el canario del ADR pasa por construcción).
- Esqueleto de la app (fija el comando de servidor local en CLAUDE.md) — tras F1.
- Modelo de negocio (las entidades objetivo tienen pocos recursos) — conversación
  de producto, sin prisa técnica.
- Ajustar la "vara de medir" de ux-reviewer.md cuando exista sistema visual propio.

### Recordatorios operativos

- Máquina Windows: comandos como `python -m pytest -q` (no rutas unix); rutas con `C:\dev\ongs-ai`.
- Mount sandbox↔host miente con ficheros recién editados — el HOST es la verdad.
- Git desde sandbox: SOLO `git log`/`git show`; jamás status/diff (index.lock huérfanos).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
