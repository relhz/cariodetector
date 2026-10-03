"""
Módulo para cargar y usar el modelo YOLO de detección de cromosomas.
Responsabilidad exclusiva: modelo de IA.
"""

from pathlib import Path
from ultralytics import YOLO
import numpy as np


# Nombres de las 24 clases en el orden que el modelo espera
# DEBE coincidir con el orden de clases del modelo entrenado
NOMBRES_CLASES = [
    "cromosoma 1", "cromosoma 2", "cromosoma 3", "cromosoma 4",
    "cromosoma 5", "cromosoma 6", "cromosoma 7", "cromosoma 8",
    "cromosoma 9", "cromosoma 10", "cromosoma 11", "cromosoma 12",
    "cromosoma 13", "cromosoma 14", "cromosoma 15", "cromosoma 16",
    "cromosoma 17", "cromosoma 18", "cromosoma 19", "cromosoma 20",
    "cromosoma 21", "cromosoma 22", "cromosoma X", "cromosoma Y"
]


class DetectorCromosomas:
    """
    Encapsula el modelo YOLO para detección de cromosomas.
    """

    def __init__(self, ruta_modelo=None):
        """
        Inicializa el detector.

        Args:
            ruta_modelo: Path al archivo .pt. Si es None, usa models/best_24_chromosomes.pt
        """
        if ruta_modelo is None:
            base_dir = Path(__file__).resolve().parent.parent
            ruta_modelo = base_dir / "models" / "best_24_chromosomes.pt"

        self.ruta_modelo = Path(ruta_modelo)
        self.modelo = None
        self._cargado = False

    def cargar_modelo(self):
        """
        Carga el modelo YOLO desde disco.
        Lanza excepción si el archivo no existe o hay error al cargar.
        """
        if not self.ruta_modelo.exists():
            raise FileNotFoundError(
                f"Modelo no encontrado: {self.ruta_modelo}. "
                f"Coloque best_24_chromosomes.pt en la carpeta models/."
            )

        try:
            self.modelo = YOLO(str(self.ruta_modelo))
            self._cargado = True
            print(f"Modelo cargado: {self.ruta_modelo.name}")
            print(f"Clases del modelo: {self.modelo.names}")
        except Exception as e:
            self._cargado = False
            raise Exception(f"Error cargando modelo: {e}")

    def esta_cargado(self):
        """Retorna True si el modelo está cargado y listo."""
        return self._cargado and self.modelo is not None

    def detectar(self, imagen, conf_threshold=0.25):
        """
        Ejecuta inferencia sobre una imagen.

        Args:
            imagen: numpy array (OpenCV BGR) o ruta a archivo de imagen
            conf_threshold: Umbral de confianza (0.0 a 1.0)

        Returns:
            Lista de diccionarios con detecciones:
            [
                {
                    "clase_id": int,
                    "nombre_clase": str,
                    "confianza": float,
                    "bbox": [x, y, w, h]  # formato xywh normalizado 0-1
                },
                ...
            ]
        """
        if not self.esta_cargado():
            self.cargar_modelo()

        try:
            # Ultralytics acepta numpy array o ruta
            resultados = self.modelo(imagen, conf=conf_threshold, verbose=False)

            detecciones = []

            for resultado in resultados:
                boxes = resultado.boxes
                if boxes is None:
                    continue

                # Obtener datos de las cajas
                xywhn = boxes.xywhn.cpu().numpy()  # normalizado
                confs = boxes.conf.cpu().numpy()
                cls_ids = boxes.cls.cpu().numpy().astype(int)

                for i in range(len(cls_ids)):
                    clase_id = cls_ids[i]
                    nombre_clase = self._obtener_nombre_clase(clase_id)

                    detecciones.append({
                        "clase_id": int(clase_id),
                        "nombre_clase": nombre_clase,
                        "confianza": float(confs[i]),
                        "bbox": xywhn[i].tolist()  # [x_center, y_center, w, h] normalizado
                    })

            return detecciones

        except Exception as e:
            raise Exception(f"Error durante inferencia: {e}")

    def _obtener_nombre_clase(self, clase_id):
        """
        Obtiene el nombre de la clase.
        Prioridad: nombres del modelo cargado > lista por defecto.
        """
        if self.modelo and hasattr(self.modelo, "names"):
            nombres_modelo = self.modelo.names
            if isinstance(nombres_modelo, dict) and clase_id in nombres_modelo:
                return nombres_modelo[clase_id]
            elif isinstance(nombres_modelo, list) and clase_id < len(nombres_modelo):
                return nombres_modelo[clase_id]

        # Fallback a lista por defecto
        if 0 <= clase_id < len(NOMBRES_CLASES):
            return NOMBRES_CLASES[clase_id]

        return f"clase_desconocida_{clase_id}"


# Función de conveniencia para uso simple
def crear_detector():
    """Crea e inicializa un detector listo para usar."""
    detector = DetectorCromosomas()
    detector.cargar_modelo()
    return detector


if __name__ == "__main__":
    # Prueba rápida
    try:
        detector = crear_detector()
        print("Detector listo")
        print(f"Clases: {NOMBRES_CLASES}")
    except Exception as e:
        print(f"Error: {e}")