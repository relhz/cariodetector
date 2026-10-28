import mysql.connector
from mysql.connector import Error
from pathlib import Path

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",               # Usuario MySQL
    "password": "root",           # Contraseña MySQL
    "database": "cariotipos",
    "charset": "utf8mb4",
    "collation": "utf8mb4_0900_ai_ci",
    "autocommit": True,
}


def obtener_conexion():
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except Error as e:
        raise Exception(f"Error conectando a MySQL: {e}")


def probar_conexion():
    try:
        conexion = obtener_conexion()
        conexion.close()
        return True, "Conexión a MySQL exitosa"
    except Exception as e:
        return False, str(e)


def _es_sentencia_util(sentencia):
    """Indica si una sentencia tiene contenido además de comentarios."""
    for linea in sentencia.splitlines():
        texto = linea.strip()
        if not texto:
            continue
        if texto.startswith("--") or texto.startswith("#"):
            continue
        return True
    return False


def _dividir_sentencias(sql_script):
    """
    Divide un script SQL en sentencias respetando los bloques DELIMITER.

    El cliente `mysql` usa DELIMITER para indicar dónde termina un
    procedimiento o una función. El servidor no entiende esa directiva,
    por lo que hay que procesarla antes de ejecutar cada sentencia.
    """
    sentencias = []
    buffer = []
    delimitador = ";"

    def volcar():
        contenido = "".join(buffer).strip()
        if contenido.endswith(delimitador):
            contenido = contenido[:-len(delimitador)].rstrip()
        if contenido and _es_sentencia_util(contenido):
            sentencias.append(contenido)
        buffer.clear()

    for linea in sql_script.splitlines():
        texto = linea.strip()

        if texto.upper().startswith("DELIMITER "):
            if "".join(buffer).strip():
                volcar()
            delimitador = texto.split(None, 1)[1].strip()
            continue

        buffer.append(linea + "\n")

        if "".join(buffer).rstrip().endswith(delimitador):
            volcar()

    if "".join(buffer).strip():
        volcar()

    return sentencias


def inicializar_bd():
    script_path = Path(__file__).resolve().parent.parent / "scripts_sql" / "crear_bd.sql"

    if not script_path.exists():
        return False, f"No se encuentra el script SQL: {script_path}"

    try:
        sql_script = script_path.read_text(encoding="utf-8")
        sentencias = _dividir_sentencias(sql_script)

        config_sin_bd = DB_CONFIG.copy()
        config_sin_bd.pop("database", None)

        conexion = mysql.connector.connect(**config_sin_bd)
        cursor = conexion.cursor()

        try:
            for numero, sentencia in enumerate(sentencias, 1):
                try:
                    cursor.execute(sentencia)
                except Error as e:
                    raise Exception(
                        f"Error en la sentencia {numero}: {e}\n"
                        f"{sentencia[:300]}"
                    )
        finally:
            cursor.close()
            conexion.close()

        return True, f"Base de datos inicializada correctamente ({len(sentencias)} sentencias)"

    except Error as e:
        return False, f"Error inicializando BD: {e}"
    except Exception as e:
        return False, f"Error inesperado: {e}"


if __name__ == "__main__":
    exito, msg = probar_conexion()
    print(f"Prueba conexión: {msg}")
    if exito:
        exito, msg = inicializar_bd()
        print(f"Inicializar BD: {msg}")
