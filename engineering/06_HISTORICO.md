# 06 HISTÓRICO — arqueología de ONGs-AI

## Semana 2026-07-13/19

- **PROMPT-006 — ADR-002: Entidad gana forma jurídica y fecha de constitución**
  (Sonnet) — **HECHO, APROBADO, 63 tests.** ADR+código en una sola sesión
  (desviación autorizada por el arquitecto: cambio pequeño y cerrado).
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
