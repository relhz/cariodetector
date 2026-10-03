"""
Interfaz gráfica principal con Tkinter.
Ventana con: selección de imagen, visualización original/analizada, resultados, guardar, historial.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import cv2
from PIL import Image, ImageTk

from funciones.analisis_imagen import AnalizadorImagen
from funciones.resultados import (
    detecciones_a_tabla,
    formatear_resumen_texto,
    detecciones_para_bd,
    obtener_estadisticas_globales
)
from utils.db_config import obtener_conexion, probar_conexion


class InterfazCromosomas:
    """
    Ventana principal de la aplicación.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Cromosomas - Trabajo Práctico")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # Estado de la aplicación
        self.analizador = AnalizadorImagen()
        self.ruta_imagen_actual = None
        self.detecciones_actuales = []
        self.imagen_original_tk = None
        self.imagen_analizada_tk = None
        self.id_analisis_guardado = None

        # Inicializar UI
        self._crear_interfaz()
        self._verificar_modelo_al_inicio()

    def _crear_interfaz(self):
        """Construye todos los widgets de la interfaz."""
        # Frame principal con padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== BARRA SUPERIOR: Controles =====
        frame_controles = ttk.Frame(main_frame)
        frame_controles.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_controles, text="ANALIZADOR DE CROMOSOMAS",
                  font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        self.btn_seleccionar = ttk.Button(frame_controles, text="Seleccionar imagen",
                                           command=self._seleccionar_imagen, width=18)
        self.btn_seleccionar.pack(side=tk.LEFT, padx=5)

        self.btn_analizar = ttk.Button(frame_controles, text="Analizar",
                                        command=self._analizar, width=15, state=tk.DISABLED)
        self.btn_analizar.pack(side=tk.LEFT, padx=5)

        self.btn_guardar = ttk.Button(frame_controles, text="Guardar análisis",
                                       command=self._guardar_analisis, width=15, state=tk.DISABLED)
        self.btn_guardar.pack(side=tk.LEFT, padx=5)

        self.btn_historial = ttk.Button(frame_controles, text="Historial",
                                         command=self._mostrar_historial, width=12)
        self.btn_historial.pack(side=tk.LEFT, padx=5)

        # ===== ÁREA DE IMÁGENES =====
        frame_imagenes = ttk.Frame(main_frame)
        frame_imagenes.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Imagen original
        frame_orig = ttk.LabelFrame(frame_imagenes, text="Imagen original", padding=5)
        frame_orig.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.canvas_original = tk.Canvas(frame_orig, bg="#f0f0f0", highlightthickness=1,
                                          highlightbackground="#ccc")
        self.canvas_original.pack(fill=tk.BOTH, expand=True)

        # Imagen analizada
        frame_anal = ttk.LabelFrame(frame_imagenes, text="Imagen analizada", padding=5)
        frame_anal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.canvas_analizada = tk.Canvas(frame_anal, bg="#f0f0f0", highlightthickness=1,
                                           highlightbackground="#ccc")
        self.canvas_analizada.pack(fill=tk.BOTH, expand=True)

        # ===== ÁREA DE RESULTADOS =====
        frame_resultados = ttk.LabelFrame(main_frame, text="RESULTADOS", padding=5)
        frame_resultados.pack(fill=tk.BOTH, expand=True)

        # Notebook para pestañas: Tabla + Resumen
        self.notebook = ttk.Notebook(frame_resultados)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña 1: Tabla de detecciones
        frame_tabla = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(frame_tabla, text="Detecciones")

        # Treeview para tabla
        columnas = ("cromosoma", "confianza", "posicion")
        self.tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=10)
        self.tree.heading("cromosoma", text="Cromosoma")
        self.tree.heading("confianza", text="Confianza")
        self.tree.heading("posicion", text="Posición (x, y, w, h) norm.")
        self.tree.column("cromosoma", width=150, anchor=tk.CENTER)
        self.tree.column("confianza", width=100, anchor=tk.CENTER)
        self.tree.column("posicion", width=300, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_tabla, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)

        # Pestaña 2: Resumen textual
        frame_resumen = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(frame_resumen, text="Resumen")

        self.txt_resumen = tk.Text(frame_resumen, wrap=tk.WORD, font=("Consolas", 10),
                                    height=12, state=tk.DISABLED)
        scroll_resumen = ttk.Scrollbar(frame_resumen, orient=tk.VERTICAL, command=self.txt_resumen.yview)
        self.txt_resumen.configure(yscrollcommand=scroll_resumen.set)

        self.txt_resumen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_resumen.pack(side=tk.RIGHT, fill=tk.Y)

        # ===== BARRA DE ESTADO =====
        self.var_estado = tk.StringVar(value="Listo. Seleccione una imagen para comenzar.")
        self.lbl_estado = ttk.Label(main_frame, textvariable=self.var_estado,
                                     relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.lbl_estado.pack(fill=tk.X, pady=(5, 0))

    def _verificar_modelo_al_inicio(self):
        """Verifica si el modelo existe al iniciar."""
        from funciones.modelo_cromosomas import DetectorCromosomas
        detector = DetectorCromosomas()
        if not detector.ruta_modelo.exists():
            self.var_estado.set("⚠ Modelo no encontrado. Coloque best_24_chromosomes.pt en models/")
            messagebox.showwarning("Modelo no encontrado",
                "No se encuentra el archivo del modelo:\n"
                f"{detector.ruta_modelo}\n\n"
                "Coloque best_24_chromosomes.pt en la carpeta models/ "
                "para poder analizar imágenes.")

    def _seleccionar_imagen(self):
        """Abre diálogo para seleccionar imagen."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de cromosomas",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("Todos", "*.*")
            ]
        )

        if not ruta:
            return

        try:
            self.ruta_imagen_actual = ruta
            self.analizador.cargar_imagen(ruta)
            self._mostrar_imagen_en_canvas(self.analizador.obtener_imagen_original(), self.canvas_original)
            self._limpiar_imagen_analizada()
            self._limpiar_resultados()
            self.btn_analizar.config(state=tk.NORMAL)
            self.btn_guardar.config(state=tk.DISABLED)
            self.id_analisis_guardado = None
            self.var_estado.set(f"Imagen cargada: {Path(ruta).name}")
        except Exception as e:
            messagebox.showerror("Error cargando imagen", str(e))
            self.var_estado.set("Error al cargar imagen")

    def _analizar(self):
        """Ejecuta el análisis de la imagen cargada."""
        if self.analizador.obtener_imagen_original() is None:
            messagebox.showwarning("Sin imagen", "Primero seleccione una imagen.")
            return

        self.var_estado.set("Analizando... Por favor espere.")
        self.root.update_idletasks()
        self.btn_analizar.config(state=tk.DISABLED)

        try:
            # Ejecutar análisis
            resultado = self.analizador.analizar(conf_threshold=0.25)
            self.detecciones_actuales = resultado["detecciones"]

            # Mostrar imagen analizada
            self._mostrar_imagen_en_canvas(resultado["imagen_anotada"], self.canvas_analizada)

            # Llenar tabla
            self._llenar_tabla(self.detecciones_actuales)

            # Mostrar resumen
            self._mostrar_resumen(resultado["resumen"])

            # Habilitar guardar
            self.btn_guardar.config(state=tk.NORMAL)

            # Estadísticas en estado
            stats = obtener_estadisticas_globales(self.detecciones_actuales)
            self.var_estado.set(f"Análisis completado: {stats['total']} detecciones, "
                                f"{stats['tipos_unicos']} tipos, conf. promedio: {stats['conf_promedio']:.1%}")

        except FileNotFoundError as e:
            messagebox.showerror("Modelo no encontrado", str(e))
            self.var_estado.set("Error: Modelo no encontrado")
        except Exception as e:
            messagebox.showerror("Error durante análisis", f"Ocurrió un error:\n{e}")
            self.var_estado.set("Error durante análisis")
        finally:
            self.btn_analizar.config(state=tk.NORMAL)

    def _mostrar_imagen_en_canvas(self, imagen_cv, canvas):
        """
        Convierte imagen OpenCV (BGR) a PhotoImage y la muestra en canvas,
        escalada para ajustarse manteniendo proporción.
        """
        if imagen_cv is None:
            return

        # Convertir BGR a RGB
        imagen_rgb = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2RGB)
        imagen_pil = Image.fromarray(imagen_rgb)

        # Obtener tamaño del canvas
        canvas.update_idletasks()
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()

        if cw <= 1 or ch <= 1:
            cw, ch = 500, 400  # fallback

        # Escalar manteniendo aspect ratio
        img_w, img_h = imagen_pil.size
        escala = min(cw / img_w, ch / img_h, 1.0)  # no ampliar
        nuevo_w = max(1, int(img_w * escala))
        nuevo_h = max(1, int(img_h * escala))

        imagen_pil = imagen_pil.resize((nuevo_w, nuevo_h), Image.Resampling.LANCZOS)
        imagen_tk = ImageTk.PhotoImage(imagen_pil)

        # Guardar referencia para evitar garbage collection
        if canvas == self.canvas_original:
            self.imagen_original_tk = imagen_tk
        else:
            self.imagen_analizada_tk = imagen_tk

        # Limpiar y dibujar centrado
        canvas.delete("all")
        x = (cw - nuevo_w) // 2
        y = (ch - nuevo_h) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=imagen_tk)

    def _limpiar_imagen_analizada(self):
        self.canvas_analizada.delete("all")
        self.imagen_analizada_tk = None

    def _llenar_tabla(self, detecciones):
        """Llena el Treeview con las detecciones."""
        # Limpiar
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Llenar
        filas = detecciones_a_tabla(detecciones)
        for i, (nombre, conf, bbox) in enumerate(filas):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", tk.END, values=(nombre, conf, bbox), tags=(tag,))

        self.tree.tag_configure("even", background="#fafafa")
        self.tree.tag_configure("odd", background="#ffffff")

    def _mostrar_resumen(self, resumen):
        """Muestra el resumen en el Text widget."""
        self.txt_resumen.config(state=tk.NORMAL)
        self.txt_resumen.delete(1.0, tk.END)
        texto = formatear_resumen_texto(resumen)
        self.txt_resumen.insert(tk.END, texto)
        self.txt_resumen.config(state=tk.DISABLED)

    def _limpiar_resultados(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.txt_resumen.config(state=tk.NORMAL)
        self.txt_resumen.delete(1.0, tk.END)
        self.txt_resumen.config(state=tk.DISABLED)
        self.detecciones_actuales = []

    def _guardar_analisis(self):
        """Guarda el análisis actual en MySQL."""
        if not self.detecciones_actuales:
            messagebox.showwarning("Sin resultados", "No hay detecciones para guardar.")
            return

        if not self.ruta_imagen_actual:
            messagebox.showwarning("Sin imagen", "No hay imagen asociada.")
            return

        # Probar conexión primero
        exito, msg = probar_conexion()
        if not exito:
            messagebox.showerror("MySQL no disponible",
                                 f"No se puede conectar a la base de datos:\n{msg}\n\n"
                                 "Verifique que MySQL esté corriendo y las credenciales en utils/db_config.py")
            return

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()

            # Insertar análisis principal
            nombre_img = Path(self.ruta_imagen_actual).name
            sql_analisis = """
                INSERT INTO analisis (nombre_imagen, total_detecciones, ruta_imagen_original)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql_analisis, (nombre_img, len(self.detecciones_actuales), self.ruta_imagen_actual))
            analisis_id = cursor.lastrowid

            # Insertar detecciones individuales
            filas_detecciones = detecciones_para_bd(self.detecciones_actuales, analisis_id)
            sql_det = """
                INSERT INTO detecciones
                (analisis_id, clase_id, nombre_clase, confianza, bbox_x, bbox_y, bbox_w, bbox_h)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(sql_det, filas_detecciones)

            conexion.commit()
            cursor.close()
            conexion.close()

            self.id_analisis_guardado = analisis_id
            messagebox.showinfo("Guardado", f"Análisis guardado correctamente (ID: {analisis_id})")
            self.var_estado.set(f"Análisis guardado en BD (ID: {analisis_id})")

        except Exception as e:
            messagebox.showerror("Error guardando", f"No se pudo guardar en MySQL:\n{e}")
            self.var_estado.set("Error al guardar en BD")

    def _mostrar_historial(self):
        """Abre ventana con historial de análisis guardados."""
        # Probar conexión
        exito, msg = probar_conexion()
        if not exito:
            messagebox.showerror("MySQL no disponible", msg)
            return

        # Ventana historial
        win = tk.Toplevel(self.root)
        win.title("Historial de análisis")
        win.geometry("700x450")
        win.transient(self.root)
        win.grab_set()

        # Treeview historial
        cols = ("id", "imagen", "fecha", "total", "tipos")
        tree_hist = ttk.Treeview(win, columns=cols, show="headings", height=15)
        tree_hist.heading("id", text="ID")
        tree_hist.heading("imagen", text="Imagen")
        tree_hist.heading("fecha", text="Fecha")
        tree_hist.heading("total", text="Total")
        tree_hist.heading("tipos", text="Tipos detectados")
        tree_hist.column("id", width=50, anchor=tk.CENTER)
        tree_hist.column("imagen", width=200)
        tree_hist.column("fecha", width=150, anchor=tk.CENTER)
        tree_hist.column("total", width=60, anchor=tk.CENTER)
        tree_hist.column("tipos", width=220)

        scroll_y = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree_hist.yview)
        tree_hist.configure(yscrollcommand=scroll_y.set)

        tree_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # Cargar datos
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.id, a.nombre_imagen, a.fecha_analisis, a.total_detecciones,
                       GROUP_CONCAT(DISTINCT d.nombre_clase ORDER BY d.nombre_clase) AS tipos
                FROM analisis a
                LEFT JOIN detecciones d ON a.id = d.analisis_id
                GROUP BY a.id, a.nombre_imagen, a.fecha_analisis, a.total_detecciones
                ORDER BY a.fecha_analisis DESC
            """)
            filas = cursor.fetchall()
            cursor.close()
            conexion.close()

            for fila in filas:
                tree_hist.insert("", tk.END, values=(
                    fila["id"],
                    fila["nombre_imagen"],
                    fila["fecha_analisis"].strftime("%Y-%m-%d %H:%M"),
                    fila["total_detecciones"],
                    fila["tipos"] or "-"
                ))

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar historial:\n{e}")

        # Botón cerrar
        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=(0, 10))


def main():
    """Punto de entrada de la interfaz."""
    root = tk.Tk()
    app = InterfazCromosomas(root)
    root.mainloop()


if __name__ == "__main__":
    main()