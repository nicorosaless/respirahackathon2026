"use client";

import { motion } from "motion/react";
import { useCohorte } from "@/lib/cohorte";

// La plataforma es solo Inferencia y ocupa todo el ancho. La vuelta a la presentación está junto a las píldoras.
export default function Plataforma({ children }: LayoutProps<"/plataforma">) {
  const { cohorte, error } = useCohorte();

  return (
    <motion.main className="min-h-screen px-7 py-6 [&_.tarjeta]:rounded-md" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.45 }}>
      <div className="mx-auto w-full max-w-[1600px]">
        {error && <p className="tarjeta p-6 text-dano-tinta">{error}</p>}
        {children}
        {cohorte?.aviso && <p className="mt-6 text-xs text-tinta-3">Datos de ejemplo: sujetos simulados sobre TC públicas. Las cifras son las de la cohorte del reto.</p>}
      </div>
    </motion.main>
  );
}
