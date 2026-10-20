# Dashboard CarioDetector (Streamlit)

Dashboard web para subir imágenes de cariotipos, detectar los cromosomas con el modelo YOLO
y ver estadísticas de los análisis guardados en MySQL.

## Qué tiene

- **Subir y detectar:** sube una imagen, detecta los cromosomas, muestra el conteo por par
  y alerta si algún par no tiene 2 copias. Permite guardar el análisis en la base de datos.
- **Dashboard:** indicadores y tablas de todos los análisis guardados.
- **Historial de sesión:** pruebas hechas desde que se abrió la página.
- **Gráficos:** cariograma, mapa de calor por imagen y par, confianza del modelo y más,
  con glosario para interpretarlos.

## Requisitos

- Python 3.10 o superior
- Los pesos del modelo en `models/` (ver `RUTA_PESOS` en `app.py`)
- MySQL local con la base creada (opcional; sin base muestra datos de demostración)

## Cómo correrlo

Desde la **raíz del repo** (no desde esta carpeta):

```
pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py
```

Se abre en el navegador en http://localhost:8501.

## Base de datos

1. Tener MySQL andando.
2. Crear la base, desde la raíz del repo: `python utils/db_config.py`
   (usa `scripts_sql/crear_bd.sql`).
3. El dashboard usa por defecto la misma conexión que `utils/db_config.py`
   (`localhost`, usuario `root`). Para otra configuración, definir las variables de entorno
   `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`.

Lo que se guarda desde el Tkinter aparece en el dashboard y viceversa, porque ambos usan las
tablas `analisis` y `detecciones`. Si no hay conexión o la base está vacía, el dashboard lo
avisa y muestra datos de demostración (con un cartel rojo, no son resultados reales).

Las imágenes guardadas desde el dashboard se copian a `assets/imagenes_analizadas/`.

## Parámetros de detección

En `app.py`: `CONF_UMBRAL = 0.35` (confianza mínima) y `IOU_UMBRAL = 0.40`
(solapamiento máximo entre cajas). Conviene que la interfaz Tkinter use los mismos valores.

## Archivos

- `app.py`: la aplicación.
- `modelo.py`: carga el modelo YOLO y detecta.
- `db.py`: conexión y consultas a MySQL, datos de demostración.

## Aviso

Herramienta de apoyo, no de diagnóstico. Toda alerta debe ser validada por un profesional.
Solo evalúa alteraciones numéricas (cantidad de copias por par), no estructurales.