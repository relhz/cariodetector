from decimal import Decimal

from utils.db_config import obtener_conexion


def _convertir(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _consultar(sql, parametros=()):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(sql, parametros)
        filas = cursor.fetchall()
        cursor.close()
    finally:
        conexion.close()

    return [
        {clave: _convertir(valor) for clave, valor in fila.items()}
        for fila in filas
    ]


def listar_estudios():
    """Estudios guardados, para el selector de la pestaña."""
    return _consultar("""
        SELECT id_estudio, imagen_original, fecha_analisis, estado
        FROM vista_resumen_estudios
        ORDER BY id_estudio DESC
    """)


def resumen_global():
    """Totales generales de la base."""
    filas = _consultar("""
        SELECT total_estudios, total_cromosomas, promedio_cromosomas_por_estudio
        FROM vista_estadisticas_globales
    """)

    if filas:
        return filas[0]

    return {
        "total_estudios": 0,
        "total_cromosomas": 0,
        "promedio_cromosomas_por_estudio": 0.0,
    }


def resumen_estudios(id_estudio=None):
    """Una fila por estudio con totales, confianza y estado."""
    sql = """
        SELECT id_estudio, imagen_original, fecha_analisis,
               total_detecciones, detecciones_guardadas, tipos,
               confianza_promedio, estado, cariotipo, alteracion
        FROM vista_resumen_estudios
    """
    parametros = ()

    if id_estudio is not None:
        sql += " WHERE id_estudio = %s"
        parametros = (id_estudio,)

    sql += " ORDER BY id_estudio"

    return _consultar(sql, parametros)


def estudios_por_estado():
    """Cantidad de estudios agrupados por estado."""
    return _consultar("""
        SELECT estado, cantidad
        FROM vista_estudios_por_estado
    """)


def clases_globales():
    """Cantidad y confianza por clase, sumando todos los estudios."""
    return _consultar("""
        SELECT clase_detectada, cantidad, confianza_promedio,
               confianza_minima, confianza_maxima
        FROM vista_clases_globales
    """)


def clases_por_estudio(id_estudio=None):
    """
    Cantidad y confianza por clase.

    Si se indica un estudio, devuelve solo sus clases. Si es None, devuelve
    el agregado de todos los estudios.
    """
    if id_estudio is None:
        return clases_globales()

    return _consultar("""
        SELECT clase_detectada, cantidad, confianza_promedio,
               confianza_minima, confianza_maxima
        FROM vista_estadisticas_clase
        WHERE id_estudio = %s
    """, (id_estudio,))


def detalle_estudio(id_estudio):
    """
    Datos para el detalle de un estudio: clases y confianzas individuales.
    """
    clases = clases_por_estudio(id_estudio)

    confianzas = _consultar("""
        SELECT confianza
        FROM cromosomas
        WHERE id_estudio = %s
          AND confianza IS NOT NULL
        ORDER BY id_cromosoma
    """, (id_estudio,))

    return clases, [fila["confianza"] for fila in confianzas]
