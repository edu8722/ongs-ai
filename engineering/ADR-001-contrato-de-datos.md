# ADR-001 — Contrato de datos central (Entidad, Convocatoria, Actividad, Match/Propuesta)

- **Estado:** ACEPTADO (v1)
- **Fecha:** 2026-07-18
- **Contexto de producto:** `PROJECT_CONTEXT.md` (raíz)
- **Regla de oro afectada:** CONTRATO CONGELADO (CLAUDE.md) — este ADR es la fuente
  que se congela; cualquier cambio de schema posterior exige ADR nuevo, nunca edición
  silenciosa de este documento ni del código que lo implementa.

Producto en una frase: SaaS multi-tenant que vigila convocatorias de subvenciones
(públicas y privadas, nacional→local, España) y las casa con asociaciones de
enfermedades raras sin personal, avisa, propone y ayuda a preparar la solicitud.

---

## 1. Decisión: el contrato de datos central

Cuatro entidades. Los nombres de esta sección son los nombres congelados — se
implementarán con estos identificadores literales (en inglés técnico dentro del
código: `Entity`, `Grant`, `Activity`, `Match`) para que el mapeo doc↔código sea
directo y auditable.

### 1.1 Entidad (el tenant)

Perfil de la asociación de enfermedades raras que usa la plataforma. Es la unidad de
aislamiento por tenant: todo dato de dominio (convocatorias vigiladas, matches,
propuestas) cuelga de un `entidad_id`.

| Campo | Tipo | Notas |
|---|---|---|
| `entidad_id` | id opaco (UUID/ULID) | Clave primaria y clave de aislamiento por tenant. Nunca se referencia por nombre. |
| `nombre_legal` | string | Dato verificado (dominio). |
| `nif` | string | Dato verificado (dominio). PII de entidad, no de paciente. |
| `ambito_territorial` | enum cerrado (`nacional`, `autonomico`, `provincial`, `local`) + `region`/`provincia` cuando aplique | Dato verificado (dominio) — determina qué convocatorias son candidatas. |
| `enfermedad_o_colectivo` | string libre (dato, NO enum de plataforma) | Dato verificado (dominio). Ver anti-hardcoding en §4: la plataforma no conoce enfermedades concretas, solo las recibe como valor de este campo. |
| `actividades` | lista de `Actividad` (§1.3) | Dato verificado (dominio) — declarado por la entidad. |
| `datos_economicos_ejercicio_anterior` | objeto: `ingresos_centimos` (int), `gastos_centimos` (int), `ejercicio` (año) | Dato verificado (dominio). **Dinero SIEMPRE en céntimos enteros.** Sensible — ver §4 PII. |
| `requisitos_formales_disponibles` | lista de flags cerrados (p. ej. `inscrita_registro_asociaciones`, `declarada_utilidad_publica`, `certificado_estar_al_corriente_aeat`, `certificado_estar_al_corriente_ss`) | Dato verificado (dominio) — lo que la entidad puede acreditar hoy; se contrasta contra los requisitos duros de cada convocatoria. |
| `contacto` | email/teléfono | Dato verificado (dominio). |
| `creado_en` / `actualizado_en` | timestamp | Metadato de dominio. |

### 1.2 Convocatoria

Una oportunidad de financiación detectada en una fuente (portal público o privado).

| Campo | Tipo | Notas |
|---|---|---|
| `convocatoria_id` | id opaco | Clave primaria. |
| `fuente` | objeto: `portal` (string), `url_origen`, `tipo` (enum cerrado: `publica_nacional`, `publica_autonomica`, `publica_local`, `privada`) | `tipo` es dato extraído por IA de la ingesta, luego el dominio puede corregirlo (ver más abajo). |
| `objeto` | texto libre | Extracción IA — resumen de para qué es la convocatoria. |
| `beneficiarios_elegibles` | texto libre (descriptivo) + `requisitos_elegibilidad` estructurados (ver siguiente fila) | El texto libre es extracción IA (explicación); lo estructurado es lo que se evalúa. |
| `requisitos_elegibilidad` | lista estructurada y tipada de condiciones evaluables (p. ej. `ambito_territorial_requerido`, `forma_juridica_requerida`, `antiguedad_minima_anios`, `requisitos_formales_requeridos: [flags cerrados de §1.1]`, `exclusiones`) | **Estos campos, aunque los rellena la IA en primera pasada (extracción del texto legal), son datos estructurados que el dominio evalúa de forma determinista.** La IA nunca decide elegibilidad; solo puebla estos campos y el dominio los valida contra la Entidad. Ver §2 y §4. |
| `ambito_geografico` | enum cerrado, igual que `ambito_territorial` de Entidad, + `region`/`provincia` | Extracción IA, verificable por dominio. |
| `plazos` | objeto: `fecha_apertura`, `fecha_cierre`, `fecha_resolucion_estimada` | Extracción IA. Fechas, no timestamps de creación de registro. |
| `cuantias` | objeto: `importe_minimo_centimos`, `importe_maximo_centimos`, `porcentaje_max_financiable` (si aplica) | Extracción IA. **Dinero en céntimos enteros.** |
| `estado_ingesta` | enum cerrado: `detectada`, `extraida`, `verificada`, `descartada_por_dominio` | Dato de dominio — trazabilidad del pipeline de ingesta (F2/F3). |
| `documento_origen_ref` | referencia a texto/PDF fuente (fuera de este contrato, en almacenamiento de documentos) | Para auditar de dónde salió cada campo extraído. |
| `creado_en` / `actualizado_en` | timestamp | Metadato de dominio. |

### 1.3 Actividad

Enum cerrado y extensible SOLO por ADR (regla de oro). Valores iniciales v1:

```
voluntariado
encuentro_de_pacientes
charlas_y_sensibilizacion
formacion
investigacion_y_estudios
atencion_directa_a_familias
otro  (con campo libre `descripcion` obligatorio cuando se usa este valor)
```

`otro` existe como válvula de escape para no bloquear el alta de una entidad con una
actividad no prevista, pero es dato de dominio marcado como no-clasificado: no debe
usarse para matching automático estricto hasta que un ADR lo incorpore como valor
propio del enum.

### 1.4 Match / Propuesta

El vínculo Entidad↔Convocatoria y su ciclo de vida. Se modela como **máquina de
estados con asientos inmutables** (regla de oro de arquitectura): cada transición es
un registro nuevo, nunca un `UPDATE` que borra el estado anterior.

| Campo | Tipo | Notas |
|---|---|---|
| `match_id` | id opaco | Clave primaria. |
| `entidad_id` | FK a Entidad | Aislamiento por tenant — todo Match pertenece a una única Entidad. |
| `convocatoria_id` | FK a Convocatoria | Las convocatorias son compartidas entre tenants (no son datos de tenant); el Match sí lo es. |
| `estado_actual` | enum cerrado: `detectada` → `propuesta` → (`aceptada` \| `descartada`) → `en_preparacion` → `presentada` | Derivado del último asiento, no almacenado como fuente de verdad independiente (o, si se cachea por rendimiento, siempre reconstruible desde los asientos). |
| `explicacion_ia` | texto | Salida de IA (capa explicativa, F3) — por qué se propone este match. Nunca decide `estado_actual`, solo lo argumenta. |
| `resultado_elegibilidad_dura` | booleano + detalle de qué requisitos cumple/incumple | Resultado del guardarraíl determinista (dominio), no de la IA. |
| `asientos` | lista inmutable de `{transicion_id, de_estado, a_estado, motivo, actor (ia\|entidad\|sistema), timestamp}` | Nunca se reescribe un asiento; una corrección es un asiento nuevo (`ajuste`), igual que en un libro contable. |
| `creado_en` | timestamp | Del primer asiento (`detectada`). |

---

## 2. Origen de cada campo: IA (extracción) vs dominio (dato verificado)

Principio rector (regla de oro): **la IA propone, el dominio valida**. En la práctica
del contrato:

- **Rellenados por IA (extracción de texto no estructurado → campos tipados):**
  `Convocatoria.objeto`, `Convocatoria.beneficiarios_elegibles` (texto descriptivo),
  `Convocatoria.requisitos_elegibilidad` (primera pasada estructurada),
  `Convocatoria.ambito_geografico`, `Convocatoria.plazos`, `Convocatoria.cuantias`,
  `Convocatoria.fuente.tipo` (primera pasada), `Match.explicacion_ia`.
- **Verificados/decididos por dominio (determinista, sin intervención de modelo):**
  todo campo de `Entidad` (lo declara la propia entidad o el operador, nunca se
  infiere), `Match.resultado_elegibilidad_dura` (evaluación de
  `requisitos_elegibilidad` contra los datos de `Entidad` — código determinista, sin
  LLM en el camino de decisión), `Match.estado_actual` y sus `asientos` (transiciones
  las dispara la entidad o el sistema, nunca "porque la IA lo decidió"),
  `Convocatoria.estado_ingesta`.
- **Frontera exacta:** aunque la IA puebla `requisitos_elegibilidad`, ese campo, una
  vez escrito, es un dato estructurado ordinario. El guardarraíl que decide
  "esta Entidad es elegible o no" es una función determinista dominio→booleano que
  lee ese campo y los de `Entidad`; no vuelve a invocar el modelo. Si la extracción
  IA falla o el texto es ambiguo, el campo queda marcado como incompleto/sospechoso
  (`estado_ingesta = extraida` sin pasar a `verificada`) y el match para esa
  convocatoria no se marca elegible por defecto — degrada limpio, nunca inventa.

---

## 3. Alternativas consideradas y por qué no

### 3.1 Schema libre por JSON vs contrato tipado

- **Opción descartada:** guardar `Convocatoria` (y/o `Entidad`) como blob JSON semi-
  estructurado, dejando que cada extracción IA defina sus propias claves según lo que
  encuentre en el texto.
- **Por qué no:** rompe la regla de oro CONTRATO CONGELADO y hace imposible un
  guardarraíl determinista de elegibilidad — evaluar "¿cumple el requisito X?" sobre
  un JSON de forma libre requiere que el propio LLM interprete la estructura en cada
  consulta, lo que reintroduce IA en el camino de decisión. También imposibilita el
  test anti-fuga cross-tenant y el anti-hardcoding, que necesitan columnas conocidas.
- **Lo que sí se admite:** un campo de "extras" no estructurado y explícitamente
  fuera de contrato (p. ej. `notas_extraccion_libre`) para no perder información que
  el pipeline de ingesta no sabe mapear todavía, pero que **nunca** participa en la
  evaluación de elegibilidad ni en matching automático.

### 3.2 Matching todo-IA vs híbrido

- **Opción descartada:** pedir al LLM que, dado el texto de la convocatoria y el
  perfil de la entidad, diga directamente "sí encaja" / "no encaja".
- **Por qué no:** viola la regla de oro "la IA propone, el dominio valida" y hace que
  la elegibilidad (que a menudo es binaria y auditable — ámbito, forma jurídica,
  certificados) dependa de la consistencia de un modelo no determinista. Una entidad
  que pierde una subvención por un falso negativo de IA, o que presenta una solicitud
  a la que no es elegible por un falso positivo, tiene coste real (tiempo, credibilidad
  ante el financiador). Es inaceptable para el dominio de "técnico de subvenciones".
- **Decisión adoptada:** híbrido — extracción y explicación por IA, evaluación de
  requisitos duros 100% determinista sobre `requisitos_elegibilidad` estructurados,
  IA reservada para ordenar/explicar/sugerir sobre el conjunto ya filtrado
  deterministamente (F3).

---

## 4. Consecuencias

### 4.1 Qué se congela en CLAUDE.md

Al aceptar este ADR, CLAUDE.md debe actualizarse (en un prompt de fase, no en este
documento) para fijar en la sección "CONTRATO CONGELADO":

- Nombre del contrato: **Entidad / Convocatoria / Actividad / Match** (este ADR,
  `engineering/ADR-001-contrato-de-datos.md`).
- Ruta de implementación prevista (se fija en PROMPT F1, no aquí, para no adelantar
  código): módulo de dominio bajo `src/ongs_ai/dominio/` (nombre tentativo — el
  prompt F1 lo confirma o corrige de forma conservadora).
- Regla: cualquier cambio a los campos de estas cuatro entidades exige ADR nuevo
  (ADR-002, etc.), nunca edición de este fichero ni migración silenciosa de schema.

### 4.2 Aislamiento por tenant

- `Entidad` es el tenant. `Match` (y cualquier futura tabla de propuesta/preparación)
  lleva `entidad_id` explícito y es la única vía de acceso — regla de oro ya fijada
  en CLAUDE.md.
- `Convocatoria` **no** es dato de tenant: es compartida (una misma convocatoria
  puede generar `Match` para varias entidades). El test anti-fuga cross-tenant se
  centra en `Match` y en cualquier vista que combine `Entidad` + `Convocatoria`:
  una consulta con `entidad_id=A` nunca debe poder leer `Match`, `asientos`, ni datos
  económicos de `entidad_id=B`.
- `datos_economicos_ejercicio_anterior` y `requisitos_formales_disponibles` son los
  campos con mayor sensibilidad de fuga cross-tenant (son los que más se usan en
  evaluación de elegibilidad) — el test anti-fuga de F1 debe cubrirlos explícitamente.

### 4.3 Anti-hardcoding

- Ninguna enfermedad, colectivo o entidad concreta aparece en el schema, en el código
  de plataforma ni en plantillas: `enfermedad_o_colectivo` es un **valor de dato**
  de `Entidad`, nunca un enum ni una constante de código. Mismo criterio para nombres
  de portales de convocatorias (`fuente.portal` es dato, la lista de portales vive
  en configuración de adapters de ingesta — F2 — no en el contrato).
- Único enum cerrado de dominio "de negocio" es `Actividad` (§1.3), y está pactado
  como extensible solo por ADR, precisamente para que crecer la lista sea una
  decisión explícita y no una entrada de datos disfrazada de código.
- El test anti-hardcoding (ya exigido por CLAUDE.md desde el día 1) debe, a partir de
  F1, incluir un caso concreto: crear una `Entidad` con una enfermedad rara inventada
  en el test y comprobar que ningún fichero de plataforma la menciona ni depende de
  su valor literal.

### 4.4 PII y datos sensibles

- **v1 no maneja datos de pacientes.** Todo el contrato opera a nivel de `Entidad`
  (la asociación) y `Convocatoria` (pública o de fuente privada, no personal). No hay
  entidad "Paciente" ni "Socio" en este ADR.
- `datos_economicos_ejercicio_anterior` (ingresos/gastos de la entidad) y `nif` se
  tratan como sensibles: nunca hardcodeados, nunca en fixtures de test con datos
  reales, y su almacenamiento sigue la regla ya vigente de CLAUDE.md — PII fuera de
  git (`.env`, `var/`), gitignorado desde el commit 1.
- Cuando exista entidad piloto real (bandeja del operador, aún sin captar), sus datos
  económicos reales nunca se commitean como fixture; los tests usan datos sintéticos.

---

## 5. Fases de implementación (sin código — orientación + 1 prompt completo por fase)

Cada fase se lanza como prompt independiente, en serie (el fichero central de
dominio se toca en cada una), con el mismo preámbulo de política de decisión.
Los prompts F2–F5 solo se detallan en su cabecera de objetivo aquí; el **arquitecto**
redacta el texto completo de cada uno cuando la fase anterior esté HECHA y
AUDITADA, para poder incorporar lo aprendido (nombres reales de ficheros, etc.) —
redactar las cinco palabra por palabra hoy arriesga prompts basados en una fase que
aún no existe. Lo que sigue es la orientación mínima pactada en este ADR más el
prompt completo de F1 (la única fase desbloqueada ahora mismo).

### F1 — Contrato + persistencia + tests anti-fuga/anti-hardcoding

- **Objetivo:** implementar `Entidad`, `Convocatoria`, `Actividad`, `Match` tal como
  los define este ADR, con persistencia mínima (adapter SQLite por defecto, `:memory:`
  para tests, con factory por entorno), y los tests obligatorios de CLAUDE.md desde
  la primera tabla de dominio: anti-fuga cross-tenant y anti-hardcoding.
- **Ficheros previstos (tentativo, el prompt puede ajustarlos de forma conservadora):**
  `src/ongs_ai/dominio/entidades.py` (modelos + enums), `src/ongs_ai/dominio/matching_estado.py`
  (máquina de estados de Match/asientos), `src/ongs_ai/adapters/persistencia/sqlite.py`,
  `src/ongs_ai/adapters/persistencia/memoria.py`, `tests/test_anti_fuga_tenant.py`,
  `tests/test_anti_hardcoding.py`, `tests/test_dominio_entidades.py`.

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
fichero entero.

TAREA: implementar el contrato de datos de ADR-001
(engineering/ADR-001-contrato-de-datos.md) — léelo completo primero, es la
fuente congelada — para el proyecto ONGs-AI.

1. Modela `Entidad`, `Convocatoria`, `Actividad` (enum cerrado v1 tal cual
   §1.3 del ADR) y `Match` (con sus asientos inmutables) exactamente con
   los campos de las tablas del ADR, en dominio puro (sin dependencias de
   framework web ni de IA).
2. Dinero SIEMPRE en céntimos enteros (int), nunca float — valida esto con
   un test explícito que rechace/tipe fuera floats en esos campos.
3. Persistencia con factory por entorno: adapter real (SQLite, ALTER TABLE
   idempotente si hace falta versionar el esquema) por defecto, adapter en
   memoria (`:memory:` o estructura Python pura) para tests. Los tests
   jamás tocan red ni fichero real de SQLite en disco compartido.
4. Test anti-fuga cross-tenant: crea dos Entidades, un Match de cada una,
   y comprueba que una consulta con `entidad_id` de la primera nunca
   devuelve datos (Match, asientos, datos económicos) de la segunda.
5. Test anti-hardcoding: crea una Entidad con una enfermedad rara
   inventada por el test (no una real) y comprueba que ningún fichero de
   `src/ongs_ai/` fuera de datos de test la menciona ni depende de su
   valor literal.
6. Test de máquina de estados de Match: las transiciones solo pueden
   seguir el orden `detectada → propuesta → (aceptada|descartada) →
   en_preparacion → presentada`; cada transición crea un asiento nuevo,
   nunca reescribe uno existente (comprueba inmutabilidad, p. ej. con
   estructura de solo-añadir o excepción al intentar mutar un asiento
   pasado).
7. Actualiza CLAUDE.md, sección CONTRATO CONGELADO: fija el nombre
   ("Entidad/Convocatoria/Actividad/Match, ADR-001") y la ruta real de los
   ficheros de dominio que hayas creado en el paso 1.
8. `python -m pytest -q` VERDE (herméticos: sin red, sin depender de
   .env de la máquina).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
git status antes del add (ni .env, ni var/, ni datos reales de entidad),
sin push si aún no hay remoto (anótalo).
```

### F2 — Ingesta de convocatorias

- **Objetivo:** adapters de ingesta por portal (uno por fuente), con red inyectable
  y apagada en tests (fixtures de HTML/JSON grabadas), que producen `Convocatoria`
  en estado `detectada`/`extraida` según el contrato de F1.
- **Ficheros previstos:** `src/ongs_ai/adapters/ingesta/<portal>.py` (uno por fuente,
  cuando exista la lista real de portales — bandeja del operador), `src/ongs_ai/adapters/ingesta/base.py`
  (interfaz común + factory red real/stub), `tests/fixtures/ingesta/`, `tests/test_ingesta_*.py`.
- **Bloqueo real:** necesita la lista concreta de portales/fuentes (bandeja del
  operador, §6). El prompt completo lo redacta el arquitecto cuando F1 esté
  AUDITADO y la lista de portales exista.

### F3 — Matching determinista + capa IA explicativa

- **Objetivo:** función determinista `Entidad × Convocatoria → resultado_elegibilidad_dura`
  (guardarraíl, sin LLM) más capa IA que ordena/explica sobre el subconjunto ya
  filtrado (`Match.explicacion_ia`), con degradación limpia si la IA falla.
- **Ficheros previstos:** `src/ongs_ai/dominio/elegibilidad.py` (determinista, sin
  imports de IA), `src/ongs_ai/ia/explicacion_match.py` (capa IA aislada, mockeable),
  `tests/test_elegibilidad_deterministas.py`, `tests/test_explicacion_ia_degrada.py`.
- El prompt completo lo redacta el arquitecto tras F1 AUDITADO.

### F4 — Propuesta / aviso

- **Objetivo:** transición `propuesta` con mecanismo de aviso a la entidad (canal por
  definir — email es el default conservador) y registro del asiento correspondiente;
  transición a `aceptada`/`descartada` por acción de la entidad.
- **Ficheros previstos:** `src/ongs_ai/dominio/propuesta.py`, `src/ongs_ai/adapters/avisos/`
  (email real + stub para tests), `tests/test_propuesta_aviso.py`.
- El prompt completo lo redacta el arquitecto tras F3 AUDITADO.

### F5 — Preparación asistida

- **Objetivo:** transición a `en_preparacion`/`presentada`; generación de borradores
  de documentos de solicitud asistidos por IA (la entidad presenta, la plataforma no
  envía nada en nombre de la entidad sin acción explícita — alcance exacto pendiente,
  ver §6).
- **Ficheros previstos:** `src/ongs_ai/dominio/preparacion.py`, `src/ongs_ai/ia/redaccion_borrador.py`,
  `tests/test_preparacion_borrador.py`.
- El prompt completo lo redacta el arquitecto tras F4 AUDITADO y tras resolver la
  pregunta de alcance de §6.

---

## 6. Preguntas al operador (agrupadas, con default cada una)

1. **Ruta/nombre exacto del módulo de dominio en F1** (`src/ongs_ai/dominio/` vs otra
   convención) — **default: `src/ongs_ai/dominio/` tal como se usa en este ADR**;
   ajustable sin coste porque aún no existe código.
2. **Alcance exacto de "desarrollar la solicitud" (F5)**: ¿borrador de memoria
   narrativa, formularios estructurados del portal, o ambos? — **default: borrador de
   memoria narrativa en texto/Markdown; la entidad copia/adapta al formulario oficial
   del portal**, por ser lo más simple y reversible sin integrarse con formularios de
   terceros.
3. **Canal de aviso (F4)**: ¿email, notificación en la propia plataforma, ambos? —
   **default: email**, por ser el canal que no exige que la entidad entre a mirar
   (coherente con "la entidad se despreocupa de mirar continuamente").
4. **¿`Convocatoria` puede tener más de un `Match` activo simultáneo por Entidad**
   (reintentos tras `descartada`)? — **default: sí, se permite un `Match` nuevo tras
   uno `descartada` para la misma `Entidad`+`Convocatoria` (p. ej. cambian datos de la
   entidad y ahora sí es elegible); el histórico de asientos del `Match` anterior no
   se toca.**
5. **Idempotencia de re-ingesta**: si la misma convocatoria se detecta dos veces (dos
   pasadas del vigilante), ¿se identifica por `url_origen` o por hash de contenido? —
   **default: `url_origen` + `portal` como clave natural de deduplicación en F2**, más
   simple que hashing de contenido; se revisa si el portal reutiliza URLs para
   convocatorias distintas.

Ninguna de estas preguntas bloquea las fases F1–F3; sí conviene resolver la 2 y 3
antes de redactar los prompts completos de F4/F5.
