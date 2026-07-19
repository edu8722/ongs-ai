# 06 HISTÓRICO — arqueología de ONGs-AI

## Semana 2026-07-13/19

- **PROMPT-009 — F2-fix: ámbito provincial (NUTS3) en el adapter BDNS** (Sonnet) —
  **HECHO 6a50af2, APROBADO (auditoría independiente del arquitecto, DESDE GIT), 133
  tests. F2-fix CERRADA.** Bug destapado por el smoke test del operador contra la API
  viva: los códigos NUTS3 (provincia, "ES"+3 dígitos: Bizkaia, Pontevedra, Córdoba) se
  etiquetaban `ambito_geografico=AUTONOMICO` con la provincia en `region`.
  `_ambito_y_region_desde_regiones` pasa a devolver terna (ambito, region, provincia) y
  deriva por nº de dígitos tras "ES": 2 (NUTS2)→AUTONOMICO/region, 3 (NUTS3)→PROVINCIAL/
  provincia, resto (no-ES, no numérico, otro nº de dígitos, cero/multi región)→NACIONAL
  conservador; `_mapear_convocatoria` rellena ambos campos. SIN tocar contrato
  (PROVINCIAL y Convocatoria.provincia ya existían) ni esquema. Fixture detalle_100003
  ahora "ES613 - Córdoba" (nivel1 LOCAL) → test espera PROVINCIAL/provincia="Córdoba"/
  region=None, conservando la prueba de ortogonalidad tipo↔ámbito. +7 tests unitarios
  directos sobre la función pura (todas las ramas) en vez de fixtures de pipeline —
  decisión del empleado, aprobada por el arquitecto (más aislado). Derivar CCAA desde
  NUTS3 (tabla NUTS3→NUTS2) fuera de alcance, anotado en docstring. LECCIÓN VIVA: el
  mount sandbox↔host mintió con el fichero recién editado (devolvió la versión antigua);
  la auditoría se hizo con `git show 6a50af2:...` — inmutable. Reafirma el quirk: para
  auditar tras un commit reciente, `git show`, nunca el mount.
- **PROMPT-008 — F2: ingesta de convocatorias vía API BDNS** (Sonnet) —
  **HECHO 5a52d27, APROBADO (auditoría independiente del arquitecto), 126 tests.
  F2 CERRADA.** `adapters/ingesta/base.py` (Protocol `FuenteConvocatorias`,
  Protocol `TransporteHTTP` inyectable, `FiltrosBusqueda` como datos,
  `TransporteURLLib` stdlib solo para el smoke); `adapters/ingesta/bdns.py`
  (`FuenteBDNS`: búsqueda paginada + detalle, mapeo determinista tipo/ámbito/
  región/dinero/plazos/beneficiarios/objeto, degradación limpia — búsqueda falla→
  corta y devuelve parcial, detalle falla→salta y sigue); `dominio/ingesta_estado.py`
  (`promocionar_si_completa` EXTRAIDA→VERIFICADA, función de dominio pura con campos
  mínimos documentados); puerto `obtener_por_url_origen` añadido y cumplido en
  `memoria.py` + `sqlite.py` (ALTER TABLE idempotente para columnas portal/url_origen
  + índice); `adapters/ingesta/servicio.py` (`ingestar` con dedupe por
  portal+url_origen); 6 fixtures JSON sintéticas ("ficticia"/"VILAFICTICIA", forma
  real de campos) + `scripts/smoke_bdns.py` manual fuera de CI. R1 committeada
  (xlsx+informe) y `.gitignore` gana `investigacion/asociaciones*`.
  Dinero: euros→céntimos `int` vía `Decimal(str()).scaleb(2).quantize(HALF_UP)` —
  jamás float al dominio. Auditoría del arquitecto: leído el código real de todos
  los ficheros + reproducción en sandbox (sin pytest/PyPI) con shim mínimo: 0 fallos
  de import en `src`, 99 casos verdes / 0 rojos (71 sin fixture + 28 de
  persistencia/dedupe sobre ambos adapters), rutas de degradación comprobadas; los 7
  no reproducidos son `parametrize` de valores de F1/F3, no de F2. Decisiones
  documentadas del empleado (no bloqueantes): (1) `nivel1` sin mapeo → `publica_local`
  (más restrictivo); (2) región única `ES*` → siempre `autonomico` (NUTS2/NUTS3 sin
  desambiguar — candidato ADR); (3) `objeto` = descripcion + descripcionFinalidad;
  (4) parámetro `tipoBeneficiario` y nombres de campo de búsqueda sin verificar
  contra Swagger (caído) → los confirma el smoke test del operador. Notas de
  auditoría vivas en el 06: pendiente humano del smoke test; gap NUTS2/NUTS3 al
  ADR-003.
- **PROMPT-007 — F3: guardarraíl determinista + capa IA explicativa** (Sonnet) —
  **HECHO fc04348, APROBADO (auditoría del arquitecto), 101 tests. F3 CERRADA.**
  `elegibilidad.py` (6 reglas puras, no-evaluable ⇒ no elegible, detalle línea a
  línea), `matching.py` (detectar_matches con ids/reloj inyectados, Protocol de
  dominio propio), `ia/explicacion_match.py` (Protocol + ExplicadorStub; la IA
  degrada limpia, jamás decide). Hallazgo de auditoría: el contrato ADR-001 tiene
  redundancia de ámbito (`ambito_geografico`+region/provincia vs
  `requisitos_elegibilidad.ambito_territorial_requerido`, hoy sin consumir) →
  candidato ADR-003. Nota de diseño para F4: detectar_matches crea Match para TODA
  pareja (literal del prompt) — la política de persistencia/filtrado se decide en
  F4 (no persistir pares no elegibles a escala BDNS).
- **PROMPT-006 — ADR-002: Entidad gana forma jurídica y fecha de constitución**
  (Sonnet) — **HECHO e97baa5, APROBADO (auditoría del arquitecto), 63 tests.**
  Nota de proceso: la sesión escribió aquí "APROBADO" por su cuenta y sin hash antes
  de la auditoría — el veredicto real llegó después y coincidió; la regla "solo el
  arquitecto cierra y aprueba" quedó fijada en el preámbulo común a raíz de esto.
  ADR+código en una sola sesión (desviación autorizada por el arquitecto: cambio
  pequeño y cerrado).
  `engineering/ADR-002-entidad-forma-juridica-antiguedad.md`: cierra la grieta de
  contrato que dejaba a F3 sin datos de `Entidad` contra los que evaluar
  `antiguedad_minima_anios`/`forma_juridica_requerida`. `Entidad` gana
  `forma_juridica: FormaJuridicaDeclarada` (enum cerrado `FormaJuridica`:
  asociacion/fundacion/federacion_o_confederacion/otra, `descripcion` obligatoria
  si `otra` — mismo patrón que `ActividadDeclarada`) y `fecha_constitucion: date`,
  ambos obligatorios; la antigüedad NO se almacena, se calculará en F3 contra una
  fecha de referencia explícita. `normalizar_forma_juridica(texto) -> FormaJuridica
  | None` en dominio puro: mapeo cerrado determinista (minúsculas, sin tildes,
  sinónimos), sin LLM; `OTRA` nunca es resultado automático; texto no mapeable →
  `None` (no evaluable, degrada limpio). Serialización/deserialización actualizada
  en `AlmacenSQLite`; fixtures y round-trip de ambos adapters cubren los campos
  nuevos; CONTRATO CONGELADO en CLAUDE.md referencia ADR-002. F3 (PROMPT-007)
  queda desbloqueada, la redacta el arquitecto tras auditar este cierre.
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
  Refinamientos del arquitecto al encolar F1: `descartada`/`presentada` terminales
  (a `en_preparacion` solo desde `aceptada`); `porcentaje_max_financiable` en puntos
  básicos enteros. Nota: test anti-hardcoding del ADR es canario débil — mejorar en
  fase posterior.
- **PROMPT-002 — Higiene post-bootstrap** (Sonnet) — **HECHO 1f50ed8, APROBADO**.
  .gitattributes (EOL fijados en repo, renormalización sin churn); pytest>=8 como
  dev-dep; versión única (`dynamic` → `ongs_ai.__version__`); cierre de PROMPT-001
  en el mismo commit. Corrección de ritual: el commit original (7e05180) salió sin
  el nº de tests en el mensaje pese a que el resumen de la sesión decía lo contrario
  — amend del operador antes de existir remoto. Lección fijada en el 06: auditar
  siempre el mensaje real (`git log -1 --format=%s`).
- **PROMPT-001 — Bootstrap del repo** (Sonnet) — **HECHO 2101890, APROBADO**.
  git init -b main; .gitignore (env/var/clientes/caches); 06 → engineering/ +
  06_HISTORICO creado; ux-reviewer → .claude/agents/; esqueleto Python
  (src/ongs_ai, pyproject con pytest configurado, 1 smoke test VERDE).
  Notas menores de auditoría absorbidas en PROMPT-002: pytest no declarado como
  dependencia dev, line endings sin fijar, versión duplicada pyproject/__init__.
