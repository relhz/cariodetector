import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import cv2
from PIL import Image, ImageTk

from funciones.analisis_imagen import AnalizadorImagen
from funciones.resultados import (
    CLASES_CROMOSOMA,
    detecciones_a_tabla,
    formatear_resumen_texto,
    detecciones_para_bd,
    generar_resumen_detallado,
    normalizar_clase,
    obtener_estadisticas_globales,
    preparar_detecciones,
    recortar_deteccion,
    sugerir_cariotipo
)
from interfaz.pestana_estadisticas import PestanaEstadisticas
from utils.db_config import obtener_conexion, probar_conexion


class InterfazCromosomas:
    """
    Ventana principal de la aplicación.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Cariodetector")
        self.root.geometry("1250x820")
        self.root.minsize(1000, 650)

        # Estado de la aplicación
        self.analizador = AnalizadorImagen()
        self.ruta_imagen_actual = None
        self.detecciones_actuales = []
        self.imagen_original_tk = None
        self.imagen_analizada_tk = None

        # Estado del panel de revisión de detecciones
        self._indice_a_item = {}
        self._recorte_pil = None
        self._recorte_tk = None

        # Estado para zoom/pan sincronizados
        # Datos de imagen original
        self.img_orig_pil = None  # PIL Image original (RGB)
        self.img_anal_cv = None  # OpenCV anotada (BGR)

        # Transformación para cada canvas: scale y offset
        self.scale_orig = 1.0
        self.scale_anal = 1.0
        self.offset_x_orig = 0
        self.offset_y_orig = 0
        self.offset_x_anal = 0
        self.offset_y_anal = 0

        # Estado de pan
        self._dragging = False
        self._last_x = 0
        self._last_y = 0

        # Inicializar UI
        self._crear_interfaz()
        self._verificar_modelo_al_inicio()

    def _crear_interfaz(self):
        """Construye todos los widgets de la interfaz."""
        # Barra de estado global, debajo de las pestañas
        self.var_estado = tk.StringVar(value="Listo. Seleccione una imagen para comenzar.")
        self.lbl_estado = ttk.Label(self.root, textvariable=self.var_estado,
                                     relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.lbl_estado.pack(side=tk.BOTTOM, fill=tk.X)

        # Pestañas principales: Análisis y Estadísticas
        self.notebook_principal = ttk.Notebook(self.root)
        self.notebook_principal.pack(fill=tk.BOTH, expand=True)

        self.tab_analisis = ttk.Frame(self.notebook_principal, padding="10")
        self.notebook_principal.add(self.tab_analisis, text="Análisis")

        # Frame principal con padding
        main_frame = ttk.Frame(self.tab_analisis)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== BARRA SUPERIOR: Controles =====
        frame_controles = ttk.Frame(main_frame)
        frame_controles.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_controles, text="CARIODETECTOR",
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

        self.btn_reset_zoom = ttk.Button(frame_controles, text="Ajustar a ventana",
                                         command=self._reset_zoom, width=16)
        self.btn_reset_zoom.pack(side=tk.LEFT, padx=5)

        # ===== ÁREA DE IMÁGENES Y RESULTADOS =====
        panel_vertical = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        panel_vertical.pack(fill=tk.BOTH, expand=True)

        frame_imagenes = ttk.Frame(panel_vertical, padding=(0, 0, 0, 6))
        panel_vertical.add(frame_imagenes, weight=1)

        # Configurar grid para que ambos paneles se expandan
        frame_imagenes.columnconfigure(0, weight=1)
        frame_imagenes.columnconfigure(1, weight=1)
        frame_imagenes.rowconfigure(0, weight=1)

        # Imagen original
        frame_orig = ttk.LabelFrame(frame_imagenes, text="Imagen original", padding=5)
        frame_orig.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.canvas_original = tk.Canvas(frame_orig, bg="#f0f0f0", highlightthickness=1,
                                          highlightbackground="#ccc")
        self.canvas_original.pack(fill=tk.BOTH, expand=True)

        # Imagen analizada
        frame_anal = ttk.LabelFrame(frame_imagenes, text="Imagen analizada", padding=5)
        frame_anal.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.canvas_analizada = tk.Canvas(frame_anal, bg="#f0f0f0", highlightthickness=1,
                                           highlightbackground="#ccc")
        self.canvas_analizada.pack(fill=tk.BOTH, expand=True)

        # ===== ÁREA DE RESULTADOS =====
        frame_resultados = ttk.LabelFrame(panel_vertical, text="RESULTADOS", padding=5)
        panel_vertical.add(frame_resultados, weight=1)

        # Notebook para pestañas: Tabla + Resumen
        self.notebook = ttk.Notebook(frame_resultados)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña 1: Tabla de detecciones + detalle de la selección
        frame_detecciones = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(frame_detecciones, text="Detecciones")
        frame_detecciones.columnconfigure(0, weight=3)
        frame_detecciones.columnconfigure(1, weight=2, minsize=280)
        frame_detecciones.rowconfigure(0, weight=1)

        frame_tabla = ttk.Frame(frame_detecciones)
        frame_tabla.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame_tabla.rowconfigure(0, weight=1)
        frame_tabla.columnconfigure(0, weight=1)

        # Treeview para tabla
        columnas = ("numero", "detectada", "asignada", "confianza")
        self.tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=8)
        self.tree.heading("numero", text="#")
        self.tree.heading("detectada", text="Detectada")
        self.tree.heading("asignada", text="Asignada")
        self.tree.heading("confianza", text="Confianza")
        self.tree.column("numero", width=40, anchor=tk.CENTER, stretch=False)
        self.tree.column("detectada", width=90, anchor=tk.CENTER)
        self.tree.column("asignada", width=90, anchor=tk.CENTER)
        self.tree.column("confianza", width=85, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_tabla, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._al_seleccionar_deteccion)

        self._crear_panel_detalle(frame_detecciones)

        # Pestaña 2: Resumen textual
        frame_resumen = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(frame_resumen, text="Resumen")

        self.txt_resumen = tk.Text(frame_resumen, wrap=tk.WORD, font=("Consolas", 10),
                                    height=12, state=tk.DISABLED)
        scroll_resumen = ttk.Scrollbar(frame_resumen, orient=tk.VERTICAL, command=self.txt_resumen.yview)
        self.txt_resumen.configure(yscrollcommand=scroll_resumen.set)

        self.txt_resumen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_resumen.pack(side=tk.RIGHT, fill=tk.Y)

        # ===== PESTAÑA DE ESTADÍSTICAS =====
        self.pestana_estadisticas = PestanaEstadisticas(self.notebook_principal)
        self.notebook_principal.add(self.pestana_estadisticas, text="Estadísticas")
        self.notebook_principal.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

    def _crear_panel_detalle(self, master):
        """Panel con el recorte del cromosoma y el editor de su clase."""
        frame = ttk.LabelFrame(master, text="Detalle de la detección", padding=5)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.canvas_recorte = tk.Canvas(
            frame,
            width=220,
            height=220,
            bg="#f0f0f0",
            highlightthickness=1,
            highlightbackground="#ccc",
        )
        self.canvas_recorte.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        self.canvas_recorte.bind("<Configure>", lambda _e: self._redibujar_recorte())

        self.var_det_info = tk.StringVar(value="Seleccione una detección")
        self.var_det_estado = tk.StringVar(value="")

        ttk.Label(
            frame,
            textvariable=self.var_det_info,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=1, column=0, sticky="w")

        ttk.Label(
            frame,
            textvariable=self.var_det_estado,
            foreground="#666",
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        fila_editor = ttk.Frame(frame)
        fila_editor.grid(row=3, column=0, sticky="ew")

        ttk.Label(fila_editor, text="Asignar:").pack(side=tk.LEFT)

        self.var_det_clase = tk.StringVar(value="")
        self.cmb_det_clase = ttk.Combobox(
            fila_editor,
            textvariable=self.var_det_clase,
            values=CLASES_CROMOSOMA,
            state="disabled",
            width=10,
        )
        self.cmb_det_clase.pack(side=tk.LEFT, padx=5)

        self.btn_det_aplicar = ttk.Button(
            fila_editor,
            text="Aplicar",
            command=self._aplicar_clase_detectada,
            state=tk.DISABLED,
        )
        self.btn_det_aplicar.pack(side=tk.LEFT, padx=(5, 2))

        self.btn_det_restaurar = ttk.Button(
            fila_editor,
            text="Restaurar",
            command=self._restaurar_clase_detectada,
            state=tk.DISABLED,
        )
        self.btn_det_restaurar.pack(side=tk.LEFT, padx=2)

        fila_acciones = ttk.Frame(frame)
        fila_acciones.grid(row=4, column=0, sticky="ew", pady=(4, 0))

        self.btn_det_eliminar = ttk.Button(
            fila_acciones,
            text="Eliminar detección",
            command=self._eliminar_deteccion_seleccionada,
            state=tk.DISABLED,
        )
        self.btn_det_eliminar.pack(side=tk.LEFT)

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

    def _al_cambiar_pestana(self, event=None):
        """Refresca las estadísticas al entrar a esa pestaña."""
        try:
            pestana_actual = self.notebook_principal.select()
            if pestana_actual == str(self.pestana_estadisticas):
                self.pestana_estadisticas.actualizar()
        except Exception:
            pass

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
            # Configurar eventos de zoom/pan para ambos canvas
            self._configurar_zoom_pan()
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
            self.detecciones_actuales = preparar_detecciones(resultado["detecciones"])

            # Mostrar imagen analizada
            self._mostrar_imagen_en_canvas(resultado["imagen_anotada"], self.canvas_analizada)

            # Llenar tabla
            self._llenar_tabla(self.detecciones_actuales)

            # Mostrar resumen con las clases normalizadas
            self._mostrar_resumen(generar_resumen_detallado(self.detecciones_actuales))

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
            # Configurar eventos de zoom/pan para ambos canvas
            self._configurar_zoom_pan()
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

        # Guardar referencias según canvas
        if canvas == self.canvas_original:
            self.img_orig_pil = imagen_pil
        else:
            self.img_anal_cv = imagen_cv

        # Ajustar a ventana con zoom sincronizado (reset)
        self._reset_zoom()

    def _limpiar_imagen_analizada(self):
        self.canvas_analizada.delete("all")
        self.imagen_analizada_tk = None
        self.img_anal_cv = None
        self.scale_anal = 1.0
        self.offset_x_anal = 0
        self.offset_y_anal = 0

    def _llenar_tabla(self, detecciones):
        """Llena el Treeview y guarda el mapeo fila -> índice de detección."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._indice_a_item = {}

        self.tree.tag_configure("par", background="#fafafa")
        self.tree.tag_configure("impar", background="#ffffff")
        self.tree.tag_configure("corregida", background="#fff4ce")

        filas = detecciones_a_tabla(detecciones)

        for indice, fila in enumerate(filas):
            tag_zebra = "par" if indice % 2 == 0 else "impar"
            tags = ("corregida",) if fila["corregida"] else (tag_zebra,)

            item = self.tree.insert(
                "",
                tk.END,
                iid=str(indice),
                values=(
                    fila["numero"],
                    fila["detectada"],
                    fila["asignada"],
                    fila["confianza"],
                ),
                tags=tags,
            )
            self._indice_a_item[indice] = item

        self._limpiar_panel_detalle()

        if filas:
            primero = self.tree.get_children()[0]
            self.tree.selection_set(primero)
            self.tree.focus(primero)
            self._al_seleccionar_deteccion()

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

        self._indice_a_item = {}
        self.txt_resumen.config(state=tk.NORMAL)
        self.txt_resumen.delete(1.0, tk.END)
        self.txt_resumen.config(state=tk.DISABLED)
        self.detecciones_actuales = []
        self._limpiar_panel_detalle()

    # ===== Revisión visual de detecciones =====
    def _indice_seleccionado(self):
        """Devuelve el índice de la detección seleccionada, o None."""
        seleccion = self.tree.selection()

        if not seleccion:
            return None

        try:
            return int(seleccion[0])
        except (TypeError, ValueError):
            return None

    def _al_seleccionar_deteccion(self, event=None):
        """Muestra el recorte y la clase de la detección seleccionada."""
        indice = self._indice_seleccionado()

        if indice is None or not (0 <= indice < len(self.detecciones_actuales)):
            self._limpiar_panel_detalle()
            return

        det = self.detecciones_actuales[indice]
        original = det.get("clase_original", det.get("nombre_clase", ""))
        actual = det.get("nombre_clase", "")

        self.var_det_info.set(f"Detectado: {original}   ({det['confianza']:.2%})")

        if actual != original:
            self.var_det_estado.set(f"Corregida a: {actual}")
        else:
            self.var_det_estado.set("Sin correcciones")

        self.var_det_clase.set(actual)
        self.cmb_det_clase.configure(state="readonly")
        self.btn_det_aplicar.configure(state=tk.NORMAL)
        self.btn_det_restaurar.configure(state=tk.NORMAL)
        if hasattr(self, "btn_det_eliminar"):
            self.btn_det_eliminar.configure(state=tk.NORMAL)

        self._mostrar_recorte(det)

    def _mostrar_recorte(self, det):
        """Calcula y muestra el recorte de la detección en el panel."""
        imagen = self.analizador.obtener_imagen_original()

        try:
            recorte = recortar_deteccion(imagen, det.get("bbox"))
        except Exception:
            recorte = None

        if recorte is None:
            self._recorte_pil = None
            self._recorte_tk = None
            self.canvas_recorte.delete("all")
            self.canvas_recorte.create_text(
                110,
                110,
                text="Sin recorte disponible",
                fill="#666",
            )
            return

        recorte_rgb = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB)
        self._recorte_pil = Image.fromarray(recorte_rgb)
        self._redibujar_recorte()

    def _redibujar_recorte(self):
        """Escala y centra el recorte según el tamaño del canvas."""
        self.canvas_recorte.delete("all")

        if self._recorte_pil is None:
            return

        ancho = self.canvas_recorte.winfo_width()
        alto = self.canvas_recorte.winfo_height()

        if ancho <= 2:
            ancho = 220
        if alto <= 2:
            alto = 220

        escala = min(ancho / self._recorte_pil.width, alto / self._recorte_pil.height)
        nuevo_ancho = max(1, int(self._recorte_pil.width * escala))
        nuevo_alto = max(1, int(self._recorte_pil.height * escala))

        imagen = self._recorte_pil.resize(
            (nuevo_ancho, nuevo_alto),
            Image.Resampling.LANCZOS,
        )
        self._recorte_tk = ImageTk.PhotoImage(imagen)
        self.canvas_recorte.create_image(
            ancho // 2,
            alto // 2,
            image=self._recorte_tk,
        )

    def _aplicar_clase_detectada(self):
        """Aplica la clase elegida a la detección seleccionada."""
        indice = self._indice_seleccionado()

        if indice is None:
            messagebox.showwarning(
                "Sin selección",
                "Seleccione una detección de la tabla.",
            )
            return

        clase = normalizar_clase(self.var_det_clase.get())

        if not clase:
            messagebox.showwarning(
                "Clase inválida",
                "Seleccione un tipo de cromosoma.",
            )
            return

        if indice < 0 or indice >= len(self.detecciones_actuales):
            return

        det = self.detecciones_actuales[indice]

        if det.get("nombre_clase") == clase:
            return

        det["nombre_clase"] = clase

        if clase in CLASES_CROMOSOMA:
            det["clase_id"] = CLASES_CROMOSOMA.index(clase)

        self._actualizar_fila_deteccion(indice)
        self._refrescar_resumen_detecciones()
        self._refrescar_imagen_anotada()
        self._al_seleccionar_deteccion()
        self.var_estado.set(f"Detección {indice + 1}: clase asignada {clase}")

    def _restaurar_clase_detectada(self):
        """Restaura la clase original detectada por el modelo."""
        indice = self._indice_seleccionado()

        if indice is None:
            return

        if indice < 0 or indice >= len(self.detecciones_actuales):
            return

        det = self.detecciones_actuales[indice]
        original = det.get("clase_original")

        if not original or det.get("nombre_clase") == original:
            return

        det["nombre_clase"] = original

        if original in CLASES_CROMOSOMA:
            det["clase_id"] = CLASES_CROMOSOMA.index(original)

        self._actualizar_fila_deteccion(indice)
        self._refrescar_resumen_detecciones()
        self._refrescar_imagen_anotada()
        self._al_seleccionar_deteccion()
        self.var_estado.set(f"Detección {indice + 1}: clase restaurada a {original}")

    def _eliminar_deteccion_seleccionada(self):
        """Elimina la detección seleccionada de la lista antes de guardar."""
        indice = self._indice_seleccionado()

        if indice is None:
            messagebox.showwarning(
                "Sin selección",
                "Seleccione una detección de la tabla para eliminarla.",
            )
            return

        if not self.detecciones_actuales:
            return

        if indice < 0 or indice >= len(self.detecciones_actuales):
            return

        det = self.detecciones_actuales[indice]
        clase = det.get("nombre_clase", "-")
        confianza = det.get("confianza", 0)

        respuesta = messagebox.askyesno(
            "Eliminar detección",
            f"¿Eliminar la detección seleccionada ({clase} - {confianza:.2%})?",
        )
        if not respuesta:
            return

        del self.detecciones_actuales[indice]
        self._llenar_tabla(self.detecciones_actuales)

        if self.detecciones_actuales:
            self._refrescar_resumen_detecciones()
        else:
            self.txt_resumen.config(state=tk.NORMAL)
            self.txt_resumen.delete(1.0, tk.END)
            self.txt_resumen.config(state=tk.DISABLED)

        self._refrescar_imagen_anotada()
        self.var_estado.set("Detección eliminada. Se guardarán solo las detecciones restantes.")

    def _actualizar_fila_deteccion(self, indice):
        """Actualiza los valores y el resaltado de una fila de la tabla."""
        item = self._indice_a_item.get(indice)

        if item is None or not self.tree.exists(item):
            return

        det = self.detecciones_actuales[indice]
        original = det.get("clase_original", det.get("nombre_clase", ""))
        actual = det.get("nombre_clase", "")
        corregida = actual != original

        self.tree.item(
            item,
            values=(
                indice + 1,
                original,
                f"{actual} *" if corregida else actual,
                f"{det['confianza']:.2%}",
            ),
            tags=("corregida",) if corregida else ("par" if indice % 2 == 0 else "impar",),
        )

    def _refrescar_resumen_detecciones(self):
        """Regenera el resumen textual con las clases corregidas."""
        if not self.detecciones_actuales:
            return

        self._mostrar_resumen(generar_resumen_detallado(self.detecciones_actuales))

    def _refrescar_imagen_anotada(self):
        """Vuelve a dibujar las etiquetas de la imagen analizada."""
        try:
            imagen = self.analizador.redibujar_anotada(self.detecciones_actuales)
        except Exception:
            return

        self.img_anal_cv = imagen
        self._redibujar_canvas(self.canvas_analizada)

    def _limpiar_panel_detalle(self):
        """Deja el panel de detalle sin selección."""
        self._recorte_pil = None
        self._recorte_tk = None

        if hasattr(self, "canvas_recorte"):
            self.canvas_recorte.delete("all")

        self.var_det_info.set("Seleccione una detección")
        self.var_det_estado.set("")
        self.var_det_clase.set("")
        self.cmb_det_clase.configure(state="disabled")
        self.btn_det_aplicar.configure(state=tk.DISABLED)
        self.btn_det_restaurar.configure(state=tk.DISABLED)
        if hasattr(self, "btn_det_eliminar"):
            self.btn_det_eliminar.configure(state=tk.DISABLED)

    def _guardar_analisis(self):
        """Guarda el análisis actual en MySQL mediante un procedimiento almacenado."""
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

        conexion = None
        cursor = None

        try:
            imagen = self.analizador.obtener_imagen_original()
            if imagen is None:
                raise ValueError("No hay una imagen cargada para calcular las coordenadas.")

            alto_img, ancho_img = imagen.shape[:2]
            nombre_img = Path(self.ruta_imagen_actual).name

            # Convertir las cajas normalizadas del modelo a píxeles y armar el JSON
            filas_detecciones = detecciones_para_bd(
                self.detecciones_actuales,
                ancho_img,
                alto_img
            )
            detecciones_json = json.dumps(filas_detecciones, ensure_ascii=False)

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            resultado = cursor.callproc(
                "sp_guardar_analisis_completo",
                (nombre_img, None, detecciones_json, 0)
            )
            id_estudio = resultado[-1] # type: ignore
            conexion.commit()

            messagebox.showinfo(
                "Guardado",
                f"Análisis guardado correctamente (ID de estudio: {id_estudio})"
            )
            self.var_estado.set(f"Análisis guardado en BD (ID de estudio: {id_estudio})")

            try:
                self.pestana_estadisticas.actualizar()
            except Exception:
                pass

        except Exception as e:
            if conexion is not None:
                try:
                    conexion.rollback()
                except Exception:
                    pass

            messagebox.showerror("Error guardando", f"No se pudo guardar en MySQL:\n{e}")
            self.var_estado.set("Error al guardar en BD")

        finally:
            if cursor is not None:
                cursor.close()
            if conexion is not None:
                conexion.close()

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
        win.geometry("950x480")
        win.transient(self.root)
        win.grab_set()

        # Pie de la ventana: resumen global y botón cerrar
        footer = ttk.Frame(win)
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        lbl_global = ttk.Label(footer, text="")
        lbl_global.pack(side=tk.LEFT, padx=5)

        ttk.Button(footer, text="Cerrar", command=win.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(footer, text="Revisar estudio",
                   command=lambda: self._revisar_seleccionado(tree_hist)).pack(side=tk.RIGHT, padx=5)

        contenido = ttk.Frame(win)
        contenido.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Treeview historial
        cols = ("id", "imagen", "fecha", "total", "confianza", "estado", "tipos")
        tree_hist = ttk.Treeview(contenido, columns=cols, show="headings", height=15)
        tree_hist.heading("id", text="ID")
        tree_hist.heading("imagen", text="Imagen")
        tree_hist.heading("fecha", text="Fecha")
        tree_hist.heading("total", text="Total")
        tree_hist.heading("confianza", text="Conf. prom.")
        tree_hist.heading("estado", text="Estado")
        tree_hist.heading("tipos", text="Tipos detectados")
        tree_hist.column("id", width=50, anchor=tk.CENTER)
        tree_hist.column("imagen", width=200)
        tree_hist.column("fecha", width=145, anchor=tk.CENTER)
        tree_hist.column("total", width=60, anchor=tk.CENTER)
        tree_hist.column("confianza", width=90, anchor=tk.CENTER)
        tree_hist.column("estado", width=100, anchor=tk.CENTER)
        tree_hist.column("tipos", width=250)

        scroll_y = ttk.Scrollbar(contenido, orient=tk.VERTICAL, command=tree_hist.yview)
        tree_hist.configure(yscrollcommand=scroll_y.set)

        tree_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        tree_hist.bind("<Double-1>", lambda _e: self._revisar_seleccionado(tree_hist))

        # Cargar datos desde la vista de estadísticas
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("""
                SELECT id_estudio, imagen_original, fecha_analisis,
                       total_detecciones, confianza_promedio, estado, tipos
                FROM vista_resumen_estudios
                ORDER BY fecha_analisis DESC
            """)
            filas = cursor.fetchall()

            cursor.execute("""
                SELECT total_estudios, total_cromosomas,
                       promedio_cromosomas_por_estudio
                FROM vista_estadisticas_globales
            """)
            resumen_global = cursor.fetchone()

            cursor.close()
            conexion.close()

            for fila in filas:
                fecha = fila["fecha_analisis"]
                fecha_txt = fecha.strftime("%Y-%m-%d %H:%M") if fecha else "-"
                confianza = fila["confianza_promedio"]
                confianza_txt = f"{float(confianza):.1%}" if confianza is not None else "-"

                tree_hist.insert("", tk.END, values=(
                    fila["id_estudio"],
                    fila["imagen_original"],
                    fecha_txt,
                    fila["total_detecciones"],
                    confianza_txt,
                    fila["estado"],
                    fila["tipos"] or "-"
                ))

            if resumen_global:
                texto_global = (
                    f"Estudios: {resumen_global['total_estudios']}  |  "
                    f"Cromosomas: {resumen_global['total_cromosomas']}  |  "
                    f"Promedio por estudio: {resumen_global['promedio_cromosomas_por_estudio']}"
                )
                lbl_global.config(text=texto_global)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar historial:\n{e}")

    # ===== Revisión de clasificaciones y resultado =====
    def _revisar_seleccionado(self, tree_hist):
        """Abre la revisión del estudio seleccionado en el historial."""
        seleccion = tree_hist.selection()

        if not seleccion:
            messagebox.showwarning(
                "Sin selección",
                "Seleccione un estudio del historial para revisarlo."
            )
            return

        valores = tree_hist.item(seleccion[0], "values")

        try:
            id_estudio = int(valores[0])
        except (IndexError, ValueError):
            return

        self._abrir_revision(id_estudio)

    def _abrir_revision(self, id_estudio):
        """Ventana para corregir clasificaciones y guardar el resultado."""
        exito, msg = probar_conexion()
        if not exito:
            messagebox.showerror("MySQL no disponible", msg)
            return

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT id_estudio, imagen_original, fecha_analisis
                FROM estudios
                WHERE id_estudio = %s
            """, (id_estudio,))
            estudio = cursor.fetchone()

            if not estudio:
                raise ValueError(f"No existe el estudio {id_estudio}")

            cursor.execute("""
                SELECT c.id_cromosoma, c.clase_detectada, c.confianza,
                       COALESCE(cl.cromosoma_asignado, c.clase_detectada) AS cromosoma_asignado,
                       COALESCE(cl.confianza, c.confianza) AS confianza_asignada
                FROM cromosomas c
                LEFT JOIN clasificaciones cl
                    ON cl.id_cromosoma = c.id_cromosoma
                WHERE c.id_estudio = %s
                ORDER BY c.id_cromosoma
            """, (id_estudio,))
            filas = cursor.fetchall()

            cursor.execute("""
                SELECT cariotipo, alteracion, observacion
                FROM resultados
                WHERE id_estudio = %s
            """, (id_estudio,))
            resultado = cursor.fetchone()

            cursor.close()
            conexion.close()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el estudio:\n{e}")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Revisión del estudio #{id_estudio}")
        win.geometry("1050x720")
        win.transient(self.root)
        win.grab_set()

        contenido = ttk.Frame(win, padding=10)
        contenido.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            contenido,
            text=f"Estudio #{id_estudio}  |  {estudio['imagen_original']}",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        # Tabla de cromosomas
        frame_tabla = ttk.LabelFrame(contenido, text="Cromosomas detectados", padding=5)
        frame_tabla.pack(fill=tk.BOTH, expand=True)

        columnas = ("id", "detectada", "asignada", "confianza")
        tree = ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings",
            selectmode="extended",
            height=14,
        )
        tree.heading("id", text="ID")
        tree.heading("detectada", text="Clase detectada")
        tree.heading("asignada", text="Asignación")
        tree.heading("confianza", text="Confianza")
        tree.column("id", width=70, anchor=tk.CENTER)
        tree.column("detectada", width=170, anchor=tk.CENTER)
        tree.column("asignada", width=170, anchor=tk.CENTER)
        tree.column("confianza", width=120, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        asignaciones = {}
        items_por_id = {}

        valores_asignacion = list(CLASES_CROMOSOMA)
        for fila in filas:
            clase = fila["clase_detectada"]
            if clase and clase not in valores_asignacion:
                valores_asignacion.append(clase)

        for fila in filas:
            id_cromosoma = fila["id_cromosoma"]
            asignacion = fila["cromosoma_asignado"] or fila["clase_detectada"] or ""
            asignaciones[id_cromosoma] = asignacion

            confianza = fila["confianza_asignada"]
            confianza_texto = f"{float(confianza):.2%}" if confianza is not None else "-"

            item = tree.insert("", tk.END, values=(
                id_cromosoma,
                fila["clase_detectada"] or "-",
                asignacion or "-",
                confianza_texto,
            ))
            items_por_id[id_cromosoma] = item

        # Editor de asignación para las filas seleccionadas
        frame_editor = ttk.Frame(contenido)
        frame_editor.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(frame_editor, text="Asignación:").pack(side=tk.LEFT)

        var_asignacion = tk.StringVar(
            value=valores_asignacion[0] if valores_asignacion else ""
        )
        cmb_asignacion = ttk.Combobox(
            frame_editor,
            textvariable=var_asignacion,
            values=valores_asignacion,
            state="readonly",
            width=12,
        )
        cmb_asignacion.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            frame_editor,
            text="(Ctrl/Shift para seleccionar varios)",
            foreground="#666",
        ).pack(side=tk.LEFT, padx=10)

        def aplicar_asignacion():
            seleccion = tree.selection()

            if not seleccion:
                messagebox.showwarning(
                    "Sin selección",
                    "Seleccione uno o más cromosomas de la tabla."
                )
                return

            codigo = var_asignacion.get().strip()
            if not codigo:
                return

            for item in seleccion:
                id_cromosoma = items_por_id.get(item)
                if id_cromosoma is None:
                    continue

                asignaciones[id_cromosoma] = codigo
                valores = list(tree.item(item, "values"))
                valores[2] = codigo
                tree.item(item, values=valores)

        ttk.Button(
            frame_editor,
            text="Aplicar a seleccionados",
            command=aplicar_asignacion,
        ).pack(side=tk.LEFT, padx=5)

        # Formulario del resultado
        frame_resultado = ttk.LabelFrame(contenido, text="Resultado del estudio", padding=5)
        frame_resultado.pack(fill=tk.X, pady=(8, 0))
        frame_resultado.columnconfigure(1, weight=1)

        var_cariotipo = tk.StringVar(
            value=(resultado or {}).get("cariotipo") or ""
        )
        var_alteracion = tk.StringVar(
            value=(resultado or {}).get("alteracion") or ""
        )

        ttk.Label(frame_resultado, text="Cariotipo:").grid(
            row=0, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Entry(frame_resultado, textvariable=var_cariotipo, width=25).grid(
            row=0, column=1, sticky="w", padx=5, pady=3
        )

        ttk.Label(frame_resultado, text="Alteración:").grid(
            row=1, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Entry(frame_resultado, textvariable=var_alteracion).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=5, pady=3
        )

        ttk.Label(frame_resultado, text="Observación:").grid(
            row=2, column=0, sticky="nw", padx=5, pady=3
        )
        txt_observacion = tk.Text(frame_resultado, height=3, wrap=tk.WORD)
        txt_observacion.grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=3
        )

        if resultado and resultado.get("observacion"):
            txt_observacion.insert("1.0", resultado["observacion"])

        def sugerir():
            cariotipo = sugerir_cariotipo(
                [asignaciones[id_cromosoma] for id_cromosoma in sorted(asignaciones)]
            )
            if cariotipo:
                var_cariotipo.set(cariotipo)

        ttk.Button(
            frame_resultado,
            text="Sugerir cariotipo",
            command=sugerir,
        ).grid(row=0, column=2, padx=5, pady=3)

        # Botones finales
        frame_botones = ttk.Frame(contenido)
        frame_botones.pack(fill=tk.X, pady=(8, 0))

        def guardar_revision():
            cariotipo = var_cariotipo.get().strip()
            alteracion = var_alteracion.get().strip()
            observacion = txt_observacion.get("1.0", tk.END).strip()

            if not cariotipo:
                messagebox.showwarning(
                    "Falta el cariotipo",
                    "Ingrese un cariotipo o use \"Sugerir cariotipo\"."
                )
                return

            if len(cariotipo) > 30:
                messagebox.showwarning(
                    "Cariotipo demasiado largo",
                    "El cariotipo no puede superar los 30 caracteres."
                )
                return

            if len(alteracion) > 100:
                messagebox.showwarning(
                    "Alteración demasiado larga",
                    "La alteración no puede superar los 100 caracteres."
                )
                return

            datos = [
                {
                    "id_cromosoma": id_cromosoma,
                    "cromosoma_asignado": str(asignaciones[id_cromosoma])[:5],
                    "confianza": None,
                }
                for id_cromosoma in sorted(asignaciones)
            ]

            conexion = None
            cursor = None

            try:
                conexion = obtener_conexion()
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

                self.var_estado.set(f"Estudio #{id_estudio} finalizado correctamente")
                messagebox.showinfo(
                    "Revisión guardada",
                    f"El estudio #{id_estudio} quedó guardado como finalizado."
                )

                win.destroy()

                try:
                    self.pestana_estadisticas.actualizar()
                except Exception:
                    pass

            except Exception as e:
                if conexion is not None:
                    try:
                        conexion.rollback()
                    except Exception:
                        pass

                messagebox.showerror(
                    "Error guardando",
                    f"No se pudo guardar la revisión:\n{e}"
                )

            finally:
                if cursor is not None:
                    cursor.close()
                if conexion is not None:
                    conexion.close()

        ttk.Button(
            frame_botones,
            text="Guardar revisión",
            command=guardar_revision,
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            frame_botones,
            text="Cerrar",
            command=win.destroy,
        ).pack(side=tk.RIGHT)

    # ===== Métodos para zoom y pan sincronizados =====
    def _redibujar_canvas(self, canvas):
        """Redibuja la imagen y sus overlays en el canvas con la transformación actual."""
        canvas.delete("all")
        if canvas == self.canvas_original:
            pil_img = self.img_orig_pil
            if pil_img is None:
                return
            scale = self.scale_orig
            offset_x = self.offset_x_orig
            offset_y = self.offset_y_orig
            # Crear imagen escalada
            new_w = max(1, int(pil_img.size[0] * scale))
            new_h = max(1, int(pil_img.size[1] * scale))
            img_resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.imagen_original_tk = ImageTk.PhotoImage(img_resized)
            canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=self.imagen_original_tk)
        else:
            cv_img = self.img_anal_cv
            if cv_img is None:
                return
            scale = self.scale_anal
            offset_x = self.offset_x_anal
            offset_y = self.offset_y_anal
            # Convertir y escalar
            img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            new_w = max(1, int(pil_img.size[0] * scale))
            new_h = max(1, int(pil_img.size[1] * scale))
            img_resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.imagen_analizada_tk = ImageTk.PhotoImage(img_resized)
            canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=self.imagen_analizada_tk)

    def _reset_zoom(self):
        """Ajusta ambas imágenes al tamaño del canvas manteniendo relación de aspecto."""
        if self.img_orig_pil is not None:
            cw = self.canvas_original.winfo_width()
            ch = self.canvas_original.winfo_height()
            if cw <= 1 or ch <= 1:
                cw, ch = 500, 400
            img_w, img_h = self.img_orig_pil.size
            escala = min(cw / img_w, ch / img_h)
            if escala <= 0:
                escala = 1.0
            self.scale_orig = escala
            new_w = int(img_w * escala)
            new_h = int(img_h * escala)
            self.offset_x_orig = (cw - new_w) // 2
            self.offset_y_orig = (ch - new_h) // 2
            self._redibujar_canvas(self.canvas_original)

        if self.img_anal_cv is not None:
            cw = self.canvas_analizada.winfo_width()
            ch = self.canvas_analizada.winfo_height()
            if cw <= 1 or ch <= 1:
                cw, ch = 500, 400
            img_w, img_h = self.img_anal_cv.shape[1], self.img_anal_cv.shape[0]
            escala = min(cw / img_w, ch / img_h)
            if escala <= 0:
                escala = 1.0
            self.scale_anal = escala
            new_w = int(img_w * escala)
            new_h = int(img_h * escala)
            self.offset_x_anal = (cw - new_w) // 2
            self.offset_y_anal = (ch - new_h) // 2
            self._redibujar_canvas(self.canvas_analizada)

    def _on_configure(self, event):
        """Reacciona al redimensionar canvas para ajustar imágenes."""
        self._reset_zoom()

    def _on_mouse_wheel(self, event):
        """Zoom con rueda del mouse, centrado en cursor. Sincronizado entre ambos canvas."""
        canvas = event.widget
        # Determinar factor de zoom
        if event.delta > 0:
            factor = 1.1  # acercar
        else:
            factor = 0.9  # alejar

        self._apply_zoom(canvas, event.x, event.y, factor)

    def _on_mouse_wheel_linux(self, event):
        """Soporte para rueda del mouse en Linux (Button-4/5)."""
        canvas = event.widget
        if event.num == 4:
            factor = 1.1
        elif event.num == 5:
            factor = 0.9
        else:
            return
        self._apply_zoom(canvas, event.x, event.y, factor)

    def _apply_zoom(self, canvas, mouse_x, mouse_y, factor):
        """Aplica zoom centrado en posición del mouse y sincroniza ambos canvas."""
        # Limitar zoom entre 10% y 800%
        if canvas == self.canvas_original:
            new_scale = self.scale_orig * factor
            if new_scale < 0.1 or new_scale > 8.0:
                return
            # Calcular nuevo offset
            self.offset_x_orig = mouse_x - (mouse_x - self.offset_x_orig) * factor
            self.offset_y_orig = mouse_y - (mouse_y - self.offset_y_orig) * factor
            self.scale_orig = new_scale
            self.scale_anal = new_scale
            self.offset_x_anal = mouse_x - (mouse_x - self.offset_x_anal) * factor
            self.offset_y_anal = mouse_y - (mouse_y - self.offset_y_anal) * factor
            self._redibujar_canvas(self.canvas_original)
            self._redibujar_canvas(self.canvas_analizada)
        else:
            new_scale = self.scale_anal * factor
            if new_scale < 0.1 or new_scale > 8.0:
                return
            self.offset_x_anal = mouse_x - (mouse_x - self.offset_x_anal) * factor
            self.offset_y_anal = mouse_y - (mouse_y - self.offset_y_anal) * factor
            self.scale_anal = new_scale
            self.scale_orig = new_scale
            self.offset_x_orig = mouse_x - (mouse_x - self.offset_x_orig) * factor
            self.offset_y_orig = mouse_y - (mouse_y - self.offset_y_orig) * factor
            self._redibujar_canvas(self.canvas_original)
            self._redibujar_canvas(self.canvas_analizada)

    def _on_mouse_press(self, event):
        """Inicia pan (arrastre) con botón izquierdo."""
        canvas = event.widget
        canvas.configure(cursor="fleur")
        self._dragging = True
        self._last_x = event.x
        self._last_y = event.y

    def _on_mouse_release(self, event):
        """Finaliza pan."""
        canvas = event.widget
        canvas.configure(cursor="")
        self._dragging = False

    def _on_mouse_move(self, event):
        """Mueve imagen durante pan - sincronizado entre ambos canvas."""
        if not self._dragging:
            return
        dx = event.x - self._last_x
        dy = event.y - self._last_y
        self._last_x = event.x
        self._last_y = event.y

        # Sincronizar desplazamiento entre ambos canvas
        self.offset_x_orig += dx
        self.offset_y_orig += dy
        self.offset_x_anal += dx
        self.offset_y_anal += dy

        self._redibujar_canvas(self.canvas_original)
        self._redibujar_canvas(self.canvas_analizada)

    def _configurar_zoom_pan(self):
        """Configura eventos de zoom y pan para ambos canvas."""
        # Eliminar eventos previos enlazando con bindtags
        for canvas in [self.canvas_original, self.canvas_analizada]:
            canvas.unbind("<MouseWheel>")
            canvas.unbind("<Button-4>")
            canvas.unbind("<Button-5>")
            canvas.unbind("<ButtonPress-1>")
            canvas.unbind("<ButtonRelease-1>")
            canvas.unbind("<B1-Motion>")
            canvas.unbind("<Configure>")

            # Configurar eventos
            canvas.bind("<MouseWheel>", self._on_mouse_wheel)
            canvas.bind("<Button-4>", self._on_mouse_wheel_linux)
            canvas.bind("<Button-5>", self._on_mouse_wheel_linux)
            canvas.bind("<ButtonPress-1>", self._on_mouse_press)
            canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
            canvas.bind("<B1-Motion>", self._on_mouse_move)
            canvas.bind("<Configure>", self._on_configure)
