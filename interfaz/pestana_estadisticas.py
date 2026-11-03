import tkinter as tk
from tkinter import ttk
from decimal import Decimal

from nucleo.db import obtener_conexion


def _formatear_valor(valor):
    if valor is None:
        return "-"
    if isinstance(valor, Decimal):
        return f"{float(valor):.4f}"
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return str(valor)


class PestanaEstadisticas(ttk.Frame):
    """Visualización de tablas, vistas e indicadores de la base de datos."""

    VISTAS_DB = (
        "estudios",
        "cromosomas",
        "clasificaciones",
        "resultados",
        "correcciones",
        "vista_resumen_estudios",
        "vista_estadisticas_globales",
    )

    def __init__(self, master):
        super().__init__(master, padding="10")

        self._crear_widgets()
        self.actualizar()

    def _crear_widgets(self):
        barra = ttk.Frame(self)
        barra.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(barra, text="Mostrar:").pack(side=tk.LEFT)

        self.var_vista = tk.StringVar(value=self.VISTAS_DB[0])
        self.cmb_vista = ttk.Combobox(
            barra,
            textvariable=self.var_vista,
            values=self.VISTAS_DB,
            state="readonly",
            width=28,
        )
        self.cmb_vista.pack(side=tk.LEFT, padx=(5, 15))
        self.cmb_vista.bind("<<ComboboxSelected>>", lambda _e: self.actualizar())

        ttk.Button(barra, text="Actualizar", command=self.actualizar).pack(side=tk.LEFT)

        self.var_mensaje = tk.StringVar(value="")
        ttk.Label(
            barra,
            textvariable=self.var_mensaje,
            foreground="#a33",
        ).pack(side=tk.RIGHT)

        indicadores = ttk.LabelFrame(self, text="Indicadores (UDF / consultas)", padding=5)
        indicadores.pack(fill=tk.X, pady=(0, 8))

        self.var_ind1 = tk.StringVar(value="Total estudios (fn_total_estudios): -")
        self.var_ind2 = tk.StringVar(value="Total cromosomas (fn_total_cromosomas): -")
        self.var_ind3 = tk.StringVar(value="Promedio cromosomas/estudio (fn_promedio_cromosomas_por_estudio): -")

        for var in (self.var_ind1, self.var_ind2, self.var_ind3):
            ttk.Label(indicadores, textvariable=var).pack(anchor=tk.W)

        frame_tabla = ttk.LabelFrame(self, text="Contenido", padding=5)
        frame_tabla.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(frame_tabla, show="headings")
        scroll_y = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame_tabla, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        frame_tabla.rowconfigure(0, weight=1)
        frame_tabla.columnconfigure(0, weight=1)

    def actualizar(self):
        self.var_mensaje.set("")
        self._cargar_indicadores()
        self._cargar_contenido()

    def _cargar_indicadores(self):
        try:
            conexion = obtener_conexion()
            try:
                cursor = conexion.cursor(dictionary=True)
                cursor.execute("""
                    SELECT total_estudios, total_cromosomas,
                           promedio_cromosomas_por_estudio
                    FROM vista_estadisticas_globales
                """)
                fila = cursor.fetchone() or {}
            finally:
                conexion.close()

            self.var_ind1.set(
                f"Total estudios (fn_total_estudios): {fila.get('total_estudios', '-')}"
            )
            self.var_ind2.set(
                f"Total cromosomas (fn_total_cromosomas): {fila.get('total_cromosomas', '-')}"
            )
            self.var_ind3.set(
                "Promedio cromosomas/estudio "
                f"(fn_promedio_cromosomas_por_estudio): "
                f"{fila.get('promedio_cromosomas_por_estudio', '-')}"
            )
        except Exception as error:
            self.var_mensaje.set(f"Sin conexión o error: {error}")

    def _cargar_contenido(self):
        self._limpiar_tabla()
        objeto = self.var_vista.get()

        try:
            conexion = obtener_conexion()
            try:
                cursor = conexion.cursor(dictionary=True)
                cursor.execute(f"SELECT * FROM `{objeto}` LIMIT 1000")
                filas = cursor.fetchall()
            finally:
                conexion.close()

            if not filas:
                self.var_mensaje.set("Sin datos para mostrar (límite 1000).")
                return

            columnas = list(filas[0].keys())
            self.tree["columns"] = columnas
            for col in columnas:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=120, minwidth=80, stretch=True)

            for fila in filas:
                valores = [_formatear_valor(fila.get(col)) for col in columnas]
                self.tree.insert("", tk.END, values=valores)
        except Exception as error:
            self.var_mensaje.set(f"Error al consultar {objeto}: {error}")

    def _limpiar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = ()
