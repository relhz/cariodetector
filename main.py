import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Asegurar que el directorio del proyecto esté en sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from interfaz.interfaz import InterfazCromosomas


def main():
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
