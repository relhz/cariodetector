Modelo YOLO para Detección de Cromosomas
=========================================

ARCHIVO ESPERADO
----------------
best_24_chromosomes.pt

UBICACIÓN
---------
Este archivo debe colocarse en:
models/best_24_chromosomes.pt

Ruta relativa desde la raíz del proyecto:
models/best_24_chromosomes.pt

CLASES QUE DETECTA (24)
-----------------------
0  - cromosoma 1
1  - cromosoma 2
2  - cromosoma 3
3  - cromosoma 4
4  - cromosoma 5
5  - cromosoma 6
6  - cromosoma 7
7  - cromosoma 8
8  - cromosoma 9
9  - cromosoma 10
10 - cromosoma 11
11 - cromosoma 12
12 - cromosoma 13
13 - cromosoma 14
14 - cromosoma 15
15 - cromosoma 16
16 - cromosoma 17
17 - cromosoma 18
18 - cromosoma 19
19 - cromosoma 20
20 - cromosoma 21
21 - cromosoma 22
22 - cromosoma X
23 - cromosoma Y

NOTAS IMPORTANTES
-----------------
- NO se incluye el archivo .pt en el repositorio (pesado, derechos)
- El modelo DEBE ser un archivo .pt de Ultralytics YOLO (v8 o v11)
- Entrenado para 24 clases en el orden exacto de arriba
- Si usa un modelo con diferente orden de clases, actualice la lista
  NOMBRES_CLASES en funciones/modelo_cromosomas.py

DÓNDE OBTENER EL MODELO
-----------------------
- Entrenar usted mismo con Ultralytics YOLO en dataset de cromosomas
- Obtener de repositorios públicos (Kaggle, GitHub, papers académicos)
- Solicitar a su docente si provee uno para la materia

VERIFICACIÓN RÁPIDA
-------------------
Desde Python:
>>> from ultralytics import YOLO
>>> model = YOLO("models/best_24_chromosomes.pt")
>>> print(model.names)
# Debe mostrar dict con 24 entradas: 0: 'cromosoma 1', ..., 23: 'cromosoma Y'

SI EL MODELO NO EXISTE
----------------------
La aplicación mostrará:
"Modelo no encontrado. Coloque best_24_chromosomes.pt en la carpeta models/."

No intente ejecutar análisis sin el modelo.