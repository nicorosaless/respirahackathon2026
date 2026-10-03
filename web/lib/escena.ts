// Los puntos de la cohorte son el hilo de la presentación: los mismos sujetos se colocan sobre el eje de la
// espirometría, se reordenan por su TC y se abren en dos dimensiones. Aquí está dónde va cada uno en cada paso.
// Todo se mide en las unidades del lienzo: 1600 × 900.

import { type Cohorte, personaDeEjemplo, type Sujeto } from "./cohorte";

export const LIENZO = { ancho: 1600, alto: 900 };
export const TINTA = "#16161a";
export const GRIS = "#cfcdc7";
export const GRIS_OSCURO = "#8e8e96";
export const DANO = "#f6821f";
export const PAPEL = "#fbfaf7";

/** El eje de la espirometría: el mismo en las diapositivas 1, 2, 5, 6 y 7. */
export const EJE_Y = 800;
const ENJAMBRE_Y = 640;
const RADIO = 11;
// Del 0,30 al 0,90: en la cohorte real el cociente más bajo es 0,34, y ninguno debe quedar pegado al borde.
const COCIENTE = { minimo: 0.3, maximo: 0.9, x0: 150, x1: 1450 };
/** La puntuación de daño, en vertical, en el gráfico de cuadrantes. */
// Hasta 5, que cubre la más alta de la cohorte real (4,9); desde -2,4 para dejar abajo sitio a los rótulos.
const PUNTUACION = { minimo: -2.4, maximo: 5, y0: EJE_Y - 30, y1: 300 };

const acotar = (valor: number, minimo: number, maximo: number) => Math.min(Math.max(valor, minimo), maximo);
const escala = (valor: number, d0: number, d1: number, r0: number, r1: number) => r0 + ((acotar(valor, Math.min(d0, d1), Math.max(d0, d1)) - d0) / (d1 - d0 || 1)) * (r1 - r0);

export const xCociente = (valor: number) => escala(valor, COCIENTE.minimo, COCIENTE.maximo, COCIENTE.x0, COCIENTE.x1);
/** El FEV1/FVC en la nube de dos dimensiones (diapositivas 6 y 7): más estrecha, para dejar sitio a la derecha. */
export const NUBE = { x0: 150, x1: 1090 };
export const xNube = (valor: number) => escala(valor, COCIENTE.minimo, COCIENTE.maximo, NUBE.x0, NUBE.x1);
export const yPuntuacion = (valor: number) => escala(valor, PUNTUACION.minimo, PUNTUACION.maximo, PUNTUACION.y0, PUNTUACION.y1);

/**
 * Coloca los puntos sin que se pisen, creciendo a los dos lados de la línea central.
 * Cuando muchos comparten valor, la columna no pasa de `alto`: el punto se corre un poco a un lado,
 * sin cruzar nunca la `frontera`.
 */
export function enjambre(xs: number[], radio: number, alto: number, frontera: number): { x: number; y: number }[] {
  const hueco = (2 * radio + 2) ** 2;
  const puestos: { x: number; y: number }[] = [];
  const salida = new Array<{ x: number; y: number }>(xs.length);
  const orden = xs.map((x, i) => ({ x, i })).sort((a, b) => a.x - b.x);
  const libre = (x: number, y: number) => !puestos.some((p) => (p.x - x) ** 2 + (p.y - y) ** 2 < hueco);
  for (const { x, i } of orden) {
    let sitio: { x: number; y: number } | null = null;
    for (let lado = 0; sitio === null; lado++) {
      const corrido = x + (lado % 2 ? -1 : 1) * Math.ceil(lado / 2) * radio;
      if (lado > 0 && corrido < frontera !== x < frontera) continue;
      for (let paso = 0; Math.ceil(paso / 2) * 3 <= alto; paso++) {
        const y = (paso % 2 ? -1 : 1) * Math.ceil(paso / 2) * 3;
        if (libre(corrido, y)) {
          sitio = { x: corrido, y };
          break;
        }
      }
    }
    puestos.push(sitio);
    salida[i] = sitio;
  }
  return salida;
}

type Sitio = { x: number; y: number } | null;

/** La franja de lo esperado en la diapositiva de la curva de crecimiento: la longitud del árbol frente a la talla. */
export interface Franja {
  x: (talla: number) => number;
  y: (milimetros: number) => number;
  tallas: [number, number];
  /** Lo esperado a cada talla y cuánto se apartan de ello quienes no tienen obstrucción. */
  centro: (talla: number) => number;
  ancho: number;
}

export interface Geometria {
  sujetos: Sujeto[];
  /** La persona de ejemplo de las cinco primeras diapositivas. */
  persona: Sujeto | undefined;
  cociente: Sitio[];
  ciego: Sitio[];
  cuadrantes: Sitio[];
  crecimiento: Sitio[];
  franja: Franja | null;
  /** Dónde cae la frontera entre los dos grupos del experimento ciego, sobre su eje. */
  xFronteraCiega: number | null;
  /** Los que están justo al otro lado de la línea: sin obstrucción y con el cociente por debajo de `CERCA`. */
  cerca: boolean[];
}

/** Hasta qué cociente se considera que alguien sin obstrucción está "justo al otro lado". */
export const CERCA = 0.75;

export function geometria(cohorte: Cohorte): Geometria {
  const { sujetos, umbral_cociente: umbral } = cohorte;
  const persona = personaDeEjemplo(cohorte);

  const conCociente = sujetos.map((s, i) => ({ i, valor: s.clinica.fev1_fvc })).filter((s): s is { i: number; valor: number } => s.valor !== null);
  const cociente: Sitio[] = sujetos.map(() => null);
  enjambre(conCociente.map((s) => xCociente(s.valor)), RADIO, 150, xCociente(umbral)).forEach((sitio, k) => {
    cociente[conCociente[k].i] = { x: sitio.x, y: ENJAMBRE_Y + sitio.y };
  });

  // El experimento ciego: los sujetos ordenados solo por su TC.
  const conCiego = sujetos.map((s, i) => ({ i, valor: s.ciego?.puntuacion ?? null })).filter((s): s is { i: number; valor: number } => s.valor !== null);
  const ciegas = conCiego.map((s) => s.valor);
  const [c0, c1] = [Math.min(...ciegas), Math.max(...ciegas)];
  const xCiego = (valor: number) => escala(valor, c0, c1, 230, 1370);
  const frontera = cohorte.umbral_natural?.dos_grupos_por_la_tc.umbral_de_puntuacion ?? null;
  const ciego: Sitio[] = sujetos.map(() => null);
  enjambre(conCiego.map((s) => xCiego(s.valor)), RADIO, 150, frontera === null ? -Infinity : xCiego(frontera)).forEach((sitio, k) => {
    ciego[conCiego[k].i] = { x: sitio.x, y: ENJAMBRE_Y + sitio.y };
  });

  // La nube de las diapositivas 6 y 7: cada sujeto por su espirometría y por la puntuación de su TC.
  const cuadrantes: Sitio[] = sujetos.map((s) => (s.clinica.fev1_fvc === null || s.puntuacion === null ? null : { x: xNube(s.clinica.fev1_fvc), y: yPuntuacion(s.puntuacion) }));

  // La curva de crecimiento: la longitud del árbol frente a la talla, con lo esperado como franja.
  const medidos = sujetos.flatMap((s) => (s.clinica.talla === null || s.valores.via_longitud_mm === null || s.esperado.via_longitud_mm === null ? [] : [{ talla: s.clinica.talla, valor: s.valores.via_longitud_mm, esperado: s.esperado.via_longitud_mm, caso: s.caso }]));
  const referencia = medidos.filter((m) => !m.caso);
  let franja: Franja | null = null;
  if (referencia.length >= 5) {
    const media = (valores: number[]) => valores.reduce((suma, v) => suma + v, 0) / valores.length;
    const [mt, me] = [media(referencia.map((m) => m.talla)), media(referencia.map((m) => m.esperado))];
    const pendiente = referencia.reduce((suma, m) => suma + (m.talla - mt) * (m.esperado - me), 0) / (referencia.reduce((suma, m) => suma + (m.talla - mt) ** 2, 0) || 1);
    const centro = (talla: number) => me + pendiente * (talla - mt);
    const residuos = referencia.map((m) => m.valor - m.esperado);
    const dispersion = Math.sqrt(media(residuos.map((r) => (r - media(residuos)) ** 2)));
    const tallas: [number, number] = [Math.min(...medidos.map((m) => m.talla)) - 3, Math.max(...medidos.map((m) => m.talla)) + 3];
    const valores = [...referencia.map((m) => m.valor), ...(persona?.valores.via_longitud_mm ? [persona.valores.via_longitud_mm] : [])];
    const [v0, v1] = [Math.min(...valores) - 250, Math.max(...valores) + 250];
    franja = { x: (talla) => escala(talla, tallas[0], tallas[1], 330, 1380), y: (mm) => escala(mm, v0, v1, EJE_Y - 20, 310), tallas, centro, ancho: 2 * dispersion };
  }
  const crecimiento: Sitio[] = sujetos.map((s) =>
    franja === null || s.clinica.talla === null || s.valores.via_longitud_mm === null ? null : { x: franja.x(s.clinica.talla), y: franja.y(s.valores.via_longitud_mm) },
  );

  return {
    sujetos,
    persona,
    cociente,
    ciego,
    cuadrantes,
    crecimiento,
    franja,
    xFronteraCiega: frontera === null ? null : xCiego(frontera),
    cerca: sujetos.map((s) => !s.caso && s.clinica.fev1_fvc !== null && s.clinica.fev1_fvc < CERCA),
  };
}

/** Las diapositivas en las que se ven los puntos. */
export type Cuadro = "soplar" | "frontera" | "crecimiento" | "ciego" | "nube" | "cuadrantes";

export interface Punto {
  id: string;
  x: number;
  y: number;
  radio: number;
  color: string;
  opacidad: number;
  /** Hueco: solo el contorno. Así se marcan los que el experimento ciego deja en el grupo que no les toca. */
  hueco: boolean;
  /** El anillo de la persona de ejemplo. */
  anillo: boolean;
}

/** Dónde espera la persona de ejemplo antes de que aparezca el eje, en la primera diapositiva. */
export const SITIO_DE_LA_PERSONA = { x: 330, y: 560 };

/** Cómo se ve cada sujeto en un cuadro y un paso. Fuera de los cuadros con puntos, todos se apagan donde estaban. */
export function puntos(g: Geometria, cuadro: Cuadro | null, clic: number): Punto[] {
  return g.sujetos.map((sujeto, i) => {
    const esLaPersona = sujeto.id === g.persona?.id;
    const oculto = (sitio: Sitio): Punto => ({ id: sujeto.id, x: sitio?.x ?? LIENZO.ancho / 2, y: sitio?.y ?? ENJAMBRE_Y, radio: RADIO, color: GRIS, opacidad: 0, hueco: false, anillo: false });
    const porObstruccion = sujeto.caso ? TINTA : GRIS;

    if (cuadro === "soplar") {
      const sitio = g.cociente[i];
      if (!sitio) return oculto(sitio);
      if (clic === 0) return esLaPersona ? { id: sujeto.id, ...SITIO_DE_LA_PERSONA, radio: 30, color: TINTA, opacidad: 1, hueco: false, anillo: false } : oculto(sitio);
      if (clic === 1) return esLaPersona ? { id: sujeto.id, ...sitio, radio: 15, color: TINTA, opacidad: 1, hueco: false, anillo: true } : oculto(sitio);
      return { id: sujeto.id, ...sitio, radio: RADIO, color: porObstruccion, opacidad: 1, hueco: false, anillo: esLaPersona };
    }
    if (cuadro === "frontera") {
      const sitio = g.cociente[i];
      if (!sitio) return oculto(sitio);
      return { id: sujeto.id, ...sitio, radio: RADIO, color: g.cerca[i] ? GRIS_OSCURO : porObstruccion, opacidad: g.cerca[i] ? 1 : 0.3, hueco: false, anillo: false };
    }
    if (cuadro === "crecimiento") {
      const sitio = g.crecimiento[i];
      if (!sitio) return oculto(g.cociente[i]);
      if (esLaPersona) return { id: sujeto.id, ...sitio, radio: 15, color: TINTA, opacidad: clic >= 1 ? 1 : 0, hueco: false, anillo: true };
      // La franja se aprende de quienes no tienen obstrucción: son los que se ven.
      return { id: sujeto.id, ...sitio, radio: 8, color: GRIS, opacidad: sujeto.caso ? 0 : 0.9, hueco: false, anillo: false };
    }
    if (cuadro === "ciego") {
      const grupo = sujeto.ciego?.grupo;
      const sitio = clic >= 2 ? (g.ciego[i] ? g.cociente[i] : null) : g.ciego[i];
      if (!sitio || !grupo) return oculto(g.cociente[i]);
      const color = clic === 0 ? GRIS_OSCURO : grupo === "alto" ? DANO : GRIS;
      // Al final, los que el reparto ciego deja en el grupo contrario a su espirometría se quedan en contorno.
      const falla = clic >= 3 && (grupo === "alto") !== sujeto.caso;
      return { id: sujeto.id, ...sitio, radio: RADIO, color: clic >= 3 && falla && grupo === "bajo" ? GRIS_OSCURO : color, opacidad: 1, hueco: falla, anillo: esLaPersona };
    }
    if (cuadro === "nube") {
      const sitio = g.cuadrantes[i];
      if (!sitio) return oculto(g.cociente[i]);
      return { id: sujeto.id, ...sitio, radio: RADIO, color: porObstruccion, opacidad: 1, hueco: false, anillo: false };
    }
    if (cuadro === "cuadrantes") {
      const sitio = g.cuadrantes[i];
      if (!sitio) return oculto(g.cociente[i]);
      const senalado = !sujeto.caso && sujeto.dano_tc;
      // Tercer paso: los que la línea de la TC deja del lado contrario a su espirometría se quedan en contorno.
      if (clic === 2) {
        const coincide = sujeto.caso === sujeto.dano_tc;
        return { id: sujeto.id, ...sitio, radio: RADIO, color: coincide ? porObstruccion : sujeto.caso ? TINTA : GRIS_OSCURO, opacidad: 1, hueco: !coincide, anillo: false };
      }
      if (clic >= 3) return { id: sujeto.id, ...sitio, radio: senalado ? 13 : RADIO, color: senalado ? DANO : porObstruccion, opacidad: senalado ? 1 : 0.4, hueco: false, anillo: false };
      return { id: sujeto.id, ...sitio, radio: RADIO, color: porObstruccion, opacidad: 1, hueco: false, anillo: false };
    }
    return oculto(g.cociente[i]);
  });
}
