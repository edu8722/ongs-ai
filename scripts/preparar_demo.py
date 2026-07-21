"""Preparación de UN COMANDO para la demo — PROMPT-021 B (sustituye a los
scripts desechables `demo_semilla_local.py`/`demo_entidad_real.py`, sin tests).

Deja TODO listo para abrir el navegador: (1) opcionalmente ejecuta una pasada
corta de ingesta si faltan convocatorias VERIFICADAS y hay red, (2)
siembra/actualiza la entidad demo (perfil ABAIMAR con supuestos marcados,
email del operador), (3) importa los prospectos del CSV maestro si existe y
aún no hay ninguno, (4) genera un enlace mágico y lo imprime junto con la URL
de la consola, la variable de entorno de clave de operador y el comando
uvicorn exacto.

`preparar_demo()` es la ORQUESTACIÓN, testeada con todo inyectado/stub (sin
red, sin disco) — ver `tests/test_preparar_demo.py`. `main()` es el
envoltorio con red/disco real, NO se testea (mismo patrón que
`scripts/ejecutar_ingesta.py`).

Uso:
    python scripts/preparar_demo.py tu-email@ejemplo.com
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import secrets
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ejecutar_ingesta import ResumenPasada  # noqa: E402

from ongs_ai.dominio.entidades import (  # noqa: E402
    ActividadDeclarada,
    AmbitoTerritorial,
    Contacto,
    DatosEconomicos,
    Entidad,
    EstadoIngesta,
    FormaJuridica,
    FormaJuridicaDeclarada,
    RequisitoFormal,
    TipoActividad,
)
from ongs_ai.prospeccion.importador import importar_prospectos  # noqa: E402

MINIMO_CONVOCATORIAS_VERIFICADAS_DEFECTO = 20
TTL_TOKEN_DEMO_DEFECTO = timedelta(hours=12)
ENTIDAD_DEMO_ID = "demo-abaimar"

RUTA_CSV_PROSPECTOS_DEFECTO = (
    Path(__file__).resolve().parents[1] / "investigacion" / "asociaciones_maestro.csv"
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _entidad_demo_abaimar(email_operador: str, *, ahora: datetime) -> Entidad:
    """Perfil ABAIMAR (Asociación Balear de Niños con Enfermedades Raras) con
    SUPUESTOS marcados — el mismo perfil que llevaba `demo_entidad_real.py`,
    ahora sembrado por la función testeada en vez de un script desechable."""
    return Entidad(
        entidad_id=ENTIDAD_DEMO_ID,
        nombre_legal="Asociación Balear de Niños con Enfermedades Raras (ABAIMAR)",
        nif="G-DEMO-000",  # SUPUESTO — no usar el NIF real sin su permiso
        ambito_territorial=AmbitoTerritorial.AUTONOMICO,
        forma_juridica=FormaJuridicaDeclarada(tipo=FormaJuridica.ASOCIACION),
        fecha_constitucion=date(2015, 1, 1),  # SUPUESTO (web: "no consta") — confirmar
        enfermedad_o_colectivo="Niños y niñas con enfermedades raras (familias)",
        actividades=(
            ActividadDeclarada(tipo=TipoActividad.ATENCION_DIRECTA_A_FAMILIAS),
            ActividadDeclarada(tipo=TipoActividad.CHARLAS_Y_SENSIBILIZACION),
            ActividadDeclarada(tipo=TipoActividad.ENCUENTRO_DE_PACIENTES),
            ActividadDeclarada(
                tipo=TipoActividad.OTRO,
                descripcion="Refuerzo escolar domiciliario y musicoterapia",
            ),
        ),
        datos_economicos_ejercicio_anterior=DatosEconomicos(
            ingresos_centimos=8_500_000, gastos_centimos=7_900_000, ejercicio=2025
        ),  # SUPUESTO realista — sustituir por reales si la piloto los facilita
        requisitos_formales_disponibles=(
            RequisitoFormal.INSCRITA_REGISTRO_ASOCIACIONES,  # SUPUESTO razonable
        ),
        contacto=Contacto(email=email_operador, telefono="638 316 661"),
        creado_en=ahora,
        actualizado_en=ahora,
        region="Islas Baleares",
        provincia="Islas Baleares",
    )


@dataclass(frozen=True)
class ResumenPreparacionDemo:
    convocatorias_verificadas_antes: int
    ingesta_ejecutada: bool
    ingesta_aviso: str | None
    resumen_ingesta: ResumenPasada | None
    entidad_id: str
    prospectos_importados: int
    prospectos_aviso: str | None
    token: str
    url_confirmacion_entidad: str
    url_consola: str


def preparar_demo(
    almacen,
    *,
    email_operador: str,
    reloj: Callable[[], datetime],
    generador_token: Callable[[], str],
    base_url: str,
    ttl_token: timedelta = TTL_TOKEN_DEMO_DEFECTO,
    minimo_convocatorias_verificadas: int = MINIMO_CONVOCATORIAS_VERIFICADAS_DEFECTO,
    ejecutar_ingesta: Callable[[], ResumenPasada] | None = None,
    filas_prospectos: list[dict[str, str]] | None = None,
    generador_id_prospecto: Callable[[], str] | None = None,
) -> ResumenPreparacionDemo:
    """Orquesta la preparación completa de la demo. Todo lo que toca red/disco
    llega YA resuelto por el llamador (`ejecutar_ingesta`/`filas_prospectos`
    son `None` si no hay red o no hay CSV) — aquí no hay ni un `open()` ni una
    petición HTTP, por eso es testeable con stubs (PROMPT-021 B1)."""
    convocatorias = almacen.listar_convocatorias()
    verificadas_antes = sum(1 for c in convocatorias if c.estado_ingesta is EstadoIngesta.VERIFICADA)

    ingesta_ejecutada = False
    ingesta_aviso: str | None = None
    resumen_ingesta: ResumenPasada | None = None
    if verificadas_antes >= minimo_convocatorias_verificadas:
        ingesta_aviso = (
            f"Ya hay {verificadas_antes} convocatorias verificadas "
            f"(al menos {minimo_convocatorias_verificadas}) — no se ejecuta ingesta."
        )
    elif ejecutar_ingesta is None:
        ingesta_aviso = (
            f"Solo {verificadas_antes} convocatorias verificadas y sin red disponible — "
            "se sigue con lo que hay en la base."
        )
    else:
        try:
            resumen_ingesta = ejecutar_ingesta()
            ingesta_ejecutada = True
        except Exception as exc:  # degradación limpia (CLAUDE.md) — nunca rompe la demo
            ingesta_aviso = f"Fallo la pasada de ingesta ({exc}) — se sigue con lo que hay."

    ahora = reloj()
    entidad = _entidad_demo_abaimar(email_operador, ahora=ahora)
    almacen.guardar_entidad(entidad)

    prospectos_importados = 0
    prospectos_aviso: str | None = None
    if almacen.listar_prospectos():
        prospectos_aviso = "Ya había prospectos importados — no se repite la importación."
    elif filas_prospectos is None:
        prospectos_aviso = "Sin CSV de prospectos disponible — no se importa nada."
    else:
        resultado = importar_prospectos(filas_prospectos, generador_id=generador_id_prospecto)
        for prospecto in resultado.prospectos:
            almacen.guardar_prospecto(prospecto)
        prospectos_importados = len(resultado.prospectos)

    token = generador_token()
    almacen.crear_token(entidad.entidad_id, _hash_token(token), ahora + ttl_token)

    return ResumenPreparacionDemo(
        convocatorias_verificadas_antes=verificadas_antes,
        ingesta_ejecutada=ingesta_ejecutada,
        ingesta_aviso=ingesta_aviso,
        resumen_ingesta=resumen_ingesta,
        entidad_id=entidad.entidad_id,
        prospectos_importados=prospectos_importados,
        prospectos_aviso=prospectos_aviso,
        token=token,
        url_confirmacion_entidad=f"{base_url}/login/confirmar?token={token}",
        url_consola=f"{base_url}/consola",
    )


def _generador_id_prospecto() -> str:
    return f"prospecto-{uuid.uuid4().hex[:12]}"


def _leer_filas_prospectos(ruta: Path) -> list[dict[str, str]] | None:
    if not ruta.exists():
        return None
    with ruta.open(encoding="utf-8-sig", newline="") as fichero:
        return list(csv.DictReader(fichero))


def _intentar_ingesta_corta(almacen):
    """Envoltorio de red real de `ejecutar_pasada` con flags conservadores
    (B1: "reutiliza ejecutar_ingesta con flags conservadores"). Cualquier
    fallo (sin red, límite de plan, lo que sea) lo captura `preparar_demo`."""
    from ejecutar_ingesta import (
        PAGE_SIZE_DEFECTO,
        PAGINAS_MAX_DEFECTO,
        _construir_notificador,
        ejecutar_pasada,
    )
    from ongs_ai.adapters.ingesta.base import FiltrosBusqueda, TransporteURLLib
    from ongs_ai.adapters.ingesta.bdns import FuenteBDNS
    from ongs_ai.ia.claude_cli import ClienteClaudeCLI
    from ongs_ai.ia.explicacion_match import ExplicadorClaudeCLI

    def reloj() -> datetime:
        return datetime.now(timezone.utc)

    def generador_ids() -> str:
        return str(uuid.uuid4())

    fuente = FuenteBDNS(TransporteURLLib(), reloj=reloj, page_size=PAGE_SIZE_DEFECTO)
    cliente_ia = ClienteClaudeCLI()
    return ejecutar_pasada(
        fuente,
        almacen,
        _construir_notificador(),
        date.today(),
        filtros=FiltrosBusqueda(),
        limite_convocatorias=PAGINAS_MAX_DEFECTO * PAGE_SIZE_DEFECTO,
        cliente_ia=cliente_ia,
        generador_explicacion=ExplicadorClaudeCLI(cliente_ia),
        generador_ids=generador_ids,
        reloj=reloj,
    )


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email_operador", help="Email del operador — será el contacto de la entidad demo")
    parser.add_argument(
        "--base-url", default="http://localhost:8001", help="Base de la app local (por defecto puerto 8001)"
    )
    parser.add_argument("--sin-ingesta", action="store_true", help="Salta la pasada de ingesta aunque haya red")
    return parser.parse_args(argv)


def main() -> None:
    args = _parsear_argumentos()

    from ongs_ai.adapters.persistencia.factory import crear_almacen

    almacen = crear_almacen()

    ejecutor_ingesta = None if args.sin_ingesta else (lambda: _intentar_ingesta_corta(almacen))
    filas_prospectos = _leer_filas_prospectos(RUTA_CSV_PROSPECTOS_DEFECTO)

    resumen = preparar_demo(
        almacen,
        email_operador=args.email_operador,
        reloj=lambda: datetime.now(timezone.utc),
        generador_token=lambda: secrets.token_urlsafe(32),
        base_url=args.base_url,
        ejecutar_ingesta=ejecutor_ingesta,
        filas_prospectos=filas_prospectos,
        generador_id_prospecto=_generador_id_prospecto,
    )

    print()
    print("=== Preparación de la demo ===")
    print(f"Convocatorias verificadas antes de esta pasada: {resumen.convocatorias_verificadas_antes}")
    if resumen.ingesta_aviso:
        print(f"Ingesta: {resumen.ingesta_aviso}")
    if resumen.ingesta_ejecutada and resumen.resumen_ingesta is not None:
        print(f"Ingesta ejecutada — convocatorias ingestadas: {resumen.resumen_ingesta.ingestadas}")
    print(f"Entidad demo sembrada/actualizada: {resumen.entidad_id}")
    if resumen.prospectos_aviso:
        print(f"Prospectos: {resumen.prospectos_aviso}")
    else:
        print(f"Prospectos importados: {resumen.prospectos_importados}")

    print()
    print("=== ACCESO ===")
    print("Panel de la entidad demo (enlace confirmable, un solo uso, 12h):")
    print(f"  {resumen.url_confirmacion_entidad}")
    print("Consola del operador:")
    print(f"  {resumen.url_consola}")
    print("Clave de operador: debe estar en la variable de entorno ONGS_AI_OPERADOR_CLAVE")
    print("(el navegador la pedirá al entrar en /consola/login).")
    print()
    print("Arranca el servidor con:")
    print("  set PYTHONPATH=src")
    print("  python -m uvicorn ongs_ai.web.app:app --reload --port 8001")


if __name__ == "__main__":
    main()
