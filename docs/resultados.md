# Resultados

Estado al 2 de octubre por la noche. Solo hay agregados: ningún dato de un sujeto.
[`cifras.md`](cifras.md) lo resume en una página.

El trabajo tuvo dos fases, y los resultados no se mezclan:

1. **Un modelo ajustado con 62 sujetos, probado una vez en 15 que no vio.** Los
   criterios se escribieron antes ([`protocolo-reserva.md`](protocolo-reserva.md)).
2. **El modelo final, ajustado con los 80 sujetos.** Como ya no queda nadie
   apartado, su rendimiento se estima con validación cruzada anidada: cada
   sujeto se puntúa con un modelo que no lo vio ni para ajustar lo esperado, ni
   para elegir medidas, ni para fijar el umbral
   ([`protocolo-mejora.md`](protocolo-mejora.md)).

Se regenera en MareNostrum con:

```bash
python3 scripts/score_cohort.py mn5/cohorte.final.toml
python3 scripts/nested_cv.py mn5/cohorte.final.toml --duro outputs/cohorte_duro_v4
python3 scripts/check_score.py mn5/cohorte.final.toml --duro outputs/cohorte_duro_v4
```

Los agregados están en [`figuras/validacion_anidada.json`](figuras/validacion_anidada.json),
[`figuras/comprobaciones.json`](figuras/comprobaciones.json),
[`figuras/escalera.json`](figuras/escalera.json) y [`figuras/reserva.json`](figuras/reserva.json).

![La puntuación por clase, su estabilidad entre reconstrucciones y el AUC por subgrupo, fuera de muestra y en reserva](figuras/evidencia.png)

## Qué se procesó

- 86 sujetos en la tabla. 80 tienen una TC de tórax que sirve: sin contraste y
  de corte fino. Se segmentaron sin fallos, en 28 minutos sobre 4 GPU.
- En 3 de los 80 la reconstrucción estándar tiene cortes que faltan. Su otra
  reconstrucción, de kernel duro, está completa y es la que se usa.
- 28 con EPOC y 52 controles. Cada adquisición tiene dos reconstrucciones, que
  sirven para medir la estabilidad.
- Los 80 se repartieron al principio en 64 de desarrollo y 16 de reserva. Para la
  primera fase se usaron los 77 con la serie estándar completa: 62 y 15.

## El modelo final, fuera de muestra (80 sujetos)

Dos medidas: %LAA-950 suavizado y longitud del árbol bronquial. Validación
cruzada de 5 grupos, repetida 10 veces.

| Pregunta | Resultado |
|---|---|
| ¿Sigue la limitación al flujo aéreo? | Spearman con FEV1/FVC de -0,73, IC del 95 % de -0,83 a -0,57 |
| ¿La sigue entre quienes no tienen obstrucción? | Sí: -0,34, IC aproximado de -0,61 a -0,04, p = 0,016 por permutación (52 sujetos) |
| ¿Separa EPOC de control? | AUC 0,91 |
| ¿Es estable entre reconstrucciones? | ICC 0,98 |
| Umbral "TC parecida a la de la EPOC" | Por encima, el 82 % de los sujetos con EPOC; por debajo, el 75 % de los controles |
| Límite superior de normalidad | Por encima, el 54 % de los sujetos con EPOC; por debajo, el 96 % de los controles |

La segunda fila es lo que faltaba. Con 40 controles y las medidas sin corregir,
la relación dentro de los controles era de -0,26 y no se distinguía del azar.

Los intervalos se calculan remuestreando sujetos con sus puntuaciones ya
hechas, sin repetir el ajuste: son aproximados. La p sale de permutar el
cociente entre sujetos, que vale porque la puntuación de cada uno no usa el
FEV1/FVC de nadie. Sin los 3 sujetos recuperados con la otra reconstrucción
(77), nada cambia: -0,73, -0,33 (p = 0,02) y AUC 0,91.

### Las vías finas siguen al cociente más que las gruesas

| Puntuación | Spearman con FEV1/FVC | Entre los sin obstrucción | AUC | Acuerdo entre reconstrucciones |
|---|---|---|---|---|
| **Enfisema + longitud total (el modelo)** | **-0,73** | **-0,34** (p = 0,016) | 0,91 | 0,98 |
| Enfisema + vías de menos de 3 mm de luz | -0,73 | -0,41 (p = 0,003) | 0,89 | 0,97 |
| Enfisema + vías de 3 mm o más | -0,56 | -0,10 (p = 0,47) | 0,84 | 0,97 |
| Enfisema + extremos del árbol | -0,73 | -0,38 (p = 0,007) | 0,90 | 0,98 |
| Enfisema + número de ramas | -0,73 | -0,37 (p = 0,009) | 0,90 | 0,98 |
| Enfisema + longitud dentro de cada lóbulo | -0,72 | -0,34 (p = 0,014) | 0,91 | 0,98 |
| Solo vía aérea, longitud total | -0,67 | -0,28 (p = 0,04) | 0,92 | 0,97 |
| Solo las vías de menos de 3 mm | -0,66 | -0,34 (p = 0,012) | 0,88 | 0,93 |
| Solo las vías de 3 mm o más | -0,30 | 0,05 (p = 0,72) | 0,75 | 0,91 |
| Solo enfisema | -0,46 | -0,29 (p = 0,03) | 0,72 | 0,97 |
| Eligiendo la medida en cada vuelta | -0,72 | -0,35 (p = 0,011) | 0,90 | 0,98 |

- Comparadas directamente, la longitud de las vías finas sigue al cociente más
  que la de las gruesas: la diferencia entre sus correlaciones es de 0,36, con
  un intervalo de 0,10 a 0,60. Entre quienes no tienen obstrucción la diferencia
  va en el mismo sentido y no está demostrada: 0,29, de -0,10 a 0,49.
- Es coherente con que la enfermedad empiece en la vía aérea pequeña, pero no lo
  demuestra. Las "vías finas" son ramas visibles de menos de 3 mm; la vía aérea
  pequeña de la literatura, de menos de 2 mm, no se ve en esta TC. Además, una vía estrecha también se segmenta peor. Y el corte de 3 mm es
  aproximado, porque el diámetro se mide en una imagen con píxeles de 0,6 a
  0,9 mm. La puntuación con las vías finas no se relaciona con el tamaño del
  píxel entre los controles (0,01).
- Ninguna medida nueva mejora al modelo de forma demostrable. La mayor ganancia
  en la correlación es de 0,01, con un intervalo de -0,02 a 0,05. Elegir entre
  ellas en cada vuelta tampoco: en 50 vueltas ganaron nueve combinaciones
  distintas. El modelo se queda con la longitud total.
- El enfisema aporta a seguir el cociente (-0,73 frente a -0,67 sin él), aunque
  no a separar la EPOC.

## La primera prueba: 15 sujetos que el modelo no vio

El mismo modelo, ajustado solo con 62 sujetos. Lo que se iba a medir y lo que
contaría como fracaso se escribió antes.

| Pregunta | Reserva (15: 6 con EPOC, 9 controles) | Criterio fijado antes |
|---|---|---|
| ¿La TC separa a quien tiene obstrucción? | AUC 0,85, IC del 95 % de 0,61 a 1 | 0,80 o más: cumple |
| ¿Sigue la limitación al flujo aéreo? | Spearman con FEV1/FVC de -0,81, p < 0,001 | -0,5 o más fuerte: cumple |
| ¿Vale "lo esperado" para sujetos nuevos? | Mediana de la puntuación de los controles: 0,02 | Entre -0,5 y 0,5: cumple |
| | Dispersión del z en los controles: 0,7 (enfisema) y 1,2 (vía aérea) | Entre 0,6 y 1,6: cumple |
| ¿Viaja el umbral? | Con EPOC por encima: 6 de 6 (IC de 0,54 a 1). Controles por debajo: 5 de 9 (IC de 0,21 a 0,86) | Menos de la mitad de los controles por encima: cumple por poco |
| ¿Es estable entre reconstrucciones? | ICC 0,99; misma decisión en 15 de 15 | 0,90 o más: cumple |
| ¿Añade a la clínica? | Edad, sexo, talla y tabaco: Spearman 0,06. Con la TC: 0,89 | Sin criterio; comparación descriptiva |

"Cumple" describe la estimación. Con 15 sujetos los intervalos son muy anchos:
la asociación con el cociente es defendible; que el umbral sirva en clínica, no.

## La cohorte con el modelo final (80 sujetos)

Estas cifras describen la cohorte. Son de los mismos sujetos con los que se
ajustó, así que el rendimiento que cuenta es el de la sección anterior.

### Adquisición y calidad de la imagen

No hemos encontrado ninguna relación que explique el resultado. Eso no descarta
artefactos: los subgrupos son pequeños y las dos reconstrucciones salen de la
misma adquisición.

| Comprobación | Resultado |
|---|---|
| AUC para EPOC a 80, 100 y 120 kVp | 0,89, 0,91 y 0,93 |
| AUC para EPOC en hombres y en mujeres | 0,85 y 0,95 |
| AUC para EPOC en quien fuma y en quien no | 0,92 y 0,90 |
| Dentro de los controles, sexo y tabaco | AUC 0,51 y 0,50 |
| Dentro de los controles, kVp | p = 0,95 |
| Ruido de la imagen, medido en el aire de la tráquea | Spearman con la puntuación de -0,07 |
| Paso de corte, 0,625 o 1,25 mm | Spearman de -0,01 |
| Tamaño del píxel | Spearman de 0,09 con la puntuación |
| Índice de masa corporal | Spearman de 0,01; dentro de los controles, -0,21 (p = 0,14) |
| Relación con FEV1/FVC descontando el tamaño del píxel | -0,73; entre los sin obstrucción, -0,38 (p = 0,006) |
| Relación con FEV1/FVC descontando el IMC | -0,75; entre los sin obstrucción, -0,38 (p = 0,005) |
| Constante que se suma al enfisema antes del logaritmo: 0,001, 0,01 o 0,1 | AUC 0,93, 0,90 y 0,90 |

El píxel es más grande en los sujetos más corpulentos, y hay más de ellos entre
los casos. Por eso se comprueba aparte: descontando el tamaño del píxel o el
IMC, la relación con el cociente es la misma.

### Medida a medida

Las que nombra el reto, las de la puntuación (en negrita) y las demás. El signo
está puesto para que más sea peor. La q es la p corregida por comparaciones
múltiples.

| Medida | AUC para EPOC | Spearman con FEV1/FVC | q | Spearman con paquetes-año | Acuerdo entre kernels |
|---|---|---|---|---|---|
| %LAA-950 clásico | 0,68 | -0,40 | < 0,01 | -0,21 | 0,18 |
| **%LAA-950 suavizado** | 0,71 | -0,46 | < 0,01 | -0,15 | 0,93 |
| Perc15 | 0,49 | -0,10 | 0,61 | -0,24 | 0,23 |
| Grosor de pared, estimado | 0,64 | -0,15 | 0,42 | 0,10 | 0,66 |
| Área de pared, aproximada | 0,57 | -0,04 | 0,83 | 0,07 | 0,66 |
| Pi10, aproximado | 0,60 | -0,08 | 0,68 | 0,03 | 0,62 |
| Disanapsia, aproximada | 0,65 | -0,33 | 0,02 | 0,01 | 0,75 |
| **Longitud de vía aérea** | 0,92 | -0,67 | < 0,01 | 0,10 | 0,94 |
| Longitud de las vías finas | 0,88 | -0,65 | < 0,01 | 0,09 | 0,89 |
| Longitud de las vías gruesas | 0,75 | -0,30 | 0,03 | 0,04 | 0,94 |
| Extremos del árbol | 0,93 | -0,71 | < 0,01 | 0,11 | 0,92 |
| Ramas por litro | 0,90 | -0,69 | < 0,01 | 0,12 | 0,95 |
| Volumen vascular | 0,72 | -0,46 | < 0,01 | -0,05 | 0,93 |
| Agrupamiento del enfisema | 0,72 | -0,42 | < 0,01 | -0,13 | 0,86 |

- Las medidas de pared no separan la EPOC en esta cohorte, y son las menos
  estables. Son aproximaciones: salen de la máscara de pared de la segmentación
  y suponen secciones circulares. La disanapsia usa las 15 vías más anchas, no
  las 19 localizaciones anatómicas de Smith 2020.
- **Tabaco.** Ninguna medida se asocia con los paquetes-año (todas las q de 0,1
  o más). Quien fuma en el momento de la TC tiene el pulmón más denso, y por eso
  el modelo descuenta el tabaquismo activo.

### Qué más sigue la puntuación

| | En los 80 | Entre los 52 sin obstrucción | Entre los 28 con EPOC |
|---|---|---|---|
| FEV1/FVC | -0,72 | -0,35 (p = 0,01) | -0,66 |
| FEV1, % del predicho | -0,47 | -0,06 | -0,53 |
| DLCO, % del predicho | -0,17 | 0,15 | -0,64 (p < 0,001) |
| Síntomas (CAT) | 0,33 (p = 0,003) | 0,06 | 0,32 (p = 0,09) |
| Paquetes-año | -0,04 | -0,24 (p = 0,10) | -0,57 (p = 0,002) |

Añade a la clínica: en validación cruzada, edad, sexo, talla y tabaco dan un
Spearman de 0,17 con el FEV1/FVC, y con las dos medidas de TC, 0,76. Es
exploratorio: el modelo normativo no se reajusta en cada vuelta de esa cuenta.
La clasificación por TC, que incluye la vía aérea, coincide poco con el enfisema
visual del radiólogo: kappa 0,32. No miden lo mismo.

## Las clases

Son las que produce nuestra regla: EPOC si hay obstrucción; posible pre-EPOC si
no la hay y la TC se parece a la de la EPOC; control en otro caso. No hay una
etiqueta externa de pre-EPOC con la que compararlas, así que esta tabla describe
la regla, no la valida. La regla no usa el PRISm (FEV1 bajo con el cociente
conservado): las investigadoras del reto no lo consideran una buena definición.

| | Control | Posible pre-EPOC | EPOC |
|---|---|---|---|
| Sujetos | 38 | 14 | 28 |
| Puntuación de daño, mediana | -0,27 | 0,88 | 1,43 |
| FEV1/FVC | 0,78 | 0,75 | 0,60 |
| FEV1, % del predicho | 97 | 91 | 73 |
| DLCO, % del predicho | 74 | 79 | 74 |
| CAT en la visita 1 | 5,5 | 9 | 12 |
| CAT en la visita 2 | 6 | 6 | 11,5 |
| Fuman | 76 % | 79 % | 57 % |
| Enfisema visual | 11 % | 29 % | 54 % |
| Paquetes-año | 21 | 20 | 28 |

### Los posibles pre-EPOC frente a los demás controles

| | Posible pre-EPOC (14) | Control (38) | p |
|---|---|---|---|
| FEV1/FVC | 0,75 | 0,78 | 0,03 |
| FEV1/FVC por debajo de 0,75 | 7 de 14 | 8 de 38 | |
| Calibre central para su pulmón (z; más es más estrecho) | 0,48 | -0,22 | 0,015 |
| FEV1, % del predicho | 91 | 97 | 0,28 |
| DLCO, % del predicho | 79 | 74 | 0,32 |
| CAT | 9 | 5,5 | 0,15 |
| Enfisema visual | 29 % | 11 % | 0,19 |
| Paquetes-año | 20 | 21 | 0,13 |
| Cambio del FEV1 % a 3,6 años | +3,4 | +2,9 | 0,36 |

Están más cerca de la obstrucción que los demás controles, y la mitad tiene el
cociente por debajo de 0,75, cerca del límite inferior de normalidad a su edad.
Tienen las vías centrales más estrechas para su pulmón. No detectamos
diferencias en síntomas, en DLCO ni en la evolución del FEV1.

## La misma puntuación, dos lecturas

Las investigadoras sugirieron mirar a los sujetos que se salen y buscar relación
con las variables de la tabla. `scripts/explore_outliers.py` relaciona la
puntuación con 26 variables, dentro de los controles y dentro de los casos. Es
exploratorio: la q es la p corregida por todas esas comparaciones.

| La puntuación frente a... | Entre los 52 sin obstrucción | Entre los 28 con EPOC |
|---|---|---|
| Calibre central estrecho para su pulmón (disanapsia aproximada) | 0,37 (p = 0,007; q = 0,11) | 0,05 |
| Disnea (mMRC) | -0,12 | 0,69 (q = 0,001) |
| DLCO, % del predicho | 0,15 | -0,64 (q = 0,002) |
| Enfisema visual | 0,02 | 0,62 (q = 0,003) |
| FEV1, % del predicho | -0,06 | -0,53 (q = 0,02) |
| Paquetes-año | -0,24 (p = 0,10) | -0,57 (q = 0,01) |
| Fumar ahora | 0,00 | -0,14 |
| Edad, sexo, talla | Nada | Nada |

- **En la EPOC, la puntuación es gravedad**: más disnea, peor intercambio de
  gases, más enfisema visible. Estas relaciones sí pasan la corrección.
- **En quien no tiene obstrucción, va con unas vías centrales estrechas para el
  tamaño del pulmón, y no con el tabaco.** Es compatible con un árbol pequeño de
  origen. No lo demuestra: no pasa la corrección, y el calibre y la longitud
  salen de la misma segmentación, así que parte de la relación puede ser del
  método.
- **Dentro de la EPOC, más daño en la TC va con menos paquetes-año.** No sabemos
  por qué. Puede ser susceptibilidad, que enferme con poco tabaco quien tiene el
  árbol pequeño, o que los más graves dejaran de fumar antes.
- Solo 2 de los 28 con EPOC tienen la TC como la de un control: no hay grupo que
  explorar por ese lado.

### Los dos umbrales

- **0,48, "TC parecida a la de la EPOC".** El punto que mejor separa EPOC de
  control. Dice que la TC se parece a las de la EPOC, no que haya una lesión.
  Con 52 controles es mucho más estable que con 40: con otros repartos del
  ajuste cruzado va de 0,45 a 0,50; antes iba de 0,33 a 0,63.
- **1,23, límite superior de normalidad.** No usa a los sujetos con EPOC: es la
  mediana de los controles más 1,645 desviaciones robustas, que sería el
  percentil 95 si la puntuación fuera normal. Lo supera 1 de 52 controles y 16
  de 28 con EPOC.
- Entre las dos reconstrucciones de una misma TC, la diferencia de puntuación
  tiene una dispersión robusta de 0,18 y un percentil 95 de 0,59. A menos de
  0,18 del umbral, la aplicación avisa de que el sujeto está "cerca del umbral".
- La aplicación enseña la TC en tres niveles: como la referencia, intermedia y
  por encima de lo normal.

## El paso "Connect"

`scripts/connect.py mn5/cohorte.final.toml`. Con el único biomarcador de la
tabla, el FENO en logaritmo, ajustando por edad, sexo, talla, tabaco y asma:

| Exposición | Coeficiente, en desviaciones de FENO | p | n |
|---|---|---|---|
| Puntuación de daño | 0,12 | 0,22 | 74 |
| z de %LAA-950 suavizado | 0,07 | 0,30 | 74 |
| z de longitud de vía aérea | 0,11 | 0,33 | 74 |
| FEV1/FVC | 0,39 | 0,72 | 74 |

No se detecta asociación. Con 74 sujetos eso no demuestra que no la haya.

El script es un motor de asociaciones: un modelo lineal por rasgo, covariables y
corrección por comparaciones múltiples dentro de cada exposición. Para una
matriz de metilación falta lo que es propio de ese ensayo: el control de calidad
de las sondas, los M-values, la composición celular y el lote. Ejecutarlo con el
FENO prueba que el flujo corre, no que sirva para un EWAS.

## Lo que estos resultados no demuestran

- **Que la TC detecte una enfermedad que la espirometría no ve.** Entre quienes
  no tienen obstrucción, la puntuación sigue al cociente FEV1/FVC, y eso es
  nuevo. Pero no se relaciona con los síntomas, con la DLCO ni con la evolución.
  Lo más probable es que mida, con una imagen, lo cerca que está cada persona
  de la obstrucción.
- **Que sea lesión adquirida.** Un árbol bronquial corto puede ser vía perdida,
  vía estrecha que se segmenta peor o un árbol pequeño de origen. Y la
  puntuación no sube con los paquetes-año: dentro de la EPOC baja (-0,57).
- **Que la pre-EPOC de nuestra regla sea enfermedad.** Es una definición operativa.
- **Que la TC se adelante a la espirometría.** No hay ningún resultado de progresión.
- **Que la longitud de vía aérea sea la de un radiólogo.** Sale de una
  segmentación automática que nadie ha validado en esta cohorte.
- **Nada sobre datos moleculares.** No los hay.
