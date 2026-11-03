# Dashboard CarioDetector (Streamlit)

Dashboard web para subir imágenes de cariotipos, detectar los cromosomas con el modelo YOLO
y ver estadísticas de los análisis guardados en MySQL.

## Requisitos

- Python 3.10 o superior
- Los pesos del modelo en `models/best_24_chromosomes.pt` (ruta definida en `nucleo/constantes.py`).
  Para comparar con el YOLOv8s anterior, guardarlo en `models/` con otro nombre `.pt`
  (está en `.gitignore`, no se sube al repo).
- MySQL local con la base creada (opcional; sin base muestra datos de demostración)

## Cómo correrlo

La forma normal es ejecutar la aplicación completa desde la **raíz del repositorio**:

```
python main.py
```

`main.py` abre Tkinter y lanza este dashboard automáticamente en un puerto libre,
abriendo el navegador. Al cerrar Tkinter, el dashboard se detiene.

Para ejecutar solo el dashboard:

```
pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py
```

Se abre en el navegador en http://localhost:8501.

## Arquitectura

- La detección, los conteos, el dibujo, los informes y el acceso a MySQL viven en
  `nucleo/`. Los usan tanto Tkinter como este dashboard.
- Los gráficos viven en `graficos/` y no dependen de Streamlit.
- `dashboard/app.py` solo arma la página y las pestañas.
- `dashboard/componentes.py` contiene el visor con zoom y los avisos reutilizables.
- `dashboard/lanzador.py` inicia y detiene Streamlit junto a la aplicación de escritorio.

## Conexión con la base de datos

- Por defecto usa la conexión de `nucleo/db.py`.
- Para otra configuración se pueden definir las variables de entorno DB_HOST, DB_PORT,
  DB_USER, DB_PASSWORD y DB_NAME.
- Lo que se guarda desde Tkinter aparece en el dashboard y viceversa.

## Parámetros de detección

- Los umbrales compartidos están en `nucleo/constantes.py`:
  `CONF_UMBRAL = 0.25`, `IOU_UMBRAL = 0.70` y `CONF_REVISION = 0.50`.
- Tkinter y el dashboard usan exactamente los mismos valores.

## Archivos

- `app.py`: la aplicación web.
- `componentes.py`: visor con zoom, semáforo y avisos.
- `lanzador.py`: arranque automático del dashboard.
- `modelo_info/`: results_yolov8l.csv y results_yolov8s.csv (registros del entrenamiento de cada modelo), que usa la pestaña "Sobre el modelo".

## Aviso importante

Es una herramienta de apoyo, no de diagnóstico. Toda alerta debe ser validada por un profesional.
Solo evalúa alteraciones numéricas (cantidad de copias por par), no estructurales.
