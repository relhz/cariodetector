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

# Esquema oficial (scripts_sql/crear_bd.sql, base `cariotipos`): estudios -> cromosomas ->
# clasificaciones. La clase final es la de `clasificaciones` (la que quedó tras la revisión);
# si un cromosoma todavía no tiene clasificación, se usa la que detectó el modelo.
# x, y, ancho y alto son píxeles de la imagen original; x,y es la esquina SUPERIOR IZQUIERDA.
# No hay tablas persona/muestra, así que cada estudio es una imagen.
CONSULTA = """
    SELECT e.id_estudio AS imagen_id, e.imagen_original AS archivo,
           e.fecha_analisis AS fecha,
           COALESCE(cl.cromosoma_asignado, c.clase_detectada) AS numero_par,
           c.confianza, c.x, c.y, c.ancho, c.alto
    FROM cromosomas c
    JOIN estudios e ON e.id_estudio = c.id_estudio
    LEFT JOIN clasificaciones cl ON cl.id_cromosoma = c.id_cromosoma
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
        database=os.getenv("DB_NAME", "cariotipos"),
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


CREAR_CORRECCIONES = """
    CREATE TABLE IF NOT EXISTS correcciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_estudio INT NOT NULL,
        id_cromosoma INT NULL,
        clase_modelo VARCHAR(50) NOT NULL,
        clase_final VARCHAR(50) NULL,
        confianza DECIMAL(5,4) NOT NULL,
        tipo VARCHAR(10) NOT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_estudio) REFERENCES estudios(id_estudio) ON DELETE CASCADE
    ) ENGINE=InnoDB
"""


def guardar_analisis(nombre_imagen, detecciones, ancho=None, alto=None, ruta_imagen=None,
                     observaciones=None, imagen_resultado=None, resultado=None):
    """Guarda un análisis en la base `cariotipos` usando los procedimientos del script
    (sp_crear_estudio, sp_carga_cromosomaDet, sp_guardar_clasificacion, sp_finalizar_estudio y,
    si hay revisión, sp_guardar_resultado).

    Cada elemento de `detecciones` es un dict con caja (x1, y1, x2, y2 en píxeles),
    clase_modelo, clase_final, confianza y descartada (bool).
    - `cromosomas.clase_detectada` guarda lo que dijo el modelo y `clasificaciones` la clase final.
    - Los cromosomas descartados NO se cargan en `cromosomas` (no son cromosomas), pero quedan
      anotados en la tabla propia `correcciones`, igual que los cambios de etiqueta.
    - `resultado` (opcional): dict con cariotipo, alteracion y observacion; solo se pasa cuando un
      profesional confirmó la revisión.
    `ancho` y `alto` ya no se usan (las cajas se guardan en píxeles); se aceptan por compatibilidad.
    Devuelve el id del estudio."""
    conexion = _conectar()
    try:
        cursor = conexion.cursor()
        conservadas = [d for d in detecciones if not d.get("descartada")]
        hay_correcciones = any(d.get("descartada") or d["clase_final"] != d["clase_modelo"]
                               for d in detecciones)
        if hay_correcciones:
            cursor.execute(CREAR_CORRECCIONES)   # DDL antes de la transacción
        # callproc devuelve la lista de argumentos; el parámetro OUT viene con su valor.
        id_estudio = cursor.callproc("sp_crear_estudio",
                                     (nombre_imagen, observaciones, 0))[2]
        correcciones = []
        for d in detecciones:
            confianza = round(float(d["confianza"]), 4)
            if d.get("descartada"):
                correcciones.append((id_estudio, None, d["clase_modelo"], None,
                                     confianza, "descarte"))
                continue
            x1, y1, x2, y2 = (int(round(v)) for v in d["caja"])
            id_cromosoma = cursor.callproc(
                "sp_carga_cromosomaDet",
                (id_estudio, d["clase_modelo"], x1, y1, x2 - x1, y2 - y1, confianza, 0))[7]
            cursor.callproc("sp_guardar_clasificacion",
                            (id_cromosoma, d["clase_final"], confianza))
            if d["clase_final"] != d["clase_modelo"]:
                correcciones.append((id_estudio, id_cromosoma, d["clase_modelo"],
                                     d["clase_final"], confianza, "cambio"))
        cursor.callproc("sp_finalizar_estudio",
                        (id_estudio, len(conservadas), imagen_resultado))
        if resultado:
            cursor.callproc("sp_guardar_resultado",
                            (id_estudio, resultado["cariotipo"], resultado["alteracion"],
                             resultado.get("observacion")))
        if correcciones:
            cursor.executemany(
                "INSERT INTO correcciones (id_estudio, id_cromosoma, clase_modelo, "
                "clase_final, confianza, tipo) VALUES (%s, %s, %s, %s, %s, %s)", correcciones)
        conexion.commit()
        return id_estudio
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def cargar_revision():
    """Datos de los estudios revisados por un profesional (observaciones que empiezan con
    'Revisado'): cuántos son, cuántas detecciones tienen y qué correcciones se hicieron.
    Devuelve None si no hay conexión a la base."""
    try:
        conexion = _conectar()
    except Exception:
        return None
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS n, COALESCE(SUM(cantidad_cromosomas), 0) AS dets "
                       "FROM estudios WHERE observaciones LIKE 'Revisado%'")
        base = cursor.fetchone()
        try:
            cursor.execute("SELECT c.clase_modelo, c.clase_final, c.tipo FROM correcciones c "
                           "JOIN estudios e ON e.id_estudio = c.id_estudio "
                           "WHERE e.observaciones LIKE 'Revisado%'")
            filas = cursor.fetchall()
        except Exception:
            filas = []     # la tabla todavía no existe
        corr = pd.DataFrame(filas, columns=["clase_modelo", "clase_final", "tipo"])
        return {"analisis": int(base["n"]), "detecciones": int(base["dets"]),
                "correcciones": corr}
    except Exception:
        return None
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
                    "confianza": float(np.clip(rng.normal(0.84, 0.12), 0.35, 0.99)),
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