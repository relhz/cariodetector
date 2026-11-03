"""Gráficos del dashboard, sin dependencias de Streamlit."""

from .cariotipo import (
    cariograma,
    histograma_confianza,
    imagenes_por_dia,
    img_alertas,
    mapa_calor,
    pares_que_fallan,
    total_por_imagen,
)
from .laboratorio import curva_iou
from .modelo import comparar_map, comparar_perdida, metricas_por_epoca, perdida_por_epoca
from .revision import confusiones

__all__ = [
    "cariograma",
    "histograma_confianza",
    "imagenes_por_dia",
    "img_alertas",
    "mapa_calor",
    "pares_que_fallan",
    "total_por_imagen",
    "curva_iou",
    "comparar_map",
    "comparar_perdida",
    "metricas_por_epoca",
    "perdida_por_epoca",
    "confusiones",
]
