"""Detector de cromosomas compartido por la aplicación y el dashboard."""

from pathlib import Path

from .constantes import CONF_UMBRAL, IOU_UMBRAL, RUTA_PESOS


class DetectorCromosomas:
    """Envoltorio único de YOLO.

    La salida de `detectar` es el formato canónico del proyecto: cajas en
    píxeles (x1, y1, x2, y2), nombre de clase y confianza.
    """

    def __init__(self, ruta_modelo=None):
        self.ruta_modelo = Path(ruta_modelo) if ruta_modelo else RUTA_PESOS
        self.modelo = None
        self._cargado = False

    def cargar_modelo(self):
        if self._cargado and self.modelo is not None:
            return self.modelo

        if not self.ruta_modelo.exists():
            raise FileNotFoundError(
                f"Modelo no encontrado: {self.ruta_modelo}. "
                "Coloque best_24_chromosomes.pt en la carpeta models/."
            )

        try:
            from ultralytics import YOLO

            self.modelo = YOLO(str(self.ruta_modelo))
            self._cargado = True
            return self.modelo
        except Exception as e:
            self._cargado = False
            raise Exception(f"Error cargando modelo: {e}") from e

    def esta_cargado(self):
        return self._cargado and self.modelo is not None

    def detectar(self, imagen, conf=CONF_UMBRAL, iou=IOU_UMBRAL, verbose=False):
        if not self.esta_cargado():
            self.cargar_modelo()

        try:
            resultados = self.modelo(imagen, conf=conf, iou=iou, verbose=verbose)

            detecciones = []
            for resultado in resultados:
                boxes = resultado.boxes
                if boxes is None:
                    continue

                xyxy = boxes.xyxy.cpu().numpy().astype(int)
                confianzas = boxes.conf.cpu().numpy()
                clases = boxes.cls.cpu().numpy().astype(int)

                for (x1, y1, x2, y2), confianza, clase_id in zip(xyxy, confianzas, clases):
                    detecciones.append({
                        "caja": (int(x1), int(y1), int(x2), int(y2)),
                        "clase": self._obtener_nombre_clase(int(clase_id)),
                        "confianza": float(confianza),
                    })

            return detecciones
        except Exception as e:
            raise Exception(f"Error durante inferencia: {e}") from e

    def _obtener_nombre_clase(self, clase_id):
        if self.modelo and hasattr(self.modelo, "names"):
            nombres = self.modelo.names
            if isinstance(nombres, dict) and clase_id in nombres:
                return nombres[clase_id]
            if isinstance(nombres, (list, tuple)) and clase_id < len(nombres):
                return nombres[clase_id]
        return f"clase_desconocida_{clase_id}"
