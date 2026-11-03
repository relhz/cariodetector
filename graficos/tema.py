"""Tema y utilidades comunes de los gráficos Altair."""

import altair as alt

from nucleo.constantes import AZUL, COLORES, ESTADOS

ESCALA_ESTADO = alt.Scale(domain=ESTADOS, range=COLORES)


def configurar():
    alt.data_transformers.disable_max_rows()


def eje_entero(minimo, maximo, titulo):
    """Eje con marcas solo en números enteros (sin 0.5, 1.5...)."""
    minimo, maximo = int(minimo), int(maximo)
    paso = max(1, -(-(maximo - minimo) // 8))  # hasta 8 marcas
    return alt.Axis(
        title=titulo,
        values=list(range(minimo, maximo + 1, paso)),
        format="d",
    )
