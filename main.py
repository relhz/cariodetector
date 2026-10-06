import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Asegurar que el directorio del proyecto esté en sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from interfaz.interfaz import InterfazCromosomas


def verificar_entorno():
    # Verificar Python version
    if sys.version_info < (3, 8):
        return False, f"Se requiere Python 3.8+. Versión actual: {sys.version}"

    # Verificar estructura básica
    modelos_dir = BASE_DIR / "models"
    if not modelos_dir.exists():
        return False, f"Falta carpeta models: {modelos_dir}"

    return True, "Entorno OK"


def main():
    ok, msg = verificar_entorno()
    if not ok:
        # Mostrar error en consola y messagebox si Tkinter funciona
        print(f"ERROR: {msg}")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error de entorno", msg)
        except:
            pass
        sys.exit(1)

    print("Iniciando Analizador de Cromosomas...")
    print(f"Directorio base: {BASE_DIR}")

    # Crear y ejecutar interfaz
    try:
        root = tk.Tk()
        app = InterfazCromosomas(root)
        root.mainloop()
    except Exception as e:
        print(f"Error fatal: {e}")
        try:
            messagebox.showerror("Error fatal", f"Error al iniciar la aplicación:\n{e}")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()