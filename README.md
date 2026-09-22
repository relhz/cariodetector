# 🧬 CarioDetector

Sistema de análisis y detección de cromosomas a partir de imágenes digitales.

## 📌 Descripción

**CarioDetector** es un proyecto académico desarrollado como propuesta propia del equipo para el Proyecto Integrador 2026 de la carrera **Ciencia de Datos e Inteligencia Artificial – ISFT N.º 204**.

El objetivo del proyecto es desarrollar una aplicación capaz de trabajar con imágenes de cromosomas y proporcionar herramientas para su procesamiento, detección y análisis.

El sistema será desarrollado de manera incremental, comenzando con un **MVP (Producto Mínimo Viable)** y agregando funcionalidades a medida que avance el proyecto.

> **Importante:** este proyecto corresponde a una propuesta propia del equipo y no al proyecto de análisis de titulares y noticias propuesto por la cátedra.

La propuesta propia debe integrar los contenidos mínimos establecidos para el proyecto integrador: **programación estructurada, programación orientada a objetos, acceso y persistencia en una base de datos e interfaz gráfica integrada**.

---

## 👥 Equipo

|     Integrante    | Rol principal |
| ----------------- | ------------- |
| Paula Sobrado     | Desarrollo    |
| Michelle Arqueros | Desarrollo    |
| Lucas Scattolin   | Desarrollo    |

> Los roles son orientativos. Todos los integrantes deben comprender la arquitectura general, las decisiones tomadas y la integración de los distintos módulos del sistema.

---

## 🏗️ Estado del proyecto

🚧 **En desarrollo**

El proyecto se desarrolla de manera incremental.

### MVP

El primer objetivo es construir una versión mínima y funcional que permita:

* [ ] Cargar una imagen.
* [ ] Procesar la imagen.
* [ ] Detectar cromosomas.
* [ ] Visualizar los resultados.
* [ ] Almacenar la información necesaria en la base de datos.
* [ ] Integrar los módulos mediante una interfaz gráfica.

Las funcionalidades podrán ampliarse posteriormente sin modificar innecesariamente la estructura inicial del proyecto.

---

## 📁 Estructura del proyecto

```text
cariodetector/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── main.py
│   │
│   ├── interfaz/
│   │   └── ...
│   │
│   ├── analisis/
│   │   └── ...
│   │
│   ├── modelos/
│   │   └── ...
│   │
│   ├── base_datos/
│   │   └── ...
│   │
│   └── utils/
│       └── ...
│
├── database/
│   ├── schema.sql
│   ├── procedures.sql
│   └── seed.sql
│
├── assets/
│   ├── imagenes/
│   └── ejemplos/
│
├── tests/
│   └── ...
│
└── docs/
    ├── DER/
    ├── decisiones/
    └── informe/
```

### Descripción de las carpetas

#### `src/`

Contiene el código fuente principal de la aplicación.

Todo código Python que forme parte de la aplicación debe ubicarse dentro de esta carpeta.

---

#### `src/interfaz/`

Contiene todo lo relacionado con la **interfaz gráfica**.

Por ejemplo:

* ventanas;
* formularios;
* botones;
* visualización de imágenes;
* presentación de resultados;
* interacción con el usuario.

La interfaz debe comunicarse con los demás módulos sin contener innecesariamente la lógica principal del sistema.

---

#### `src/analisis/`

Contiene la lógica relacionada con el **procesamiento y análisis de las imágenes**.

Aquí se incorporarán progresivamente las funciones necesarias para:

* procesamiento de imágenes;
* detección de cromosomas;
* segmentación;
* extracción de características;
* clasificación;
* otros algoritmos que se incorporen al proyecto.

---

#### `src/modelos/`

Contiene las **clases y modelos del sistema**.

Esta carpeta será utilizada principalmente para implementar la programación orientada a objetos necesaria para representar las entidades y comportamientos propios del proyecto.

---

#### `src/base_datos/`

Contiene todo lo relacionado con el acceso a la base de datos.

Por ejemplo:

* conexión;
* consultas;
* inserciones;
* actualizaciones;
* recuperación de información;
* funciones auxiliares relacionadas con persistencia.

Las credenciales de acceso **no deben subirse al repositorio**.

---

#### `src/utils/`

Contiene funciones y herramientas auxiliares que puedan ser reutilizadas por diferentes módulos.

No debe utilizarse esta carpeta para colocar código que tenga una responsabilidad específica de otro módulo.

---

#### `database/`

Contiene los scripts SQL necesarios para reproducir la base de datos.

```text
database/
├── schema.sql
├── procedures.sql
└── seed.sql
```

* `schema.sql`: creación de la base de datos y tablas.
* `procedures.sql`: procedimientos almacenados y otras funciones SQL.
* `seed.sql`: datos iniciales o de prueba, si fueran necesarios.

La idea es que una persona pueda reconstruir la base de datos utilizando los archivos del repositorio.

---

#### `assets/`

Contiene los recursos utilizados por la aplicación.

```text
assets/
├── imagenes/
└── ejemplos/
```

Las imágenes utilizadas por el programa deben almacenarse dentro del proyecto y referenciarse mediante **rutas relativas**, evitando rutas específicas de una computadora.

Ejemplo:

```text
❌ C:\Users\Usuario\Desktop\CarioDetector\imagen.jpg

✅ assets/imagenes/imagen.jpg
```

---

#### `tests/`

Contiene las pruebas realizadas sobre los distintos módulos del sistema.

A medida que el proyecto crezca, se incorporarán pruebas para verificar que las funciones principales continúen funcionando correctamente.

---

#### `docs/`

Contiene documentación complementaria del proyecto.

```text
docs/
├── DER/
├── decisiones/
└── informe/
```

Aquí se podrán almacenar:

* Diagramas Entidad-Relación;
* decisiones de diseño;
* documentación técnica;
* documentación del proyecto;
* informe final.

---

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd cariodetector
```

### 2. Crear un entorno virtual

```bash
python -m venv venv
```

Activarlo según el sistema operativo.

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 🗄️ Configuración de la base de datos

La configuración de la base de datos debe realizarse de manera local.

**No subir contraseñas, claves API ni credenciales al repositorio.**

Los scripts necesarios para crear la estructura de la base de datos se encuentran en:

```text
database/
```

La configuración específica de cada entorno deberá documentarse cuando se establezca definitivamente la tecnología utilizada.

---

## ▶️ Ejecución

El punto de entrada principal de la aplicación será:

```text
src/main.py
```

Para ejecutar el proyecto:

```bash
python src/main.py
```

> Este comando podrá modificarse a medida que se defina la arquitectura definitiva del proyecto.

---

# 🌿 Metodología de trabajo con Git

El proyecto utiliza un modelo de trabajo basado en **branches**.

## Branch principal

```text
main
```

La branch `main` representa una versión estable del proyecto.

**No se debe trabajar directamente sobre `main`.**

---

## Branches de desarrollo

Cada funcionalidad o modificación importante debe desarrollarse en una branch independiente.

Ejemplos:

```text
feature/interfaz-inicial
feature/deteccion-cromosomas
feature/base-datos
feature/modelo-cromosoma
fix/error-carga-imagen
docs/der
```

### Convención

```text
tipo/descripcion
```

Tipos principales:

* `feature/` → nueva funcionalidad.
* `fix/` → corrección de errores.
* `docs/` → documentación.
* `refactor/` → reorganización o mejora del código sin cambiar su comportamiento.

---

## 🔄 Flujo de trabajo

Antes de comenzar una tarea:

```bash
git checkout main
git pull origin main
```

Crear una nueva branch:

```bash
git checkout -b feature/nombre-de-la-tarea
```

Realizar los cambios y probarlos.

Luego:

```bash
git add .
git commit -m "feat: descripcion del cambio"
git push -u origin feature/nombre-de-la-tarea
```

Finalmente, crear un **Pull Request hacia `main`**.

Otro integrante deberá revisar los cambios antes del merge.

---

## 📝 Commits

Los commits deben describir claramente qué se modificó.

### Ejemplos

```text
feat: agrega carga de imagen
feat: implementa deteccion inicial de cromosomas
fix: corrige ruta de imagen
docs: agrega diagrama DER
refactor: reorganiza modulo de analisis
test: agrega pruebas para deteccion
```

Evitar commits como:

```text
cambios
arreglos
cosas
funciona
final
final2
ahora_si
```

---

## 🔀 Pull Requests

Antes de realizar un merge hacia `main`, verificar:

* [ ] El código funciona.
* [ ] La funcionalidad fue probada.
* [ ] No existen rutas absolutas.
* [ ] No se subieron credenciales.
* [ ] No se modificaron archivos innecesariamente.
* [ ] El código está ubicado en la carpeta correspondiente.
* [ ] El README se actualizó si el cambio afecta la instalación o utilización.
* [ ] Otro integrante revisó el Pull Request.

---

## 🔐 Archivos que NO deben subirse

No subir información sensible o archivos generados localmente.

Ejemplos:

```text
.env
venv/
__pycache__/
*.pyc
*.log
db_config.json
```

Las claves API, contraseñas y credenciales deben permanecer fuera del repositorio.

---

## 📌 Reglas generales del equipo

1. No trabajar directamente sobre `main`.
2. Crear una branch para cada funcionalidad o modificación importante.
3. Hacer commits pequeños y descriptivos.
4. Probar los cambios antes de crear un Pull Request.
5. Revisar el código de otro integrante antes del merge.
6. Mantener la estructura de carpetas organizada.
7. No subir contraseñas, claves API ni configuraciones personales.
8. Utilizar rutas relativas dentro del proyecto.
9. Documentar decisiones importantes.
10. Todos los integrantes deben conocer y comprender la arquitectura general del proyecto.

---

## 📚 Documentación académica

La organización del proyecto toma como referencia las pautas de entrega del Proyecto Integrador 2026.

La propuesta de **CarioDetector** es una propuesta propia del equipo y deberá mantener los requisitos mínimos establecidos para este tipo de propuesta:

* programación estructurada;
* programación orientada a objetos;
* interfaz gráfica;
* acceso y persistencia en una base de datos;
* integración de los módulos;
* pruebas;
* documentación;
* código fuente e instrucciones de ejecución.

---

## 🚧 Próximos pasos

* [ ] Definir arquitectura inicial.
* [ ] Finalizar DER.
* [ ] Crear estructura inicial del repositorio.
* [ ] Configurar entorno de desarrollo.
* [ ] Definir modelo de datos.
* [ ] Crear base de datos inicial.
* [ ] Implementar carga de imágenes.
* [ ] Implementar primer algoritmo de detección.
* [ ] Crear interfaz gráfica inicial.
* [ ] Integrar módulos.
* [ ] Crear pruebas.
* [ ] Documentar el MVP.
* [ ] Planificar extensiones posteriores.

---

**CarioDetector — Proyecto Integrador 2026**
**Ciencia de Datos e Inteligencia Artificial — ISFT N.º 204**
