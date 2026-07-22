"""Orquestación de la demo de un comando (`scripts/preparar_demo.preparar_demo`)
— PROMPT-021 B1/B2. Todo inyectado/stub: sin red, sin disco, `AlmacenMemoria`
en vez de SQLite. `scripts/` no es un paquete instalado — se añade a
`sys.path` igual que `tests/test_ejecutar_ingesta.py`.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ejecutar_ingesta import ResumenPasada  # noqa: E402
from preparar_demo import (  # noqa: E402
    ENTIDAD_DEMO_ID,
    IDS_CONVOCATORIAS_DEMO_FICTICIAS,
    preparar_demo,
)

from ongs_ai.adapters.persistencia.memoria import AlmacenMemoria  # noqa: E402
from ongs_ai.dominio.entidades import (  # noqa: E402
    AmbitoTerritorial,
    Convocatoria,
    Cuantias,
    EstadoIngesta,
    Fuente,
    Plazos,
    RequisitosElegibilidad,
    TipoFuente,
)

AHORA = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _reloj():
    return AHORA


def _contador_tokens():
    contador = iter(f"token-{i}" for i in range(1, 1000))
    return lambda: next(contador)


def _contador_ids_prospecto():
    contador = iter(f"prospecto-{i}" for i in range(1, 1000))
    return lambda: next(contador)


def _convocatoria(cid: str, estado: EstadoIngesta) -> Convocatoria:
    return Convocatoria(
        convocatoria_id=cid,
        fuente=Fuente(portal="BDNS", url_origen=f"https://demo.example/{cid}", tipo=TipoFuente.PUBLICA_NACIONAL),
        objeto="Ayudas de prueba",
        beneficiarios_elegibles="Entidades sin ánimo de lucro",
        requisitos_elegibilidad=RequisitosElegibilidad(),
        ambito_geografico=AmbitoTerritorial.NACIONAL,
        plazos=Plazos(fecha_apertura=date(2026, 1, 1), fecha_cierre=date(2026, 12, 31)),
        cuantias=Cuantias(importe_maximo_centimos=100_000),
        estado_ingesta=estado,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


def _resumen_ingesta_fake(ingestadas: int = 3) -> ResumenPasada:
    return ResumenPasada(
        ingestadas=ingestadas,
        ya_existentes=0,
        enriquecidas_por_ia=0,
        promovidas=0,
        esperadas_enlazadas=0,
        esperadas_no_aparecidas=0,
        propuestas_nuevas=0,
        propuestas_sobrevenidas=0,
        avisos_intentados=0,
        no_elegibles_persistidas=0,
        saltadas_pre_puerta=0,
        llamadas_ia_usadas=0,
        convocatorias_sin_ia_por_freno=0,
        fallos_ia_inesperados=0,
        descartadas_no_abiertas=0,
        descartadas_concesion_directa=0,
    )


def _filas_prospectos() -> list[dict[str, str]]:
    return [
        {
            "Nombre": "Asociación de Prueba de Prospección",
            "Web": "prueba.example.org",
            "Email": "info@prueba.example.org",
            "Teléfono": "",
            "Ámbito": "autonomico",
            "CCAA": "Región de Murcia",
            "Enfermedad / Colectivo": "colectivo de prueba",
            "Personas visibles (cargo)": "",
            "Tamaño": "",
            "Fuente(s)": "",
            "Notas": "",
        }
    ]


def test_siembra_entidad_demo_con_email_operador():
    almacen = AlmacenMemoria()
    resumen = preparar_demo(
        almacen,
        email_operador="operador@example.org",
        reloj=_reloj,
        generador_token=_contador_tokens(),
        base_url="http://localhost:8001",
    )
    entidad = almacen.obtener_entidad(ENTIDAD_DEMO_ID)
    assert entidad is not None
    assert entidad.contacto.email == "operador@example.org"
    assert entidad.creado_en == AHORA
    assert resumen.entidad_id == ENTIDAD_DEMO_ID


def test_reejecutar_actualiza_en_vez_de_duplicar():
    almacen = AlmacenMemoria()
    preparar_demo(
        almacen, email_operador="uno@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )
    preparar_demo(
        almacen, email_operador="dos@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )
    assert len(almacen.listar_entidades()) == 1
    assert almacen.obtener_entidad(ENTIDAD_DEMO_ID).contacto.email == "dos@example.org"


def test_token_generado_permite_consumir_el_enlace():
    almacen = AlmacenMemoria()
    resumen = preparar_demo(
        almacen, email_operador="operador@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )
    assert resumen.token in resumen.url_confirmacion_entidad
    assert almacen.consumir_token(
        __import__("hashlib").sha256(resumen.token.encode("utf-8")).hexdigest(), AHORA
    ) == ENTIDAD_DEMO_ID


def test_sin_ejecutor_ingesta_y_pocas_verificadas_avisa_y_sigue():
    almacen = AlmacenMemoria()
    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        ejecutar_ingesta=None,
    )
    assert resumen.ingesta_ejecutada is False
    assert "sin red" in resumen.ingesta_aviso.lower() or "verificadas" in resumen.ingesta_aviso.lower()


def test_con_ejecutor_ingesta_exitoso_lo_ejecuta():
    almacen = AlmacenMemoria()
    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        ejecutar_ingesta=lambda: _resumen_ingesta_fake(ingestadas=7),
    )
    assert resumen.ingesta_ejecutada is True
    assert resumen.resumen_ingesta.ingestadas == 7
    assert resumen.ingesta_aviso is None


def test_ejecutor_ingesta_que_falla_degrada_limpio():
    almacen = AlmacenMemoria()

    def _falla():
        raise ConnectionError("sin red simulada")

    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        ejecutar_ingesta=_falla,
    )
    assert resumen.ingesta_ejecutada is False
    assert "sin red simulada" in resumen.ingesta_aviso


def test_ya_hay_suficientes_verificadas_no_ejecuta_ingesta():
    almacen = AlmacenMemoria()
    for i in range(20):
        almacen.guardar_convocatoria(_convocatoria(f"conv-{i}", EstadoIngesta.VERIFICADA))

    llamado = []
    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        ejecutar_ingesta=lambda: (llamado.append(1), _resumen_ingesta_fake())[1],
    )
    assert resumen.ingesta_ejecutada is False
    assert llamado == []
    assert resumen.convocatorias_verificadas_antes == 20


def test_sin_csv_no_importa_prospectos():
    almacen = AlmacenMemoria()
    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        filas_prospectos=None,
    )
    assert resumen.prospectos_importados == 0
    assert almacen.listar_prospectos() == []
    assert "sin csv" in resumen.prospectos_aviso.lower()


def test_con_csv_importa_prospectos_una_sola_vez():
    almacen = AlmacenMemoria()
    preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        filas_prospectos=_filas_prospectos(),
        generador_id_prospecto=_contador_ids_prospecto(),
    )
    assert len(almacen.listar_prospectos()) == 1

    resumen2 = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
        filas_prospectos=_filas_prospectos(),
        generador_id_prospecto=_contador_ids_prospecto(),
    )
    assert resumen2.prospectos_importados == 0
    assert "ya había" in resumen2.prospectos_aviso.lower()
    assert len(almacen.listar_prospectos()) == 1


# --- Retirada de convocatorias demo ficticias (bandeja del operador,
#     pendiente desde PROMPT-023) --------------------------------------------


def test_retira_convocatorias_demo_ficticias_si_existen_en_la_base():
    almacen = AlmacenMemoria()
    for cid in IDS_CONVOCATORIAS_DEMO_FICTICIAS:
        almacen.guardar_convocatoria(_convocatoria(cid, EstadoIngesta.VERIFICADA))
    otra_real = _convocatoria("conv-real-1", EstadoIngesta.VERIFICADA)
    almacen.guardar_convocatoria(otra_real)

    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )

    assert resumen.convocatorias_demo_retiradas == len(IDS_CONVOCATORIAS_DEMO_FICTICIAS)
    for cid in IDS_CONVOCATORIAS_DEMO_FICTICIAS:
        assert almacen.obtener_convocatoria(cid).estado_ingesta is EstadoIngesta.DESCARTADA_POR_DOMINIO
    # una convocatoria real cualquiera no se toca.
    assert almacen.obtener_convocatoria("conv-real-1").estado_ingesta is EstadoIngesta.VERIFICADA


def test_retirada_de_demo_ficticias_no_borra_filas_ni_falla_si_no_existen():
    almacen = AlmacenMemoria()
    # ninguna demo-conv-* sembrada — no debe lanzar.
    resumen = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )
    assert resumen.convocatorias_demo_retiradas == 0
    for cid in IDS_CONVOCATORIAS_DEMO_FICTICIAS:
        assert almacen.obtener_convocatoria(cid) is None


def test_retirada_de_demo_ficticias_es_idempotente():
    almacen = AlmacenMemoria()
    almacen.guardar_convocatoria(_convocatoria(IDS_CONVOCATORIAS_DEMO_FICTICIAS[0], EstadoIngesta.VERIFICADA))

    preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )
    resumen_2 = preparar_demo(
        almacen, email_operador="a@example.org", reloj=_reloj,
        generador_token=_contador_tokens(), base_url="http://localhost:8001",
    )

    assert resumen_2.convocatorias_demo_retiradas == 0
    assert (
        almacen.obtener_convocatoria(IDS_CONVOCATORIAS_DEMO_FICTICIAS[0]).estado_ingesta
        is EstadoIngesta.DESCARTADA_POR_DOMINIO
    )
