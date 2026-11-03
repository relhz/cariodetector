"""Gráficos de conteos y estado de los pares cromosómicos."""

import altair as alt
import numpy as np
import pandas as pd

from nucleo.constantes import (
    AZUL,
    CATEGORIAS_IMG,
    COLORES,
    COLORES_IMG,
    CONF_UMBRAL,
    DE_MAS,
    DE_MENOS,
    ETIQUETA_GRUPO,
    ETIQUETA_SEXUALES,
    GRUPOS,
    ORDEN_FILAS,
    PARES_AUTOSOMICOS,
    PARES_ORDEN,
)
from nucleo.detecciones import categoria_imagen, estado_par

from .tema import ESCALA_ESTADO, eje_entero


def cariograma(fila):
    """Grilla de pares agrupados A–G. fila: Serie con la cantidad de cada par."""
    celdas = []
    for grupo, pares in GRUPOS.items():
        for indice, par in enumerate(pares):
            celdas.append((ETIQUETA_GRUPO[grupo], indice, par))
    for indice, par in enumerate(["X", "Y"]):
        celdas.append((ETIQUETA_SEXUALES, indice, par))

    datos = pd.DataFrame([
        {
            "fila": grupo,
            "col": columna,
            "par": par,
            "cantidad": int(fila.get(par, 0)),
            "estado": estado_par(par, int(fila.get(par, 0))),
        }
        for grupo, columna, par in celdas
    ])

    base = alt.Chart(datos).encode(
        x=alt.X("col:O", axis=None, scale=alt.Scale(paddingInner=0.1)),
        y=alt.Y(
            "fila:N",
            sort=ORDEN_FILAS,
            title=None,
            scale=alt.Scale(paddingInner=0.1),
            axis=alt.Axis(labelFontSize=13, labelLimit=250, ticks=False, domain=False),
        ),
    )
    casilleros = base.mark_rect(cornerRadius=6).encode(
        color=alt.Color(
            "estado:N",
            scale=ESCALA_ESTADO,
            legend=alt.Legend(title="Estado", orient="bottom"),
        ),
        tooltip=[
            alt.Tooltip("par:N", title="Par"),
            alt.Tooltip("cantidad:Q", title="Copias detectadas"),
            alt.Tooltip("estado:N", title="Estado"),
        ],
    )
    nombre = base.mark_text(dy=-11, fontSize=12, color="white").encode(text="par:N")
    numero = base.mark_text(dy=9, fontSize=20, fontWeight="bold", color="white").encode(
        text="cantidad:Q"
    )
    return (casilleros + nombre + numero).properties(width="container", height=430)


def mapa_calor(matriz):
    """Imágenes (filas) × pares (columnas), coloreado por estado."""
    datos = matriz.reset_index().melt(
        id_vars=["imagen_id", "archivo"], var_name="par", value_name="cantidad"
    )
    datos["estado"] = [
        estado_par(par, cantidad) for par, cantidad in zip(datos["par"], datos["cantidad"])
    ]
    n_imagenes = datos["archivo"].nunique()

    base = alt.Chart(datos).encode(
        x=alt.X(
            "par:N",
            sort=PARES_ORDEN,
            title="Par cromosómico",
            axis=alt.Axis(labelAngle=0),
        ),
        y=alt.Y("archivo:N", title=None),
    )
    celdas = base.mark_rect().encode(
        color=alt.Color(
            "estado:N",
            scale=ESCALA_ESTADO,
            legend=alt.Legend(title="Estado", orient="bottom"),
        ),
        tooltip=[
            alt.Tooltip("archivo:N", title="Imagen"),
            alt.Tooltip("par:N", title="Par"),
            alt.Tooltip("cantidad:Q", title="Copias detectadas"),
            alt.Tooltip("estado:N", title="Estado"),
        ],
    )
    capas = celdas
    if n_imagenes <= 30:
        capas = celdas + base.mark_text(fontSize=11, color="white").encode(text="cantidad:Q")
    return capas.properties(width="container", height=max(160, 26 * n_imagenes + 60))


def img_alertas(matriz):
    """Cuántas imágenes salieron sin alertas / con pares de más / de menos."""
    categorias = matriz[PARES_AUTOSOMICOS].apply(categoria_imagen, axis=1)
    cantidades = [int((categorias == categoria).sum()) for categoria in CATEGORIAS_IMG]
    etiquetas = [
        f"{categoria}: {cantidad}"
        for categoria, cantidad in zip(CATEGORIAS_IMG, cantidades)
    ]
    datos = pd.DataFrame({"categoria": etiquetas, "imagenes": cantidades})

    return alt.Chart(datos).mark_arc(innerRadius=70, outerRadius=130).encode(
        theta=alt.Theta("imagenes:Q", stack=True),
        color=alt.Color(
            "categoria:N",
            scale=alt.Scale(domain=etiquetas, range=COLORES_IMG),
            legend=alt.Legend(title=None, orient="right", labelLimit=300),
        ),
        tooltip=[
            alt.Tooltip("categoria:N", title="Grupo"),
            alt.Tooltip("imagenes:Q", title="Imágenes"),
        ],
    ).properties(height=300)


def histograma_confianza(datos):
    """Detecciones por franja de confianza, con el umbral marcado."""
    bordes = np.round(np.arange(0, 1.0001, 0.05), 2)
    cuenta = (
        pd.cut(datos["confianza"], bins=bordes, include_lowest=True)
        .value_counts()
        .sort_index()
    )
    histograma = pd.DataFrame({
        "desde": bordes[:-1],
        "hasta": bordes[1:],
        "cantidad": cuenta.to_numpy(),
        "cero": 0,
    })

    barras = alt.Chart(histograma).mark_rect(
        color=AZUL, stroke="white", strokeWidth=1
    ).encode(
        x=alt.X(
            "desde:Q",
            title="Confianza del modelo (0 a 1)",
            scale=alt.Scale(domain=[0, 1]),
        ),
        x2="hasta:Q",
        y=alt.Y("cantidad:Q", title="Cromosomas detectados"),
        y2="cero:Q",
        tooltip=[
            alt.Tooltip("desde:Q", title="Desde"),
            alt.Tooltip("hasta:Q", title="Hasta"),
            alt.Tooltip("cantidad:Q", title="Detecciones"),
        ],
    )
    referencia = pd.DataFrame({
        "x": [CONF_UMBRAL],
        "texto": [f"Umbral usado ({CONF_UMBRAL})"],
    })
    linea = alt.Chart(referencia).mark_rule(
        color=COLORES[1], strokeDash=[6, 4], size=2
    ).encode(x="x:Q")
    rotulo = alt.Chart(referencia).mark_text(
        align="left", dx=6, fontSize=12, color=COLORES[1]
    ).encode(x="x:Q", y=alt.value(12), text="texto:N")
    return (barras + linea + rotulo).properties(width="container", height=300)


def total_por_imagen(matriz):
    """Cromosomas detectados en cada imagen, con la referencia de 46."""
    datos = matriz.sum(axis=1).rename("total").reset_index()
    minimo, maximo = int(min(datos["total"].min(), 46)), int(max(datos["total"].max(), 46))

    puntos = alt.Chart(datos).mark_circle(size=140, color=AZUL).encode(
        x=alt.X(
            "total:Q",
            scale=alt.Scale(domain=[minimo - 1, maximo + 1]),
            axis=eje_entero(minimo - 1, maximo + 1, "Cromosomas detectados"),
        ),
        y=alt.Y("archivo:N", title=None),
        tooltip=[
            alt.Tooltip("archivo:N", title="Imagen"),
            alt.Tooltip("total:Q", title="Detectados"),
        ],
    )
    referencia = pd.DataFrame({
        "x": [46],
        "texto": ["46: célula sin alteraciones numéricas"],
    })
    linea = alt.Chart(referencia).mark_rule(
        color=COLORES[3], strokeDash=[6, 4], size=2
    ).encode(x="x:Q")
    rotulo = alt.Chart(referencia).mark_text(
        align="left", dx=6, fontSize=12, color=COLORES[3]
    ).encode(x="x:Q", y=alt.value(12), text="texto:N")

    alto = max(160, 26 * len(datos) + 60)
    return (puntos + linea + rotulo).properties(width="container", height=alto)


def pares_que_fallan(matriz):
    """Ranking de pares con más imágenes fuera de lo esperado (de más / de menos)."""
    autosomicos = matriz[PARES_AUTOSOMICOS]
    tabla = pd.DataFrame({
        DE_MAS: (autosomicos >= 3).sum(),
        DE_MENOS: (autosomicos <= 1).sum(),
    })
    tabla["total"] = tabla.sum(axis=1)
    tabla = tabla[tabla["total"] > 0].sort_values("total", ascending=False).head(10)
    if tabla.empty:
        return None

    largo = (
        tabla.drop(columns="total")
        .rename_axis("par")
        .reset_index()
        .melt(id_vars="par", var_name="tipo", value_name="imagenes")
    )

    return alt.Chart(largo).mark_bar().encode(
        y=alt.Y("par:N", sort=list(tabla.index), title=None),
        x=alt.X(
            "imagenes:Q",
            axis=eje_entero(0, tabla["total"].max(), "Imágenes afectadas"),
        ),
        color=alt.Color(
            "tipo:N",
            scale=alt.Scale(domain=[DE_MAS, DE_MENOS], range=[COLORES[1], COLORES[2]]),
            legend=alt.Legend(title=None, orient="bottom"),
        ),
        tooltip=[
            alt.Tooltip("par:N", title="Par"),
            alt.Tooltip("tipo:N", title="Tipo"),
            alt.Tooltip("imagenes:Q", title="Imágenes"),
        ],
    ).properties(width="container", height=max(160, 30 * len(tabla) + 60))


def imagenes_por_dia(datos):
    """Cuántas imágenes se analizaron por fecha de muestra."""
    por_dia = datos.groupby(datos["fecha"].dt.date)["imagen_id"].nunique().reset_index()
    por_dia.columns = ["fecha", "imagenes"]
    por_dia["fecha"] = pd.to_datetime(por_dia["fecha"])

    return alt.Chart(por_dia).mark_bar(color=AZUL, size=10).encode(
        x=alt.X("fecha:T", title="Fecha de la muestra"),
        y=alt.Y("imagenes:Q", axis=eje_entero(0, por_dia["imagenes"].max(), "Imágenes")),
        tooltip=[
            alt.Tooltip("fecha:T", title="Fecha"),
            alt.Tooltip("imagenes:Q", title="Imágenes"),
        ],
    ).properties(width="container", height=260)
