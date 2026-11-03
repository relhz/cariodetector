import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Asegurar que el directorio del proyecto esté en sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from interfaz.interfaz import InterfazCromosomas
from dashboard.lanzador import detener_dashboard, iniciar_dashboard


def main():
    print("Iniciando Analizador de Cromosomas...")
    print(f"Directorio base: {BASE_DIR}")

    proceso_dashboard = None

    try:
        root = tk.Tk()
        app = InterfazCromosomas(root)

        def cerrar_aplicacion():
            detener_dashboard(proceso_dashboard)
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", cerrar_aplicacion)

        # Abrir la ventana antes de esperar al dashboard, para que no parezca colgada.
        root.update_idletasks()
        root.update()

        print("Iniciando dashboard web...")
        proceso_dashboard = iniciar_dashboard()

        root.mainloop()

    except Exception as e:
        print(f"Error fatal: {e}")
        try:
            messagebox.showerror("Error fatal", f"Error al iniciar la aplicación:\n{e}")
        except Exception:
            pass
        sys.exit(1)

    finally:
        detener_dashboard(proceso_dashboard)


if __name__ == "__main__":
    main()
