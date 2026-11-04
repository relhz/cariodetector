"""Operaciones sobre detecciones, conteos y resultados.

Formato canónico de una detección:

    {
        "caja": (x1, y1, x2, y2),   # píxeles
        "clase_modelo": "D13",       # lo que dijo el modelo
        "clase_final": "D13",        # lo que quedó tras la revisión
        "confianza": 0.87,
        "descartada": False,
        "n": 1,                      # número de fila para la revisión
    }
"""

from collections import Counter

from .constantes import (
    CLASES_CROMOSOMA,
    CONF_REVISION,
    DE_MAS,
    DE_MENOS,
    NORMAL,
    PARES_AUTOSOMICOS,
    PARES_ORDEN,
    SEXUAL,
)

_CLASES_POR_CODIGO = {clase.upper(): clase for clase in CLASES_CROMOSOMA}


def normalizar_clase(nombre):
    """Unifica nombres: 'cromosoma 13' -> 'D13', 'cromosoma X' -> 'X'."""
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


def nombre_par(nombre):
    """Alias histórico usado por el dashboard."""
    return normalizar_clase(nombre)


def _caja_px(det, ancho=None, alto=None):
    caja = det.get("caja")
    if caja is not None and len(caja) >= 4:
        return tuple(int(round(float(v))) for v in caja[:4])

    bbox = det.get("bbox")
    if bbox is not None and len(bbox) >= 4 and ancho and alto:
        cx, cy, w, h = [float(v) for v in bbox[:4]]
        x1 = int(round((cx - w / 2) * ancho))
        y1 = int(round((cy - h / 2) * alto))
        x2 = int(round((cx + w / 2) * ancho))
        y2 = int(round((cy + h / 2) * alto))
        return (x1, y1, x2, y2)

    return None


def preparar_detecciones(detecciones, ancho=None, alto=None):
    """Completa las detecciones crudas con los campos canónicos.

    Acepta tanto la salida nueva del detector (`caja` en píxeles) como dicts
    antiguos con `bbox` normalizado, siempre que se pasen `ancho` y `alto`.
    """
    preparadas = []

    for indice, det in enumerate(detecciones, start=1):
        clase_original = (
            det.get("clase_modelo")
            or det.get("clase_original")
            or det.get("clase")
            or det.get("nombre_clase")
        )
        clase_modelo = normalizar_clase(clase_original)

        if "clase_final" in det and det["clase_final"]:
            clase_final = normalizar_clase(det["clase_final"])
        elif det.get("nombre_clase") and not det.get("clase_modelo"):
            clase_final = normalizar_clase(det["nombre_clase"])
        else:
            clase_final = clase_modelo

        caja = _caja_px(det, ancho=ancho, alto=alto)

        preparadas.append({
            **det,
            "n": int(det.get("n", indice)),
            "caja": caja,
            "clase_modelo": clase_modelo,
            "clase_final": clase_final,
            "confianza": float(det["confianza"]),
            "descartada": bool(det.get("descartada", False)),
        })

    return preparadas


def contar(clases):
    """Cuenta cuántas veces aparece cada clase. Devuelve {clase: cantidad}."""
    return {clase: clases.count(clase) for clase in set(clases)}


def conteo_desde_detecciones(detecciones, campo="clase_final"):
    return contar([det.get(campo) or det.get("clase_modelo") for det in detecciones])


def estado_par(par, cantidad):
    """Estado de un par según cuántas copias se detectaron."""
    if par in ("X", "Y"):
        return SEXUAL
    if cantidad == 2:
        return NORMAL
    return DE_MAS if cantidad >= 3 else DE_MENOS


def categoria_imagen(fila):
    """Categoría de una imagen a partir de su fila de conteos."""
    de_mas = bool(any(fila.get(par, 0) >= 3 for par in PARES_AUTOSOMICOS))
    de_menos = bool(any(fila.get(par, 0) <= 1 for par in PARES_AUTOSOMICOS))

    from .constantes import CAT_AMBAS, CAT_MAS, CAT_MENOS, CAT_SIN

    if de_mas and de_menos:
        return CAT_AMBAS
    if de_mas:
        return CAT_MAS
    if de_menos:
        return CAT_MENOS
    return CAT_SIN


def matriz_conteos(df):
    """Filas = imágenes, columnas = pares, valores = cantidad detectada."""
    matriz = df.pivot_table(
        index=["imagen_id", "archivo"],
        columns="numero_par",
        values="confianza",
        aggfunc="count",
        fill_value=0,
    )
    return matriz.reindex(columns=PARES_ORDEN, fill_value=0)


def _orden_par(par):
    return PARES_ORDEN.index(par) if par in PARES_ORDEN else 99


# Alias público: el orden canónico de pares también lo usan los informes.
orden_par = _orden_par


def motivos_revision(total, conteo, n_baja):
    """Motivos por los que conviene revisar una imagen (vacía = sin motivos)."""
    from .constantes import CONF_REVISION

    motivos = []
    if total != 46:
        motivos.append(f"Total detectado: {total} (se esperan 46)")

    n_pares = sum(1 for par in PARES_AUTOSOMICOS if conteo.get(par, 0) != 2)
    if n_pares:
        motivos.append(f"{n_pares} par(es) autosómico(s) con cantidad distinta de 2")

    x, y = conteo.get("X", 0), conteo.get("Y", 0)
    if (x, y) not in ((2, 0), (1, 1)):
        motivos.append(f"Combinación X/Y inusual (X={x}, Y={y}); se espera XX o XY")

    if n_baja:
        motivos.append(f"{n_baja} detección(es) con confianza menor a {CONF_REVISION}")

    return motivos


def resumen_deteccion(detecciones, conf_revision=CONF_REVISION):
    """Resumen numérico y motivos de revisión de detecciones canónicas.

    Lo usan las dos interfaces para no repetir el cálculo de conteo,
    detecciones dudosas y pares fuera de lo esperado.
    """
    conteo = contar([
        normalizar_clase(det.get("clase_final") or det.get("clase_modelo"))
        for det in detecciones
    ])
    n_baja = sum(1 for det in detecciones if det["confianza"] < conf_revision)
    pares = sum(1 for par in PARES_AUTOSOMICOS if conteo.get(par, 0) != 2)

    return {
        "conteo": conteo,
        "n_baja": n_baja,
        "pares": pares,
        "motivos": motivos_revision(len(detecciones), conteo, n_baja),
    }


def _numero_cromosoma(codigo):
    codigo = (codigo or "").strip().upper()

    if codigo in ("X", "Y"):
        return codigo

    if len(codigo) >= 2 and codigo[0].isalpha() and codigo[1:].isdigit():
        numero = int(codigo[1:])
        if 1 <= numero <= 22:
            return str(numero)

    return None


def clave_orden_clase(nombre):
    numero = _numero_cromosoma(nombre)

    if numero is None:
        return (2, str(nombre))
    if numero == "X":
        return (1, 23)
    if numero == "Y":
        return (1, 24)

    return (0, int(numero))


def _como_conteo(conteo):
    if isinstance(conteo, dict):
        return conteo
    return contar([normalizar_clase(clase) for clase in conteo])


def alteraciones_numericas(conteo):
    """Ganancias y pérdidas numéricas en los pares autosómicos."""
    conteo = _como_conteo(conteo)
    alteraciones = []
    for numero, par in enumerate(PARES_AUTOSOMICOS, start=1):
        diferencia = conteo.get(par, 0) - 2
        signo = "+" if diferencia > 0 else "-"
        alteraciones.extend([f"{signo}{numero}"] * abs(diferencia))
    return alteraciones


def sugerir_cariotipo(conteo):
    """Cariotipo aproximado a partir del conteo por par.

    Acepta un dict {par: cantidad} o una lista de clases asignadas.
    """
    conteo = _como_conteo(conteo)

    total = sum(cantidad for par, cantidad in conteo.items() if par in PARES_ORDEN)
    x, y = conteo.get("X", 0), conteo.get("Y", 0)

    if x == 0 and y == 0:
        sexo = "?"
    elif y == 0:
        sexo = "X" * x
    elif x == 0:
        sexo = "Y" * y
    else:
        sexo = "X" * x + "Y" * y

    cariotipo = f"{total},{sexo}"
    alteraciones = alteraciones_numericas(conteo)
    if alteraciones:
        cariotipo += "," + ",".join(alteraciones)
    return cariotipo


def resultado_revision(conteo, observacion=None):
    """Datos para la tabla `resultados` cuando un profesional confirma la revisión."""
    conteo = _como_conteo(conteo)
    cariotipo = sugerir_cariotipo(conteo)
    x, y = conteo.get("X", 0), conteo.get("Y", 0)

    partes = list(alteraciones_numericas(conteo))
    if (x, y) not in ((2, 0), (1, 1)):
        partes.append(f"sexuales X={x}, Y={y}")

    alteracion = ", ".join(partes) if partes else "Sin alteraciones numéricas detectadas"
    return {
        "cariotipo": cariotipo[:30],
        "alteracion": alteracion[:100],
        "observacion": observacion,
    }


def detecciones_a_tabla(detecciones):
    filas = []

    for indice, det in enumerate(detecciones, start=1):
        original = normalizar_clase(det.get("clase_modelo", ""))
        actual = normalizar_clase(det.get("clase_final", original))
        corregida = actual != original

        filas.append({
            "numero": indice,
            "detectada": original,
            "asignada": f"{actual} *" if corregida else actual,
            "confianza": f"{det['confianza']:.2%}",
            "corregida": corregida,
        })

    return filas


def generar_resumen_detallado(detecciones):
    from collections import defaultdict

    stats = defaultdict(lambda: {"count": 0, "conf_sum": 0.0, "conf_max": 0.0, "conf_min": 1.0})

    for det in detecciones:
        nombre = normalizar_clase(det.get("clase_final") or det.get("clase_modelo"))
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
            "conf_min": data["conf_min"],
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
                lineas.append(
                    f"{nombre:15s}  {count:2d} detecciones  "
                    f"(conf: {data['conf_promedio']:.2%} avg)"
                )
            else:
                lineas.append(f"{nombre:15s}  {count:2d} detecciones")
        else:
            count = data
            lineas.append(f"{nombre:15s}  {count:2d} detecciones")
        total += count

    lineas.insert(0, f"Total: {total} cromosomas detectados")
    lineas.append("-" * 40)
    return "\n".join(lineas)


def detecciones_para_bd(detecciones, ancho_imagen=None, alto_imagen=None):
    """Convierte detecciones canónicas a las filas que espera MySQL."""
    filas = []

    for det in detecciones:
        if det.get("descartada"):
            continue

        caja = det.get("caja")
        if caja is None:
            caja = _caja_px(det, ancho=ancho_imagen, alto=alto_imagen)
        if caja is None:
            continue

        x1, y1, x2, y2 = [int(round(float(v))) for v in caja[:4]]
        ancho = max(1, x2 - x1)
        alto = max(1, y2 - y1)

        if ancho_imagen is not None:
            x1 = max(0, min(x1, ancho_imagen - 1))
            ancho = max(1, min(ancho, ancho_imagen - x1))
        if alto_imagen is not None:
            y1 = max(0, min(y1, alto_imagen - 1))
            alto = max(1, min(alto, alto_imagen - y1))

        filas.append({
            "clase": normalizar_clase(det.get("clase_modelo")),
            "x": x1,
            "y": y1,
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
            "tipos_unicos": 0,
        }

    confianzas = [det["confianza"] for det in detecciones]
    tipos = set(normalizar_clase(det.get("clase_final") or det.get("clase_modelo")) for det in detecciones)

    return {
        "total": len(detecciones),
        "conf_promedio": sum(confianzas) / len(confianzas),
        "conf_max": max(confianzas),
        "conf_min": min(confianzas),
        "tipos_unicos": len(tipos),
    }
