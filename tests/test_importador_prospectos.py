"""Tests del importador puro del maestro de prospección (ADR-006 §2.4/§4.1).

HERMÉTICOS: filas sintéticas en memoria, JAMÁS el fichero real del maestro
(que además está gitignorado y contiene PII). Degradación limpia: fila sin
nombre se descarta y cuenta; valor de Ámbito no mapeable -> None y cuenta.
"""
from __future__ import annotations

from ongs_ai.dominio.entidades import AmbitoTerritorial, Contacto
from ongs_ai.prospeccion.importador import importar_prospectos


def _generador_id():
    contador = iter(f"prospecto-fijo-{i}" for i in range(1, 1000))
    return lambda: next(contador)


def _fila(**overrides) -> dict:
    base = {
        "Nombre": "Asociación de Prueba",
        "Web": "https://prueba.example.org",
        "Email": "contacto@prueba.example.org",
        "Teléfono": "600111222",
        "Ámbito": "nacional",
        "CCAA": "Andalucía",
        "Enfermedad / Colectivo": "colectivo de prueba",
        "Personas visibles (cargo)": "Persona Ficticia — presidenta (sintética)",
        "Tamaño": "pequeña",
        "Fuente(s)": "Fuente sintética",
        "Notas": "notas sintéticas",
    }
    base.update(overrides)
    return base


def test_fila_completa_produce_prospecto_correcto():
    resultado = importar_prospectos([_fila()], generador_id=_generador_id())

    assert resultado.filas_descartadas_sin_nombre == 0
    assert resultado.valores_ambito_no_mapeados == 0
    assert len(resultado.prospectos) == 1

    prospecto = resultado.prospectos[0]
    assert prospecto.nombre == "Asociación de Prueba"
    assert prospecto.web == "https://prueba.example.org"
    assert prospecto.contacto == Contacto(email="contacto@prueba.example.org", telefono="600111222")
    assert prospecto.ambito_territorial is AmbitoTerritorial.NACIONAL
    assert prospecto.region == "Andalucía"
    assert prospecto.enfermedad_o_colectivo == "colectivo de prueba"
    assert prospecto.contacto_personal_nota == "Persona Ficticia — presidenta (sintética)"
    assert prospecto.tamano == "pequeña"
    assert prospecto.fuente_maestro == "Fuente sintética"
    assert prospecto.notas == "notas sintéticas"
    assert prospecto.prospecto_id == "prospecto-fijo-1"


def test_fila_sin_nombre_se_descarta_y_cuenta():
    filas = [_fila(Nombre=""), _fila(Nombre="   "), _fila()]

    resultado = importar_prospectos(filas, generador_id=_generador_id())

    assert resultado.filas_descartadas_sin_nombre == 2
    assert len(resultado.prospectos) == 1


def test_nombre_ausente_del_dict_tambien_se_descarta():
    fila_sin_columna = _fila()
    del fila_sin_columna["Nombre"]

    resultado = importar_prospectos([fila_sin_columna], generador_id=_generador_id())

    assert resultado.filas_descartadas_sin_nombre == 1
    assert resultado.prospectos == ()


def test_ambito_con_tilde_se_normaliza_como_adr002():
    resultado = importar_prospectos([_fila(Ámbito="autonómico")], generador_id=_generador_id())

    assert resultado.valores_ambito_no_mapeados == 0
    assert resultado.prospectos[0].ambito_territorial is AmbitoTerritorial.AUTONOMICO


def test_ambito_no_mapeable_queda_none_y_cuenta():
    resultado = importar_prospectos(
        [_fila(Ámbito="nacional (sede Murcia)")], generador_id=_generador_id()
    )

    assert resultado.valores_ambito_no_mapeados == 1
    assert resultado.prospectos[0].ambito_territorial is None


def test_ambito_vacio_no_cuenta_como_no_mapeado():
    resultado = importar_prospectos([_fila(Ámbito="")], generador_id=_generador_id())

    assert resultado.valores_ambito_no_mapeados == 0
    assert resultado.prospectos[0].ambito_territorial is None


def test_ccaa_sin_ccaa_se_trata_como_vacio():
    resultado = importar_prospectos([_fila(CCAA="(sin CCAA)")], generador_id=_generador_id())

    assert resultado.prospectos[0].region is None


def test_ccaa_vacia_se_trata_como_vacio():
    resultado = importar_prospectos([_fila(CCAA="")], generador_id=_generador_id())

    assert resultado.prospectos[0].region is None


def test_email_con_varios_separados_por_punto_y_coma_coge_el_primero():
    resultado = importar_prospectos(
        [_fila(Email="primero@example.org;segundo@example.org")], generador_id=_generador_id()
    )

    assert resultado.prospectos[0].contacto.email == "primero@example.org"


def test_email_y_telefono_vacios_producen_contacto_none():
    resultado = importar_prospectos([_fila(Email="", Teléfono="")], generador_id=_generador_id())

    assert resultado.prospectos[0].contacto is None


def test_campos_vacios_quedan_none_nunca_inventados():
    fila = _fila(
        Web="",
        **{
            "Enfermedad / Colectivo": "",
            "Personas visibles (cargo)": "",
            "Tamaño": "",
            "Fuente(s)": "",
            "Notas": "",
        },
    )
    resultado = importar_prospectos([fila], generador_id=_generador_id())

    prospecto = resultado.prospectos[0]
    assert prospecto.web is None
    assert prospecto.enfermedad_o_colectivo is None
    assert prospecto.contacto_personal_nota is None
    assert prospecto.tamano is None
    assert prospecto.fuente_maestro == ""
    assert prospecto.notas is None


def test_prospecto_id_es_opaco_nunca_derivado_del_nombre():
    resultado = importar_prospectos(
        [_fila(Nombre="Asociación X"), _fila(Nombre="Asociación Y")], generador_id=_generador_id()
    )

    ids = [p.prospecto_id for p in resultado.prospectos]
    assert ids == ["prospecto-fijo-1", "prospecto-fijo-2"]
    assert "Asociación X" not in ids[0]
    assert "Asociación Y" not in ids[1]
