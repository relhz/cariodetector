"""Servicio de carga y análisis de una imagen (sin dependencias de UI)."""

from pathlib import Path

import cv2

from .constantes import CONF_UMBRAL, IOU_UMBRAL
from .dibujo import dibujar
from .modelo import DetectorCromosomas


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

        self.detecciones = self.detector.detectar(
            self.imagen_original, conf=conf_threshold, iou=iou
        )
        self.imagen_anotada = dibujar(self.imagen_original, self.detecciones)

        return {
            "detecciones": self.detecciones,
            "imagen_anotada": self.imagen_anotada,
            "total": len(self.detecciones),
        }

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
