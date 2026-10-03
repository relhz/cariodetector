"""
Configuración de base de datos MySQL.
Ajuste las credenciales según su entorno.
"""

import mysql.connector
from mysql.connector import Error
from pathlib import Path

# CONFIGURACIÓN - MODIFIQUE SEGÚN SU ENTORNO
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "admin",           # Cambie por su usuario MySQL
    "password": "cario",           # Cambie por su contraseña MySQL
    "database": "cariodetector",
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": True,
}


def obtener_conexion():
    """
    Crea y devuelve una conexión a MySQL.
    Lanza excepción si falla.
    """
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except Error as e:
        raise Exception(f"Error conectando a MySQL: {e}")


def probar_conexion():
    """
    Prueba la conexión a MySQL.
    Retorna (exito: bool, mensaje: str)
    """
    try:
        conexion = obtener_conexion()
        conexion.close()
        return True, "Conexión a MySQL exitosa"
    except Exception as e:
        return False, str(e)


def inicializar_bd():
    """
    Ejecuta el script SQL para crear la base de datos y tablas.
    Útil para configuración inicial.
    """
    script_path = Path(__file__).resolve().parent.parent / "scripts_sql" / "crear_bd.sql"

    if not script_path.exists():
        return False, f"No se encuentra el script SQL: {script_path}"

    try:
        # Leer script
        with open(script_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Conectar sin base de datos específica para CREATE DATABASE
        config_sin_bd = DB_CONFIG.copy()
        config_sin_bd.pop("database", None)

        conexion = mysql.connector.connect(**config_sin_bd)
        cursor = conexion.cursor()

        # Ejecutar sentencias separadas por ;
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
    # Prueba rápida al ejecutar este archivo directamente
    exito, msg = probar_conexion()
    print(f"Prueba conexión: {msg}")
    if exito:
        exito, msg = inicializar_bd()
        print(f"Inicializar BD: {msg}")