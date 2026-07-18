"""Contrato de datos central — ADR-001 (engineering/ADR-001-contrato-de-datos.md).

Dominio puro: sin dependencias de framework web ni de IA. Todo campo monetario
y `porcentaje_max_financiable` son int (céntimos / puntos básicos), nunca float.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from ongs_ai.dominio.errores import DineroInvalidoError, ErrorDominio


def _validar_entero(valor: int, nombre: str) -> None:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise DineroInvalidoError(
            f"{nombre} debe ser int (céntimos o puntos básicos), nunca "
            f"{type(valor).__name__} — recibido: {valor!r}"
        )


# --- Ámbito territorial (compartido por Entidad y Convocatoria) ---------


class AmbitoTerritorial(str, Enum):
    NACIONAL = "nacional"
    AUTONOMICO = "autonomico"
    PROVINCIAL = "provincial"
    LOCAL = "local"


# --- Actividad (§1.3 del ADR — enum cerrado, extensible SOLO por ADR) ---


class TipoActividad(str, Enum):
    VOLUNTARIADO = "voluntariado"
    ENCUENTRO_DE_PACIENTES = "encuentro_de_pacientes"
    CHARLAS_Y_SENSIBILIZACION = "charlas_y_sensibilizacion"
    FORMACION = "formacion"
    INVESTIGACION_Y_ESTUDIOS = "investigacion_y_estudios"
    ATENCION_DIRECTA_A_FAMILIAS = "atencion_directa_a_familias"
    OTRO = "otro"


@dataclass(frozen=True)
class ActividadDeclarada:
    """Una actividad declarada por una Entidad. `descripcion` obligatoria si tipo=OTRO."""

    tipo: TipoActividad
    descripcion: str | None = None

    def __post_init__(self) -> None:
        if self.tipo is TipoActividad.OTRO and not self.descripcion:
            raise ErrorDominio(
                "ActividadDeclarada con tipo=OTRO exige 'descripcion' (ADR §1.3)"
            )


# --- Flags de requisitos formales (cerrados, §1.1/§1.2 del ADR) ---------


class RequisitoFormal(str, Enum):
    INSCRITA_REGISTRO_ASOCIACIONES = "inscrita_registro_asociaciones"
    DECLARADA_UTILIDAD_PUBLICA = "declarada_utilidad_publica"
    CERTIFICADO_ESTAR_AL_CORRIENTE_AEAT = "certificado_estar_al_corriente_aeat"
    CERTIFICADO_ESTAR_AL_CORRIENTE_SS = "certificado_estar_al_corriente_ss"


# --- Forma jurídica (ADR-002 — enum cerrado, extensible SOLO por ADR) ---


class FormaJuridica(str, Enum):
    ASOCIACION = "asociacion"
    FUNDACION = "fundacion"
    FEDERACION_O_CONFEDERACION = "federacion_o_confederacion"
    OTRA = "otra"


@dataclass(frozen=True)
class FormaJuridicaDeclarada:
    """Forma jurídica declarada por una Entidad. `descripcion` obligatoria si tipo=OTRA."""

    tipo: FormaJuridica
    descripcion: str | None = None

    def __post_init__(self) -> None:
        if self.tipo is FormaJuridica.OTRA and not self.descripcion:
            raise ErrorDominio(
                "FormaJuridicaDeclarada con tipo=OTRA exige 'descripcion' (ADR-002)"
            )


# --- Normalización determinista forma_juridica_requerida -> FormaJuridica
#     (ADR-002 — mapeo cerrado, sin LLM en el camino; vive en dominio) -----

_TABLA_TILDES = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")

_MAPA_FORMA_JURIDICA: dict[str, FormaJuridica] = {
    "asociacion": FormaJuridica.ASOCIACION,
    "asociaciones": FormaJuridica.ASOCIACION,
    "asociacion sin animo de lucro": FormaJuridica.ASOCIACION,
    "asociaciones sin animo de lucro": FormaJuridica.ASOCIACION,
    "asoc": FormaJuridica.ASOCIACION,
    "fundacion": FormaJuridica.FUNDACION,
    "fundaciones": FormaJuridica.FUNDACION,
    "federacion": FormaJuridica.FEDERACION_O_CONFEDERACION,
    "federaciones": FormaJuridica.FEDERACION_O_CONFEDERACION,
    "confederacion": FormaJuridica.FEDERACION_O_CONFEDERACION,
    "confederaciones": FormaJuridica.FEDERACION_O_CONFEDERACION,
    "federacion o confederacion": FormaJuridica.FEDERACION_O_CONFEDERACION,
    "federacion/confederacion": FormaJuridica.FEDERACION_O_CONFEDERACION,
}


def normalizar_forma_juridica(texto: str) -> FormaJuridica | None:
    """Normaliza un `forma_juridica_requerida` (texto libre, extracción IA) contra el
    mapeo cerrado de sinónimos → `FormaJuridica` (ADR-002 §2.3).

    Determinista, sin LLM: minúsculas + sin tildes + espacios colapsados. `OTRA`
    nunca es resultado de esta normalización (es declaración humana, no inferible
    de un texto). Si no hay mapeo posible, devuelve `None` — el requisito queda
    NO EVALUABLE (degrada limpio, nunca inventa).
    """
    if not texto:
        return None
    clave = " ".join(texto.strip().lower().translate(_TABLA_TILDES).split())
    return _MAPA_FORMA_JURIDICA.get(clave)


# --- Entidad (§1.1 del ADR — el tenant) ----------------------------------


@dataclass(frozen=True)
class DatosEconomicos:
    ingresos_centimos: int
    gastos_centimos: int
    ejercicio: int

    def __post_init__(self) -> None:
        _validar_entero(self.ingresos_centimos, "ingresos_centimos")
        _validar_entero(self.gastos_centimos, "gastos_centimos")


@dataclass(frozen=True)
class Contacto:
    email: str | None = None
    telefono: str | None = None


@dataclass(frozen=True)
class Entidad:
    entidad_id: str
    nombre_legal: str
    nif: str
    ambito_territorial: AmbitoTerritorial
    forma_juridica: FormaJuridicaDeclarada
    fecha_constitucion: date
    enfermedad_o_colectivo: str
    actividades: tuple[ActividadDeclarada, ...]
    datos_economicos_ejercicio_anterior: DatosEconomicos
    requisitos_formales_disponibles: tuple[RequisitoFormal, ...]
    contacto: Contacto
    creado_en: datetime
    actualizado_en: datetime
    region: str | None = None
    provincia: str | None = None


# --- Convocatoria (§1.2 del ADR) -----------------------------------------


class TipoFuente(str, Enum):
    PUBLICA_NACIONAL = "publica_nacional"
    PUBLICA_AUTONOMICA = "publica_autonomica"
    PUBLICA_LOCAL = "publica_local"
    PRIVADA = "privada"


@dataclass(frozen=True)
class Fuente:
    portal: str
    url_origen: str
    tipo: TipoFuente


@dataclass(frozen=True)
class RequisitosElegibilidad:
    """Condiciones evaluables por el guardarraíl determinista (nunca por IA en runtime)."""

    ambito_territorial_requerido: AmbitoTerritorial | None = None
    forma_juridica_requerida: str | None = None
    antiguedad_minima_anios: int | None = None
    requisitos_formales_requeridos: tuple[RequisitoFormal, ...] = ()
    exclusiones: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plazos:
    fecha_apertura: date | None = None
    fecha_cierre: date | None = None
    fecha_resolucion_estimada: date | None = None


@dataclass(frozen=True)
class Cuantias:
    importe_minimo_centimos: int | None = None
    importe_maximo_centimos: int | None = None
    porcentaje_max_financiable: int | None = None  # puntos básicos: 8000 = 80%

    def __post_init__(self) -> None:
        if self.importe_minimo_centimos is not None:
            _validar_entero(self.importe_minimo_centimos, "importe_minimo_centimos")
        if self.importe_maximo_centimos is not None:
            _validar_entero(self.importe_maximo_centimos, "importe_maximo_centimos")
        if self.porcentaje_max_financiable is not None:
            _validar_entero(
                self.porcentaje_max_financiable, "porcentaje_max_financiable"
            )


class EstadoIngesta(str, Enum):
    DETECTADA = "detectada"
    EXTRAIDA = "extraida"
    VERIFICADA = "verificada"
    DESCARTADA_POR_DOMINIO = "descartada_por_dominio"


@dataclass(frozen=True)
class Convocatoria:
    convocatoria_id: str
    fuente: Fuente
    objeto: str
    beneficiarios_elegibles: str
    requisitos_elegibilidad: RequisitosElegibilidad
    ambito_geografico: AmbitoTerritorial
    plazos: Plazos
    cuantias: Cuantias
    estado_ingesta: EstadoIngesta
    creado_en: datetime
    actualizado_en: datetime
    documento_origen_ref: str | None = None
    region: str | None = None
    provincia: str | None = None
