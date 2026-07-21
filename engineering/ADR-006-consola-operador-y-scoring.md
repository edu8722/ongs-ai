# ADR-006 — Consola del operador, prospectos y scoring de afinidad/importe

- **Estado:** PROPUESTA (pendiente de aprobación del operador) — 2026-07-21.
- **Contexto de fase:** F1 ✔ · ADR-002 ✔ · F3 ✔ · F4.1/4.2 ✔ · ADR-005 (web+auth) ✔ ·
  PROMPT-018 ✔ (v1 corre como proceso local; ingesta real BDNS + IA por suscripción;
  1 propuesta real avisada). Este ADR abre el **"paso previo"**: la herramienta del
  OPERADOR para explorar candidatas y enseñar a cuántas convocatorias podrían presentarse
  y por cuánto importe — el cruce que el prototipo maqueta con datos sintéticos
  (`prototipos/ongs-ai-prototipo.html`, vista "Cruce y puntos").
- **Relación:** NO modifica el contrato congelado (Entidad/Convocatoria/Actividad/Match,
  ADR-001/ADR-002) ni el guardarraíl binario de elegibilidad (`dominio/elegibilidad.py`,
  F3) ni la máquina de estados (`matching_estado.py`). Añade, de forma **aditiva y
  claramente marcada como fuera del contrato**: (a) un rol nuevo "operador" con su capa
  web propia, (b) un concepto `Prospecto` de infraestructura de captación (precedente:
  `RepositorioTokensAcceso` de ADR-005 §5 — infra, no dominio congelado), y (c) un
  servicio de solo lectura de scoring de afinidad + importe potencial que **ordena y
  comunica, jamás decide elegibilidad**.
- **Documento SOLO decisión** — sin código de producción; el código lo entrega
  F-consola.1 (§7).
- **Hallazgo previo (adelantado, se justifica en §4.6):** este diseño **NO exige tocar el
  contrato congelado**. Todo lo que necesita se resuelve con conceptos fuera de contrato
  (Prospecto) y con lecturas/servicios aditivos. Si en algún punto pareciera que hay que
  hacer opcional un campo obligatorio de `Entidad` (NIF, datos económicos,
  `fecha_constitucion`), eso sería un ADR de contrato distinto y una regla de oro rota,
  no una licencia de este ADR.

---

## 1. Contexto y problema

Hasta hoy toda la plataforma está construida alrededor del **tenant** (la Entidad ya
captada, dada de alta con todos sus datos verificados). El panel de ADR-005 es
estrictamente por-tenant: cada entidad ve SOLO lo suyo, y el aislamiento cross-tenant
está garantizado por construcción (`web/dependencias.py::entidad_actual` es la única
fuente de `entidad_id`, jamás un parámetro manipulable).

Pero el negocio tiene un **paso anterior a captar el tenant**: el operador necesita
recorrer las **511 candidatas** del maestro de prospección (investigación R2,
`investigacion/asociaciones_EERR_directorio_v3.xlsx`, **fuera de git**, datos parciales
y con contacto personal), y para cada una poder decir con datos: *"a estas convocatorias
abiertas podrías presentarte, con esta afinidad, por este importe potencial"*. Ese es el
argumento comercial del "técnico de subvenciones" y es exactamente el cruce que el
prototipo maqueta. Hoy no existe como producto: el prototipo lo calcula en JavaScript con
datos sintéticos.

Cuatro problemas a resolver, en orden de riesgo:

1. **Aislamiento (el riesgo real de este ADR).** La consola del operador hace lo
   contrario del panel: **lecturas GLOBALES de todas las entidades**. Introducir esa
   capacidad sin debilitar **ni un milímetro** la garantía cross-tenant del panel exige
   una separación estricta, **por construcción**, entre el rol operador y el rol tenant:
   la dependencia de operador jamás se usa en una ruta de tenant, y `entidad_actual`
   jamás en una ruta de consola. Un error aquí reintroduce el incidente más caro del
   proyecto (fuga cross-tenant).
2. **Contrato congelado.** Un prospecto **no tiene** NIF, ni `datos_economicos_ejercicio_
   anterior`, ni `fecha_constitucion`, ni `forma_juridica` — todos **obligatorios** en
   `Entidad` (ADR-001 §1.1, ADR-002 §2.4). Meter las 511 candidatas como `Entidad` con
   campos vacíos o inventados rompería el contrato y contaminaría el matching real y los
   tests anti-fuga/anti-hardcoding con datos falsos. Hay que darles un hogar **fuera del
   contrato**.
3. **Honestidad del número.** El prototipo introduce, además de la elegibilidad
   determinista, una **puntuación de afinidad**, un **importe potencial** y — esto es lo
   delicado — una **"probabilidad de concesión"** que descuenta el importe
   (`prob = 0.30 + score/100*0.5`, líneas 384–386 del prototipo). Un score determinista y
   explicable es adoptable; una probabilidad de concesión inventada es una **promesa que
   no podemos sostener** y roza "inventar datos" (regla de oro). Hay que separar qué se
   adopta y qué se rechaza de la hipótesis del prototipo.
4. **PII.** La consola muestra datos de prospección que incluyen **contacto personal**
   (⚠ dato personal) de asociaciones aún no captadas. Es aceptable SOLO en localhost v1;
   nunca desplegada tal cual.

Usuario de esta herramienta: **el operador**, no las entidades. Corre como proceso local
en su PC (decisión de producto del 2026-07-21, 06 §ESTADO VIVO). No hay hosting todavía.

---

## 2. Decisión

### 2.1 Rol "operador": capa web propia, separada por construcción del tenant

Se añade un **segundo rol** a la app web, con superficie, dependencias y sesión
**disjuntas** de las del tenant. La regla estructural es simétrica y dura:

- **`web/dependencias_operador.py::operador_actual`** es la ÚNICA función que autoriza una
  ruta de consola. Vive en un **fichero separado** de `web/dependencias.py` (donde vive
  `entidad_actual`).
- **`operador_actual` jamás se importa ni se usa en una ruta de tenant**
  (`rutas/panel.py`, `rutas/propuestas.py`, `rutas/auth.py`).
- **`entidad_actual` jamás se importa ni se usa en una ruta de consola** (`rutas/consola/*`).
- Las dos autorizaciones leen **claves de sesión distintas** en la misma cookie firmada:
  `entidad_actual` lee `session["entidad_id"]`; `operador_actual` lee
  `session["operador_autenticado"]`. Ninguna de las dos toca la clave de la otra. Que un
  mismo navegador pudiera portar ambas (operador que además es una entidad de prueba) es
  irrelevante: cada dependencia solo mira su propia clave y produce su propio tipo.
- Rutas de consola en **módulo propio** bajo `web/rutas/consola/` (regla de CLAUDE.md
  "una ruta nueva = un `include_router` más en `app.py`, nunca lógica en el central").
  Prefijo de ruta común `/consola` (p. ej. `APIRouter(prefix="/consola")`).

Esto convierte la separación operador↔tenant en una propiedad **verificable por
inspección de rutas** (test estructural, §4.1), no en disciplina de cada handler.

### 2.2 Autenticación del operador v1: proporcional al riesgo (proceso local)

El modelo de despliegue v1 es **proceso local en el PC del operador**, un solo operador,
sin hosting. La auth se dimensiona a ese riesgo — **defensa en profundidad de dos
capas**, ambas necesarias:

1. **Bind a loopback + comprobación de loopback en la propia app.** El arranque
   documentado es `uvicorn ... --host 127.0.0.1` (nunca `0.0.0.0` mientras haya consola).
   Como el bind lo decide quien arranca uvicorn y no el código, se añade **además** una
   dependencia `solo_loopback` que rechaza (404 genérico — ni siquiera revela que la ruta
   existe) toda petición a `/consola/*` cuyo `request.client.host` no sea `127.0.0.1`/
   `::1`. Cinturón y tirantes: aunque alguien arranque mal el servidor, la consola no
   responde fuera de la máquina.
2. **Clave de operador por variable de entorno.** `ONGS_AI_OPERADOR_CLAVE` (leída SOLO en
   la composición de la app, mismo patrón que `ONGS_AI_SECRET_KEY`/`ONGS_AI_SMTP_*`;
   nunca hardcodeada, nunca en git). `GET /consola/login` (formulario de clave) →
   `POST /consola/login` compara en **tiempo constante** (`hmac.compare_digest`) contra la
   variable y, si coincide, marca `session["operador_autenticado"] = True`. Sin clave
   definida en el entorno → la consola **no** arranca sus rutas de login válidas (se
   niega a autenticar contra una clave vacía), igual que la app real exige
   `ONGS_AI_SECRET_KEY`.

No se reutiliza el magic-link del tenant para el operador: sobra infraestructura (no hay
buzón que verificar; el operador es quien arranca el proceso) y mezclaría los dos roles.

**Qué cambia cuando haya hosting** (documentado, no se construye ahora): la consola deja
de poder depender de "solo localhost". Antes de exponerla haría falta (a) auth real de
operador (usuario+contraseña con hash, o SSO), (b) TLS obligatorio (`secure=True` en la
cookie), (c) las redacciones de PII de §2.5, y (d) revisar rate-limiting/registro de
acceso. Hasta que todo eso exista, **la consola NO se despliega** — se ejecuta solo en la
máquina del operador.

### 2.3 Prospectos: concepto fuera del contrato congelado

Se introduce **`Prospecto`**, una candidata de prospección con **datos parciales**. NO es
`Entidad` y **no forma parte del contrato congelado** — es infraestructura de captación,
igual que `RepositorioTokensAcceso` es infraestructura de auth (ADR-005 §5).

**Ubicación (decisión conservadora, evita contaminar el dominio congelado):**

- Paquete nuevo **`src/ongs_ai/prospeccion/`**, hermano de `dominio/`, `servicios/`,
  `adapters/`, `web/` — para que "esto NO es el contrato congelado" sea evidente por la
  estructura de ficheros y no por un comentario:
  - `prospeccion/modelo.py` — el dataclass `Prospecto` (frozen).
  - `prospeccion/puertos.py` — puerto `RepositorioProspectos` (Protocol).
  - `prospeccion/importador.py` — importador desde el maestro (§2.4).
- El puerto **no** se mete en `dominio/puertos.py` para **no** hacer que el dominio
  dependa de un concepto de fuera de contrato (`dominio/puertos.py` solo conoce
  Entidad/Convocatoria/Match). Esto es más estricto que el precedente de
  `RepositorioTokensAcceso` (que sí vive en `dominio/puertos.py` pero solo maneja strings
  hash, no un modelo nuevo), y es la razón de separarlo: un `Prospecto` es un modelo de
  datos, no un hash.

**Forma de `Prospecto` (v1, ampliable sin ADR porque no es contrato congelado):** todos
los campos salvo `prospecto_id` y `nombre` son **opcionales** — reflejan lo que el maestro
trae, que es parcial y desigual:

| Campo | Tipo | Notas |
|---|---|---|
| `prospecto_id` | id opaco | Clave. Nunca por nombre. |
| `nombre` | str | Obligatorio (lo único garantizado del maestro). |
| `ambito_territorial` | `AmbitoTerritorial \| None` | Reusa el enum de dominio (valor, no dependencia de contrato). |
| `region` / `provincia` | `str \| None` | Para el cruce por ámbito cuando exista. |
| `enfermedad_o_colectivo` | `str \| None` | Dato, nunca enum (anti-hardcoding). |
| `actividades` | `tuple[TipoActividad, ...]` | Vacío si el maestro no lo trae; nunca se inventa. |
| `forma_juridica` | `FormaJuridica \| None` | Si el maestro lo trae mapeable; si no, `None`. |
| `contacto` | `Contacto \| None` | **⚠ PII** (email/teléfono de la asociación). |
| `fuente_maestro` | str | De qué fichero/fila salió (trazabilidad). |
| `notas` | `str \| None` | Texto libre de prospección, nunca evaluable. |

**Lo que un `Prospecto` NUNCA tiene** (y por eso no es `Entidad`): `nif`,
`datos_economicos_ejercicio_anterior`, `fecha_constitucion`. Son datos verificados que
solo se obtienen al **captar** la entidad, no en prospección.

**Conversión explícita Prospecto → Entidad (§7, F-consola.2, sin prompt aún):** al
completar el alta, el operador rellena los campos obligatorios que faltan (NIF, datos
económicos, fecha de constitución, forma jurídica si no estaba) y el sistema construye una
`Entidad` **válida** por las vías normales. La conversión es **explícita y manual**, nunca
automática y **nunca inventando** los datos que faltan. Un `Prospecto` no se "promueve" a
`Entidad` con placeholders.

### 2.4 Importador del maestro (fichero SIEMPRE fuera de git)

- `prospeccion/importador.py`: función pura que, dado un iterable de filas ya parseadas
  (dicts columna→valor), produce `list[Prospecto]` aplicando un **mapeo columna→campo
  cerrado y documentado**, con **degradación limpia**: fila sin `nombre` → se descarta y
  se cuenta (`filas_descartadas`), nunca se inventa; valor de ámbito/forma jurídica no
  mapeable → ese campo queda `None` y se cuenta, la fila entra igual. Mismo principio que
  el resto del proyecto ("la proyección jamás lanza por un dato feo: descarta, marca
  sospecha, sigue", CLAUDE.md).
- El **parseo del xlsx/csv** (I/O de fichero) se separa de la lógica de mapeo: un
  `scripts/importar_prospectos.py` (manual, como `scripts/ejecutar_ingesta.py`, **no corre
  en CI**) lee el fichero real y llama al importador puro. Así los tests del importador son
  herméticos (filas sintéticas en memoria, jamás el fichero real con PII).
- **Dependencia de lectura de xlsx:** el maestro es `.xlsx`. Para no añadir una dependencia
  runtime nueva por algo que solo usa un script manual, el **default** es pedir al operador
  un export a **CSV UTF-8** (parseable con el `csv` de la stdlib). Si se prefiere leer xlsx
  directo, se añade `openpyxl` como **dependencia opcional del script de importación**
  (nunca del runtime web ni de los tests) — ver pregunta §8.
- El fichero del maestro y cualquier CSV derivado **jamás** entran a git: el patrón
  `investigacion/*asociaciones*` ya está en `.gitignore`; el importador y su script se
  documentan para leer SIEMPRE de una ruta fuera del árbol versionado (o de
  `investigacion/`, que está cubierta).

### 2.5 Scoring de afinidad + importe potencial: determinista, ordena, no decide

Servicio de **solo lectura** `servicios/afinidad.py` (compone dominio, como
`servicios/panel.py`), **sin LLM en el número** (regla de oro: la IA propone, el dominio
valida — y aquí ni siquiera propone: el número es 100% determinista). Opera sobre una
pareja `(perfil, convocatoria)` donde `perfil` puede ser una `Entidad` **o** un
`Prospecto` (evaluación degradada, §2.6).

**El score NO decide elegibilidad.** La elegibilidad la sigue decidiendo, intacto, el
guardarraíl binario de F3 (`evaluar_elegibilidad(Entidad, Convocatoria, fecha_referencia)
-> ResultadoElegibilidad`). El score **ordena y comunica** sobre lo que el guardarraíl ya
dictaminó.

**`ScoreAfinidad` (0–100), determinista, explicable motivo a motivo** (como el prototipo):
combinación de dos componentes con pesos explícitos y documentados (defaults en §8, la
pregunta de calibración es del operador):

1. **Cobertura de requisitos duros evaluables** (peso mayor, default 70): proporción de
   requisitos duros que el perfil **cumple** sobre los que son **evaluables** con sus
   datos. Los requisitos son los de `elegibilidad.py`: estado de ingesta, ámbito, forma
   jurídica, antigüedad, requisitos formales. Cada uno cae en `cumple` / `incumple` /
   `pendiente_de_dato` (no evaluable). Score parcial = `cumplidos / evaluables`; los
   `pendiente_de_dato` **no cuentan ni a favor ni en contra** (se muestran como pendientes,
   nunca se rellenan con un supuesto). Si **algún** requisito evaluable **incumple** → el
   perfil **no es elegible** para esa convocatoria → el score se **capa** por debajo del
   umbral de elegible (como el prototipo lo capa a 44) y el importe **no** se agrega.
2. **Afinidad temática de actividades** (peso menor, default 30): solape **determinista**
   entre las `actividades` declaradas (enum cerrado `TipoActividad`) del perfil y las
   señales temáticas del texto de la convocatoria (`objeto` + `beneficiarios_elegibles`),
   vía un **mapeo cerrado palabra-clave→`TipoActividad`** que vive en el servicio (sin
   LLM, sin regex "mágica" que puntúe sola — un diccionario cerrado y testeable, como el
   `_MAPA_FORMA_JURIDICA` de ADR-002). Convocatoria cuyo texto no active ninguna señal →
   afinidad temática neutra baja, nunca penalización inventada.

**Qué se RECHAZA de la hipótesis del prototipo (y por qué):**

- **"Probabilidad de concesión"** (`prob = 0.30 + score/100*0.5`, y el descuento de
  importe que aplica). **Rechazada**: no tenemos ninguna base determinista ni histórica
  para afirmar una probabilidad de que concedan una subvención; es una promesa que no
  podemos sostener y contamina un importe honesto con un número inventado. El importe se
  comunica como **techo teórico**, no como esperanza matemática.
- **"Capacidad de ejecución" por ratio ingresos/cuantía** como factor del score de
  afinidad. **Rechazada como factor del score**: (a) depende de `datos_economicos`, que un
  `Prospecto` **no tiene** (inflaría el score con un dato ausente); (b) es una señal de
  *ajuste de tamaño*, no de *afinidad*. Se permite **mostrarla aparte** como señal
  informativa **solo cuando hay datos económicos** (Entidad ya captada), nunca dentro del
  número de afinidad ni para prospectos.
- **"Margen de plazo"** como factor del score. **Rechazada como factor**: los días que
  quedan son **urgencia**, no afinidad, y cambian cada día (un score que baja solo porque
  pasa el tiempo no es "afinidad"). El plazo se muestra **aparte** como señal de urgencia.

Estas tres desviaciones respecto al prototipo son **decisiones deliberadas de honestidad**
del ADR, no omisiones — el prototipo es maqueta de producto, no especificación.

**Importe potencial** (céntimos int, **rangos, no promesas**):

- Se agrega **solo** sobre convocatorias para las que el perfil es **elegible** (el
  guardarraíl binario dijo `elegible=True`).
- `importe_potencial_maximo_centimos` = suma de `cuantias.importe_maximo_centimos` de esas
  convocatorias. `importe_potencial_minimo_centimos` = suma de
  `cuantias.importe_minimo_centimos` donde exista. Se comunica como **rango**
  `[mínimo, máximo]` y **explícitamente como techo teórico** ("importe al que podría optar
  si se presentara a todas y se las concedieran"), jamás como predicción de ingreso.
- Convocatoria elegible **sin** `importe_maximo_centimos` (None): **no suma importe** pero
  se **cuenta e informa** como "elegible, importe no publicado" — nunca se imputa 0 ni se
  omite en silencio (sería fingir que no existe una oportunidad real).
- Todo en **céntimos enteros** (regla de oro dinero); el formateo a euros es de la capa de
  render (`_euros`, ya existe en `rutas/panel.py`), nunca `float` en el cálculo.

**Salida del servicio** (dataclasses de solo lectura, p. ej. `ResultadoAfinidad` con
`score`, `elegible`, `detalle_por_requisito`, `afinidad_tematica`, `importe` y las señales
aparte cuando aplican; y un agregado `ResumenProspeccion` por perfil con nº de elegibles y
el rango de importe). Explicable motivo a motivo, como el prototipo.

### 2.6 Evaluación de elegibilidad sobre un Prospecto (datos parciales)

El guardarraíl de F3 exige una `Entidad` completa; un `Prospecto` no lo es. Para no tocar
`elegibilidad.py` **ni** fabricar una `Entidad` falsa, el servicio de afinidad evalúa el
prospecto con una función **degradada de solo lectura** que aplica, requisito a requisito,
la **misma lógica** que `elegibilidad.py` **donde hay dato**, y marca `pendiente_de_dato`
donde no lo hay:

- Ámbito: evaluable si el prospecto tiene `ambito`/`region`/`provincia` según el caso;
  si no, `pendiente_de_dato`.
- Forma jurídica: evaluable si el prospecto declara `forma_juridica` y la convocatoria la
  exige; si el prospecto no la tiene, `pendiente_de_dato`.
- Antigüedad: **siempre `pendiente_de_dato`** para un prospecto (no tiene
  `fecha_constitucion`).
- Requisitos formales: **siempre `pendiente_de_dato`** (el maestro no trae qué acredita).
- Estado de ingesta: es de la convocatoria, evaluable igual que para una entidad.

Un `pendiente_de_dato` **nunca** cuenta como cumplido (no se inventa elegibilidad) ni como
incumplido (no se descarta injustamente): se **muestra** como pendiente y baja la
*confianza* del score, no lo falsea. Un prospecto con muchos pendientes aparece como
"prometedor, faltan datos para confirmar", que es exactamente lo que es.

Nota de reutilización (para quien implemente): lo ideal es **refactorizar** las
sub-evaluaciones de `elegibilidad.py` (`_evaluar_ambito`, `_evaluar_forma_juridica`, …) a
una forma que acepte tanto `Entidad` como el perfil parcial y devuelva
`cumple|incumple|pendiente`, **sin cambiar** el comportamiento observable de
`evaluar_elegibilidad(Entidad, …)` (mismos tests verdes). Si ese refactor resultara
arriesgado, la alternativa conservadora es **duplicar** la lógica por-requisito en el
servicio de afinidad con un test que ancle la equivalencia con `elegibilidad.py` para el
caso Entidad. La primera es preferible (una sola fuente de verdad); la decisión final es
del prompt de F-consola.1, documentada allí.

### 2.7 Lecturas globales que necesita la consola (aditivas, no contrato)

La consola necesita listar **todas** las entidades y **todas** las convocatorias:

- `RepositorioEntidades.listar_entidades()` **ya existe** (añadido en PROMPT-018 para el
  runner de ingesta) — se reutiliza tal cual.
- `RepositorioConvocatorias` **no** tiene un método de listado. F-consola.1 añade
  `listar_convocatorias() -> list[Convocatoria]` a ese puerto (implementado en
  `AlmacenMemoria` y `AlmacenSQLite`, test de contrato parametrizado). Es una **lectura
  aditiva**, no un cambio de contrato: el contrato son las **formas de dato**
  (Entidad/Convocatoria/…), no la superficie de consultas del repositorio — mismo
  razonamiento con el que ADR-005 §5 añadió `obtener_entidad_por_email` sin considerarlo
  cambio de contrato.
- `RepositorioProspectos` (puerto nuevo, §2.3): `guardar_prospecto`, `obtener_prospecto`,
  `listar_prospectos`. Implementado en ambos backends (tabla `prospectos` en SQLite vía
  `CREATE TABLE IF NOT EXISTS`, patrón idempotente ya usado; dict en memoria).

### 2.8 Resumen de decisión

Rol operador con dependencias y sesión **disjuntas** del tenant (separación por
construcción, no por disciplina) ⇒ las lecturas globales de la consola **no** pueden
tocar el aislamiento cross-tenant del panel. `Prospecto` **fuera del contrato** ⇒ las 511
candidatas entran sin campos falsos y sin romper el contrato congelado. Scoring
**determinista, explicable y honesto** (sin probabilidad inventada, sin factores que
dependan de datos ausentes) ⇒ el número ordena y comunica, y el guardarraíl binario de F3
queda **intacto**. PII de prospección **solo en localhost** ⇒ nada se expone hasta que
exista la auth/TLS/redacción de hosting.

---

## 3. Alternativas consideradas y descartadas

- **Cargar las 511 candidatas como `Entidad` con campos obligatorios vacíos o
  placeholder** (NIF `""`, datos económicos a 0, fecha de constitución ficticia).
  Descartada: rompe el CONTRATO CONGELADO (esos campos son obligatorios y verificados),
  contamina el matching real y los tests anti-fuga/anti-hardcoding con datos falsos, y
  falsearía el guardarraíl (una fecha de constitución inventada haría "cumplir" o
  "incumplir" antigüedad con un dato mentira). El concepto `Prospecto` fuera de contrato
  lo evita por completo.
- **Ampliar el contrato para hacer opcionales NIF / datos económicos / `fecha_constitucion`.**
  Descartada: debilita el guardarraíl determinista (que se apoya en que esos datos existen
  y son verificados) y sería, además, un ADR de **contrato** con su propio proceso — no
  algo que este ADR pueda decidir. El hallazgo de §Relación es justamente que **no hace
  falta**.
- **Consola como un "tenant especial" con un `entidad_id` mágico que ve todo.**
  Descartada: cualquier ruta que mezcle "ver todo" con la maquinaria de `entidad_actual`
  erosiona la garantía cross-tenant y crea el riesgo de que un bug exponga el super-tenant
  a un tenant normal. El rol separado por construcción es la única forma de tener lecturas
  globales sin poner en riesgo el aislamiento.
- **Reutilizar el magic-link del tenant para autenticar al operador.** Descartada: el
  operador no necesita verificar un buzón (es quien arranca el proceso), y mezclar los dos
  flujos de auth acopla dos roles que deben estar separados. Clave por env + loopback es
  proporcional al riesgo de un proceso local monousuario.
- **Adoptar el scoring del prototipo tal cual** (con probabilidad de concesión y descuento
  de importe, capacidad por ratio y margen de plazo dentro del número). Descartada en sus
  tres piezas problemáticas (§2.5): la probabilidad es una promesa insostenible; la
  capacidad depende de datos que un prospecto no tiene; el plazo es urgencia, no afinidad.
  Se adopta **solo** la parte determinista, explicable y honesta.
- **Scoring con LLM** ("pregúntale al modelo cómo de afín es"). Descartada por la regla de
  oro (ya justificada en ADR-001 §3.2): reintroduce no-determinismo en un número que
  ordena decisiones de negocio y que el operador va a enseñar a las candidatas. El LLM
  puede, como mucho, **explicar en prosa** un match ya puntuado (capa F3 existente), nunca
  producir el número.
- **Poner `Prospecto` y su puerto dentro de `dominio/`** (junto a Entidad). Descartada:
  aunque `RepositorioTokensAcceso` sienta el precedente de "infra en `dominio/puertos.py`",
  un `Prospecto` es un **modelo de datos** nuevo, no un hash; meterlo en `dominio/` diluye
  la frontera "esto es el contrato congelado". El paquete `prospeccion/` separado lo deja
  inequívoco.

---

## 4. Consecuencias

### 4.1 Tests (el anti-fuga sigue siendo obligatorio; la consola gana los suyos)

- **Anti-fuga cross-tenant INTACTO y sin debilitar** (regla de oro): los tests existentes
  (`tests/test_anti_fuga_tenant.py`, incluido el caso HTTP de ADR-005) siguen verdes tal
  cual. La consola **no** los toca.
- **Test estructural de separación de roles** (nuevo, el que da valor a §2.1): por
  inspección de las rutas montadas, **ninguna** ruta bajo `/consola` depende de
  `entidad_actual`, y **ninguna** ruta fuera de `/consola` depende de `operador_actual`.
  (Se puede implementar recorriendo `app.routes` y los `Depends` de cada endpoint, o como
  mínimo con un test de import que falle si un módulo de tenant importa
  `dependencias_operador` o viceversa.)
- **Tests de auth de consola** (nuevos, herméticos con `TestClient`): `/consola/*` sin
  clave → login/negado; con clave correcta → acceso; petición con `client.host` no
  loopback → 404 genérico; clave incorrecta → mismo error genérico (comparación en tiempo
  constante).
- **Tests del importador** (herméticos, filas sintéticas en memoria, **jamás** el maestro
  real): fila sin nombre se descarta y cuenta; ámbito/forma no mapeable → campo `None` y
  cuenta; fila completa → `Prospecto` correcto.
- **Tests del scoring** (deterministas): mismo `(perfil, convocatoria)` → mismo score
  siempre; convocatoria no elegible → score capado e importe no agregado; convocatoria
  elegible sin importe máximo → cuenta como elegible, no suma importe; prospecto con datos
  faltantes → los requisitos correspondientes salen `pendiente_de_dato`, nunca inventados;
  y un **test de anclaje** que confirme que, para una `Entidad` completa, la parte de
  elegibilidad del score coincide con lo que dicta `evaluar_elegibilidad` (una sola verdad).
- **Tests de contrato del puerto** `RepositorioProspectos` y del nuevo
  `listar_convocatorias`, parametrizados sobre `AlmacenMemoria` y `AlmacenSQLite` (mismo
  patrón que el resto de puertos).
- **Anti-hardcoding**: el importador y el scoring no pueden introducir ninguna enfermedad,
  colectivo o entidad concreta en el código — todo llega como dato del maestro. El test
  anti-hardcoding sigue vigilando `src/ongs_ai/` (incluye ahora `prospeccion/`).
- Todo **hermético** (CLAUDE.md): sin red, sin fichero real, sin CLI, sin `.env` de la
  máquina.

### 4.2 PII y superficies sin fugas

- La consola muestra `Prospecto.contacto` (**⚠ dato personal** de asociaciones no
  captadas). Aceptable SOLO en localhost v1. La tabla de superficies:

| Ruta | Expone | No expone |
|---|---|---|
| `GET /consola/login` | Formulario de clave | — |
| `POST /consola/login` | Acceso o error genérico | Si la clave es "casi" correcta (comparación en tiempo constante) |
| `GET /consola/prospectos` (y detalle) | Prospectos con su contacto ⚠, score, cruce motivo a motivo, importe potencial (rango, techo) | Datos de tenants ajenos mezclados como si fueran del prospecto; costes internos de plataforma (tokens IA, coste de scraping); ids de workers |
| `GET /consola/entidades` / cruce | Todas las entidades y su cruce (lectura global — es el propósito del rol operador) | — (el operador SÍ ve global; esto NO se expone jamás a un tenant) |

- **Autoescape de Jinja2 activado** (igual que ADR-005 §2.4): `objeto`,
  `beneficiarios_elegibles`, `notas` y demás texto libre/IA son no confiables.
- **Qué se redacta/oculta si algún día se hospeda** (no se construye ahora): (a) el
  contacto personal del prospecto se oculta por defecto y se muestra solo bajo permiso
  explícito/rol; (b) auth real de operador + TLS (§2.2); (c) registro de acceso a datos de
  prospección; (d) revisión legal de base de tratamiento de esos datos personales. **Hasta
  entonces la consola no se despliega.**

### 4.3 Dependencias

- **Runtime**: ninguna nueva para la web/servicio (FastAPI/Jinja2 ya están). El scoring y
  los puertos son stdlib + dominio.
- **Solo script manual de importación**: `openpyxl` **opcional** si se lee xlsx directo;
  evitable con export a CSV (§2.4, pregunta §8). Nunca dependencia de runtime ni de tests.

### 4.4 Arranque y operación

- Comando documentado (a fijar en el 06/CLAUDE.md tras F-consola.1): arrancar uvicorn con
  `--host 127.0.0.1` y con `ONGS_AI_OPERADOR_CLAVE` en el entorno para habilitar la
  consola; sin esa variable, la app web del tenant funciona igual y la consola no
  autentica.
- El importador es un paso manual del operador (como `ejecutar_ingesta.py`): lee el maestro
  fuera de git y puebla `prospectos`.

### 4.5 Reversibilidad

- Todo es aditivo: si el rol operador o el scoring no convencen, se retiran sus módulos
  (`web/rutas/consola/`, `dependencias_operador.py`, `prospeccion/`, `servicios/afinidad.py`)
  sin tocar dominio, contrato ni panel de tenant. La tabla `prospectos` es desechable como
  el resto de `var/`.

### 4.6 Confirmación del hallazgo: no se toca el contrato

Recorridos los cuatro problemas, ninguno exige modificar Entidad/Convocatoria/Actividad/
Match ni el guardarraíl binario: los prospectos viven fuera del contrato, el scoring es un
servicio de lectura sobre datos ya validados, y las lecturas globales son aditivas. El
contrato congelado permanece congelado.

---

## 5. Mapa de lo que se añade (para orientar la fase)

```
src/ongs_ai/
  prospeccion/                 # NUEVO paquete — NO es el contrato congelado
    modelo.py                  # Prospecto (frozen, campos opcionales salvo id/nombre)
    puertos.py                 # RepositorioProspectos (Protocol)
    importador.py              # filas dict -> list[Prospecto], degradación limpia
  servicios/
    afinidad.py                # NUEVO — scoring determinista + importe potencial (solo lectura)
  web/
    dependencias_operador.py   # NUEVO — operador_actual + solo_loopback (jamás en rutas de tenant)
    rutas/
      consola/                 # NUEVO — rutas /consola/* (jamás usan entidad_actual)
        auth.py                # /consola/login, /consola/logout
        prospectos.py          # /consola/prospectos (+ cruce con scoring)
        entidades.py           # /consola/entidades (lectura global) + cruce
    plantillas/
      consola/                 # plantillas propias de la consola
  adapters/persistencia/
    memoria.py / sqlite.py     # +RepositorioProspectos, +listar_convocatorias
scripts/
  importar_prospectos.py       # NUEVO — manual, lee el maestro fuera de git (no CI)
tests/
  test_consola_auth.py, test_afinidad.py, test_prospectos_puerto.py,
  test_importador_prospectos.py, (+ test estructural de separación de roles)
```

---

## 6. Preguntas al operador (con default cada una — no bloqueantes salvo la 2)

1. **Clave de operador.** Default: `ONGS_AI_OPERADOR_CLAVE`, generada una vez por el
   operador (p. ej. `openssl rand -hex 32`), en el entorno, nunca en git. ¿Conforme?
2. **Mapeo de columnas del maestro (BLOQUEANTE del importador, no del ADR).** El importador
   necesita el nombre **real** de las columnas del xlsx/csv (v3, 511 filas): cuál es el
   nombre, cuál el ámbito/región/provincia, cuál el contacto, etc. **Esto es un dato que no
   tengo y no se puede inventar** (regla de oro): sin el mapeo real, el importador no se
   puede escribir correctamente. ¿Me pasas las cabeceras (o una fila de ejemplo anonimizada)
   antes de F-consola.1?
3. **Formato de entrega del maestro.** Default: export a **CSV UTF-8** (cero dependencias
   nuevas). Alternativa: xlsx directo añadiendo `openpyxl` como dependencia **solo** del
   script de importación. ¿Cuál prefieres?
4. **Pesos del score de afinidad.** Default: cobertura de requisitos duros **70%** +
   afinidad temática de actividades **30%**; umbral de "elegible" y capado de no elegibles
   como el prototipo. ¿Vale como punto de partida (es calibrable sin ADR, es solo un
   servicio de lectura)?
5. **Presentación del importe potencial.** Default: **rango** `[suma de mínimos, suma de
   máximos]` de las convocatorias elegibles, etiquetado como **techo teórico** ("importe al
   que podría optar", no predicción). ¿Prefieres mostrar solo el máximo, o el rango
   completo?
6. **Señales "aparte" (capacidad de ejecución y margen de plazo).** Default: se muestran
   como información contextual **fuera** del número de afinidad (capacidad solo cuando hay
   datos económicos, es decir para entidades ya captadas; plazo siempre). ¿Conforme, o las
   quieres ver dentro del score como en el prototipo (con la salvedad de honestidad ya
   argumentada en §2.5)?
7. **Hosting futuro.** Default: la consola **no** se despliega hasta tener auth real +
   TLS + redacción de PII (§2.2/§4.2). ¿Hay ya intención de hospedarla, o v1 se queda como
   proceso local del operador indefinidamente?

---

## 7. Fases y prompts

- **F-consola.1 — rol operador + prospectos + importador + scoring + primera vista de
  consola** → prompt completo abajo. **Bloqueo parcial:** el importador necesita el mapeo
  de columnas real (pregunta §6.2); el resto de la fase (rol, auth, puerto, scoring, vista)
  se puede construir en paralelo con datos sintéticos y cablear el mapeo cuando llegue.
- **F-consola.2 — conversión Prospecto → Entidad** (orientación, sin prompt aún): formulario
  en la consola donde el operador completa los campos obligatorios que un prospecto no tiene
  (NIF, datos económicos, fecha de constitución, forma jurídica) y se crea una `Entidad`
  válida por las vías normales. Conversión **explícita, nunca inventando** datos. Se redacta
  tras auditar F-consola.1.
- **F-consola.3 — resto de vistas del prototipo** (orientación, sin prompt): explorador
  global de convocatorias, mapa de sedes, top-matches. Se redacta tras F-consola.1/2.

### PROMPT F-consola.1 — consola del operador + prospectos + scoring · MODELO: Sonnet · ORDEN: 1º (nada en paralelo — toca `web/app.py` central, puertos y adapters)

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

TAREA: F-consola.1 del ADR-006 (léelo entero: engineering/ADR-006-consola-
operador-y-scoring.md). Construye el rol OPERADOR con su capa web propia, el
concepto Prospecto fuera del contrato, el importador, el servicio de scoring
determinista y una primera vista de consola de solo lectura. NO toques el
contrato congelado (dominio/entidades.py, matching_estado.py), NI el
guardarraíl binario de elegibilidad salvo el refactor sin-cambio-de-conducta
del punto 4, NI el panel/rutas de tenant.

1. Prospecto (paquete NUEVO src/ongs_ai/prospeccion/, hermano de dominio/):
   a. modelo.py: dataclass frozen `Prospecto` con los campos de §2.3 del ADR
      (solo prospecto_id y nombre obligatorios; el resto opcional; reutiliza
      los enums AmbitoTerritorial/TipoActividad/FormaJuridica y Contacto de
      dominio como VALORES, sin crear dependencia inversa dominio->prospeccion).
      NUNCA lleva nif/datos_economicos/fecha_constitucion.
   b. puertos.py: Protocol `RepositorioProspectos` (guardar_prospecto,
      obtener_prospecto, listar_prospectos). NO lo metas en dominio/puertos.py.
   c. importador.py: función PURA filas(dict) -> list[Prospecto] con mapeo
      columna->campo CERRADO y documentado; degradación limpia (fila sin
      nombre se descarta y cuenta; valor no mapeable -> campo None y cuenta;
      nunca inventa). Devuelve también contadores. Si NO tienes el mapeo real
      de columnas del maestro (pregunta al operador, es dato que no se
      inventa), implementa el importador con un mapeo PROVISIONAL documentado
      y déjalo señalado como pregunta bloqueante al final.

2. Persistencia (adapters/persistencia/memoria.py y sqlite.py):
   a. Implementa RepositorioProspectos en ambos (tabla `prospectos` en SQLite
      vía CREATE TABLE IF NOT EXISTS, idempotente; dict en memoria).
   b. Añade `listar_convocatorias() -> list[Convocatoria]` al puerto
      RepositorioConvocatorias (dominio/puertos.py) y ambos adapters. Es
      lectura aditiva, NO cambio de contrato.
   c. Tests de contrato parametrizados sobre ambos backends para (a) y (b),
      mismo patrón que el resto de puertos.

3. Servicio de scoring — servicios/afinidad.py (solo lectura, compone
   dominio, SIN LLM en el número):
   - ScoreAfinidad 0-100 determinista: cobertura de requisitos duros
     evaluables (peso 70 por defecto) + afinidad temática de actividades
     (peso 30) vía un mapeo cerrado palabra-clave->TipoActividad testeable
     (NADA de regex que puntúe sola; un diccionario cerrado como
     _MAPA_FORMA_JURIDICA de ADR-002). Convocatoria no elegible -> score
     capado bajo el umbral e importe NO agregado.
   - Importe potencial en CÉNTIMOS INT, rango [suma min, suma max] SOLO de
     convocatorias elegibles, etiquetado como techo teórico; elegible sin
     importe_maximo -> cuenta pero no suma. NADA de probabilidad de concesión
     ni descuentos (RECHAZADO en §2.5 del ADR). Capacidad y plazo NO entran
     en el número (señales aparte; capacidad solo si hay datos_economicos).
   - Explicable motivo a motivo (dataclasses de solo lectura con el detalle
     por requisito: cumple/incumple/pendiente_de_dato).

4. Evaluación de prospecto (datos parciales) — §2.6: aplica la MISMA lógica
   por-requisito que dominio/elegibilidad.py donde hay dato y marca
   pendiente_de_dato donde no. PREFERIDO: refactoriza las sub-evaluaciones de
   elegibilidad.py a una forma que sirva para Entidad y para el perfil parcial
   SIN cambiar la conducta observable de evaluar_elegibilidad(Entidad,...)
   (sus tests F3 siguen VERDES, verifícalo). Si el refactor te parece
   arriesgado, DUPLICA la lógica en afinidad.py con un test de anclaje que
   ancle la equivalencia para el caso Entidad, y documenta por qué.

5. Rol operador (web) — separación por construcción:
   - web/dependencias_operador.py: `operador_actual` (lee
     session["operador_autenticado"], NUNCA entidad_id) y `solo_loopback`
     (rechaza con 404 genérico si request.client.host no es 127.0.0.1/::1).
     Este fichero JAMÁS se importa desde rutas de tenant.
   - web/rutas/consola/ (APIRouter prefix="/consola"): auth.py
     (/consola/login form con clave ONGS_AI_OPERADOR_CLAVE comparada con
     hmac.compare_digest; /consola/logout), prospectos.py
     (/consola/prospectos: lista prospectos con su cruce y scoring),
     entidades.py (/consola/entidades: lectura GLOBAL vía listar_entidades +
     cruce con scoring). NINGUNA ruta de consola usa entidad_actual.
   - web/app.py (central): lee ONGS_AI_OPERADOR_CLAVE SOLO aquí (inyectable en
     tests, como secret_key); incluye los routers de consola. Sin lógica de
     negocio. Si la clave no está definida, la consola no autentica (no
     rompas el arranque del tenant por ello).
   - plantillas/consola/ con autoescape (default de Jinja2Templates, no lo
     desactives). Sin CSS/JS de terceros por CDN.

6. Script manual scripts/importar_prospectos.py (NO corre en CI, como
   ejecutar_ingesta.py): lee el maestro (CSV UTF-8 por defecto; xlsx solo si
   el operador lo pide, con openpyxl como dep OPCIONAL del script), llama al
   importador puro, guarda en RepositorioProspectos, imprime resumen
   (importados, descartados, campos no mapeados). Lee SIEMPRE de fuera de git
   (investigacion/ está gitignorada); NUNCA commitees el fichero ni un CSV.

7. Tests (HERMÉTICOS, TestClient, sin red/CLI/fichero real/.env de la
   máquina), §4.1 del ADR:
   - Anti-fuga cross-tenant existente SIGUE VERDE sin tocarlo.
   - Test estructural de separación de roles: ninguna ruta /consola depende
     de entidad_actual; ninguna ruta de tenant depende de
     dependencias_operador (por import o por inspección de app.routes).
   - Auth de consola: sin clave -> negado; clave ok -> acceso; client.host no
     loopback -> 404; clave incorrecta -> mismo error genérico.
   - Importador: fila sin nombre descartada+contada; no mapeable -> None
     +contado; fila completa -> Prospecto correcto (filas sintéticas, JAMÁS
     el maestro real).
   - Scoring: determinismo (mismo input, mismo score); no elegible -> capado
     e importe no agregado; elegible sin importe_max -> cuenta sin sumar;
     prospecto con datos faltantes -> pendiente_de_dato (nunca inventado);
     anclaje: para Entidad completa, la parte de elegibilidad coincide con
     evaluar_elegibilidad.
   - Contrato de RepositorioProspectos y listar_convocatorias en ambos
     backends.

8. Chequeo sintáctico (ast.parse) de cada .py tocado. `python -m pytest -q`
   VERDE y HERMÉTICO con el nº REAL de tests. Incluye engineering/06_* del
   working tree tal cual.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add (ni .env, ni var/, ni el maestro/CSV de
prospección, ni ONGS_AI_OPERADOR_CLAVE en ningún fichero), `git push`.
Agrupa al final las preguntas al operador (mapeo de columnas del maestro,
formato CSV/xlsx, pesos del score) con su default.
```
