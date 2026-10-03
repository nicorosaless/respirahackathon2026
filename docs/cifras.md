# Cifras para la demo y las diapositivas

Las cifras definitivas del 2 de octubre por la noche. Sustituyen a cualquier
cifra anterior. Hay tres bloques y no se mezclan:

1. **El modelo final**, ajustado con los 80 sujetos. Su rendimiento se estima con
   validación cruzada anidada: cada sujeto se puntúa con un modelo que no lo vio
   en ningún paso (`docs/figuras/validacion_anidada.json`).
2. **La descripción de la cohorte con el modelo final** (`docs/figuras/comprobaciones.json`
   y `escalera.json`): clases, subgrupos, estabilidad.
3. **La prueba en reserva del modelo anterior**, hecha una vez antes de usar a
   todos los sujetos (`docs/figuras/reserva.json`).

## Datos

- 86 sujetos de 35 a 50 años, fumadores o exfumadores: 30 con obstrucción y 56 sin ella.
- 80 con una TC de tórax utilizable: 28 con EPOC y 52 controles. En 3 de ellos la
  serie estándar estaba incompleta y se usa la otra reconstrucción de la misma TC.

## 1. El modelo final, fuera de muestra (80 sujetos)

Dos medidas: enfisema (%LAA-950 suavizado) y longitud del árbol bronquial.

| Qué | Cifra |
|---|---|
| Relación de la puntuación con FEV1/FVC (Spearman) | -0,73, IC del 95 % de -0,83 a -0,57 |
| La misma, solo entre los 52 sin obstrucción | -0,34, IC aproximado de -0,61 a -0,04, p = 0,016 por permutación |
| Separa EPOC de control (AUC) | 0,91 |
| Acuerdo entre las dos reconstrucciones (ICC) | 0,98 |
| Umbral "TC parecida a la de la EPOC": con EPOC por encima / controles por debajo | 82 % / 75 % |
| Límite superior de normalidad: con EPOC por encima / controles por debajo | 54 % / 96 % |
| Descontando el tamaño del píxel o el índice de masa corporal (descriptivo, con el modelo final) | La relación con FEV1/FVC no cambia: -0,73 y -0,75 |

Las vías finas siguen al cociente más que las gruesas:

| Puntuación | Relación con FEV1/FVC | Solo entre los sin obstrucción |
|---|---|---|
| Enfisema + longitud total (el modelo) | -0,73 | -0,34 (p = 0,016) |
| Enfisema + longitud de las vías de menos de 3 mm de luz | -0,73 | -0,41 (p = 0,003) |
| Enfisema + longitud de las vías de 3 mm o más | -0,56 | -0,10 (p = 0,47) |
| Enfisema + número de extremos del árbol | -0,73 | -0,38 (p = 0,007) |
| Solo las vías de menos de 3 mm | -0,66 | -0,34 (p = 0,012) |
| Solo las vías de 3 mm o más | -0,30 | 0,05 (p = 0,72) |
| Solo enfisema | -0,46 | -0,29 (p = 0,03) |

Comparadas directamente, las finas siguen al cociente más que las gruesas en el
conjunto: diferencia de 0,36 en la correlación, IC de 0,10 a 0,60. Entre los sin
obstrucción la diferencia va en el mismo sentido y no está demostrada: 0,29, IC
de -0,10 a 0,49. El corte de 3 mm es aproximado: el diámetro se mide en una
imagen con píxeles de 0,6 a 0,9 mm.

Sin los 3 sujetos recuperados con la otra reconstrucción (77), nada cambia:
-0,73 en el conjunto, -0,33 entre los sin obstrucción (p = 0,02), AUC 0,91.

Ninguna de las medidas nuevas mejora al modelo de forma demostrable: la mayor
ganancia es de 0,01 en la correlación, con un intervalo de -0,02 a 0,05. El
modelo se queda con la longitud total. Si en vez de fijar la medida se elige en
cada vuelta, el AUC fuera de muestra es 0,90 y la correlación, -0,72.

### Menos es más: añadir medidas no mejora (`docs/figuras/complejidad.json`)

Fuera de muestra, con los 80 (validación cruzada de 5 grupos repetida 5 veces;
lo esperado y los pesos se ajustan solo con los de entrenamiento).

| Modelo | AUC | Relación con FEV1/FVC | Acuerdo entre reconstrucciones |
|---|---|---|---|
| 1 medida: vía aérea | 0,92 | -0,67 | 0,97 |
| **2 medidas: más enfisema (el modelo)** | **0,91** | **-0,72** | **0,98** |
| 3: más disanapsia | 0,89 | -0,70 | 0,96 |
| 4: más grosor de pared | 0,90 | -0,68 | 0,96 |
| 5: más volumen vascular | 0,89 | -0,68 | 0,95 |
| 6: más agrupamiento | 0,88 | -0,68 | 0,97 |
| 7: más Pi10 | 0,87 | -0,65 | 0,94 |
| 8: más Perc15 | 0,85 | -0,63 | 0,77 |
| Regresión logística con las 27 medidas, pesos aprendidos | 0,85 | -0,61 | 0,43 |
| Clínica sola (edad, sexo, talla, IMC, paquetes-año, fumar) | 0,63 | -0,23 | |
| Clínica más las dos medidas de TC | 0,95 | -0,75 | 0,99 |
| Clínica ampliada sola (lo anterior más DLCO, CAT, mMRC, COPD-PS, FENO y asma) | 0,76 | -0,51 | |
| Clínica ampliada más las dos medidas de TC | 0,90 | -0,69 | 0,99 |

- Cada medida que se añade baja la AUC y la estabilidad. Aprender los pesos con
  todas las medidas es peor aún, y su acuerdo entre reconstrucciones cae a 0,43:
  con 80 sujetos, el modelo aprende ruido.
- Las dos medidas dan la mejor relación con el cociente y el mejor acuerdo; la
  vía aérea sola separa igual, pero sigue peor el cociente.
- Juntar la TC con la clínica básica sube la AUC de 0,91 a 0,95. La clínica sola, 0,63.
- Añadir el resto de la tabla (síntomas, DLCO, FENO, asma) no ayuda: con la TC
  baja de 0,95 a 0,90. Solas dan 0,76, porque los síntomas y la DLCO son en parte
  consecuencia de la enfermedad, no una medida independiente de ella.
- El FEV1 y la FVC no pueden entrar como variables: la obstrucción es su
  cociente. Meterlos sería darle la respuesta al modelo.

Caída acelerada del FEV1 entre visitas (la investigadora del reto propone 30 mL
al año; la definición publicada dice 60): con 30, 23 de 71 con seguimiento. La
puntuación fuera de muestra no la anuncia: AUC 0,63 (p = 0,08) en todos y 0,43
(p = 0,50) entre los sin obstrucción (10 de 45). Con 60, igual: 0,64 y 0,51.

### Cómo se eligieron las dos medidas: el embudo (`docs/figuras/embudo.json`)

Cada una de las 27 medidas pasa tres filtros, por orden:

| Filtro | Pasan |
|---|---|
| Estable: acuerdo de 0,90 o más entre los dos filtros del escáner | 13 de 27 |
| Asociada: relación con el FEV1/FVC con q < 0,05 | 10 de esas 13 |
| Aporta algo nuevo: la relación se mantiene (p < 0,05) al descontar las ya elegidas | 2: una de vía aérea y el enfisema |

Ejemplos para contarlo:

- **Fuera por inestable y sin asociación:** Pi10 y grosor de pared. Acuerdo de
  0,62 y 0,66, y q de 0,68 y 0,42.
- **Fuera por inestable aunque sí se asocia:** el %LAA-950 clásico. q = 0,003,
  pero acuerdo de 0,18: su valor depende del filtro del escáner.
- **Fuera por redundante aunque pasa los dos primeros filtros:** el volumen
  vascular. Acuerdo de 0,93 y q < 0,001, pero al descontar las dos elegidas su
  relación con el cociente baja a -0,19 (p = 0,09): dice lo mismo que ellas. Y el
  número de ramas se parece a los extremos del árbol un 0,99.
- **Dentro, aunque es la segunda:** el enfisema. Descontando la vía aérea, sigue
  relacionado con el cociente (-0,34, p = 0,002): dice algo que la vía aérea no.

El embudo elige como medida de vía aérea los extremos del árbol, que es la más
asociada; nuestro modelo usa la longitud total, fijada antes. Se parecen un 0,97
y fuera de muestra dan lo mismo (diferencia de 0,01 en la correlación).

### La línea de la TC reconstruye la de la espirometría

Con el umbral de 0,48, la TC deja por encima a 26 de los 28 con obstrucción y
por debajo a 38 de los 52 sin ella: las dos líneas coinciden en 64 de 80. Fuera
de muestra, 82 % y 75 %. Los 14 en los que no coinciden por el lado sano son los
posibles pre-EPOC.

### El experimento ciego (`docs/figuras/umbral_natural.json`)

Lo esperado se ajusta con los 80 sin saber quién es caso, y la frontera sale de
partir la puntuación en dos grupos sin ninguna etiqueta. La espirometría no
entra en ningún paso.

| Qué | Cifra |
|---|---|
| Coinciden con la obstrucción | 64 de 80 |
| Grupo alto por la TC | 26 personas, FEV1/FVC mediano de 0,62; ahí están 19 de los 28 con obstrucción |
| Grupo bajo por la TC | 54 personas, FEV1/FVC mediano de 0,755; ahí están 45 de los 52 sin obstrucción |
| Relación de la puntuación ciega con FEV1/FVC | -0,56 (el modelo, -0,73) |
| Qué corte del cociente separa mejor la TC | Igual de bien de 0,60 a 0,71; a partir de 0,72, peor |

No es el modelo: funciona peor, porque los enfermos entran en lo que se toma
como esperado. Es la prueba de que la señal no viene de haberle enseñado la
respuesta.

## 2. La cohorte con el modelo final (80 sujetos)

| Qué | Cifra |
|---|---|
| Clases | 38 control, 14 posible pre-EPOC, 28 EPOC |
| Posible pre-EPOC | Sin obstrucción y con la TC parecida a la de la EPOC. El PRISm ya no entra: las investigadoras del reto no lo consideran una buena definición |
| Umbral de "TC parecida a la de la EPOC" | 0,48 |
| Límite superior de normalidad | 1,23: lo supera 1 de 52 controles y 16 de 28 con EPOC |
| Zona gris alrededor del umbral | 0,18 |
| AUC a 80, 100 y 120 kVp | 0,89, 0,91 y 0,93 |
| AUC en hombres y en mujeres | 0,85 y 0,95 |
| AUC en quien fuma y en quien no | 0,92 y 0,90 |
| Dentro de los controles: sexo, tabaco, kVp | AUC 0,51 y 0,50; p = 0,95 |
| Acuerdo entre reconstrucciones: puntuación | 0,98 (0,94 solo entre controles) |
| Acuerdo: %LAA-950 clásico | 0,18 |
| Acuerdo: %LAA-950 suavizado | 0,93 |
| Acuerdo: longitud de vía aérea | 0,94 |
| Acuerdo: grosor de pared estimado | 0,66 |
| Acuerdo: Pi10 aproximado | 0,62 |
| Acuerdo: disanapsia aproximada | 0,75 |
| Clínica sola frente a FEV1/FVC (Spearman, validación cruzada; exploratorio) | 0,17 |
| Clínica más las dos medidas de TC | 0,76 |
| Relación de la puntuación con los síntomas (CAT) | 0,33 en el conjunto (p = 0,003); 0,06 dentro de los controles |
| Relación con la DLCO | -0,64 dentro de la EPOC; nada en el conjunto ni en los controles |
| Mediana de %LAA-950 clásico | 0,42 % en controles, 3,1 % en EPOC |
| Mediana de %LAA-950 suavizado | 0,02 % en controles, 0,2 % en EPOC |
| Ruido de la imagen frente a la puntuación | -0,07 |

Los 14 posibles pre-EPOC (controles con la TC parecida a la de la EPOC), frente a los otros 38:

| | Con | Sin | p |
|---|---|---|---|
| FEV1/FVC | 0,75 | 0,78 | 0,03 |
| FEV1/FVC por debajo de 0,75 | 7 de 14 | 8 de 38 | |
| Calibre central para su pulmón (z; más es más estrecho) | 0,48 | -0,22 | 0,015 |
| FEV1, % del predicho | 91 | 97 | 0,28 |
| CAT | 9 | 5,5 | 0,15 |
| DLCO, % | 79 | 74 | 0,32 |
| Enfisema visual | 29 % | 11 % | 0,19 |
| Cambio del FEV1 % a 3,6 años | +3,4 | +2,9 | 0,36 |

Paquetes-año: dentro de los controles, -0,24 (p = 0,10); dentro de la EPOC, -0,57 (p = 0,002), y -0,58 (p = 0,002, n = 26) descontando la edad y fumar ahora. Más tabaco acumulado no va con más puntuación.

### Obstrucción por el límite inferior de normalidad (LLN)

El LLN del FEV1/FVC sale de GLI-2012 (caucásica) con la edad, el sexo y la talla
de cada persona (`scripts/lln_analysis.py`, `docs/figuras/lln.json`). El FEV1 en
% del predicho que calcula coincide con el de la tabla (diferencia mediana 0,3
puntos), así que las ecuaciones son las mismas.

| | |
|---|---|
| LLN del cociente en esta cohorte | 0,70 de mediana (0,68 a 0,72) |
| Sin obstrucción por el 0,70 y por debajo de su LLN | 1 de 52 |
| De ellos, entre los 14 posibles pre-EPOC | 1 de 14 (0 de los otros 38; Fisher p = 0,27) |
| EPOC por el 0,70 pero no por el LLN | 0 de 28 |
| Puntuación frente al z del cociente, entre los 52 sin obstrucción | -0,33 (p = 0,017) |

En esta cohorte, de 45 a 65 años, el LLN cae casi encima del 0,70: cambiar de
criterio no reclasifica a nadie salvo a uno. Los 14 no son obstruidos que se
escapan del 0,70: 13 tienen el cociente normal para su edad, sexo y talla. Y la
relación con el cociente dentro de los no obstruidos se mantiene con el z, que ya
descuenta esas tres variables.

### La misma puntuación, dos lecturas (exploratorio)

Las investigadoras sugirieron mirar a los que se salen y buscar relación con las
variables de la tabla (`scripts/explore_outliers.py`, `docs/figuras/discordantes.json`).
Son muchas comparaciones con pocos sujetos: q es la p corregida.

| La puntuación frente a... | Entre los 52 sin obstrucción | Entre los 28 con EPOC |
|---|---|---|
| Calibre central estrecho para su pulmón (disanapsia aproximada) | 0,37 (p = 0,007; q = 0,11) | 0,05 |
| Disnea (mMRC) | -0,12 | 0,69 (q = 0,001) |
| DLCO, % del predicho | 0,15 | -0,64 (q = 0,002) |
| Enfisema visual | 0,02 | 0,62 (q = 0,003) |
| FEV1, % del predicho | -0,06 | -0,53 (q = 0,02) |
| Paquetes-año | -0,24 (p = 0,10) | -0,57 (q = 0,01) |
| Fumar ahora | 0,00 | -0,14 |

- En la EPOC, la puntuación es gravedad: más disnea, peor intercambio de gases,
  más enfisema visible.
- En quien no tiene obstrucción, va con unas vías centrales estrechas para el
  tamaño del pulmón y no con el tabaco. Es compatible con un árbol pequeño de
  origen; no lo demuestra, y el calibre y la longitud salen de la misma
  segmentación.
- Dentro de la EPOC, más puntuación va con menos paquetes-año. Pregunta abierta:
  ¿enferman con poco tabaco quienes tienen el árbol pequeño, o los más graves
  dejaron de fumar antes?
- Solo 2 de los 28 con EPOC tienen la TC como la de un control: no hay grupo que
  explorar por ese lado.


## 3. La prueba en reserva del modelo anterior (15 sujetos: 6 con EPOC, 9 controles)

El mismo modelo, ajustado solo con 62 sujetos, y 15 apartados que no vio.
Criterios escritos antes de mirar (`protocolo-reserva.md`).

| Qué | Cifra | Criterio fijado antes |
|---|---|---|
| Separa EPOC de control (AUC) | 0,85, IC de 0,61 a 1 | 0,80 o más: cumple |
| Relación con FEV1/FVC (Spearman) | -0,81 (p < 0,001) | -0,5 o más fuerte: cumple |
| Mediana de la puntuación en los controles | 0,02 | entre -0,5 y 0,5: cumple |
| Con EPOC por encima del umbral | 6 de 6 (IC de 0,54 a 1) | |
| Controles por encima del umbral | 4 de 9 (por debajo: 5 de 9, IC de 0,21 a 0,86) | menos de la mitad: cumple por poco |
| Acuerdo entre reconstrucciones (ICC) | 0,99; misma decisión en 15 de 15 | 0,90 o más: cumple |
| Clínica sola y clínica más TC frente a FEV1/FVC | 0,06 y 0,89 (comparación descriptiva) | |

## Palabras

- "Puntuación de daño" se mantiene como nombre. Lo que supera el umbral se llama
  "TC parecida a la de la EPOC", no "daño objetivo": el umbral separa EPOC de
  control, no demuestra lesión.
- La TC de un sujeto tiene tres niveles: "como la referencia" (por debajo del
  umbral), "intermedia" (entre el umbral y el límite de normalidad) y "por
  encima de lo normal".
- La clase intermedia es "posible pre-EPOC": sin obstrucción y con la TC
  parecida a la de la EPOC. Sin PRISm.
- "Sin obstrucción (FEV1/FVC de 0,70 o más)", no "espirometría normal".
- "Acuerdo alto entre estas dos reconstrucciones" o la cifra, no "no cambia" ni
  "sin sesgos". "No hemos encontrado relación con...", no "descarta artefactos".
- "No detectamos diferencias en síntomas", no "no tienen más síntomas".
- La puntuación se calcula "sin usar su espirometría", no "solo con la imagen":
  usa edad, sexo, talla y tabaco.
- Grosor de pared "estimado", Pi10 y disanapsia "aproximados".
- La TC ve el daño antes que la espirometría: solo como motivación.
- Lo nuevo de hoy que sí se puede decir: entre quienes no tienen obstrucción, la
  puntuación sigue al FEV1/FVC (-0,34, p = 0,016, con modelos que no vieron a
  cada sujeto), y las vías de menos de 3 mm siguen al cociente más que las de
  3 mm o más. No se dice "la señal está en las vías finas" como hecho probado:
  entre los sin obstrucción la diferencia no está demostrada.
- En el paso Connect, con el modelo final: puntuación 0,12 (p = 0,22), enfisema
  0,07 (p = 0,30), vía aérea 0,11 (p = 0,33), FEV1/FVC 0,39 (p = 0,72), n = 74.
