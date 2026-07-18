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
- **ADR-002 CERRADO Y AUDITADO — HECHO e97baa5, 63 tests (2026-07-18):** `Entidad`
  gana `forma_juridica` y `fecha_constitucion` + `normalizar_forma_juridica`
  determinista. Detalle en histórico. **F3 desbloqueada → PROMPT-007 EN COLA.**
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

#### PROMPT-007 — F3: guardarraíl determinista de elegibilidad + capa IA explicativa · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: F3 del ADR-001 (léelo, y el ADR-002) — guardarraíl determinista de
elegibilidad + capa IA explicativa. La IA propone, el dominio valida.

1. `src/ongs_ai/dominio/elegibilidad.py` — función PURA y determinista
   (sin IA, sin red, sin reloj implícito):
   `evaluar_elegibilidad(entidad, convocatoria, fecha_referencia: date)
   -> ResultadoElegibilidad`. Reglas:
   a. `estado_ingesta != VERIFICADA` → elegible=False (motivo: datos sin
      verificar; ADR-001 §2 — nunca elegible por defecto).
   b. Ámbito: convocatoria NACIONAL acepta cualquier entidad; AUTONOMICO
      exige misma `region` (comparación normalizada: minúsculas, sin
      tildes, espacios colapsados — reutiliza/extrae el normalizador de
      ADR-002); PROVINCIAL exige misma `provincia`; LOCAL → NO EVALUABLE
      en v1 (el contrato no tiene `municipio`; anótalo en el detalle).
      Dato necesario ausente en cualquiera de los dos lados → NO EVALUABLE.
   c. `forma_juridica_requerida`: None → no aplica; texto →
      `normalizar_forma_juridica`; sin mapeo → NO EVALUABLE; con mapeo →
      compara con `entidad.forma_juridica.tipo`; entidad con OTRA nunca
      casa automáticamente.
   d. `antiguedad_minima_anios`: años COMPLETOS entre `fecha_constitucion`
      y `fecha_referencia` (aniversario no alcanzado no cuenta — testea el
      borde del día exacto).
   e. `requisitos_formales_requeridos` ⊆ `requisitos_formales_disponibles`.
   f. `exclusiones` (texto libre): NO se evalúan automáticamente en v1 —
      no bloquean, pero aparecen en el detalle como "revisar manualmente".
   Regla global: cualquier requisito NO EVALUABLE ⇒ elegible=False (no
   elegible automático ≠ excluida — el detalle lo distingue). `detalle`:
   string legible línea a línea (requisito → cumple / incumple /
   no_evaluable / revisar).
2. `src/ongs_ai/ia/explicacion_match.py` (+ `__init__.py` del paquete):
   Protocol `GeneradorExplicacion` (mockeable) y una ÚNICA implementación
   v1: `ExplicadorStub`, determinista, sin red (el proveedor LLM real lo
   decidirá el arquitecto más adelante). Si el generador lanza o devuelve
   vacío, el llamador sigue con `explicacion_ia=None`: la IA JAMÁS lanza
   al dominio ni altera la elegibilidad.
3. `src/ongs_ai/dominio/matching.py` — servicio determinista
   `detectar_matches(entidades, convocatorias, fecha_referencia,
   generador_explicacion=None, generador_ids, reloj=...) -> list[Match]`
   (ids y timestamps SIEMPRE inyectados, nada de now()/uuid4() implícitos
   en dominio): evalúa cada pareja, crea Match en estado `detectada`
   (asiento actor=sistema) con `resultado_elegibilidad_dura` SIEMPRE
   informado; `explicacion_ia` solo si elegible y el generador responde.
   La transición a `propuesta` es F4 — NO la implementes.
4. Tests: una batería por regla (cumple/incumple/no_evaluable), borde de
   aniversario exacto, convocatoria sin verificar, OTRA nunca casa,
   exclusiones no bloquean pero aparecen en el detalle, degradación IA
   (stub que lanza → Match válido sin explicación, sin excepción),
   `detectar_matches` produce Matches `detectada` correctos, y el
   anti-hardcoding sigue verde (ninguna región/provincia/enfermedad real
   hardcodeada en plataforma — solo en datos de test).
5. `python -m pytest -q` VERDE, herméticos.
6. Incluye en tu commit los cambios de `engineering/06_*` del working
   tree, tal cual están (cierre de ADR-002 por el arquitecto).

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add, `git push` al terminar.
```

### Bandeja del OPERADOR

- Pegar PROMPT-007 (F3) en una sesión de Claude Code (Sonnet) y avisar al arquitecto
  al terminar para auditoría.
- **Captar entidad piloto** (acceso + ingresos/gastos del ejercicio anterior +
  lista de actividades). El arquitecto ofrece redactar el mensaje de propuesta.
- (La lista de portales ya NO es tuya: la cubre R1 del arquitecto, en curso.)

### Backlog

- F2 ingesta (bloqueada por lista de portales) · F3 matching+IA explicativa ·
  F4 propuesta/aviso · F5 preparación asistida — el arquitecto redacta cada prompt
  al quedar AUDITADA la fase anterior (pactado en ADR-001 §5).
- Endurecer el test anti-hardcoding (el canario del ADR pasa por construcción) — F3+.
- Esqueleto de la app (fija el comando de servidor local en CLAUDE.md) — tras F1.
- Modelo de negocio (las entidades objetivo tienen pocos recursos) — conversación
  de producto, sin prisa técnica.
- Ajustar la "vara de medir" de ux-reviewer.md cuando exista sistema visual propio.

### Recordatorios operativos

- Máquina Windows: comandos como `python -m pytest -q` (no rutas unix); rutas con `C:\dev\ongs-ai`.
- Mount sandbox↔host miente con ficheros recién editados — el HOST es la verdad.
- Git desde sandbox: SOLO `git log`/`git show`; jamás status/diff (index.lock huérfanos).
- JSONs/salidas grandes siempre como archivo, jamás pegadas al chat.
