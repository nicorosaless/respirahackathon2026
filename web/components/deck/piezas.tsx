"use client";

// Las piezas que comparten las diapositivas: el titular, la entrada escalonada y las cifras grandes.
// Dentro del lienzo todo se mide en cqw, para que la diapositiva sea la misma a cualquier tamaño.

import { motion } from "motion/react";
import type { Cohorte } from "@/lib/cohorte";
import type { Geometria } from "@/lib/escena";

export interface PropsDiapositiva {
  cohorte: Cohorte;
  /** Dónde va cada punto de la cohorte en cada dibujo. La comparten las diapositivas en vivo. */
  geometria: Geometria;
  clic: number;
  avanzar: () => void;
  /** Sale de la presentación hacia una vista de la plataforma. */
  abrir: (ruta: string) => void;
  /** Salta al índice del anexo de preguntas. */
  alAnexo: () => void;
  /** Salta a una diapositiva del anexo por su título. Lo usa el índice. */
  irA: (titulo: string) => void;
}

export const SUAVE = [0.4, 0, 0.2, 1] as const;
export const TINTA = "#16161a";
export const TINTA_2 = "#55555e";
export const TINTA_3 = "#8e8e96";
export const GRIS = "#cfcdc7";
export const LINEA = "#e8e6e1";
export const LINEA_2 = "#d8d5ce";
export const DANO = "#f6821f";
export const DANO_TINTA = "#b4540a";

export function Titular({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.h1
      className={`font-semibold tracking-[-0.035em] text-balance ${className}`}
      initial={{ opacity: 0, y: "0.8cqw" }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: SUAVE }}
    >
      {children}
    </motion.h1>
  );
}

export function Aparece({ children, retraso, className = "" }: { children: React.ReactNode; retraso: number; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: "0.5cqw" }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: retraso, ease: SUAVE }}>
      {children}
    </motion.div>
  );
}

/**
 * El marco de las diapositivas del anexo: la pregunta tal como la haría el jurado, la respuesta corta como titular,
 * una frase debajo si hace falta y la evidencia en lo que queda.
 */
export function Diapositiva({
  pregunta,
  titular,
  entradilla,
  children,
  tamano = "text-[2.6cqw]",
}: {
  pregunta?: string;
  titular: React.ReactNode;
  entradilla?: React.ReactNode;
  children: React.ReactNode;
  tamano?: string;
}) {
  return (
    <div className="flex h-full flex-col px-[6cqw] pt-[2.2cqw] pb-[3.4cqw]">
      {pregunta && <p className="mb-[0.6cqw] text-[1.45cqw] leading-[1.25] font-medium text-tinta-3">«{pregunta}»</p>}
      <Titular className={`${tamano} leading-[1.08]`}>{titular}</Titular>
      {entradilla && (
        <Aparece retraso={0.2} className="mt-[1.1cqw] max-w-[78cqw] text-[1.55cqw] leading-[1.35] text-tinta-2">
          {entradilla}
        </Aparece>
      )}
      <div className="mt-[1.8cqw] flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}

/** Una cifra grande con la frase que dice qué es. */
export function Cifra({ valor, children, dano = false, className = "" }: { valor: React.ReactNode; children: React.ReactNode; dano?: boolean; className?: string }) {
  return (
    <div className={className}>
      <p className={`text-[4.4cqw] leading-none font-semibold tracking-[-0.045em] whitespace-nowrap ${dano ? "text-dano" : ""}`}>{valor}</p>
      <p className="mt-[0.7cqw] text-[1.2cqw] leading-[1.35] text-pretty text-tinta-2">{children}</p>
    </div>
  );
}

/** Al pie, cuando los puntos del gráfico no son personas reales. Las cifras impresas sí lo son. */
export function Simulado({ cohorte, que = "Los puntos" }: { cohorte: Cohorte; que?: string }) {
  if (!cohorte.aviso) return null;
  return (
    <p className="absolute bottom-[1.3cqw] left-[6cqw] text-[0.95cqw] text-tinta-3">
      {que} son sujetos simulados. Las cifras son las de los {cohorte.comprobaciones.sujetos} sujetos reales.
    </p>
  );
}

export function Rotulo({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <p className={`text-[0.95cqw] font-medium tracking-[0.05em] text-tinta-3 uppercase ${className}`}>{children}</p>;
}
