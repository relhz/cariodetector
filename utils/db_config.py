import mysql.connector
from mysql.connector import Error
from pathlib import Path

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",               # Usuario MySQL
    "password": "root",           # Contraseña MySQL
    "database": "cariodetector",
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
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

def inicializar_bd():

    script_path = Path(__file__).resolve().parent.parent / "scripts_sql" / "crear_bd.sql"

    if not script_path.exists():
        return False, f"No se encuentra el script SQL: {script_path}"

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        config_sin_bd = DB_CONFIG.copy()
        config_sin_bd.pop("database", None)

        conexion = mysql.connector.connect(**config_sin_bd)
        cursor = conexion.cursor()

        for sentencia in sql_script.split(";"):
            sentencia = sentencia.strip()
            if sentencia and not sentencia.startswith("--"):
                cursor.execute(sentencia)

        cursor.close()
        conexion.close()
        return True, "Base de datos inicializada correctamente"

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