import tkinter as tk
from tkinter import ttk
from decimal import Decimal

from utils.db_config import obtener_conexion


def _formatear_valor(valor):
    if valor is None:
        return "-"
    if isinstance(valor, Decimal):
        return f"{float(valor):.4f}"
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return str(valor)


class PestanaEstadisticas(ttk.Frame):
    """Visualización de tablas, vistas y indicadores de la base de datos."""

    VISTAS_DB = (
        "estudios",
        "cromosomas",
        "clasificaciones",
        "resultados",
        "vista_resumen_estudios",
        "vista_estadisticas_clase",
        "vista_estadisticas_globales",
        "vista_estudios_por_estado",
        "vista_clases_globales",
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
        self.var_ind4 = tk.StringVar(value="Estudios en BD: -")

        for var in (self.var_ind1, self.var_ind2, self.var_ind3, self.var_ind4):
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
        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            try:
                cursor.execute("SELECT fn_total_estudios() AS v")
                self.var_ind1.set(f"Total estudios (fn_total_estudios): {cursor.fetchone()['v']}")
            except Exception as e:
                self.var_ind1.set(f"Total estudios (fn_total_estudios): ERROR")

            try:
                cursor.execute("SELECT fn_total_cromosomas() AS v")
                self.var_ind2.set(f"Total cromosomas (fn_total_cromosomas): {cursor.fetchone()['v']}")
            except Exception as e:
                self.var_ind2.set(f"Total cromosomas (fn_total_cromosomas): ERROR")

            try:
                cursor.execute("SELECT fn_promedio_cromosomas_por_estudio() AS v")
                val = cursor.fetchone()['v']
                self.var_ind3.set(f"Promedio cromosomas/estudio (fn_promedio_cromosomas_por_estudio): {val}")
            except Exception as e:
                self.var_ind3.set(f"Promedio cromosomas/estudio (fn_promedio_cromosomas_por_estudio): ERROR")

            try:
                cursor.execute("SELECT COUNT(*) AS v FROM estudios")
                self.var_ind4.set(f"Estudios en BD: {cursor.fetchone()['v']}")
            except Exception as e:
                self.var_ind4.set(f"Estudios en BD: ERROR")
        except Exception as error:
            self.var_mensaje.set(f"Sin conexión o error: {error}")
        finally:
            if cursor is not None:
                cursor.close()
            if conexion is not None:
                conexion.close()

    def _cargar_contenido(self):
        self._limpiar_tabla()
        objeto = self.var_vista.get()

        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM `{objeto}` LIMIT 1000")
            filas = cursor.fetchall()

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
        finally:
            if cursor is not None:
                cursor.close()
            if conexion is not None:
                conexion.close()

    def _limpiar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = ()

    def _actualizar_selectores(self):
        estudios = estadisticas_bd.listar_estudios()

        etiquetas = ["Todos"]
        self._estudios_por_etiqueta = {"Todos": None}

        for estudio in estudios:
            etiqueta = f"{estudio['id_estudio']} - {estudio['imagen_original']}"
            etiquetas.append(etiqueta)
            self._estudios_por_etiqueta[etiqueta] = estudio["id_estudio"]

        self.cmb_estudio.configure(values=etiquetas)

        if self.var_estudio.get() not in etiquetas:
            self.var_estudio.set("Todos")

    def _id_estudio_seleccionado(self):
        return self._estudios_por_etiqueta.get(self.var_estudio.get())

    # ------------------------------------------------------------------
    # Vistas
    # ------------------------------------------------------------------

    def _cargar_vista(self):
        vista = self.var_vista.get()
        id_estudio = self._id_estudio_seleccionado()

        if vista == "Resumen global":
            self._vista_resumen_global()
        elif vista == "Estudios":
            self._vista_estudios(id_estudio)
        elif vista == "Estados":
            self._vista_estados()
        elif vista == "Clases globales":
            self._vista_clases(None)
        elif vista == "Clases por estudio":
            self._vista_clases(id_estudio)
        elif vista == "Detalle de estudio":
            self._vista_detalle(id_estudio)

    def _vista_resumen_global(self):
        resumen = estadisticas_bd.resumen_global()

        self._mostrar_tabla(
            [
                {"clave": "total_estudios", "titulo": "Estudios", "ancho": 110, "formato": _entero},
                {"clave": "total_cromosomas", "titulo": "Cromosomas", "ancho": 130, "formato": _entero},
                {
                    "clave": "promedio_cromosomas_por_estudio",
                    "titulo": "Promedio por estudio",
                    "ancho": 180,
                    "formato": _promedio,
                },
            ],
            [resumen],
        )

        filas = estadisticas_bd.resumen_estudios()

        if not filas:
            self._grafico_mensaje("Todavía no hay estudios guardados.")
            return

        etiquetas = [
            f"#{fila['id_estudio']}  {fila['imagen_original']}"
            for fila in filas
        ]
        valores = [fila["total_detecciones"] for fila in filas]

        self._grafico_barras_h(
            etiquetas,
            valores,
            "Cromosomas detectados por estudio",
            "Cantidad de cromosomas",
        )

    def _vista_estudios(self, id_estudio):
        filas = estadisticas_bd.resumen_estudios(id_estudio)

        self._mostrar_tabla(
            [
                {"clave": "id_estudio", "titulo": "ID", "ancho": 55, "formato": _entero},
                {"clave": "imagen_original", "titulo": "Imagen", "ancho": 160, "formato": _texto},
                {"clave": "fecha_analisis", "titulo": "Fecha", "ancho": 135, "formato": _fecha},
                {"clave": "total_detecciones", "titulo": "Total", "ancho": 60, "formato": _entero},
                {
                    "clave": "confianza_promedio",
                    "titulo": "Conf. prom.",
                    "ancho": 90,
                    "formato": _confianza,
                },
                {"clave": "estado", "titulo": "Estado", "ancho": 100, "formato": _texto},
                {"clave": "cariotipo", "titulo": "Cariotipo", "ancho": 100, "formato": _texto},
                {"clave": "alteracion", "titulo": "Alteración", "ancho": 140, "formato": _texto},
            ],
            filas,
        )

        if not filas:
            self._grafico_mensaje("No hay estudios que coincidan con el filtro.")
            return

        etiquetas = [
            f"#{fila['id_estudio']}  {fila['imagen_original']}"
            for fila in filas
        ]
        valores = [fila["total_detecciones"] for fila in filas]

        self._grafico_barras_h(
            etiquetas,
            valores,
            "Detecciones por estudio",
            "Cantidad de cromosomas",
        )

    def _vista_estados(self):
        filas = estadisticas_bd.estudios_por_estado()
        filas.sort(key=lambda fila: str(fila["estado"]))

        self._mostrar_tabla(
            [
                {"clave": "estado", "titulo": "Estado", "ancho": 150, "formato": _texto},
                {"clave": "cantidad", "titulo": "Estudios", "ancho": 100, "formato": _entero},
            ],
            filas,
        )

        if not filas:
            self._grafico_mensaje("No hay estudios guardados.")
            return

        etiquetas = [fila["estado"] for fila in filas]
        valores = [fila["cantidad"] for fila in filas]
        colores = [self.COLORES.get(etiqueta, "#9e9e9e") for etiqueta in etiquetas]

        self._grafico_torta(etiquetas, valores, colores, "Estudios por estado")

    def _vista_clases(self, id_estudio):
        filas = estadisticas_bd.clases_por_estudio(id_estudio)
        filas.sort(key=lambda fila: clave_orden_clase(fila["clase_detectada"]))

        self._mostrar_tabla(
            [
                {
                    "clave": "clase_detectada",
                    "titulo": "Clase",
                    "ancho": 90,
                    "formato": _texto,
                },
                {"clave": "cantidad", "titulo": "Cantidad", "ancho": 90, "formato": _entero},
                {
                    "clave": "confianza_promedio",
                    "titulo": "Conf. prom.",
                    "ancho": 100,
                    "formato": _confianza,
                },
                {
                    "clave": "confianza_minima",
                    "titulo": "Conf. mín.",
                    "ancho": 100,
                    "formato": _confianza,
                },
                {
                    "clave": "confianza_maxima",
                    "titulo": "Conf. máx.",
                    "ancho": 100,
                    "formato": _confianza,
                },
            ],
            filas,
        )

        if not filas:
            self._grafico_mensaje("No hay cromosomas para el filtro seleccionado.")
            return

        etiquetas = [fila["clase_detectada"] for fila in filas]
        valores = [fila["cantidad"] for fila in filas]

        if id_estudio is None:
            titulo = "Cromosomas por clase (todos los estudios)"
        else:
            titulo = f"Cromosomas por clase (estudio #{id_estudio})"

        self._grafico_barras_h(etiquetas, valores, titulo, "Cantidad")

    def _vista_detalle(self, id_estudio):
        if id_estudio is None:
            self.var_mensaje.set("Seleccione un estudio para ver el detalle.")
            self._limpiar_tabla()
            self._grafico_mensaje("Seleccione un estudio en el selector.")
            return

        clases, confianzas = estadisticas_bd.detalle_estudio(id_estudio)
        clases.sort(key=lambda fila: clave_orden_clase(fila["clase_detectada"]))

        self._mostrar_tabla(
            [
                {
                    "clave": "clase_detectada",
                    "titulo": "Clase",
                    "ancho": 90,
                    "formato": _texto,
                },
                {"clave": "cantidad", "titulo": "Cantidad", "ancho": 90, "formato": _entero},
                {
                    "clave": "confianza_promedio",
                    "titulo": "Conf. prom.",
                    "ancho": 100,
                    "formato": _confianza,
                },
                {
                    "clave": "confianza_minima",
                    "titulo": "Conf. mín.",
                    "ancho": 100,
                    "formato": _confianza,
                },
                {
                    "clave": "confianza_maxima",
                    "titulo": "Conf. máx.",
                    "ancho": 100,
                    "formato": _confianza,
                },
            ],
            clases,
        )

        self.figura.clear()

        if not clases:
            self._grafico_mensaje("El estudio seleccionado no tiene detecciones.")
            return

        eje_clases = self.figura.add_subplot(1, 2, 1)
        etiquetas = [fila["clase_detectada"] for fila in clases]
        valores = [fila["cantidad"] for fila in clases]
        posiciones = range(len(etiquetas))

        eje_clases.barh(list(posiciones), valores, color="#4c78a8")
        eje_clases.set_yticks(list(posiciones))
        eje_clases.set_yticklabels(etiquetas, fontsize=8)
        eje_clases.invert_yaxis()
        eje_clases.set_title(f"Clases del estudio #{id_estudio}", fontsize=10)
        eje_clases.set_xlabel("Cantidad")
        eje_clases.grid(axis="x", alpha=0.3)
        eje_clases.margins(x=0.12)

        for posicion, valor in zip(posiciones, valores):
            eje_clases.text(valor, posicion, f" {valor}", va="center", fontsize=8)

        eje_conf = self.figura.add_subplot(1, 2, 2)

        if confianzas:
            eje_conf.hist(confianzas, bins=10, range=(0, 1), color="#f58518", edgecolor="white")
            eje_conf.set_xlim(0, 1)
            eje_conf.set_title("Distribución de confianza", fontsize=10)
            eje_conf.set_xlabel("Confianza")
            eje_conf.set_ylabel("Cantidad")
            eje_conf.grid(axis="y", alpha=0.3)
        else:
            eje_conf.axis("off")
            eje_conf.text(
                0.5,
                0.5,
                "Sin datos de confianza",
                ha="center",
                va="center",
                color="#666",
            )

        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Tabla
    # ------------------------------------------------------------------

    def _limpiar_tabla(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=())

    def _mostrar_tabla(self, columnas, filas):
        self._limpiar_tabla()

        claves = [columna["clave"] for columna in columnas]
        self.tree.configure(columns=claves)

        for columna in columnas:
            self.tree.heading(columna["clave"], text=columna["titulo"])
            self.tree.column(
                columna["clave"],
                width=columna.get("ancho", 100),
                anchor=columna.get("anchor", tk.CENTER),
            )

        for indice, fila in enumerate(filas):
            valores = []
            for columna in columnas:
                valor = fila.get(columna["clave"])
                formato = columna.get("formato")
                valores.append(formato(valor) if formato else _texto(valor))

            etiqueta = "par" if indice % 2 == 0 else "impar"
            self.tree.insert("", tk.END, values=valores, tags=(etiqueta,))

        self.tree.tag_configure("par", background="#fafafa")
        self.tree.tag_configure("impar", background="#ffffff")

    # ------------------------------------------------------------------
    # Gráficos
    # ------------------------------------------------------------------

    def _grafico_mensaje(self, texto):
        self.figura.clear()
        eje = self.figura.add_subplot(111)
        eje.axis("off")
        eje.text(
            0.5,
            0.5,
            texto,
            ha="center",
            va="center",
            fontsize=11,
            color="#666",
            wrap=True,
        )
        self.canvas.draw_idle()

    def _grafico_barras_h(self, etiquetas, valores, titulo, xlabel):
        self.figura.clear()
        eje = self.figura.add_subplot(111)

        posiciones = range(len(etiquetas))

        eje.barh(list(posiciones), valores, color="#4c78a8")
        eje.set_yticks(list(posiciones))
        eje.set_yticklabels(etiquetas, fontsize=8)
        eje.invert_yaxis()
        eje.set_title(titulo, fontsize=11)
        eje.set_xlabel(xlabel)
        eje.grid(axis="x", alpha=0.3)
        eje.margins(x=0.12)

        for posicion, valor in zip(posiciones, valores):
            eje.text(valor, posicion, f" {valor}", va="center", fontsize=8)

        self.canvas.draw_idle()

    def _grafico_torta(self, etiquetas, valores, colores, titulo):
        self.figura.clear()
        eje = self.figura.add_subplot(111)

        eje.pie(
            valores,
            labels=etiquetas,
            colors=colores,
            autopct="%1.1f%%",
            startangle=90,
        )
        eje.set_title(titulo, fontsize=11)
        eje.axis("equal")

        self.canvas.draw_idle()
