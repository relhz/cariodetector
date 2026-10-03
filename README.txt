Analizador de Cromosomas - Trabajo Práctico Universitario
==========================================================

DESCRIPCIÓN
-----------
Aplicación de escritorio en Python para análisis de imágenes microscópicas
de cromosomas humanos. Utiliza un modelo YOLO preentrenado para detectar
y clasificar 24 tipos de cromosomas (1-22, X, Y).

REQUISITOS
----------
- Python 3.8+
- MySQL Server
- Librerías en requirements.txt

INSTALACIÓN
-----------
1. Crear entorno virtual (recomendado):
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

2. Instalar dependencias:
   pip install -r requirements.txt

3. Configurar base de datos:
   - Ejecutar scripts_sql/crear_bd.sql en MySQL
   - Ajustar credenciales en utils/db_config.py

4. Modelo de IA:
   - Descargar/obtener best_24_chromosomes.pt
   - Colocarlo en la carpeta models/
   - Ver models/README.txt para más detalles

EJECUCIÓN
---------
python main.py

ESTRUCTURA DEL PROYECTO
-----------------------
proyecto/
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias
├── README.txt              # Este archivo
├── interfaz/
│   └── interfaz.py         # Interfaz Tkinter
├── funciones/
│   ├── analisis_imagen.py  # Clase AnalizadorImagen (OOP)
│   ├── modelo_cromosomas.py # Clase DetectorCromosomas
│   └── resultados.py       # Funciones de resultados
├── utils/
│   └── db_config.py        # Configuración MySQL
├── models/
│   └── README.txt          # Instrucciones del modelo
├── assets/
│   └── imagenes/           # Imágenes de ejemplo
└── scripts_sql/
    └── crear_bd.sql        # Script de base de datos

FLUJO DE USO
------------
1. Abrir programa
2. "Seleccionar imagen" -> elegir JPG/PNG
3. Ver imagen original
4. "Analizar" -> detecta cromosomas
5. Ver imagen con bounding boxes y etiquetas
6. Ver tabla de detecciones y resumen
7. "Guardar análisis" -> almacena en MySQL
8. "Historial" -> consulta análisis previos

CLASES DE CROMOSOMAS (24)
-------------------------
Cromosoma 1  al 22
Cromosoma X
Cromosoma Y

ERRORES COMUNES
---------------
- "Modelo no encontrado": Coloque best_24_chromosomes.pt en models/
- "MySQL no disponible": Verifique servidor MySQL y credenciales
- "Imagen inválida": Use formatos JPG o PNG

NOTAS
-----
- Rutas relativas con pathlib
- Sin Docker, sin API web, sin autenticación
- Preparado para Windows y Linux
