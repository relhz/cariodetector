"""Componentes visuales reutilizables del dashboard (Streamlit)."""

import base64
import html
import json

import cv2
import streamlit as st


def explicar(que, como):
    """Texto breve para explicar qué muestra un gráfico y cómo leerlo."""
    st.caption(f"**Qué muestra:** {que}  \n**Cómo leerlo:** {como}")


def mostrar_origen(origen, aviso):
    """Indica de dónde salieron los datos que se están mostrando."""
    if aviso:
        st.warning(aviso)
    if origen == "DEMO":
        st.error(
            "DATOS DE DEMO: son inventados, solo para probar el diseño. "
            "No son resultados reales."
        )
    elif origen == "CSV":
        st.info("Datos leídos de un CSV exportado de la base.")
    else:
        st.success("Datos en vivo desde MySQL.")


def mostrar_semaforo(motivos):
    """Semáforo de revisión de una imagen."""
    if not motivos:
        st.success(
            "🟢 **OK**: sin motivos de revisión según los criterios del sistema. "
            "Igual debe ser validado por un profesional."
        )
    else:
        st.warning("🟠 **Revisar**\n\n" + "\n".join(f"- {m}" for m in motivos))


def visor_zoom(original, analizada, alto=520, titulos=("Imagen original", "Imagen analizada"), foco=None):
    """Visor con zoom y desplazamiento sincronizado para dos imágenes."""
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
    html_vis = (
        pagina.replace("__ALTO__", str(alto))
        .replace("__A__", _b64(original))
        .replace("__B__", _b64(analizada))
        .replace("__T1__", html.escape(titulos[0]))
        .replace("__T2__", html.escape(titulos[1]))
        .replace("__FOCO__", foco_js)
    )
    if hasattr(st, "iframe"):
        st.iframe(html_vis, height=alto + 90)
    else:
        st.components.v1.html(html_vis, height=alto + 90)
