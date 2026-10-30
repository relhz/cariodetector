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
- [Autores](#-autores)

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
- Revisar y corregir la clasificación de cada cromosoma.
- Registrar el cariotipo, las alteraciones y las observaciones del estudio.
- Consultar el historial de análisis realizados.
- Visualizar tablas y estadísticas en una pestaña aparte.

---

## ✨ Características

- 🖼️ Carga y visualización de imágenes.
- 🤖 Detección automática mediante YOLO.
- 🧬 Clasificación de 24 tipos de cromosomas.
- 📦 Visualización de *bounding boxes*.
- 📊 Tabla de resultados y resumen de detecciones.
- 🔍 Recorte ampliado de cada cromosoma para revisar su clasificación.
- 📚 Historial de análisis anteriores.

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
- **MySQL Server 8.0 o superior** (el script usa `utf8mb4_0900_ai_ci` y `JSON_TABLE`)
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

El script ubicado en:

```text
scripts_sql/crear_bd.sql
```

crea la base de datos `cariotipos` con las tablas `estudios`, `cromosomas`,
`clasificaciones` y `resultados`, además de las funciones de estadísticas, los
procedimientos de alta y las vistas de consulta.

El script es idempotente: se puede volver a ejecutar para actualizar las
funciones, procedimientos y vistas. También completa las clasificaciones
provisionales de los estudios que se hayan guardado antes de que existiera
esa funcionalidad.

Podés ejecutarlo desde el cliente MySQL:
v
```bash
mysql -u root -p < scripts_sql/crear_bd.sql
```

### 2. Configurar las credenciales

Editá el archivo:

```text
utils/db_config.py
```

y configurá los datos correspondientes a tu instalación de MySQL.

Ejemplo:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "tu_contraseña",
    "database": "cariotipos",
    "charset": "utf8mb4",
    "collation": "utf8mb4_0900_ai_ci",
    "autocommit": True,
}
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
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Revisar estudio    │
│ clasificación +     │
│ cariotipo           │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│   Estadísticas y    │
│       tablas        │
└─────────────────────┘
```

### Pasos principales

1. Abrir la aplicación.
2. Seleccionar una imagen microscópica.
3. Visualizar la imagen original.
4. Ejecutar el análisis.
5. Revisar las detecciones: seleccionar una fila, ver el recorte del cromosoma y corregir su clase si hace falta.
6. Consultar la tabla y el resumen de resultados.
7. Guardar el análisis en MySQL.
8. Consultar los análisis anteriores desde el historial.
9. Abrir la revisión de un estudio, corregir la asignación de cromosomas y guardar el cariotipo.
10. Consultar la pestaña **Estadísticas** para ver las tablas y resúmenes.

### Revisión en la pestaña Detecciones

Después de analizar la imagen, la pestaña **Detecciones** permite revisar cada
cromosoma antes de guardar:

- Al seleccionar una fila se muestra un **recorte ampliado de la imagen original**
  centrado en esa detección.
- El panel indica la clase detectada por el modelo y su confianza.
- Con el selector **Asignar** se puede elegir el tipo correcto (`A1`…`G22`, `X`, `Y`).
- **Aplicar** reemplaza la clase de esa detección; **Restaurar** vuelve a la clase
  original del modelo.
- Las filas corregidas se marcan con `*` y un fondo resaltado.
- El resumen y las etiquetas de la imagen analizada se actualizan automáticamente.

La clase corregida es la que se guarda en la base: queda tanto en
`cromosomas.clase_detectada` como en `clasificaciones.cromosoma_asignado`.

### Revisión de un estudio

Al guardar un análisis, la aplicación crea una **clasificación provisional** por
cada cromosoma usando la clase que detectó el modelo. Desde el historial, el
botón **Revisar estudio** (o un doble clic sobre una fila) abre una ventana
donde se puede:

- Seleccionar uno o varios cromosomas y cambiar su asignación (`A1`…`G22`, `X`, `Y`).
- Generar automáticamente un cariotipo sugerido a partir de las asignaciones.
- Completar el cariotipo, la alteración y las observaciones.
- Guardar la revisión, que deja el estudio en estado `FINALIZADO`.

---
## 📊 Dashboard web

Además de la interfaz de escritorio, el proyecto incluye un dashboard web que usa el mismo modelo YOLO y la misma base de datos MySQL. Permite subir una imagen, detectar los cromosomas, corregir lo que el modelo etiquetó mal y ver estadísticas de todos los análisis guardados.

### *Contenidos* 
| Pestaña| Para qué sirve |
|---|---|
| **Subir y detectar** | Sube una imagen y muestra un semáforo (OK / Revisar) con los motivos. El profesional puede corregir la etiqueta de cada detección o descartarla, guardar el análisis y descargar un informe (HTML) y las detecciones (CSV). |
| **Dashboard** | Indicadores y tablas de todos los análisis guardados, con su estado de revisión. |
| **Gráficos** | Cariograma, mapa de calor por imagen y par, confianza del modelo y más, con glosario. |
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
│   ├── interfaz.py
│   └── pestana_estadisticas.py
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
| `interfaz.py` | Ventana principal, guardado e historial |
| `pestana_estadisticas.py` | Pestaña de tablas e indicadores |
| `funciones/` | Lógica principal del análisis |
| `analisis_imagen.py` | Procesamiento y análisis de imágenes |
| `modelo_cromosomas.py` | Gestión del modelo de detección |
| `resultados.py` | Procesamiento y presentación de resultados |
| `dashboard/` | Dashboard web en Streamlit (detección, revisión, estadísticas) |
| `resultados.py` | Procesamiento, clasificación y presentación de resultados |
| `utils/` | Configuraciones y utilidades |
| `db_config.py` | Configuración de conexión a MySQL |
| `models/` | Archivos relacionados con el modelo YOLO |
| `assets/` | Recursos e imágenes de ejemplo |
| `scripts_sql/` | Scripts para crear y configurar la base de datos |

---

## 🧬 Clases de cromosomas

El modelo contempla **24 clases**. Las etiquetas que devuelve el modelo usan
los grupos Denver con el número de cromosoma:

| Clase | Cromosoma |
|---|---|
| A1, A2, A3 | Cromosomas 1–3 |
| B4, B5 | Cromosomas 4–5 |
| C6 … C12 | Cromosomas 6–12 |
| D13, D14, D15 | Cromosomas 13–15 |
| E16, E17, E18 | Cromosomas 16–18 |
| F19, F20 | Cromosomas 19–20 |
| G21, G22 | Cromosomas 21–22 |
| X | Cromosoma X |
| Y | Cromosoma Y |

En términos generales, las clases corresponden a los cromosomas humanos **1–22, X e Y**.

---

## 👤 Autores

**Arqueros, Michelle**
**Scattolin, Lucas**
**Sobrado, Paula**

> Proyecto desarrollado con fines académicos.
