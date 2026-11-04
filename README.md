# Cariodetector

## Información del proyecto

| Dato | Información |
|---|---|
| **Título** | Cariodetector — Sistema de análisis de cromosomas |
| **Materia** | Proyecto Integrador |
| **Curso** | 3er Año |
| **Institución** | ISFT N. 204 |
| **Fecha de entrega** | 02/11/2026 |

**Integrantes**

- Arqueros, Michelle
- Scattolin, Lucas
- Sobrado, Paula

---

## Descripción del proyecto

Cariodetector es una aplicación para analizar imágenes microscópicas de
cromosomas humanos mediante un modelo YOLO. El proyecto incluye una aplicación
de escritorio y un dashboard web, y permite:

- Cargar imágenes microscópicas en formato JPG o PNG.
- Detectar cromosomas y clasificarlos en 24 clases: cromosomas 1–22, X e Y.
- Visualizar las detecciones con recuadros, etiquetas y valores de confianza.
- Revisar recortes individuales y corregir manualmente las clases detectadas.
- Registrar estudios, clasificaciones, cariotipos, alteraciones y observaciones.
- Consultar el historial de análisis y estadísticas.
- Usar un dashboard web para cargar imágenes, revisar resultados y explorar datos.
- Guardar y consultar los resultados en una base de datos MySQL.

> **Aviso:** Cariodetector es una herramienta de apoyo y no reemplaza la
> evaluación de un profesional. El análisis de alteraciones se limita a cambios
> numéricos; no evalúa alteraciones estructurales.

---

## Software externo requerido

| Software | ¿Requerido? | Uso |
|----------|-------------|-----|
| Python 3.8 o superior | Sí | Lenguaje y entorno de ejecución. Se recomienda Python 3.10 a 3.12. |
| MySQL Server 8.0 o superior | Sí | Almacenamiento de estudios y resultados. |
| Modelo YOLO entrenado | Sí | `models/best_24_chromosomes.pt`, necesario para analizar imágenes. |
| Git | Opcional | Recomendado para clonar el repositorio. |

El modelo debe contener las 24 clases esperadas.

---

## Instalación de librerías Python

Desde la carpeta raíz del proyecto, instala las dependencias:

```bash
pip install -r requirements.txt
```

---

## Archivos y carpetas del proyecto

```text
main.py                         Punto de entrada: abre Tkinter y lanza el dashboard
requirements.txt                Dependencias de Python del proyecto
README.md                       Este archivo

assets/
├── imagenes_prueba/            Imágenes de ejemplo para analizar
└── imagenes_analizadas/        Imágenes originales y resultados generados

nucleo/                         Lógica compartida por Tkinter y el dashboard
├── constantes.py               Clases, umbrales, colores y rutas comunes
├── modelo.py                   Carga única del modelo YOLO y detección
├── detecciones.py              Formato canónico, conteos, revisión y cariotipo
├── analisis_imagen.py          Servicio de análisis y resumen de una imagen
├── dibujo.py                   Dibujo de cajas, recortes y cariograma
├── db.py                       Conexión y operaciones de MySQL
├── guardado.py                 Preparación y guardado de un análisis
├── informe.py                  Informe HTML y conversión de imágenes
└── modelo_info.py              Fichas y registros de entrenamiento

graficos/                       Gráficos Altair del dashboard, sin Streamlit
├── tema.py                     Tema, escalas y ejes comunes
├── cariotipo.py                Cariograma, mapa de calor, alertas y confianza
├── laboratorio.py              Curva de barrido de IoU
├── modelo.py                   Curvas y comparación de entrenamientos
└── revision.py                 Confusiones corregidas por profesionales

interfaz/                       Interfaz gráfica de escritorio (Tkinter)
├── interfaz.py                 Ventana principal, historial y revisión
└── pestana_estadisticas.py     Tablas e indicadores estadísticos

dashboard/                      Dashboard web en Streamlit
├── app.py                      Página web (solo interfaz)
├── componentes.py              Visor con zoom y avisos reutilizables
└── lanzador.py                 Arranque y cierre automático de Streamlit

models/                         Modelo de detección YOLO y sus métricas
├── best_24_chromosomes.pt      Pesos requeridos para analizar imágenes
├── metricas/                   Registros CSV de los entrenamientos
│   ├── results_yolov8l.csv
│   └── results_yolov8s.csv
└── README.md                   Información sobre el modelo y sus clases

notebooks/
└── colab_entrenamiento_YOLO.ipynb   Entrenamiento del modelo en Google Colab

docs/                           Documentación y presentación del proyecto
├── Informe_Proyecto_Integrador.pdf
└── Presentacion_Proyecto_Integrador.pptx

tests/
└── test_nucleo.py              Pruebas de resumen, análisis y guardado

scripts_sql/
└── crear_bd.sql                Creación y configuración de la base `cariotipos`
```

---

## Pruebas

Las pruebas de la lógica compartida usan solo la biblioteca estándar. Desde la
raíz del proyecto:

```bash
python -m unittest discover -s tests
```

---

## Configuración de la base de datos

1. Instala y pon en marcha MySQL Server 8.0 o superior.
2. Desde la carpeta raíz, ejecuta el script de creación:

   ```bash
   mysql -u root -p < scripts_sql/crear_bd.sql
   ```

   También puedes abrir y ejecutar `scripts_sql/crear_bd.sql` desde MySQL
   Workbench.

3. El script crea la base de datos `cariotipos`, sus tablas y los objetos SQL
   necesarios para guardar y consultar estudios.
4. Revisa y ajusta las credenciales de MySQL en `nucleo/db.py` para que
   coincidan con tu instalación local. El archivo contiene valores de ejemplo.

El dashboard usa la misma configuración y la misma lógica de guardado que la
interfaz Tkinter. También permite definir las variables de entorno `DB_HOST`,
`DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`.

---

## Configuración del modelo

El archivo `best_24_chromosomes.pt` debe estar ubicado en:

```text
models/best_24_chromosomes.pt
```

El modelo debe tener 24 clases compatibles con el orden esperado por el
proyecto: cromosomas 1–22, X e Y. Sin este archivo no es posible analizar
imágenes. Consulta [models/README.md](models/README.md) para más información.

---

## Cómo ejecutar el proyecto

### Aplicación de escritorio + dashboard

1. Instala Python y las dependencias.
2. Configura MySQL y ejecuta `scripts_sql/crear_bd.sql`.
3. Revisa las credenciales en `nucleo/db.py`.
4. Confirma que el modelo esté en `models/best_24_chromosomes.pt`.
5. Desde la carpeta raíz, ejecuta:

   ```bash
   python main.py
   ```

   Esto abre la interfaz Tkinter y, automáticamente, inicia el dashboard en un
   puerto local libre y lo abre en el navegador. Al cerrar la ventana de
   Tkinter también se detiene el dashboard.

### Dashboard web por separado

El dashboard también puede ejecutarse solo, por ejemplo durante el desarrollo.
Usa las mismas dependencias del proyecto (`requirements.txt` de la raíz).

1. Ejecuta Streamlit:

   ```bash
   python -m streamlit run dashboard/app.py
   ```

2. Abre en el navegador la dirección local que indique Streamlit. Por defecto,
   es [`http://localhost:8501`](http://localhost:8501).

---

## Flujo de uso

1. Abre la aplicación y selecciona una imagen microscópica JPG o PNG.
2. Ejecuta el análisis y revisa las detecciones, etiquetas y confianza.
3. Corrige las clases que sea necesario antes de guardar.
4. Guarda el estudio en MySQL.
5. Desde el historial, revisa la clasificación y completa el cariotipo,
   alteración u observaciones.
6. Consulta el historial y las estadísticas desde la aplicación o el dashboard.

El dashboard también permite cargar imágenes, revisar o descartar detecciones,
guardar análisis y descargar informes HTML y detecciones CSV. La aplicación de
escritorio permite además generar el mismo informe HTML desde el botón
**Informe HTML**, y el dashboard permite corregir estudios ya guardados desde la
pestaña **Revisar estudios**.

---

## Notas adicionales y aclaraciones

- Las imágenes de ejemplo se encuentran en `assets/imagenes_prueba/`.
- Las imágenes analizadas y sus resultados se almacenan en
  `assets/imagenes_analizadas/`.
- El tiempo de análisis depende del tamaño de la imagen y del equipo utilizado.
- El modelo trabaja con las clases de cromosomas 1–22, X e Y.
- Si no hay conexión con la base de datos, el dashboard muestra datos de
  demostración. Estos datos no son resultados reales.
- La confianza mínima, el IoU y el umbral de revisión están definidos en
  `nucleo/constantes.py` y los comparten ambas interfaces.
- Todo resultado debe ser revisado por un profesional.

---

## Dificultades conocidas y soluciones

### 1. No se encuentra el modelo

- Verifica que `models/best_24_chromosomes.pt` exista y sea accesible.
- Consulta [models/README.md](models/README.md) para comprobar el modelo esperado.

### 2. No se puede conectar con MySQL

- Verifica que MySQL Server esté ejecutándose.
- Confirma usuario, contraseña, host y puerto en `nucleo/db.py` o en las
  variables de entorno del dashboard.
- Comprueba que se haya ejecutado `scripts_sql/crear_bd.sql`.

### 3. Faltan módulos de Python

- Activa el entorno virtual, si estás utilizando uno.
- Ejecuta `pip install -r requirements.txt`.

### 4. El dashboard muestra datos de demostración

- Verifica la conexión a MySQL y las credenciales configuradas.
