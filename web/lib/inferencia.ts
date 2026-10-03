// Los textos y las cuentas de la prueba en sujetos de reserva: lo que la TC dice frente a lo que dice la espirometría.

import { type Cohorte, type NivelTC, nivelTC, type Reserva, type Sujeto, umbralNormalidad } from "./cohorte";
import { num } from "./formato";

/** "un hombre de 43 años, 182 cm, fumador". Lo que falte en la tabla clínica no se dice. */
export function describirPersona(clinica: Sujeto["clinica"]): string {
  const hombre = clinica.sexo === "H";
  const partes = [`${hombre ? "un hombre" : "una mujer"}${clinica.edad === null ? "" : ` de ${num(clinica.edad, 0)} años`}`];
  if (clinica.talla !== null) partes.push(`${num(clinica.talla, 0)} cm`);
  partes.push(clinica.fuma ? (hombre ? "fumador" : "fumadora") : hombre ? "exfumador" : "exfumadora");
  return partes.join(", ");
}

/** Por debajo de este porcentaje no hay enfisema medible: un cociente entre dos valores así (0,16 % y 0,04 %) engaña. */
export const ENFISEMA_MEDIBLE = 1;

/**
 * La distancia entre lo medido y lo esperado, en palabras.
 * El enfisema se compara en veces, como hace el modelo (en logaritmo), solo cuando los dos valores se pueden medir;
 * por debajo del 1 % se dice que no hay enfisema medible. El árbol, en metros.
 */
export function comparacion(medida: "laa950_smooth" | "via_longitud_mm", valor: number | null, esperado: number | null): string | null {
  if (valor === null || esperado === null || !Number.isFinite(esperado) || !Number.isFinite(valor)) return null;
  if (medida === "laa950_smooth") {
    if (!(esperado > 0)) return null;
    if (valor < ENFISEMA_MEDIBLE) return `sin enfisema medible (menos del ${num(ENFISEMA_MEDIBLE, 0)} %)`;
    // Lo esperado ya se ve al lado: un "40 veces" sobre un 0,05 % no dice nada más.
    if (esperado < ENFISEMA_MEDIBLE) return "por encima de lo esperado";
    const veces = valor / esperado;
    // "0,9 veces lo esperado" no se entiende: por debajo de lo esperado se dice así.
    if (veces >= 1.05) return `${num(veces, 1)} veces lo esperado`;
    return veces > 0.95 ? "como lo esperado" : "por debajo de lo esperado";
  }
  const diferencia = (valor - esperado) / 1000;
  return `${num(Math.abs(diferencia), 2)} m ${diferencia < 0 ? "menos" : "más"} de lo esperado`;
}

/**
 * Una desviación dicha con palabras y sin signo: "1,3" y "desviaciones menos árbol de lo esperado".
 * Las desviaciones llegan orientadas (más es peor): en el enfisema peor es más; en el árbol, menos.
 */
export function desviacionEnPalabras(medida: "enfisema" | "via", z: number | null): { cuanto: string; direccion: string } | null {
  if (z === null || !Number.isFinite(z)) return null;
  const cuanto = num(Math.abs(z), 1);
  if (cuanto === "0,0") return { cuanto, direccion: "desviaciones: como lo esperado" };
  const peor = z > 0;
  const direccion = medida === "enfisema" ? `${peor ? "más" : "menos"} enfisema` : `${peor ? "menos" : "más"} árbol`;
  return { cuanto, direccion: `desviaciones ${direccion} de lo esperado` };
}

export interface Contraste {
  danoConObstruccion: number;
  sinDanoConObstruccion: number;
  danoSinObstruccion: number;
  sinDanoSinObstruccion: number;
}

/** Daño en la TC frente a obstrucción en la espirometría, en los sujetos de reserva. */
export function tablaDeContraste(reserva: Reserva): Contraste {
  const { sensibilidad, especificidad } = reserva;
  return {
    danoConObstruccion: sensibilidad.aciertos,
    sinDanoConObstruccion: sensibilidad.de - sensibilidad.aciertos,
    danoSinObstruccion: especificidad.de - especificidad.aciertos,
    sinDanoSinObstruccion: especificidad.aciertos,
  };
}

export interface Veredicto {
  coincide: boolean;
  titulo: string;
  texto: string;
}

/**
 * Qué pasó al revelar la espirometría. La clase EPOC la pone la espirometría: aquí solo se contrasta si la TC se parece
 * a la de la EPOC. Superar el umbral no demuestra una lesión, así que no se dice "daño".
 */
export function veredicto(sujeto: Pick<Sujeto, "dano_tc" | "caso">): Veredicto {
  if (sujeto.dano_tc && sujeto.caso) return { coincide: true, titulo: "Coinciden", texto: "La TC se parece a la de la EPOC y la espirometría encuentra obstrucción." };
  if (!sujeto.dano_tc && !sujeto.caso) return { coincide: true, titulo: "Coinciden", texto: "La TC no se parece a la de la EPOC y la espirometría no encuentra obstrucción." };
  if (sujeto.dano_tc)
    return {
      coincide: false,
      titulo: "No coinciden",
      texto: "La TC se parece a la de la EPOC y la espirometría no encuentra obstrucción. La regla lo deja como posible pre-EPOC. No sabemos si la TC se adelanta o se equivoca.",
    };
  return { coincide: false, titulo: "No coinciden", texto: "Hay obstrucción y la puntuación de la TC queda por debajo del umbral: no lo detecta." };
}

export interface Criterio {
  pregunta: string;
  resultado: string;
  /** Lo que se escribió antes de mirar. `null` cuando se informa sin criterio. */
  esperado: string | null;
  cumple: boolean | null;
  /** Cumple, pero con un sujeto más habría fallado. */
  porPoco?: boolean;
}

/**
 * Las preguntas de la prueba en reserva, con su resultado y con lo que se fijó antes de mirar.
 * Los umbrales de cada criterio son los de `docs/protocolo-reserva.md`; si se cumplen lo dice `reserva.criterios`.
 */
export function criteriosDeReserva(reserva: Reserva): Criterio[] {
  const { criterios, separa_epoc: auc, fev1_fvc, sensibilidad, especificidad, calibracion_controles: calibracion, otra_reconstruccion: otra, anade_a_la_clinica: clinica } = reserva;
  const porEncima = especificidad.de - especificidad.aciertos;
  const filas: Criterio[] = [
    {
      pregunta: "Separa a quien tiene obstrucción",
      resultado: `AUC ${num(auc.auc, 2)} (IC del 95 %: ${num(auc.ic95[0], 2)} a ${num(auc.ic95[1], 2)})`,
      esperado: "0,80 o más",
      cumple: criterios?.separa_epoc ?? null,
    },
    { pregunta: "Sigue al FEV1/FVC", resultado: `Correlación de ${num(fev1_fvc.rho, 2)}`, esperado: "−0,5 o más fuerte", cumple: criterios?.sigue_el_cociente ?? null },
  ];
  if (calibracion)
    filas.push({
      pregunta: "Lo esperado vale para sujetos nuevos",
      resultado: `Mediana de los controles: ${num(calibracion.puntuacion.mediana, 2)}`,
      esperado: "entre −0,5 y 0,5",
      cumple: criterios?.controles_centrados ?? null,
    });
  filas.push({
    pregunta: "El umbral sirve en sujetos nuevos",
    resultado: `Por encima: ${sensibilidad.aciertos} de ${sensibilidad.de} EPOC, ${porEncima} de ${especificidad.de} controles`,
    esperado: "controles: menos de la mitad",
    cumple: criterios ? porEncima * 2 < especificidad.de : null,
    porPoco: porEncima * 2 < especificidad.de && (porEncima + 1) * 2 >= especificidad.de,
  });
  if (otra)
    filas.push({
      pregunta: "Estable entre los dos filtros del escáner",
      resultado: `Acuerdo ${num(otra.icc, 2)}; misma decisión en ${otra.misma_decision_de_dano.aciertos} de ${otra.misma_decision_de_dano.de}`,
      esperado: "0,90 o más",
      cumple: criterios?.estable_entre_reconstrucciones ?? null,
    });
  if (clinica && clinica.length >= 2)
    filas.push({
      pregunta: "Añade a la clínica",
      resultado: `Clínica sola ${num(clinica[0].rho, 2)}; con la TC ${num(clinica[clinica.length - 1].rho, 2)}`,
      esperado: null,
      cumple: null,
    });
  return filas;
}

/** Lo que el recorrido de un sujeto enseña: sus medidas, su puntuación y los umbrales, todo del mismo modelo. */
export interface Lectura {
  /** Del modelo que se probó en reserva, ajustado sin este sujeto. Si no, del modelo final, que sí lo usó. */
  delModeloProbado: boolean;
  puntuacion: number | null;
  dano_tc: boolean;
  cerca_umbral: boolean;
  nivel: NivelTC | null;
  z: Sujeto["z"];
  valores: Sujeto["valores"];
  esperado: Sujeto["esperado"];
  umbral: number;
  normalidad: number | null;
  /** Con cuántos sujetos se ajustó ese modelo. */
  sujetosDeAjuste: number;
}

/** De qué modelo son los umbrales de una lectura. Los dos juegos (0,38 y 1,29 frente a 0,48 y 1,23) no se pueden confundir. */
export function nombreDelModelo(lectura: Pick<Lectura, "delModeloProbado" | "sujetosDeAjuste">): string {
  return lectura.delModeloProbado ? `Umbrales del modelo congelado, probado en la reserva (${lectura.sujetosDeAjuste} sujetos)` : `Umbrales del modelo final, ${lectura.sujetosDeAjuste} sujetos`;
}

/** La lectura de un sujeto con el modelo final, ajustado con todos: la que se enseña en Cohorte y en los ejemplos de cada clase. */
export function lecturaDelModeloFinal(sujeto: Sujeto, cohorte: Cohorte): Lectura {
  return {
    delModeloProbado: false,
    puntuacion: sujeto.puntuacion,
    dano_tc: sujeto.dano_tc,
    cerca_umbral: sujeto.cerca_umbral,
    nivel: nivelTC(sujeto, cohorte),
    z: sujeto.z,
    valores: sujeto.valores,
    esperado: sujeto.esperado,
    umbral: cohorte.umbral_dano,
    normalidad: umbralNormalidad(cohorte),
    sujetosDeAjuste: cohorte.comprobaciones.sujetos,
  };
}

/**
 * La lectura de un sujeto que el modelo probado no vio: la de ese modelo, con sus umbrales. Así el recorrido y la tabla
 * de la prueba hablan del mismo modelo. Si la exportación no la trae, se cae a la del modelo final y `delModeloProbado` lo dice.
 */
export function lecturaDeInferencia(sujeto: Sujeto, cohorte: Cohorte): Lectura {
  const [suya, modelo] = [sujeto.congelado, cohorte.congelado];
  if (!suya || !modelo) return lecturaDelModeloFinal(sujeto, cohorte);
  return {
    delModeloProbado: true,
    puntuacion: suya.puntuacion,
    dano_tc: suya.dano_tc,
    cerca_umbral: suya.cerca_umbral,
    nivel: suya.nivel_tc ?? nivelTC({ puntuacion: suya.puntuacion }, { umbral_dano: modelo.umbral_dano, umbral_normalidad: modelo.umbral_normalidad, comprobaciones: cohorte.comprobaciones }),
    z: suya.z,
    valores: suya.valores,
    esperado: suya.esperado,
    umbral: modelo.umbral_dano,
    normalidad: modelo.umbral_normalidad,
    sujetosDeAjuste: modelo.sujetos_de_ajuste,
  };
}
