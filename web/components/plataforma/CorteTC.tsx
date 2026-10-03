"use client";

import { useEffect, useRef, useState } from "react";
import { ETIQUETA_LOBULO, type Imagen, type Lobulo } from "@/lib/cohorte";
import { num } from "@/lib/formato";
import { publica } from "@/lib/ruta";

const DANO = [246, 130, 31];
/** Desde qué desviación se tiñe un lóbulo y a partir de cuál el color está lleno. */
export const TINTE_DESDE = 1;
export const TINTE_HASTA = 4;
const ATENUACION_FUERA = 0.55;
/** Con el árbol encima, la TC se apaga un poco para que las ramas, en blanco, se lean. */
const ATENUACION_BAJO_ARBOL = 0.8;
const OPACIDAD_ARBOL = 0.9;
/** La paleta de la diapositiva 2.1 (`components/deck/vivo.tsx`): un color suave por lóbulo, sin naranja, que es solo para el daño. */
export const COLOR_LOBULO: Record<Lobulo, [number, number, number]> = { LSD: [122, 166, 216], LM: [108, 192, 176], LID: [156, 207, 122], LSI: [179, 157, 219], LII: [230, 161, 192] };
const OPACIDAD_COLOR = 120 / 255;
/** Los píxeles por debajo de -950 HU, en rojo: el enfisema que se mide. */
const ROJO_ENFISEMA = [220, 38, 38];

/** Qué se dibuja encima de la TC. Sin ninguna capa, el corte queda tal cual sale del escáner. */
export interface Capas {
  /** El contorno de cada lóbulo; lo de fuera del pulmón se apaga. */
  lobulos: boolean;
  /** Cada lóbulo teñido por cuánto se aparta su enfisema de lo esperado. */
  tinte: boolean;
  /** El árbol bronquial segmentado, proyectado de delante atrás. Solo si el sujeto lo trae. */
  arbol: boolean;
  rotulos: "ninguno" | "nombres" | "desviaciones";
  /** Cada lóbulo de su color, como en la diapositiva 2.1. */
  colores?: boolean;
  /** Los píxeles de pulmón por debajo de -950 HU en rojo. Solo si la cohorte trae `<imagen>-<corte>-enfisema.png`. */
  enfisema?: boolean;
}

export const CAPAS_SUJETO: Capas = { lobulos: true, tinte: true, arbol: false, rotulos: "desviaciones" };

export function opacidadDano(z: number): number {
  if (!(z >= TINTE_DESDE)) return 0;
  return 0.14 + 0.56 * Math.min((z - TINTE_DESDE) / (TINTE_HASTA - TINTE_DESDE), 1);
}

function cargar(url: string): Promise<HTMLImageElement> {
  return new Promise((resolver, rechazar) => {
    const imagen = new Image();
    imagen.onload = () => resolver(imagen);
    imagen.onerror = () => rechazar(new Error(`No se pudo leer ${url}`));
    imagen.src = url;
  });
}

function pixeles(imagen: HTMLImageElement, ancho: number, alto: number): Uint8ClampedArray {
  const lienzo = document.createElement("canvas");
  lienzo.width = ancho;
  lienzo.height = alto;
  const contexto = lienzo.getContext("2d", { willReadFrequently: true })!;
  contexto.imageSmoothingEnabled = false;
  contexto.drawImage(imagen, 0, 0, ancho, alto);
  return contexto.getImageData(0, 0, ancho, alto).data;
}

/** Un corte coronal en gris con las capas pedidas encima. La TC nunca cambia de gris: el color es una capa. */
export function CorteTC({
  clave,
  imagen,
  corte,
  z,
  capas = CAPAS_SUJETO,
}: {
  clave: string;
  imagen: Imagen;
  corte: number;
  z: Record<Lobulo, number | null>;
  capas?: Capas;
}) {
  const lienzo = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState<string | null>(null);
  const { lobulos, tinte, arbol, rotulos, colores = false, enfisema = false } = capas;

  useEffect(() => {
    let vivo = true;
    const base = publica(`/data/previews/${clave}-${corte}`);
    // Si la máscara del árbol no está, el corte se dibuja sin ella: no es un fallo de la vista.
    const mascara = arbol ? cargar(publica(`/data/previews/${clave}-arbol.png`)).catch(() => null) : Promise.resolve(null);
    const bajo950 = enfisema ? cargar(`${base}-enfisema.png`).catch(() => null) : Promise.resolve(null);
    Promise.all([cargar(`${base}.png`), cargar(`${base}-lobulos.png`), mascara, bajo950]).then(
      ([gris, mapa, ramas, rojo]) => {
        const destino = lienzo.current;
        if (!vivo || !destino) return;
        const [ancho, alto] = [gris.naturalWidth, gris.naturalHeight];
        destino.width = ancho;
        destino.height = alto;
        const [tono, etiquetas] = [pixeles(gris, ancho, alto), pixeles(mapa, ancho, alto)];
        const via = ramas ? pixeles(ramas, ancho, alto) : null;
        const laa = rojo ? pixeles(rojo, ancho, alto) : null;
        const salida = new ImageData(ancho, alto);
        for (let i = 0; i < ancho * alto; i++) {
          const etiqueta = etiquetas[i * 4];
          const lobulo = ETIQUETA_LOBULO[etiqueta];
          const fuera = etiqueta === 0;
          const borde =
            lobulos &&
            !fuera &&
            (etiquetas[(i - 1) * 4] !== etiqueta || etiquetas[(i + 1) * 4] !== etiqueta || etiquetas[(i - ancho) * 4] !== etiqueta || etiquetas[(i + ancho) * 4] !== etiqueta);
          const alfa = colores && lobulo ? OPACIDAD_COLOR : 0;
          const pintura = colores && lobulo ? COLOR_LOBULO[lobulo] : DANO;
          const dano = tinte && lobulo ? opacidadDano(z[lobulo] ?? NaN) : 0;
          const enArbol = via !== null && via[i * 4] > 127;
          const enEnfisema = laa !== null && !fuera && laa[i * 4] > 127;
          const valor = tono[i * 4] * (lobulos && fuera ? ATENUACION_FUERA : 1) * (via ? ATENUACION_BAJO_ARBOL : 1);
          for (let canal = 0; canal < 3; canal++) {
            const coloreado = (1 - alfa) * valor + alfa * pintura[canal];
            const tintado = (1 - dano) * coloreado + dano * DANO[canal];
            const conBorde = borde ? 0.5 * tintado + 0.5 * 255 : tintado;
            const final = enArbol ? (1 - OPACIDAD_ARBOL) * conBorde + OPACIDAD_ARBOL * 255 : conBorde;
            salida.data[i * 4 + canal] = enEnfisema ? ROJO_ENFISEMA[canal] : final;
          }
          salida.data[i * 4 + 3] = 255;
        }
        destino.getContext("2d")!.putImageData(salida, 0, 0);
        setError(null);
      },
      (fallo: Error) => vivo && setError(fallo.message),
    );
    return () => {
      vivo = false;
    };
  }, [clave, corte, z, lobulos, tinte, arbol, colores, enfisema]);

  const centros = rotulos === "ninguno" ? {} : (imagen.cortes[corte]?.centros ?? {});

  return (
    <div className="relative overflow-hidden rounded-md bg-black" style={{ aspectRatio: `${imagen.ancho} / ${imagen.alto}` }}>
      <canvas ref={lienzo} className="size-full" aria-label="Corte coronal de la TC" />
      <span className="absolute top-2.5 left-2.5 rounded bg-black/60 px-1.5 py-0.5 text-[11px] font-semibold text-white">D</span>
      <span className="absolute top-2.5 right-2.5 rounded bg-black/60 px-1.5 py-0.5 text-[11px] font-semibold text-white">I</span>
      {(Object.entries(centros) as [Lobulo, [number, number]][]).map(([lobulo, [x, y]]) => {
        const desviacion = z[lobulo];
        const marcado = rotulos === "desviaciones" && tinte && desviacion !== null && desviacion >= TINTE_DESDE;
        return (
          <span
            key={lobulo}
            className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap tabular-nums ${
              colores ? "text-tinta" : marcado ? "bg-dano text-white" : "bg-black/65 text-white/90"
            }`}
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, background: colores ? `rgb(${COLOR_LOBULO[lobulo].join(" ")})` : undefined }}
          >
            {lobulo}
            {rotulos === "desviaciones" && ` ${num(desviacion, 1, true)}`}
          </span>
        );
      })}
      {error && <p className="absolute inset-0 grid place-items-center p-6 text-center text-sm text-white/80">{error}</p>}
    </div>
  );
}
