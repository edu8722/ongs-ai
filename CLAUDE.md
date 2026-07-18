# ONGs-AI — reglas para Claude

Plataforma SaaS multi-tenant que actúa de técnico de subvenciones para entidades de
enfermedades raras: cada entidad es un tenant que gestiona su propia cartera y recibe
matching de convocatorias compatibles. Visión y dominio: `PROJECT_CONTEXT.md`.
Plan operativo vigente y prompts por paso: `engineering/06_SIGUIENTES_PASOS.md`.

## Reglas de oro (INNEGOCIABLES)

- CONTRATO CONGELADO: **Entidad / Convocatoria / Actividad / Match** (ADR-001,
  `engineering/ADR-001-contrato-de-datos.md`; ampliado por ADR-002,
  `engineering/ADR-002-entidad-forma-juridica-antiguedad.md` — Entidad gana
  `forma_juridica`/`fecha_constitucion` + normalizador determinista
  `normalizar_forma_juridica`). Implementado en `src/ongs_ai/dominio/entidades.py`
  (Entidad, Convocatoria, Actividad y value objects) y
  `src/ongs_ai/dominio/matching_estado.py` (Match, asientos, máquina de estados).
  Puertos de persistencia en `src/ongs_ai/dominio/puertos.py`; adapters en
  `src/ongs_ai/adapters/persistencia/` (`memoria.py`, `sqlite.py`, `factory.py`).
  Enums cerrados. Nunca se modifica sin ADR nuevo.
- AISLAMIENTO POR TENANT: ninguna lectura/escritura de datos de dominio sin `tenant_id`
  explícito; test anti-fuga cross-tenant desde que exista la primera tabla de dominio.
- Nada de datos de ONG/cliente hardcodeados en plataforma o plantillas — todo llega
  como datos (protégelo con tests anti-hardcoding desde el día 1 y no los debilites jamás).
- La IA propone, el dominio valida — toda salida de modelo pasa guardarraíl
  determinista y degrada limpia; nunca inventa, nunca lanza excepciones al dominio.
- Dinero SIEMPRE en enteros (céntimos) — cuotas, donaciones y costes incluidos. Jamás float.
- PII fuera de git: `.env`, `var/`, ficheros de ONGs reales — gitignorados desde el
  commit 1; `git status` antes de cada commit.
- Superficies públicas sin fugas de datos internos (ids de workers, costes, otros tenants).

## Comandos

- Tests/CI: `python -m pytest -q` (debe salir VERDE antes de CUALQUIER commit; tests
  HERMÉTICOS: sin red, sin depender del .env de la máquina — los adapters de red van
  apagados en tests).
- Servidor local: PENDIENTE — se fija en el prompt del esqueleto de la app (PROMPT-002).

## Ritual de cierre de CADA tarea

1. Chequeo sintáctico de cada fichero tocado (p. ej. `python -c "import ast; ast.parse(open('fichero.py').read())"`).
2. CI → VERDE.
3. Un prompt = UN commit, con el nº REAL de tests en el mensaje (nunca "<N>").
4. `git status` antes del add: ni .env, ni var/, ni datos de ONGs.
5. `git push` al terminar (si aún no hay remoto, anótalo en el resumen final).

## Arquitectura (mapa rápido — rellena al crecer)

- Puertos+invariantes en dominio · adapters con factories por entorno (backend real por
  defecto, `:memory:`/stub para tests) · workers deterministas con red inyectable ·
  rutas de cada feature en MÓDULO PROPIO (el fichero central solo gana includes).
- Patrones que pagan: ALTER TABLE idempotente para migrar; claves por id de entidad,
  nunca por nombre; overlay para intención humana que ningún hecho materializa;
  registros contables como asientos inmutables (ajustes, jamás reescrituras);
  dinero SIEMPRE en enteros (céntimos), jamás float.

## Lecciones que costaron caras (heredadas de travel-ai-blueprint)

- Dos sesiones en paralelo SOLO con ficheros realmente disjuntos; si ambas tocan el
  fichero central aunque sea una línea (import, include, gancho) → EN SERIE.
- Tests herméticos o no son tests; un test que tarda >1s en red, algo está mal.
- Rutas de almacenes/DB SIEMPRE absolutas o ancladas al repo — un default relativo al
  CWD crea bases gemelas y "pérdidas" fantasma.
- La proyección/render jamás lanza por un dato feo: descarta, marca sospecha, sigue.
- Los cambios de prompts de IA = versión nueva + CHANGELOG, jamás editar la vieja.

## Dieta de contexto (OBLIGATORIA)

- El 06 vivo lleva SOLO pendientes + estado de la última semana; lo cerrado viaja a
  `06_HISTORICO.md` en el mismo commit en que se cierra.
- Ficheros grandes: Grep al símbolo y leer el rango — nunca lectura completa por defecto.
