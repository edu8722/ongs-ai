# ADR-007 — Convocatorias recurrentes esperadas (el corazón proactivo)

- **Estado:** PROPUESTA (pendiente de aprobación del operador) — 2026-07-21.
- **Contexto de fase:** F1 ✔ · ADR-002 ✔ · F3 ✔ · F4 (ADR-004) ✔ · ADR-005 (web+auth) ✔ ·
  ADR-006 (consola/prospectos/scoring) ✔ · PROMPT-023 (honestidad ingesta: `abierto`,
  ámbito NUTS1, concesión directa) ✔ · PROMPT-024 (batería de búsquedas dirigidas contra
  la BDNS a partir del histórico real) ✔ · PROMPT-025 ✔. Este ADR abre el **paso
  proactivo por adelantado**: no esperar a que una convocatoria aparezca para avisar, sino
  decir *"el año pasado recibiste estas ayudas; sus ediciones anuales suelen salir en tal
  ventana; están **pendientes de publicar** y te avisaré cuando salgan"*.
- **Relación:** NO modifica el contrato congelado (Entidad/Convocatoria/Actividad/Match,
  ADR-001/ADR-002), NI el guardarraíl binario de elegibilidad (`dominio/elegibilidad.py`),
  NI la máquina de estados de Match (`dominio/matching_estado.py`), NI el flujo de
  detección/propuesta/aviso de ADR-004. Añade, **fuera del contrato congelado** y de forma
  aditiva: (a) un paquete nuevo `proactivo/` con dos modelos derivados
  (`HistorialConcesion`, `ConvocatoriaEsperada`) y su ciclo de estados propio; (b) un
  adapter de ingesta contra `/concesiones/busqueda` de la BDNS; (c) un servicio de
  derivación determinista historial→esperadas; (d) el enganche de la esperada con la
  ingesta ya existente (PROMPT-024) y con el `Notificador` de ADR-004.
- **Documento SOLO decisión** — cero código de producción; el código lo entrega
  F-proactivo.1 (§9).
- **Origen de la petición (operador, literal, 2026-07-22):** *"en base al año pasado
  debería informar de a qué convocatorias se podrían intentar presentar y que tengan un
  estado de pendiente de publicar o algo así y en base a las fechas de otros años marque
  en torno a qué fecha debería salir la convocatoria"*. Evidencia real aportada: histórico
  de concesiones de Aniridia 2022-2024 (15 ayudas, la mayoría ediciones anuales
  recurrentes — IRPF 0,7% estatal y CAM, mantenimiento de servicios CAM, ayuda mutua
  Sanidad CAM, fomento del asociacionismo municipal, diputaciones). El histórico vive en
  `investigacion/` (**fuera de git**); aquí solo se referencian sus **patrones**, nunca sus
  datos.

---

## 1. Contexto y problema

Toda la plataforma es **reactiva**: la ingesta (PROMPT-018/024) trae convocatorias
**ya publicadas**, el guardarraíl las casa y ADR-004 avisa. El operador ha detectado el
límite con datos reales: casi ninguna de las 15 ayudas del histórico de Aniridia aparecía
en la base cuando se buscaba de forma genérica, porque **muchas son ediciones anuales de
la misma convocatoria** y, entre edición y edición, simplemente **no existe todavía** una
convocatoria abierta que ingerir. La asociación, sin embargo, **sabe** —porque la recibió
el año pasado— que esa ayuda volverá a salir; el valor de un "técnico de subvenciones" es
justamente **no perder la ventana** de una ayuda recurrente.

El corazón proactivo, entonces, es: partir del **historial público de concesiones** de la
entidad (lo que ya recibió), reconocer las que son **ediciones anuales recurrentes**,
estimar **con honestidad** en torno a qué fecha suele salir la próxima edición, marcarla
como **esperada / pendiente de publicar**, y **enlazarla** con la convocatoria real en
cuanto la ingesta la traiga, avisando por los canales que ya existen.

Cuatro problemas a resolver, en orden de riesgo:

1. **Honestidad de la estimación (el riesgo real de este ADR).** "Suele salir por mayo"
   es útil; "saldrá el 20 de mayo de 2027" es una promesa que no podemos sostener. Mismo
   filo que el importe **techo teórico** de ADR-006 §2.5 y que el rechazo a la
   "probabilidad de concesión": la estimación de fecha es **siempre un rango/mes derivado
   de ediciones previas**, jamás una fecha exacta, y **degrada** cuando los datos son
   pocos o irregulares.
2. **Que la esperada no contamine el contrato congelado ni el matching real.** Una
   `ConvocatoriaEsperada` **no es** una `Convocatoria` (no tiene requisitos estructurados
   verificados, ni `estado_ingesta`, ni ámbito derivado de la fuente). Meterla como
   `Convocatoria` fantasma con campos inventados rompería el contrato, el guardarraíl y los
   tests anti-hardcoding. Necesita un hogar **fuera del contrato**, como el `Prospecto` de
   ADR-006.
3. **La fuente del historial.** Hay que verificar contra la API **real** de la BDNS si
   existe un filtro server-side por beneficiario utilizable, o decidir la alternativa. §2.
4. **Aislamiento por tenant.** El historial y las esperadas son **por entidad** (cuelgan
   de un `entidad_id`, se consultan por el NIF **verificado** de la entidad). Deben quedar
   bajo la misma garantía anti-fuga cross-tenant que `Match` (ADR-001 §4.2).

Usuario de esta capacidad: **la entidad captada** (tenant), no el prospecto. Surge en el
**panel** (ADR-005) y reutiliza el **aviso** de ADR-004. Un `Prospecto` (ADR-006) **no
tiene NIF** (§2.3 de aquel ADR: "Lo que un Prospecto NUNCA tiene: nif, …"), luego no puede
consultarse su historial: el proactivo es, por construcción, una capacidad **de entidad
captada** (§3.9). Se documenta como frontera, no como omisión.

---

## 2. Verificación contra la API real de la BDNS (fuente del historial)

Método idéntico a ADR-001..006: peticiones manuales a la API pública, documentadas aquí
(ejecutadas **2026-07-21** contra `https://www.infosubvenciones.es/bdnstrans/api`). El
arquitecto ya había comprobado que `descripcionBeneficiario` **no** filtra; esta sesión lo
confirma **y** encuentra el filtro utilizable.

### 2.1 El endpoint de concesiones existe y es masivo

`GET /concesiones/busqueda?page=0&pageSize=1` → HTTP 200, `totalElements = 28 321 349`
(~28,3 M). Cada registro (`content[]`) trae, verificado sobre datos vivos:

| Campo BDNS | Ejemplo real | Uso en nuestro modelo |
|---|---|---|
| `beneficiario` | `"P0704500H AJUNTAMENT DE PUIGPUNYENT"` | NIF + nombre concatenados (se separa al parsear). |
| `fechaConcesion` | `"2026-07-20"` | Fecha del **acto de concesión** (posterior a la resolución). |
| `importe` | `155000` | Euros (posible decimal) → céntimos int (regla de oro). |
| `numeroConvocatoria` | `"864272"` | **Código BDNS de la convocatoria** (ver §2.4). |
| `idConvocatoria` | `1065833` | Id interno BDNS (trazabilidad). |
| `convocatoria` | `"convocatoria pública de subvenciones para el diseño de refugios…"` | Título de la edición (base del fingerprint de serie, §3.5). |
| `nivel1` / `nivel2` / `nivel3` | `"AUTONOMICA"` / `"ILLES BALEARS"` / `"DIRECCIÓN GENERAL…"` | Órgano convocante (parte del fingerprint de serie). |

### 2.2 `descripcionBeneficiario` NO filtra (confirmado)

`…/busqueda?descripcionBeneficiario=ANIRIDIA` → `totalElements = 28 354 645`, **idéntico**
al baseline sin parámetro. Spring ignora el parámetro y devuelve los 28 M. Inutilizable
como filtro por entidad (confirma el hallazgo previo del arquitecto).

### 2.3 `nifCif` SÍ filtra server-side (hallazgo que decide la fuente)

| Petición | `totalElements` | Lectura |
|---|---|---|
| baseline | 28 354 645 | — |
| `nifCif=P0704500H` (NIF real de un beneficiario existente) | **76** | Filtra a las concesiones de ese NIF. |
| `nifCif=G12345678` (NIF inexistente) | **0** | El parámetro **se reconoce y filtra** (no lo ignora: si lo ignorase daría 28 M). |
| `nifCif=P0704500H&fechaDesde=01/01/2024&fechaHasta=31/12/2024` | **22** | `fechaDesde`/`fechaHasta` (formato `dd/mm/yyyy`) **también** filtran, combinables. |

**Conclusión:** existe un filtro server-side utilizable por NIF. La fuente del historial es
`/concesiones/busqueda?nifCif=<NIF de la entidad>` (opcionalmente acotado por rango de
fechas). No hace falta el fallback caro de "traer todo y filtrar en cliente". El NIF es un
dato **verificado** que la `Entidad` ya tiene (`Entidad.nif`, ADR-001 §1.1) — no se inventa
ni se hardcodea.

### 2.4 Enlace concesión ↔ convocatoria ↔ id de nuestra ingesta

Verificado que el `numeroConvocatoria` de una concesión coincide con el `codigoBDNS` del
detalle de esa convocatoria: `GET /convocatorias?numConv=864272` → `codigoBDNS = "864272"`.
Y la ingesta (`adapters/ingesta/bdns.py::mapear_convocatoria`) construye
`convocatoria_id = f"bdns-{codigoBDNS}"`. Luego una concesión pasada apunta, de forma
determinista, a `bdns-<numeroConvocatoria>`.

**Matiz crítico de honestidad:** cada **edición anual** de una convocatoria recurrente
tiene un `codigoBDNS` **distinto** (IRPF 2024, 2025, 2026 son códigos diferentes). Por
tanto el enlace esperada→edición-real **NO puede hacerse por código exacto** (aún no existe
el código de la edición futura): se hace por **serie** (fingerprint determinista de órgano
+ título normalizado, §3.5). El código exacto solo sirve para enlazar hacia atrás (una
concesión con su convocatoria histórica) y como clave de dedupe cuando la edición real
por fin se ingiere.

### 2.5 Fallback documentado (por si `nifCif` dejara de filtrar)

Si en el futuro la BDNS retirase o rompiese `nifCif`, la alternativa es
**búsqueda por convocatoria conocida + filtrado en cliente**: se verificó que
`/concesiones/busqueda?numeroConvocatoria=864272` → `totalElements = 2` (filtra por
convocatoria). Conociendo los `numeroConvocatoria` de las ediciones pasadas de la serie, se
recuperan sus concesiones y se filtra el beneficiario en cliente por prefijo de NIF sobre
`beneficiario`. Es más caro (una consulta por convocatoria conocida) y solo cubre series ya
conocidas, por eso es fallback, no diseño principal. Se documenta para no re-investigar si
hace falta.

---

## 3. Decisión

### 3.1 Dónde viven los modelos: paquete `proactivo/`, fuera del contrato congelado

Se introduce un **paquete nuevo `src/ongs_ai/proactivo/`**, hermano de `dominio/`,
`prospeccion/`, `servicios/`, `adapters/`, `web/` — misma razón estructural que el
`prospeccion/` de ADR-006 §2.3: que "esto **NO** es el contrato congelado" sea evidente por
la estructura de ficheros, no por un comentario.

- `proactivo/modelo.py` — dataclasses frozen `HistorialConcesion` y `ConvocatoriaEsperada`
  + enum `EstadoEsperada`.
- `proactivo/puertos.py` — puertos `RepositorioHistorialConcesiones` y
  `RepositorioConvocatoriasEsperadas` (Protocol). **No** se meten en `dominio/puertos.py`
  (que solo conoce Entidad/Convocatoria/Match): son modelos derivados, no contrato.
- `proactivo/derivacion.py` — servicio **determinista** historial→esperadas (§3.5). Sin
  LLM (la IA no participa en el número ni en la fecha; regla de oro).

**Por qué fuera del contrato y no ampliación de éste (como se preguntaba):** `Historial`
y `Esperada` son datos **derivados y auxiliares**, no las cuatro entidades núcleo. Meterlos
en el contrato congelado obligaría a un ADR nuevo por cada ajuste del algoritmo de ventana
o de los niveles de confianza (que son calibrables, como los pesos del score de ADR-006).
Manteniéndolos fuera, el contrato congelado sigue mínimo y estable, y estos modelos evolucionan
como datos. Ninguno modifica Entidad/Convocatoria/Actividad/Match.

### 3.2 `HistorialConcesion` — una ayuda pasada de una entidad (hecho)

Registro **inmutable** de una concesión pública recibida por una entidad, mapeado 1:1 desde
un registro de `/concesiones/busqueda`. Es **hecho**, no estimación.

| Campo | Tipo | Notas |
|---|---|---|
| `historial_id` | id opaco | Clave. Nunca por nombre. |
| `entidad_id` | str (FK a Entidad) | **Aislamiento por tenant** — todo historial cuelga de una entidad. |
| `cod_concesion` | str | `codConcesion` de la BDNS (dedupe natural de la concesión). |
| `nif_beneficiario` | str | Parseado del prefijo de `beneficiario`; debe coincidir con `Entidad.nif`. |
| `fecha_concesion` | date | `fechaConcesion`. |
| `importe_centimos` | int \| None | Euros→céntimos (Decimal, como `bdns.py`); `None` si ausente. Nunca float. |
| `cod_bdns_convocatoria` | str | `numeroConvocatoria` (= `codigoBDNS`, §2.4). |
| `titulo_convocatoria` | str | `convocatoria` (título de esa edición). |
| `organo_nivel1/2/3` | str \| None | `nivel1/2/3` (parte del fingerprint de serie). |
| `es_concesion_directa` | bool | True si la convocatoria de origen fue no-concurrencia (§3.7). |
| `serie_fingerprint` | str | Clave determinista de agrupación (§3.5), calculada, no de la BDNS. |
| `capturado_en` | datetime | Metadato (reloj inyectado). |

Mapeo con **degradación limpia** (mismo principio que `bdns.py` y el importador de
prospectos): registro sin `beneficiario` parseable o sin `numeroConvocatoria` → se descarta
y se **cuenta** (`descartados`), nunca se inventa; campo ausente → `None` y se cuenta, el
registro entra igual.

### 3.3 `ConvocatoriaEsperada` — edición anual prevista (estimación honesta)

Derivada de un grupo de `HistorialConcesion` de **la misma serie**. Es **estimación**, y su
forma lo grita: ventana en meses, nunca fecha exacta; confianza explícita; ciclo propio.

| Campo | Tipo | Notas |
|---|---|---|
| `esperada_id` | id opaco | Clave. |
| `entidad_id` | str (FK) | **Por entidad** (§3.9). |
| `serie_fingerprint` | str | La serie que la origina (agrupa el historial). |
| `titulo_representativo` | str | Título de la última edición observada (para mostrar). |
| `organo` | str \| None | Órgano convocante (nivel1/2/3 legibles). |
| `ediciones_previas` | int | Nº de ediciones históricas que la sustentan (≥1). |
| `anios_observados` | tuple[int, ...] | Años de las ediciones previas (trazabilidad de la ventana). |
| `ventana_mes_inicio` | int (1-12) | Mes inicial de la ventana estimada de **apertura**. |
| `ventana_mes_fin` | int (1-12) | Mes final; == inicio si todas las ediciones caen en el mismo mes. |
| `anio_esperado` | int | Año de la próxima edición (derivado de `fecha_referencia`, §3.5). |
| `confianza` | enum `Confianza` (`BAJA`/`MEDIA`/`ALTA`) | §3.5. |
| `accionable` | bool | False si la serie es de concesión directa (§3.7). |
| `estado` | enum `EstadoEsperada` | `ESPERADA` → `PUBLICADA_ENLAZADA` \| `NO_APARECIDA`. |
| `convocatoria_id_enlazada` | str \| None | Se rellena al enlazar con la edición real (§3.6). |
| `creado_en` / `actualizado_en` | datetime | Reloj inyectado. |

**Ciclo de estados propio** (independiente de la máquina de Match, no la toca):

```
ESPERADA ──(la ingesta trae la edición real y se enlaza)──► PUBLICADA_ENLAZADA   [terminal]
ESPERADA ──(pasa la ventana + margen sin aparecer)────────► NO_APARECIDA          [terminal]
```

`ESPERADA` es el estado vivo; los dos terminales cierran el ciclo de esa edición-año. La
edición del año siguiente es una **esperada nueva** (nuevo `anio_esperado`), como el
reintento de un Match descartado es un Match nuevo (ADR-001 §1.4) — no se "resucita" una
terminal.

### 3.4 Adapter de concesiones y su servicio de captura

- **`adapters/ingesta/bdns_concesiones.py`** — `FuenteConcesionesBDNS`, análogo a
  `FuenteBDNS`: usa el mismo `TransporteHTTP` inyectable (`adapters/ingesta/base.py`), la
  misma paginación y la misma **degradación limpia de transporte** (un fallo se registra y
  se corta/salta, nunca propaga al dominio). Método `buscar_por_nif(nif, *, fecha_desde,
  fecha_hasta) -> Iterator[HistorialConcesion]`, aplicando `nifCif` (+ fechas) como filtros
  de servidor (§2.3) y el mapeo de §3.2. La red va **apagada en tests** (fixtures JSON
  grabadas, como el resto de ingesta); solo el script manual usa `TransporteURLLib`.
- **`servicios/recurrentes.py`** (compone puertos, no dominio puro): orquesta
  captura→persistencia de historial→derivación de esperadas→persistencia de esperadas para
  una entidad, con ids y reloj **inyectados** (como ADR-004 §5). Dedupe de historial por
  `cod_concesion`; upsert de esperadas por `(entidad_id, serie_fingerprint, anio_esperado)`.
- Se **reutiliza** la batería de PROMPT-024 (`busquedas_dirigidas.py`) tal cual: no cambia.
  El proactivo es complementario — la batería mejora la **cobertura de lo publicado**; el
  proactivo cubre lo **aún no publicado** que la entidad ya recibió.

### 3.5 Derivación determinista de series y ventana (honestidad, como el techo teórico)

Todo lo que sigue es **determinista, sin LLM, testeable** (mismo criterio que
`_MAPA_FORMA_JURIDICA` de ADR-002 y el mapeo palabra-clave de ADR-006 §2.5).

**Fingerprint de serie** (`serie_fingerprint`): clave estable que agrupa ediciones del
mismo programa a lo largo de los años. Construcción determinista:
`normalizar_texto_comparacion(organo_nivel1|nivel2|nivel3)` + `"::"` +
`normalizar_texto_comparacion(titulo)` **tras eliminar tokens de año/edición** (años de 4
dígitos `20\d\d`, ordinales romanos de edición, y números sueltos que denoten ejercicio),
con un helper cerrado y documentado. Se reutiliza `normalizar_texto_comparacion` del
dominio (nunca se reimplementa). **Degradación conservadora:** si dos ediciones no agrupan
(título muy cambiante entre años), en el peor caso **no** se deriva la esperada (un
**miss**), jamás una esperada falsa. Se degrada hacia "faltó avisar", nunca hacia "avisé de
algo que no existe" — la IA no interviene para "adivinar" la equivalencia (rechazado igual
que en ADR-002 §3).

**Cuántas ediciones exigen derivar una esperada** (la pregunta del operador):

- **1 edición previa** → se **crea** una esperada con `confianza = BAJA`, ventana = el mes
  de esa única edición, etiquetada explícitamente *"una sola edición previa — sin patrón
  confirmado"*. Honra la petición literal del operador ("en base al año pasado") sin fingir
  regularidad que un solo punto no puede sostener.
- **≥2 ediciones** → esperada con ventana = **rango [mes mínimo, mes máximo]** de las
  aperturas observadas (p. ej. dos ediciones en mayo y junio → *"mayo–junio"*; ambas en
  mayo → *"en torno a mayo"*). `confianza`:
  - `ALTA` — ≥3 ediciones y meses agrupados (rango ≤ 2 meses).
  - `MEDIA` — 2 ediciones, o ≥3 con rango de 3 meses.
  - `BAJA` — meses **dispersos** (rango > 3 meses): la ventana se **amplía** al rango
    observado y se etiqueta *"irregular"* — nunca se estrecha a un mes que los datos no
    respaldan. Ésta es la degradación con datos irregulares que pide el requisito 3.

**Qué fecha define la ventana** (matiz de honestidad, requisito 3): el operador quiere "en
torno a qué fecha debería **salir** la convocatoria" — es la fecha de **apertura**
(`fechaInicioSolicitud` → `plazos.fecha_apertura`), no la de concesión (`fechaConcesion`,
que ocurre meses **después** de resolver). Por tanto la ventana se deriva de la
**apertura** de las ediciones previas, obtenida del detalle de cada convocatoria histórica
(`/convocatorias?numConv=<cod>`, ya mapeado por `bdns.py`). Si la apertura no está
disponible para una edición, se usa el **mes de `fechaConcesion` como proxy tosco**,
**marcado como tal** (baja la confianza), nunca presentado como fecha de salida real.

**Año esperado** (`anio_esperado`): determinista desde la `fecha_referencia` **inyectada**
(regla de oro: el dominio/servicio no lee un "ahora" implícito) — el primer año posterior a
la última edición observada cuya ventana aún no haya pasado respecto a `fecha_referencia`.
Nunca un `datetime.now()` dentro del cálculo.

### 3.6 Relación con Match: una esperada NUNCA crea un Match

Se **adopta la propuesta conservadora** del operador. Una `ConvocatoriaEsperada` **jamás**
genera un `Match` ni entra en el flujo de `evaluar_elegibilidad`/`detectar_y_proponer`
(ADR-004): no tiene requisitos estructurados verificados contra los que evaluar, y fabricar
un Match sobre una convocatoria inexistente contaminaría el contrato y el panel. La
esperada vive su ciclo propio (§3.3) **en paralelo** al mundo de Match.

El enlace es en un solo sentido y ocurre **cuando la edición real se publica** (la ingesta
de PROMPT-024 la traerá): en el servicio de recurrentes, tras cada ingesta, se comparan las
convocatorias recién ingeridas contra las esperadas `ESPERADA` de la entidad por
`serie_fingerprint` (mismo fingerprint determinista aplicado al título/órgano de la
convocatoria nueva). Al primer match de serie:

1. La esperada transiciona `ESPERADA → PUBLICADA_ENLAZADA`, guardando
   `convocatoria_id_enlazada`.
2. A partir de ahí **el mundo normal hace el resto**: esa convocatoria real, ya en el
   catálogo, pasa por `detectar_y_proponer` (ADR-004) como cualquier otra — guardarraíl
   determinista, Match, y aviso de propuesta si resulta elegible. **No** hay un camino de
   elegibilidad paralelo para esperadas: la esperada solo **anticipa y enlaza**; la
   decisión sigue siendo del guardarraíl intacto.

Esto mantiene una sola fuente de verdad para la elegibilidad (el guardarraíl de F3) y
evita duplicar lógica de matching en la capa proactiva.

### 3.7 Concesión directa (nominativa) vs concurrencia — accionable o no

PROMPT-023 ya distingue determinísticamente las convocatorias de **concesión directa / no
concurrencia** (campo `tipoConvocatoria` con "concesión directa", motivo
`MOTIVO_CONCESION_DIRECTA`): esas **no se solicitan** en concurrencia competitiva, se
asignan. Aplicado al proactivo: una serie cuyas ediciones fueron de **concesión directa** se
registra como `HistorialConcesion` (hecho: la recibió) pero su esperada se marca
`accionable = False` — se muestra como *"recibida el año pasado; adjudicación directa/
nominativa, no se solicita en concurrencia"*, **sin** sugerir "preséntate". Sugerir
presentarse a una ayuda que no se solicita sería inventar una oportunidad inexistente
(regla de oro). El dato `es_concesion_directa` se deriva del mismo detalle que ya consulta
`bdns.py`, reutilizando su determinismo; ausente → se asume concurrencia (conservador:
accionable, pero nunca al revés).

### 3.8 Avisos: publicación (email+panel) y ventana próxima (panel)

Se reutiliza el `Notificador` (Protocol) de ADR-004 §2.6 / `servicios/notificacion.py` y su
política de canales (§2.5 de aquel ADR: **email solo para oportunidades accionables reales;
panel para todo**). Dos momentos:

1. **Publicación de la edición real de una esperada** (el aviso fuerte, factual). Cuando
   §3.6 enlaza esperada→convocatoria, la convocatoria entra al flujo normal de ADR-004; si
   resulta elegible, el aviso de propuesta sale **por email+panel como siempre**,
   **enriquecido** con el contexto de la esperada (*"la ayuda que recibiste en 2024 ya está
   abierta"*). No se crea un canal nuevo ni se duplica el aviso: se **añade contexto** al
   aviso de propuesta existente. Si no es elegible, panel con su motivo (como ADR-004).
2. **"Se acerca la ventana estimada"** (el aviso suave, estimado) — **decisión: SÍ, pero
   solo en panel y acotado**. Cuando `fecha_referencia` entra en la ventana estimada de una
   esperada `ESPERADA` aún no publicada, se muestra en el panel un aviso hedged (*"suele
   publicarse en mayo–junio; aún no la hemos detectado"*), **una sola vez por ventana**, y
   **solo** para `confianza` MEDIA/ALTA y esperadas `accionable=True` (no se molesta con
   corazonadas de una sola edición ni con nominativas). **No** sale por email: el email
   queda reservado, como en ADR-004, a oportunidades **reales y accionables**, para no
   erosionar su valor con estimaciones. Este aviso es aditivo y su cadencia exacta la
   afina F-proactivo (calibrable, no es contrato).
3. **`NO_APARECIDA`** — si pasa la ventana + un margen configurable sin que la edición
   aparezca, la esperada transiciona a `NO_APARECIDA` y se informa **en panel** (*"la ayuda
   esperada no ha aparecido en su ventana habitual — conviene revisarla manualmente"*).
   Valioso: una recurrente que deja de convocarse es información, no ruido.

### 3.9 Tenancy y PII

- **Por entidad, sin excepción.** `HistorialConcesion` y `ConvocatoriaEsperada` llevan
  `entidad_id` explícito y son la única vía de acceso — exactamente como `Match` (ADR-001
  §4.2, regla de oro de aislamiento). El **test anti-fuga cross-tenant** se **amplía** para
  cubrirlos: una consulta con `entidad_id=A` **jamás** devuelve historial ni esperadas de
  `entidad_id=B`. Los puertos nuevos exigen `entidad_id` en toda lectura/escritura.
- **Esperada es por entidad, NO global** (la pregunta del requisito 2). Lo "esperado"
  depende de lo que **esa** entidad recibió; una esperada es intrínsecamente relativa a su
  historial. Un catálogo **global** de "ediciones recurrentes de toda la BDNS" es otra cosa
  (mucho mayor, exigiría afirmar recurrencia serie a serie sobre 28 M de concesiones sin la
  evidencia por-entidad que aquí la sustenta) y no es lo que el operador pide — se descarta
  como sobre-ingeniería (§5), documentado en §4.
- **PII.** El NIF con el que se consulta es el **propio** de la entidad (`Entidad.nif`, dato
  verificado del tenant), nunca un NIF ajeno ni inventado. Las concesiones de la BDNS son
  **públicas** (SNPSAP), luego el historial no introduce PII nueva más allá del vínculo
  "esta entidad recibió esta ayuda", que **es** dato de tenant y por tanto sujeto al
  aislamiento anterior. El adapter **nunca** consulta un NIF que no sea el de una entidad
  captada; el `Prospecto` (sin NIF) **no** tiene historial (§1, frontera). Superficies
  públicas sin fugas: el panel del tenant muestra solo su historial/esperadas; la consola
  del operador (ADR-006, lectura global, solo localhost) puede verlo agregado, nunca un
  tenant al otro.

### 3.10 Resumen de decisión

Fuente = `/concesiones/busqueda?nifCif=<NIF de la entidad>` (**verificado que filtra**,
§2.3), con el NIF verificado del tenant. Modelos derivados `HistorialConcesion` (hecho) y
`ConvocatoriaEsperada` (estimación) **fuera del contrato congelado**, en `proactivo/`.
Estimación de fecha **siempre rango/mes** derivado de las **aperturas** de ediciones
previas, con confianza explícita y degradación honesta con datos escasos/irregulares — 1
edición basta para una esperada de confianza BAJA, ≥2 para una ventana fiable. La esperada
**nunca crea Match**: al publicarse la edición real se enlaza y el guardarraíl intacto de F3
hace el resto. Concesión directa → historial sí, "preséntate" no. Avisos por los canales de
ADR-004: publicación por email+panel (enriqueciendo el aviso existente), ventana próxima y
no-aparición solo en panel. Todo **por entidad**, bajo el mismo anti-fuga que `Match`.

---

## 4. Alternativas consideradas y descartadas

- **Filtrar el historial por `descripcionBeneficiario` (o por nombre).** Descartada:
  verificado que **no filtra** (§2.2, 28 M de registros). El nombre, además, es frágil
  (variantes, mayúsculas). `nifCif` sobre el NIF verificado es la clave estable.
- **Traer toda la BDNS de concesiones y filtrar en cliente por NIF.** Descartada como
  diseño principal: 28 M de registros por entidad es inviable. Solo sobrevive como
  **fallback por convocatoria conocida** (§2.5) si `nifCif` se rompiera.
- **Modelar la esperada como una `Convocatoria` "fantasma" en el catálogo** (estado nuevo
  tipo `PENDIENTE_DE_PUBLICAR`). Descartada: rompería el **contrato congelado** (añadir un
  valor a `EstadoIngesta` es ADR de contrato), contaminaría el matching real y el panel con
  convocatorias sin requisitos verificados, y forzaría al guardarraíl a evaluar algo que no
  existe. El paquete `proactivo/` fuera de contrato lo evita, igual que `Prospecto` en
  ADR-006.
- **Ampliar el contrato congelado con `HistorialConcesion`/`ConvocatoriaEsperada`.**
  Descartada: son datos **derivados y calibrables** (algoritmo de ventana, niveles de
  confianza), no las cuatro entidades núcleo; congelarlos obligaría a un ADR por cada ajuste
  del algoritmo. Fuera de contrato evolucionan como datos (§3.1).
- **Que una esperada genere directamente un Match "pre-elegible".** Descartada (propuesta
  conservadora del operador, adoptada §3.6): duplicaría la lógica de elegibilidad fuera del
  guardarraíl único de F3 y crearía Matches contra convocatorias inexistentes. La esperada
  solo anticipa y enlaza; el guardarraíl intacto decide cuando la convocatoria es real.
- **Estimar una fecha exacta de publicación** (p. ej. "media de las fechas previas ± N
  días"). Descartada por honestidad, mismo filo que el techo teórico de ADR-006 y el
  rechazo de la probabilidad de concesión: los datos administrativos no soportan precisión
  diaria; solo un **mes/rango** es defendible. Una fecha exacta sería una promesa
  insostenible.
- **Usar IA para agrupar ediciones en series** ("pregúntale al modelo si estas dos
  convocatorias son la misma de años distintos"). Descartada por la regla de oro (ya
  argumentada en ADR-001 §3.2 y ADR-002 §3): reintroduce no-determinismo en una decisión
  que dispara avisos al usuario. El fingerprint determinista degrada a **miss** (no avisar),
  nunca a un enlace falso; la IA, como mucho, podría explicar en prosa un enlace ya hecho
  (capa F3 existente), nunca producirlo.
- **Catálogo global de recurrentes de toda la BDNS.** Descartada como sobre-ingeniería
  (§3.9, §5): no es lo que el operador pide y exigiría afirmar recurrencia sobre 28 M de
  concesiones sin la evidencia por-entidad que aquí la sustenta.
- **Estimar la ventana desde `fechaConcesion` (la única fecha que trae la concesión).**
  Descartada como fuente principal: la concesión ocurre **después** de resolver, no cuando
  la convocatoria **sale**; usarla respondería a la pregunta equivocada. Se deriva de la
  **apertura** de la convocatoria histórica; `fechaConcesion` solo como proxy tosco y
  marcado cuando la apertura falte (§3.5).

---

## 5. Qué queda fuera (anti-sobre-ingeniería)

- **Sin predicción de importe.** El historial muestra el importe pasado como **hecho**; la
  esperada **no** predice cuánto concederán (mismo criterio que ADR-006 §2.5).
- **Sin probabilidad de concesión.** Rechazada ya en ADR-006; aquí tampoco existe.
- **Sin scraping de bases reguladoras** ni de webs de convocantes: solo BDNS estructurada
  (`/concesiones` y `/convocatorias`) en esta fase. Los adapters privados (FEDER, la Caixa,
  ONCE — R1) siguen fuera de alcance.
- **Sin catálogo global de recurrentes** (§3.9): solo por entidad captada.
- **Sin auto-Match desde esperada** (§3.6).
- **Sin fecha exacta** (§3.5): siempre rango/mes.
- **Sin proactivo para prospectos** (no tienen NIF; §1/§3.9): solo entidades captadas.
- **Cadencia de la re-derivación** (cada ingesta / semanal) se decide en F-proactivo con el
  esqueleto de scheduling; por defecto, tras cada pasada de ingesta de la entidad.

---

## 6. Consecuencias

### 6.1 Tests (anti-fuga ampliado; el proactivo gana los suyos) — herméticos

- **Anti-fuga cross-tenant AMPLIADO y sin debilitar** (regla de oro): además de `Match`,
  se cubre que `entidad_id=A` nunca lee `HistorialConcesion` ni `ConvocatoriaEsperada` de
  `entidad_id=B`. Los tests existentes siguen verdes tal cual.
- **Adapter de concesiones** (fixtures JSON grabadas, **jamás** red ni el histórico real de
  `investigacion/`): `nifCif` se pasa como filtro; registro sin beneficiario/convocatoria →
  descartado y contado; campo ausente → `None` y contado; fallo de transporte → degrada
  limpio (no propaga). Fixture derivada de la **forma** real verificada en §2, con NIF y
  datos **sintéticos**.
- **Derivación determinista**: mismo historial → mismas esperadas siempre; 1 edición →
  confianza BAJA con etiqueta; ≥2 en meses agrupados → ventana [min,max] y confianza
  MEDIA/ALTA; meses dispersos → ventana ampliada + BAJA "irregular"; concesión directa →
  `accionable=False`; fingerprint que no agrupa → **miss** (ninguna esperada falsa);
  `anio_esperado` derivado de `fecha_referencia` inyectada (sin `now()` implícito).
- **Enlace esperada→edición real**: convocatoria ingerida de la misma serie →
  `ESPERADA→PUBLICADA_ENLAZADA` con `convocatoria_id_enlazada`, y **no** se crea Match por
  la vía proactiva (lo crea, si procede, el flujo normal de ADR-004). Ventana sin aparición
  → `NO_APARECIDA`.
- **Avisos**: publicación enriquece el aviso de propuesta existente (no duplica); "ventana
  próxima" solo panel, una vez, solo MEDIA/ALTA accionable; `NotificadorStub` verifica que
  el email **no** sale por la ventana estimada.
- **Contrato de puertos** `RepositorioHistorialConcesiones` y
  `RepositorioConvocatoriasEsperadas`, parametrizados sobre `AlmacenMemoria` y
  `AlmacenSQLite` (tablas `CREATE TABLE IF NOT EXISTS`, patrón idempotente ya usado).
- **Anti-hardcoding**: `proactivo/` no introduce ninguna enfermedad/entidad/serie concreta;
  el fingerprint y el NIF llegan como **dato**. El test anti-hardcoding vigila también
  `src/ongs_ai/proactivo/`.
- Todo **hermético** (CLAUDE.md): sin red, sin fichero real, sin `.env` de la máquina.

### 6.2 Dependencias, arranque, reversibilidad

- **Runtime**: ninguna nueva (stdlib + `TransporteHTTP` ya existente).
- **Script manual** `scripts/derivar_recurrentes.py` (NO en CI, como `ejecutar_ingesta.py`):
  para una entidad captada, consulta `nifCif`, puebla historial, deriva esperadas, imprime
  resumen (concesiones capturadas, descartadas, series, esperadas por confianza). Lee el NIF
  de la entidad de la BD, nunca de un fichero commiteado.
- **Reversibilidad**: todo aditivo. Si el proactivo no convence, se retiran `proactivo/`,
  `adapters/ingesta/bdns_concesiones.py`, `servicios/recurrentes.py` y las tablas nuevas
  (desechables como el resto de `var/`) sin tocar dominio, contrato, panel ni ADR-004.
- **Sin cambio de contrato ni de esquema del contrato congelado.**

---

## 7. Mapa de lo que se añade (para orientar la fase)

```
src/ongs_ai/
  proactivo/                       # NUEVO paquete — NO es el contrato congelado
    modelo.py                      # HistorialConcesion, ConvocatoriaEsperada, EstadoEsperada, Confianza
    puertos.py                     # RepositorioHistorialConcesiones, RepositorioConvocatoriasEsperadas
    derivacion.py                  # determinista: historial -> esperadas (fingerprint, ventana, confianza)
  adapters/ingesta/
    bdns_concesiones.py            # NUEVO — FuenteConcesionesBDNS (nifCif + fechas), mapeo -> HistorialConcesion
  servicios/
    recurrentes.py                 # NUEVO — captura+persistencia+derivación+enlace+aviso (compone puertos)
  adapters/persistencia/
    memoria.py / sqlite.py         # + los dos repos nuevos (tablas idempotentes)
scripts/
  derivar_recurrentes.py           # NUEVO — manual, por entidad captada (no CI)
tests/
  test_bdns_concesiones.py, test_recurrentes_derivacion.py,
  test_recurrentes_servicio.py, test_proactivo_puertos.py,
  (+ ampliación de test_anti_fuga_tenant.py y test_anti_hardcoding.py)
```

Superficie de panel/UI (mostrar historial + esperadas al tenant) → fase aparte del
esqueleto web (ADR-005), como se hizo con el panel de ADR-004.

---

## 8. Preguntas al operador (con default cada una — ninguna bloqueante)

1. **Ventana temporal del historial.** Default: consultar `nifCif` con
   `fechaDesde/fechaHasta` de los **últimos 5 años** (cubre 2-4 ediciones de una anual sin
   traer ruido antiguo). ¿Suficiente, o prefieres otra profundidad?
2. **Umbral de ediciones para una esperada.** Default (§3.5): **1** edición crea esperada
   de confianza **BAJA** (honra "en base al año pasado"); **≥2** para ventana fiable.
   ¿Conforme, o prefieres exigir ≥2 y no mostrar nada con una sola edición?
3. **Aviso de "ventana próxima".** Default (§3.8): **solo panel**, una vez por ventana, solo
   confianza MEDIA/ALTA y accionable; el email queda para la publicación real. ¿Conforme, o
   quieres también email al acercarse la ventana (asumiendo que es estimación, no hecho)?
4. **Margen para declarar `NO_APARECIDA`.** Default: **2 meses** tras el fin de la ventana
   estimada. ¿Vale como punto de partida (es calibrable sin ADR)?
5. **Concesión directa / nominativa.** Default (§3.7): se muestra en historial pero su
   esperada es `accionable=False` (no se sugiere presentarse). ¿Conforme, o prefieres
   ocultarlas del todo?
6. **Cadencia de la re-derivación.** Default (§5): tras cada pasada de ingesta de la
   entidad. ¿O una cadencia propia (p. ej. semanal)? Se fija con el scheduling del esqueleto.

---

## 9. Fases y prompt

- **F-proactivo.1 — historial + esperadas + adapter de concesiones + derivación +
  enlace/aviso** → se redacta como prompt completo tras la aprobación de este ADR (mismo
  patrón que ADR-004/006: el arquitecto lo redacta cuando el ADR está aceptado, para
  incorporar los nombres reales y las respuestas a §8). Orden: **en serie** con cualquier
  tarea que toque `web/app.py`, puertos o adapters de persistencia (los toca).
- **F-proactivo.2 — vista de panel** (historial + esperadas del tenant) → tras F-proactivo.1
  auditado; se apoya en el esqueleto web de ADR-005.

Bloqueo parcial: nada bloquea el diseño ni el adapter (la forma de la API está verificada,
§2). La calibración de §8 es ajustable sin ADR (son datos/umbrales, no contrato).
