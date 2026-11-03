"""Acceso único a MySQL para la aplicación de escritorio y el dashboard."""

import json
import os

import numpy as np
import pandas as pd

from .detecciones import normalizar_clase
from .constantes import PARES_AUTOSOMICOS, PARES_ORDEN

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "cariotipos",
    "charset": "utf8mb4",
    "autocommit": False,
}

COLUMNAS = [
    "persona_id", "muestra_id", "fecha", "imagen_id", "archivo",
    "numero_par", "confianza", "x", "y", "ancho", "alto",
]

RUTA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "cromosomas.csv")

# Esquema oficial (scripts_sql/crear_bd.sql, base `cariotipos`): estudios ->
# cromosomas -> clasificaciones. La clase final es la de `clasificaciones` (la
# que quedó tras la revisión); si un cromosoma todavía no tiene clasificación,
# se usa la que detectó el modelo.
CONSULTA = """
    SELECT e.id_estudio AS imagen_id, e.imagen_original AS archivo,
           e.fecha_analisis AS fecha,
           COALESCE(cl.cromosoma_asignado, c.clase_detectada) AS numero_par,
           c.confianza, c.x, c.y, c.ancho, c.alto
    FROM cromosomas c
    JOIN estudios e ON e.id_estudio = c.id_estudio
    LEFT JOIN clasificaciones cl ON cl.id_cromosoma = c.id_cromosoma
"""

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


def _config_conexion():
    return {
        **DB_CONFIG,
        "host": os.getenv("DB_HOST", DB_CONFIG["host"]),
        "port": int(os.getenv("DB_PORT", str(DB_CONFIG["port"]))),
        "user": os.getenv("DB_USER", DB_CONFIG["user"]),
        "password": os.getenv("DB_PASSWORD", DB_CONFIG["password"]),
        "database": os.getenv("DB_NAME", DB_CONFIG["database"]),
    }


def _conectar():
    import mysql.connector

    try:
        return mysql.connector.connect(**_config_conexion())
    except Exception as e:
        raise Exception(f"Error conectando a MySQL: {e}") from e


# Alias público para las pantallas que necesitan consultar tablas sueltas.
obtener_conexion = _conectar


def probar_conexion():
    try:
        conexion = _conectar()
        conexion.close()
        return True, "Conexión a MySQL exitosa"
    except Exception as e:
        return False, str(e)


def _normalizar(df):
    df = df.copy()
    df["numero_par"] = df["numero_par"].map(normalizar_clase)
    df["fecha"] = pd.to_datetime(df["fecha"])
    for columna in ["confianza", "x", "y", "ancho", "alto"]:
        df[columna] = pd.to_numeric(df[columna])
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
    df["muestra_id"] = df["imagen_id"]  # no hay tabla muestra
    df["persona_id"] = None             # no hay tabla persona
    return df[COLUMNAS]


def guardar_analisis(nombre_imagen, detecciones, ancho=None, alto=None, ruta_imagen=None,
                     observaciones=None, imagen_resultado=None, resultado=None):
    """Guarda un análisis en la base `cariotipos`.

    - sp_guardar_analisis_completo: crea el estudio y carga los cromosomas con
      la clase que dijo el modelo.
    - Si el profesional cambió alguna etiqueta, actualiza
      `clasificaciones.cromosoma_asignado`.
    - Si confirmó la revisión, `sp_guardar_revision_estudio` guarda el
      resultado y deja el estudio como FINALIZADO.

    Los cromosomas descartados no se cargan en `cromosomas`, pero quedan
    anotados en la tabla `correcciones`.
    """
    from .detecciones import preparar_detecciones

    detecciones = preparar_detecciones(detecciones)

    conexion = _conectar()
    try:
        cursor = conexion.cursor()

        conservadas = [det for det in detecciones if not det.get("descartada")]
        hay_correcciones = any(
            det.get("descartada") or det["clase_final"] != det["clase_modelo"]
            for det in detecciones
        )
        if hay_correcciones:
            cursor.execute(CREAR_CORRECCIONES)

        filas = []
        for det in conservadas:
            caja = det.get("caja")
            if caja is None or len(caja) < 4:
                continue

            x1, y1, x2, y2 = (int(round(float(v))) for v in caja[:4])
            filas.append({
                "clase": det["clase_modelo"],
                "x": x1,
                "y": y1,
                "ancho": x2 - x1,
                "alto": y2 - y1,
                "confianza": round(float(det["confianza"]), 4),
            })

        id_estudio = cursor.callproc(
            "sp_guardar_analisis_completo",
            (nombre_imagen, imagen_resultado, json.dumps(filas, ensure_ascii=False), 0),
        )[3]

        cursor.execute(
            "SELECT id_cromosoma FROM cromosomas WHERE id_estudio = %s "
            "ORDER BY id_cromosoma",
            (id_estudio,),
        )
        ids = [fila[0] for fila in cursor.fetchall()]
        if len(ids) != len(conservadas):
            raise RuntimeError(
                f"Se esperaban {len(conservadas)} cromosomas y la base devolvió {len(ids)}"
            )

        cambios, correcciones = [], []
        for det, id_cromosoma in zip(conservadas, ids):
            if det["clase_final"] != det["clase_modelo"]:
                cambios.append((det["clase_final"], id_cromosoma))
                correcciones.append((
                    id_estudio, id_cromosoma, det["clase_modelo"],
                    det["clase_final"], round(float(det["confianza"]), 4), "cambio",
                ))
        for det in detecciones:
            if det.get("descartada"):
                correcciones.append((
                    id_estudio, None, det["clase_modelo"], None,
                    round(float(det["confianza"]), 4), "descarte",
                ))

        if cambios:
            cursor.executemany(
                "UPDATE clasificaciones SET cromosoma_asignado = %s "
                "WHERE id_cromosoma = %s",
                cambios,
            )
        if observaciones:
            cursor.execute(
                "UPDATE estudios SET observaciones = %s WHERE id_estudio = %s",
                (observaciones, id_estudio),
            )
        if resultado:
            cursor.callproc(
                "sp_guardar_revision_estudio",
                (id_estudio, None, resultado["cariotipo"], resultado["alteracion"],
                 resultado.get("observacion")),
            )
        if correcciones:
            cursor.executemany(
                "INSERT INTO correcciones (id_estudio, id_cromosoma, clase_modelo, "
                "clase_final, confianza, tipo) VALUES (%s, %s, %s, %s, %s, %s)",
                correcciones,
            )

        conexion.commit()
        return id_estudio
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def cargar_revision():
    """Datos de los estudios revisados por un profesional."""
    try:
        conexion = _conectar()
    except Exception:
        return None

    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(cantidad_cromosomas), 0) AS dets "
            "FROM estudios WHERE observaciones LIKE 'Revisado%'"
        )
        base = cursor.fetchone()
        try:
            cursor.execute(
                "SELECT c.clase_modelo, c.clase_final, c.tipo FROM correcciones c "
                "JOIN estudios e ON e.id_estudio = c.id_estudio "
                "WHERE e.observaciones LIKE 'Revisado%'"
            )
            filas = cursor.fetchall()
        except Exception:
            filas = []  # la tabla todavía no existe

        correcciones = pd.DataFrame(filas, columns=["clase_modelo", "clase_final", "tipo"])
        return {
            "analisis": int(base["n"]),
            "detecciones": int(base["dets"]),
            "correcciones": correcciones,
        }
    except Exception:
        return None
    finally:
        conexion.close()


def historial_estudios(limite=1000):
    conexion = _conectar()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_estudio, imagen_original, fecha_analisis, total_detecciones, "
            "confianza_promedio, estado, tipos, cariotipo, alteracion "
            "FROM vista_resumen_estudios ORDER BY fecha_analisis DESC LIMIT %s",
            (int(limite),),
        )
        filas = cursor.fetchall()
    finally:
        conexion.close()
    return filas


def estadisticas_globales():
    conexion = _conectar()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT total_estudios, total_cromosomas, "
            "promedio_cromosomas_por_estudio FROM vista_estadisticas_globales"
        )
        fila = cursor.fetchone()
    finally:
        conexion.close()
    return fila or {}


def cargar_estudio(id_estudio):
    conexion = _conectar()
    try:
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT id_estudio, imagen_original, fecha_analisis FROM estudios "
            "WHERE id_estudio = %s",
            (id_estudio,),
        )
        estudio = cursor.fetchone()
        if not estudio:
            raise ValueError(f"No existe el estudio {id_estudio}")

        cursor.execute(
            "SELECT c.id_cromosoma, c.clase_detectada, c.confianza, "
            "COALESCE(cl.cromosoma_asignado, c.clase_detectada) AS cromosoma_asignado, "
            "COALESCE(cl.confianza, c.confianza) AS confianza_asignada "
            "FROM cromosomas c "
            "LEFT JOIN clasificaciones cl ON cl.id_cromosoma = c.id_cromosoma "
            "WHERE c.id_estudio = %s ORDER BY c.id_cromosoma",
            (id_estudio,),
        )
        cromosomas = cursor.fetchall()

        cursor.execute(
            "SELECT cariotipo, alteracion, observacion FROM resultados "
            "WHERE id_estudio = %s",
            (id_estudio,),
        )
        resultado = cursor.fetchone()

        return {"estudio": estudio, "cromosomas": cromosomas, "resultado": resultado}
    finally:
        conexion.close()


def guardar_revision(id_estudio, asignaciones, cariotipo, alteracion=None, observacion=None):
    """Guarda la revisión de un estudio. `asignaciones` es {id_cromosoma: clase}."""
    datos = [
        {
            "id_cromosoma": int(id_cromosoma),
            "cromosoma_asignado": str(clase)[:5],
            "confianza": None,
        }
        for id_cromosoma, clase in sorted(asignaciones.items())
    ]

    conexion = _conectar()
    try:
        cursor = conexion.cursor()
        cursor.callproc(
            "sp_guardar_revision_estudio",
            (
                id_estudio,
                json.dumps(datos, ensure_ascii=False),
                cariotipo,
                alteracion or None,
                observacion or None,
            ),
        )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def _demo():
    """Datos inventados, solo para probar el diseño del dashboard."""
    rng = np.random.default_rng(42)
    hoy = pd.Timestamp.today().normalize()
    filas = []

    for imagen in range(1, 13):
        persona = int(rng.integers(1, 6))
        fecha = hoy - pd.Timedelta(days=int(rng.integers(0, 60)))
        copias = {par: 2 for par in PARES_AUTOSOMICOS}
        if rng.random() < 0.5:
            copias.update({"X": 2, "Y": 0})
        else:
            copias.update({"X": 1, "Y": 1})

        for par in rng.choice(PARES_AUTOSOMICOS, size=int(rng.integers(0, 4)), replace=False):
            copias[str(par)] += int(rng.choice([-1, 1]))

        for par, cantidad in copias.items():
            for _ in range(cantidad):
                filas.append({
                    "persona_id": persona,
                    "muestra_id": imagen,
                    "fecha": fecha,
                    "imagen_id": imagen,
                    "archivo": f"demo_{imagen:02d}.jpg",
                    "numero_par": par,
                    "confianza": float(np.clip(rng.normal(0.84, 0.12), 0.35, 0.99)),
                    "x": int(rng.integers(0, 1000)),
                    "y": int(rng.integers(0, 1000)),
                    "ancho": int(rng.integers(20, 120)),
                    "alto": int(rng.integers(20, 120)),
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
