import streamlit as st
import cv2
import numpy as np
import pandas as pd
import altair as alt
import base64
import html
from datetime import datetime
from pathlib import Path
from modelo import DetectorCromosomas
from db import (cargar_datos, guardar_analisis, cargar_revision, nombre_par,
                PARES_AUTOSOMICOS, PARES_ORDEN)

RUTA_PESOS = "models/best_24_chromosomes.pt"
CONF_UMBRAL = 0.35   # confianza mínima para aceptar una detección
IOU_UMBRAL = 0.40    # solapamiento máximo entre cajas (evita duplicados)
CONF_REVISION = 0.50  # por debajo de esta confianza, la detección se marca para revisar
# Archivo de la pestaña "Sobre el modelo" (results.csv, el registro del entrenamiento)
RUTA_INFO = Path(__file__).resolve().parent / "modelo_info"
# Datos del entrenamiento, leídos de los metadatos de los pesos
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
if "n_runs" not in st.session_state:
    st.session_state.n_runs = 0


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


# ---------- Revisión: reglas simples para decidir si una imagen necesita ojo humano ----------
def contar(clases):
    """Cuenta cuántas veces aparece cada clase en una lista, usando list.count().
    Devuelve un diccionario {clase: cantidad}; con .get(par, 0) se consulta un par."""
    return {c: clases.count(c) for c in set(clases)}


def motivos_revision(total, conteo, n_baja):
    """Lista de motivos por los que conviene revisar una imagen (vacía = sin motivos)."""
    motivos = []
    if total != 46:
        motivos.append(f"Total detectado: {total} (se esperan 46)")
    n_pares = sum(1 for p in PARES_AUTOSOMICOS if conteo.get(p, 0) != 2)
    if n_pares:
        motivos.append(f"{n_pares} par(es) autosómico(s) con cantidad distinta de 2")
    x, y = conteo.get("X", 0), conteo.get("Y", 0)
    if (x, y) not in ((2, 0), (1, 1)):
        motivos.append(f"Combinación X/Y inusual (X={x}, Y={y}); se espera XX o XY")
    if n_baja:
        motivos.append(f"{n_baja} detección(es) con confianza menor a {CONF_REVISION}")
    return motivos


def mostrar_semaforo(motivos):
    if not motivos:
        st.success("🟢 **OK**: sin motivos de revisión según los criterios del sistema. "
                   "Igual debe ser validado por un profesional.")
    else:
        st.warning("🟠 **Revisar**\n\n" + "\n".join(f"- {m}" for m in motivos))


def _orden_par(par):
    return PARES_ORDEN.index(par) if par in PARES_ORDEN else 99


def dibujar(imagen, dets):
    """Dibuja las cajas: verde (confianza suficiente), naranja (confianza baja) y
    violeta (etiqueta corregida por el profesional)."""
    salida = imagen.copy()
    for d in dets:
        x1, y1, x2, y2 = [int(v) for v in d["caja"]]
        if d["clase_final"] != d["clase_modelo"]:
            color = (200, 0, 200)
        elif d["confianza"] < CONF_REVISION:
            color = (0, 140, 255)
        else:
            color = (0, 200, 0)
        cv2.rectangle(salida, (x1, y1), (x2, y2), color, 2)
        cv2.putText(salida, f"{d['clase_final']} {d['confianza']:.2f}", (x1, max(14, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return salida


def detecciones_normalizadas(crudas):
    """Pasa las detecciones del modelo al formato interno (clase en formato A1…G22)."""
    return [{"caja": tuple(int(v) for v in d["caja"]),
             "clase_modelo": nombre_par(d["clase"]),
             "confianza": float(d["confianza"])} for d in crudas]


def informe_html(nombre, conteo, motivos, filas, png_b64=None, parametros=None, notas=None):
    """Informe de un análisis como página HTML (se abre en el navegador y se puede
    imprimir o guardar como PDF)."""
    esc = html.escape
    etiquetas = {NORMAL: ("Normal", "#E8F5E9"), DE_MAS: ("De más", "#FFEBEE"),
                 DE_MENOS: ("De menos", "#FFF3E0"), SEXUAL: ("Según sexo", "#ECEFF1")}
    pares = ""
    for p in PARES_ORDEN:
        n = conteo.get(p, 0)
        texto, fondo = etiquetas[estado_par(p, n)]
        pares += f'<tr style="background:{fondo}"><td>{p}</td><td>{n}</td><td>{texto}</td></tr>'
    dets = "".join(f"<tr><td>{esc(str(c))}</td><td>{conf:.2f}</td></tr>"
                   for c, conf in sorted(filas, key=lambda f: (_orden_par(f[0]), -f[1])))
    if motivos:
        caja = ('<div class="caja rev"><b>Revisar</b><ul>'
                + "".join(f"<li>{esc(m)}</li>" for m in motivos) + "</ul></div>")
    else:
        caja = '<div class="caja ok"><b>Sin motivos de revisión</b> según los criterios del sistema.</div>'
    imagen = f'<img src="data:image/png;base64,{png_b64}" alt="Detecciones">' if png_b64 else ""
    params = "".join(f"<li>{esc(k)}: {esc(str(v))}</li>" for k, v in (parametros or {}).items())
    extra = "".join(f"<p>{esc(n)}</p>" for n in (notas or []))
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Informe CarioDetector</title><style>
body{{font-family:Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#222}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:26px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left}}
th{{background:#f0f0f0}} img{{max-width:100%;border:1px solid #ccc}}
.caja{{padding:10px 14px;border-radius:6px;margin:12px 0}} .ok{{background:#E8F5E9}} .rev{{background:#FFF3E0}}
.aviso{{font-size:12px;color:#555;border-top:1px solid #ccc;margin-top:28px;padding-top:10px}}
</style></head><body>
<h1>Informe de análisis · CarioDetector</h1>
<p>Imagen: <b>{esc(nombre)}</b><br>Generado: {datetime.now():%d/%m/%Y %H:%M}</p>
{caja}{extra}{imagen}
<h2>Conteo por par</h2>
<p>Se esperan 2 copias en cada par del 1 al 22. X e Y se interpretan según el sexo.</p>
<table><tr><th>Par</th><th>Copias detectadas</th><th>Estado</th></tr>{pares}</table>
<h2>Detecciones</h2><table><tr><th>Clase</th><th>Confianza</th></tr>{dets}</table>
<h2>Parámetros</h2><ul>{params}</ul>
<p class="aviso">Herramienta de apoyo, no de diagnóstico. Toda alerta debe ser validada por un
profesional. Solo evalúa alteraciones numéricas (cantidad de copias por par), no estructurales.
El modelo puede confundir pares de tamaño y forma parecidos y cromosomas superpuestos.</p>
</body></html>"""


def png_base64(imagen, ancho_max=1200):
    alto, ancho = imagen.shape[:2]
    if ancho > ancho_max:
        imagen = cv2.resize(imagen, (ancho_max, int(alto * ancho_max / ancho)))
    ok, buf = cv2.imencode(".png", imagen)
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else None


def sugerir_cariotipo(conteo):
    """Cariotipo aproximado a partir del conteo por par, con el mismo formato que la sugerencia
    de la interfaz Tkinter (funciones/resultados.py): total, sexo y ganancias o pérdidas.
    Ejemplos: '46,XX' · '47,XY,+21' · '45,XX,-18'. Devuelve (cariotipo, alteraciones)."""
    total = sum(n for par, n in conteo.items() if par in PARES_ORDEN)
    x, y = conteo.get("X", 0), conteo.get("Y", 0)
    sexo = "?" if x == 0 and y == 0 else "X" * x + "Y" * y
    alteraciones = []
    for numero, par in enumerate(PARES_AUTOSOMICOS, start=1):
        diferencia = conteo.get(par, 0) - 2
        signo = "+" if diferencia > 0 else "-"
        alteraciones += [f"{signo}{numero}"] * abs(diferencia)
    cariotipo = f"{total},{sexo}" + ("," + ",".join(alteraciones) if alteraciones else "")
    return cariotipo, alteraciones


def resultado_revision(total, conteo, motivos, observ):
    """Datos para la tabla `resultados` cuando un profesional confirma la revisión.
    El cariotipo se sugiere igual que en el Tkinter; la alteración lista las ganancias y
    pérdidas numéricas (y avisa si los cromosomas sexuales no son XX ni XY)."""
    cariotipo, alteraciones = sugerir_cariotipo(conteo)
    x, y = conteo.get("X", 0), conteo.get("Y", 0)
    partes = list(alteraciones)
    if (x, y) not in ((2, 0), (1, 1)):
        partes.append(f"sexuales X={x}, Y={y}")
    alteracion = ", ".join(partes) if partes else "Sin alteraciones numéricas detectadas"
    return {"cariotipo": cariotipo[:30], "alteracion": alteracion[:100], "observacion": observ}


def mostrar_resultado(imagen, u):
    """Resultado de una detección: revisión de etiquetas, semáforo, conteo, guardado e informe.
    El estado vive en session_state, así que sobrevive a los reruns de Streamlit."""
    guardado = bool(u.get("guardado_id"))
    originales = u["detecciones"]
    base = pd.DataFrame({
        "N°": list(range(1, len(originales) + 1)),
        "Clase del modelo": [d["clase_modelo"] for d in originales],
        "Confianza": [round(d["confianza"], 3) for d in originales],
        "Clase final": [d["clase_modelo"] for d in originales],
        "Descartar": [False] * len(originales),
    })
    opciones = list(PARES_ORDEN) + sorted(set(base["Clase del modelo"]) - set(PARES_ORDEN))

    c_img = st.container()
    c_sem = st.container()

    st.subheader("Revisión de etiquetas")
    st.caption("Si el modelo se equivocó de par, cambiá la **Clase final**. Si detectó algo que no "
               "es un cromosoma, tildá **Descartar**. El conteo, el semáforo y la imagen se "
               "actualizan con tus cambios.")
    editado = st.data_editor(
        base, hide_index=True,
        disabled=True if guardado else ["N°", "Clase del modelo", "Confianza"],
        column_config={
            "Clase final": st.column_config.SelectboxColumn("Clase final", options=opciones,
                                                            required=True),
            "Descartar": st.column_config.CheckboxColumn("Descartar"),
        },
        key=f"editor_{u['run']}")

    dets, descartes = [], []
    for d, (_, fila) in zip(originales, editado.iterrows()):
        if fila["Descartar"]:
            descartes.append(d)
        else:
            dets.append({**d, "clase_final": fila["Clase final"]})
    cambios = [d for d in dets if d["clase_final"] != d["clase_modelo"]]
    conteo = contar([d["clase_final"] for d in dets])
    n_baja = sum(1 for d in dets if d["confianza"] < CONF_REVISION)
    motivos = motivos_revision(len(dets), conteo, n_baja)
    dibujada = dibujar(imagen, dets)

    with c_img:
        st.write(f"El modelo detectó {len(originales)} cromosomas; tras la revisión quedan {len(dets)}.")
        st.image(dibujada, channels="BGR",
                 caption="Verde: confianza suficiente · Naranja: confianza baja, conviene revisar · "
                         "Violeta: etiqueta corregida")
    with c_sem:
        mostrar_semaforo(motivos)

    st.subheader("Conteo por par")
    st.dataframe([{"Par": p, "Cantidad detectada": n}
                  for p, n in sorted(conteo.items(), key=lambda t: _orden_par(t[0]))])

    st.subheader("Guardar y descargar")
    revisado = st.checkbox("Confirmo que un profesional revisó este análisis",
                           key=f"rev_{u['run']}", disabled=guardado)
    if guardado:
        st.success(f"Guardado en la base de datos (análisis {u['guardado_id']}). "
                   "Ya aparece en las pestañas Dashboard y Gráficos.")
    elif st.button("Guardar en la base de datos", key=f"guardar_{u['run']}"):
        if revisado or cambios or descartes:
            observ = (f"Revisado (dashboard): {len(cambios)} cambios de etiqueta, "
                      f"{len(descartes)} descartes")
        else:
            observ = "Sin revisión manual (dashboard)"
        try:
            alto, ancho = imagen.shape[:2]
            ruta = ruta_res = resultado = None
            if u.get("bytes"):
                CARPETA_IMAGENES.mkdir(parents=True, exist_ok=True)
                marca = f"{datetime.now():%Y%m%d_%H%M%S}"
                ruta = CARPETA_IMAGENES / f"{marca}_{u['archivo']}"
                ruta.write_bytes(u["bytes"])
                # imagen con las cajas dibujadas (es la "imagen_resultado" del estudio)
                ruta_res = CARPETA_IMAGENES / f"{marca}_resultado_{Path(u['archivo']).stem}.png"
                cv2.imwrite(str(ruta_res), dibujada)
            if revisado:
                resultado = resultado_revision(len(dets), conteo, motivos, observ)
            todas = ([{**d, "descartada": False} for d in dets]
                     + [{**d, "clase_final": None, "descartada": True} for d in descartes])
            u["guardado_id"] = guardar_analisis(
                u["archivo"], todas, ancho, alto, str(ruta) if ruta else None, observ,
                imagen_resultado=str(ruta_res) if ruta_res else None, resultado=resultado)
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar en MySQL: {e}")

    filas = [(d["clase_final"], d["confianza"]) for d in dets]
    tabla = pd.DataFrame({
        "par": [d["clase_final"] for d in dets], "confianza": [d["confianza"] for d in dets],
        "par_del_modelo": [d["clase_modelo"] for d in dets],
        "x1": [d["caja"][0] for d in dets], "y1": [d["caja"][1] for d in dets],
        "x2": [d["caja"][2] for d in dets], "y2": [d["caja"][3] for d in dets]})
    notas = []
    if cambios or descartes:
        notas.append(f"Revisión manual: {len(cambios)} etiqueta(s) corregida(s) y "
                     f"{len(descartes)} detección(es) descartada(s).")
    if revisado:
        notas.append("Un profesional confirmó haber revisado este análisis.")
    informe = informe_html(
        u["archivo"], conteo, motivos, filas, png_base64(dibujada),
        {"Confianza mínima (conf)": CONF_UMBRAL, "IoU máximo (iou)": IOU_UMBRAL,
         "Pesos": RUTA_PESOS}, notas)
    d1, d2 = st.columns(2)
    d1.download_button("Descargar informe (HTML)", informe.encode("utf-8"),
                       f"informe_{Path(u['archivo']).stem}.html", "text/html",
                       key=f"dl_html_{u['run']}")
    d2.download_button("Descargar detecciones (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                       f"detecciones_{Path(u['archivo']).stem}.csv", "text/csv",
                       key=f"dl_csv_{u['run']}")
    st.caption("El informe se abre en el navegador; desde ahí se puede imprimir o guardar como PDF.")


# ---------- Laboratorio de parámetros ----------
def _resumen_deteccion(dets):
    conteo = contar([d["clase_modelo"] for d in dets])
    n_baja = sum(1 for d in dets if d["confianza"] < CONF_REVISION)
    pares = sum(1 for p in PARES_AUTOSOMICOS if conteo.get(p, 0) != 2)
    return conteo, n_baja, pares


def panel_laboratorio():
    st.subheader("Laboratorio de parámetros")
    explicar("cómo cambia lo que detecta el modelo al variar la confianza mínima (conf) y el "
             "solapamiento máximo entre cajas (IoU).",
             "subí una imagen, elegí valores y compará. Un IoU más alto deja pasar más cajas "
             "solapadas (útil con cromosomas cruzados, pero puede traer duplicados); una confianza "
             "más alta descarta las detecciones dudosas.")
    subida = st.file_uploader("Imagen de prueba", type=["jpg", "jpeg", "png"], key="lab_subida")
    if subida is None:
        st.info("Subí una imagen para empezar.")
        return
    imagen = cv2.imdecode(np.frombuffer(subida.read(), np.uint8), cv2.IMREAD_COLOR)
    c1, c2 = st.columns(2)
    conf = c1.slider("Confianza mínima (conf)", 0.05, 0.90, float(CONF_UMBRAL), 0.05)
    iou = c2.slider("IoU máximo entre cajas (iou)", 0.10, 0.90, float(IOU_UMBRAL), 0.05)

    b1, b2 = st.columns(2)
    if b1.button("Detectar con estos valores"):
        dets = detecciones_normalizadas(modelo.detectar(imagen, conf=conf, iou=iou))
        st.session_state.lab_uno = {"archivo": subida.name, "conf": conf, "iou": iou, "dets": dets}
    if b2.button("Comparar varios valores de IoU"):
        filas = []
        barra = st.progress(0.0, text="Detectando…")
        valores = [0.3, 0.4, 0.5, 0.6, 0.7]
        for i, v in enumerate(valores):
            dets = detecciones_normalizadas(modelo.detectar(imagen, conf=conf, iou=v))
            conteo, n_baja, pares = _resumen_deteccion(dets)
            filas.append({"IoU": v, "Cromosomas detectados": len(dets),
                          "Pares con cantidad distinta de 2": pares,
                          f"Detecciones con confianza < {CONF_REVISION}": n_baja})
            barra.progress((i + 1) / len(valores), text="Detectando…")
        barra.empty()
        st.session_state.lab_barrido = {"archivo": subida.name, "conf": conf,
                                        "tabla": pd.DataFrame(filas)}

    uno = st.session_state.get("lab_uno")
    if uno and uno["archivo"] == subida.name:
        st.markdown(f"**Resultado con conf={uno['conf']:.2f} e iou={uno['iou']:.2f}**")
        dets = [{**d, "clase_final": d["clase_modelo"]} for d in uno["dets"]]
        conteo, n_baja, pares = _resumen_deteccion(uno["dets"])
        k1, k2, k3 = st.columns(3)
        k1.metric("Cromosomas detectados", len(dets))
        k2.metric("Pares con cantidad distinta de 2", pares)
        k3.metric(f"Confianza < {CONF_REVISION}", n_baja)
        mostrar_semaforo(motivos_revision(len(dets), conteo, n_baja))
        st.image(dibujar(imagen, dets), channels="BGR")

    barrido = st.session_state.get("lab_barrido")
    if barrido and barrido["archivo"] == subida.name:
        st.markdown(f"**Comparación de IoU con conf={barrido['conf']:.2f}**")
        t = barrido["tabla"]
        st.dataframe(t, hide_index=True)
        lineas = alt.Chart(t).mark_line(point=True, color=AZUL).encode(
            x=alt.X("IoU:Q", scale=alt.Scale(domain=[0.25, 0.75])),
            y=alt.Y("Cromosomas detectados:Q", scale=alt.Scale(zero=False)),
            tooltip=["IoU", "Cromosomas detectados"])
        ref = alt.Chart(pd.DataFrame({"y": [46]})).mark_rule(
            color=COLORES[3], strokeDash=[6, 4]).encode(y="y:Q")
        st.altair_chart((lineas + ref).properties(width="container", height=240))
        st.caption("La línea gris marca 46, el total esperado en una célula sin alteraciones "
                   "numéricas. Elegir el IoU que más se acerque sin generar duplicados.")


# ---------- Sobre el modelo ----------
@st.cache_data(ttl=60)
def _revision_cacheada():
    return cargar_revision()


def pestana_modelo():
    st.subheader("Sobre el modelo")
    st.markdown("El detector es un **YOLOv8s** que partió de pesos preentrenados con COCO y se "
                "reentrenó (*fine-tuning*) con imágenes de cariotipos para reconocer los 24 tipos de "
                "cromosoma. Lo que sigue describe cómo fue entrenado y qué tan bien funciona.")
    st.table(pd.DataFrame({"Dato": list(INFO_MODELO), "Valor": list(INFO_MODELO.values())})
             .set_index("Dato"))

    ruta_csv = RUTA_INFO / "results.csv"
    if ruta_csv.exists():
        r = pd.read_csv(ruta_csv)
        r.columns = [c.strip() for c in r.columns]
        mejor = r.loc[r["metrics/mAP50-95(B)"].idxmax()]
        st.markdown(f"#### Resultados en validación (mejor época: {int(mejor['epoch'])})")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Precisión", f"{mejor['metrics/precision(B)']:.1%}")
        k2.metric("Recall", f"{mejor['metrics/recall(B)']:.1%}")
        k3.metric("mAP@50", f"{mejor['metrics/mAP50(B)']:.1%}")
        k4.metric("mAP@50-95", f"{mejor['metrics/mAP50-95(B)']:.1%}")
        with st.expander("¿Qué significa cada métrica?"):
            st.markdown("""
- **Precisión:** de todo lo que el modelo detectó, qué proporción era correcto.
- **Recall:** de todos los cromosomas que había, qué proporción encontró.
- **mAP@50:** resume precisión y recall para todas las clases; cuenta una detección como acertada si
  su caja se solapa al menos 50 % con la real y la clase es correcta.
- **mAP@50-95:** igual, pero más exigente: promedia solapamientos de 50 % a 95 %.
- Son métricas **por cromosoma**, sobre imágenes de validación del mismo conjunto de datos. Un
  cariotipo exige acertar los 46 a la vez, así que el desempeño por imagen completa es menor.
""")
        met = r[["epoch", "metrics/precision(B)", "metrics/recall(B)",
                 "metrics/mAP50(B)", "metrics/mAP50-95(B)"]].rename(columns={
            "metrics/precision(B)": "Precisión", "metrics/recall(B)": "Recall",
            "metrics/mAP50(B)": "mAP@50", "metrics/mAP50-95(B)": "mAP@50-95"})
        largo = met.melt("epoch", var_name="Métrica", value_name="Valor")
        nombres = ["Precisión", "Recall", "mAP@50", "mAP@50-95"]
        curva = alt.Chart(largo).mark_line().encode(
            x=alt.X("epoch:Q", title="Época"),
            y=alt.Y("Valor:Q", title="Valor", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("Métrica:N", scale=alt.Scale(
                domain=nombres, range=[AZUL, "#8E24AA", "#26A69A", "#4D4D4D"]),
                legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["epoch", "Métrica", alt.Tooltip("Valor:Q", format=".3f")])
        marca = alt.Chart(pd.DataFrame({"x": [int(mejor["epoch"])]})).mark_rule(
            color=COLORES[3], strokeDash=[6, 4]).encode(x="x:Q")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Métricas por época**")
            explicar("cómo mejoró el modelo durante el entrenamiento.",
                     "las curvas suben y se estabilizan; la línea gris es la mejor época, la "
                     "que se guardó como pesos finales.")
            st.altair_chart((curva + marca).properties(width="container", height=280))
        perdida = r[["epoch", "train/box_loss", "val/box_loss"]].rename(columns={
            "train/box_loss": "Entrenamiento", "val/box_loss": "Validación"}).melt(
            "epoch", var_name="Conjunto", value_name="Pérdida")
        with g2:
            st.markdown("**Error de las cajas por época**")
            explicar("qué tan bien ubica las cajas (menos es mejor).",
                     "si la curva de validación se separa hacia arriba de la de entrenamiento, hay "
                     "sobreajuste; acá se mantienen juntas.")
            st.altair_chart(alt.Chart(perdida).mark_line().encode(
                x=alt.X("epoch:Q", title="Época"), y=alt.Y("Pérdida:Q", scale=alt.Scale(zero=False)),
                color=alt.Color("Conjunto:N", scale=alt.Scale(
                    domain=["Entrenamiento", "Validación"], range=[AZUL, "#4D4D4D"]),
                    legend=alt.Legend(orient="bottom", title=None)),
                tooltip=["epoch", "Conjunto", alt.Tooltip("Pérdida:Q", format=".3f")]
            ).properties(width="container", height=280))
    else:
        st.info("Falta el archivo modelo_info/results.csv para mostrar las métricas.")

    st.markdown("#### Errores corregidos por profesionales")
    rev = _revision_cacheada()
    if rev is None or rev["analisis"] == 0:
        st.info("Todavía no hay análisis revisados. Cuando alguien corrija etiquetas en la pestaña "
                "*Subir y detectar* y guarde, acá va a aparecer una medida real de los errores del modelo.")
    else:
        corr = rev["correcciones"]
        cambios = corr[corr["tipo"] == "cambio"]
        descartes = int((corr["tipo"] == "descarte").sum())
        total_modelo = rev["detecciones"] + descartes
        k1, k2, k3 = st.columns(3)
        k1.metric("Análisis revisados", rev["analisis"])
        k2.metric("Detecciones del modelo", total_modelo)
        k3.metric("Corregidas o descartadas",
                  f"{(len(cambios) + descartes) / max(total_modelo, 1):.1%}")
        if len(cambios):
            top = (cambios.groupby(["clase_modelo", "clase_final"]).size()
                   .reset_index(name="veces").sort_values("veces", ascending=False).head(10))
            top["Confusión"] = top["clase_modelo"] + " → " + top["clase_final"]
            st.markdown("**Confusiones más frecuentes** (lo que dijo el modelo → lo que corrigió la persona)")
            st.altair_chart(alt.Chart(top).mark_bar(color=AZUL).encode(
                y=alt.Y("Confusión:N", sort="-x", title=None),
                x=alt.X("veces:Q", title="Veces", axis=eje_entero(0, int(top["veces"].max()), "Veces")),
                tooltip=["Confusión", "veces"]).properties(width="container",
                                                           height=max(120, 28 * len(top) + 40)))
        st.caption("Se calcula solo con los análisis marcados como revisados por un profesional.")

    st.markdown("#### Limitaciones")
    st.markdown("""
- Puede **confundir pares de tamaño y forma parecidos**, sobre todo dentro de un mismo grupo
  (el detalle de las confusiones está en la evaluación de modelos del equipo).
- Puede contar mal los **cromosomas superpuestos o cruzados**.
- Solo evalúa **alteraciones numéricas**, no estructurales.
- Es una herramienta de **apoyo**: toda alerta debe ser validada por un profesional.
""")


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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Subir y detectar", "Dashboard", "Historial de sesión", "Gráficos", "Laboratorio",
     "Sobre el modelo"])

# ---------- TAB 1: subir y detectar ----------
with tab1:
    archivo = st.file_uploader("Subí una imagen de cariotipo", type=["jpg", "jpeg", "png"])
    if archivo is not None:
        bytes_imagen = np.frombuffer(archivo.read(), np.uint8)
        imagen = cv2.imdecode(bytes_imagen, cv2.IMREAD_COLOR)

        if st.button("Detectar cromosomas"):
            dets = detecciones_normalizadas(
                modelo.detectar(imagen, conf=CONF_UMBRAL, iou=IOU_UMBRAL))
            st.session_state.n_runs += 1
            st.session_state.ultimo_resultado = {
                "run": st.session_state.n_runs, "archivo": archivo.name,
                "detecciones": dets, "guardado_id": None, "bytes": bytes_imagen.tobytes()}
            conteo0 = contar([d["clase_modelo"] for d in dets])
            motivos0 = motivos_revision(
                len(dets), conteo0, sum(1 for d in dets if d["confianza"] < CONF_REVISION))
            st.session_state.historial_pruebas.append({
                "Imagen": archivo.name,
                "Total detectado": len(dets),
                "Pares con cantidad inesperada": ", ".join(
                    f"{p} ({conteo0.get(p, 0)})" for p in PARES_AUTOSOMICOS
                    if conteo0.get(p, 0) != 2) or "Ninguno",
                "Revisión": "Revisar" if motivos0 else "OK",
            })

        u = st.session_state.get("ultimo_resultado")
        if u and u["archivo"] == archivo.name:
            mostrar_resultado(imagen, u)
        else:
            st.image(imagen, channels="BGR", caption="Imagen cargada")

# ---------- TAB 2: dashboard ----------
with tab2:
    mostrar_origen()
    if df_f.empty:
        st.info("No hay datos para los filtros elegidos.")
    else:
        baja = df_f.groupby(["imagen_id", "archivo"])["confianza"].apply(
            lambda s: int((s < CONF_REVISION).sum()))
        motivos_img = {idx: motivos_revision(int(m.loc[idx].sum()), m.loc[idx].to_dict(),
                                             int(baja.get(idx, 0))) for idx in m.index}
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Imágenes analizadas", df_f["imagen_id"].nunique())
        k2.metric("Cromosomas detectados", len(df_f))
        k3.metric("Confianza promedio", f"{df_f['confianza'].mean():.1%}")
        k4.metric("Imágenes a revisar", sum(1 for v in motivos_img.values() if v))

        st.subheader("Resumen por imagen")
        st.caption("**Revisión** indica si conviene que un profesional mire la imagen: total distinto "
                   "de 46, pares con cantidad distinta de 2, X/Y inusual o detecciones de baja confianza.")
        resumen = pd.DataFrame({
            "Total detectado": m.sum(axis=1),
            "Pares con cantidad inesperada": m[PARES_AUTOSOMICOS].apply(
                lambda fila: ", ".join(fila[fila != 2].index) or "Ninguno", axis=1),
            "Revisión": ["Revisar" if motivos_img[idx] else "OK" for idx in m.index],
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

        with st.expander("Informe de una imagen"):
            sel = st.selectbox("Imagen", list(m.index), key="informe_img",
                               format_func=lambda t: f"{t[1]} (id {t[0]})")
            sub = df_f[df_f["imagen_id"] == sel[0]]
            filas_i = list(zip(sub["numero_par"], sub["confianza"]))
            html_i = informe_html(
                sel[1], contar(list(sub["numero_par"])), motivos_img[sel], filas_i,
                None, {"Fuente": "Base de datos"},
                ["Informe generado desde los datos guardados (sin imagen)."])
            st.download_button("Descargar informe (HTML)", html_i.encode("utf-8"),
                               f"informe_{Path(sel[1]).stem}.html", "text/html")

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

# ---------- TAB 5: laboratorio ----------
with tab5:
    panel_laboratorio()

# ---------- TAB 6: sobre el modelo ----------
with tab6:
    pestana_modelo()
