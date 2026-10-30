import mysql.connector
from mysql.connector import Error

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
