"""Dashboard web de CarioDetector.

Toda la lógica de detección, conteo, dibujo, base de datos e informes vive en
`nucleo/`. Los gráficos viven en `graficos/`. Este archivo solo arma la página.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import time

import altair as alt
import cv2
import numpy as np
import pandas as pd
import streamlit as st

from dashboard.componentes import explicar, mostrar_origen, mostrar_semaforo, visor_zoom
from graficos import (
    cariograma,
    comparar_map,
    comparar_perdida,
    confusiones,
    curva_iou,
    histograma_confianza,
    imagenes_por_dia,
    img_alertas,
    mapa_calor,
    metricas_por_epoca,
    pares_que_fallan,
    perdida_por_epoca,
    total_por_imagen,
)
from nucleo.analisis_imagen import analizar
from nucleo.constantes import (
    COLORES,
    CONF_REVISION,
    CONF_UMBRAL,
    IOU_UMBRAL,
    PARES_AUTOSOMICOS,
    PARES_ORDEN,
    RUTA_PESOS,
)
from nucleo.db import (
    cargar_datos,
    cargar_estudio,
    cargar_revision,
    guardar_revision,
    historial_estudios,
)
from nucleo.detecciones import (
    contar,
    matriz_conteos,
    motivos_revision,
    orden_par,
    resumen_deteccion,
    sugerir_cariotipo,
)
from nucleo.dibujo import cariograma_recortes, dibujar
from nucleo.guardado import guardar_resultado
from nucleo.informe import informe_html, png_base64
from nucleo.modelo import DetectorCromosomas
from nucleo.modelo_info import (
    INFO_MODELO,
    INFO_V8S,
    METRICAS_FINALES,
    MODELOS_INFO,
    leer_results,
    mejor_epoca,
)

alt.data_transformers.disable_max_rows()

st.set_page_config(page_title="CarioDetector", layout="wide")
st.title("🧬 CarioDetector")

if "historial_pruebas" not in st.session_state:
    st.session_state.historial_pruebas = []
if "n_runs" not in st.session_state:
    st.session_state.n_runs = 0


@st.cache_resource
def detector_compartido():
    """Carga el modelo una sola vez, y solo cuando hace falta detectar."""
    return DetectorCromosomas(RUTA_PESOS)


@st.cache_data(ttl=60)
def datos_cacheados():
    return cargar_datos()


@st.cache_resource
def cargar_detector(ruta):
    return DetectorCromosomas(ruta)


@st.cache_data(ttl=60)
def _revision_cacheada():
    return cargar_revision()


df, origen, aviso = datos_cacheados()


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
    resumen = resumen_deteccion(dets)
    conteo = resumen["conteo"]
    motivos = resumen["motivos"]
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
                  for p, n in sorted(conteo.items(), key=lambda t: orden_par(t[0]))])

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
            u["guardado_id"], _ = guardar_resultado(
                u["archivo"],
                dets,
                descartes,
                imagen=imagen,
                imagen_anotada=dibujada,
                bytes_imagen=u.get("bytes"),
                guardar_archivos=True,
                revisado=revisado,
                observacion=observ,
            )
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
         "Pesos": str(RUTA_PESOS)}, notas)
    d1, d2 = st.columns(2)
    d1.download_button("Descargar informe (HTML)", informe.encode("utf-8"),
                       f"informe_{Path(u['archivo']).stem}.html", "text/html",
                       key=f"dl_html_{u['run']}")
    d2.download_button("Descargar detecciones (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                       f"detecciones_{Path(u['archivo']).stem}.csv", "text/csv",
                       key=f"dl_csv_{u['run']}")
    st.caption("El informe se abre en el navegador; desde ahí se puede imprimir o guardar como PDF.")


def panel_comparar_modelos(imagen, archivo, conf, iou):
    st.divider()
    st.subheader("Comparar dos modelos")
    explicar("cómo detecta cada modelo la misma imagen: cantidad, pares con cantidad distinta de 2, "
             "confianza y tiempo.",
             "elegí dos archivos de pesos (.pt). Mismos valores de conf e iou para los dos, así la "
             "comparación es justa.")
    ruta_actual = str(RUTA_PESOS)
    pesos = sorted(str(p).replace("\\", "/") for p in Path(RUTA_PESOS).parent.glob("*.pt"))
    if len(pesos) < 2:
        st.info("Para comparar hacen falta al menos dos archivos .pt en la carpeta models/ "
                "(por ejemplo, el YOLOv8s anterior junto al YOLOv8l actual).")
        return
    c1, c2 = st.columns(2)
    ia = pesos.index(ruta_actual) if ruta_actual in pesos else 0
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
            r = analizar(imagen, det, conf=conf, iou=iou)
            res.append({"ruta": ruta, "dets": r["detecciones"],
                        "seg": time.perf_counter() - t0})
        st.session_state.lab_comp = {"archivo": archivo, "a": a, "b": b, "conf": conf, "iou": iou,
                                     "res": res}
    comp = st.session_state.get("lab_comp")
    if not comp or comp["archivo"] != archivo or (comp["a"], comp["b"]) != (a, b):
        return
    filas, imgs = [], []
    for r in comp["res"]:
        resumen = resumen_deteccion(r["dets"])
        pares, n_baja = resumen["pares"], resumen["n_baja"]
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
        dets = analizar(imagen, detector_compartido(), conf=conf, iou=iou)["detecciones"]
        st.session_state.lab_uno = {"archivo": subida.name, "conf": conf, "iou": iou, "dets": dets}
    if b2.button("Comparar varios valores de IoU"):
        filas = []
        barra = st.progress(0.0, text="Detectando…")
        valores = [0.3, 0.4, 0.5, 0.6, 0.7]
        detector = detector_compartido()
        for i, v in enumerate(valores):
            r = analizar(imagen, detector, conf=conf, iou=v)
            filas.append({"IoU": v, "Cromosomas detectados": len(r["detecciones"]),
                          "Pares con cantidad distinta de 2": r["pares"],
                          f"Detecciones con confianza < {CONF_REVISION}": r["n_baja"]})
            barra.progress((i + 1) / len(valores), text="Detectando…")
        barra.empty()
        st.session_state.lab_barrido = {"archivo": subida.name, "conf": conf,
                                        "tabla": pd.DataFrame(filas)}

    uno = st.session_state.get("lab_uno")
    if uno and uno["archivo"] == subida.name:
        st.markdown(f"**Resultado con conf={uno['conf']:.2f} e iou={uno['iou']:.2f}**")
        dets = [{**d, "clase_final": d["clase_modelo"]} for d in uno["dets"]]
        resumen_uno = resumen_deteccion(uno["dets"])
        conteo, n_baja, pares = (
            resumen_uno["conteo"], resumen_uno["n_baja"], resumen_uno["pares"]
        )
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
        st.altair_chart(curva_iou(t))
        st.caption("La línea gris marca 46, el total esperado en una célula sin alteraciones "
                   "numéricas. Elegir el IoU que más se acerque sin generar duplicados.")

    panel_comparar_modelos(imagen, subida.name, conf, iou)


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


def _curvas_modelo(r):
    """Resultados en validación y curvas de un entrenamiento (r = results.csv)."""
    mejor = mejor_epoca(r)
    st.markdown(f"#### Resultados en validación (mejor época: {int(mejor['epoch'])})")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Precisión", f"{mejor['metrics/precision(B)']:.1%}")
    k2.metric("Recall", f"{mejor['metrics/recall(B)']:.1%}")
    k3.metric("mAP@50", f"{mejor['metrics/mAP50(B)']:.1%}")
    k4.metric("mAP@50-95", f"{mejor['metrics/mAP50-95(B)']:.1%}")
    _ayuda_metricas()
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Métricas por época**")
        explicar("cómo mejoró el modelo durante el entrenamiento.",
                 "las curvas suben y se estabilizan; la línea gris es la mejor época, la "
                 "que se guardó como pesos finales.")
        st.altair_chart(metricas_por_epoca(r))
    with g2:
        st.markdown("**Error de las cajas por época**")
        explicar("qué tan bien ubica las cajas (menos es mejor).",
                 "si la curva de validación se separa hacia arriba de la de entrenamiento, hay "
                 "sobreajuste; si se mantienen juntas, el modelo generaliza.")
        st.altair_chart(perdida_por_epoca(r))


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
        st.info("Para comparar las métricas faltan en models/metricas/: " + ", ".join(faltan))
        return
    ml = mejor_epoca(rl)
    ms = mejor_epoca(rs)
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
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**mAP@50-95 por época**")
        explicar("la métrica más exigente, época por época, para los dos modelos.",
                 "la curva más alta y estable es la del modelo que mejor ubica los cromosomas.")
        st.altair_chart(comparar_map(larga))
    with g2:
        st.markdown("**Error de las cajas en validación**")
        explicar("qué tan bien ubica las cajas cada modelo (menos es mejor).",
                 "una curva más baja significa cajas mejor ajustadas.")
        st.altair_chart(comparar_perdida(larga))


def pestana_modelo():
    st.subheader("Sobre el modelo")
    vista = st.radio("Qué ver", ["YOLOv8l (actual)", "YOLOv8s (anterior)", "Comparar los dos"],
                     horizontal=True, key="vista_modelo", label_visibility="collapsed")
    st.markdown("Los detectores son modelos **YOLOv8** que partieron de pesos preentrenados con COCO "
                "y se reentrenaron (*fine-tuning*) con imágenes de cariotipos para reconocer los 24 "
                "tipos de cromosoma. Lo que sigue describe cómo fueron entrenados y qué tan bien funcionan.")
    rl = leer_results(MODELOS_INFO["YOLOv8l (actual)"]["csv"])
    rs = leer_results(MODELOS_INFO["YOLOv8s (anterior)"]["csv"])
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
            st.info(f"Las curvas por época se muestran cuando se agrega models/metricas/"
                    f"{MODELOS_INFO[vista]['csv']}.")
        else:
            st.info(f"Falta el archivo models/metricas/{MODELOS_INFO[vista]['csv']} para mostrar las métricas.")

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
            st.altair_chart(confusiones(top))
        st.caption("Se calcula solo con los análisis marcados como revisados por un profesional.")

    st.markdown("#### Limitaciones")
    st.markdown("""
- Puede **confundir pares de tamaño y forma parecidos**, sobre todo dentro de un mismo grupo
  (el detalle de las confusiones está en la evaluación de modelos del equipo).
- Puede contar mal los **cromosomas superpuestos o cruzados**.
- Solo evalúa **alteraciones numéricas**, no estructurales.
- Es una herramienta de **apoyo**: toda alerta debe ser validada por un profesional.
""")


def panel_revisar_estudios():
    """Revisión y corrección de estudios ya guardados en MySQL."""
    st.subheader("Revisar estudios guardados")
    st.caption("Corregí las clases asignadas, completá el resultado y guardá la revisión. "
               "Queda registrada igual que desde la aplicación de escritorio.")
    try:
        estudios = historial_estudios()
    except Exception as e:
        st.error(f"No se pudo cargar el historial desde MySQL: {e}")
        return
    if not estudios:
        st.info("No hay estudios guardados para revisar.")
        return

    def etiqueta(estudio):
        fecha = estudio.get("fecha_analisis")
        fecha_txt = fecha.strftime("%Y-%m-%d %H:%M") if hasattr(fecha, "strftime") else str(fecha)
        return f"#{estudio['id_estudio']} · {estudio['imagen_original']} · {fecha_txt}"

    opciones = {etiqueta(estudio): estudio for estudio in estudios}
    elegido = st.selectbox("Estudio", list(opciones), key="rev_estudio")
    id_estudio = opciones[elegido]["id_estudio"]

    try:
        datos = cargar_estudio(id_estudio)
    except Exception as e:
        st.error(f"No se pudo cargar el estudio #{id_estudio}: {e}")
        return

    cromosomas = datos["cromosomas"]
    if not cromosomas:
        st.warning("El estudio no tiene cromosomas guardados.")
        return

    base = pd.DataFrame({
        "ID": [c["id_cromosoma"] for c in cromosomas],
        "Clase detectada": [c["clase_detectada"] for c in cromosomas],
        "Clase asignada": [
            c["cromosoma_asignado"] or c["clase_detectada"] for c in cromosomas
        ],
        "Confianza": [
            round(float(c["confianza_asignada"] or 0), 3) for c in cromosomas
        ],
    })
    opciones_clase = list(PARES_ORDEN) + sorted(
        set(base["Clase detectada"]) - set(PARES_ORDEN)
    )
    editado = st.data_editor(
        base, hide_index=True, key=f"rev_editor_{id_estudio}",
        disabled=["ID", "Clase detectada", "Confianza"],
        column_config={
            "Clase asignada": st.column_config.SelectboxColumn(
                "Clase asignada", options=opciones_clase, required=True),
        },
    )

    resultado = datos["resultado"] or {}
    conteo_actual = contar(list(editado["Clase asignada"]))
    st.caption(f"Conteo actual: {sum(conteo_actual.values())} cromosomas · "
               f"{sum(1 for p in PARES_AUTOSOMICOS if conteo_actual.get(p, 0) != 2)} "
               "par(es) autosómico(s) distinto(s) de 2.")

    clave_car = f"rev_cariotipo_{id_estudio}"
    if clave_car not in st.session_state:
        st.session_state[clave_car] = resultado.get("cariotipo") or ""

    if st.button("Sugerir cariotipo", key=f"rev_sugerir_{id_estudio}"):
        propuesto = sugerir_cariotipo(list(editado["Clase asignada"]))
        if propuesto:
            st.session_state[clave_car] = propuesto
            st.rerun()
        else:
            st.warning("No se pudo sugerir un cariotipo con esas asignaciones.")

    cariotipo = st.text_input("Cariotipo", key=clave_car, max_chars=30)

    clave_alt = f"rev_alteracion_{id_estudio}"
    if clave_alt not in st.session_state:
        st.session_state[clave_alt] = resultado.get("alteracion") or ""
    alteracion = st.text_input("Alteración", key=clave_alt, max_chars=100)

    clave_obs = f"rev_observacion_{id_estudio}"
    if clave_obs not in st.session_state:
        st.session_state[clave_obs] = resultado.get("observacion") or ""
    observacion = st.text_area("Observación", key=clave_obs)

    if st.button("Guardar revisión", type="primary", key=f"rev_guardar_{id_estudio}"):
        if not cariotipo.strip():
            st.warning("Ingresá un cariotipo o usá «Sugerir cariotipo».")
        else:
            asignaciones = {
                int(fila["ID"]): fila["Clase asignada"]
                for _, fila in editado.iterrows()
            }
            try:
                guardar_revision(
                    id_estudio,
                    asignaciones,
                    cariotipo.strip(),
                    alteracion.strip() or None,
                    observacion.strip() or None,
                )
                st.cache_data.clear()
                st.success(f"Estudio #{id_estudio} guardado como finalizado.")
            except Exception as e:
                st.error(f"No se pudo guardar la revisión: {e}")


# Filtros de la barra lateral
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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["Subir y detectar", "Dashboard", "Historial de sesión", "Gráficos", "Laboratorio",
     "Sobre el modelo", "Revisar estudios"])

#  TAB 1: subir y detectar
with tab1:
    archivo = st.file_uploader("Subí una imagen de cariotipo", type=["jpg", "jpeg", "png"])
    if archivo is not None:
        bytes_imagen = np.frombuffer(archivo.read(), np.uint8)
        imagen = cv2.imdecode(bytes_imagen, cv2.IMREAD_COLOR)

        if st.button("Detectar cromosomas"):
            t0 = time.perf_counter()
            r = analizar(imagen, detector_compartido())
            dets = r["detecciones"]
            segundos = time.perf_counter() - t0
            st.session_state.n_runs += 1
            st.session_state.ultimo_resultado = {
                "run": st.session_state.n_runs, "archivo": archivo.name,
                "detecciones": dets, "guardado_id": None, "bytes": bytes_imagen.tobytes(),
                "segundos": segundos}
            conteo0 = r["conteo"]
            motivos0 = r["motivos"]
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
    mostrar_origen(origen, aviso)
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
    mostrar_origen(origen, aviso)
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

        # 3 y 4. alerta + histograma
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("3 · Imágenes con y sin alertas")
            explicar("cuántas imágenes salieron sin alertas y cuántas con algún par de más o de menos.",
                     "cada imagen cuenta una sola vez; X e Y no se incluyen.")
            st.altair_chart(img_alertas(m))
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

#  TAB 7: revisar estudios guardados
with tab7:
    panel_revisar_estudios()
