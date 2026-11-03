"""Gráficos del laboratorio de parámetros."""

import altair as alt
import pandas as pd

from nucleo.constantes import AZUL, COLORES


def curva_iou(tabla):
    """Cromosomas detectados según el IoU, con la referencia de 46."""
    lineas = alt.Chart(tabla).mark_line(point=True, color=AZUL).encode(
        x=alt.X("IoU:Q", scale=alt.Scale(domain=[0.25, 0.75])),
        y=alt.Y("Cromosomas detectados:Q", scale=alt.Scale(zero=False)),
        tooltip=["IoU", "Cromosomas detectados"],
    )
    referencia = alt.Chart(pd.DataFrame({"y": [46]})).mark_rule(
        color=COLORES[3], strokeDash=[6, 4]
    ).encode(y="y:Q")
    return (lineas + referencia).properties(width="container", height=240)
