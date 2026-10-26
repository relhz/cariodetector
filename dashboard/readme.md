# Dashboard CarioDetector (Streamlit)

Dashboard web para subir imágenes de cariotipos, detectar los cromosomas con el modelo YOLO
y ver estadísticas de los análisis guardados en MySQL.

## Requisitos

- Necesita los pesos del modelo en models/best_24_chromosomes.pt. Se recomienda Python 3.10 a 3.12. 
- Si no hay base de datos conectada, el dashboard avisa y muestra datos de demostración (con un cartel rojo: no son resultados reales).

## Cómo correrlo

Desde la **raíz del repositorio**:

```
pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py
```

Se abre en el navegador en http://localhost:8501.

## Conexión con la base de datos

- Por defecto usa la misma conexión que utils/db_config.py. 
- Para otra configuración se pueden definir las variables de entorno DB_HOST, DB_PORT, DB_USER, DB_PASSWORD y DB_NAME.
- Lo que se guarda desde el Tkinter aparece en el dashboard y viceversa.

## Parámetros de detección

El dashboard usa conf = 0.35 (confianza mínima) e iou = 0.40 (solapamiento máximo entre cajas). 
Se pueden cambiar en dashboard/app.py (CONF_UMBRAL e IOU_UMBRAL).
Conviene que la interfaz Tkinter use los mismos valores.

## Archivos

- `app.py`: la aplicación.
- `modelo.py`: carga el modelo YOLO y detecta.
- `db.py`: conexión y consultas a MySQL, datos de demostración.

## Aviso importante

Es una herramienta de apoyo, no de diagnóstico. Toda alerta debe ser validada por un profesional.
Solo evalúa alteraciones numéricas (cantidad de copias por par), no estructurales.
