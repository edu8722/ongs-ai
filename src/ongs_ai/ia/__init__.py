"""Capa IA — aislada del dominio, mockeable, nunca decide (ADR-001 §2, §3.2).

La IA propone (explicaciones, extracciones); el dominio valida. Cualquier
fallo en esta capa degrada limpio: el llamador sigue con `explicacion_ia=None`,
nunca se lanza al dominio.
"""
