# El modelo, pieza a pieza

Qué hace cada parte, por qué la elegimos y qué no sabemos todavía. Los números
son del modelo final, ajustado con los 80 sujetos, y su rendimiento es el de la
validación cruzada anidada: cada sujeto puntuado por un modelo que no lo vio.
Donde se dice "reserva" son los 15 sujetos apartados con los que se probó, una
sola vez, la versión anterior del modelo.

## En una frase

Medimos en la TC cuánto enfisema hay y cuánto árbol bronquial se ve, comparamos
cada medida con lo que se espera en una persona de la misma edad, sexo, talla y
hábito de tabaco, y resumimos las dos desviaciones en una puntuación de daño que
alimenta una regla de tres clases.

No hay ninguna red entrenada por nosotros. La única red es la de segmentación,
que viene preentrenada. El resto son dos medidas, una regresión lineal y un
umbral.

## Las cinco piezas

```
TC  ->  1. segmentar  ->  2. medir  ->  3. comparar con lo esperado  ->  4. puntuación  ->  5. clase
                                               ^                                              ^
                                    edad, sexo, talla, tabaco, kVp               FEV1/FVC y FEV1 de la tabla
```

### 1. Segmentar

**Qué.** TotalSegmentator separa los cinco lóbulos, la luz de la vía aérea, la
pared bronquial, las arterias y las venas pulmonares.

**Cómo es por dentro.** Es una nnU-Net, una U-Net 3D que ajusta sola su
configuración al conjunto de datos. Está entrenada por sus autores con más de
mil TC anotadas. Nosotros solo la ejecutamos.

**Por qué.** Segmentar a mano 80 TC no es posible en dos días, y una red propia
entrenada con 80 sujetos sería peor. Es de código abierto, funciona sin
internet y tarda un minuto por TC en una GPU.

**Qué no sabemos.** La calidad de la segmentación de vía aérea en TC de baja
dosis. La revisamos a ojo en una TC pública y es plausible. No hemos encontrado
ninguna validación independiente de TotalSegmentator en pulmón con enfisema.

Referencias: Wasserthal 2023 e Isensee 2021, en la [bibliografía](bibliografia.md), punto 1.

### 2. Medir

De cada TC salen 27 medidas, por lóbulo cuando tiene sentido. Están todas las
que nombra el reto y varias más:

| Lo que pide el reto | Medida | Cómo se calcula |
|---|---|---|
| Presencia y % de enfisema | `laa950`, `laa950_smooth` | Porcentaje del parénquima (sin vasos ni vías) por debajo de -950 HU, crudo y tras un filtro gaussiano de 1 mm |
| Grosor de pared de vía aérea | `via_grosor_pared_mm`, `via_pared_pct`, `via_pi10_mm` | Grosor medio, porcentaje de área de pared y Pi10, en las vías de 6 a 20 mm de perímetro interno |
| Disanapsia | `via_disanapsia` | Calibre de las 15 vías más anchas partido por la raíz cúbica del volumen pulmonar |
| Rasgos nuevos | `via_longitud_mm`, `via_longitud_fina_mm`, `via_extremos`, `via_longitud_lobar_mm`, `agrupamiento`, `vasos_por_litro` | Longitud del árbol bronquial que se segmenta, en total, por calibre y por lóbulo; extremos del árbol; agrupamiento del enfisema; volumen vascular |

Las de pared y la disanapsia son aproximaciones. El grosor y el Pi10 salen de la
máscara de pared de la segmentación, suponiendo secciones circulares, no del
perfil de densidad del bronquio. La disanapsia usa las vías más anchas que
encuentra la segmentación, no las 19 localizaciones anatómicas de Smith 2020.

**La puntuación usa dos.** Una por cada compartimento donde empieza la EPOC:

| Compartimento | Medida | Qué mide |
|---|---|---|
| Parénquima | `laa950_smooth` | Cuánto enfisema hay |
| Vía aérea | `via_longitud_mm` | Cuánto árbol bronquial se ve en la TC |

**Por qué estas dos.** Cada sujeto tiene la misma adquisición reconstruida con
dos kernels. Para cada medida miramos dos cosas: si sigue la limitación al flujo
aéreo y si da lo mismo en las dos reconstrucciones.

| Medida | Acuerdo entre kernels (ICC) | AUC para EPOC | Spearman con FEV1/FVC |
|---|---|---|---|
| `laa950`, el clásico | 0,18 | 0,68 | -0,40 |
| `perc15` | 0,23 | 0,49 | -0,10 |
| `via_pi10_mm` | 0,62 | 0,60 | -0,08 |
| `via_grosor_pared_mm` | 0,66 | 0,64 | -0,15 |
| `via_disanapsia` | 0,75 | 0,65 | -0,33 |
| `via_ramas_por_litro` | 0,95 | 0,90 | -0,69 |
| `vasos_por_litro` | 0,93 | 0,72 | -0,46 |
| **`laa950_smooth`** | **0,93** | **0,71** | **-0,46** |
| **`via_longitud_mm`** | **0,94** | **0,92** | **-0,67** |

El %LAA-950 clásico depende de cómo se reconstruyó la imagen. Filtrar antes de
contar lo corrige. La longitud del árbol bronquial es la medida que mejor sigue
la obstrucción y es igual de estable.

**Por qué no otra medida de vía aérea.** Con los 80 sujetos probamos seis
candidatos para acompañar al enfisema: la longitud total, la de las vías de
menos de 3 mm, su fracción, el número de extremos, el número de ramas y la
longitud por lóbulo. La comparación se hizo fuera de muestra, eligiendo dentro
de cada vuelta de la validación. Ninguno mejora a la longitud total: la mayor
ganancia en la correlación con el FEV1/FVC es de 0,01, con un intervalo de -0,02
a 0,05. Son medidas muy parecidas entre sí, y la regla de elección escogía una
distinta en cada vuelta. Los candidatos y la regla se escribieron antes
([`protocolo-mejora.md`](protocolo-mejora.md)).

**De dónde parece venir la señal.** De las vías finas. La longitud de las vías
de menos de 3 mm de luz sigue al FEV1/FVC más que la de las vías de 3 mm o más:
la diferencia entre sus correlaciones es de 0,36, con un intervalo de 0,10 a
0,60. Entre quienes no tienen obstrucción la diferencia va en el mismo sentido
(-0,34 frente a 0,05) y no está demostrada. El corte de 3 mm es aproximado, y
estas ramas visibles no son la vía aérea pequeña (menos de 2 mm), que la TC no resuelve.

**Por qué el enfisema se queda.** No ayuda a separar la EPOC, pero sí a seguir
el cociente: -0,73 con él y -0,67 sin él. Y es lo primero que pide el reto.

**Lo que dice la literatura.** El umbral de -950 HU se validó contra histología
(Gevenois 1996). Que el kernel y el ruido mueven el %LAA-950 varios puntos se
sabe desde 2004 (Boedeker), y un filtro de ruido lo corrige (Schilham 2006). En
CanCOLD, el recuento de vías aéreas visibles es un 19 % más bajo en la EPOC leve
(Kirby 2018), y en fumadores sin obstrucción es la única medida de TC que
predice EPOC a tres años (Kirby 2021). Los acuerdos entre kernels de la tabla
son nuestros, no de ningún artículo.

**Qué no sabemos.** La longitud del árbol depende de hasta dónde llega la
segmentación. Kirby usó otro programa (VIDA) y contó vías; nosotros sumamos
longitud con TotalSegmentator, y nadie ha validado eso. No hemos encontrado
relación con el kVp, el paso de corte, el ruido de la imagen ni el índice de
masa corporal; el resultado se mantiene al descontar el tamaño del píxel, y hay
acuerdo alto entre las dos reconstrucciones. Eso cubre los artefactos que hemos
sabido buscar, no todos. Y hay algo que estos datos no separan: si en la EPOC
hay menos vías o si las mismas vías, más estrechas, se segmentan peor. Las
longitudes de cada rama son aproximadas: al unir tramos se pierden los puentes
entre ellos, lo que afecta al recuento de ramas pero no a la longitud total.

### 3. Comparar con lo esperado

**Qué.** Para cada medida y cada lóbulo ajustamos, solo con los controles de
desarrollo, una regresión lineal sobre edad, talla, volumen pulmonar, sexo,
tabaquismo activo y kVp. El z de un sujeto es su residuo partido por la
dispersión de los residuos de la referencia.

**Por qué.** Es lo que hace la espirometría: el FEV1 no se interpreta en
litros, sino como porcentaje de lo esperado para la edad, el sexo y la talla.
Un pulmón grande tiene menos densidad sin estar enfermo.

**Por qué esas covariables.**

- *Volumen pulmonar*: corrige cuánto inspiró el sujeto. Menos aire, más densidad.
- *Tabaquismo activo*: en nuestros datos, quien fuma tiene Perc15 de -890 HU
  frente a -912. La inflamación sube la densidad y tapa el enfisema.
- *kVp*: es lo que varía entre adquisiciones (80, 100 y 120).

**Cuatro cuidados.**

- Cada control recibe el z de un modelo ajustado con los otros 51. Antes se
  repartían en cinco grupos al azar, y el umbral de daño cambiaba con el reparto.
- La escala del z es la del error con un sujeto que el ajuste no vio. Con 40
  sujetos de referencia y 8 columnas de covariables, usar los residuos del propio ajuste
  inflaba el z de un sujeto nuevo en torno a un 24 %.
- La dispersión se estima con la MAD, que aguanta que algún control tenga daño.
- El porcentaje de enfisema se compara en logaritmo. En estos controles la
  mediana del %LAA-950 suavizado es 0,02 %, y en la EPOC hay sujetos por encima
  del 10 %. En escala lineal, un sujeto con un 3 % quedaba a decenas de
  desviaciones y esa sola medida decidía la puntuación. Antes del logaritmo se
  suma 0,01; con 0,001 o con 0,1 el resultado es el mismo.

**Lo que dice la literatura.** La espirometría puntúa frente a ecuaciones de
referencia (GLI 2012). Para la densidad en TC existen ecuaciones en nunca
fumadores de 54 a 93 años (Hoffman 2014), pero ninguna para adultos de 35 a 50
ni por escáner. Por eso la referencia es propia. Los fumadores activos tienen
el pulmón más denso: 3,5 puntos menos de %LAA-950 en COPDGene (Zach 2016), y la
Fleischner Society recomienda estratificar por tabaquismo (2025).

**Qué no sabemos.** La referencia son fumadores sin obstrucción, no personas
sanas. El z dice "se aparta de un fumador sin EPOC", no "se aparta de un pulmón
sano". En la prueba de reserva, el z de los controles nuevos se centró en cero
(mediana 0,02) con una dispersión de 0,7 en el enfisema y 1,2 en la vía aérea.

### 4. La puntuación de daño

La media de los dos z, orientados para que positivo sea peor. Cada medida pesa
lo mismo: el enfisema se resume antes en un número por sujeto, la media de sus
cinco lóbulos.

| Qué hace la puntuación | Modelo final, fuera de muestra (80) | Primera prueba, en reserva (15) |
|---|---|---|
| Sigue la limitación al flujo aéreo | Spearman con FEV1/FVC de -0,73 | -0,81 |
| La sigue entre quienes no tienen obstrucción | -0,34, p = 0,016 | |
| Separa EPOC de control | AUC 0,91 | 0,85, IC de 0,61 a 1 |
| Acuerdo alto entre las dos reconstrucciones | ICC 0,98 | 0,99 |

Y describiendo la cohorte con el modelo final: da AUC parecidos a 80, 100 y 120
kVp (0,89, 0,91 y 0,93); dentro de los controles no distingue sexo, tabaco ni
kVp; sigue la DLCO solo dentro de la EPOC (-0,64); y se relaciona con los
síntomas en el conjunto (CAT, 0,33) pero no dentro de los controles (0,06).
Añade a la clínica: edad, sexo, talla y tabaco dan un Spearman de 0,17 con el
FEV1/FVC, y con las dos medidas de TC, 0,76. Esa cuenta es exploratoria, porque
lo esperado no se reajusta en cada vuelta; en la prueba de reserva, donde sí
estaba todo ajustado sin esos sujetos, fue de 0,06 a 0,89.

### 5. La regla de tres clases

1. **EPOC**: FEV1/FVC posbroncodilatador menor de 0,70. Es el criterio de la
   cohorte para sus casos: obstrucción persistente compatible con EPOC.
2. **Posible pre-EPOC**: sin obstrucción y con la TC parecida a la de la EPOC
   (puntuación de 0,48 o más).
3. **Control**: lo demás.

Es una clasificación experimental, no una definición clínica validada. La
aplicación enseña siempre la puntuación y la frase que dice por qué.

**De dónde sale 0,48.** Es el punto de la puntuación que mejor separa EPOC de
control. Dice "esta TC se parece a las de la EPOC". No demuestra que haya una
lesión. Fuera de muestra deja por encima al 82 % de los sujetos con EPOC y por
debajo al 75 % de los controles.

**Era la pieza más frágil, y con todos los sujetos lo es menos.** Con 40
controles, el umbral iba de 0,33 a 0,63 según cómo cayera el ajuste cruzado; con
52, de 0,45 a 0,50. Entre las dos reconstrucciones de una misma TC, la diferencia
de puntuación tiene una dispersión robusta de 0,18: a esa distancia del umbral,
la aplicación avisa de que el sujeto está cerca.

**El segundo umbral.** El límite superior de normalidad de la referencia, 1,23,
no usa a los sujetos con EPOC: es la mediana de los controles más 1,645 desviaciones
robustas, lo que sería el percentil 95 si la puntuación fuera normal. Fuera de
muestra deja por debajo al 96 % de los controles y por encima al 54 % de los
sujetos con EPOC. Es más defendible como "anormal" y mucho menos sensible. La
aplicación enseña la TC en tres niveles: como la referencia, intermedia y por
encima de lo normal.

**Por qué no el PRISm.** La primera versión de la regla contaba también como
pre-EPOC a quien tiene el FEV1 por debajo del 80 % con el cociente conservado.
Las investigadoras del reto no lo consideran una buena definición, y se quitó.
GOLD 2023 y Han 2021 definen pre-EPOC como síntomas, lesiones estructurales o
alteraciones funcionales sin obstrucción, y no dan ningún umbral numérico.

**Por qué no la DLCO.** Está por debajo del 80 % en 6 de cada 10 controles de
esta cohorte, y no sabemos si está corregida por la hemoglobina y por el
monóxido del tabaco. No entra por esa incertidumbre, no porque no importe.

**Por qué 0,70 y no el límite inferior de normalidad.** Porque es la etiqueta
con la que la cohorte definió sus casos. En adultos de 35 a 50 años el límite
inferior de normalidad del cociente está más arriba, cerca de 0,75, así que
parte de los "controles" de esta cohorte tendrían obstrucción con ese criterio.

**Qué da.** 38 controles, 14 posibles pre-EPOC y 28 EPOC.

**Lo que hay que decir sin rodeos.** Los 14 posibles pre-EPOC tienen el FEV1/FVC
más bajo que los demás controles (0,75 frente a 0,78, p = 0,03), y 7 de ellos
están por debajo de 0,75. No detectamos diferencias en síntomas ni en DLCO, y a
los 3,6 años su función no ha caído más. Lo más probable es que la TC esté
viendo a la gente que roza la obstrucción, no una enfermedad que la
espirometría no ve.

**Qué significa la puntuación en cada grupo.** Explorando a los que se salen, la
puntuación se lee de dos maneras. En la EPOC es gravedad: va con la disnea
(0,69), la DLCO (-0,64) y el enfisema visual (0,62). En quien no tiene
obstrucción va con un calibre central estrecho para su pulmón (0,37) y no con el
tabaco. Es exploratorio; el detalle está en [los resultados](resultados.md).

## Cómo se juntan la TC y la tabla

Por fusión tardía, no con dos torres neuronales.

- La "torre" de TC no es una red: es segmentación, medidas y z. Su salida es un
  vector corto e interpretable por sujeto.
- La tabla clínica entra como otro bloque de variables.
- Los bloques se combinan con un modelo lineal regularizado, evaluado con
  validación cruzada anidada. La escalera de evidencia dice qué añade cada
  bloque.

**Por qué no dos torres con una capa de fusión.** Con 80 sujetos no hay datos
para aprender una representación conjunta. Lo comprobamos antes de empezar: una
ResNet-50 congelada empató con Perc15 en una base pública y correlacionaba
-0,95 con él. Y un vector de 1.536 dimensiones no se le puede explicar a un
clínico.

**Cuándo cambiaría.** Con miles de sujetos y un objetivo claro, un encoder 3D
preentrenado con atención por parches sería la opción. Está fuera del alcance
de esta cohorte.

## Lo molecular

`scripts/connect.py` es un motor de asociaciones al estilo de un EWAS: para cada
exposición (la puntuación de daño, el z de una medida o una variable clínica)
ajusta un modelo lineal por rasgo molecular, con covariables, y corrige por
comparaciones múltiples dentro de cada exposición. La tabla molecular lleva un
sujeto por fila y un rasgo por columna.

No nos han dado datos moleculares y no simulamos ninguno. El único biomarcador
de la tabla es el FENO, un indicador indirecto de inflamación eosinofílica, y
con él está ejecutado: ajustando por edad, sexo, talla, tabaco y asma, no se
detecta asociación con la puntuación ni con el FEV1/FVC (p = 0,22 y 0,72, 74
sujetos). Con 74 sujetos eso no demuestra que no la haya.

Para metilación no basta con cambiar la tabla. La matriz tiene que llegar
depurada (control de calidad de sondas y muestras, M-values), y hay que ajustar
por la composición celular y por el lote, que el script acepta como covariables
pero no calcula.

## Sujetos nuevos

`scripts/score_cohort.py` guarda el modelo: las regresiones por región, el
umbral y la regla. `scripts/predict.py` lo aplica a sujetos que no estaban en
la cohorte, sin reajustar nada.

## Cómo se valida

- **Primero, una reserva.** Con 62 sujetos se cerró un modelo y se probó una
  vez en 15 que no había visto, con lo que se iba a medir escrito antes
  ([`protocolo-reserva.md`](protocolo-reserva.md)). Cumplió.
- **Después, todos los sujetos.** El modelo final se ajusta con los 80 y se
  valida con validación cruzada anidada: en cada vuelta se reajusta lo esperado,
  se eligen las medidas y se fijan los umbrales solo con los sujetos de
  entrenamiento ([`protocolo-mejora.md`](protocolo-mejora.md)). Es más débil
  que una reserva, y es lo que queda cuando se usan todos los datos.
- **Controles negativos.** La puntuación no debe separar sexo, tabaco ni kVp.
- **Estabilidad.** La misma TC con otro kernel debe dar la misma puntuación.
- **Calidad de imagen.** No debe seguir el ruido, el tamaño del píxel ni el paso de corte.
- **Revisión independiente.** El 2 de octubre, revisores automáticos de otra
  familia de modelos leyeron la estadística, el código de medida y la biología.
  Encontraron errores en las longitudes de rama, en la raíz del árbol, en el
  suavizado y en la escala del z, que se corrigieron antes de la prueba de reserva.

## Lo que el modelo no hace todavía

- No demuestra daño clínicamente relevante dentro de los controles.
- No predice quién empeora: la caída del FEV1 a 3,6 años es casi ruido.
- No tiene un umbral estable: es la pieza que más cambiaría con más sujetos.
- No distingue una vía aérea perdida de una estrecha que se segmenta peor, ni
  de un árbol pequeño de origen.
- Tres sujetos entran con la otra reconstrucción de su TC, porque la estándar está incompleta. La puntuación mostró un acuerdo alto entre las dos, pero no está demostrado que sean intercambiables.
