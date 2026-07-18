# R1 — Catálogo de fuentes de subvenciones (informe)

**ONGs-AI · 2026-07-18 · Investigación del arquitecto** · Entregable acompañante:
`R1_catalogo_fuentes_subvenciones.xlsx`

## El hallazgo que cambia la arquitectura de F2

**La BDNS (Base de Datos Nacional de Subvenciones), expuesta públicamente como
SNPSAP en infosubvenciones.es, tiene una API REST pública, sin autenticación,
documentada con Swagger, que agrega las convocatorias de TODAS las administraciones
españolas** — estatal, las 17 CCAA, diputaciones y ayuntamientos (cobertura local
confirmada con ejemplos reales: Diputación de Tarragona, Ayuntamiento de Vigo).

- Búsqueda paginada JSON: `/bdnstrans/api/convocatorias/busqueda?page=N&pageSize=M`
  (~639.000 convocatorias acumuladas).
- Detalle por convocatoria: `/bdnstrans/api/convocatorias?numConv=<códigoBDNS>`, con
  campos estructurados que mapean casi 1:1 a nuestro contrato ADR-001:
  `tiposBeneficiarios` → beneficiarios/forma jurídica; `regiones` → ámbito
  geográfico; `fechaInicioSolicitud`/`fechaFinSolicitud` → plazos; `abierto`;
  `presupuestoTotal` → cuantías; `finalidad` → objeto; `urlBasesReguladoras` →
  documento_origen_ref.
- Estas tres afirmaciones están **verificadas 3-0** contra la fuente primaria
  (Swagger oficial). Existe además un cliente Python de referencia (`bdns-fetch`,
  PyPI) que cubre 29 endpoints.

**Consecuencia para F2:** el primer adapter de ingesta es UNO — el de la BDNS — y
cubre todo el sector público. IRPF 0,7%, IMSERSO, Sanidad, CCAA y entes locales
llegan por ahí (sus webs propias solo aportan las bases completas en PDF).

## Las fuentes que NO llegan por BDNS (adapters propios ligeros, fase posterior)

Privadas: **FEDER** (recopila ayudas del nicho EERR y tiene convocatoria propia de
investigación), **Fundación "la Caixa"** (convocatorias sociales anuales por
territorio), **Fundación ONCE** (convocatoria general para entidades de
discapacidad). Como red de seguridad: **SolucionesONG.org** (agregador del tercer
sector con servicio de alertas).

## La convocatoria reina del nicho

La estatal del **0,7% del IRPF** (Ministerio de Derechos Sociales): anual, ventana
de solicitud de ~1 mes en primavera/verano (2026: 20-may → 18-jun), beneficiarios =
entidades del Tercer Sector de Acción Social. Llega por BDNS (código 2026: 905627).

## Honestidad metodológica

5 ángulos de búsqueda paralelos · 21 fuentes analizadas · 101 afirmaciones
extraídas · 25 sometidas a verificación adversarial. **3 confirmadas 3-0, 0
refutadas**; las restantes quedaron sin verificar porque se agotó el límite de uso
de la sesión a mitad de la fase — todas proceden de fuentes oficiales/primarias y
ninguna fue refutada, pero el Excel las marca como "verificación pendiente". La
verificación puede completarse en una pasada posterior si se desea.

## Siguiente paso propuesto (spec F2)

Adapter único `bdns.py` contra la API de la BDNS (red inyectable, fixtures JSON
grabadas para tests), filtrando por `tiposBeneficiarios` compatibles con entidades
sin ánimo de lucro + palabras clave de finalidad. Dedupe por `portal`+`url_origen`
(ya decidido, ADR-001 §6.5) — con la BDNS, el código BDNS de convocatoria es la
clave natural. Los adapters privados (FEDER, la Caixa, ONCE) vienen después.
