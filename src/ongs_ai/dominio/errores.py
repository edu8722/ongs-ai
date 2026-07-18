"""Excepciones de dominio — nunca framework web ni IA."""


class ErrorDominio(Exception):
    """Base de toda violación de invariante de dominio."""


class DineroInvalidoError(ErrorDominio):
    """Un campo monetario o de puntos básicos no es int (p. ej. llegó como float)."""


class TransicionIlegalError(ErrorDominio):
    """Transición de estado de Match no permitida por la máquina de estados."""
