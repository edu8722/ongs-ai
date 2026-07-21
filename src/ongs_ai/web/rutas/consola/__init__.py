"""Rutas de la consola del OPERADOR — ADR-006. Prefijo común `/consola`.

Módulo propio por feature (CLAUDE.md): `app.py` solo gana un `include_router`
más por cada submódulo (`auth`, `prospectos`, `entidades`); ninguno de estos
ficheros importa `web.dependencias.entidad_actual`.
"""
