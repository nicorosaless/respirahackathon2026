"use client";

import { motion } from "motion/react";
import { useEffect } from "react";
import { DosMedidas, Espirometria, NivelDeLaTC, TCDeLaPersona } from "@/components/plataforma/Persona";
import { EtiquetaClase } from "@/components/ui";
import type { Cohorte, Sujeto } from "@/lib/cohorte";
import { num } from "@/lib/formato";
import { lecturaDelModeloFinal } from "@/lib/inferencia";

/** La ficha de una persona, como panel lateral: se abre al pinchar su punto en el gráfico de la cohorte. */
export function FichaSujeto({ cohorte, sujeto, alCerrar }: { cohorte: Cohorte; sujeto: Sujeto; alCerrar: () => void }) {
  useEffect(() => {
    const alPulsar = (evento: KeyboardEvent) => evento.key === "Escape" && alCerrar();
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [alCerrar]);

  const lectura = lecturaDelModeloFinal(sujeto, cohorte);
  const c = sujeto.clinica;
  // Lo que falta en la tabla clínica se dice; no se dibuja como un cero.
  const dato = (valor: number | null, texto: (v: number) => string) => (valor === null ? "sin dato" : texto(valor));
  const clinica: [string, string][] = [
    ["Edad", dato(c.edad, (v) => `${num(v, 0)} años`)],
    ["Sexo", c.sexo === "H" ? "Hombre" : "Mujer"],
    ["Talla", dato(c.talla, (v) => `${num(v, 0)} cm`)],
    ["Tabaco", c.fuma ? "Fuma" : "Ya no fuma"],
    ["Paquetes-año", dato(c.paquetes_ano, (v) => num(v, 0))],
    ["FEV1, % del predicho", dato(c.fev1_pct, (v) => num(v, 0))],
    ["DLCO, % del predicho", dato(c.dlco_pct, (v) => num(v, 0))],
    ["Síntomas (CAT)", dato(c.cat, (v) => num(v, 0))],
  ];

  return (
    <>
      <motion.div className="fixed inset-0 z-30 bg-tinta/20" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={alCerrar} aria-hidden />
      <motion.aside
        className="fixed inset-y-0 right-0 z-40 flex w-[30rem] max-w-full flex-col overflow-y-auto border-l border-linea bg-white p-5 shadow-[-24px_0_60px_-30px_rgb(22_22_26/0.3)]"
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
        role="dialog"
        aria-label={`Ficha de ${sujeto.id}`}
      >
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">{sujeto.id}</h2>
          <EtiquetaClase clase={sujeto.clase} />
          <button type="button" className="btn btn-linea btn-s ml-auto" onClick={alCerrar}>
            Cerrar
          </button>
        </div>
        <p className="mt-2 text-sm leading-snug text-tinta-2">{sujeto.motivo}</p>

        <div className="mt-4">
          <TCDeLaPersona cohorte={cohorte} sujeto={sujeto} segmentada />
        </div>
        <div className="mt-2">
          <DosMedidas sujeto={sujeto} lectura={lectura} conEsperado />
        </div>
        <div className="mt-3 flex flex-col gap-3">
          <NivelDeLaTC lectura={lectura} nota="La puntuación no usa su espirometría." />
          <Espirometria sujeto={sujeto}>{null}</Espirometria>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-6 text-sm">
          {clinica.map(([nombre, valor]) => (
            <div key={nombre} className="flex items-baseline justify-between gap-3 border-b border-linea py-1.5">
              <dt className="text-tinta-2">{nombre}</dt>
              <dd className={valor === "sin dato" ? "text-tinta-3" : "font-medium tabular-nums"}>{valor}</dd>
            </div>
          ))}
        </dl>

        {sujeto.tradicionales.length > 0 && (
          <>
            <h3 className="mt-5 text-sm font-semibold">Las medidas que nombra el reto</h3>
            <table className="mt-1 w-full text-sm">
              <tbody className="tabular-nums">
                {sujeto.tradicionales.map((m) => (
                  <tr key={m.medida} className="border-b border-linea last:border-0 [&>td]:py-1.5">
                    <td className="text-tinta-2">{m.medida === "laa950" ? "%LAA-950 clásico" : m.nombre}</td>
                    <td className="text-right font-medium">{m.valor === null ? <span className="font-normal text-tinta-3">sin dato</span> : `${num(m.valor, 2)}${m.unidad ? ` ${m.unidad}` : ""}`}</td>
                    <td className="w-14 text-right text-tinta-2">{m.z === null ? "–" : num(m.z, 1, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-1 text-xs text-tinta-3">A la derecha, cuántas desviaciones se aparta de lo esperado. Con signo más, hacia el lado de la EPOC.</p>
          </>
        )}
      </motion.aside>
    </>
  );
}
