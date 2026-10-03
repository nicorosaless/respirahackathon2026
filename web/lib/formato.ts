// Números como se escriben en español: coma decimal y el signo menos tipográfico.

export function num(valor: number | null | undefined, decimales = 2, signo = false): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "–";
  // El 5 final redondea hacia arriba, como en `docs/cifras.md`: 0,745 es 0,75. `toFixed` solo lo dejaría en 0,74.
  const escala = 10 ** decimales;
  const texto = (Math.round(Math.abs(valor) * escala + 1e-9) / escala).toFixed(decimales).replace(".", ",");
  // Un cero redondeado no lleva signo: ni «−0,00» ni «+0,0».
  if (Number(texto.replace(",", ".")) === 0) return texto;
  if (valor < 0) return `−${texto}`;
  return signo ? `+${texto}` : texto;
}

/** Una mediana de cuestionario: entera casi siempre, con un decimal cuando cae entre dos valores (5,5). */
export function mediano(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "–";
  return num(valor, Number.isInteger(Math.round(valor * 10) / 10) ? 0 : 1);
}

/** Una proporción como porcentaje entero: 0,821 es "82 %". */
export function porcentaje(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "–";
  return `${num(valor * 100, 0)}\u00a0%`;
}

export function pValor(p: number | null | undefined): string {
  if (p === null || p === undefined || !Number.isFinite(p)) return "–";
  if (p < 0.001) return "< 0,001";
  // Dos decimales, como en `docs/cifras.md`. El tercero solo cuando cambia la lectura: pequeña (0,014) o pegada a 0,05.
  return num(p, p < 0.02 || (p >= 0.045 && p < 0.055) ? 3 : 2);
}

export function mediana(valores: number[]): number {
  const orden = [...valores].sort((a, b) => a - b);
  const mitad = Math.floor(orden.length / 2);
  return orden.length % 2 ? orden[mitad] : (orden[mitad - 1] + orden[mitad]) / 2;
}

/** Generador determinista: los dibujos salen iguales en el servidor y en el navegador. */
export function azar(semilla: number): () => number {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function descargar(nombre: string, contenido: string, tipo = "text/csv;charset=utf-8"): void {
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(new Blob([contenido], { type: tipo }));
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}

/** Una longitud en milímetros, escrita en metros. */
export function metros(milimetros: number | null | undefined): string {
  if (milimetros === null || milimetros === undefined || !Number.isFinite(milimetros)) return "sin dato";
  return `${num(milimetros / 1000, 2)} m`;
}
