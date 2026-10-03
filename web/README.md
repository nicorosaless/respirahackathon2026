# MAPS web: diapositivas y aplicación

Las diapositivas y la aplicación en una sola pestaña. Diez diapositivas en 16:9
que se construyen por pasos; antes de las conclusiones se abre la aplicación
(Inferencia, persona a persona) y desde ella se vuelve a las conclusiones.
Detrás hay un anexo con las preguntas del jurado y una diapositiva por respuesta.

Publicada en <https://nicorosaless.github.io/maps/>.

Los sujetos son simulados sobre cuatro TC públicas de LIDC-IDRI. Las cifras son
las reales: los agregados de `docs/figuras/`, que resume `docs/cifras.md`.

## Arrancar

```bash
pnpm install
pnpm dev                                   # http://localhost:3000
pnpm test
pnpm build                                 # sitio estático en out/
NEXT_PUBLIC_BASE_PATH=/maps pnpm build     # para servirlo en /maps/
```

`out/` no necesita Node: lo sirve cualquier servidor de ficheros. Con la flecha
derecha se avanza; `?d=<n>` abre la diapositiva n.

## El recorrido

| # | Parte | Lo que se ve |
|---|---|---|
| 1.1 | Problema | Una espirometría, el índice de Tiffeneau y la línea de 0,70 |
| 1.2 | Problema (opcional) | Los que quedan justo al otro lado de la línea |
| 2.1 | La idea | La TC: lóbulos, árbol bronquial y las dos medidas, con por qué esas dos |
| 2.2 | La idea | El modelo: lo esperado, el z, la puntuación y el umbral |
| 2.3 | La idea | La regla de la TC frente al índice de 0,70, con sus errores |
| 3.1 | Hallazgos | La correlación con el FEV1/FVC |
| 3.2 | Hallazgos | Los cuatro cuadrantes y los 14 posibles pre-EPOC |
| 4.1 | Cómo está hecho | La curva ROC y las matrices de confusión, con el umbral de cribado |
| 4.2 | Cómo está hecho | Frente a las alternativas: AUC y EPOC que se escapan |
| | Aplicación | Inferencia, persona a persona |
| 6.1 | Conclusiones | Lo que encontramos y la pregunta del tabaco |

Reglas de las diapositivas: una frase corta, como mucho una cifra grande,
ninguna tabla. Las cifras de respaldo están en la aplicación y en el anexo.

**Los puntos son el hilo.** Los mismos 80 puntos aparecen sobre el eje de la
espirometría, se reordenan por su TC, vuelven al eje y se abren en dos
dimensiones. Los dibuja una sola capa (`components/deck/Puntos.tsx`), y dónde va
cada uno en cada paso está en `lib/escena.ts`.

| Tecla | Qué hace |
|---|---|
| `→`, espacio o clic | Avanza un paso. Tras la 4.2 abre la aplicación |
| `←` | Retrocede |
| `S` | Salta lo que queda de esta diapositiva y las opcionales |
| `A` | Abre el índice del anexo; en el índice, vuelve a donde se estaba |
| `T` | Enseña el cronómetro |
| `F` | Pantalla completa |

## La aplicación

`/plataforma/` es Inferencia, persona a persona. Tres personas de la cohorte,
una de cada clase, y una que el modelo no vio. A la izquierda, la TC (lóbulos y
enfisema, o el árbol bronquial dibujándose) y dónde cae la persona entre los 80.
A la derecha, paso a paso con `→`: la persona, sus dos medidas frente a lo
esperado, por qué sale esa puntuación, si su TC queda por encima o por debajo
del umbral y qué dice su espirometría. Arriba, un botón lleva a las conclusiones.

## Las palabras

Siguen `docs/cifras.md`:

- "Puntuación de daño" es el nombre. Lo que supera el umbral es una "TC
  alterada", no un daño demostrado. El naranja marca eso y nada más.
- La clase intermedia se escribe "posible pre-EPOC": sin obstrucción y con la TC
  alterada.
