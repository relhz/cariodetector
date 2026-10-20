import streamlit as st
import cv2
import numpy as np
import pandas as pd
import altair as alt
from collections import Counter
from datetime import datetime
from pathlib import Path
from modelo import DetectorCromosomas
from db import cargar_datos, guardar_analisis, nombre_par, PARES_AUTOSOMICOS, PARES_ORDEN

RUTA_PESOS = "models/best_24_chromosomes.pt"
CONF_UMBRAL = 0.35   # confianza mínima para aceptar una detección
IOU_UMBRAL = 0.40    # solapamiento máximo entre cajas (evita duplicados)
# Carpeta (en la raíz del repo) donde se copian las imágenes guardadas desde el dashboard
CARPETA_IMAGENES = Path(__file__).resolve().parent.parent / "assets" / "imagenes_analizadas"

alt.data_transformers.disable_max_rows()

# ---------- Colores: el mismo significado en todo el dashboard ----------
NORMAL = "Normal (2 copias)"
DE_MAS = "De más (3 o más)"
DE_MENOS = "De menos (0 o 1)"
SEXUAL = "X / Y (según sexo)"
ESTADOS = [NORMAL, DE_MAS, DE_MENOS, SEXUAL]
COLORES = ["#2E7D32", "#C62828", "#D97706", "#78909C"]
ESCALA_ESTADO = alt.Scale(domain=ESTADOS, range=COLORES)
AZUL = "#4C78A8"


def estado_par(par, n):
    """Estado de un par según cuántas copias se detectaron."""
    if par in ("X", "Y"):
        return SEXUAL
    if n == 2:
        return NORMAL
    return DE_MAS if n >= 3 else DE_MENOS


def _grupos():
    grupos = {}
    for p in PARES_AUTOSOMICOS:
        grupos.setdefault(p[0], []).append(p)
    etiquetas = {}
    for g, pares in grupos.items():
        nums = [int(x[1:]) for x in pares]
        etiquetas[g] = f"Grupo {g} · pares {min(nums)}–{max(nums)}"
    return grupos, etiquetas


GRUPOS, ETIQUETA_GRUPO = _grupos()
ETIQUETA_SEXUALES = "Sexuales · X, Y"
ORDEN_FILAS = [ETIQUETA_GRUPO[g] for g in GRUPOS] + [ETIQUETA_SEXUALES]


def eje_entero(minimo, maximo, titulo):
    """Eje con marcas solo en números enteros (sin 0.5, 1.5...)."""
    minimo, maximo = int(minimo), int(maximo)
    paso = max(1, -(-(maximo - minimo) // 8))   # como mucho ~8 marcas
    return alt.Axis(title=titulo, values=list(range(minimo, maximo + 1, paso)), format="d")


def matriz_conteos(d):
    """Filas = imágenes, columnas = pares, valores = cantidad detectada."""
    m = d.pivot_table(index=["imagen_id", "archivo"], columns="numero_par",
                      values="confianza", aggfunc="count", fill_value=0)
    return m.reindex(columns=PARES_ORDEN, fill_value=0)


# ---------- Gráficos ----------
def cariograma(fila):
    """Grilla de pares agrupados A–G. fila: Serie con la cantidad de cada par."""
    celdas = []
    for g, pares in GRUPOS.items():
        for i, p in enumerate(pares):
            celdas.append((ETIQUETA_GRUPO[g], i, p))
    for i, p in enumerate(["X", "Y"]):
        celdas.append((ETIQUETA_SEXUALES, i, p))
    d = pd.DataFrame([{
        "fila": f, "col": c, "par": p,
        "cantidad": int(fila.get(p, 0)),
        "estado": estado_par(p, int(fila.get(p, 0))),
    } for f, c, p in celdas])

    base = alt.Chart(d).encode(
        x=alt.X("col:O", axis=None, scale=alt.Scale(paddingInner=0.1)),
        y=alt.Y("fila:N", sort=ORDEN_FILAS, title=None,
                scale=alt.Scale(paddingInner=0.1),
                axis=alt.Axis(labelFontSize=13, labelLimit=250, ticks=False, domain=False)),
    )
    casilleros = base.mark_rect(cornerRadius=6).encode(
        color=alt.Color("estado:N", scale=ESCALA_ESTADO,
                        legend=alt.Legend(title="Estado", orient="bottom")),
        tooltip=[alt.Tooltip("par:N", title="Par"),
                 alt.Tooltip("cantidad:Q", title="Copias detectadas"),
                 alt.Tooltip("estado:N", title="Estado")],
    )
    nombre = base.mark_text(dy=-11, fontSize=12, color="white").encode(text="par:N")
    numero = base.mark_text(dy=9, fontSize=20, fontWeight="bold",
                            color="white").encode(text="cantidad:Q")
    return (casilleros + nombre + numero).properties(width="container", height=430)


def mapa_calor(m):
    """Imágenes (filas) × pares (columnas), coloreado por estado."""
    d = m.reset_index().melt(id_vars=["imagen_id", "archivo"],
                             var_name="par", value_name="cantidad")
    d["estado"] = [estado_par(p, n) for p, n in zip(d["par"], d["cantidad"])]
    n_img = d["archivo"].nunique()

    base = alt.Chart(d).encode(
        x=alt.X("par:N", sort=PARES_ORDEN, title="Par cromosómico",
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y("archivo:N", title=None),
    )
    celdas = base.mark_rect().encode(
        color=alt.Color("estado:N", scale=ESCALA_ESTADO,
                        legend=alt.Legend(title="Estado", orient="bottom")),
        tooltip=[alt.Tooltip("archivo:N", title="Imagen"),
                 alt.Tooltip("par:N", title="Par"),
                 alt.Tooltip("cantidad:Q", title="Copias detectadas"),
                 alt.Tooltip("estado:N", title="Estado")],
    )
    capas = celdas
    if n_img <= 30:
        capas = celdas + base.mark_text(fontSize=11, color="white").encode(text="cantidad:Q")
    return capas.properties(width="container", height=max(160, 26 * n_img + 60))


CAT_SIN = "Sin alertas"
CAT_MAS = "Algún par de más"
CAT_MENOS = "Algún par de menos"
CAT_AMBAS = "Pares de más y de menos"
CATEGORIAS_IMG = [CAT_SIN, CAT_MAS, CAT_MENOS, CAT_AMBAS]
COLORES_IMG = [COLORES[0], COLORES[1], COLORES[2], "#8E24AA"]


def _categoria_imagen(fila):
    de_mas = bool((fila >= 3).any())
    de_menos = bool((fila <= 1).any())
    if de_mas and de_menos:
        return CAT_AMBAS
    if de_mas:
        return CAT_MAS
    if de_menos:
        return CAT_MENOS
    return CAT_SIN


def dona_alertas(m):
    """Cuántas imágenes salieron sin alertas / con pares de más / de menos."""
    cats = m[PARES_AUTOSOMICOS].apply(_categoria_imagen, axis=1)
    cantidades = [int((cats == c).sum()) for c in CATEGORIAS_IMG]
    # la cantidad va en la etiqueta para que se lea sin pasar el mouse
    etiquetas = [f"{c}: {n}" for c, n in zip(CATEGORIAS_IMG, cantidades)]
    d = pd.DataFrame({"categoria": etiquetas, "imagenes": cantidades})
    return alt.Chart(d).mark_arc(innerRadius=70, outerRadius=130).encode(
        theta=alt.Theta("imagenes:Q", stack=True),
        color=alt.Color("categoria:N",
                        scale=alt.Scale(domain=etiquetas, range=COLORES_IMG),
                        legend=alt.Legend(title=None, orient="right", labelLimit=300)),
        tooltip=[alt.Tooltip("categoria:N", title="Grupo"),
                 alt.Tooltip("imagenes:Q", title="Imágenes")],
    ).properties(height=300)


def histograma_confianza(d):
    """Cuántas detecciones hay en cada franja de confianza, con el umbral marcado."""
    bordes = np.round(np.arange(0, 1.0001, 0.05), 2)
    cuenta = pd.cut(d["confianza"], bins=bordes, include_lowest=True).value_counts().sort_index()
    h = pd.DataFrame({"desde": bordes[:-1], "hasta": bordes[1:],
                      "cantidad": cuenta.to_numpy(), "cero": 0})
    barras = alt.Chart(h).mark_rect(color=AZUL, stroke="white", strokeWidth=1).encode(
        x=alt.X("desde:Q", title="Confianza del modelo (0 a 1)",
                scale=alt.Scale(domain=[0, 1])),
        x2="hasta:Q",
        y=alt.Y("cantidad:Q", title="Cromosomas detectados"),
        y2="cero:Q",
        tooltip=[alt.Tooltip("desde:Q", title="Desde"),
                 alt.Tooltip("hasta:Q", title="Hasta"),
                 alt.Tooltip("cantidad:Q", title="Detecciones")],
    )
    ref = pd.DataFrame({"x": [CONF_UMBRAL], "texto": [f"Umbral usado ({CONF_UMBRAL})"]})
    linea = alt.Chart(ref).mark_rule(color=COLORES[1], strokeDash=[6, 4], size=2).encode(x="x:Q")
    rotulo = alt.Chart(ref).mark_text(align="left", dx=6, fontSize=12, color=COLORES[1]).encode(
        x="x:Q", y=alt.value(12), text="texto:N")
    return (barras + linea + rotulo).properties(width="container", height=300)


def total_por_imagen(m):
    """Cromosomas detectados en cada imagen, con la referencia de 46."""
    d = m.sum(axis=1).rename("total").reset_index()
    lo, hi = int(min(d["total"].min(), 46)), int(max(d["total"].max(), 46))
    puntos = alt.Chart(d).mark_circle(size=140, color=AZUL).encode(
        x=alt.X("total:Q", scale=alt.Scale(domain=[lo - 1, hi + 1]),
                axis=eje_entero(lo - 1, hi + 1, "Cromosomas detectados")),
        y=alt.Y("archivo:N", title=None),
        tooltip=[alt.Tooltip("archivo:N", title="Imagen"),
                 alt.Tooltip("total:Q", title="Detectados")],
    )
    ref = pd.DataFrame({"x": [46], "texto": ["46: célula sin alteraciones numéricas"]})
    linea = alt.Chart(ref).mark_rule(color=COLORES[3], strokeDash=[6, 4], size=2).encode(x="x:Q")
    rotulo = alt.Chart(ref).mark_text(align="left", dx=6, fontSize=12, color=COLORES[3]).encode(
        x="x:Q", y=alt.value(12), text="texto:N")
    alto = max(160, 26 * len(d) + 60)
    return (puntos + linea + rotulo).properties(width="container", height=alto)


def pares_que_fallan(m):
    """Ranking de pares con más imágenes fuera de lo esperado (de más / de menos)."""
    a = m[PARES_AUTOSOMICOS]
    t = pd.DataFrame({DE_MAS: (a >= 3).sum(), DE_MENOS: (a <= 1).sum()})
    t["total"] = t.sum(axis=1)
    t = t[t["total"] > 0].sort_values("total", ascending=False).head(10)
    if t.empty:
        return None
    largo = t.drop(columns="total").rename_axis("par").reset_index().melt(
        id_vars="par", var_name="tipo", value_name="imagenes")
    return alt.Chart(largo).mark_bar().encode(
        y=alt.Y("par:N", sort=list(t.index), title=None),
        x=alt.X("imagenes:Q", axis=eje_entero(0, t["total"].max(), "Imágenes afectadas")),
        color=alt.Color("tipo:N",
                        scale=alt.Scale(domain=[DE_MAS, DE_MENOS], range=[COLORES[1], COLORES[2]]),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("par:N", title="Par"), alt.Tooltip("tipo:N", title="Tipo"),
                 alt.Tooltip("imagenes:Q", title="Imágenes")],
    ).properties(width="container", height=max(160, 30 * len(t) + 60))


def imagenes_por_dia(d):
    """Cuántas imágenes se analizaron por fecha de muestra."""
    x = d.groupby(d["fecha"].dt.date)["imagen_id"].nunique().reset_index()
    x.columns = ["fecha", "imagenes"]
    x["fecha"] = pd.to_datetime(x["fecha"])
    # barras (no línea): entre un día con datos y otro no hay valores intermedios
    return alt.Chart(x).mark_bar(color=AZUL, size=10).encode(
        x=alt.X("fecha:T", title="Fecha de la muestra"),
        y=alt.Y("imagenes:Q", axis=eje_entero(0, x["imagenes"].max(), "Imágenes")),
        tooltip=[alt.Tooltip("fecha:T", title="Fecha"),
                 alt.Tooltip("imagenes:Q", title="Imágenes")],
    ).properties(width="container", height=260)


# ===== FIN FUNCIONES DE GRÁFICOS =====

st.set_page_config(page_title="CarioDetector", layout="wide")
st.title("🧬 CarioDetector")

if "historial_pruebas" not in st.session_state:
    st.session_state.historial_pruebas = []


@st.cache_resource
def cargar_modelo():
    try:
        return DetectorCromosomas(RUTA_PESOS)
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()


@st.cache_data(ttl=60)
def datos_cacheados():
    return cargar_datos()


modelo = cargar_modelo()
df, origen, aviso = datos_cacheados()


def mostrar_origen():
    if aviso:
        st.warning(aviso)
    if origen == "DEMO":
        st.error("DATOS DE DEMO: son inventados, solo para probar el diseño. "
                 "No son resultados reales.")
    elif origen == "CSV":
        st.info("Datos leídos de un CSV exportado de la base.")
    else:
        st.success("Datos en vivo desde MySQL.")


def explicar(que, como):
    st.caption(f"**Qué muestra:** {que}  \n**Cómo leerlo:** {como}")


# ---------- Filtros (barra lateral) ----------
df_f = df
with st.sidebar:
    st.header("Filtros")
    st.caption("Se aplican a las pestañas Dashboard y Gráficos.")
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.rerun()
    if not df.empty:
        fmin, fmax = df["fecha"].min().date(), df["fecha"].max().date()
        rango = st.date_input("Fecha de la muestra", value=(fmin, fmax),
                              min_value=fmin, max_value=fmax)
        personas = []
        if df["persona_id"].notna().any():   # la base real no tiene personas
            personas = st.multiselect("Persona (id)",
                                      sorted(df["persona_id"].dropna().unique().tolist()))
        archivos = st.multiselect("Imagen", sorted(df["archivo"].unique().tolist()))
        if len(rango) == 2:
            df_f = df_f[(df_f["fecha"].dt.date >= rango[0]) &
                        (df_f["fecha"].dt.date <= rango[1])]
        if personas:
            df_f = df_f[df_f["persona_id"].isin(personas)]
        if archivos:
            df_f = df_f[df_f["archivo"].isin(archivos)]

m = matriz_conteos(df_f) if not df_f.empty else None

tab1, tab2, tab3, tab4 = st.tabs(
    ["Subir y detectar", "Dashboard", "Historial de sesión", "Gráficos"])

# ---------- TAB 1: subir y detectar ----------
def mostrar_resultado(imagen, u):
    """Muestra el resultado guardado en session_state (sobrevive a los reruns)."""
    detecciones = u["detecciones"]
    st.write(f"Se detectaron {len(detecciones)} cromosomas")

    imagen_dibujada = imagen.copy()
    for d in detecciones:
        x1, y1, x2, y2 = d["caja"]
        cv2.rectangle(imagen_dibujada, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(imagen_dibujada, d["clase"], (x1, max(20, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    st.image(imagen_dibujada, channels="BGR", caption="Detecciones")

    st.subheader("Listado de detecciones")
    st.dataframe([
        {"Clase": d["clase"], "Confianza": f"{d['confianza']:.2f}",
         "x1": d["caja"][0], "y1": d["caja"][1],
         "x2": d["caja"][2], "y2": d["caja"][3]}
        for d in detecciones
    ])

    conteo = Counter(nombre_par(d["clase"]) for d in detecciones)
    st.subheader("Conteo por par")
    st.dataframe([{"Par": c, "Cantidad detectada": n} for c, n in sorted(conteo.items())])

    # Un par con 0 detecciones también cuenta como alerta
    alertas = [f"{p} ({conteo.get(p, 0)})" for p in PARES_AUTOSOMICOS
               if conteo.get(p, 0) != 2]
    if alertas:
        st.warning("⚠️ Pares con cantidad inesperada: " + ", ".join(alertas))
    else:
        st.success("✅ Todos los pares autosómicos tienen 2 copias")

    st.subheader("Guardar")
    if u.get("guardado_id"):
        st.success(f"Guardado en la base de datos (análisis {u['guardado_id']}). "
                   "Ya aparece en las pestañas Dashboard y Gráficos.")
    elif st.button("Guardar en la base de datos"):
        try:
            alto, ancho = imagen.shape[:2]
            ruta = None
            if u.get("bytes"):
                CARPETA_IMAGENES.mkdir(parents=True, exist_ok=True)
                ruta = CARPETA_IMAGENES / f"{datetime.now():%Y%m%d_%H%M%S}_{u['archivo']}"
                ruta.write_bytes(u["bytes"])
            u["guardado_id"] = guardar_analisis(u["archivo"], detecciones, ancho, alto,
                                                str(ruta) if ruta else None)
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar en MySQL: {e}")
    return alertas


with tab1:
    archivo = st.file_uploader("Subí una imagen de cariotipo", type=["jpg", "jpeg", "png"])
    if archivo is not None:
        bytes_imagen = np.frombuffer(archivo.read(), np.uint8)
        imagen = cv2.imdecode(bytes_imagen, cv2.IMREAD_COLOR)
        st.image(imagen, channels="BGR", caption="Imagen cargada")

        if st.button("Detectar cromosomas"):
            detecciones = modelo.detectar(imagen, conf=CONF_UMBRAL, iou=IOU_UMBRAL)
            u = {"archivo": archivo.name, "detecciones": detecciones,
                 "guardado_id": None, "bytes": bytes_imagen.tobytes()}
            st.session_state.ultimo_resultado = u
            conteo = Counter(nombre_par(d["clase"]) for d in detecciones)
            alertas = [f"{p} ({conteo.get(p, 0)})" for p in PARES_AUTOSOMICOS
                       if conteo.get(p, 0) != 2]
            st.session_state.historial_pruebas.append({
                "Imagen": archivo.name,
                "Total detectado": len(detecciones),
                "Pares con cantidad inesperada": ", ".join(alertas) if alertas else "Ninguno",
            })

        u = st.session_state.get("ultimo_resultado")
        if u and u["archivo"] == archivo.name:
            mostrar_resultado(imagen, u)

# ---------- TAB 2: dashboard ----------
with tab2:
    mostrar_origen()
    if df_f.empty:
        st.info("No hay datos para los filtros elegidos.")
    else:
        alerta_img = (m[PARES_AUTOSOMICOS] != 2).any(axis=1)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Imágenes analizadas", df_f["imagen_id"].nunique())
        k2.metric("Cromosomas detectados", len(df_f))
        k3.metric("Confianza promedio", f"{df_f['confianza'].mean():.1%}")
        k4.metric("Imágenes con alertas", int(alerta_img.sum()))

        st.subheader("Resumen por imagen")
        resumen = pd.DataFrame({
            "Total detectado": m.sum(axis=1),
            "Pares con cantidad inesperada": m[PARES_AUTOSOMICOS].apply(
                lambda fila: ", ".join(fila[fila != 2].index) or "Ninguno", axis=1),
        }).reset_index()
        st.dataframe(resumen)

        st.subheader("Cantidad por par en cada imagen")
        st.caption("Lo esperado es 2 en cada par autosómico. "
                   "🟥 de más (3 o más) · 🟧 de menos (0 o 1) · sin color = 2 copias.")

        def resaltar(v):
            if v >= 3:
                return f"background-color: {COLORES[1]}; color: white"
            if v <= 1:
                return f"background-color: {COLORES[2]}; color: white"
            return ""

        st.dataframe(m.reset_index().style.map(resaltar, subset=PARES_AUTOSOMICOS))

        with st.expander("Detalle de detecciones"):
            detalle = df_f[["archivo", "fecha", "numero_par", "confianza",
                            "x", "y", "ancho", "alto"]].copy()
            detalle["fecha"] = detalle["fecha"].dt.date
            st.dataframe(detalle)
            st.download_button("Descargar detalle (CSV)",
                               detalle.to_csv(index=False).encode("utf-8"),
                               "detecciones.csv", "text/csv")

# ---------- TAB 3: historial de la sesión ----------
with tab3:
    st.subheader("Pruebas hechas en esta sesión")
    if st.session_state.historial_pruebas:
        st.dataframe(st.session_state.historial_pruebas)
    else:
        st.info("Todavía no probaste ninguna imagen en esta sesión")

# ---------- TAB 4: gráficos ----------
with tab4:
    mostrar_origen()
    st.caption("Herramienta de apoyo para el análisis de cariotipos. "
               "Toda alerta debe ser validada por un profesional. "
               "Solo se evalúan alteraciones numéricas, no estructurales.")
    st.markdown(
        "**Colores:** 🟩 **2 copias** (normal) · "
        "🟥 **de más** (3 o más: posible trisomía) · "
        "🟧 **de menos** (0 o 1: posible monosomía) · "
        "⬜ **X / Y**: se interpretan según el sexo")

    with st.expander("Glosario y cómo leer estos gráficos"):
        st.markdown(f"""
- **Nombre del par (A1 … G22, X, Y):** el modelo nombra cada cromosoma con la letra de su grupo y el
  número de par. A1 es el par 1 (grupo A) y G22 es el par 22 (grupo G).
- **Grupos A–G:** clasificación estándar por tamaño y posición del centrómero. Va del grupo A
  (pares 1–3, los más grandes) al grupo G (pares 21–22, los más chicos). X e Y se muestran aparte.
- **Copias detectadas:** cuántos cromosomas asignó el modelo a ese par en la imagen. En una célula sin
  alteraciones numéricas se esperan 2 copias en cada par del 1 al 22.
- **De más (3 o más):** compatible con una trisomía.
- **De menos (0 o 1):** compatible con una monosomía.
- **X e Y:** lo esperado depende del sexo (XX: dos X y ninguna Y; XY: una X y una Y). Por eso no se
  pintan como alerta.
- **Confianza:** qué tan seguro está el modelo de cada detección, de 0 a 1. No es la probabilidad de
  un diagnóstico.
- **Umbral ({CONF_UMBRAL}):** confianza mínima para aceptar una detección. Si se baja, se detectan más
  cromosomas, pero también más errores.
- **Limitaciones:** el modelo puede confundir pares parecidos en tamaño y forma, o contar mal
  cromosomas superpuestos. Una alerta es un aviso para revisar, no un diagnóstico.
""")

    if df_f.empty:
        st.info("No hay datos para los filtros elegidos.")
    else:
        # 1. Cariograma
        st.subheader("1 · Cariograma de una imagen")
        explicar("la cantidad de copias que detectó el modelo en cada par de la imagen elegida.",
                 "cada casillero es un par; el número grande son las copias detectadas. "
                 "Verde es 2 (normal), rojo es de más y naranja es de menos.")
        elegido = st.selectbox("Imagen", list(m.index),
                               format_func=lambda t: f"{t[1]} (id {t[0]})")
        st.altair_chart(cariograma(m.loc[elegido]))

        # 2. Mapa de calor
        st.subheader("2 · Todas las imágenes, par por par")
        explicar("en qué pares y en qué imágenes el modelo detectó una cantidad distinta de 2.",
                 "cada fila es una imagen y cada columna un par. Una columna con muchos "
                 "casilleros rojos o naranjas indica un par que el modelo confunde seguido.")
        st.altair_chart(mapa_calor(m))

        # 3 y 4. Dona + histograma
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("3 · Imágenes con y sin alertas")
            explicar("cuántas imágenes salieron sin alertas y cuántas con algún par de más o de menos.",
                     "cada imagen cuenta una sola vez; X e Y no se incluyen.")
            st.altair_chart(dona_alertas(m))
        with c2:
            st.subheader("4 · Confianza del modelo")
            explicar("qué tan seguro estuvo el modelo en cada detección.",
                     "cuanto más a la derecha, más seguro. Las barras pegadas a la línea roja "
                     "son detecciones dudosas, cerca del mínimo aceptado.")
            st.altair_chart(histograma_confianza(df_f))

        with st.expander("Más gráficos"):
            d1, d2 = st.columns(2)
            with d1:
                st.subheader("Cromosomas detectados por imagen")
                explicar("el total que contó el modelo en cada imagen.",
                         "la línea gris marca 46. Una diferencia puede ser una alteración real "
                         "o un error de detección del modelo.")
                st.altair_chart(total_por_imagen(m))
            with d2:
                st.subheader("Pares que más fallan")
                explicar("los pares con más imágenes fuera de lo esperado, separados en "
                         "de más y de menos.",
                         "barras más largas son pares más problemáticos; se muestran hasta 10.")
                graf = pares_que_fallan(m)
                if graf is None:
                    st.success("Ningún par fuera de lo esperado en las imágenes filtradas.")
                else:
                    st.altair_chart(graf)
            st.subheader("Imágenes analizadas por día")
            explicar("cuántas imágenes se analizaron según la fecha de la muestra.",
                     "cada punto es un día con al menos una imagen.")
            st.altair_chart(imagenes_por_dia(df_f))