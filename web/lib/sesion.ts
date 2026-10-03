// Lo que la presentación recuerda mientras la pestaña sigue abierta: el cronómetro y la diapositiva a la que se vuelve.
// La demo sale de la presentación a la plataforma y regresa; sin esto el reloj se pondría a cero a mitad del recorrido.

export interface Reloj {
  inicio: number | null;
  /** Cuándo se paró. `null` mientras corre. */
  fin: number | null;
}

export const RELOJ_PARADO: Reloj = { inicio: null, fin: null };
/** Lo que debe durar la presentación ante el jurado: 4:30, para dejar margen hasta los 5:00. Pasado este tiempo el cronómetro se pone naranja. */
export const SEGUNDOS_DE_DEMO = 270;

export type AccionReloj = "arrancar" | "parar" | "borrar";

/** Arranca con el primer avance, se para una sola vez y solo vuelve a cero si se borra. */
export function siguienteReloj(reloj: Reloj, accion: AccionReloj, ahora: number): Reloj {
  if (accion === "borrar") return RELOJ_PARADO;
  if (accion === "arrancar") return reloj.inicio === null ? { inicio: ahora, fin: null } : reloj;
  return reloj.inicio !== null && reloj.fin === null ? { ...reloj, fin: ahora } : reloj;
}

const CLAVE_RELOJ = "maps.reloj";
const CLAVE_VUELTA = "maps.vuelta";

export function leerReloj(): Reloj {
  try {
    const guardado = JSON.parse(window.sessionStorage.getItem(CLAVE_RELOJ) ?? "null") as Partial<Reloj> | null;
    if (guardado && (typeof guardado.inicio === "number" || guardado.inicio === null)) return { inicio: guardado.inicio, fin: typeof guardado.fin === "number" ? guardado.fin : null };
  } catch {
    // Sin almacenamiento o con un valor roto, el reloj empieza de cero.
  }
  return RELOJ_PARADO;
}

export function moverReloj(accion: AccionReloj): Reloj {
  const reloj = siguienteReloj(leerReloj(), accion, Date.now());
  try {
    window.sessionStorage.setItem(CLAVE_RELOJ, JSON.stringify(reloj));
  } catch {
    // El cronómetro sigue funcionando dentro de la presentación aunque no se pueda guardar.
  }
  return reloj;
}

export interface Vuelta {
  /** Por dónde sigue la presentación al volver de la plataforma, como ruta (`/?d=9`). */
  ruta: string;
  /** La diapositiva desde la que se salió, para poder retroceder. */
  anterior: string;
  /** Se llegó a la plataforma desde la presentación: las flechas siguen el recorrido de la demo. */
  desdePresentacion: boolean;
}

/**
 * Al salir hacia la plataforma: por qué diapositiva se sigue al volver y desde cuál se salió, como consultas de URL (`?d=9`).
 * En la demo no coinciden: se sale de los hallazgos y se vuelve a las conclusiones.
 */
export function guardarVuelta(siguiente: string, anterior = siguiente): void {
  try {
    window.sessionStorage.setItem(CLAVE_VUELTA, JSON.stringify({ siguiente, anterior }));
  } catch {
    // Sin almacenamiento se vuelve a la primera diapositiva.
  }
}

export function leerVuelta(): Vuelta {
  try {
    const guardado = JSON.parse(window.sessionStorage.getItem(CLAVE_VUELTA) ?? "null") as { siguiente?: unknown; anterior?: unknown } | null;
    if (guardado && typeof guardado.siguiente === "string")
      return { ruta: `/${guardado.siguiente}`, anterior: `/${typeof guardado.anterior === "string" ? guardado.anterior : guardado.siguiente}`, desdePresentacion: true };
  } catch {
    // Igual que arriba.
  }
  return { ruta: "/", anterior: "/", desdePresentacion: false };
}
