# Experimento previo: ¿supera una ResNet a la densitometría?

Lo hicimos antes de ver los datos del reto, con una base pública de enfisema.
La respuesta fue que no: una ResNet-50 congelada detecta el enfisema mínimo,
pero empata con Perc15, un índice clásico de densidad. Por eso el pipeline
actual mide anatomía interpretable en lugar de embeddings. El código sigue en
el repo porque fija la referencia que cualquier modelo profundo tiene que
superar.

Para reproducirlo hace falta la base de enfisema: `./scripts/fetch_data.sh emphysema`.

## Scripts

| Script | Qué hace | CPU | GPU |
|---|---|---|---|
| `scripts/exp_patches.py` | Sonda lineal sobre 168 parches anotados | 1 min | |
| `scripts/exp_slices.py` | Mapas de daño en 115 cortes, dejando fuera un sujeto cada vez | 5 min | 2,5 min |
| `scripts/report_slices.py` | Métricas, intervalos y figuras del experimento anterior | 1 min | |
| `scripts/run_volume.py <serie>` | Lóbulos, densitometría y mapa de una TC completa | 2,5 min | 30 s |

Los scripts usan la GPU solo si quedan 2,5 GiB de VRAM libres. En la devbox eso
exige parar antes `localjev-scorer` (`systemctl --user stop localjev-scorer`) y
arrancarlo al terminar. Con la GPU, los embeddings de los 115 cortes bajan de
133 s a 4 s.

`exp_slices.py` y `report_slices.py` aceptan `--pretraining imagenet` o
`radimagenet`. `run_volume.py` usa el modelo de parches que deja `exp_slices.py`.

## Resultados del 1 de octubre de 2026

Datos: base de enfisema de Sørensen et al. (2010), 39 sujetos, 115 cortes HRCT
con severidad consensuada por un radiólogo y un neumólogo. La tarea que imita
la EPOC precoz es separar cortes sin enfisema (61) de cortes con enfisema
mínimo (26). Todo se evalúa sobre sujetos que el modelo no ha visto.

**Parches, tres clases (normal, centrolobulillar, paraseptal).** Acierto con
regresión logística dejando fuera un sujeto cada vez.

| Variables | Acierto |
|---|---|
| Densitometría del parche | 0,917 |
| ResNet-50 ImageNet | 0,946 |
| ResNet-50 RadImageNet | 0,946 |

**Cortes, con ResNet-50 RadImageNet.** AUC con IC 95 % remuestreando sujetos.

| Puntuación del corte | Sin enfisema vs mínimo | Sin enfisema vs cualquier grado | Spearman con severidad |
|---|---|---|---|
| ResNet con etiquetas débiles | 0,81 (0,64-0,94) | 0,87 (0,74-0,96) | 0,69 |
| Perc15 | 0,78 (0,62-0,91) | 0,86 (0,75-0,96) | 0,71 |
| %LAA-910 | 0,71 (0,55-0,86) | 0,83 (0,72-0,93) | 0,67 |
| %LAA-950 | 0,61 (0,43-0,79) | 0,78 (0,65-0,89) | 0,59 |
| ResNet normativo, sin etiquetas | 0,53 (0,37-0,69) | 0,68 (0,54-0,81) | 0,43 |

Lo que dicen estos números:

- El mapa normativo falla. Mide la distancia de cada parche a un banco de
  pulmón sano y lo que marca es el hilio, los vasos y las cisuras, que son
  anatomía normal poco frecuente. En enfisema mínimo no supera el azar.
- El mapa con etiquetas débiles funciona. Se entrena con cortes sin enfisema
  frente a cortes con enfisema leve o mayor y detecta el grado mínimo, que no
  ve nunca al entrenar. Supera a %LAA-950 en 0,19 de AUC (IC 0,05 a 0,33).
- No supera a Perc15. La diferencia es 0,03 (IC -0,02 a 0,08) y la puntuación
  de la ResNet correlaciona -0,95 con Perc15. El modelo ha aprendido sobre todo
  densidad. Juntar densitometría y ResNet no mejora a la ResNet sola.
- ImageNet y RadImageNet rinden parecido: 0,80 y 0,81 en la tarea de enfisema
  mínimo.
- El modelo no se transfiere entre escáneres. En una TC de LIDC-IDRI con
  %LAA-950 por debajo del 1 % marca el 90 % de cada lóbulo como enfermo, porque
  ese pulmón es más oscuro (Perc15 de -915 HU) que los de la base de enfisema.
  Hay que reentrenar el modelo de parches con la cohorte de la hackathon.

La variante con etiquetas débiles se eligió después de ver que la normativa
fallaba, sobre los mismos 39 sujetos. Un barrido de capas y de regularización
dio AUC entre 0,78 y 0,80 en todas las combinaciones, así que el resultado no
depende de un ajuste concreto, pero no hay un conjunto de prueba aparte.

## Código

```
src/maps/lungs.py       segmentación de pulmón y lóbulos con lungmask
src/maps/backbone.py    ResNet-50 hasta layer3, con pesos ImageNet o RadImageNet
src/maps/pipeline.py    embeddings por celda de 3 mm dentro del pulmón
src/maps/weak.py        modelo de parches con etiquetas débiles
src/maps/damage.py      banco de referencia y distancia kNN
src/maps/fusion.py      AUC por bloque de variables, agrupando por sujeto
```
