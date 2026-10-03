"use client";

// Respuestas del anexo: dos lecturas y pre-EPOC. Las constantes de la primera prueba las comparten las demás.
// Las cifras salen de `cohorte.validacion`, `cohorte.comprobaciones`, `cohorte.escalera`, `cohorte.reserva` y
// `cohorte.discordantes`, que son los agregados de `docs/figuras/` y coinciden con `docs/cifras.md`.
// Las palabras siguen `docs/cifras.md`: lo que supera el umbral es una "TC parecida a la de la EPOC", no un daño demostrado.

import { motion } from "motion/react";
import { type FilaExploratoria, lectura } from "@/lib/cohorte";
import { mediano, num, pValor } from "@/lib/formato";
import { LLN } from "@/lib/lln";
import { Aparece, Diapositiva, type PropsDiapositiva, SUAVE } from "./piezas";

// Los 62 sujetos del primer modelo y los 15 que se apartaron: `docs/cifras.md`, bloque 3.
export const AJUSTE_DEL_PRIMER_MODELO = 62;
export const RESERVA_DE_LA_PRIMERA_PRUEBA = 15;

function BarraDeLectura({ nombre, fila, fuerte, retraso }: { nombre: string; fila: FilaExploratoria | undefined; fuerte: boolean; retraso: number }) {
  if (!fila) return null;
  // De −1 a +1, con el cero en el centro: hacia la derecha, más puntuación va con más de esa variable; hacia la izquierda, con menos.
  const mitad = `${Math.min(Math.abs(fila.rho), 1) * 50}%`;
  return (
    <div className="grid grid-cols-[1fr_15cqw_5.5cqw] items-center gap-[1.2cqw] border-b border-linea py-[0.85cqw]">
      <div>
        <p className={`text-[1.3cqw] leading-[1.2] ${fuerte ? "font-semibold" : "text-tinta-2"}`}>{nombre}</p>
        <p className="mt-[0.2cqw] text-[0.95cqw] text-tinta-3">
          p {fila.p < 0.001 ? "" : "= "}
          {pValor(fila.p)}; corregida, q = {pValor(fila.q)}
        </p>
      </div>
      <span className="relative h-[1.5cqw] rounded-full bg-fondo">
        <span className="absolute inset-y-[-0.3cqw] left-1/2 w-px bg-tinta-3" />
        <motion.span
          className={`absolute inset-y-0 rounded-full ${fuerte ? "bg-tinta" : "bg-control"} ${fila.rho < 0 ? "right-1/2 origin-right" : "left-1/2 origin-left"}`}
          style={{ width: `max(${mitad}, 0.3cqw)` }}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ delay: retraso, duration: 0.6, ease: SUAVE }}
        />
      </span>
      <strong className={`text-right text-[2.2cqw] leading-none font-semibold tracking-[-0.03em] tabular-nums ${fuerte ? "" : "text-tinta-2"}`}>{num(fila.rho, 2)}</strong>
    </div>
  );
}

export function DosLecturasConCifras({ cohorte }: PropsDiapositiva) {
  const { epoc, controles } = cohorte.comprobaciones;
  const hay = Boolean(cohorte.discordantes);
  const columna = "rounded-[1.1cqw] border border-linea bg-white px-[1.7cqw] pt-[1.4cqw] pb-[0.6cqw]";

  return (
    <Diapositiva
      pregunta="¿Es lesión o un árbol pequeño de origen?"
      titular={
        <>
          No lo distinguimos. Hipótesis: en los controles, calibre de la vía más que tabaco.{" "}
          <span className="ml-[0.6cqw] inline-block rounded-full border-[0.14cqw] border-dashed border-tinta-3 px-[1cqw] py-[0.3cqw] align-middle text-[1.2cqw] font-medium tracking-normal text-tinta-2">
            Exploratorio
          </span>
        </>
      }
      entradilla="Con qué va la puntuación de daño dentro de cada grupo. Cada barra es una correlación: a la derecha del centro, más puntuación va con más de eso; a la izquierda, con menos."
    >
      {hay ? (
        <div className="grid min-h-0 flex-1 grid-cols-2 items-start gap-[2.4cqw]">
          <Aparece retraso={0.3} className={columna}>
            <p className="text-[1.6cqw] leading-[1.2] font-semibold tracking-[-0.02em]">En los {epoc} con EPOC: gravedad</p>
            <p className="mt-[0.3cqw] mb-[0.4cqw] text-[1.1cqw] text-tinta-2">Más disnea, peor intercambio de gases, más enfisema visible.</p>
            <BarraDeLectura nombre="Disnea (escala mMRC)" fila={lectura(cohorte, "casos", "Disnea")} fuerte retraso={0.6} />
            <BarraDeLectura nombre="Difusión (DLCO)" fila={lectura(cohorte, "casos", "DLCO")} fuerte retraso={0.7} />
            <BarraDeLectura nombre="Enfisema a ojo del radiólogo" fila={lectura(cohorte, "casos", "Enfisema visual")} fuerte retraso={0.8} />
          </Aparece>
          <Aparece retraso={0.5} className={columna}>
            <p className="text-[1.6cqw] leading-[1.2] font-semibold tracking-[-0.02em]">En los {controles} sin obstrucción: una hipótesis</p>
            <p className="mt-[0.3cqw] mb-[0.4cqw] text-[1.1cqw] text-tinta-2">Va más con un calibre central estrecho para su pulmón que con el tabaco.</p>
            <BarraDeLectura nombre="Calibre central estrecho para su pulmón" fila={lectura(cohorte, "controles", "Calibre central")} fuerte retraso={0.9} />
            <BarraDeLectura nombre="Fumar ahora" fila={lectura(cohorte, "controles", "Fuman ahora")} fuerte={false} retraso={1.0} />
            <BarraDeLectura nombre="Paquetes-año" fila={lectura(cohorte, "controles", "Paquetes-año")} fuerte={false} retraso={1.1} />
          </Aparece>
        </div>
      ) : (
        <p className="my-auto text-[1.4cqw] text-tinta-2">Pendiente: esta cohorte no trae el análisis de la puntuación dentro de cada grupo.</p>
      )}
      <Aparece retraso={1.3} className="mt-[1.4cqw] max-w-[70cqw] text-[1.15cqw] leading-[1.4] text-tinta-2">
        Es compatible con un árbol bronquial pequeño de origen. <strong className="font-semibold text-tinta">No lo demuestra:</strong> el calibre y la longitud salen de la misma segmentación, y son muchas comparaciones
        con pocos sujetos.
      </Aparece>
    </Diapositiva>
  );
}

// Anexo. Lo que no demostramos: los posibles pre-EPOC frente a los demás sin obstrucción.
// El seguimiento es a 3,6 años: `docs/cifras.md`. El resto sale de `controles_por_dano`, `asociaciones` y `conexion`.
const ANOS_SEGUIMIENTO = "3,6";

export function Limites({ cohorte }: PropsDiapositiva) {
  const { controles_por_dano: marcados, asociaciones } = cohorte.comprobaciones;
  const total = marcados.con_dano + marcados.sin_dano;
  const cociente = marcados.visita_1.find((f) => f.variable === "FEV1/FVC");
  const cat = marcados.visita_1.find((f) => f.variable === "CAT");
  const cambio = marcados.seguimiento.find((f) => f.variable === "Cambio del FEV1 %");
  const cerca = marcados.cerca_de_la_obstruccion;
  const tabaco = asociaciones.find((a) => a.variable === "Paquetes-año")?.controles;
  const columnas = Math.ceil(Math.sqrt(total * 1.6));

  const filas = [
    {
      nombre: "FEV1/FVC",
      con: num(cociente?.con_dano, 2),
      sin: num(cociente?.sin_dano, 2),
      p: cociente?.p,
      lectura: cerca ? `Están más cerca de la obstrucción: ${cerca.con_dano} de ${marcados.con_dano} por debajo de 0,75, frente a ${cerca.sin_dano} de ${marcados.sin_dano}.` : "Están más cerca de la obstrucción.",
    },
    { nombre: "Síntomas (cuestionario CAT)", con: mediano(cat?.con_dano), sin: mediano(cat?.sin_dano), p: cat?.p, lectura: "No detectamos diferencias en síntomas." },
    {
      nombre: `Cambio del FEV1 en ${ANOS_SEGUIMIENTO} años (puntos del % predicho)`,
      con: num(cambio?.con_dano, 1, true),
      sin: num(cambio?.sin_dano, 1, true),
      p: cambio?.p,
      lectura: "No detectamos una caída mayor del FEV1.",
    },
  ];

  return (
    <Diapositiva
      pregunta="¿Qué es pre-EPOC para vosotros?"
      titular={`Sin obstrucción y con la TC parecida a la de la EPOC: ${marcados.con_dano} de ${total}. Sin PRISm.`}
      entradilla={`Es nuestra regla, no un diagnóstico. Esto es lo que distingue a esas ${marcados.con_dano} personas de las otras ${marcados.sin_dano}.`}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[19cqw_1fr] items-center gap-[4cqw]">
        <div>
          <div className="grid gap-[0.5cqw]" style={{ gridTemplateColumns: `repeat(${columnas}, 1fr)` }}>
            {Array.from({ length: total }, (_, i) => (
              <motion.span
                key={i}
                className={`aspect-square rounded-full ${i < marcados.con_dano ? "bg-dano" : "bg-[#cfcdc7]"}`}
                initial={{ opacity: 0, scale: 0.4 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 + 0.012 * i }}
              />
            ))}
          </div>
          <p className="mt-[1.1cqw] text-[1.2cqw] leading-[1.35]">
            <strong className="font-semibold text-dano-tinta">{marcados.con_dano} con la TC parecida a la de la EPOC</strong>
            <br />
            <span className="text-tinta-2">{marcados.sin_dano} por debajo del umbral</span>
          </p>
        </div>

        <div className="flex flex-col">
          <div className="grid grid-cols-[1.2fr_6.5cqw_6.5cqw_1.6fr] items-baseline gap-x-[1.6cqw] border-b border-linea pb-[0.6cqw] text-[1cqw] text-tinta-3">
            <span />
            <span className="text-right font-medium text-dano-tinta">Los {marcados.con_dano}</span>
            <span className="text-right">Los {marcados.sin_dano}</span>
            <span />
          </div>
          {filas.map((f, i) => (
            <Aparece key={f.nombre} retraso={0.7 + 0.2 * i} className="grid grid-cols-[1.2fr_6.5cqw_6.5cqw_1.6fr] items-baseline gap-x-[1.6cqw] border-b border-linea py-[1cqw]">
              <span className="text-[1.3cqw] leading-[1.25] font-medium">{f.nombre}</span>
              <span className="text-right text-[2.3cqw] leading-none font-semibold tracking-[-0.03em] text-dano-tinta tabular-nums">{f.con}</span>
              <span className="text-right text-[2.3cqw] leading-none font-semibold tracking-[-0.03em] text-tinta-2 tabular-nums">{f.sin}</span>
              <span className="text-[1.15cqw] leading-[1.3] text-tinta-2">
                {f.lectura}
                {f.p !== undefined && <span className="text-tinta-3"> p = {pValor(f.p)}</span>}
              </span>
            </Aparece>
          ))}
          <Aparece retraso={1.4} className="mt-[1.2cqw] text-[1.2cqw] leading-[1.45] text-tinta-2">
            <strong className="font-semibold text-tinta">El umbral separa EPOC de control. No demuestra una lesión.</strong>
            {tabaco && ` Más tabaco acumulado no va con más puntuación (dentro de los controles, ${num(tabaco.rho, 2)}).`}
          </Aparece>
          {marcados.con_dano === LLN.pre_epoc && (
            <Aparece retraso={1.6} className="mt-[0.8cqw] text-[1.2cqw] leading-[1.45] text-tinta-2">
              <strong className="font-semibold text-tinta">
                {LLN.pre_epoc - LLN.pre_epoc_bajo_lln} de {LLN.pre_epoc} tienen el cociente normal para su edad, sexo y talla (GLI-2012).
              </strong>{" "}
              No son obstruidos que se escapan del 0,70.
            </Aparece>
          )}
        </div>
      </div>
    </Diapositiva>
  );
}

