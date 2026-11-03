"""Compatibilidad: la lógica de resultados ahora vive en nucleo.detecciones."""

from nucleo.detecciones import (
    CLASES_CROMOSOMA,
    clave_orden_clase,
    contar,
    detecciones_a_tabla,
    detecciones_para_bd,
    estado_par,
    formatear_resumen_texto,
    generar_resumen_detallado,
    motivos_revision,
    normalizar_clase,
    obtener_estadisticas_globales,
    preparar_detecciones,
    resultado_revision,
    sugerir_cariotipo,
)
from nucleo.dibujo import recortar_deteccion

__all__ = [
    "CLASES_CROMOSOMA",
    "clave_orden_clase",
    "contar",
    "detecciones_a_tabla",
    "detecciones_para_bd",
    "estado_par",
    "formatear_resumen_texto",
    "generar_resumen_detallado",
    "motivos_revision",
    "normalizar_clase",
    "obtener_estadisticas_globales",
    "preparar_detecciones",
    "recortar_deteccion",
    "resultado_revision",
    "sugerir_cariotipo",
]
