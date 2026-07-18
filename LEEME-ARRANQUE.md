# Cómo arrancar un proyecto nuevo con este método

Kit destilado de travel-ai-blueprint (semana 2026-07-13/19: 2 ADRs, ~40 prompts
ejecutados y auditados, 1267→1546 tests). Pasos:

## 1. Prepara la carpeta

```
mkdir C:\dev\<proyecto-nuevo>
cd C:\dev\<proyecto-nuevo>
git init
mkdir engineering
mkdir .claude\agents
```

Copia del kit:
- `CLAUDE.md` → raíz del repo. RELLENA los <placeholders> (nombre, comandos, reglas de
  oro del dominio nuevo) — 10 minutos que valen la semana.
- `06_SIGUIENTES_PASOS.md` → `engineering/`. Crea también un `engineering/06_HISTORICO.md`
  vacío con un título.
- `ux-reviewer.md` → `.claude/agents/` (ajusta la "vara de medir" al sistema visual del
  proyecto nuevo cuando exista). Añade a `.gitignore` la excepción `!.claude/agents/`.
- `.gitignore` desde el día 1: `.env`, `var/`, datos de clientes, `__pycache__`, `*.log`.

## 2. Abre el proyecto en Cowork

Nuevo proyecto de Cowork apuntando a `C:\dev\<proyecto-nuevo>`. Esa conversación ES el
arquitecto. Pega el "Prompt de arranque del arquitecto" del 06 (rellenados nombre y ruta).

La memoria persistente del espacio de Cowork ya contiene las lecciones operativas de esta
máquina (mount, git desde sandbox, McAfee…) — el arquitecto nuevo las hereda solo.

## 3. El ciclo de trabajo (el método entero en 6 líneas)

1. Tú pides producto → el arquitecto lo convierte en spec/prompt (o ADR si es grande).
2. Los prompts viven en el 06, completos, con su MODELO en la cabecera.
3. Tú los pegas en sesiones de Claude Code (terminal) — una sesión, un prompt, un commit.
4. La sesión cierra con el ritual (CI verde, nº real de tests, push).
5. El arquitecto audita el CÓDIGO REAL (no el resumen) → APROBADO o correcciones.
6. Lo cerrado viaja al histórico; el 06 solo enseña lo que queda.

## 4. Reglas que no se negocian desde el minuto uno

- Tests herméticos desde el primer commit (la deuda de tests no se paga, se arrastra).
- Anti-hardcoding con test si el dominio lo pide.
- Serie por defecto; paralelo solo con ficheros disjuntos DE VERDAD.
- ADR antes de cualquier cosa que huela a dinero, seguridad o contrato de datos.
- El operador verifica en navegador/dispositivo real lo que las sesiones no pueden.
