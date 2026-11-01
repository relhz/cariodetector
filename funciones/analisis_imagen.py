from pathlib import Path
import cv2
import numpy as np
from funciones.modelo_cromosomas import DetectorCromosomas


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

    def analizar(self, conf_threshold=0.25):

        if self.imagen_original is None:
            raise ValueError("No hay imagen cargada. Use cargar_imagen() primero.")

        self.detecciones = self.detector.detectar(self.imagen_original, conf_threshold)
        self.imagen_anotada = self._dibujar_detecciones(self.imagen_original, self.detecciones)

        return {
            "detecciones": self.detecciones,
            "imagen_anotada": self.imagen_anotada,
            "total": len(self.detecciones)
        }

    def redibujar_anotada(self, detecciones=None):
 
        if self.imagen_original is None:
            raise ValueError("No hay imagen cargada. Use cargar_imagen() primero.")

        if detecciones is not None:
            self.detecciones = detecciones

        self.imagen_anotada = self._dibujar_detecciones(self.imagen_original, self.detecciones)
        return self.imagen_anotada

    def _dibujar_detecciones(self, imagen, detecciones):

        imagen_anotada = imagen.copy()
        alto, ancho = imagen.shape[:2]

        colores = self._generar_colores_clases()

        for det in detecciones:
            bbox = det["bbox"]  # [x_center, y_center, w, h] normalizado 0-1
            clase_id = det["clase_id"]
            nombre = det["nombre_clase"]
            conf = det["confianza"]

            # Convertir bbox normalizado a píxeles
            x_center = int(bbox[0] * ancho)
            y_center = int(bbox[1] * alto)
            w = int(bbox[2] * ancho)
            h = int(bbox[3] * alto)

            # Coordenadas esquinas
            x1 = max(0, x_center - w // 2)
            y1 = max(0, y_center - h // 2)
            x2 = min(ancho, x_center + w // 2)
            y2 = min(alto, y_center + h // 2)

            # Color para esta clase
            color = colores[clase_id % len(colores)]

            # Dibujar rectángulo
            cv2.rectangle(imagen_anotada, (x1, y1), (x2, y2), color, 2)

            # Etiqueta con nombre y confianza
            etiqueta = f"{nombre} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            # Fondo de la etiqueta
            cv2.rectangle(imagen_anotada, (x1, y1 - th - 4), (x1 + tw + 4, y1), color, -1)
            # Texto
            cv2.putText(imagen_anotada, etiqueta, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return imagen_anotada

    def _generar_colores_clases(self):
        colores = []
        for i in range(24):
            # Generar color en HSV y convertir a BGR para mejor distribución
            hue = int(180 * i / 24)
            color_hsv = np.uint8([[[hue, 255, 200]]]) # type: ignore
            color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0] # type: ignore
            colores.append(tuple(int(c) for c in color_bgr))
        return colores

    def obtener_imagen_original(self):
        return self.imagen_original
