# <NOMBRE-PROYECTO> — reglas para Claude

<Una frase: qué es el producto. Visión y dominio: PROJECT_CONTEXT.md si existe.>
Plan operativo vigente y prompts por paso: `engineering/06_SIGUIENTES_PASOS.md`.

## Reglas de oro (INNEGOCIABLES — adapta la lista, mantén el espíritu)

- <CONTRATO CONGELADO: si el proyecto tiene un schema/contrato central, congélalo aquí
  con nombre y ruta. Enums cerrados. Nunca se modifica sin ADR.>
- Nada de datos de cliente/dominio hardcodeados en plataforma o plantillas — todo llega
  como datos (protégelo con tests anti-hardcoding desde el día 1 y no los debilites jamás).
- Si hay IA: la IA propone, el dominio valida — toda salida de modelo pasa guardarraíl
  determinista y degrada limpia; nunca inventa, nunca lanza excepciones al dominio.
- PII fuera de git: `.env`, `var/`, ficheros de clientes — gitignorados desde el commit 1;
  `git status` antes de cada commit.
- Superficies públicas sin fugas de datos internos (ids de workers, costes, tenants).

## Comandos

- Tests/CI: `<comando CI>` (debe salir VERDE antes de CUALQUIER commit; tests HERMÉTICOS:
  sin red, sin depender del .env de la máquina — los adapters de red van apagados en tests).
- Servidor local: `<comando>`.

## Ritual de cierre de CADA tarea

1. Chequeo sintáctico de cada fichero tocado (p. ej. `python -c "import ast; ..."`).
2. CI → VERDE.
3. Un prompt = UN commit, con el nº REAL de tests en el mensaje (nunca "<N>").
4. `git status` antes del add: ni .env, ni var/, ni datos de clientes.
5. `git push` al terminar.

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
