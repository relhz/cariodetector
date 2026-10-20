from ultralytics import YOLO
import os

class DetectorCromosomas:
    def __init__(self, RUTA_PESOS="modelo/best.pt"):
        if not os.path.exists(RUTA_PESOS):
            raise FileNotFoundError("Modelo no encontrado. Verificá la ruta: " + RUTA_PESOS)
        self.modelo = YOLO(RUTA_PESOS)

    def detectar(self, imagen, conf=0.50, iou=0.40):
        resultados = self.modelo(imagen, conf=conf, iou=iou)
        detecciones = []
        for resultado in resultados:
            for caja in resultado.boxes:
                x1, y1, x2, y2 = caja.xyxy[0].cpu().numpy().astype(int)
                confianza = float(caja.conf[0])
                clase = resultado.names[int(caja.cls[0])]
                detecciones.append({"caja": (x1, y1, x2, y2), "clase": clase, "confianza": confianza})
        return detecciones