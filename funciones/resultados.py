"""
Funciones auxiliares para procesar y formatear resultados de detección.
Transforma salidas del modelo a estructuras fáciles de mostrar en la interfaz.
"""

from collections import Counter


def detecciones_a_tabla(detecciones):
    """
    Convierte lista de detecciones a lista de filas para tabla/Treeview.

    Args:
        detecciones: lista de dicts con clase_id, nombre_clase, confianza, bbox

    Returns:
        lista de tuplas: (nombre_clase, confianza_str, bbox_str)
    """
    filas = []
    for det in detecciones:
        nombre = det["nombre_clase"]
        confianza = f"{det['confianza']:.2%}"
        bbox = det["bbox"]  # [x, y, w, h] normalizado
        bbox_str = f"({bbox[0]:.3f}, {bbox[1]:.3f}, {bbox[2]:.3f}, {bbox[3]:.3f})"
        filas.append((nombre, confianza, bbox_str))
    return filas


def generar_resumen_conteo(detecciones):
    """
    Genera resumen de conteos por tipo de cromosoma.

    Returns:
        dict: {nombre_clase: count}
    """
    contador = Counter(d["nombre_clase"] for d in detecciones)
    return dict(contador)


def generar_resumen_detallado(detecciones):
    """
    Genera resumen con estadísticas por tipo.

    Returns:
        dict: {nombre_clase: {"count": int, "conf_promedio": float, "conf_max": float, "conf_min": float}}
    """
    from collections import defaultdict

    stats = defaultdict(lambda: {"count": 0, "conf_sum": 0.0, "conf_max": 0.0, "conf_min": 1.0})

    for det in detecciones:
        nombre = det["nombre_clase"]
        conf = det["confianza"]
        stats[nombre]["count"] += 1
        stats[nombre]["conf_sum"] += conf
        stats[nombre]["conf_max"] = max(stats[nombre]["conf_max"], conf)
        stats[nombre]["conf_min"] = min(stats[nombre]["conf_min"], conf)

    # Calcular promedios
    resumen = {}
    for nombre, data in stats.items():
        resumen[nombre] = {
            "count": data["count"],
            "conf_promedio": data["conf_sum"] / data["count"],
            "conf_max": data["conf_max"],
            "conf_min": data["conf_min"]
        }

    return resumen


def formatear_resumen_texto(resumen):
    """
    Formatea el resumen como texto legible para mostrar en la interfaz.

    Args:
        resumen: dict de generar_resumen_conteo o generar_resumen_detallado

    Returns:
        str multilínea
    """
    if not resumen:
        return "Sin detecciones"

    lineas = []
    total = 0

    # Ordenar: primero numéricos (1-22), luego X, Y
    def orden_clave(nombre):
        try:
            num = int(nombre.split()[-1])
            return (0, num)
        except ValueError:
            if nombre.endswith("X"):
                return (1, 23)
            if nombre.endswith("Y"):
                return (1, 24)
            return (2, nombre)

    for nombre in sorted(resumen.keys(), key=orden_clave):
        data = resumen[nombre]
        if isinstance(data, dict) and "count" in data:
            count = data["count"]
            if "conf_promedio" in data:
                lineas.append(f"{nombre:15s}  {count:2d} detecciones  (conf: {data['conf_promedio']:.2%} avg)")
            else:
                lineas.append(f"{nombre:15s}  {count:2d} detecciones")
        else:
            count = data
            lineas.append(f"{nombre:15s}  {count:2d} detecciones")
        total += count

    lineas.insert(0, f"Total: {total} cromosomas detectados")
    lineas.append("-" * 40)
    return "\n".join(lineas)


def detecciones_para_bd(detecciones, analisis_id):
    """
    Prepara detecciones para insertar en base de datos.

    Returns:
        lista de tuplas: (analisis_id, clase_id, nombre_clase, confianza, bbox_x, bbox_y, bbox_w, bbox_h)
    """
    filas = []
    for det in detecciones:
        bbox = det["bbox"]
        filas.append((
            analisis_id,
            det["clase_id"],
            det["nombre_clase"],
            round(det["confianza"], 4),
            round(bbox[0], 4),
            round(bbox[1], 4),
            round(bbox[2], 4),
            round(bbox[3], 4)
        ))
    return filas


def ordenar_detecciones_por_posicion(detecciones):
    """
    Ordena detecciones por posición en imagen (arriba-abajo, izquierda-derecha).
    Útil para presentar en orden de lectura cariotípica.
    """
    return sorted(detecciones, key=lambda d: (d["bbox"][1], d["bbox"][0]))


def filtrar_por_confianza(detecciones, umbral=0.5):
    """
    Filtra detecciones por umbral de confianza.
    """
    return [d for d in detecciones if d["confianza"] >= umbral]


def obtener_estadisticas_globales(detecciones):
    """
    Calcula estadísticas globales del análisis.
    """
    if not detecciones:
        return {
            "total": 0,
            "conf_promedio": 0.0,
            "conf_max": 0.0,
            "conf_min": 0.0,
            "tipos_unicos": 0
        }

    confianzas = [d["confianza"] for d in detecciones]
    tipos = set(d["nombre_clase"] for d in detecciones)

    return {
        "total": len(detecciones),
        "conf_promedio": sum(confianzas) / len(confianzas),
        "conf_max": max(confianzas),
        "conf_min": min(confianzas),
        "tipos_unicos": len(tipos)
    }


if __name__ == "__main__":
    # Test rápido con datos ficticios
    detecciones_test = [
        {"clase_id": 0, "nombre_clase": "cromosoma 1", "confianza": 0.95, "bbox": [0.1, 0.2, 0.05, 0.1]},
        {"clase_id": 1, "nombre_clase": "cromosoma 2", "confianza": 0.92, "bbox": [0.2, 0.2, 0.05, 0.1]},
        {"clase_id": 0, "nombre_clase": "cromosoma 1", "confianza": 0.88, "bbox": [0.3, 0.2, 0.05, 0.1]},
        {"clase_id": 22, "nombre_clase": "cromosoma X", "confianza": 0.99, "bbox": [0.5, 0.5, 0.05, 0.1]},
    ]

    print("=== Tabla ===")
    for fila in detecciones_a_tabla(detecciones_test):
        print(fila)

    print("\n=== Resumen conteo ===")
    print(generar_resumen_conteo(detecciones_test))

    print("\n=== Resumen detallado ===")
    print(generar_resumen_detallado(detecciones_test))

    print("\n=== Texto formateado ===")
    print(formatear_resumen_texto(generar_resumen_detallado(detecciones_test)))

    print("\n=== Stats globales ===")
    print(obtener_estadisticas_globales(detecciones_test))