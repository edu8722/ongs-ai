"""Smoke test MANUAL de envío de email real vía SMTP.

Hace red real (conecta al servidor SMTP configurado) — por eso NO se ejecuta
en pytest ni en CI (regla de oro CLAUDE.md: tests herméticos, sin red). Lo
ejecuta el OPERADOR a mano, con credenciales SMTP reales en el entorno,
cuando quiera verificar que el aviso llega de verdad a una bandeja de
entrada. Este prompt (F4.2) NO necesita esas credenciales para cerrarse: los
tests de `email_smtp.py` van con un cliente SMTP stub inyectado.

Variables de entorno requeridas (mismo prefijo que la factory de
composición, `adapters/avisos/factory.py`):
    ONGS_AI_SMTP_HOST
    ONGS_AI_SMTP_PUERTO      (opcional, por defecto 587)
    ONGS_AI_SMTP_REMITENTE
    ONGS_AI_SMTP_USUARIO     (opcional, según el servidor)
    ONGS_AI_SMTP_CONTRASENA  (opcional, según el servidor)

Uso:
    ONGS_AI_SMTP_HOST=smtp.example.org \\
    ONGS_AI_SMTP_REMITENTE=avisos@ongs-ai.example \\
    ONGS_AI_SMTP_USUARIO=avisos@ongs-ai.example \\
    ONGS_AI_SMTP_CONTRASENA=... \\
    python scripts/smoke_email.py destinatario-de-prueba@example.org
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.avisos.factory import crear_notificador  # noqa: E402
from ongs_ai.dominio.entidades import (  # noqa: E402
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    Convocatoria,
    Cuantias,
    DatosEconomicos,
    Entidad,
    EstadoIngesta,
    FormaJuridica,
    FormaJuridicaDeclarada,
    Fuente,
    Plazos,
    RequisitoFormal,
    RequisitosElegibilidad,
    TipoActividad,
    TipoFuente,
)
from ongs_ai.dominio.matching_estado import ActorAsiento, crear_match  # noqa: E402


def _entidad_de_prueba(email_destino: str) -> Entidad:
    ahora = datetime.now(timezone.utc)
    return Entidad(
        entidad_id="ent-smoke-email",
        nombre_legal="Entidad de prueba (smoke_email.py)",
        nif="B00000000",
        ambito_territorial=AmbitoTerritorial.NACIONAL,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2010, 1, 1),
        enfermedad_o_colectivo="colectivo de prueba",
        actividades=(ActividadDeclarada(tipo=TipoActividad.VOLUNTARIADO),),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=0, gastos_centimos=0, ejercicio=ahora.year - 1
        ),
        requisitos_formales_disponibles=(RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,),
        contacto=Contacto(email=email_destino),
        creado_en=ahora,
        actualizado_en=ahora,
    )


def _convocatoria_de_prueba() -> Convocatoria:
    ahora = datetime.now(timezone.utc)
    return Convocatoria(
        convocatoria_id="conv-smoke-email",
        fuente=Fuente(portal="portal-smoke", url_origen="https://example.org/smoke", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Convocatoria de prueba (smoke_email.py)",
        beneficiarios_elegibles="Asociaciones sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=1_000_000, porcentaje_max_financiable=8000),
        estado_ingesta=EstadoIngesta.VERIFICADA,
        creado_en=ahora,
        actualizado_en=ahora,
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python scripts/smoke_email.py <email-destino-de-prueba>")
        raise SystemExit(1)
    email_destino = sys.argv[1]

    entidad = _entidad_de_prueba(email_destino)
    convocatoria = _convocatoria_de_prueba()
    match = crear_match(
        match_id="match-smoke-email",
        entidad_id=entidad.entidad_id,
        convocatoria_id=convocatoria.convocatoria_id,
        transicion_id="t-smoke-0",
        motivo="smoke test de envío de email",
        actor=ActorAsiento.SISTEMA,
        timestamp=datetime.now(timezone.utc),
    )

    notificador = crear_notificador()
    notificador.notificar_propuesta(entidad, convocatoria, match)

    print(f"enviados={getattr(notificador, 'enviados', '?')} "
          f"omitidos_sin_email={getattr(notificador, 'omitidos_sin_email', '?')} "
          f"fallidos={getattr(notificador, 'fallidos', '?')}")


if __name__ == "__main__":
    main()
