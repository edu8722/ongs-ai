# ADR-004 — Política de persistencia de matches y aviso proactivo (F4)

- **Estado:** ACEPTADA (2026-07-19). Decisiones de producto del operador registradas abajo.
- **Contexto de fase:** F1 ✔ · ADR-002 ✔ · F3 ✔ · F2 ✔ (con corrección PROMPT-009). Este ADR abre F4.
- **Relación:** amplía ADR-001 (§1.4 Match / máquina de estados, §6.4) sin modificar el
  contrato congelado (Entidad/Convocatoria/Actividad/Match) ni sus enums. Si algo aquí
  exigiera tocar el contrato, se detiene y se abre ADR de contrato — no es el caso.

## 1. Contexto y problema

F3 dejó `detectar_matches` (dominio puro) evaluando **cada** pareja Entidad×Convocatoria,
calculando siempre `resultado_elegibilidad_dura` (guardarraíl determinista, función PURA
y por tanto **recalculable gratis**) y creando un `Match` en estado `detectada`. Pero
`detectar_matches` **no persiste** y la transición `detectada → propuesta` se dejó
explícitamente para F4. La política de persistencia de los pares **no elegibles** quedó
como decisión abierta (nota en histórico F3: "no persistir a escala BDNS").

Dos hechos tensionan la decisión:

1. **Escala.** La ingesta BDNS (F2) agrega TODAS las subvenciones públicas de España, de
   todos los sectores. Persistir un `Match` por cada pareja contra decenas de miles de
   convocatorias irrelevantes es O(entidades × convocatorias) de filas, casi todas "no
   elegible" y recalculables — ruido que hincha almacén y panel.
2. **Valor de producto.** El operador quiere **persistencia de todo**: ver también los
   "casi", el motivo por el que no se calificó, y el histórico en el tiempo — no solo lo
   elegible. La trazabilidad ("¿por qué no me avisaron de X?") es parte del producto.

La clave para reconciliarlos: lo único NO recalculable de un `Match` es su historial de
**asientos** (decisiones humanas/sistema) y la `explicacion_ia` (cuesta dinero
regenerarla). El veredicto de elegibilidad es derivable. Así que "persistir todo" es
viable si se **acota el universo** de convocatorias, no si se recalcula todo bajo demanda.

## 2. Decisión

### 2.1 Persistir todo match, acotado a un CATÁLOGO RELEVANTE
Se persiste un `Match` por cada pareja Entidad×Convocatoria **elegible y no elegible**,
pero **solo** sobre convocatorias del catálogo relevante. El acotado tiene dos capas,
ninguna hardcodea enfermedad/entidad (regla de oro):

- **Filtro de relevancia en la INGESTA** (ya soportado por `FiltrosBusqueda` de F2:
  texto/beneficiario/fechas): lo que entra al catálogo compartido son convocatorias
  plausiblemente relevantes para el tercer sector / entidades sin ánimo de lucro. Es
  best-effort y coarse (alta cobertura); su afinado es iterativo y vive en datos.
- **Pre-puerta de dominio en la detección**: solo se generan/persisten matches contra
  convocatorias en estado `VERIFICADA` **y con plazo abierto** (`fecha_cierre` presente y
  ≥ `fecha_referencia`). Las no verificadas y las cerradas no son accionables → no
  generan fila.

"Todo" ⇒ **todo lo relevante que ingerimos y está vivo**. Un par no elegible por ámbito o
por requisito se persiste con su motivo; una ayuda pesquera nunca entra al catálogo.

### 2.2 Clave natural y no duplicación
El `Match` **activo** de una pareja se identifica por la clave natural
`(entidad_id, convocatoria_id)`, donde "activo" = su `estado_actual` NO es terminal
(`descartada` ni `presentada`). Invariante: **como mucho un match activo por pareja**.

- Re-detección periódica: si existe match activo para la pareja → **upsert** (se actualiza,
  no se duplica). Si NO hay activo pero sí un match terminal (`descartada`/`presentada`) →
  **no se hace nada** (se respeta la conclusión humana/sistema; la re-detección automática
  nunca "resucita" un descartado ni re-propone un presentado). Si no hay ningún match para
  la pareja → se crea.
- El reintento tras `descartada` como **match nuevo** (mismo Entidad+Convocatoria) sigue
  siendo, como en ADR-001 §1.4, una acción HUMANA explícita — no la dispara la detección
  automática.

### 2.3 Estados y aviso
- **Elegible**: en la detección, el match avanza `detectada → propuesta` (actor SISTEMA) y
  se **avisa** (email + panel). `detectada` es transitorio (el instante entre detección y
  propuesta).
- **No elegible**: el match se queda en `detectada`, con `resultado_elegibilidad_dura` y su
  `detalle` línea a línea. Visible en el panel (filtrable), sin aviso.

### 2.4 Elegibilidad sobrevenida → avisar como nueva propuesta
Si en una re-detección una pareja pasa de **no elegible → elegible** sobre un match
**activo en `detectada`**, se transiciona `detectada → propuesta` y se **avisa igual que
una propuesta nueva** (decisión del operador). Idempotencia: si el activo ya está en
`propuesta` (ya se avisó) y sigue elegible, **no** se re-avisa. Regresión (un match ya
propuesto/aceptado que deja de ser elegible por cambio de datos) **no** se auto-retrocede:
se actualiza `resultado_elegibilidad_dura` para el registro y se deja el estado alcanzado
(ya se comunicó / ya se actuó); queda anotado para revisión, no se automatiza el retroceso.

### 2.5 Canales
- **Email**: SOLO elegibles / recién-elegibles (propuestas).
- **Panel**: TODO, con filtros (elegible / no elegible + motivo). El panel adelanta la
  necesidad del esqueleto web.

### 2.6 Notificación por puerto inyectable
El aviso sale por un puerto `Notificador` (Protocol) inyectable. En tests, stub que
registra llamadas (red apagada). El **email real se difiere** (stub por ahora, mismo
patrón que `ExplicadorStub` de la capa IA). Fallo de notificación **degrada limpio**: se
registra y se sigue; nunca rompe la persistencia ni lanza al dominio (regla de oro).

### 2.7 Alcance de entrega de F4
F4 entrega **backend + modelo de lectura + puerto de notificación**. La **UI del panel**
(web) es el **esqueleto de la app**, tarea aparte del backlog (fija además el comando de
servidor local en CLAUDE.md). No se construye HTML en F4.

## 3. Alternativas consideradas y descartadas

- **Persistir la BDNS entera sin filtrar.** Máxima trazabilidad, pero O(E×C) de ruido
  recalculable; hincha almacén y panel. Descartada: el valor está en el catálogo relevante,
  no en el sector ajeno.
- **Persistir solo elegibles; recalcular no-elegibles bajo demanda.** Barata y el veredicto
  es recalculable, pero pierde el histórico en el tiempo y el motivo del "casi" que el
  operador quiere ver, y no deja overlay para intención humana sobre un no-elegible.
  Descartada por decisión de producto.
- **Auto-resucitar/re-proponer matches `descartada` en cada detección.** Descartada:
  spamea y pisa la intención humana; el reintento es acción humana (§2.2).
- **Añadir columna `estado` + índice ya en F4.1.** Útil para el panel a escala, pero no
  imprescindible ahora (el read model reconstruye desde `datos_json`). Se difiere como
  optimización (§5) para no meter migración innecesaria — se hará cuando el volumen lo pida.

## 4. Consecuencias

- (+) Trazabilidad y transparencia completas dentro del catálogo relevante; el operador ve
  los "casi" y su motivo.
- (+) No se pierde una oportunidad **sobrevenida** (aviso al flip no→sí).
- (+) Respeta la intención humana (no resucita descartadas).
- (−) La tabla `matches` crece con los no-elegibles del catálogo relevante — **acotado**,
  pero **a vigilar**: si el catálogo relevante se ensancha, reevaluar el pre-filtro
  geográfico y/o añadir el índice/columna `estado` (§5).
- (−) Coste de re-detección periódica (recorrer catálogo vivo × entidades). Mitigado por la
  pre-puerta (solo VERIFICADA+abierta) y por indexar en memoria los matches de la entidad.
- (Neutro) Sin cambio de contrato ni de esquema en F4.1: se reutilizan
  `guardar_match`/`listar_matches_por_entidad` (F1) y la máquina de estados (F3).

## 5. Diseño técnico (para las fases)

- **Orquestador de detección-y-propuesta** (servicio, NO dominio puro — compone puertos):
  nuevo módulo propio. Algoritmo por entidad:
  1. Cargar los matches existentes de la entidad (`listar_matches_por_entidad`) e indexarlos
     en memoria por `convocatoria_id`.
  2. Para cada convocatoria del catálogo **VERIFICADA y con plazo abierto**:
     evaluar `evaluar_elegibilidad`; localizar el match activo de la pareja (estado no
     terminal) y si hay terminal.
     - Con activo: actualizar `resultado_elegibilidad_dura`; si estaba en `detectada` y el
       veredicto es elegible → `transicionar(detectada→propuesta)` + notificar; `guardar_match`.
     - Sin activo pero con terminal: no hacer nada.
     - Sin match: `crear_match` (detectada) con el veredicto; si elegible →
       `transicionar(detectada→propuesta)` + notificar; `guardar_match`.
  3. Notificación siempre envuelta en try/except (degrada limpio).
- **Puerto `Notificador`** (Protocol) + `NotificadorStub` (registra llamadas). Email real
  diferido.
- **Sin nuevos métodos de puerto obligatorios** en F4.1 (basta `listar_matches_por_entidad`
  + `guardar_match`). El read model del panel puede añadir consultas en F4.2.
- **Determinismo**: ids y reloj SIEMPRE inyectados (como F3). Tests herméticos, sin red.

## 6. Fases y prompts

- **F4.1 — persistencia + propuesta automática + sobrevenida** → PROMPT-010 (abajo, listo).
- **F4.2 — adapter de email real + modelo de lectura del panel** (consultas por
  estado/elegibilidad; posible columna `estado`+índice si el volumen lo pide) → se redacta
  tras auditar F4.1.
- **Esqueleto de la app / UI del panel** → tarea de backlog aparte (fija servidor local en
  CLAUDE.md).

### PROMPT-010 — F4.1: persistencia de matches + propuesta automática · MODELO: Sonnet · ORDEN: tras PROMPT-009 (F2-fix)

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
engineering/06_* y engineering/ADR-004-* que ya estén en el working tree,
tal cual estén.

TAREA: F4.1 del ADR-004 (léelo entero: engineering/ADR-004-persistencia-
matches-y-aviso-proactivo.md). Implementa la persistencia de matches y la
propuesta automática. NO toques el contrato (dominio/entidades.py,
matching_estado.py) ni el esquema SQLite: F4.1 se apoya en lo que ya existe
(guardar_match, listar_matches_por_entidad, la máquina de estados de F3).

1. Puerto de notificación — nuevo módulo `src/ongs_ai/servicios/notificacion.py`:
   Protocol `Notificador` con `notificar_propuesta(entidad, convocatoria,
   match) -> None`. Añade `NotificadorStub` (registra las llamadas en una
   lista para los tests). El email real NO se implementa aquí (F4.2).

2. Orquestador — nuevo módulo `src/ongs_ai/servicios/propuestas.py`:
   función `detectar_y_proponer(entidades, convocatorias, fecha_referencia,
   almacen, notificador, *, generador_ids, reloj, generador_explicacion=None)
   -> ResumenPropuestas`. NO es dominio puro (compone puertos), como
   `adapters/ingesta/servicio.py`. Algoritmo POR ENTIDAD:
   a. Cargar `almacen.listar_matches_por_entidad(entidad_id)` e indexar en
      memoria por `convocatoria_id`.
   b. PRE-PUERTA: recorrer SOLO las convocatorias en estado_ingesta
      VERIFICADA y con plazo abierto (`plazos.fecha_cierre` no None y
      >= fecha_referencia). Las demás se ignoran (ni se evalúan ni se
      persisten). Cuenta cuántas se saltan.
   c. Para cada convocatoria que pasa la pre-puerta:
      - `resultado = evaluar_elegibilidad(entidad, convocatoria, fecha_referencia)`.
      - localizar el match ACTIVO de la pareja (estado_actual NO en
        {DESCARTADA, PRESENTADA}) y si existe alguno TERMINAL.
      - CON activo:
          * actualizar su `resultado_elegibilidad_dura` (dataclasses.replace).
          * si el activo está en DETECTADA y `resultado.elegible` →
            `transicionar(detectada→propuesta, actor=SISTEMA, motivo=...)`,
            rellenar `explicacion_ia` si elegible y hay generador (mismo
            patrón que detectar_matches: try/except, texto o None), y NOTIFICAR.
          * si ya está en PROPUESTA (ya avisado) y sigue elegible → NO re-avisar.
          * regresión (elegible→no elegible en un match ya propuesto/avanzado)
            → solo actualizar resultado, NO retroceder de estado, NO avisar.
          * `almacen.guardar_match(match)` (upsert por match_id).
      - SIN activo pero CON terminal → no hacer nada (respeta la conclusión).
      - SIN match para la pareja → `crear_match` (detectada) + set
        `resultado_elegibilidad_dura`; si elegible → transicionar a propuesta
        + explicacion_ia + NOTIFICAR; `guardar_match`.
   d. La notificación SIEMPRE envuelta en try/except: si el notificador lanza,
      registra (logging.warning) y sigue — nunca rompe la persistencia ni el
      bucle (regla de oro: degrada limpio).
   `ResumenPropuestas` (dataclass frozen): nuevas_propuestas, propuestas_
   sobrevenidas, no_elegibles_persistidas, ya_existentes_sin_cambio,
   saltadas_pre_puerta (documenta cada contador).

3. Ids/reloj SIEMPRE inyectados (como F3). NADA de datetime.now()/uuid4()
   implícitos. Nada hardcodeado de enfermedad/entidad.

4. Tests (`tests/test_propuestas.py`), parametrizados sobre AMBOS almacenes
   (memoria y sqlite ':memory:') como el resto de tests de persistencia,
   herméticos y sin red:
   - convocatoria elegible en primera detección → match nuevo en PROPUESTA +
     el NotificadorStub registra 1 aviso.
   - convocatoria no elegible → match nuevo en DETECTADA, persistido, SIN aviso.
   - pre-puerta: convocatoria no VERIFICADA o con plazo cerrado/None → NO
     genera match (y cuenta en saltadas_pre_puerta).
   - segunda pasada idempotente: re-ejecutar no duplica; un elegible ya en
     PROPUESTA no re-avisa; un no elegible sin cambios no crea filas nuevas.
   - ELEGIBILIDAD SOBREVENIDA: match no elegible en DETECTADA; en la 2ª pasada
     la convocatoria/entidad cambian a elegible → transiciona a PROPUESTA +
     avisa (como propuesta nueva).
   - RESPETO A TERMINAL: pareja con match DESCARTADA → una nueva detección NO
     crea match nuevo ni avisa. (idem PRESENTADA.)
   - notificador que LANZA → degrada limpio: el match igualmente se persiste,
     no se propaga excepción, el bucle sigue con las demás.
   - reloj/ids inyectados verificables.

5. `python -m pytest -q` VERDE y HERMÉTICO. Chequeo sintáctico
   (`ast.parse`) de cada fichero tocado. Si `src/ongs_ai/servicios/` no
   existe, créalo con su `__init__.py`.

Incluye en tu commit los cambios de engineering/06_* y engineering/ADR-004-*
que ya estén en el working tree, tal cual estén.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add (ni .env, ni var/, ni investigacion/asociaciones*),
`git push` al terminar.
```

## 7. Preguntas abiertas (con default) para más adelante

- Afinar el filtro de relevancia de la ingesta (qué `tipoBeneficiario`/texto define
  "tercer sector") — depende de la verificación del parámetro con el smoke (pendiente).
  Default: cobertura amplia, se estrecha con datos.
- ¿Pre-filtro geográfico antes de persistir no-elegibles por ámbito de otra CCAA? Default:
  NO por ahora (persistir con motivo; el panel filtra); reconsiderar si el volumen molesta.
- Cadencia de la re-detección (cada ingesta / diaria) → decisión de F4.2 / esqueleto de app.
