"""Preparación y guardado de un análisis, compartido por ambas interfaces."""

from datetime import datetime
from pathlib import Path

import cv2

from .constantes import CARPETA_IMAGENES
from .db import guardar_analisis
from .detecciones import resultado_revision, resumen_deteccion


def guardar_resultado(
    nombre_imagen,
    detecciones,
    descartadas=(),
    *,
    imagen=None,
    imagen_anotada=None,
    bytes_imagen=None,
    ruta_imagen=None,
    guardar_archivos=False,
    revisado=False,
    observacion=None,
):
    """Arma y persiste un análisis completo.

    Concentra lo que antes hacía cada interfaz por su cuenta: mezclar
    detecciones activas y descartadas, calcular dimensiones, copiar las
    imágenes y decidir si se registra el resultado de la revisión.

    Devuelve `(id_estudio, rutas)`, donde `rutas` tiene las claves
    `original` y `resultado` (o `None` si no se guardaron archivos).
    """
    activas = [{**det, "descartada": False} for det in detecciones]
    descartes = [
        {**det, "clase_final": None, "descartada": True}
        for det in descartadas
    ]
    todas = activas + descartes

    ancho = alto = None
    if imagen is not None:
        alto, ancho = imagen.shape[:2]

    rutas = {"original": None, "resultado": None}
    if guardar_archivos:
        CARPETA_IMAGENES.mkdir(parents=True, exist_ok=True)
        marca = f"{datetime.now():%Y%m%d_%H%M%S}"
        nombre = Path(nombre_imagen)

        if bytes_imagen is not None:
            ruta_original = CARPETA_IMAGENES / f"{marca}_{nombre.name}"
            ruta_original.write_bytes(bytes_imagen)
            rutas["original"] = ruta_original

        if imagen_anotada is not None:
            ruta_resultado = CARPETA_IMAGENES / f"{marca}_resultado_{nombre.stem}.png"
            cv2.imwrite(str(ruta_resultado), imagen_anotada)
            rutas["resultado"] = ruta_resultado

    resultado = None
    if revisado:
        conteo = resumen_deteccion(activas)["conteo"]
        resultado = resultado_revision(conteo, observacion)

    ruta_original = rutas["original"] or ruta_imagen
    id_estudio = guardar_analisis(
        nombre_imagen,
        todas,
        ancho,
        alto,
        str(ruta_original) if ruta_original else None,
        observacion,
        imagen_resultado=(
            str(rutas["resultado"]) if rutas["resultado"] is not None else None
        ),
        resultado=resultado,
    )

    return id_estudio, rutas
