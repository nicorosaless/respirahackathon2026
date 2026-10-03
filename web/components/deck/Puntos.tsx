"use client";

import { motion } from "motion/react";
import { useMemo } from "react";
import { azar } from "@/lib/formato";
import { type Cuadro, type Geometria, LIENZO, PAPEL, puntos, TINTA } from "@/lib/escena";

const SUAVE = [0.4, 0, 0.2, 1] as const;

/**
 * Los puntos de la cohorte, siempre los mismos. Viven por encima de las diapositivas y no se desmontan al cambiar
 * de una a otra: por eso se mueven de un dibujo al siguiente en vez de aparecer en un gráfico nuevo.
 */
export function Puntos({ geometria, cuadro, clic }: { geometria: Geometria; cuadro: Cuadro | null; clic: number }) {
  const retrasos = useMemo(() => {
    const aleatorio = azar(7);
    return geometria.sujetos.map(() => aleatorio() * 0.35);
  }, [geometria]);
  const estado = puntos(geometria, cuadro, clic);

  return (
    <svg viewBox={`0 0 ${LIENZO.ancho} ${LIENZO.alto}`} className="pointer-events-none absolute inset-0 size-full" aria-hidden>
      {estado.map((p, i) => (
        <motion.circle
          key={p.id}
          initial={false}
          animate={{ cx: p.x, cy: p.y, r: p.radio, fill: p.hueco ? PAPEL : p.color, stroke: p.anillo ? TINTA : p.hueco ? p.color : PAPEL, opacity: p.opacidad }}
          strokeWidth={p.anillo ? 4 : p.hueco ? 3 : 1.5}
          transition={{
            cx: { duration: 0.95, delay: retrasos[i], ease: SUAVE },
            cy: { duration: 0.95, delay: retrasos[i], ease: SUAVE },
            r: { duration: 0.5, ease: SUAVE },
            fill: { duration: 0.5, delay: retrasos[i] * 0.6 },
            stroke: { duration: 0.5 },
            opacity: { duration: 0.45, delay: p.opacidad > 0 ? retrasos[i] : 0 },
          }}
        />
      ))}
    </svg>
  );
}
