"""Constantes y catálogos compartidos por todas las interfaces."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PARES_AUTOSOMICOS = [
    "A1", "A2", "A3", "B4", "B5", "C6", "C7", "C8", "C9", "C10",
    "C11", "C12", "D13", "D14", "D15", "E16", "E17", "E18",
    "F19", "F20", "G21", "G22",
]
PARES_ORDEN = PARES_AUTOSOMICOS + ["X", "Y"]

# Orden canónico usado por el proyecto (pares 1-22 y luego X/Y).
CLASES_CROMOSOMA = PARES_ORDEN

# Ids de clase del modelo (best_24_chromosomes.pt), leídos de sus pesos.
# OJO: el modelo ordena los nombres alfabéticamente (C10, C11, C12 antes de C6...),
# así que NO coincide con PARES_ORDEN. El detector devuelve los nombres, pero se
# mantiene esta lista para mapear ids de clase cuando haga falta.
CLASES_MODELO = [
    "A1", "A2", "A3", "B4", "B5", "C10", "C11", "C12", "C6", "C7", "C8", "C9",
    "D13", "D14", "D15", "E16", "E17", "E18", "F19", "F20", "G21", "G22", "X", "Y",
]

# Umbrales de detección y revisión. Los usan tanto Tkinter como el dashboard.
CONF_UMBRAL = 0.25      # confianza mínima para aceptar una detección
IOU_UMBRAL = 0.70       # solapamiento máximo entre cajas (evita duplicados)
CONF_REVISION = 0.50    # por debajo de esta confianza, la detección se marca para revisar

RUTA_PESOS = BASE_DIR / "models" / "best_24_chromosomes.pt"
CARPETA_IMAGENES = BASE_DIR / "assets" / "imagenes_analizadas"
RUTA_MODELO_INFO = BASE_DIR / "models" / "metricas"

# Colores: el mismo significado en toda la aplicación.
NORMAL = "Normal (2 copias)"
DE_MAS = "De más (3 o más)"
DE_MENOS = "De menos (0 o 1)"
SEXUAL = "X / Y (según sexo)"
ESTADOS = [NORMAL, DE_MAS, DE_MENOS, SEXUAL]
COLORES = ["#2E7D32", "#C62828", "#D97706", "#78909C"]
AZUL = "#4C78A8"

CAT_SIN = "Sin alertas"
CAT_MAS = "Algún par de más"
CAT_MENOS = "Algún par de menos"
CAT_AMBAS = "Pares de más y de menos"
CATEGORIAS_IMG = [CAT_SIN, CAT_MAS, CAT_MENOS, CAT_AMBAS]
COLORES_IMG = [COLORES[0], COLORES[1], COLORES[2], "#8E24AA"]

ETIQUETA_SEXUALES = "Sexuales · X, Y"


def _grupos():
    grupos = {}
    for par in PARES_AUTOSOMICOS:
        grupos.setdefault(par[0], []).append(par)
    etiquetas = {}
    for grupo, pares in grupos.items():
        numeros = [int(par[1:]) for par in pares]
        etiquetas[grupo] = f"Grupo {grupo} · pares {min(numeros)}–{max(numeros)}"
    return grupos, etiquetas


GRUPOS, ETIQUETA_GRUPO = _grupos()
ORDEN_FILAS = [ETIQUETA_GRUPO[grupo] for grupo in GRUPOS] + [ETIQUETA_SEXUALES]
