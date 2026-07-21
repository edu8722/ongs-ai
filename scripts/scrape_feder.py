"""Extracción MANUAL y COMPLETA del directorio de entidades asociadas de FEDER.

Hace red real (peticiones HTTP a enfermedades-raras.org) — por eso NO se
ejecuta en pytest ni en CI (regla de oro CLAUDE.md: tests herméticos, sin
red). Lo ejecuta el OPERADOR a mano para generar el fichero de prospección
(`investigacion/asociaciones_feder_completo.xlsx` + `.csv`, gitignorados —
JAMÁS se commitean datos de entidades).

El parseo (HTML -> `EntidadFeder`) vive en
`ongs_ai.adapters.captacion.feder` y se testea aparte, herméticamente, con
fixtures sintéticos (`tests/test_captacion_feder.py`). Este script es SOLO
transporte + paginación + escritura de fichero.

Recorre la paginación real siguiendo el link "página siguiente"
(`rel="next"`) que la propia página HTML expone, con pausa de 1-2 s entre
peticiones y un User-Agent identificable — no adivina el parámetro, lo lee
del HTML de cada respuesta.

DECISIÓN DOCUMENTADA (auditoría PROMPT-012): la capa de mapa de la que se
extraen las fichas (Drupal + Geolocation) devuelve, en las pruebas hechas al
escribir este script, el MISMO conjunto de entidades geocodificadas
independientemente del número de página pedido — es decir, `?page=N` mueve
el indicador de página activa pero no cambia el resultado embebido. Por eso
el bucle para en cuanto detecta `LIMITE_PAGINAS_SIN_NOVEDAD` páginas
seguidas sin ninguna entidad nueva (deduplicando por `url_ficha`), en vez de
insistir en las ~40 páginas reales contra el servidor de una entidad
pequeña. Es una salvaguarda conservadora y reversible (una constante): si en
el futuro la paginación real del sitio cambia y sí aporta entidades nuevas,
el bucle las seguirá recogiendo con normalidad hasta que se agote el link
"siguiente" o se cumpla la salvaguarda. Consecuencia conocida: el recuento
final puede quedar por debajo del contador "~476 entidades" del propio
sitio, que incluye entidades sin geocodificar (fuera del alcance de esta
capa) — se imprime igualmente en el resumen para que el operador lo vea.

Uso:
    python scripts/scrape_feder.py
"""
from __future__ import annotations

import csv
import random
import sys
import time
import urllib.request
import xml.sax.saxutils as saxutils
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ongs_ai.adapters.captacion.feder import (  # noqa: E402
    EntidadFeder,
    extraer_url_pagina_siguiente,
    parsear_pagina_entidades,
)

URL_INICIAL = "https://www.enfermedades-raras.org/movimiento-asociativo/entidades-asociadas"
USER_AGENT = "ongs-ai-captacion-feder/1.0 (uso interno, prospección manual; contacto: operador de ONGs-AI)"
PAUSA_MIN_SEGUNDOS = 1.0
PAUSA_MAX_SEGUNDOS = 2.0
LIMITE_PAGINAS_SIN_NOVEDAD = 3
TIMEOUT_SEGUNDOS = 20.0

RUTA_REPO = Path(__file__).resolve().parents[1]
RUTA_XLSX = RUTA_REPO / "investigacion" / "asociaciones_feder_completo.xlsx"
RUTA_CSV = RUTA_REPO / "investigacion" / "asociaciones_feder_completo.csv"

CABECERAS = ("nombre", "url_ficha", "direccion", "telefonos", "emails", "web", "provincia", "ccaa")


def _descargar_pagina(url: str) -> str:
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(peticion, timeout=TIMEOUT_SEGUNDOS) as respuesta:
        return respuesta.read().decode("utf-8")


def _fila_de(entidad: EntidadFeder) -> tuple[str, ...]:
    return (
        entidad.nombre,
        entidad.url_ficha,
        entidad.direccion,
        "; ".join(entidad.telefonos),
        "; ".join(entidad.emails),
        entidad.web,
        entidad.provincia,
        entidad.ccaa,
    )


def recolectar_directorio_completo() -> tuple[list[EntidadFeder], int]:
    """Sigue la paginación real (link "siguiente") y devuelve
    (entidades deduplicadas por url_ficha, nº de páginas realmente pedidas)."""
    vistas: dict[str, EntidadFeder] = {}
    url = URL_INICIAL
    paginas_recorridas = 0
    paginas_seguidas_sin_novedad = 0

    while url is not None:
        html = _descargar_pagina(url)
        paginas_recorridas += 1

        nuevas = 0
        for entidad in parsear_pagina_entidades(html):
            if entidad.url_ficha not in vistas:
                vistas[entidad.url_ficha] = entidad
                nuevas += 1

        paginas_seguidas_sin_novedad = 0 if nuevas else paginas_seguidas_sin_novedad + 1
        print(
            f"página {paginas_recorridas}: +{nuevas} nuevas "
            f"(acumulado {len(vistas)}) — {url}"
        )

        if paginas_seguidas_sin_novedad >= LIMITE_PAGINAS_SIN_NOVEDAD:
            print(
                f"corte por salvaguarda: {LIMITE_PAGINAS_SIN_NOVEDAD} páginas seguidas "
                "sin entidades nuevas (ver decisión documentada en la cabecera del script)."
            )
            break

        siguiente = extraer_url_pagina_siguiente(html, url)
        if siguiente is None:
            break
        url = siguiente
        time.sleep(random.uniform(PAUSA_MIN_SEGUNDOS, PAUSA_MAX_SEGUNDOS))

    return list(vistas.values()), paginas_recorridas


def _columna_excel(indice_0: int) -> str:
    letras = ""
    n = indice_0 + 1
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(ord("A") + resto) + letras
    return letras


def _celda_xml(columna: str, fila: int, texto: str) -> str:
    valor = saxutils.escape(texto)
    return f'<c r="{columna}{fila}" t="inlineStr"><is><t xml:space="preserve">{valor}</t></is></c>'


def escribir_xlsx(ruta: Path, cabeceras: tuple[str, ...], filas: list[tuple[str, ...]]) -> None:
    """Escribe un .xlsx mínimo válido (una hoja, cadenas inline) sin
    dependencias nuevas — solo stdlib (`zipfile`), acorde a la filosofía del
    proyecto (CLAUDE.md / precedente en `adapters/ingesta/base.py`)."""
    filas_xml = []
    for numero_fila, valores in enumerate([cabeceras, *filas], start=1):
        celdas = "".join(
            _celda_xml(_columna_excel(i), numero_fila, str(valor)) for i, valor in enumerate(valores)
        )
        filas_xml.append(f'<row r="{numero_fila}">{celdas}</row>')

    hoja_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(filas_xml)}</sheetData>"
        "</worksheet>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels_raiz_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Entidades" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels_workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_raiz_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_workbook_xml)
        zf.writestr("xl/worksheets/sheet1.xml", hoja_xml)


def escribir_csv(ruta: Path, cabeceras: tuple[str, ...], filas: list[tuple[str, ...]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(cabeceras)
        escritor.writerows(filas)


def main() -> None:
    entidades, paginas_recorridas = recolectar_directorio_completo()
    filas = [_fila_de(e) for e in entidades]

    escribir_xlsx(RUTA_XLSX, CABECERAS, filas)
    escribir_csv(RUTA_CSV, CABECERAS, filas)

    con_email = sum(1 for e in entidades if e.emails)
    con_telefono = sum(1 for e in entidades if e.telefonos)

    print()
    print(f"Entidades extraídas: {len(entidades)}")
    print(f"Con email: {con_email}")
    print(f"Con teléfono: {con_telefono}")
    print(f"Páginas recorridas: {paginas_recorridas}")
    print(f"Escrito: {RUTA_XLSX}")
    print(f"Escrito: {RUTA_CSV}")


if __name__ == "__main__":
    main()
