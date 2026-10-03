# Modelo YOLO para Cariodetector

La aplicación utiliza un modelo **Ultralytics YOLO** para detectar y clasificar 24 tipos de cromosomas.

## Modelo requerido

Archivo:

```text
best_24_chromosomes.pt
```

Debe ubicarse en:

```text
models/best_24_chromosomes.pt
```

## Clases

El modelo debe tener exactamente estas 24 clases y en este orden:

| ID | Clase |
|---:|---|
| 0 | cromosoma 1 |
| 1 | cromosoma 2 |
| 2 | cromosoma 3 |
| ... | ... |
| 21 | cromosoma 22 |
| 22 | cromosoma X |
| 23 | cromosoma Y |

Si el modelo utiliza un orden diferente, es necesario actualizar `NOMBRES_CLASES` en:

```text
funciones/modelo_cromosomas.py
```

## Verificar el modelo

Desde Python:

```python
from ultralytics import YOLO

model = YOLO("models/best_24_chromosomes.pt")

print(model.names)
```

Debe mostrar **24 clases**, desde `cromosoma 1` hasta `cromosoma Y`.

## ¿Dónde obtenerlo?

El modelo puede:

- Ser entrenado con un dataset de cromosomas.
- Obtenerse de una fuente pública, verificando siempre su licencia y compatibilidad.

## Si el modelo no existe

La aplicación mostrará:

```text
Modelo no encontrado. Coloque best_24_chromosomes.pt en la carpeta models/.
```

Sin el archivo `.pt` no se puede realizar el análisis de imágenes.