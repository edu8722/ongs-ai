# PROJECT_CONTEXT — ONGs-AI (v1, 2026-07-18)

## Visión

SaaS multi-tenant que hace de **técnico de subvenciones** para entidades sin ánimo de
lucro de **enfermedades raras** con poco o ningún personal: vigila convocatorias
públicas y privadas, detecta las compatibles con cada entidad, avisa, propone y ayuda
a preparar la solicitud. La entidad se despreocupa de mirar continuamente qué sale.

## Problema

Estas asociaciones (mayoría de pacientes/familiares, sin técnico de proyectos) pierden
financiación porque nadie vigila los boletines nacional/regional/local ni las
convocatorias privadas, y porque preparar una solicitud exige oficio y datos que
nadie tiene ordenados.

## Usuarios

- Tenant = asociación de enfermedades raras (España) con 0–muy poco personal.
- Primer usuario: **entidad piloto por captar**, que dará acceso y datos reales
  (ingresos/gastos del ejercicio anterior, actividades) — muchos requisitos de
  convocatoria dependen de esos datos.

## Los dos pilares

1. **Cartera de entidades** (BD multi-tenant): perfil por entidad — ámbito territorial,
   actividades típicas (voluntariado, encuentros de pacientes, charlas…), datos
   económicos del ejercicio anterior, requisitos formales que las convocatorias piden.
2. **Buscador/vigilante de subvenciones**: ingesta de convocatorias desde portales
   (lista concreta la aporta Eduardo: nacional, regional, local + privadas), análisis
   de cada convocatoria (objeto, beneficiarios, plazos, cuantías, requisitos) y
   matching contra la cartera.

## Ciclo de valor

vigilar → detectar compatibilidad → avisar/proponer ("ha salido X: ¿encaja con tu
actividad Y?", o al revés: "estas son mis actividades, búscame subvenciones") → si la
entidad acepta la propuesta → desarrollar la solicitud.

## Dónde entra la IA (regla de oro: la IA propone, el dominio valida)

- Extracción estructurada de convocatorias (texto legal/bases → campos del contrato).
- Matching explicable entidad↔convocatoria (los requisitos DUROS de elegibilidad se
  validan deterministas; la IA solo ordena/explica/sugiere).
- Redacción asistida de la solicitud (borradores; la entidad presenta).

## Abierto a 2026-07-18

- Lista concreta de portales/fuentes (Eduardo).
- Entidad piloto con nombre.
- Alcance exacto de "desarrollar la subvención" (¿borrador de memoria? ¿formularios?).
- Modelo de negocio (las entidades objetivo tienen pocos recursos).
