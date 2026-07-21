# ADR-005 — Esqueleto de la aplicación web y autenticación multi-tenant

- **Estado:** PROPUESTA (pendiente de aprobación del operador) — 2026-07-21.
- **Contexto de fase:** F1 ✔ · ADR-002 ✔ · F3 ✔ · F4.1 ✔ · F4.2 ✔. Este ADR abre el
  esqueleto web (backlog de ADR-004 §2.7) y precede a F5.
- **Relación:** amplía ADR-004 §2.5 (canal "panel") y §2.7 (alcance: F4 entregó backend
  + read model + puerto de notificación; la UI queda pendiente, aquí se resuelve). NO
  modifica el contrato congelado (Entidad/Convocatoria/Actividad/Match, ADR-001/ADR-002)
  ni la máquina de estados (`matching_estado.py`). Añade, de forma aditiva, dos piezas de
  infraestructura de autenticación al puerto de persistencia (§5) — no son parte del
  contrato de dominio y no lo alteran.
- **Documento SOLO decisión** — sin código de producción; el código lo entrega F-web.1
  (§6).

## 1. Contexto y problema

El backend está completo hasta F4.2: ingesta BDNS, elegibilidad determinista, detección
y propuesta automática con aviso por email real (`adapters/avisos/email_smtp.py`), y un
read model de solo lectura por tenant (`servicios/panel.py::resumen_panel`). Falta la
única pieza que convierte esto en un producto usable: la capa web donde cada entidad
(tenant) entra, ve sus propuestas agrupadas por estado y decide.

Dos problemas a resolver, uno de arquitectura y uno de seguridad:

1. **Arquitectura**: qué stack sirve HTML, cómo se organizan las rutas sin romper la
   regla de CLAUDE.md de "fichero central solo gana includes", y qué mínimo nuevo hace
   falta en los puertos de persistencia.
2. **Seguridad (el riesgo real de este ADR)**: cómo se identifica a una entidad sin
   contraseñas que custodiar, y cómo se garantiza **por construcción** — no por
   disciplina de cada ruta — que el `entidad_id` que llega a `resumen_panel` es siempre
   el de la sesión autenticada y jamás un valor que el cliente pueda manipular. Un fallo
   aquí es un incidente de aislamiento cross-tenant, la regla de oro más cara de romper
   en este proyecto.

Usuario objetivo (`PROJECT_CONTEXT.md`): asociaciones con 0–muy poco personal, sin
técnico de proyectos. La UI debe pedir lo mínimo posible (nada de gestionar
contraseñas) y el operador (no la entidad) da de alta cada tenant.

## 2. Decisión

### 2.1 Stack web: FastAPI + uvicorn + Jinja2 (SSR), sin SPA en v1

Se adopta **FastAPI + uvicorn + plantillas Jinja2 renderizadas en servidor**. Sin
frontend SPA (React/Vue + build propio) en v1.

Justificación:

- El dominio ya es dataclasses tipadas y frozen (`entidades.py`, `matching_estado.py`).
  FastAPI encaja porque su capa de rutas es tipos + inyección de dependencias, no exige
  duplicar el contrato en esquemas Pydantic paralelos: en v1 no hay API JSON pública, así
  que las rutas pasan los objetos de dominio directamente al contexto de Jinja2. Esto
  mantiene la frontera "la IA propone, el dominio valida" (CLAUDE.md) limpia — la capa
  web es un renderizador fino sobre objetos ya validados, sin lógica de negocio propia
  que pueda desincronizarse del guardarraíl.
- uvicorn es el servidor ASGI estándar para FastAPI; sin necesidad de gunicorn/workers
  múltiples en v1 (tráfico de una entidad piloto y, a corto plazo, un puñado de tenants).
- Jinja2 SSR evita un toolchain de build de JS por completo — coherente con un producto
  para asociaciones sin personal técnico: menos superficie, menos dependencias, menos
  que mantener. Un panel de lectura + un par de formularios (login, aceptar/descartar)
  no necesitan un framework de cliente.
- Reversible: si más adelante hace falta interactividad rica, se puede añadir htmx
  (fragmentos SSR con `hx-*`) de forma incremental sin abandonar el modelo SSR ni
  reescribir el backend — no hace falta decidirlo ahora.

Rutas de cada feature en **módulo propio** (regla de CLAUDE.md), nunca en el fichero
central:

```
src/ongs_ai/web/
  app.py                  # ÚNICO fichero central: crea la app, monta middleware de
                           # sesión, hace app.include_router(...) por módulo — NADA más.
  dependencias.py          # entidad_actual(request) -> Entidad (§2.2/§2.3)
  rutas/
    auth.py                # /login, /login/confirmar, /logout
    panel.py                # /panel (F-web.1, solo lectura)
    # futuros: propuestas.py (aceptar/descartar, F-web.2), preparacion.py (F5), ...
  plantillas/
    base.html, login.html, panel.html, error.html
```

`app.py` importa cada router y lo incluye; una ruta nueva nunca añade lógica ahí, solo
un `include_router` más — igual que el patrón de "el fichero central solo gana
includes" que ya rige el resto del proyecto.

### 2.2 Autenticación multi-tenant: magic link por email, sin contraseñas

**Identificación de la entidad**: cada `Entidad` ya tiene `contacto.email` (contrato
ADR-001, `dominio/entidades.py`). Ese email, dado de alta por el operador al crear la
entidad (§2.2.4), es el único identificador de login. No hay contraseña que custodiar,
resetear ni filtrar en una brecha.

**Flujo (magic link)**:

1. `GET /login` — formulario que pide solo el email.
2. `POST /login` — busca la entidad por email (`RepositorioEntidades`, nuevo método
   `obtener_entidad_por_email`, §5). Si existe: genera un token de un solo uso, lo
   persiste **hasheado** (nunca el token en claro) con expiración corta (default 15
   min, §7), y envía un email con el enlace `GET /login/confirmar?token=...` reutilizando
   la infraestructura SMTP de F4.2 (`ClienteSMTP`/`ConfiguracionSMTP` de
   `adapters/avisos/email_smtp.py`) tras una nueva clase de envío específica para el
   enlace de acceso (plantilla propia, sin reutilizar `Notificador.notificar_propuesta`
   que es un concepto de negocio distinto). Si el email NO existe: **misma respuesta
   genérica** ("si el correo está dado de alta, se ha enviado un enlace") — no se filtra
   si un email está o no registrado (anti user-enumeration).
3. `GET /login/confirmar?token=...` — consume el token (operación atómica
   check-and-mark-used, §5): si es válido, no expirado y no usado, crea una sesión
   firmada para esa `entidad_id` y redirige a `/panel`. Si es inválido/expirado/ya usado:
   página de error **genérica** (§2.4), nunca distingue el motivo exacto.
4. El token es de **un solo uso** — tras consumirse (válido o no), no vuelve a servir;
   si el destinatario reenvía o reutiliza el enlace, falla igual que uno caducado.

**Sesión**: cookie firmada (`itsdangerous`, vía `SessionMiddleware` de Starlette —
dependencia que FastAPI ya trae transitivamente) que contiene ÚNICAMENTE el
`entidad_id` (un id opaco, no PII) y la marca de tiempo de emisión. Firmada con una
clave (`ONGS_AI_SECRET_KEY`) leída SOLO en la composición de la app (mismo patrón que
`ONGS_AI_SMTP_*`: nunca hardcodeada, nunca en el adapter). Flags: `httponly=True`
siempre; `samesite="lax"` (permite la navegación GET desde el cliente de correo hasta
`/login/confirmar`); `secure=True` cuando la app corre bajo HTTPS (ver pregunta §7 sobre
hosting v1). Expira a las 12h (default, §7): pasado ese tiempo, nueva petición de magic
link — sin fricción de "recordar contraseña", coherente con el usuario objetivo.

**`entidad_id` de la sesión es la ÚNICA fuente que llega a `resumen_panel`** (§2.3).

**Gestión de credenciales — qué NO se hace en v1**:

- **Sin contraseñas**: cero superficie de custodia/hash/reset/fuerza bruta.
- **Sin autoregistro abierto**: las altas de entidad las hace el operador (fuera de la
  capa web pública; vía script/consola interna, no una ruta HTTP expuesta). Una entidad
  nunca puede crear su propio tenant desde el login.
- **Sin API pública / tokens de larga duración** en v1 (§3).

### 2.3 Aislamiento por tenant por construcción

La única función que puede producir un `entidad_id` para una petición HTTP es la
dependencia `entidad_actual(request) -> Entidad` (`web/dependencias.py`): lee la cookie
de sesión firmada, extrae `entidad_id`, resuelve la `Entidad` vía
`RepositorioEntidades.obtener_entidad`. Si la sesión no existe, está corrupta, caducada
o la entidad ya no existe → **401/redirect a `/login`**, nunca un fallback silencioso.

Regla dura para todas las rutas de dominio (panel y, después, aceptar/descartar): el
handler de FastAPI declara `entidad: Entidad = Depends(entidad_actual)` y usa
`entidad.entidad_id` para llamar a `resumen_panel`/`listar_matches_por_entidad`/etc. —
**ninguna ruta acepta jamás un `entidad_id` como parámetro de query, de path, de
formulario oculto ni de cabecera**. No existe una ruta tipo `/panel/{entidad_id}`; existe
`/panel` a secas, y el tenant sale exclusivamente de la sesión. Esto hace la fuga
cross-tenant no solo "testeada" sino estructuralmente imposible de introducir por accidente
en una ruta nueva, siempre que se siga usando `Depends(entidad_actual)` — que es
precisamente lo que el test anti-fuga a nivel HTTP (§4) verifica en cada ruta.

### 2.4 Superficies públicas sin fugas

| Ruta | Expone | No expone |
|---|---|---|
| `GET /login` | Formulario de email | — |
| `POST /login` | Mensaje genérico de confirmación | Si el email existe o no en el sistema |
| `GET /login/confirmar` | Redirect a `/panel` o error genérico | Motivo exacto de fallo (caducado vs. usado vs. inválido) |
| `GET /panel` | Propuestas/matches de LA PROPIA entidad (objeto, portal, fechas, cuantías, motivo si no elegible, `explicacion_ia`) | `match_id`/`convocatoria_id`/`entidad_id` internos como texto plano en la UI más allá de lo necesario para el formulario de acción; datos de OTRAS entidades; costes de plataforma (tokens IA, coste de scraping); ids de workers/procesos |
| `POST /logout` | — | — |
| Errores (4xx/5xx) | Página genérica ("algo falló, inténtalo de nuevo" / "sesión caducada") | Trazas, excepción Python, nombre de tabla/columna, versión de librería |

Jinja2 con **autoescape activado** (por defecto para plantillas `.html` en
`Jinja2Templates`) — control de seguridad, no cosmético: `convocatoria.objeto` y el resto
de campos de extracción IA son texto libre no confiable y deben tratarse como tal en el
render.

### 2.5 Resumen de decisión

Sesión firmada (no token en URL) ⇒ el `entidad_id` nunca viaja como parámetro
manipulable; magic link (no contraseña) ⇒ cero credenciales que custodiar; altas por
operador (no autoregistro) ⇒ el operador sigue siendo el único punto de entrada de un
tenant nuevo, coherente con el modelo actual (sin entidad piloto todavía puede
autoinscribirse nadie).

## 3. Alternativas consideradas y descartadas

- **SPA (React/Vue) + API JSON.** Añade un segundo runtime (Node), un toolchain de
  build, y obliga a espejar el contrato de dominio en esquemas de API. Para un panel de
  lectura + dos acciones (aceptar/descartar) es sobre-ingeniería; el usuario objetivo no
  necesita una app "rica". Descartada para v1; no cerrada para siempre (§2.1, ruta de
  htmx si hace falta más interactividad).
- **Contraseñas clásicas.** Añade custodia de secretos (hash+salt), flujo de "olvidé mi
  contraseña" (que además reintroduce el problema de "cómo verifico quién eres" por
  email de todos modos), y riesgo de credential stuffing/reutilización. El magic link ya
  resuelve "demuestra que controlas ese buzón" sin nada de eso. Descartada.
- **Sesión por token en la URL (`?token=...` persistente, no de un solo uso).** Un token
  que sirve para más de un login queda en el historial del navegador, en logs de
  servidor/proxy, en el "reenviar" de un cliente de correo — no se puede revocar de
  forma fina ni tiene expiración natural. Se usa un token de URL SOLO para el
  intercambio de un solo uso que arranca la sesión (paso 3 de §2.2); a partir de ahí,
  cookie firmada. Descartada como mecanismo de sesión continuada.
- **JWT sin estado como sesión.** Añade una librería y la complejidad de claims/firma
  asimétrica sin beneficio aquí (no hay API externa ni microservicios que verifiquen el
  token de forma independiente); una cookie firmada con `itsdangerous` es lo mínimo que
  resuelve "sesión con integridad verificable server-side". Se puede migrar a JWT si
  algún día hace falta SSO/API externa — no es un callejón sin salida. Descartada por
  ahora.
- **OAuth/SSO externo (Google, etc.).** Exige que la entidad tenga una cuenta
  compatible y añade una dependencia de un proveedor externo para un login que ya
  resuelve el magic link con la infraestructura de email que el proyecto ya tiene.
  Descartada para v1.

## 4. Consecuencias

- (+) Cero contraseñas que custodiar; superficie de credenciales mínima.
- (+) Aislamiento cross-tenant garantizado por construcción (§2.3), no solo por
  disciplina de cada ruta — el punto de fuga estaría en no usar `Depends(entidad_actual)`,
  que es exactamente lo que el test HTTP anti-fuga (abajo) puede detectar por inspección
  de rutas si se quiere reforzar más adelante.
- (+) Reutiliza infraestructura ya construida y auditada (SMTP de F4.2, read model de
  F4.2) — cero cambio de contrato.
- (−) Depende de que el email de la entidad esté siempre actualizado y accesible — si
  una entidad pierde acceso a su buzón, el operador necesita un procedimiento manual de
  recuperación (backlog, no bloqueante para F-web.1: dar de alta un nuevo email vía la
  misma vía interna que el alta inicial).
- (−) Primeras dependencias runtime del proyecto (hasta ahora solo `pytest` en dev) —
  justificadas una a una en §5.
- (Neutro) Nueva superficie de tests: la capa web se testea con el `TestClient` de
  FastAPI/Starlette (basado en `httpx`, en proceso, sin abrir socket real ni servidor) —
  sigue siendo hermético (CLAUDE.md). El test anti-fuga cross-tenant existente
  (`tests/test_anti_fuga_tenant.py`) gana un caso a nivel HTTP: login como entidad A,
  `GET /panel`, verificar que solo aparecen matches de A; y confirmar que no existe
  ninguna ruta que acepte un `entidad_id` ajeno como parámetro.
- (Neutro) CSRF: en F-web.1 los únicos POST son `/login` (envía un email a la dirección
  indicada — no depende de la sesión actual, impacto de un CSRF ahí es bajo: como mucho
  fuerza un envío de magic link no solicitado a un email que el propio atacante no
  controla) y `/logout` (sin impacto sensible). Las acciones de F-web.2
  (aceptar/descartar, que SÍ mutan estado de negocio bajo la sesión activa) exigen
  protección CSRF explícita (token de formulario) antes de implementarse — se deja
  anotado para el prompt de F-web.2, no se resuelve aquí.

### Dependencias runtime nuevas (primeras del proyecto)

Se fijan por **cota mínima conocida y estable** a la fecha de este ADR; el lockeo del
patch exacto se hace en el momento de instalar en F-web.1 (`pip install` + registrar la
versión resuelta en el propio commit) — no se inventa aquí un número de patch que no se
puede verificar sin red:

| Paquete | Cota mínima | Para qué |
|---|---|---|
| `fastapi` | `>=0.115` | Framework de rutas + inyección de dependencias |
| `uvicorn` | `>=0.30` | Servidor ASGI |
| `jinja2` | `>=3.1` | Plantillas SSR (ya viene con autoescape) |
| `itsdangerous` | `>=2.2` | Firma de la cookie de sesión (`SessionMiddleware`) |
| `python-multipart` | `>=0.0.9` | Parseo de formularios (`POST /login`) |
| `httpx` | `>=0.27` | Solo test/dev: requerido por `TestClient` |

Se añaden en `pyproject.toml` como dependencias de `[project]` (las cuatro primeras +
`python-multipart`, necesarias en producción) y `httpx` en `[project.optional-dependencies].dev`
junto a `pytest`.

### Comando de servidor local (para fijar en CLAUDE.md tras F-web.1)

```
uvicorn ongs_ai.web.app:app --reload   # desarrollo
uvicorn ongs_ai.web.app:app --host 0.0.0.0 --port 8000   # sin --reload en despliegue
```

## 5. Diseño técnico (para la fase)

Piezas nuevas de infraestructura de auth, aditivas al puerto de persistencia — **no
tocan el contrato congelado**:

- `RepositorioEntidades` (puerto existente, `dominio/puertos.py`) gana un método:
  `obtener_entidad_por_email(email: str) -> Entidad | None`. Implementado en AMBOS
  adapters (`memoria.py`, `sqlite.py`) con test de contrato parametrizado, mismo patrón
  que el resto del puerto.
- Puerto nuevo `RepositorioTokensAcceso` (`dominio/puertos.py`, junto a los demás —
  infraestructura de auth, no forma parte de Entidad/Convocatoria/Actividad/Match):
  - `crear_token(entidad_id: str, token_hash: str, expira_en: datetime) -> None`
  - `consumir_token(token_hash: str, ahora: datetime) -> str | None` — operación
    ATÓMICA: si existe, no expiró y no se ha usado, lo marca usado y devuelve
    `entidad_id`; en cualquier otro caso devuelve `None`. Un solo uso posible por token.
  - Implementado en `AlmacenMemoria` (dict) y `AlmacenSQLite` (tabla nueva
    `tokens_acceso`: `token_hash TEXT PRIMARY KEY, entidad_id TEXT, expira_en TEXT,
    usado_en TEXT NULL` vía `CREATE TABLE IF NOT EXISTS`, patrón idempotente ya usado en
    el esquema). Solo se persiste el **hash** del token (p. ej. sha256), nunca el valor
    en claro — igual que un token de reset de contraseña bien hecho.
- `servicios/autenticacion.py` (nuevo, como `servicios/propuestas.py`/`panel.py`: compone
  puertos, no es dominio puro): `generar_y_enviar_enlace(email, almacen_entidades,
  almacen_tokens, enviador_email, *, generador_token, reloj)` y
  `validar_y_consumir_token(token, almacen_tokens, reloj)`. Ids/token/reloj SIEMPRE
  inyectados (como F3/F4).
- `adapters/avisos/` gana la clase de envío del enlace de acceso (nombre propuesto:
  `EnviadorEnlaceAccesoSMTP`), reutilizando `ClienteSMTP`/`ConfiguracionSMTP` de
  `email_smtp.py` — mismo degradado limpio (log + contador, sin excepción) si el envío
  SMTP falla.
- `web/dependencias.py::entidad_actual` — única función autorizada a producir un
  `entidad_id` desde una `Request`.

## 6. Fases y prompts

- **F-web.1 — esqueleto + auth + panel de solo lectura** → prompt completo abajo.
- **F-web.2 — acciones aceptar/descartar** (orientación, sin prompt aún): formularios
  `POST` en `/panel` que llaman a `matching_estado.transicionar` con
  `actor=ActorAsiento.ENTIDAD`; requiere protección CSRF (token de formulario, §4);
  redirige de vuelta a `/panel` con el match movido de cubo. Se redacta tras auditar
  F-web.1.
- **F5 (preparación asistida)** — crece sobre este esqueleto (checklist documental,
  borradores) una vez cerrado F-web.2; ya en el backlog (06).

### PROMPT F-web.1 — esqueleto web + auth (magic link) + panel de solo lectura · MODELO: Sonnet · ORDEN: 1º (nada en paralelo)

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

TAREA: F-web.1 del ADR-005 (léelo entero: engineering/ADR-005-esqueleto-
web-y-auth.md). Construye el esqueleto de la app web, la autenticación
multi-tenant por magic link y el panel de solo lectura sobre
`servicios/panel.py::resumen_panel`. NO toques el contrato
(dominio/entidades.py, matching_estado.py) ni implementes aceptar/descartar
(F-web.2, prompt aparte).

1. Dependencias — añade a `pyproject.toml` (`[project]`): `fastapi>=0.115`,
   `uvicorn>=0.30`, `jinja2>=3.1`, `itsdangerous>=2.2`,
   `python-multipart>=0.0.9`; a `[project.optional-dependencies].dev`:
   `httpx>=0.27` (junto a pytest). Instala y anota en el resumen final la
   versión EXACTA resuelta de cada una (pip freeze), sin inventarla.

2. Puerto — `dominio/puertos.py`:
   a. `RepositorioEntidades` gana `obtener_entidad_por_email(email: str)
      -> Entidad | None`. Implementa en `AlmacenMemoria` y `AlmacenSQLite`
      (ALTER TABLE/índice si hace falta, idempotente). Test de contrato
      parametrizado sobre ambos backends (existe / no existe / email
      duplicado entre entidades — decide y documenta el comportamiento
      conservador: si hay duplicado, trátalo como "no permitir login
      ambiguo", devuelve None y cuenta el caso, no inventes cuál elegir).
   b. Puerto nuevo `RepositorioTokensAcceso`: `crear_token(entidad_id,
      token_hash, expira_en)`, `consumir_token(token_hash, ahora) ->
      str | None` (atómico, un solo uso). Implementa en ambos backends
      (tabla `tokens_acceso` en SQLite, dict en memoria). Test de contrato
      parametrizado: token válido se consume una vez y la segunda falla;
      expirado falla; inexistente falla.

3. Servicio — `servicios/autenticacion.py` (compone puertos, no dominio
   puro, como `servicios/propuestas.py`):
   - `generar_y_enviar_enlace(email, almacen_entidades, almacen_tokens,
     enviador_email, *, generador_token, reloj, ttl=timedelta(minutes=15))`:
     busca por email; si existe, genera token (inyectado, no
     `secrets.token_urlsafe` implícito — usa un `generador_token: Callable[[],
     str]` inyectable como el resto de ids), guarda su HASH (sha256) con
     expiración, envía el enlace. Si NO existe: no hace nada (no hay a quién
     avisar) — el llamador HTTP responde igual en ambos casos (anti
     enumeración, §2.2/§2.4 del ADR).
   - `validar_y_consumir_token(token, almacen_tokens, reloj) -> str | None`:
     hashea el token recibido y llama a `consumir_token`.
   - Envío envuelto en try/except: degrada limpio (log + contador), igual
     patrón que `NotificadorEmailSMTP` (nunca rompe la petición HTTP con una
     excepción cruda — pero SÍ debe propagar un error controlado hacia la
     ruta para poder mostrar el mensaje genérico, no un 500).

4. Adapter — `adapters/avisos/`: clase de envío del enlace de acceso
   (reutiliza `ClienteSMTP`/`ConfiguracionSMTP`/`FabricaClienteSMTP` de
   `email_smtp.py`; plantilla de texto plano propia, función pura testeable,
   sin datos internos). Factory: extiende `adapters/avisos/factory.py` con
   la construcción de este enviador (mismo `entorno='test'` -> stub).

5. Web — `src/ongs_ai/web/`:
   - `app.py`: ÚNICO fichero central. Crea `FastAPI()`, monta
     `SessionMiddleware` (clave desde `ONGS_AI_SECRET_KEY`, leída SOLO aquí
     — en tests, inyectada explícita, NUNCA del .env de la máquina),
     `app.include_router(...)` de `rutas/auth.py` y `rutas/panel.py`. Sin
     lógica de negocio en este fichero.
   - `dependencias.py`: `entidad_actual(request) -> Entidad` — lee
     `entidad_id` de la sesión, resuelve vía `obtener_entidad`; si falta o
     la entidad no existe, `HTTPException` que la ruta traduce a redirect a
     `/login` (panel) o 401 genérico.
   - `rutas/auth.py`: `GET /login`, `POST /login` (mensaje genérico
     siempre), `GET /login/confirmar` (consume token, crea sesión, redirect
     a `/panel`; falla -> página de error genérica), `POST /logout` (borra
     sesión).
   - `rutas/panel.py`: `GET /panel` con `entidad: Entidad =
     Depends(entidad_actual)`; llama a `resumen_panel(entidad.entidad_id,
     almacen)`; renderiza `panel.html` con los 6 cubos de
     `ResumenPanel` (nombres exactos de campos de `servicios/panel.py`, sin
     inventar agrupaciones nuevas). NINGÚN parámetro de ruta/query acepta un
     entidad_id.
   - `plantillas/`: Jinja2 con autoescape (default de `Jinja2Templates`
     para `.html` — no lo desactives). `base.html` + `login.html` +
     `panel.html` (listas simples por cubo: objeto, portal, fecha_cierre,
     motivo si no elegible) + `error.html` genérico (sin traza, sin motivo
     técnico).
   - Sin CSS/JS de terceros vía CDN — inline mínimo o nada; no es el foco
     de esta fase.

6. Tests (`tests/test_web_auth.py`, `tests/test_web_panel.py` +
   ampliación de `tests/test_anti_fuga_tenant.py`), con `TestClient` de
   FastAPI, HERMÉTICOS (sin red, sin servidor real, SMTP siempre stub):
   - login feliz: email existente -> stub de envío registra 1 enlace ->
     confirmar token -> sesión creada -> `/panel` responde 200 con los
     datos de ESA entidad.
   - email inexistente -> MISMA respuesta que el feliz (no hay forma de
     distinguir desde fuera); cero enlaces registrados en el stub.
   - token ya usado / caducado / inventado -> error genérico, sin sesión.
   - `/panel` sin sesión -> redirect/401 a `/login`.
   - ANTI-FUGA CROSS-TENANT a nivel HTTP: entidad A logueada, matches
     sembrados para A y B -> `/panel` de A NUNCA muestra nada de B; no
     existe ninguna ruta que acepte un entidad_id ajeno como parámetro (si
     se te ocurre añadir una así, NO lo hagas — es exactamente lo que este
     ADR prohíbe).
   - logout invalida la sesión (siguiente `/panel` vuelve a exigir login).
   - plantilla del enlace de acceso: contenido correcto, sin campos
     internos (test de la función pura, sin enviar nada).

7. Chequeo sintáctico (`ast.parse`) de cada fichero `.py` tocado.
   `python -m pytest -q` VERDE y HERMÉTICO con el nº REAL de tests.

Incluye en tu commit los cambios de engineering/06_* que ya estén en el
working tree, tal cual estén.

Ritual de cierre: commit ÚNICO con el nº REAL de tests en el mensaje,
`git status` antes del add (ni .env, ni var/, ni ONGS_AI_SECRET_KEY en
ningún fichero), `git push` al terminar.
```

## 7. Preguntas al operador (con default cada una — no bloqueantes)

- **Duración de la sesión.** Default: 12h fijas; pasado ese tiempo, nuevo magic link.
  ¿Vale, o prefieres sesión más larga (p. ej. 30 días) para minimizar fricción de la
  entidad piloto?
- **TTL del token de magic link.** Default: 15 minutos. ¿Vale, o prefieres una ventana
  mayor (p. ej. 1h) pensando en usuarios que no revisan el correo al instante?
- **Hosting/TLS para v1.** Default: durante la validación interna, `localhost`/HTTP sin
  `secure` en la cookie; antes de dar acceso a la entidad piloto real, exigir HTTPS
  (dominio + certificado) y activar `secure=True`. ¿Ya hay dominio/hosting decidido, o
  se resuelve cuando la piloto esté lista?
- **`ONGS_AI_SECRET_KEY`.** Default: variable de entorno, generada una vez por el
  operador (p. ej. `openssl rand -hex 32`), nunca en git, documentada como requisito de
  arranque igual que `ONGS_AI_SMTP_*`. ¿Conforme?
- **Idioma de las rutas públicas.** Default: `/login`, `/panel`, `/login/confirmar`,
  `/logout` en español (usuario final hispanohablante), aunque el código interno siga
  usando términos técnicos en inglés donde ya es la convención (Entity/Grant en
  ADR-001). ¿Conforme, o prefieres las rutas en inglés por convención de la industria?
- **Recuperación si una entidad pierde acceso a su email.** Default: procedimiento
  manual del operador (backlog, fuera de F-web.1) — no se construye autoservicio de
  cambio de email en esta fase. ¿Conforme?
