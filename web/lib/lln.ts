// La obstrucción por el límite inferior de normalidad (LLN) y los paquetes-año dentro de la EPOC.
// No vienen en `cohorte.json`: son las cifras de `docs/cifras.md` ("Obstrucción por el límite inferior de normalidad"
// y "Paquetes-año") y de `docs/figuras/lln.json`. Si esos ficheros cambian, hay que cambiar esto a mano.

export const LLN = {
  /** El LLN del FEV1/FVC (GLI-2012) en esta cohorte: mediana, mínimo y máximo. */
  mediana: 0.7,
  rango: [0.68, 0.72] as [number, number],
  /** Sin obstrucción por el 0,70 y por debajo de su LLN. */
  sin_obstruccion_bajo_lln: 1,
  sin_obstruccion: 52,
  /** De ellos, entre los posibles pre-EPOC y entre los demás sin obstrucción; Fisher. */
  pre_epoc_bajo_lln: 1,
  pre_epoc: 14,
  otros_bajo_lln: 0,
  otros: 38,
  fisher_p: 0.27,
  /** Con EPOC por el 0,70 que el LLN no confirma. */
  epoc_no_confirmados: 0,
  epoc: 28,
  /** La puntuación frente al z del cociente, entre los sin obstrucción. */
  z_cociente: { rho: -0.33, p: 0.017 },
  /** El FEV1 en % del predicho que calculan las ecuaciones frente al de la tabla: diferencia mediana, en puntos. */
  diferencia_fev1_pct: 0.3,
} as const;

/** Paquetes-año frente a la puntuación: dentro de la EPOC, en crudo y descontando la edad y fumar ahora; dentro de los controles. */
export const PAQUETES_ANO = {
  epoc: { rho: -0.57, p: 0.002 },
  epoc_ajustado: { rho: -0.58, p: 0.002, n: 26 },
  controles: { rho: -0.24, p: 0.1 },
} as const;
