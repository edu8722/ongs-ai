# Demo — de un comando a las dos pantallas (panel + consola)

Sección ÚNICA de demo (PROMPT-021 B3). Sustituye a cualquier instrucción de
demo anterior dispersa en la pizarra. Cuatro pasos, en este orden.

## 1. Variables de entorno

```
set ONGS_AI_SECRET_KEY=prueba-local
set ONGS_AI_OPERADOR_CLAVE=una-clave-cualquiera-para-la-consola
set ONGS_AI_SMTP_HOST=localhost
set ONGS_AI_SMTP_REMITENTE=demo@localhost
set ONGS_AI_APP_BASE_URL=http://localhost:8001
set PYTHONPATH=src
```

El servidor (paso 3) exige `ONGS_AI_SMTP_HOST`/`ONGS_AI_SMTP_REMITENTE`/
`ONGS_AI_APP_BASE_URL` para arrancar aunque no llegues a enviar ningún email
real en la demo (`localhost`/`demo@localhost` bastan — el enlace mágico ya
lo imprime el paso 2, no hace falta que el correo salga de verdad). Dentro
de `scripts/ejecutar_ingesta.py` (que `preparar_demo.py` puede invocar en el
paso 2) SÍ degrada limpio sin estas variables: sin SMTP, sus avisos de
propuesta salen impresos en consola en vez de por email.

## 2. Preparar la demo (un comando)

```
python scripts/preparar_demo.py tu-email@ejemplo.com
```

Este comando deja TODO listo: ingiere convocatorias si faltan y hay red,
siembra/actualiza la entidad demo (perfil ABAIMAR, con supuestos marcados),
importa los prospectos del CSV maestro si existe y aún no hay ninguno, y
**imprime al final** la URL del panel de la entidad (enlace mágico
confirmable, un solo uso), la URL de la consola y un recordatorio de la
clave de operador.

## 3. Arrancar el servidor

```
python -m uvicorn ongs_ai.web.app:app --reload --port 8001
```

## 4. Abrir las URLs impresas por el paso 2

- Panel de la entidad demo (enlace de un solo uso): `http://localhost:8001/login/confirmar?token=...`
- Consola del operador: `http://localhost:8001/consola` (pide la clave de `ONGS_AI_OPERADOR_CLAVE`)

Si el enlace del panel ya se usó (un solo uso) o caducó (12 h), vuelve a
ejecutar el paso 2 — regenera un enlace nuevo sin duplicar la entidad ni los
prospectos ya importados.
