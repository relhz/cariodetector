"""Generación del informe HTML descargable."""

import base64
import html
from datetime import datetime

import cv2

from .constantes import DE_MAS, DE_MENOS, NORMAL, PARES_ORDEN, SEXUAL
from .detecciones import _orden_par, estado_par


def png_base64(imagen, ancho_max=1200):
    alto, ancho = imagen.shape[:2]
    if ancho > ancho_max:
        imagen = cv2.resize(imagen, (ancho_max, int(alto * ancho_max / ancho)))
    ok, buffer = cv2.imencode(".png", imagen)
    return base64.b64encode(buffer.tobytes()).decode("ascii") if ok else None


def informe_html(nombre, conteo, motivos, filas, png_b64=None, parametros=None, notas=None):
    esc = html.escape
    etiquetas = {
        NORMAL: ("Normal", "#E8F5E9"),
        DE_MAS: ("De más", "#FFEBEE"),
        DE_MENOS: ("De menos", "#FFF3E0"),
        SEXUAL: ("Según sexo", "#ECEFF1"),
    }

    pares = ""
    for par in PARES_ORDEN:
        cantidad = conteo.get(par, 0)
        texto, fondo = etiquetas[estado_par(par, cantidad)]
        pares += (
            f'<tr style="background:{fondo}"><td>{par}</td>'
            f"<td>{cantidad}</td><td>{texto}</td></tr>"
        )

    detecciones = "".join(
        f"<tr><td>{esc(str(clase))}</td><td>{confianza:.2f}</td></tr>"
        for clase, confianza in sorted(filas, key=lambda fila: (_orden_par(fila[0]), -fila[1]))
    )

    if motivos:
        caja = (
            '<div class="caja rev"><b>Revisar</b><ul>'
            + "".join(f"<li>{esc(motivo)}</li>" for motivo in motivos)
            + "</ul></div>"
        )
    else:
        caja = '<div class="caja ok"><b>Sin motivos de revisión</b> según los criterios del sistema.</div>'

    imagen = (
        f'<img src="data:image/png;base64,{png_b64}" alt="Detecciones">'
        if png_b64 else ""
    )
    parametros_html = "".join(
        f"<li>{esc(clave)}: {esc(str(valor))}</li>" for clave, valor in (parametros or {}).items()
    )
    notas_html = "".join(f"<p>{esc(nota)}</p>" for nota in (notas or []))

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
{caja}{notas_html}{imagen}
<h2>Conteo por par</h2>
<p>Se esperan 2 copias en cada par del 1 al 22. X e Y se interpretan según el sexo.</p>
<table><tr><th>Par</th><th>Copias detectadas</th><th>Estado</th></tr>{pares}</table>
<h2>Detecciones</h2><table><tr><th>Clase</th><th>Confianza</th></tr>{detecciones}</table>
<h2>Parámetros</h2><ul>{parametros_html}</ul>
<p class="aviso">Herramienta de apoyo, no de diagnóstico. Toda alerta debe ser validada por un
profesional. Solo evalúa alteraciones numéricas (cantidad de copias por par), no estructurales.
El modelo puede confundir pares de tamaño y forma parecidos y cromosomas superpuestos.</p>
</body></html>"""
