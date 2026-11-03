"""Fichas y registros de entrenamiento de los modelos disponibles."""

import pandas as pd

from .constantes import RUTA_MODELO_INFO

INFO_MODELO = {
    "Modelo base": "YOLOv8l (preentrenado en COCO)",
    "Tarea": "Detección de objetos, 24 clases (A1…G22, X, Y)",
    "Épocas": "40",
    "Tamaño de imagen": "640 px",
    "Batch": "16",
    "Optimizador": "AdamW",
    "Fecha de entrenamiento": "30 de octubre de 2026",
    "Librería": "Ultralytics 8.4.193",
}

INFO_V8S = {
    "Modelo base": "YOLOv8s (preentrenado en COCO)",
    "Tarea": "Detección de objetos, 24 clases (A1…G22, X, Y)",
    "Épocas": "60",
    "Tamaño de imagen": "640 px",
    "Batch": "16",
    "Optimizador": "AdamW",
    "Fecha de entrenamiento": "3 de octubre de 2026",
    "Librería": "Ultralytics 8.4.172",
}

# Métricas finales en validación, guardadas dentro de los pesos (train_metrics).
METRICAS_FINALES = {
    "Precisión": 0.99088,
    "Recall": 0.98243,
    "mAP@50": 0.99355,
    "mAP@50-95": 0.86743,
}

MODELOS_INFO = {
    "YOLOv8l (actual)": {"info": INFO_MODELO, "csv": "results_yolov8l.csv", "color": "#1565C0"},
    "YOLOv8s (anterior)": {"info": INFO_V8S, "csv": "results_yolov8s.csv", "color": "#EF6C00"},
}

COLUMNAS_METRICAS = {
    "metrics/precision(B)": "Precisión",
    "metrics/recall(B)": "Recall",
    "metrics/mAP50(B)": "mAP@50",
    "metrics/mAP50-95(B)": "mAP@50-95",
}


def leer_results(nombre_csv):
    ruta = RUTA_MODELO_INFO / nombre_csv
    if not ruta.exists():
        return None
    resultados = pd.read_csv(ruta)
    resultados.columns = [columna.strip() for columna in resultados.columns]
    return resultados


def mejor_epoca(resultados):
    return resultados.loc[resultados["metrics/mAP50-95(B)"].idxmax()]
