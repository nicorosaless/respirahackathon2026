"use client";

// El único fichero que lee la app: `public/data/cohorte.json`.
// Lo escribe `scripts/make_fixture.py` con sujetos simulados; la cohorte real saldrá con esta misma forma.

import { useEffect, useState } from "react";
import { publica } from "./ruta";

export type Clase = "control" | "pre-EPOC" | "EPOC";
export const CLASES: Clase[] = ["control", "pre-EPOC", "EPOC"];
/** Cómo se nombra cada clase. La intermedia es una definición operativa nuestra: sin obstrucción y con la TC parecida a la de la EPOC. */
export const NOMBRE_CLASE: Record<Clase, string> = { control: "control", "pre-EPOC": "posible pre-EPOC", EPOC: "EPOC" };
export type Lobulo = "LSD" | "LM" | "LID" | "LSI" | "LII";
export const LOBULOS: Lobulo[] = ["LSD", "LM", "LID", "LSI", "LII"];
export const NOMBRE_LOBULO: Record<Lobulo, string> = {
  LSD: "Superior derecho",
  LM: "Medio",
  LID: "Inferior derecho",
  LSI: "Superior izquierdo",
  LII: "Inferior izquierdo",
};
/** Número con el que el mapa de lóbulos marca cada píxel. */
export const ETIQUETA_LOBULO: Record<number, Lobulo> = { 1: "LSI", 2: "LII", 3: "LSD", 4: "LM", 5: "LID" };

export type Particion = "desarrollo" | "reserva";
/** Dónde cae la puntuación: por debajo del umbral, entre el umbral y el límite de normalidad, o por encima de este. */
export type NivelTC = "esperada" | "intermedia" | "alta";
export const NOMBRE_NIVEL: Record<NivelTC, string> = { esperada: "como la referencia", intermedia: "intermedia", alta: "por encima de lo normal" };

/** Una medida de las que nombra el reto y que no entra en la puntuación. */
export interface MedidaTradicional {
  medida: string;
  nombre: string;
  unidad: string;
  valor: number | null;
  /** Desviación respecto a lo esperado, orientada: más es peor. */
  z: number | null;
}

/** Lo que dijo de un sujeto de reserva el modelo ajustado sin él: el que se probó una vez en la reserva. */
export interface LecturaCongelada {
  puntuacion: number | null;
  dano_tc: boolean;
  clase: Clase;
  motivo: string;
  cerca_umbral: boolean;
  nivel_tc: NivelTC | null;
  z: { enfisema: number | null; via: number | null };
  valores: { laa950_smooth: number | null; via_longitud_mm: number | null };
  esperado: { laa950_smooth: number | null; via_longitud_mm: number | null };
}

/** Los umbrales de aquel modelo y con cuántos sujetos se ajustó. */
export interface ModeloCongelado {
  umbral_dano: number;
  umbral_normalidad: number | null;
  zona_gris: number;
  sujetos_de_ajuste: number;
}

export interface Sujeto {
  id: string;
  /** "reserva": uno de los sujetos apartados para la primera prueba. El modelo final se ajusta también con ellos. */
  particion: Particion;
  clase: Clase;
  motivo: string;
  /** Obstrucción en la espirometría: FEV1/FVC por debajo de 0,70. */
  caso: boolean;
  /** Puntuación en el umbral de daño o por encima. */
  dano_tc: boolean;
  /** La puntuación queda a menos de `zona_gris` del umbral. */
  cerca_umbral: boolean;
  /** `null` si no se pudo medir la TC. */
  puntuacion: number | null;
  /** La puntuación con un modelo que no vio a este sujeto en ningún paso (validación cruzada anidada). */
  fuera_de_muestra?: number | null;
  nivel_tc?: NivelTC | null;
  /** Desviaciones respecto a lo esperado, orientadas: más es peor. */
  z: { enfisema: number | null; via: number | null };
  valores: { laa950_smooth: number | null; via_longitud_mm: number | null };
  /** Lo que se espera en una persona de su edad, sexo, talla y tabaco, en las mismas unidades que `valores`. */
  esperado: { laa950_smooth: number | null; via_longitud_mm: number | null };
  tradicionales: MedidaTradicional[];
  /** Desviación del enfisema en cada lóbulo. */
  lobulos: Record<Lobulo, number>;
  /** La misma TC con el kernel estándar y con el duro. */
  kernels: { laa950: [number | null, number | null]; puntuacion: [number | null, number | null] };
  /** Cualquier número puede faltar en la tabla clínica. */
  clinica: {
    edad: number | null;
    sexo: "H" | "M";
    talla: number | null;
    fuma: boolean;
    paquetes_ano: number | null;
    fev1_fvc: number | null;
    fev1_pct: number | null;
    dlco_pct: number | null;
    cat: number | null;
    kvp: number | null;
  };
  /** Solo en los sujetos de reserva: la lectura del modelo que no los vio. `null` en los demás. */
  congelado?: LecturaCongelada | null;
  /** El experimento ciego: la puntuación con lo esperado ajustado sin saber quién es caso, y el grupo en que cae sin usar la espirometría para cortar. */
  ciego?: { puntuacion: number | null; grupo: "alto" | "bajo" } | null;
  imagen: string | null;
  /** Existe `/data/previews/<imagen>-arbol.png`: la máscara del árbol bronquial, del tamaño de los cortes. */
  arbol: boolean;
}

export interface Imagen {
  ancho: number;
  alto: number;
  cortes: { centros: Partial<Record<Lobulo, [number, number]>> }[];
}

export interface Auc {
  auc: number;
  ic95: [number, number];
  n: number;
  casos: number;
}

export interface Correlacion {
  rho: number;
  p: number;
  n: number;
}

/** Cuántos aciertos de cuántos. `valor` falta cuando no hay ninguno que contar. */
export interface Fraccion {
  aciertos: number;
  de: number;
  valor: number | null;
  ic95?: [number, number];
}

/** Lo que se escribió antes de mirar la reserva (`docs/protocolo-reserva.md`) y si se cumplió. */
export interface CriteriosReserva {
  separa_epoc: boolean;
  sigue_el_cociente: boolean;
  controles_centrados: boolean;
  controles_con_dispersion_normal: boolean;
  fracaso: boolean;
  estable_entre_reconstrucciones?: boolean;
}

/** La prueba en los sujetos de reserva, con el modelo ya cerrado. */
export interface Reserva {
  cuando: string;
  sujetos: number;
  epoc: number;
  separa_epoc: Auc;
  fev1_fvc: Correlacion;
  sensibilidad: Fraccion;
  especificidad: Fraccion;
  clases: Record<Clase, number>;
  otra_reconstruccion?: { icc: number; separa_epoc: Auc; misma_decision_de_dano: Fraccion };
  /** Sujetos de reserva a los que no se pudo puntuar. No entran en las cuentas. */
  sin_puntuacion?: number;
  /** La puntuación de los controles de reserva: si "lo esperado" vale para sujetos nuevos, su mediana queda cerca de 0. */
  calibracion_controles?: { n: number; puntuacion: { mediana: number; dispersion: number } };
  /** Lo mismo con el límite superior de normalidad de la referencia, que no usa la etiqueta de EPOC. */
  limite_de_normalidad?: { umbral: number; sensibilidad: Fraccion; especificidad: Fraccion };
  /** Correlación con el FEV1/FVC real de la reserva de dos modelos ajustados solo con desarrollo. */
  anade_a_la_clinica?: { hasta: string; rho: number; p: number; n: number }[];
  criterios?: CriteriosReserva;
}

/** Una fila de la validación cruzada anidada: una medida de vía aérea junto al enfisema, con una referencia. */
export interface FilaValidacion {
  medida: string;
  referencia: string;
  /** Correlación con el FEV1/FVC de las puntuaciones fuera de muestra, con su intervalo. */
  rho_media: number;
  rho_ic95: [number, number];
  rho_p: number;
  /** La misma, solo entre los que no tienen obstrucción. */
  rho_controles_media: number;
  rho_controles_ic95: [number, number];
  rho_controles_p: number;
  auc: number;
  icc: number;
  /** Con el umbral de "TC parecida a la de la EPOC": EPOC por encima y controles por debajo. */
  sensibilidad_youden: number;
  especificidad_youden: number;
  /** Lo mismo con el límite superior de normalidad. */
  sensibilidad_normalidad: number;
  especificidad_normalidad: number;
  /** Cuánto mejora la correlación respecto al modelo. Falta en la fila del propio modelo. */
  mejora_rho?: number;
  mejora_rho_ic95?: [number, number];
}

/** La diferencia entre las correlaciones con el FEV1/FVC de dos puntuaciones, con su intervalo. */
export interface Comparacion {
  primera: string;
  segunda: string;
  todos: { diferencia: number; ic95: [number, number] };
  controles: { diferencia: number; ic95: [number, number] };
}

/** La validación del modelo final con todos los sujetos: cada uno se puntúa con un modelo que no lo vio. */
export interface Validacion {
  sujetos: number;
  epoc: number;
  controles: number;
  recuperados_de_la_otra_reconstruccion?: number;
  vueltas: number;
  repeticiones: number;
  resultados: FilaValidacion[];
  comparaciones?: Comparacion[];
  /** Cuántas vueltas ganó cada combinación de medida y referencia cuando se elige en cada vuelta. */
  elegido_en_cada_vuelta?: Record<string, number>;
}

/** La relación de la puntuación con una variable de la tabla, dentro de un grupo. `q` es la p corregida por las comparaciones hechas. */
export interface FilaExploratoria {
  variable: string;
  rho: number;
  p: number;
  q: number;
  n: number;
}

/** El experimento ciego en agregados (`docs/figuras/umbral_natural.json`). */
export interface UmbralNatural {
  sujetos: number;
  /** Cuántos sujetos quedan en el grupo que les corresponde por su espirometría, como texto: "64 de 80". */
  coinciden_con_la_obstruccion: string;
  dos_grupos_por_la_tc: {
    umbral_de_puntuacion: number;
    por_encima: number;
    por_debajo: number;
    con_obstruccion_por_encima: string;
    sin_obstruccion_por_debajo: string;
    fev1_fvc_mediana_por_encima?: number;
    fev1_fvc_mediana_por_debajo?: number;
  };
  fev1_fvc?: { rho: number; p: number };
  /** La misma relación, solo entre quienes no tienen obstrucción. */
  fev1_fvc_sin_obstruccion?: { rho: number; p: number; n?: number };
}

/** Un modelo de la comparación de complejidad (`docs/figuras/complejidad.json`), validado fuera de muestra. */
export interface ModeloDeComplejidad {
  /** "1 medida", "2 medidas"…, "logística con todas las medidas de TC", "clínica sola"… */
  modelo: string;
  auc: number;
  auc_dt?: number;
  rho_fev1_fvc: number;
  rho_sin_obstruccion?: number;
  /** Acuerdo entre los dos filtros del escáner. `null` en los modelos sin TC. */
  icc: number | null;
  medidas: string[] | null;
}

/** Si la puntuación anuncia una caída acelerada del FEV1 entre visitas. */
export interface CaidaDelFev1 {
  con_seguimiento: number;
  caida_acelerada: number;
  auc: number;
  p_mann_whitney: number;
  rho_con_la_caida?: number;
}

/** Menos es más: añadir medidas, aprender pesos o sumar la clínica, todo fuera de muestra. */
export interface Complejidad {
  sujetos: number;
  repeticiones: number;
  modelos: ModeloDeComplejidad[];
  /** Por definición ("30 mL al año, sin obstrucción"…). */
  caida_acelerada_del_fev1?: Record<string, CaidaDelFev1>;
}

/** Una medida a su paso por el embudo (`docs/figuras/embudo.json`). */
export interface PasoDelEmbudo {
  medida: string;
  nombre: string;
  /** Acuerdo entre los dos filtros del escáner. */
  icc: number;
  /** Relación con el FEV1/FVC, su p y su q (corregida por las 27 medidas). */
  rho: number;
  p: number;
  q: number;
  /** La relación con el FEV1/FVC descontando las medidas ya elegidas. Solo en las que pasan los dos primeros filtros. */
  rho_descontando?: number;
  p_descontando?: number;
  parecido_a_las_elegidas?: number;
  resultado: string;
}

/** Cómo se eligieron las dos medidas: tres filtros por orden. */
export interface Embudo {
  criterios: { acuerdo_minimo: number; q_maximo: number; p_descontando_maximo: number };
  medidas: number;
  estables: number;
  estables_y_asociadas: number;
  elegidas: string[];
  pasos: PasoDelEmbudo[];
}

/** Por dónde sale una medida del embudo, o si se queda. */
export type SalidaDelEmbudo = "inestable" | "sin asociación" | "redundante" | "dentro";

/** Un sujeto elegido para la demo, con otros que también valdrían. */
export interface Eleccion {
  elegido: string | null;
  alternativas: string[];
  candidatos: number;
}

/** Los sujetos que se enseñan en la demo: uno típico de cada clase y uno que el modelo probado no vio. */
export interface Ejemplos {
  criterio: string;
  clases: Record<Clase, Eleccion>;
  inferencia: Eleccion & { criterio: string };
}

/** El análisis exploratorio de la puntuación dentro de cada grupo (`docs/figuras/discordantes.json`). */
export interface Discordantes {
  dentro_de_los_casos: { puntuacion: FilaExploratoria[] };
  dentro_de_los_controles: { puntuacion: FilaExploratoria[] };
}

export interface MedidaCohorte {
  medida: string;
  nombre: string;
  en_la_puntuacion: boolean;
  auc_epoc: number;
  icc_kernel: number;
  fev1_fvc_post_v1: Correlacion & { q: number };
}

export interface Panel {
  panel: string;
  auc_epoc: number;
  rho_fev1_fvc: number;
  icc_kernel: number;
}

export interface Cohorte {
  /** Texto del aviso cuando los sujetos no son reales. `null` con la cohorte del reto. */
  aviso: string | null;
  umbral_dano: number;
  /** Límite superior de normalidad de la referencia: por encima, la TC está "por encima de lo normal". */
  umbral_normalidad?: number | null;
  umbral_cociente: number;
  /** Anchura alrededor del umbral en la que se avisa "cerca del umbral". */
  zona_gris: number;
  sujetos: Sujeto[];
  imagenes: Record<string, Imagen>;
  /** El modelo que se probó en reserva, ajustado sin esos sujetos. `null` si la exportación no lo trae. */
  congelado?: ModeloCongelado | null;
  comprobaciones: {
    sujetos: number;
    controles: number;
    epoc: number;
    /** Sujetos cuya serie estándar estaba incompleta y entran con la serie del otro filtro del escáner. */
    recuperados_de_la_otra_reconstruccion?: number;
    asociaciones: { variable: string; todos: Correlacion; controles: Correlacion; epoc: Correlacion }[];
    separa_epoc: Auc;
    por_estrato: (Auc & { variable: string; nivel: string })[];
    cada_medida_sola: (Auc & { medida: string })[];
    controles_negativos: { sexo_auc: number; fuma_auc: number; kvp_kruskal_p: number; imc: Correlacion; imc_todos: Correlacion };
    otra_reconstruccion: { icc: number; separa_epoc: Auc; fev1_fvc: Correlacion; icc_controles?: number };
    zona_gris?: number;
    /** La relación de la puntuación con el FEV1/FVC descontando una variable de la imagen o del cuerpo. */
    descontando?: { variable: string; todos: Correlacion; controles: Correlacion }[];
    limite_de_normalidad?: { umbral: number; controles_por_encima: number; sensibilidad: number; especificidad: number };
    estabilidad_del_umbral?: { umbral: [number, number]; controles_marcados: [number, number] };
    calidad_de_imagen?: { variable: string; puntuacion: Correlacion; puntuacion_en_controles: Correlacion }[];
    /** Mediana del porcentaje de enfisema en cada grupo, clásico y suavizado. */
    enfisema_medido?: Record<"controles" | "epoc", { laa950: number; laa950_smooth: number }>;
    paneles: Panel[];
    por_medida: MedidaCohorte[];
    controles_por_dano: {
      con_dano: number;
      sin_dano: number;
      visita_1: { variable: string; con_dano: number; sin_dano: number; p: number }[];
      seguimiento: { variable: string; con_dano: number; n_con: number; sin_dano: number; n_sin: number; p: number }[];
      cerca_de_la_obstruccion?: { criterio: string; con_dano: number; sin_dano: number };
    };
    por_clase: Record<Clase, { n: number; p50: number }>;
    /** `por_fev1` es de la regla anterior, que incluía el PRISm: no se enseña. */
    pre_epoc: { n: number; por_tc: number; por_fev1?: number };
  };
  escalera: {
    objetivo: string;
    metrica_nombre: string;
    escalera: { escalon: string; metrica: number; incremento: number | null; incremento_ic95_inf: number | null; incremento_ic95_sup: number | null; p_permutacion: number }[];
  };
  /** La primera prueba: el modelo ajustado sin los sujetos de reserva. `null` si no se hizo. */
  reserva: Reserva | null;
  /** La validación del modelo final con todos los sujetos. `null` si no se ha hecho. */
  validacion?: Validacion | null;
  /** Con qué va la puntuación dentro de la EPOC y dentro de los que no tienen obstrucción. Exploratorio. */
  discordantes?: Discordantes | null;
  umbral_natural?: UmbralNatural | null;
  complejidad?: Complejidad | null;
  embudo?: Embudo | null;
  ejemplos?: Ejemplos | null;
  conexion: {
    rasgo: string;
    covariables: string[];
    filas: { exposicion: string; coeficiente: number; p: number; n: number }[];
  };
}

let peticion: Promise<Cohorte> | null = null;

export function cargarCohorte(): Promise<Cohorte> {
  peticion ??= fetch(publica("/data/cohorte.json")).then(async (respuesta) => {
    if (!respuesta.ok) throw new Error(`No se pudo leer /data/cohorte.json (${respuesta.status}).`);
    const datos = (await respuesta.json()) as Cohorte;
    if (!Array.isArray(datos.sujetos) || datos.sujetos.length === 0) throw new Error("cohorte.json no trae sujetos.");
    return datos;
  });
  return peticion;
}

export function useCohorte(): { cohorte: Cohorte | null; error: string | null } {
  const [estado, setEstado] = useState<{ cohorte: Cohorte | null; error: string | null }>({ cohorte: null, error: null });
  useEffect(() => {
    let vivo = true;
    cargarCohorte().then(
      (cohorte) => vivo && setEstado({ cohorte, error: null }),
      (fallo: Error) => vivo && setEstado({ cohorte: null, error: fallo.message }),
    );
    return () => {
      vivo = false;
    };
  }, []);
  return estado;
}

export type SujetoPuntuado = Sujeto & { puntuacion: number };

/** Los sujetos con puntuación: los que se pueden dibujar, ordenar y cruzar. */
export function conPuntuacion(cohorte: Cohorte): SujetoPuntuado[] {
  return cohorte.sujetos.filter((s): s is SujetoPuntuado => s.puntuacion !== null && Number.isFinite(s.puntuacion));
}

/** Los sujetos apartados para la primera prueba: el modelo de entonces no los vio. */
export function deReserva(cohorte: Cohorte): Sujeto[] {
  return cohorte.sujetos.filter((s) => s.particion === "reserva");
}

/** El límite superior de normalidad, venga en la cohorte o en las comprobaciones. */
export function umbralNormalidad(cohorte: Cohorte): number | null {
  return cohorte.umbral_normalidad ?? cohorte.comprobaciones.limite_de_normalidad?.umbral ?? null;
}

/** El nivel de la TC de un sujeto. Si la exportación no lo trae, sale de su puntuación y de los dos umbrales. */
export function nivelTC(sujeto: Pick<Sujeto, "puntuacion" | "nivel_tc">, cohorte: Pick<Cohorte, "umbral_dano" | "umbral_normalidad" | "comprobaciones">): NivelTC | null {
  if (sujeto.nivel_tc) return sujeto.nivel_tc;
  if (sujeto.puntuacion === null) return null;
  const normalidad = cohorte.umbral_normalidad ?? cohorte.comprobaciones.limite_de_normalidad?.umbral ?? null;
  if (normalidad !== null && sujeto.puntuacion >= normalidad) return "alta";
  return sujeto.puntuacion >= cohorte.umbral_dano ? "intermedia" : "esperada";
}

const MEDIDA_DEL_MODELO = "via_longitud_mm";
const REFERENCIA_DEL_MODELO = "todos los controles";

/** Una fila de la validación con la referencia del modelo: todos los controles. */
export function filaDeValidacion(cohorte: Cohorte, medidaDeVia: string): FilaValidacion | undefined {
  return cohorte.validacion?.resultados.find((fila) => fila.medida === medidaDeVia && fila.referencia === REFERENCIA_DEL_MODELO);
}

/** Las vías de menos de 3 mm frente a las de 3 mm o más, cada una sola: la diferencia entre sus correlaciones con el FEV1/FVC. */
export function comparacionDeVias(cohorte: Cohorte): Comparacion | undefined {
  return cohorte.validacion?.comparaciones?.find((c) => c.primera === "solo vía fina" && c.segunda === "solo vía gruesa");
}

/** El modelo final, validado fuera de muestra: de aquí salen las cifras principales. */
export function validacionDelModelo(cohorte: Cohorte): FilaValidacion | undefined {
  return filaDeValidacion(cohorte, MEDIDA_DEL_MODELO);
}

/**
 * La correlación de la puntuación con el FEV1/FVC que se enseña como resultado principal.
 * Fuera de muestra si hay validación; si no, la de la cohorte con el modelo ajustado.
 */
export function correlacionPrincipal(cohorte: Cohorte): { rho: number; n: number; p: number; ic95: [number, number] | null; fueraDeMuestra: boolean } | undefined {
  const validada = validacionDelModelo(cohorte);
  if (validada && cohorte.validacion) return { rho: validada.rho_media, n: cohorte.validacion.sujetos, p: validada.rho_p, ic95: validada.rho_ic95, fueraDeMuestra: true };
  const ajustada = correlacionCociente(cohorte);
  return ajustada && { ...ajustada, ic95: null, fueraDeMuestra: false };
}

export function medida(cohorte: Cohorte, clave: string): MedidaCohorte | undefined {
  return cohorte.comprobaciones.por_medida.find((m) => m.medida === clave);
}

/** El acuerdo entre los dos filtros del escáner del %LAA-950 clásico, el número que usa todo el mundo. */
export function acuerdoClasico(cohorte: Cohorte): number {
  return medida(cohorte, "laa950")?.icc_kernel ?? NaN;
}

/** La correlación de la puntuación con el FEV1/FVC en la cohorte, con el modelo ajustado con esos mismos sujetos. */
export function correlacionCociente(cohorte: Cohorte): Correlacion | undefined {
  return cohorte.comprobaciones.asociaciones.find((a) => a.variable === "FEV1/FVC")?.todos;
}

/** La relación de la puntuación con una variable dentro de un grupo, buscada por el principio de su nombre. */
export function lectura(cohorte: Cohorte, grupo: "casos" | "controles", variable: string): FilaExploratoria | undefined {
  const filas = grupo === "casos" ? cohorte.discordantes?.dentro_de_los_casos.puntuacion : cohorte.discordantes?.dentro_de_los_controles.puntuacion;
  return filas?.find((fila) => fila.variable.startsWith(variable));
}

/** La fila del paso Connect que cruza el biomarcador con la puntuación de daño. */
export function conexionConPuntuacion(cohorte: Cohorte): Cohorte["conexion"]["filas"][number] | undefined {
  const { filas } = cohorte.conexion;
  return filas.find((f) => /puntuaci[oó]n/i.test(f.exposicion)) ?? filas[0];
}

/** El caso con el que se abre la vista de sujeto: sin obstrucción, con el FEV1 conservado y con daño en la TC. */
export function casoDeEntrada(cohorte: Cohorte): Sujeto {
  const sujetos = conPuntuacion(cohorte);
  const candidatos = sujetos.filter((s) => s.clase === "pre-EPOC" && s.puntuacion >= cohorte.umbral_dano);
  // Entre los candidatos se prefiere uno con el árbol bronquial segmentado, para poder enseñarlo.
  const orden = [...candidatos].sort((a, b) => Number(b.arbol) - Number(a.arbol) || b.puntuacion - a.puntuacion);
  return orden[0] ?? sujetos[0] ?? cohorte.sujetos[0];
}

const mediana = (valores: number[]): number => {
  const orden = [...valores].sort((a, b) => a - b);
  const mitad = Math.floor(orden.length / 2);
  return orden.length === 0 ? NaN : orden.length % 2 ? orden[mitad] : (orden[mitad - 1] + orden[mitad]) / 2;
};

/**
 * Los sujetos que se pueden enseñar como ejemplo de una clase: el elegido primero y después sus alternativas.
 * Si la cohorte no trae `ejemplos`, los más cercanos a la mediana de puntuación de su clase, con preferencia
 * por los que tienen imagen y árbol y no están cerca del umbral.
 */
export function ejemplosDeClase(cohorte: Cohorte, clase: Clase): SujetoPuntuado[] {
  const deLaClase = conPuntuacion(cohorte).filter((s) => s.clase === clase);
  const eleccion = cohorte.ejemplos?.clases[clase];
  const pedidos = [eleccion?.elegido, ...(eleccion?.alternativas ?? [])].flatMap((id) => deLaClase.find((s) => s.id === id) ?? []);
  if (pedidos.length > 0) return pedidos;
  const centro = mediana(deLaClase.map((s) => s.puntuacion));
  const reparo = (s: SujetoPuntuado) => Number(!s.imagen) * 4 + Number(!s.arbol) * 2 + Number(s.cerca_umbral);
  return [...deLaClase].sort((a, b) => reparo(a) - reparo(b) || Math.abs(a.puntuacion - centro) - Math.abs(b.puntuacion - centro)).slice(0, 4);
}

/**
 * Los sujetos que el modelo probado no vio y que se pueden recorrer paso a paso: el elegido primero.
 * Sin `ejemplos`, los de reserva, con preferencia por los que traen imagen, árbol y la lectura de aquel modelo.
 */
export function ejemplosDeInferencia(cohorte: Cohorte): Sujeto[] {
  const reserva = deReserva(cohorte);
  const eleccion = cohorte.ejemplos?.inferencia;
  const pedidos = [eleccion?.elegido, ...(eleccion?.alternativas ?? [])].flatMap((id) => reserva.find((s) => s.id === id) ?? []);
  if (pedidos.length > 0) return pedidos;
  const reparo = (s: Sujeto) => Number(!s.congelado) * 4 + Number(!s.imagen) * 2 + Number(!s.arbol);
  return [...reserva].sort((a, b) => reparo(a) - reparo(b));
}

/**
 * La persona de ejemplo que recorre las primeras diapositivas: alguien con obstrucción cuya TC lo dice claro.
 * Se prefiere un FEV1/FVC cerca de 0,61, que el grupo ciego sea el alto y un árbol bronquial muy por debajo de lo esperado.
 */
export function personaDeEjemplo(cohorte: Cohorte): SujetoPuntuado | undefined {
  const candidatos = conPuntuacion(cohorte).filter((s) => s.caso && s.clinica.fev1_fvc !== null && s.clinica.talla !== null && s.esperado.via_longitud_mm !== null && s.valores.via_longitud_mm !== null);
  const reparo = (s: SujetoPuntuado) =>
    Number(!s.dano_tc) * 16 + Number(s.ciego?.grupo !== "alto") * 8 + Number((s.z.via ?? 0) < 1.5) * 4 + Math.min(Math.abs((s.clinica.fev1_fvc ?? 0) - 0.61) * 10, 1.9) - Math.min(Math.max(s.z.via ?? 0, 0), 4) * 0.45;
  return [...candidatos].sort((a, b) => reparo(a) - reparo(b))[0];
}

/** "64 de 80" en dos números. `null` si el texto no tiene esa forma. */
export function fraccionDeTexto(texto: string | undefined): { aciertos: number; de: number } | null {
  const partes = texto?.match(/^(\d+) de (\d+)$/);
  return partes ? { aciertos: Number(partes[1]), de: Number(partes[2]) } : null;
}

/**
 * Por dónde sale una medida del embudo. Se decide con los números y los criterios, no con el texto de `resultado`:
 * primero la estabilidad entre los dos filtros del escáner, después la asociación y por último si aporta algo nuevo.
 */
export function salidaDelEmbudo(paso: PasoDelEmbudo, embudo: Pick<Embudo, "criterios" | "elegidas">): SalidaDelEmbudo {
  if (paso.icc < embudo.criterios.acuerdo_minimo) return "inestable";
  if (paso.q >= embudo.criterios.q_maximo) return "sin asociación";
  return embudo.elegidas.includes(paso.medida) ? "dentro" : "redundante";
}

/** La AUC fuera de muestra según cuántas medidas entran: los modelos "1 medida", "2 medidas"…, por orden. */
export function curvaDeComplejidad(complejidad: Complejidad): (ModeloDeComplejidad & { n: number })[] {
  return complejidad.modelos
    .flatMap((m) => {
      const n = m.modelo.match(/^(\d+) medidas?$/)?.[1];
      return n ? [{ ...m, n: Number(n) }] : [];
    })
    .sort((a, b) => a.n - b.n);
}

/** Un modelo de la comparación de complejidad por su nombre exacto. */
export function modeloDeComplejidad(complejidad: Complejidad | null | undefined, nombre: string): ModeloDeComplejidad | undefined {
  return complejidad?.modelos.find((m) => m.modelo === nombre);
}

/** El modelo que aprende los pesos de todas las medidas de TC. */
export function modeloConTodas(complejidad: Complejidad | null | undefined): ModeloDeComplejidad | undefined {
  return complejidad?.modelos.find((m) => /^log[ií]stica/.test(m.modelo));
}

/** Cuántos quedan del lado que les toca: con obstrucción y por encima de la línea de la TC, sin ella y por debajo. */
export function coincidenciaConLaEspirometria(cohorte: Cohorte): { epocPorEncima: number; epoc: number; controlesPorDebajo: number; controles: number } {
  const puntuados = conPuntuacion(cohorte);
  const epoc = puntuados.filter((s) => s.caso);
  const controles = puntuados.filter((s) => !s.caso);
  return { epocPorEncima: epoc.filter((s) => s.dano_tc).length, epoc: epoc.length, controlesPorDebajo: controles.filter((s) => !s.dano_tc).length, controles: controles.length };
}
