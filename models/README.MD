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

El modelo tiene 24 clases con nombres de grupo y número de par (por ejemplo
`A1`, `C7`, `G22`, `X`, `Y`). El orden interno del archivo de pesos es
alfabético, así que no coincide con el orden 1–22, X, Y; por eso el detector
usa los nombres que devuelve el propio modelo. La lista de referencia está en
`nucleo/constantes.py` (`CLASES_MODELO`) y la carga en `nucleo/modelo.py`.

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