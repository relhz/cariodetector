"""Servicio de carga y análisis de una imagen (sin dependencias de UI)."""

from pathlib import Path

import cv2

from .constantes import CONF_UMBRAL, IOU_UMBRAL
from .detecciones import preparar_detecciones, resumen_deteccion
from .dibujo import dibujar
from .modelo import DetectorCromosomas


def analizar(imagen, detector, conf=CONF_UMBRAL, iou=IOU_UMBRAL):
    """Analiza una imagen ya cargada con un detector concreto.

    Devuelve las detecciones en formato canónico, la imagen anotada y el
    resumen de revisión. Es el único punto de entrada que deberían usar las
    interfaces para analizar; el detector se recibe como parámetro para poder
    cachearlo o comparar distintos pesos.
    """
    detecciones = preparar_detecciones(detector.detectar(imagen, conf=conf, iou=iou))

    return {
        "detecciones": detecciones,
        "imagen_anotada": dibujar(imagen, detecciones),
        **resumen_deteccion(detecciones),
    }


class AnalizadorImagen:
    def __init__(self, detector=None):
        self.detector = detector or DetectorCromosomas()
        self.imagen_original = None
        self.imagen_anotada = None
        self.detecciones = []
        self.ruta_imagen = None

    def cargar_imagen(self, ruta_imagen):
        ruta = Path(ruta_imagen)
        if not ruta.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {ruta}")

        imagen = cv2.imread(str(ruta))
        if imagen is None:
            raise ValueError(f"No se pudo leer la imagen: {ruta}. Formato inválido o corrupto.")

        self.imagen_original = imagen.copy()
        self.ruta_imagen = ruta
        return self.imagen_original

    def analizar(self, conf_threshold=CONF_UMBRAL, iou=IOU_UMBRAL):
        if self.imagen_original is None:
            raise ValueError("No hay imagen cargada. Use cargar_imagen() primero.")

        resultado = analizar(self.imagen_original, self.detector, conf_threshold, iou)
        self.detecciones = resultado["detecciones"]
        self.imagen_anotada = resultado["imagen_anotada"]

        return {**resultado, "total": len(self.detecciones)}

    def redibujar_anotada(self, detecciones=None):
        if self.imagen_original is None:
            raise ValueError("No hay imagen cargada. Use cargar_imagen() primero.")

        if detecciones is not None:
            self.detecciones = detecciones

        self.imagen_anotada = dibujar(self.imagen_original, self.detecciones)
        return self.imagen_anotada

    def obtener_imagen_original(self):
        return self.imagen_original

    def obtener_imagen_analizada(self):
        return self.imagen_anotada
