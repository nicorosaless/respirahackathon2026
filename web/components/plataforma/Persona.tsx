"use client";

// Las piezas con las que se enseña a una persona: su TC, sus dos medidas frente a lo esperado, si su TC pasa el umbral y su
// espirometría. Las comparten la ficha de Cohorte, los ejemplos de cada clase y el recorrido paso a paso.

import { motion } from "motion/react";
import { type Capas, CorteTC } from "@/components/plataforma/CorteTC";
import { Regla } from "@/components/plataforma/Regla";
import type { Cohorte, Sujeto } from "@/lib/cohorte";
import { metros, num } from "@/lib/formato";
import { comparacion, describirPersona, desviacionEnPalabras, type Lectura, nombreDelModelo } from "@/lib/inferencia";

export const SIN_CAPAS: Capas = { lobulos: false, tinte: false, arbol: false, rotulos: "ninguno" };
export const SEGMENTADA: Capas = { lobulos: true, tinte: false, arbol: true, rotulos: "nombres" };

export function Entra({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}

/** El corte de TC de una persona, con las capas pedidas. Sin imagen, lo dice. */
export function TCDeLaPersona({ cohorte, sujeto, segmentada }: { cohorte: Cohorte; sujeto: Sujeto; segmentada: boolean }) {
  const imagen = sujeto.imagen ? cohorte.imagenes[sujeto.imagen] : undefined;
  if (!imagen || !sujeto.imagen) return <p className="grid aspect-square place-items-center rounded-md bg-fondo p-6 text-center text-sm text-tinta-3">Esta persona no tiene vista previa de la TC. Las medidas sí están.</p>;
  return (
    <>
      <CorteTC clave={sujeto.imagen} imagen={imagen} corte={Math.floor(imagen.cortes.length / 2)} z={sujeto.lobulos} capas={segmentada ? { ...SEGMENTADA, arbol: sujeto.arbol } : SIN_CAPAS} />
      <p className="mt-2 text-xs text-tinta-3">{!segmentada ? "La TC, sin nada encima." : sujeto.arbol ? "Los lóbulos y, en blanco, el árbol bronquial." : "Los lóbulos. Esta persona no trae el árbol segmentado."}</p>
    </>
  );
}

function Medida({ nombre, valor, detalle, persona, esperado, compara, medida, z, conEsperado }: { nombre: string; valor: string; detalle: string; persona: string; esperado: string | null; compara: string | null; medida: "enfisema" | "via"; z: number | null; conEsperado: boolean }) {
  const desviacion = desviacionEnPalabras(medida, z);
  // El z va orientado: positivo es hacia el daño y suma a la puntuación; negativo resta.
  const suma = z !== null && desviacion !== null && desviacion.cuanto !== "0,0" && z > 0;
  const resta = z !== null && desviacion !== null && desviacion.cuanto !== "0,0" && z < 0;
  const sentido = medida === "enfisema" ? (suma ? "más enfisema" : "menos enfisema") : suma ? "menos árbol" : "más árbol";
  const conSigno = desviacion === null ? "–" : suma || resta ? num(z, 1, true) : desviacion.cuanto;
  const lectura = desviacion === null ? "sin desviación calculada" : suma || resta ? `desviaciones (${sentido} de lo esperado: ${suma ? "suma" : "resta"})` : desviacion.direccion;
  return (
    <div className="grid grid-cols-[1fr_auto] items-start gap-x-4 border-b border-linea py-2.5">
      <div>
        <p className="text-xs font-medium tracking-wide text-tinta-3 uppercase">{nombre}</p>
        <p className="mt-0.5 flex items-baseline gap-2">
          <span className="text-2xl font-semibold tracking-tight whitespace-nowrap tabular-nums">{valor}</span>
          <span className="text-xs text-tinta-3">{detalle}</span>
        </p>
        {conEsperado && (
          <Entra className="mt-0.5 text-sm leading-snug text-tinta-2">
            {esperado === null ? (
              "No hay valor esperado para esta persona."
            ) : (
              <>
                Esperado para {persona}: <strong className="font-semibold text-tinta">{esperado}</strong>.{compara && ` ${compara[0].toUpperCase()}${compara.slice(1)}.`}
              </>
            )}
          </Entra>
        )}
      </div>
      {conEsperado && (
        <Entra className="text-right">
          <span className={`text-3xl font-semibold tracking-tight tabular-nums ${suma ? "text-dano-tinta" : resta ? "text-tinta-3" : ""}`}>{conSigno}</span>
          <span className="block ml-auto max-w-[9rem] text-xs leading-tight text-balance text-tinta-3">{lectura}</span>
        </Entra>
      )}
    </div>
  );
}

/** Las dos medidas de la TC. Con `conEsperado`, cada una junto a lo esperado para esa persona. */
export function DosMedidas({ sujeto, lectura, conEsperado, solo }: { sujeto: Sujeto; lectura: Lectura; conEsperado: boolean; solo?: "enfisema" | "via" }) {
  const persona = describirPersona(sujeto.clinica);
  const { valores, esperado, z } = lectura;
  return (
    <div>
      {solo !== "via" && <Medida
        nombre="Enfisema"
        valor={valores.laa950_smooth === null ? "sin dato" : `${num(valores.laa950_smooth, 2)} %`}
        detalle="del pulmón"
        persona={persona}
        esperado={esperado.laa950_smooth === null ? null : `${num(esperado.laa950_smooth, 2)} %`}
        compara={comparacion("laa950_smooth", valores.laa950_smooth, esperado.laa950_smooth)}
        medida="enfisema"
        z={z.enfisema}
        conEsperado={conEsperado}
      />}
      {solo !== "enfisema" && <Medida
        nombre="Árbol bronquial"
        valor={metros(valores.via_longitud_mm)}
        detalle="la suma de las ramas que se ven"
        persona={persona}
        esperado={esperado.via_longitud_mm === null ? null : metros(esperado.via_longitud_mm)}
        compara={comparacion("via_longitud_mm", valores.via_longitud_mm, esperado.via_longitud_mm)}
        medida="via"
        z={z.via}
        conEsperado={conEsperado}
      />}
    </div>
  );
}

/** La TC por encima o por debajo del umbral, con la puntuación sobre la regla. */
export function NivelDeLaTC({ lectura, nota }: { lectura: Lectura; nota: string }) {
  return (
    <div className="rounded-md bg-papel px-4 py-3">
      <div className="grid grid-cols-[1fr_auto] items-center gap-x-4">
        <p className="flex flex-wrap items-center gap-2 text-lg font-semibold tracking-tight">
          Su TC es:
          {lectura.puntuacion === null ? (
            <span className="inline-flex items-center rounded-full border border-dashed border-tinta-3 px-2.5 py-0.5 text-lg text-tinta-2">sin puntuación</span>
          ) : (
            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-lg whitespace-nowrap ${lectura.dano_tc ? "border-dano bg-dano text-white" : "border-linea-2 bg-white text-tinta-2"}`}>
              {lectura.dano_tc ? "por encima del umbral" : "por debajo del umbral"}
            </span>
          )}
          {lectura.cerca_umbral && <span className="rounded-full border border-dashed border-tinta-3 px-2.5 py-0.5 text-xs font-medium tracking-normal text-tinta-2">cerca del umbral</span>}
        </p>
        <p className="text-right">
          <span className={`text-3xl leading-none font-semibold tracking-tight tabular-nums ${lectura.dano_tc ? "text-dano-tinta" : ""}`}>{num(lectura.puntuacion, 2, true)}</span>
          <span className="block text-[11px] text-tinta-3">puntuación de daño</span>
        </p>
      </div>
      {/* Hay dos juegos de umbrales en la app: el de cada lectura dice de qué modelo es. */}
      <p className="mt-2 text-xs font-medium tracking-wide text-tinta-3 uppercase">{nombreDelModelo(lectura)}</p>
      {lectura.puntuacion === null ? <p className="mt-2 text-sm text-tinta-2">Sin puntuación: no se pudo medir esta TC.</p> : <Regla z={lectura.puntuacion} umbral={lectura.umbral} escala />}
      <p className="mt-1 text-xs leading-relaxed text-tinta-3">{nota}</p>
    </div>
  );
}

/** Lo que dice la espirometría de esta persona, y debajo lo que toque: si coincide con la TC o cuál es su clase. */
export function Espirometria({ sujeto, children }: { sujeto: Sujeto; children: React.ReactNode }) {
  const cociente = sujeto.clinica.fev1_fvc;
  return (
    <div className="rounded-md border border-tinta px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <p>
          <span className="block text-xs font-medium tracking-wide text-tinta-3 uppercase">FEV1/FVC</span>
          {cociente === null ? <span className="text-base font-medium text-tinta-3">sin dato</span> : <span className="text-3xl leading-none font-semibold tracking-tight tabular-nums">{num(cociente, 2)}</span>}
        </p>
        <p className="text-lg font-semibold tracking-tight">
          La espirometría dice: <span className={`rounded-full px-3 py-0.5 ${sujeto.caso ? "bg-tinta text-white" : "border border-linea-2 bg-white"}`}>{sujeto.caso ? "obstrucción" : "sin obstrucción"}</span>
        </p>
      </div>
      {children}
    </div>
  );
}
