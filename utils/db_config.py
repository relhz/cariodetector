"""Compatibilidad: la configuración de MySQL ahora vive en nucleo.db."""

from nucleo.db import DB_CONFIG, _conectar as obtener_conexion, probar_conexion

__all__ = ["DB_CONFIG", "obtener_conexion", "probar_conexion"]
