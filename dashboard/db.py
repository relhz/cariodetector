import os
import numpy as np
import pandas as pd

PARES_AUTOSOMICOS = ["A1", "A2", "A3", "B4", "B5", "C6", "C7", "C8", "C9", "C10",
                     "C11", "C12", "D13", "D14", "D15", "E16", "E17", "E18",
                     "F19", "F20", "G21", "G22"]
PARES_ORDEN = PARES_AUTOSOMICOS + ["X", "Y"]

# Ids de clase del modelo (best_24_chromosomes.pt), leídos de sus pesos.
# OJO: el modelo ordena los nombres alfabéticamente (C10, C11, C12 antes de C6...),
# así que NO coincide con PARES_ORDEN.
CLASES_MODELO = ["A1", "A2", "A3", "B4", "B5", "C10", "C11", "C12", "C6", "C7", "C8", "C9",
                 "D13", "D14", "D15", "E16", "E17", "E18", "F19", "F20", "G21", "G22", "X", "Y"]

COLUMNAS = ["persona_id", "muestra_id", "fecha", "imagen_id", "archivo",
            "numero_par", "confianza", "x", "y", "ancho", "alto"]

RUTA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cromosomas.csv")

# Esquema real del repo (scripts_sql/crear_bd): tablas `analisis` y `detecciones`.
# No hay tablas persona/muestra, así que cada análisis es una imagen.
CONSULTA = """
    SELECT a.id AS imagen_id, a.nombre_imagen AS archivo, a.fecha_analisis AS fecha,
           d.nombre_clase AS numero_par, d.confianza,
           d.bbox_x AS x, d.bbox_y AS y, d.bbox_w AS ancho, d.bbox_h AS alto
    FROM detecciones d
    JOIN analisis a ON d.analisis_id = a.id
"""


def nombre_par(nombre):
    """Unifica nombres: 'cromosoma 13' -> 'D13', 'cromosoma X' -> 'X'. 'A1'... queda igual."""
    n = str(nombre).strip()
    if n in PARES_ORDEN:
        return n
    if n.lower().startswith("cromosoma"):
        resto = n.split()[-1]
        if resto.upper() in ("X", "Y"):
            return resto.upper()
        if resto.isdigit() and 1 <= int(resto) <= 22:
            return PARES_AUTOSOMICOS[int(resto) - 1]
    return n


def _conectar():
    """Misma configuración que utils/db_config.py (MySQL local). Se puede
    cambiar con variables de entorno DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME."""
    import mysql.connector
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        database=os.getenv("DB_NAME", "cariodetector"),
        charset="utf8mb4",
        connection_timeout=3,
    )


def _normalizar(df):
    df = df.copy()
    df["numero_par"] = df["numero_par"].map(nombre_par)
    df["fecha"] = pd.to_datetime(df["fecha"])
    for col in ["confianza", "x", "y", "ancho", "alto"]:
        df[col] = pd.to_numeric(df[col])   # MySQL entrega DECIMAL
    return df


def _desde_mysql():
    conexion = _conectar()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(CONSULTA)
        filas = cursor.fetchall()
    finally:
        conexion.close()
    if not filas:
        return pd.DataFrame(columns=COLUMNAS)
    df = pd.DataFrame(filas)
    df["muestra_id"] = df["imagen_id"]   # no hay tabla muestra
    df["persona_id"] = None              # no hay tabla persona
    return df[COLUMNAS]


def guardar_analisis(nombre_imagen, detecciones, ancho, alto, ruta_imagen=None):
    """Guarda un análisis igual que 'Guardar análisis' del Tkinter (tablas analisis y
    detecciones, bbox normalizado centro/ancho/alto). Devuelve el id del análisis."""
    conexion = _conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO analisis (nombre_imagen, total_detecciones, ruta_imagen_original) "
            "VALUES (%s, %s, %s)", (nombre_imagen, len(detecciones), ruta_imagen))
        analisis_id = cursor.lastrowid
        filas = []
        for d in detecciones:
            x1, y1, x2, y2 = d["caja"]
            par = nombre_par(d["clase"])
            clase_id = CLASES_MODELO.index(par) if par in CLASES_MODELO else -1
            filas.append((analisis_id, clase_id, d["clase"], round(float(d["confianza"]), 4),
                          round((x1 + x2) / 2 / ancho, 4), round((y1 + y2) / 2 / alto, 4),
                          round((x2 - x1) / ancho, 4), round((y2 - y1) / alto, 4)))
        if filas:
            cursor.executemany(
                "INSERT INTO detecciones (analisis_id, clase_id, nombre_clase, confianza, "
                "bbox_x, bbox_y, bbox_w, bbox_h) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", filas)
        conexion.commit()
        return analisis_id
    finally:
        conexion.close()


def _demo():
    """Datos inventados, solo para probar el diseño del dashboard."""
    rng = np.random.default_rng(42)
    hoy = pd.Timestamp.today().normalize()
    filas = []
    for img in range(1, 13):
        persona = int(rng.integers(1, 6))
        fecha = hoy - pd.Timedelta(days=int(rng.integers(0, 60)))
        copias = {p: 2 for p in PARES_AUTOSOMICOS}
        if rng.random() < 0.5:
            copias.update({"X": 2, "Y": 0})
        else:
            copias.update({"X": 1, "Y": 1})
        # simulamos errores de clasificación del modelo
        for p in rng.choice(PARES_AUTOSOMICOS, size=int(rng.integers(0, 4)), replace=False):
            copias[str(p)] += int(rng.choice([-1, 1]))
        for par, n in copias.items():
            for _ in range(n):
                filas.append({
                    "persona_id": persona, "muestra_id": img, "fecha": fecha,
                    "imagen_id": img, "archivo": f"demo_{img:02d}.jpg",
                    "numero_par": par,
                    "confianza": float(np.clip(rng.normal(0.62, 0.12), 0.35, 0.98)),
                    "x": int(rng.integers(0, 1000)), "y": int(rng.integers(0, 1000)),
                    "ancho": int(rng.integers(20, 120)), "alto": int(rng.integers(20, 120)),
                })
    return pd.DataFrame(filas, columns=COLUMNAS)


def cargar_datos():
    """Devuelve (dataframe, origen, aviso). origen: 'MySQL', 'CSV' o 'DEMO'."""
    aviso = None
    try:
        df = _desde_mysql()
        if not df.empty:
            return _normalizar(df), "MySQL", None
        aviso = "La base MySQL está vacía: todavía no hay detecciones guardadas."
    except Exception as e:
        aviso = f"No se pudo conectar a MySQL: {e}"
    if os.path.exists(RUTA_CSV):
        return _normalizar(pd.read_csv(RUTA_CSV)), "CSV", aviso
    return _normalizar(_demo()), "DEMO", aviso