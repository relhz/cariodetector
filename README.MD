# 🧬 Cariodetector

Aplicación de escritorio y nube desarrollada en **Python** para el análisis de imágenes microscópicas de cromosomas humanos mediante técnicas de **visión artificial e inteligencia artificial**.

El sistema utiliza un modelo **YOLO preentrenado** para detectar y clasificar los **24 tipos de cromosomas humanos**: cromosomas 1–22, X e Y.

---

## 📋 Tabla de contenidos

- [Descripción](#-descripción)
- [Características](#-características)
- [Tecnologías utilizadas](#-tecnologías-utilizadas)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Configuración de la base de datos](#-configuración-de-la-base-de-datos)
- [Configuración del modelo](#-configuración-del-modelo)
- [Ejecución](#-ejecución)
- [Flujo de uso](#-flujo-de-uso)
- [Dashboard web(Streamlit)](#-dashboard-web)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Clases de cromosomas](#-clases-de-cromosomas)
- [Errores comunes](#-errores-comunes)
- [Notas](#-notas)
- [Autor](#-autor)

---

## 🔬 Descripción

**Cariodetector** es una aplicación de escritorio orientada al procesamiento y análisis de imágenes microscópicas de cromosomas.

El sistema permite:

- Cargar imágenes microscópicas en formato JPG o PNG.
- Detectar cromosomas automáticamente mediante un modelo YOLO.
- Clasificar cada cromosoma según su tipo.
- Visualizar las detecciones mediante *bounding boxes* y etiquetas.
- Consultar un resumen de los cromosomas detectados.
- Guardar los resultados de los análisis en una base de datos MySQL.
- Consultar el historial de análisis realizados.

---

## ✨ Características

- 🖼️ Carga y visualización de imágenes.
- 🤖 Detección automática mediante YOLO.
- 🧬 Clasificación de 24 tipos de cromosomas.
- 📦 Visualización de *bounding boxes*.
- 📊 Tabla de resultados y resumen de detecciones.
- 💾 Persistencia de resultados mediante MySQL.
- 📚 Historial de análisis anteriores.
- 🖥️ Interfaz gráfica desarrollada con Tkinter.
- 🐍 Implementación completamente realizada en Python.

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| **Python 3.8+** | Lenguaje principal |
| **YOLO** | Detección y clasificación de cromosomas |
| **Tkinter** | Interfaz gráfica |
| **MySQL** | Almacenamiento de resultados |
| **OpenCV** | Procesamiento de imágenes |
| **Pillow** | Manejo y visualización de imágenes |
| **Streamlit** | Dashboard web |
| **Altair / Pandas** | Gráficos y tablas del dashboard |

Las dependencias completas del proyecto se encuentran en [`requirements.txt`](requirements.txt).

---

## 📋 Requisitos

Antes de instalar el proyecto, es necesario contar con:

- **Python 3.8 o superior**
- **MySQL Server**
- **Git** (opcional, pero recomendado)
- Las dependencias especificadas en `requirements.txt`
- El modelo `best_24_chromosomes.pt`

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/lucasscattolin/cariodetector.git
cd cariodetector
```

### 2. Crear un entorno virtual

Se recomienda utilizar un entorno virtual para aislar las dependencias del proyecto.

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

---

## 🗄️ Configuración de la base de datos

El proyecto utiliza **MySQL** para almacenar los resultados de los análisis.

### 1. Crear la base de datos

Ejecutá el script SQL ubicado en:

```text
scripts_sql/crear_bd.sql
```

Por ejemplo, desde MySQL:

```sql
SOURCE scripts_sql/crear_bd.sql;
```

### 2. Configurar las credenciales

Editá el archivo:

```text
utils/db_config.py
```

y configurá los datos correspondientes a tu instalación de MySQL.

Ejemplo:

```python
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "tu_contraseña"
DB_NAME = "nombre_base_datos"
```

---

## 🤖 Configuración del modelo

El proyecto requiere el modelo entrenado:

```text
best_24_chromosomes.pt
```

El archivo debe ubicarse dentro de:

```text
models/
```

La estructura esperada es:

```text
models/
└── best_24_chromosomes.pt
```

Para obtener información adicional sobre el modelo, consultar:

```text
models/README.txt
```

---

## ▶️ Ejecución

Una vez configurado el entorno, la base de datos y el modelo, ejecutá:

```bash
python main.py
```

En Linux/macOS, si tu sistema utiliza `python3`:

```bash
python3 main.py
```

---

## 🔄 Flujo de uso

El funcionamiento básico de la aplicación es el siguiente:

```text
┌─────────────────────┐
│   Abrir programa    │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Seleccionar imagen  │
│      JPG / PNG      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Visualizar imagen   │
│      original       │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│      Analizar       │
│     con YOLO        │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Visualizar detección│
│ + bounding boxes    │
│ + etiquetas         │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Tabla y resumen de  │
│    detecciones      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│   Guardar análisis  │
│      en MySQL       │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│      Historial      │
│ análisis anteriores │
└─────────────────────┘
```

### Pasos principales

1. Abrir la aplicación.
2. Seleccionar una imagen microscópica.
3. Visualizar la imagen original.
4. Ejecutar el análisis.
5. Revisar las detecciones realizadas por el modelo.
6. Consultar la tabla y el resumen de resultados.
7. Guardar el análisis en MySQL.
8. Consultar los análisis anteriores desde el historial.

---
## 📊 Dashboard web

Además de la interfaz de escritorio, el proyecto incluye un dashboard web que usa el mismo modelo YOLO y la misma base de datos MySQL. Permite subir una imagen, detectar los cromosomas, corregir lo que el modelo etiquetó mal y ver estadísticas de todos los análisis guardados.

### *Contenidos* 
| Pestaña| Para qué sirve |
|---|---|
| **Subir y detectar** | Sube una imagen y muestra un semáforo (OK / Revisar) con los motivos. El profesional puede corregir la etiqueta de cada detección o descartarla, guardar el análisis y descargar un informe (HTML) y las detecciones (CSV). |
| **Dashboard** | Indicadores y tablas de todos los análisis guardados, con su estado de revisión. |
| **Historial de sesión** | Pruebas hechas desde que se abrió la página. |
| **Gráficos** | Cariograma, mapa de calor por imagen y par, confianza del modelo y más, con glosario. |
| **Laboratorio** | 	Prueba una imagen con distintos valores de conf e iou y compara cuántos cromosomas detecta. |
| **Sobre el modelo** | Datos del entrenamiento, métricas, curvas y limitaciones. |

---

## 📁 Estructura del proyecto

```text
analizador-cromosomas/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── interfaz/
│   └── interfaz.py
│
├── funciones/
│   ├── analisis_imagen.py
│   ├── modelo_cromosomas.py
│   └── resultados.py
│
├── dashboard/
│   ├── app.py
│   ├── db.py
│   ├── modelo.py
│   ├── requirements.txt
│   ├── README.md
│   └── modelo_info/
│
├── utils/
│   └── db_config.py
│
├── models/
│   ├── best_24_chromosomes.pt
│   └── README.txt
│
├── assets/
│   └── imagenes/
│
└── scripts_sql/
    └── crear_bd.sql
```

### Descripción de los principales archivos

| Archivo / Carpeta | Descripción |
|---|---|
| `main.py` | Punto de entrada de la aplicación |
| `requirements.txt` | Dependencias de Python |
| `interfaz/` | Componentes de la interfaz gráfica |
| `funciones/` | Lógica principal del análisis |
| `analisis_imagen.py` | Procesamiento y análisis de imágenes |
| `modelo_cromosomas.py` | Gestión del modelo de detección |
| `resultados.py` | Procesamiento y presentación de resultados |
| `dashboard/` | Dashboard web en Streamlit (detección, revisión, estadísticas) |
| `utils/` | Configuraciones y utilidades |
| `db_config.py` | Configuración de conexión a MySQL |
| `models/` | Archivos relacionados con el modelo YOLO |
| `assets/` | Recursos e imágenes de ejemplo |
| `scripts_sql/` | Scripts para crear y configurar la base de datos |

---

## 🧬 Clases de cromosomas

El modelo contempla **24 clases**:

| Clase | Tipo |
|---:|---|
| 1 | Cromosoma 1 |
| 2 | Cromosoma 2 |
| 3 | Cromosoma 3 |
| ... | ... |
| 22 | Cromosoma 22 |
| X | Cromosoma X |
| Y | Cromosoma Y |

En términos generales, las clases corresponden a los cromosomas humanos **1–22, X e Y**.

---

## ⚠️ Errores comunes

### `Modelo no encontrado`

Verificá que el archivo:

```text
best_24_chromosomes.pt
```

se encuentre dentro de:

```text
models/
```

---

### `MySQL no disponible`

Comprobá:

- Que MySQL Server esté ejecutándose.
- Que la base de datos haya sido creada.
- Que el usuario y contraseña sean correctos.
- Que la configuración de `utils/db_config.py` sea correcta.

---

### `Imagen inválida`

La aplicación admite imágenes en formatos:

```text
JPG
JPEG
PNG
```

Verificá que el archivo seleccionado sea una imagen válida y que pueda abrirse correctamente.

---

## 🔐 Seguridad

Este proyecto está pensado principalmente para fines académicos.

No se recomienda almacenar credenciales directamente en el código fuente cuando el proyecto vaya a ser publicado.

Antes de subir el proyecto a GitHub, asegurate de incluir archivos sensibles en `.gitignore`, por ejemplo:

```gitignore
venv/
__pycache__/
*.pyc
.env
*.log
```

También se recomienda revisar el repositorio antes del primer `push` para evitar publicar contraseñas, claves API u otras credenciales.

---

## 📝 Notas

- El proyecto utiliza rutas relativas mediante `pathlib`.
- No requiere Docker.
- No utiliza una API web.
- No incluye sistema de autenticación.
- Está preparado para ejecutarse en Windows y Linux.
- El modelo YOLO debe estar disponible localmente para realizar las detecciones.
- La precisión de las detecciones depende del modelo entrenado y de la calidad de las imágenes utilizadas.

---

## 🎓 Proyecto académico

Este proyecto fue desarrollado como **Trabajo Final** y tiene como objetivo integrar conceptos de:

- Programación orientada a objetos.
- Procesamiento de imágenes.
- Visión artificial.
- Inteligencia artificial.
- Detección de objetos.
- Interfaces gráficas.
- Bases de datos relacionales.

---

## 👤 Autores

**Arqueros, Michelle**
**Scattolin, Lucas**
**Sobrado, Paula**

> Proyecto desarrollado con fines académicos.
