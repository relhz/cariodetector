from collections import Counter


# Clases que produce el modelo, en orden cromosómico (grupos Denver).
CLASES_CROMOSOMA = (
    ["A1", "A2", "A3", "B4", "B5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "D13", "D14", "D15", "E16", "E17", "E18", "F19", "F20", "G21", "G22", "X", "Y"]
)

_CLASES_POR_CODIGO = {clase.upper(): clase for clase in CLASES_CROMOSOMA}


def normalizar_clase(nombre):
    
    if nombre is None:
        return ""

    texto = str(nombre).strip()
    if not texto:
        return ""

    codigo = _CLASES_POR_CODIGO.get(texto.upper())
    if codigo is not None:
        return codigo

    texto_minusculas = texto.lower()
    if texto_minusculas.startswith("cromosoma "):
        sufijo = texto_minusculas.split()[-1]
        if sufijo in ("x", "y"):
            return sufijo.upper()
        if sufijo.isdigit() and 1 <= int(sufijo) <= 22:
            return CLASES_CROMOSOMA[int(sufijo) - 1]

    return texto


def preparar_detecciones(detecciones):
    """
    Normaliza las clases de las detecciones y conserva la clase detectada.

    `nombre_clase` pasa a ser la clase efectiva (la que se puede corregir) y
    `clase_original` guarda la salida original del modelo.
    """
    for det in detecciones:
        clase = normalizar_clase(det.get("nombre_clase"))
        det.setdefault("clase_original", clase)
        det["nombre_clase"] = clase

    return detecciones


def _numero_cromosoma(codigo):
    """Convierte 'A1', 'C10', 'X' o 'Y' al número/letra del cromosoma."""
    codigo = (codigo or "").strip().upper()

    if codigo in ("X", "Y"):
        return codigo

    if len(codigo) >= 2 and codigo[0].isalpha() and codigo[1:].isdigit():
        numero = int(codigo[1:])
        if 1 <= numero <= 22:
            return str(numero)

    return None


def clave_orden_clase(nombre):
    """Clave para ordenar clases como A1, A2, ..., G22, X, Y."""
    numero = _numero_cromosoma(nombre)

    if numero is None:
        return (2, str(nombre))
    if numero == "X":
        return (1, 23)
    if numero == "Y":
        return (1, 24)

    return (0, int(numero))


def sugerir_cariotipo(asignaciones):
    """
    Arma un cariotipo aproximado a partir de las clases asignadas.
    """
    conteo = Counter()

    for codigo in asignaciones:
        numero = _numero_cromosoma(codigo)
        if numero is not None:
            conteo[numero] += 1

    if not conteo:
        return ""

    total = sum(conteo.values())
    x = conteo.get("X", 0)
    y = conteo.get("Y", 0)

    if x == 0 and y == 0:
        sexo = "?"
    elif y == 0:
        sexo = "X" * x
    elif x == 0:
        sexo = "Y" * y
    else:
        sexo = "X" * x + "Y" * y

    anomalias = []
    for numero in range(1, 23):
        diferencia = conteo.get(str(numero), 0) - 2
        if diferencia > 0:
            anomalias.extend([f"+{numero}"] * diferencia)
        elif diferencia < 0:
            anomalias.extend([f"-{numero}"] * (-diferencia))

    cariotipo = f"{total},{sexo}"
    if anomalias:
        cariotipo += "," + ",".join(anomalias)

    return cariotipo


def detecciones_a_tabla(detecciones):
    """
    Prepara las filas de la tabla de detecciones.

    Cada fila incluye la clase detectada por el modelo, la clase efectiva
    (eventualmente corregida) y si hubo una corrección.
    """
    filas = []

    for indice, det in enumerate(detecciones):
        nombre = det.get("nombre_clase", "")
        original = det.get("clase_original", nombre)
        corregida = nombre != original

        filas.append({
            "numero": indice + 1,
            "detectada": original,
            "asignada": f"{nombre} *" if corregida else nombre,
            "confianza": f"{det['confianza']:.2%}",
            "corregida": corregida,
        })

    return filas


def recortar_deteccion(imagen, bbox, margen=0.15):
    """
    Recorta la región de una detección de la imagen original.

    `bbox` viene en formato [cx, cy, w, h] normalizado. Se agrega un margen
    relativo al tamaño de la caja para no cortar los brazos del cromosoma.
    Devuelve el fragmento BGR o None si no se puede recortar.
    """
    if imagen is None or not bbox or len(bbox) < 4:
        return None

    alto, ancho = imagen.shape[:2]
    cx, cy, w, h = bbox[:4]

    x1 = int(round((cx - w / 2 - w * margen) * ancho))
    y1 = int(round((cy - h / 2 - h * margen) * alto))
    x2 = int(round((cx + w / 2 + w * margen) * ancho))
    y2 = int(round((cy + h / 2 + h * margen) * alto))

    x1 = max(0, min(x1, ancho - 1))
    y1 = max(0, min(y1, alto - 1))
    x2 = max(x1 + 1, min(x2, ancho))
    y2 = max(y1 + 1, min(y2, alto))

    recorte = imagen[y1:y2, x1:x2]
    return recorte if recorte.size else None

def generar_resumen_detallado(detecciones):

    from collections import defaultdict

    stats = defaultdict(lambda: {"count": 0, "conf_sum": 0.0, "conf_max": 0.0, "conf_min": 1.0})

    for det in detecciones:
        nombre = det["nombre_clase"]
        conf = det["confianza"]
        stats[nombre]["count"] += 1
        stats[nombre]["conf_sum"] += conf
        stats[nombre]["conf_max"] = max(stats[nombre]["conf_max"], conf)
        stats[nombre]["conf_min"] = min(stats[nombre]["conf_min"], conf)

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

    if not resumen:
        return "Sin detecciones"

    lineas = []
    total = 0

    for nombre in sorted(resumen.keys(), key=clave_orden_clase):
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
        total += count      # type: ignore

    lineas.insert(0, f"Total: {total} cromosomas detectados")
    lineas.append("-" * 40)
    return "\n".join(lineas)


def detecciones_para_bd(detecciones, ancho_imagen, alto_imagen):
    """
    Convierte las detecciones del modelo al formato que espera la tabla
    `cromosomas`.

    El modelo entrega [x_centro, y_centro, ancho, alto] normalizados (0..1),
    mientras que la base guarda la esquina superior izquierda y el tamaño en
    píxeles enteros.
    """
    filas = []

    for det in detecciones:
        x_centro, y_centro, ancho_norm, alto_norm = det["bbox"]

        x = int(round((x_centro - ancho_norm / 2) * ancho_imagen))
        y = int(round((y_centro - alto_norm / 2) * alto_imagen))
        ancho = int(round(ancho_norm * ancho_imagen))
        alto = int(round(alto_norm * alto_imagen))

        # Evitar coordenadas fuera de la imagen o cajas de tamaño cero.
        x = max(0, min(x, ancho_imagen - 1))
        y = max(0, min(y, alto_imagen - 1))
        ancho = max(1, min(ancho, ancho_imagen - x))
        alto = max(1, min(alto, alto_imagen - y))

        filas.append({
            "clase": normalizar_clase(det.get("nombre_clase", "")),
            "x": x,
            "y": y,
            "ancho": ancho,
            "alto": alto,
            "confianza": round(float(det["confianza"]), 4),
        })

    return filas


def obtener_estadisticas_globales(detecciones):
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
