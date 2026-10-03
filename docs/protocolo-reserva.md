# Protocolo de la prueba en los sujetos de reserva

Escrito el 2 de octubre, antes de mirar la reserva. Lo que hay aquí no se cambia
después de ejecutar la prueba.

## Qué son

15 sujetos de los 77 con TC utilizable, apartados al azar (1 de cada 5,
estratificado por caso y control, semilla 2026) antes de elegir medidas. No han
entrado en el modelo normativo, en la elección de las dos medidas ni en el
umbral de daño. Nadie ha mirado sus puntuaciones.

## Qué se ha tocado ya de la reserva

- Sus TC se segmentaron y midieron con las demás, sin mirar los resultados.
- El 1 de octubre se comprobó que `scripts/predict.py` daba, para los sujetos de
  fuera de la referencia (los de reserva entre ellos), la misma puntuación que
  `scripts/score_cohort.py`. Fue una comparación de igualdad entre dos cálculos;
  no se miró ningún rendimiento. Ese comando imprimió el recuento de clases de
  los 86 sujetos juntos.
- Nada más. Ninguna decisión del modelo se tomó con ellos.

## Qué se prueba

El modelo congelado: `outputs/cohorte_v3/modelo.pkl` (sha256 `c14db8eeae6b8b86…`)
y `modelo.json` (`89275e2d65ed3fdb…`).

- Dos medidas: %LAA-950 suavizado (en logaritmo) y longitud del árbol bronquial.
- Lo esperado se ajustó con los 40 controles de desarrollo.
- Umbral de daño: 0,38, el punto de Youden frente a EPOC en desarrollo.

El 2 de octubre, antes de esta prueba y a raíz de una revisión independiente, se
corrigieron las medidas de vía aérea (longitudes de rama en milímetros, raíz del
árbol, suavizado en milímetros), se calibró la escala del z con residuos fuera
de muestra y el ajuste cruzado pasó a dejar un sujeto fuera cada vez. Todo con
los 62 de desarrollo.

No se ajusta nada con la reserva. `scripts/holdout.py` carga el modelo guardado,
comprueba que reproduce las puntuaciones y cuenta. Un sujeto sin puntuación se
informa y no entra en las cuentas.

## Qué se mide y qué esperamos

| Pregunta | Medida | Esperado | En desarrollo |
|---|---|---|---|
| ¿La TC sola separa a quien tiene obstrucción? | AUC de la puntuación para EPOC | 0,80 o más | 0,93 |
| ¿Sigue la limitación al flujo aéreo? | Spearman con FEV1/FVC | -0,5 o más fuerte | -0,73 |
| ¿Vale "lo esperado" para sujetos nuevos? | Mediana de la puntuación en los controles de reserva | Entre -0,5 y 0,5 | 0,0 |
| | Dispersión del z de cada medida en esos controles | Entre 0,6 y 1,6 | Cerca de 1, por construcción |
| ¿Viaja el umbral? | Controles de reserva por encima de 0,38 | Menos de la mitad | 11 de 40 |
| ¿Es estable entre reconstrucciones? | Acuerdo (ICC) entre los dos kernels | 0,90 o más | 0,98 |

También se informa, sin criterio:

- Sensibilidad y especificidad con el umbral de 0,38 y con el límite superior de
  normalidad de la referencia (1,29, que no usa la etiqueta de EPOC), con su
  intervalo exacto.
- El reparto en las tres clases.
- Si la TC añade a la clínica: dos modelos ajustados solo con desarrollo, uno
  con edad, sexo, talla y tabaco y otro con eso y las dos medidas, y la
  correlación de cada uno con el FEV1/FVC real de la reserva.

## Qué sería un fracaso

- AUC por debajo de 0,75, o
- la mediana de la puntuación de los controles de reserva fuera de -0,5 a 0,5:
  querría decir que "lo esperado" no sirve fuera de los sujetos con los que se
  ajustó.

Si pasa, se publica igual.

## Qué no se puede concluir con 15 sujetos

- El intervalo del AUC será ancho, de unas dos décimas a cada lado. Solo cabe
  decir si es compatible con el de desarrollo.
- La clase EPOC la pone la espirometría, no la TC. La reserva no puede "acertar
  la clase": lo que se contrasta es daño en la TC frente a obstrucción.
- No dice nada sobre si la pre-EPOC por TC es enfermedad. No hay etiqueta de
  pre-EPOC en ningún sitio.

## Después de la prueba

- El modelo no se toca en función del resultado. Si hubiera que cambiarlo, la
  reserva deja de ser una prueba y se dice.
- Los sujetos de reserva sirven para enseñar en la demo una inferencia sobre
  alguien que el modelo no vio.
- La validación cruzada sobre los 77 y el reajuste final con todos quedan para
  después de la entrega: reajustar antes quitaría los únicos sujetos no vistos.
