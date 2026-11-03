"""Curvas de entrenamiento y comparación de modelos."""

import altair as alt
import pandas as pd

from nucleo.constantes import AZUL, COLORES
from nucleo.modelo_info import COLUMNAS_METRICAS, MODELOS_INFO, mejor_epoca

NOMBRES_METRICAS = list(COLUMNAS_METRICAS.values())


def metricas_por_epoca(resultados):
    mejor = mejor_epoca(resultados)
    metricas = resultados[
        ["epoch", "metrics/precision(B)", "metrics/recall(B)",
         "metrics/mAP50(B)", "metrics/mAP50-95(B)"]
    ].rename(columns=COLUMNAS_METRICAS)
    largo = metricas.melt("epoch", var_name="Métrica", value_name="Valor")

    curva = alt.Chart(largo).mark_line().encode(
        x=alt.X("epoch:Q", title="Época"),
        y=alt.Y("Valor:Q", title="Valor", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color(
            "Métrica:N",
            scale=alt.Scale(
                domain=NOMBRES_METRICAS,
                range=[AZUL, "#8E24AA", "#26A69A", "#4D4D4D"],
            ),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        tooltip=["epoch", "Métrica", alt.Tooltip("Valor:Q", format=".3f")],
    )
    marca = alt.Chart(pd.DataFrame({"x": [int(mejor["epoch"])]})).mark_rule(
        color=COLORES[3], strokeDash=[6, 4]
    ).encode(x="x:Q")
    return (curva + marca).properties(width="container", height=280)


def perdida_por_epoca(resultados):
    perdida = resultados[["epoch", "train/box_loss", "val/box_loss"]].rename(
        columns={"train/box_loss": "Entrenamiento", "val/box_loss": "Validación"}
    ).melt("epoch", var_name="Conjunto", value_name="Pérdida")

    return alt.Chart(perdida).mark_line().encode(
        x=alt.X("epoch:Q", title="Época"),
        y=alt.Y("Pérdida:Q", scale=alt.Scale(zero=False)),
        color=alt.Color(
            "Conjunto:N",
            scale=alt.Scale(
                domain=["Entrenamiento", "Validación"], range=[AZUL, "#4D4D4D"]
            ),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        tooltip=["epoch", "Conjunto", alt.Tooltip("Pérdida:Q", format=".3f")],
    ).properties(width="container", height=280)


def _dominio_colores():
    dominio = list(MODELOS_INFO)
    colores = [MODELOS_INFO[modelo]["color"] for modelo in dominio]
    return dominio, colores


def comparar_map(larga):
    dominio, colores = _dominio_colores()
    return alt.Chart(larga).mark_line().encode(
        x=alt.X("epoch:Q", title="Época"),
        y=alt.Y(
            "metrics/mAP50-95(B):Q",
            title="mAP@50-95",
            scale=alt.Scale(zero=False),
        ),
        color=alt.Color(
            "Modelo:N",
            scale=alt.Scale(domain=dominio, range=colores),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        tooltip=["Modelo", "epoch", alt.Tooltip("metrics/mAP50-95(B):Q", format=".3f")],
    ).properties(width="container", height=280)


def comparar_perdida(larga):
    dominio, colores = _dominio_colores()
    return alt.Chart(larga).mark_line().encode(
        x=alt.X("epoch:Q", title="Época"),
        y=alt.Y("val/box_loss:Q", title="Pérdida de cajas", scale=alt.Scale(zero=False)),
        color=alt.Color(
            "Modelo:N",
            scale=alt.Scale(domain=dominio, range=colores),
            legend=alt.Legend(orient="bottom", title=None),
        ),
        tooltip=["Modelo", "epoch", alt.Tooltip("val/box_loss:Q", format=".3f")],
    ).properties(width="container", height=280)
