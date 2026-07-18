# 06 HISTÓRICO — arqueología de ONGs-AI

## Semana 2026-07-13/19

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
