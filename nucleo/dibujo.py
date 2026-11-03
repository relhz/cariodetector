"""Dibujo de detecciones y composición de recortes (OpenCV)."""

import colorsys

import cv2
import numpy as np

from .constantes import CLASES_CROMOSOMA, CONF_REVISION, PARES_AUTOSOMICOS, PARES_ORDEN


def _paleta_clases():
    paleta = {}
    for indice, nombre in enumerate(CLASES_CROMOSOMA):
        hue = (indice * 0.381966) % 1.0  # ángulo áureo: clases vecinas bien distintas
        valor = 0.62 if 0.12 < hue < 0.45 else 0.78
        r, g, b = colorsys.hsv_to_rgb(hue, 0.85, valor)
        paleta[nombre] = (int(b * 255), int(g * 255), int(r * 255))  # BGR
    return paleta


COLOR_CLASE = _paleta_clases()


def color_bgr(clase):
    return COLOR_CLASE.get(str(clase).strip().upper(), (117, 117, 117))


def _clase_modelo(det):
    return det.get("clase_modelo") or det.get("clase") or det.get("nombre_clase") or ""


def _clase_final(det):
    return det.get("clase_final") or det.get("clase_modelo") or det.get("clase") or det.get("nombre_clase") or ""


def dibujar(imagen, detecciones, resaltar=None):
    """Dibuja las cajas con el color de la clase final.

    La etiqueta lleva fondo de color, '?' marca confianza baja (conviene
    revisar) y '*' una etiqueta corregida por el profesional.
    """
    salida = imagen.copy()
    escala = max(0.4, min(salida.shape[:2]) / 1400)

    for det in detecciones:
        caja = det.get("caja")
        if caja is None or len(caja) < 4:
            continue

        x1, y1, x2, y2 = [int(v) for v in caja[:4]]
        clase_final = _clase_final(det)
        clase_modelo = _clase_modelo(det)
        color = color_bgr(clase_final)
        dudosa = det["confianza"] < CONF_REVISION
        corregida = clase_final != clase_modelo

        if resaltar is not None and det.get("n") == resaltar:
            cv2.rectangle(salida, (x1 - 5, y1 - 5), (x2 + 5, y2 + 5), (255, 255, 255), 4)
            cv2.rectangle(salida, (x1 - 5, y1 - 5), (x2 + 5, y2 + 5), (0, 0, 0), 1)

        cv2.rectangle(salida, (x1, y1), (x2, y2), color, 3 if dudosa else 2)
        texto = (
            f"{clase_final} {det['confianza']:.2f}"
            + ("?" if dudosa else "")
            + ("*" if corregida else "")
        )
        (ancho_texto, alto_texto), base = cv2.getTextSize(
            texto, cv2.FONT_HERSHEY_SIMPLEX, escala, 1
        )
        ytop = max(alto_texto + base + 2, y1)
        cv2.rectangle(
            salida,
            (x1, ytop - alto_texto - base - 2),
            (x1 + ancho_texto + 4, ytop),
            color,
            -1,
        )
        cv2.putText(
            salida,
            texto,
            (x1 + 2, ytop - base),
            cv2.FONT_HERSHEY_SIMPLEX,
            escala,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return salida


def recortar_deteccion(imagen, caja, margen=0.15):
    """Recorta una detección con margen. `caja` está en píxeles."""
    if imagen is None or caja is None or len(caja) < 4:
        return None

    alto, ancho = imagen.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in caja[:4]]

    margen_x = int((x2 - x1) * margen)
    margen_y = int((y2 - y1) * margen)

    x1 = max(0, min(int(x1) - margen_x, ancho - 1))
    y1 = max(0, min(int(y1) - margen_y, alto - 1))
    x2 = max(x1 + 1, min(int(x2) + margen_x, ancho))
    y2 = max(y1 + 1, min(int(y2) + margen_y, alto))

    recorte = imagen[y1:y2, x1:x2]
    return recorte if recorte.size else None


def cariograma_recortes(imagen, detecciones, celda=(120, 190), margen=0.12):
    """Cariograma armado con los recortes ordenados por par."""
    ancho_celda_base, alto_celda = celda
    pie = 26
    filas_pares = [PARES_ORDEN[:12], PARES_ORDEN[12:]]
    lienzo = np.full(
        (len(filas_pares) * (alto_celda + pie) + 8, 12 * ancho_celda_base, 3), 255, np.uint8
    )
    alto_imagen, ancho_imagen = imagen.shape[:2]

    for fila, pares in enumerate(filas_pares):
        for columna, par in enumerate(pares):
            detecciones_par = sorted(
                (det for det in detecciones if _clase_final(det) == par),
                key=lambda det: -det["confianza"],
            )
            origen_x = columna * ancho_celda_base
            origen_y = fila * (alto_celda + pie) + 4
            ancho_celda = (ancho_celda_base - 6) // max(len(detecciones_par), 2)

            for indice, det in enumerate(detecciones_par):
                caja = det.get("caja")
                if caja is None or len(caja) < 4:
                    continue
                x1, y1, x2, y2 = [int(v) for v in caja[:4]]
                margen_x = int((x2 - x1) * margen)
                margen_y = int((y2 - y1) * margen)
                recorte = imagen[
                    max(0, y1 - margen_y):min(alto_imagen, y2 + margen_y),
                    max(0, x1 - margen_x):min(ancho_imagen, x2 + margen_x),
                ]
                if recorte.size == 0:
                    continue

                alto_recorte, ancho_recorte = recorte.shape[:2]
                factor = min(ancho_celda / ancho_recorte, (alto_celda - 6) / alto_recorte)
                recorte = cv2.resize(
                    recorte,
                    (max(1, int(ancho_recorte * factor)), max(1, int(alto_recorte * factor))),
                    interpolation=cv2.INTER_AREA,
                )
                alto_r, ancho_r = recorte.shape[:2]
                x0 = origen_x + 3 + indice * ancho_celda + (ancho_celda - ancho_r) // 2
                y0 = origen_y + (alto_celda - alto_r) // 2
                lienzo[y0:y0 + alto_r, x0:x0 + ancho_r] = recorte

            mal = par in PARES_AUTOSOMICOS and len(detecciones_par) != 2
            cv2.putText(
                lienzo,
                f"{par} ({len(detecciones_par)})",
                (origen_x + 6, origen_y + alto_celda + 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 200) if mal else (60, 60, 60),
                1,
                cv2.LINE_AA,
            )
            cv2.line(
                lienzo,
                (origen_x, origen_y),
                (origen_x, origen_y + alto_celda + pie - 4),
                (225, 225, 225),
                1,
            )

    return lienzo
