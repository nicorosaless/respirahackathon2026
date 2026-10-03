# Protocolo de la mejora del modelo con todos los sujetos

Escrito el 2 de octubre por la tarde, antes de calcular nada de lo que describe.

## De dónde se parte

El modelo del 2 de octubre a mediodía (dos medidas, lo esperado ajustado con 40
controles, umbral de Youden) se probó una vez en 15 sujetos de reserva y cumplió
los criterios escritos antes (`protocolo-reserva.md`). Ese resultado es de ese
modelo y se queda como está.

A partir de aquí se usan todos los sujetos para ajustar. Ya no queda ningún
sujeto apartado, así que el rendimiento del modelo nuevo se estima con validación
cruzada anidada, que es más débil que una reserva y se dice así.

## Qué se cambia y por qué

Cada cambio responde a un hallazgo de la revisión independiente.

| Hallazgo | Cambio |
|---|---|
| La referencia y el umbral salen de 40 controles y el umbral es inestable | Ajustar con todos los controles disponibles |
| Tres sujetos quedaron fuera por tener incompleta la serie estándar, y la puntuación es casi igual con la otra reconstrucción | Recuperarlos con su serie de kernel duro, que está completa |
| La validación no repetía la elección de medidas ni el modelo normativo en cada vuelta | Validación cruzada anidada: en cada vuelta se reajusta lo esperado, se eligen las medidas y se fija el umbral solo con los sujetos de entrenamiento |
| La longitud total mezcla vías centrales, que no cambian, con periféricas; y depende del calibre | Medir la longitud por calibre y por lóbulo |
| El umbral de Youden dice "se parece a EPOC", no "es anormal" | Comparar, fuera de muestra, el umbral de Youden con el límite superior de normalidad |
| Algunos controles rozan la obstrucción y están en la referencia | Probar una referencia sin ellos |

## Candidatos, fijados antes de mirar

La puntuación es siempre la media, con pesos iguales, del z del enfisema
(`laa950_smooth`) y el z de una medida de vía aérea. Los candidatos para esa
segunda medida:

1. `via_longitud_mm`: longitud total. Es el modelo actual.
2. `via_longitud_fina_mm`: longitud de las vías de menos de 3 mm de diámetro de luz.
3. `via_fraccion_fina`: esa longitud partida por la total.
4. `via_extremos`: número de extremos del árbol, las vías más periféricas que se ven.
5. `via_ramas`: número de ramas.
6. `via_longitud_lobar_mm`: longitud dentro de cada lóbulo, comparada lóbulo a lóbulo.

`via_longitud_gruesa_mm`, la longitud de las vías de 3 mm o más, se calcula como
control: no debería separar tanto.

Dos referencias: todos los controles, y solo los controles con FEV1/FVC de 0,75 o
más y FEV1 del 80 % o más.

## Cómo se decide

- Validación cruzada de 5 grupos, estratificada por caso, repetida 10 veces. En
  cada vuelta, con los sujetos de entrenamiento: se ajusta lo esperado, se
  calcula el acuerdo entre reconstrucciones y se elige el candidato.
- **Regla de elección, dentro de cada vuelta:** entre los candidatos con acuerdo
  entre reconstrucciones de 0,90 o más, el de mayor correlación de Spearman, en
  valor absoluto, entre la puntuación y el FEV1/FVC.
- **Lo que se informa**, siempre con los sujetos de prueba de cada vuelta:
  correlación con FEV1/FVC en todos y dentro de los controles, AUC para EPOC,
  sensibilidad y especificidad con los dos umbrales, y acuerdo entre
  reconstrucciones. Para cada candidato fijo y para el procedimiento de elección
  entero.
- **Qué cuenta como mejora:** el modelo nuevo sustituye al actual si la
  correlación con FEV1/FVC fuera de muestra mejora en todos y no empeora dentro
  de los controles, y el acuerdo entre reconstrucciones sigue en 0,90 o más. La
  diferencia se da con su intervalo por bootstrap emparejado. Si el intervalo
  incluye el cero, se dice que no hay mejora demostrada, y el modelo actual se
  queda, reajustado con todos los sujetos.
- No se prueban más candidatos que estos. Si ninguno mejora, se cuenta así.

## Resultado (2 de octubre por la noche)

80 sujetos: 28 con EPOC y 52 controles. Los tres con la serie estándar incompleta
se recuperaron con la otra reconstrucción.

| Medida de vía aérea, junto al enfisema | Spearman con FEV1/FVC, fuera de muestra | Entre los sin obstrucción | AUC | Acuerdo entre reconstrucciones | Mejora sobre el modelo actual |
|---|---|---|---|---|---|
| **Longitud total (modelo actual)** | **-0,73** (de -0,83 a -0,57) | **-0,34** (de -0,61 a -0,04; p = 0,016 por permutación) | 0,91 | 0,98 | |
| Longitud de las vías de menos de 3 mm | -0,73 | -0,41 (p = 0,003) | 0,89 | 0,97 | 0,00 (de -0,06 a 0,05) |
| Fracción de vía fina | -0,56 | -0,37 | 0,76 | 0,93 | -0,16 (de -0,33 a -0,01) |
| Extremos del árbol | -0,73 | -0,38 (p = 0,006) | 0,90 | 0,98 | 0,01 (de -0,02 a 0,04) |
| Número de ramas | -0,73 | -0,37 | 0,90 | 0,98 | 0,01 (de -0,02 a 0,04) |
| Longitud por lóbulo | -0,72 | -0,34 | 0,91 | 0,98 | 0,00 (de -0,01 a 0,01) |
| El procedimiento de elección entero | -0,72 | -0,35 | 0,90 | 0,98 | 0,00 (de -0,05 a 0,03) |
| Control: vías de 3 mm o más | -0,56 | -0,10 (p = 0,47) | 0,84 | 0,97 | -0,17 (de -0,30 a -0,05) |
| Control: solo vía aérea, sin enfisema | -0,67 | -0,28 | 0,92 | 0,97 | -0,05 (de -0,16 a 0,06) |
| Control: solo enfisema | -0,46 | -0,29 | 0,72 | 0,97 | -0,27 (de -0,45 a -0,12) |

Con la referencia sin los controles que rozan la obstrucción (33 en vez de 52), la
mejora es de 0,01 (de -0,02 a 0,05) y el límite de normalidad se vuelve menos
específico (92 % frente a 96 %).

**Decisión, según la regla escrita antes:** ningún candidato mejora al modelo
actual con un intervalo que excluya el cero. El modelo se queda con la longitud
total y se reajusta con los 80 sujetos. En cada vuelta la regla elegía una
medida distinta (nueve ganadores diferentes en 50 vueltas): con estos datos,
elegir entre estas medidas es elegir ruido.

**Lo que sí ha mejorado, y por qué:**

- Con 52 controles en vez de 40 y las medidas corregidas, la puntuación sigue al
  FEV1/FVC también entre quienes no tienen obstrucción: -0,34, p = 0,016, con
  modelos que no vieron a cada sujeto. Antes era -0,26 y no se distinguía del azar.
- El umbral deja de depender del reparto: antes iba de 0,33 a 0,63 según cómo
  cayera el ajuste cruzado; ahora, de 0,45 a 0,50.
- Hay una pista de dónde viene la señal: la longitud de las vías de menos de
  3 mm de luz sigue al FEV1/FVC más que la de las vías de 3 mm o más (diferencia
  de 0,36 entre sus correlaciones, de 0,10 a 0,60). Entre los sin obstrucción la
  diferencia va en el mismo sentido y no está demostrada (0,29, de -0,10 a 0,49).
- Sin los 3 sujetos recuperados con la otra reconstrucción, el resultado es el
  mismo: -0,73 y -0,33 entre los sin obstrucción (p = 0,02).
- El rendimiento se informa fuera de muestra: AUC 0,91 con la medida fijada, y
  0,90 si además se elige la medida en cada vuelta. Las decisiones anteriores,
  como las covariables o la lista de candidatos, no se repiten dentro de la
  validación.

**Los dos umbrales, fuera de muestra:** el de Youden deja por encima al 82 % de
los sujetos con EPOC y por debajo al 75 % de los controles. El límite superior
de normalidad, al 54 % y al 96 %, y sus decisiones cambian la mitad de veces
entre repeticiones. La aplicación enseña los dos como tres niveles de TC.
