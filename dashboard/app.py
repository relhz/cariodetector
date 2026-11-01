import streamlit as st
import cv2
import numpy as np
import pandas as pd
import altair as alt
import base64
import html
import json
import time
from datetime import datetime
from pathlib import Path
from modelo import DetectorCromosomas
from db import (cargar_datos, guardar_analisis, cargar_revision, nombre_par,
                PARES_AUTOSOMICOS, PARES_ORDEN)

RUTA_PESOS = "models/best_24_chromosomes.pt"
CONF_UMBRAL = 0.25   # confianza mínima para aceptar una detección
IOU_UMBRAL = 0.70    # solapamiento máximo entre cajas (evita duplicados)
CONF_REVISION = 0.50  # por debajo de esta confianza, la detección se marca para revisar
# Archivo de la pestaña "Sobre el modelo" (results_yolov8l.csv, el registro del entrenamiento)
RUTA_INFO = Path(__file__).resolve().parent / "modelo_info"
# Datos del entrenamiento
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
# Métricas finales en validación, guardadas dentro de los pesos (train_metrics)
METRICAS_FINALES = {"Precisión": 0.99088, "Recall": 0.98243,
                    "mAP@50": 0.99355, "mAP@50-95": 0.86743}
# Carpeta donde se copian las imágenes guardadas desde el dashboard
CARPETA_IMAGENES = Path(__file__).resolve().parent.parent / "assets" / "imagenes_analizadas"

alt.data_transformers.disable_max_rows()

# Colores: el mismo significado en todo el dashboard 
NORMAL = "Normal (2 copias)"
DE_MAS = "De más (3 o más)"
DE_MENOS = "De menos (0 o 1)"
SEXUAL = "X / Y (según sexo)"
ESTADOS = [NORMAL, DE_MAS, DE_MENOS, SEXUAL]
COLORES = ["#2E7D32", "#C62828", "#D97706", "#78909C"]
ESCALA_ESTADO = alt.Scale(domain=ESTADOS, range=COLORES)
AZUL = "#4C78A8"

#Funciones para los pares según cantidad y grupo 
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
    paso = max(1, -(-(maximo - minimo) // 8))   #Hasta 8 marcas
    return alt.Axis(title=titulo, values=list(range(minimo, maximo + 1, paso)), format="d")


def matriz_conteos(d):
    """Filas = imágenes, columnas = pares, valores = cantidad detectada."""
    m = d.pivot_table(index=["imagen_id", "archivo"], columns="numero_par",
                      values="confianza", aggfunc="count", fill_value=0)
    return m.reindex(columns=PARES_ORDEN, fill_value=0)


# Gráficos 
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


def img_alertas(m):
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


# FIN FUNCIONES DE GRÁFICOS

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


# Revisión: Para revisión de un profesional 
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


# Color de la caja: uno por clase
def _paleta_clases():
    import colorsys
    nombres = [f"{g}{n}" for g, ns in (("A", (1, 2, 3)), ("B", (4, 5)), ("C", range(6, 13)),
               ("D", (13, 14, 15)), ("E", (16, 17, 18)), ("F", (19, 20)), ("G", (21, 22)))
               for n in ns] + ["X", "Y"]
    pal = {}
    for i, nombre in enumerate(nombres):
        h = (i * 0.381966) % 1.0          # ángulo áureo: clases vecinas quedan bien distintas
        v = 0.62 if 0.12 < h < 0.45 else 0.78   # verdes/amarillos más oscuros para leer el texto blanco
        r, g, b = colorsys.hsv_to_rgb(h, 0.85, v)
        pal[nombre] = (int(b * 255), int(g * 255), int(r * 255))   # BGR
    return pal


COLOR_CLASE = _paleta_clases()


def _color_bgr(clase):
    return COLOR_CLASE.get(str(clase).strip().upper(), (117, 117, 117))

#Dibuja las cajas con el color de la clase final. La etiqueta lleva fondo de color, '?' marca confianza baja (conviene revisar) y '*' una etiqueta corregida por el profesional
def dibujar(imagen, dets, resaltar=None):
    salida = imagen.copy()
    esc = max(0.4, min(salida.shape[:2]) / 1400)
    for d in dets:
        x1, y1, x2, y2 = [int(v) for v in d["caja"]]
        color = _color_bgr(d["clase_final"])
        dudosa = d["confianza"] < CONF_REVISION
        corregida = d["clase_final"] != d["clase_modelo"]
        if resaltar is not None and d.get("n") == resaltar:
            cv2.rectangle(salida, (x1 - 5, y1 - 5), (x2 + 5, y2 + 5), (255, 255, 255), 4)
            cv2.rectangle(salida, (x1 - 5, y1 - 5), (x2 + 5, y2 + 5), (0, 0, 0), 1)
        cv2.rectangle(salida, (x1, y1), (x2, y2), color, 3 if dudosa else 2)
        texto = f"{d['clase_final']} {d['confianza']:.2f}" + ("?" if dudosa else "") + ("*" if corregida else "")
        (tw, th), base = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, esc, 1)
        ytop = max(th + base + 2, y1)
        cv2.rectangle(salida, (x1, ytop - th - base - 2), (x1 + tw + 4, ytop), color, -1)
        cv2.putText(salida, texto, (x1 + 2, ytop - base), cv2.FONT_HERSHEY_SIMPLEX, esc,
                    (255, 255, 255), 1, cv2.LINE_AA)
    return salida

#Zoom para las imagenes
def visor_zoom(original, analizada, alto=520, titulos=("Imagen original", "Imagen analizada"), foco=None):
    def _b64(img):
        h, w = img.shape[:2]
        if max(h, w) > 1800:
            f = 1800 / max(h, w)
            img = cv2.resize(img, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        return base64.b64encode(buf).decode()
    h0, w0 = original.shape[:2]
    f = min(1.0, 1800 / max(h0, w0))
    foco_js = json.dumps([round(v * f, 1) for v in foco]) if foco else "null"
    pagina = """
<style>
 body{margin:0;font-family:sans-serif;color-scheme:light dark}
 .barra{display:flex;gap:6px;align-items:center;margin-bottom:6px;flex-wrap:wrap}
 .barra button{padding:4px 12px;border:1px solid #888;border-radius:6px;background:#f2f2f2;
   color:#222;cursor:pointer;font-size:14px}
 .barra span{font-size:12px;color:#888}
 .par{display:flex;gap:8px}
 .caja{flex:1;min-width:0}
 .tit{font-size:13px;font-weight:600;margin:0 0 3px 2px}
 .pane{position:relative;overflow:hidden;height:__ALTO__px;background:#ececec;
   border:1px solid #aaa;border-radius:6px;cursor:grab;touch-action:none}
 .pane img{position:absolute;left:0;top:0;transform-origin:0 0;user-select:none;
   -webkit-user-drag:none;max-width:none}
</style>
<div class="barra">
 <button id="mas">＋</button><button id="menos">－</button>
 <button id="ajustar">Ajustar a ventana</button><button id="uno">100 %</button>
 <span>Rueda del mouse para acercar · arrastrá para mover · doble clic para ajustar</span>
</div>
<div class="par">
 <div class="caja"><p class="tit">__T1__</p><div class="pane"><img id="i1" src="data:image/jpeg;base64,__A__"></div></div>
 <div class="caja"><p class="tit">__T2__</p><div class="pane"><img id="i2" src="data:image/jpeg;base64,__B__"></div></div>
</div>
<script>
const panes=[...document.querySelectorAll('.pane')], imgs=[i1,i2];
let k=1,tx=0,ty=0,k0=1;const foco=__FOCO__;
function aplicar(){imgs.forEach(i=>i.style.transform=`translate(${tx}px,${ty}px) scale(${k})`);}
function ajustar(){const p=panes[0],w=imgs[0].naturalWidth,h=imgs[0].naturalHeight;
  if(!w)return;k0=Math.min(p.clientWidth/w,p.clientHeight/h);k=k0;
  tx=(p.clientWidth-w*k)/2;ty=(p.clientHeight-h*k)/2;aplicar();}
function zoom(f,cx,cy){const n=Math.min(Math.max(k*f,k0*0.5),k0*20);f=n/k;
  tx=cx-(cx-tx)*f;ty=cy-(cy-ty)*f;k=n;aplicar();}
panes.forEach(p=>{
  p.addEventListener('wheel',e=>{e.preventDefault();const r=p.getBoundingClientRect();
    zoom(e.deltaY<0?1.2:1/1.2,e.clientX-r.left,e.clientY-r.top);},{passive:false});
  let d=null;
  p.addEventListener('pointerdown',e=>{d={x:e.clientX,y:e.clientY};p.setPointerCapture(e.pointerId);p.style.cursor='grabbing';});
  p.addEventListener('pointermove',e=>{if(!d)return;tx+=e.clientX-d.x;ty+=e.clientY-d.y;d={x:e.clientX,y:e.clientY};aplicar();});
  p.addEventListener('pointerup',()=>{d=null;p.style.cursor='grab';});
  p.addEventListener('dblclick',ajustar);
});
const c=()=>[panes[0].clientWidth/2,panes[0].clientHeight/2];
mas.onclick=()=>zoom(1.4,...c());menos.onclick=()=>zoom(1/1.4,...c());
ajustar_btn=document.getElementById('ajustar');ajustar_btn.onclick=ajustar;
uno.onclick=()=>{const [cx,cy]=c();zoom(1/k,cx,cy);};
function inicio(){ajustar();if(!foco)return;const p=panes[0],bw=foco[2]-foco[0],bh=foco[3]-foco[1];
  k=Math.max(Math.min(p.clientWidth/(bw*3),p.clientHeight/(bh*3),k0*20),k0);
  tx=p.clientWidth/2-(foco[0]+bw/2)*k;ty=p.clientHeight/2-(foco[1]+bh/2)*k;aplicar();}
imgs[0].onload=inicio;if(imgs[0].complete)inicio();
window.addEventListener('resize',ajustar);
</script>
"""
    html_vis = (pagina.replace("__ALTO__", str(alto)).replace("__A__", _b64(original)).replace("__B__", _b64(analizada))
                           .replace("__T1__", html.escape(titulos[0])).replace("__T2__", html.escape(titulos[1]))
                           .replace("__FOCO__", foco_js))
    if hasattr(st, "iframe"):     
        st.iframe(html_vis, height=alto + 90)
    else:
        st.components.v1.html(html_vis, height=alto + 90)

#Cariograma con recortes para ver cada par etiquetado 
def cariograma_recortes(imagen, dets, celda=(120, 190), margen=0.12):
    cw, ch = celda
    pie = 26
    filas_pares = [PARES_ORDEN[:12], PARES_ORDEN[12:]]
    lienzo = np.full((len(filas_pares) * (ch + pie) + 8, 12 * cw, 3), 255, np.uint8)
    alto_i, ancho_i = imagen.shape[:2]
    for f, pares in enumerate(filas_pares):
        for c, par in enumerate(pares):
            ds = sorted((d for d in dets if d["clase_final"] == par), key=lambda d: -d["confianza"])
            ox, oy = c * cw, f * (ch + pie) + 4
            ancho_celda = (cw - 6) // max(len(ds), 2)
            for i, d in enumerate(ds):
                x1, y1, x2, y2 = d["caja"]
                mx, my = int((x2 - x1) * margen), int((y2 - y1) * margen)
                rec = imagen[max(0, y1 - my):min(alto_i, y2 + my), max(0, x1 - mx):min(ancho_i, x2 + mx)]
                if rec.size == 0:
                    continue
                h, w = rec.shape[:2]
                k = min(ancho_celda / w, (ch - 6) / h)
                rec = cv2.resize(rec, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)
                rh, rw = rec.shape[:2]
                x0 = ox + 3 + i * ancho_celda + (ancho_celda - rw) // 2
                y0 = oy + (ch - rh) // 2
                lienzo[y0:y0 + rh, x0:x0 + rw] = rec
            mal = par in PARES_AUTOSOMICOS and len(ds) != 2
            cv2.putText(lienzo, f"{par} ({len(ds)})", (ox + 6, oy + ch + 18), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 0, 200) if mal else (60, 60, 60), 1, cv2.LINE_AA)
            cv2.line(lienzo, (ox, oy), (ox, oy + ch + pie - 4), (225, 225, 225), 1)
    return lienzo


def detecciones_normalizadas(crudas):
    return [{"caja": tuple(int(v) for v in d["caja"]),
             "clase_modelo": nombre_par(d["clase"]),
             "confianza": float(d["confianza"])} for d in crudas]


def informe_html(nombre, conteo, motivos, filas, png_b64=None, parametros=None, notas=None):
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

#Cariotipo aproximado a partir del conteo por par, con el mismo formato que la sugerencia de la interfaz Tkinter
def sugerir_cariotipo(conteo):
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
            dets.append({**d, "clase_final": fila["Clase final"], "n": int(fila["N°"])})
    cambios = [d for d in dets if d["clase_final"] != d["clase_modelo"]]
    conteo = contar([d["clase_final"] for d in dets])
    n_baja = sum(1 for d in dets if d["confianza"] < CONF_REVISION)
    motivos = motivos_revision(len(dets), conteo, n_baja)
    dibujada = dibujar(imagen, dets)

    with c_img:
        st.write(f"El modelo detectó {len(originales)} cromosomas; tras la revisión quedan {len(dets)}.")
        if u.get("segundos") is not None:
            st.caption(f"Detección procesada en {u['segundos']:.1f} s")
        with st.expander("Filtrar y resaltar en la imagen"):
            f1, f2, f3 = st.columns(3)
            sel = f1.multiselect("Mostrar solo estas clases", opciones, placeholder="Todas",
                                 key=f"fil_cl_{u['run']}")
            solo_dudosas = f2.checkbox(f"Solo confianza < {CONF_REVISION}", key=f"fil_du_{u['run']}")
            por_etiqueta = {"Ninguno": None}
            for d in dets:
                por_etiqueta[f"N° {d['n']} · {d['clase_final']}"] = d
            elegido = f3.selectbox("Resaltar y acercar", list(por_etiqueta), key=f"fil_re_{u['run']}")
            st.caption("El filtro solo cambia lo que se ve; el conteo y lo que se guarda no cambian.")
        foco_det = por_etiqueta.get(elegido)
        visibles = [d for d in dets
                    if (not sel or d["clase_final"] in sel)
                    and (not solo_dudosas or d["confianza"] < CONF_REVISION)]
        vista = dibujar(imagen, visibles, resaltar=foco_det["n"] if foco_det else None)
        visor_zoom(imagen, vista, foco=foco_det["caja"] if foco_det else None)
        st.caption("Cada color es una clase · ? = confianza baja, conviene revisar · "
                   "* = etiqueta corregida")
        with st.expander("Cariograma armado (recortes ordenados por par)"):
            st.image(cariograma_recortes(imagen, dets), channels="BGR")
            st.caption("Cada columna es un par con los cromosomas que quedaron con esa Clase final. "
                       "El rótulo va en rojo si un par autosómico no tiene exactamente 2.")
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
                # imagen con las cajas dibujadas
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


#Laboratorio de parámetros
def _resumen_deteccion(dets):
    conteo = contar([d["clase_modelo"] for d in dets])
    n_baja = sum(1 for d in dets if d["confianza"] < CONF_REVISION)
    pares = sum(1 for p in PARES_AUTOSOMICOS if conteo.get(p, 0) != 2)
    return conteo, n_baja, pares


@st.cache_resource
def cargar_detector(ruta):
    return DetectorCromosomas(ruta)


def panel_comparar_modelos(imagen, archivo, conf, iou):
    st.divider()
    st.subheader("Comparar dos modelos")
    explicar("cómo detecta cada modelo la misma imagen: cantidad, pares con cantidad distinta de 2, "
             "confianza y tiempo.",
             "elegí dos archivos de pesos (.pt). Mismos valores de conf e iou para los dos, así la "
             "comparación es justa.")
    pesos = sorted(str(p).replace("\\", "/") for p in Path(RUTA_PESOS).parent.glob("*.pt"))
    if len(pesos) < 2:
        st.info("Para comparar hacen falta al menos dos archivos .pt en la carpeta models/ "
                "(por ejemplo, el YOLOv8s anterior junto al YOLOv8l actual).")
        return
    c1, c2 = st.columns(2)
    ia = pesos.index(RUTA_PESOS) if RUTA_PESOS in pesos else 0
    a = c1.selectbox("Modelo A", pesos, index=ia, key="comp_a")
    b = c2.selectbox("Modelo B", pesos, index=0 if ia != 0 else 1, key="comp_b")
    if a == b:
        st.warning("Elegí dos modelos distintos.")
        return
    if st.button("Comparar modelos"):
        res = []
        for ruta in (a, b):
            det = cargar_detector(ruta)
            t0 = time.perf_counter()
            dets = detecciones_normalizadas(det.detectar(imagen, conf=conf, iou=iou))
            res.append({"ruta": ruta, "dets": dets, "seg": time.perf_counter() - t0})
        st.session_state.lab_comp = {"archivo": archivo, "a": a, "b": b, "conf": conf, "iou": iou,
                                     "res": res}
    comp = st.session_state.get("lab_comp")
    if not comp or comp["archivo"] != archivo or (comp["a"], comp["b"]) != (a, b):
        return
    filas, imgs = [], []
    for r in comp["res"]:
        conteo, n_baja, pares = _resumen_deteccion(r["dets"])
        conf_prom = sum(d["confianza"] for d in r["dets"]) / len(r["dets"]) if r["dets"] else 0
        filas.append({"Modelo": Path(r["ruta"]).name, "Cromosomas detectados": len(r["dets"]),
                      "Pares con cantidad distinta de 2": pares,
                      f"Detecciones con confianza < {CONF_REVISION}": n_baja,
                      "Confianza promedio": round(conf_prom, 3), "Tiempo (s)": round(r["seg"], 2)})
        imgs.append(dibujar(imagen, [{**d, "clase_final": d["clase_modelo"]} for d in r["dets"]]))
    st.caption(f"Resultados con conf={comp['conf']:.2f} e iou={comp['iou']:.2f}.")
    st.dataframe(pd.DataFrame(filas), hide_index=True)
    visor_zoom(imgs[0], imgs[1], titulos=(Path(a).name, Path(b).name))
    cA = contar([d["clase_modelo"] for d in comp["res"][0]["dets"]])
    cB = contar([d["clase_modelo"] for d in comp["res"][1]["dets"]])
    difs = [{"Clase": p, Path(a).name: cA.get(p, 0), Path(b).name: cB.get(p, 0)}
            for p in PARES_ORDEN if cA.get(p, 0) != cB.get(p, 0)]
    if difs:
        st.markdown("**Clases donde los modelos no coinciden**")
        st.dataframe(pd.DataFrame(difs), hide_index=True)
    else:
        st.success("Los dos modelos dan el mismo conteo en todas las clases.")


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

    panel_comparar_modelos(imagen, subida.name, conf, iou)


#Sobre el modelo 
@st.cache_data(ttl=60)
def _revision_cacheada():
    return cargar_revision()


def _ayuda_metricas():
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
# Cada modelo con su ficha y su registro de entrenamiento (carpeta modelo_info/)
MODELOS_INFO = {
    "YOLOv8l (actual)": {"info": INFO_MODELO, "csv": "results_yolov8l.csv", "color": "#1565C0"},
    "YOLOv8s (anterior)": {"info": INFO_V8S, "csv": "results_yolov8s.csv", "color": "#EF6C00"},
}


def _leer_results(nombre_csv):
    ruta = RUTA_INFO / nombre_csv
    if not ruta.exists():
        return None
    r = pd.read_csv(ruta)
    r.columns = [c.strip() for c in r.columns]
    return r


def _curvas_modelo(r):
    """Resultados en validación y curvas de un entrenamiento (r = results.csv)."""
    mejor = r.loc[r["metrics/mAP50-95(B)"].idxmax()]
    st.markdown(f"#### Resultados en validación (mejor época: {int(mejor['epoch'])})")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Precisión", f"{mejor['metrics/precision(B)']:.1%}")
    k2.metric("Recall", f"{mejor['metrics/recall(B)']:.1%}")
    k3.metric("mAP@50", f"{mejor['metrics/mAP50(B)']:.1%}")
    k4.metric("mAP@50-95", f"{mejor['metrics/mAP50-95(B)']:.1%}")
    _ayuda_metricas()
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
                 "sobreajuste; si se mantienen juntas, el modelo generaliza.")
        st.altair_chart(alt.Chart(perdida).mark_line().encode(
            x=alt.X("epoch:Q", title="Época"), y=alt.Y("Pérdida:Q", scale=alt.Scale(zero=False)),
            color=alt.Color("Conjunto:N", scale=alt.Scale(
                domain=["Entrenamiento", "Validación"], range=[AZUL, "#4D4D4D"]),
                legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["epoch", "Conjunto", alt.Tooltip("Pérdida:Q", format=".3f")]
        ).properties(width="container", height=280))


def _comparar_modelos_info(rl, rs):
    """Compara los dos entrenamientos: ficha, métricas de la mejor época y curvas superpuestas."""
    nl, ns = "YOLOv8l (actual)", "YOLOv8s (anterior)"
    st.markdown("#### Fichas de los dos modelos")
    ficha = pd.DataFrame({"Dato": list(INFO_MODELO),
                          ns: [INFO_V8S[k] for k in INFO_MODELO],
                          nl: [INFO_MODELO[k] for k in INFO_MODELO]}).set_index("Dato")
    st.table(ficha)
    if rl is None or rs is None:
        faltan = [MODELOS_INFO[n]["csv"] for n, r in ((nl, rl), (ns, rs)) if r is None]
        st.info("Para comparar las métricas faltan en modelo_info/: " + ", ".join(faltan))
        return
    ml = rl.loc[rl["metrics/mAP50-95(B)"].idxmax()]
    ms = rs.loc[rs["metrics/mAP50-95(B)"].idxmax()]
    claves = [("Precisión", "metrics/precision(B)"), ("Recall", "metrics/recall(B)"),
              ("mAP@50", "metrics/mAP50(B)"), ("mAP@50-95", "metrics/mAP50-95(B)")]
    filas = [{"Métrica": n, ns: f"{ms[c]:.1%}", nl: f"{ml[c]:.1%}",
              "Diferencia (puntos)": f"{(ml[c] - ms[c]) * 100:+.1f}"} for n, c in claves]
    filas.append({"Métrica": "Mejor época", ns: f"{int(ms['epoch'])} de {len(rs)}",
                  nl: f"{int(ml['epoch'])} de {len(rl)}", "Diferencia (puntos)": ""})
    if "time" in rl.columns and "time" in rs.columns:
        filas.append({"Métrica": "Duración del entrenamiento",
                      ns: f"{rs['time'].iloc[-1] / 3600:.1f} h", nl: f"{rl['time'].iloc[-1] / 3600:.1f} h",
                      "Diferencia (puntos)": ""})
    st.markdown("#### Resultados en validación (mejor época de cada uno)")
    st.table(pd.DataFrame(filas).set_index("Métrica"))
    st.caption("Son métricas por cromosoma sobre las imágenes de validación. La comparación es justa "
               "solo si los dos modelos usaron las mismas imágenes de validación. Para medir imágenes "
               "completas (46 cromosomas bien clasificados) se usa la evaluación sobre el conjunto TEST.")
    _ayuda_metricas()
    larga = pd.concat([
        rs.assign(Modelo=ns), rl.assign(Modelo=nl)])[
        ["epoch", "Modelo", "metrics/mAP50-95(B)", "val/box_loss"]]
    dom = [nl, ns]
    rng = [MODELOS_INFO[nl]["color"], MODELOS_INFO[ns]["color"]]
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**mAP@50-95 por época**")
        explicar("la métrica más exigente, época por época, para los dos modelos.",
                 "la curva más alta y estable es la del modelo que mejor ubica los cromosomas.")
        st.altair_chart(alt.Chart(larga).mark_line().encode(
            x=alt.X("epoch:Q", title="Época"),
            y=alt.Y("metrics/mAP50-95(B):Q", title="mAP@50-95", scale=alt.Scale(zero=False)),
            color=alt.Color("Modelo:N", scale=alt.Scale(domain=dom, range=rng),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Modelo", "epoch", alt.Tooltip("metrics/mAP50-95(B):Q", format=".3f")]
        ).properties(width="container", height=280))
    with g2:
        st.markdown("**Error de las cajas en validación**")
        explicar("qué tan bien ubica las cajas cada modelo (menos es mejor).",
                 "una curva más baja significa cajas mejor ajustadas.")
        st.altair_chart(alt.Chart(larga).mark_line().encode(
            x=alt.X("epoch:Q", title="Época"),
            y=alt.Y("val/box_loss:Q", title="Pérdida de cajas", scale=alt.Scale(zero=False)),
            color=alt.Color("Modelo:N", scale=alt.Scale(domain=dom, range=rng),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Modelo", "epoch", alt.Tooltip("val/box_loss:Q", format=".3f")]
        ).properties(width="container", height=280))


def pestana_modelo():
    st.subheader("Sobre el modelo")
    vista = st.radio("Qué ver", ["YOLOv8l (actual)", "YOLOv8s (anterior)", "Comparar los dos"],
                     horizontal=True, key="vista_modelo", label_visibility="collapsed")
    st.markdown("Los detectores son modelos **YOLOv8** que partieron de pesos preentrenados con COCO "
                "y se reentrenaron (*fine-tuning*) con imágenes de cariotipos para reconocer los 24 "
                "tipos de cromosoma. Lo que sigue describe cómo fueron entrenados y qué tan bien funcionan.")
    rl = _leer_results(MODELOS_INFO["YOLOv8l (actual)"]["csv"])
    rs = _leer_results(MODELOS_INFO["YOLOv8s (anterior)"]["csv"])
    if vista == "Comparar los dos":
        _comparar_modelos_info(rl, rs)
    else:
        st.table(pd.DataFrame({"Dato": list(MODELOS_INFO[vista]["info"]),
                               "Valor": list(MODELOS_INFO[vista]["info"].values())}).set_index("Dato"))
        r = rl if vista.startswith("YOLOv8l") else rs
        if r is not None:
            _curvas_modelo(r)
        elif vista.startswith("YOLOv8l"):
            st.markdown("#### Resultados en validación")
            k1, k2, k3, k4 = st.columns(4)
            for col, (nom, val) in zip((k1, k2, k3, k4), METRICAS_FINALES.items()):
                col.metric(nom, f"{val:.1%}")
            _ayuda_metricas()
            st.info(f"Las curvas por época se muestran cuando se agrega modelo_info/"
                    f"{MODELOS_INFO[vista]['csv']}.")
        else:
            st.info(f"Falta el archivo modelo_info/{MODELOS_INFO[vista]['csv']} para mostrar las métricas.")

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

# Los filtros de la solapa
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
        archivos = st.multiselect("Imagen", sorted(df["archivo"].unique().tolist()))
        if len(rango) == 2:
            df_f = df_f[(df_f["fecha"].dt.date >= rango[0]) &
                        (df_f["fecha"].dt.date <= rango[1])]
        if archivos:
            df_f = df_f[df_f["archivo"].isin(archivos)]

m = matriz_conteos(df_f) if not df_f.empty else None

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Subir y detectar", "Dashboard", "Historial de sesión", "Gráficos", "Laboratorio",
     "Sobre el modelo"])

#  TAB 1: subir y detectar
with tab1:
    archivo = st.file_uploader("Subí una imagen de cariotipo", type=["jpg", "jpeg", "png"])
    if archivo is not None:
        bytes_imagen = np.frombuffer(archivo.read(), np.uint8)
        imagen = cv2.imdecode(bytes_imagen, cv2.IMREAD_COLOR)

        if st.button("Detectar cromosomas"):
            t0 = time.perf_counter()
            dets = detecciones_normalizadas(
                modelo.detectar(imagen, conf=CONF_UMBRAL, iou=IOU_UMBRAL))
            segundos = time.perf_counter() - t0
            st.session_state.n_runs += 1
            st.session_state.ultimo_resultado = {
                "run": st.session_state.n_runs, "archivo": archivo.name,
                "detecciones": dets, "guardado_id": None, "bytes": bytes_imagen.tobytes(),
                "segundos": segundos}
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

# TAB 2: dashboard 
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

# TAB 3: historial de la sesión 
with tab3:
    st.subheader("Pruebas hechas en esta sesión")
    if st.session_state.historial_pruebas:
        st.dataframe(st.session_state.historial_pruebas)
    else:
        st.info("Todavía no probaste ninguna imagen en esta sesión")

# TAB 4: gráficos
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

# TAB 5: laboratorio 
with tab5:
    panel_laboratorio()

#  TAB 6: sobre el modelo 
with tab6:
    pestana_modelo()