# App de demostración MAPS

Dos vistas sobre un directorio de cohorte:

- **Paciente.** La TC en cortes coronales con cada lóbulo teñido por cuánto se
  desvía de lo esperado, la tabla de medidas por lóbulo y el perfil clínico y
  biológico situado en la cohorte.
- **Cohorte.** La puntuación de daño por grupo, los controles negativos y la
  escalera de evidencia con sus intervalos.

La app no hace ninguna petición fuera de la máquina: sin CDN, sin fuentes web y
sin telemetría (`app/.streamlit/config.toml`). No genera texto. Todas las
frases son plantillas fijas rellenadas con números de la cohorte.

## Arrancar en local

Con el entorno del repo ya instalado (`uv sync`), desde la raíz:

```bash
# 1. Cohorte sintética para desarrollar y ensayar (una vez; unos 2 minutos en CPU)
PYTHONPATH=src python app/make_fixture.py --tc data/lidc/LIDC-IDRI-0004

# 2. La app
PYTHONPATH=src python -m streamlit run app/maps_app.py \
  --server.headless true --browser.gatherUsageStats false --server.port 8501
```

Se abre en `http://localhost:8501`. Sin más argumentos usa
`outputs/cohorte_sintetica`. Para otra cohorte:

```bash
python -m streamlit run app/maps_app.py --server.port 8501 -- --cohort /ruta/a/la/cohorte
# o bien
MAPS_COHORT=/ruta/a/la/cohorte python -m streamlit run app/maps_app.py --server.port 8501
```

`?paciente=<subject_id>` en la URL abre la app en ese paciente y
`?vista=Cohorte` en la vista de cohorte.

## Desde un nodo de cómputo, por túnel SSH

Los datos no salen del clúster: la app corre allí y el portátil solo ve la
página.

```bash
# En el nodo de cómputo (anota su nombre con `hostname`)
python -m streamlit run app/maps_app.py --server.headless true \
  --browser.gatherUsageStats false --server.address 0.0.0.0 --server.port 8501 \
  -- --cohort /ruta/a/la/cohorte

# En el portátil
ssh -L 8501:<nodo>:8501 <usuario>@<login>
```

Abre `http://localhost:8501` en el portátil. Si el puerto 8501 está ocupado en
el nodo, cambia el número en los dos sitios.

Con `--server.address 0.0.0.0` cualquier usuario del clúster que conozca el
nodo y el puerto puede abrir la app. Si se puede entrar por SSH al nodo, es
mejor arrancarla con `--server.address 127.0.0.1` y saltar por el login:
`ssh -L 8501:localhost:8501 -J <usuario>@<login> <usuario>@<nodo>`.

Antes de la demo, abre una vez las dos vistas: la primera visita a Cohorte
carga la librería de gráficos y tarda alrededor de un segundo; después el
cambio es inmediato.

## Directorio de cohorte

```
subjects.csv            una fila por sujeto; `subject_id` y las columnas clínicas que haya
features.csv            subject_id, region (LSI, LII, LSD, LM, LID o pulmon) y una columna por medida
zscores.csv             mismas claves y columnas, en z
measures.json           {medida: {"nombre", "unidad", "descripcion", "peor": "menor" | "mayor"}}
previews/<id>.npz       hu (k, Z, X) int16, lobes (k, Z, X) uint8, spacing (mm por fila, mm por columna)
evidence.json           opcional: escalera de evidencia y controles negativos
SINTETICO               opcional: si existe, la app avisa de que los datos son sintéticos y muestra su primera línea
```

Solo `subjects.csv` es imprescindible. Lo que falte se dice en la vista que lo
necesita y en «Avisos al cargar la cohorte», al pie de la vista Cohorte.

Convención de `previews`: cortes de anterior a posterior, fila 0 craneal,
columna 0 a la derecha del paciente. La app lo comprueba con las etiquetas de
los lóbulos y voltea la imagen si viene al revés.

## Qué cambiar y dónde

| Para | Fichero |
|---|---|
| Redefinir la puntuación de daño | `puntuacion_dano` en `maps_core.py` |
| Cambiar el umbral de 2 desviaciones | `UMBRAL_Z` en `maps_core.py`; el color y los textos lo siguen |
| Dar nombre y unidad a las columnas clínicas reales | `ETIQUETAS_CLINICAS` en `maps_core.py` |
| Cambiar el color del daño o la ventana de la TC | `COLOR_DANO` y `PASOS_DANO` en `maps_render.py` |
| Cambiar textos, tablas y estilos | `maps_ui.py`: los tokens de diseño están al principio |
| Cambiar la fuente o el color de los controles | `.streamlit/config.toml` |

Una medida que esté en los CSV y no en `measures.json` se muestra con su nombre
de columna, sin color, y no entra en la puntuación.

## Diseño

Blanco dominante, negro para el texto y la estructura, y un solo acento: el
dorado de AstraZeneca (`#F0AB00`). El dorado significa siempre «daño, lo que hay
que mirar»: tiñe los lóbulos desviados, las celdas fuera de rango y el paciente
elegido en la vista de cohorte. Nunca es color de texto. Los botones siguen la
forma y los estados del botón de Kumo, el sistema de diseño de Cloudflare. La
tipografía es Helvetica Neue con Helvetica y Arial de reserva, todas del
sistema.

## Pruebas

```bash
uv run pytest tests/test_app_core.py tests/test_app_render.py -q
```
