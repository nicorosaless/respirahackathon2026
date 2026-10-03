"use client";

import { useState } from "react";
import { COLOR_CLASE } from "@/components/ui";
import { type Clase, type Cohorte, conPuntuacion, NOMBRE_CLASE, type SujetoPuntuado, umbralNormalidad } from "@/lib/cohorte";
import { num } from "@/lib/formato";

const ANCHO = 800;
const ALTO = 480;
const MARGEN = { izquierda: 64, derecha: 20, arriba: 20, abajo: 52 };

function marcas(minimo: number, maximo: number, paso: number): number[] {
  const salida = [];
  for (let valor = Math.ceil(minimo / paso) * paso; valor <= maximo + 1e-9; valor += paso) salida.push(Number(valor.toFixed(6)));
  return salida;
}

type Punto = SujetoPuntuado & { cociente: number };

/** Cada sujeto por su espirometría y por su puntuación de daño, con el umbral de obstrucción y los dos de la TC. */
export function Dispersion({ cohorte, filtro, alElegir }: { cohorte: Cohorte; filtro: Clase | null; alElegir: (sujeto: SujetoPuntuado) => void }) {
  const [encima, setEncima] = useState<Punto | null>(null);
  const { umbral_dano, umbral_cociente } = cohorte;
  // Sin espirometría o sin puntuación no hay dónde poner el punto.
  const sujetos: Punto[] = conPuntuacion(cohorte).flatMap((s) => (s.clinica.fev1_fvc === null ? [] : [{ ...s, cociente: s.clinica.fev1_fvc }]));
  const normalidad = umbralNormalidad(cohorte);
  const cocientes = sujetos.map((s) => s.cociente);
  const puntuaciones = sujetos.map((s) => s.puntuacion);
  const [x0, x1] = [Math.min(...cocientes) - 0.02, Math.max(...cocientes) + 0.02];
  // Hueco abajo para los rótulos de las dos zonas de debajo del umbral.
  const [y0, y1] = [Math.min(...puntuaciones) - 1.1, Math.max(...puntuaciones) + 0.4];
  const x = (valor: number) => MARGEN.izquierda + ((valor - x0) / (x1 - x0)) * (ANCHO - MARGEN.izquierda - MARGEN.derecha);
  const y = (valor: number) => ALTO - MARGEN.abajo - ((valor - y0) / (y1 - y0)) * (ALTO - MARGEN.arriba - MARGEN.abajo);
  const [xu, yu] = [x(umbral_cociente), y(umbral_dano)];

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="w-full" role="img" aria-label="Puntuación de daño frente a FEV1/FVC">
        <rect x={xu} y={MARGEN.arriba} width={ANCHO - MARGEN.derecha - xu} height={yu - MARGEN.arriba} fill="var(--color-dano-suave)" />
        {marcas(x0, x1, 0.1).map((marca) => (
          <g key={`x${marca}`}>
            <line x1={x(marca)} x2={x(marca)} y1={MARGEN.arriba} y2={ALTO - MARGEN.abajo} stroke="var(--color-linea)" />
            <text x={x(marca)} y={ALTO - MARGEN.abajo + 20} textAnchor="middle" fontSize={12} fill="var(--color-tinta-3)">
              {num(marca, 1)}
            </text>
          </g>
        ))}
        {marcas(y0, y1, 1).map((marca) => (
          <g key={`y${marca}`}>
            <line x1={MARGEN.izquierda} x2={ANCHO - MARGEN.derecha} y1={y(marca)} y2={y(marca)} stroke="var(--color-linea)" />
            <text x={MARGEN.izquierda - 10} y={y(marca) + 4} textAnchor="end" fontSize={12} fill="var(--color-tinta-3)">
              {num(marca, 0, true)}
            </text>
          </g>
        ))}
        <line x1={xu} x2={xu} y1={MARGEN.arriba} y2={ALTO - MARGEN.abajo} stroke="var(--color-tinta)" strokeDasharray="2 5" strokeLinecap="round" strokeWidth={1.5} />
        <line x1={xu} x2={ANCHO - MARGEN.derecha} y1={yu} y2={yu} stroke="var(--color-dano)" strokeDasharray="2 5" strokeLinecap="round" strokeWidth={1.5} />
        {normalidad !== null && (
          <>
            <line x1={MARGEN.izquierda} x2={ANCHO - MARGEN.derecha} y1={y(normalidad)} y2={y(normalidad)} stroke="var(--color-dano)" strokeWidth={1} opacity={0.55} />
            <text x={MARGEN.izquierda + 10} y={y(normalidad) - 6} fontSize={12} fill="var(--color-dano-tinta)">
              límite superior de lo normal: {num(normalidad, 2)}
            </text>
          </>
        )}

        <text x={MARGEN.izquierda + 10} y={ALTO - MARGEN.abajo - 29} fontSize={13} fontWeight={600} fill="var(--color-tinta)">
          EPOC
        </text>
        <text x={MARGEN.izquierda + 10} y={ALTO - MARGEN.abajo - 12} fontSize={12} fill="var(--color-tinta-3)">
          FEV1/FVC por debajo de {num(umbral_cociente, 2)}
        </text>
        <text x={ANCHO - MARGEN.derecha - 10} y={MARGEN.arriba + 20} textAnchor="end" fontSize={13} fontWeight={600} fill="var(--color-dano-tinta)">
          Sin obstrucción, con la TC
        </text>
        <text x={ANCHO - MARGEN.derecha - 10} y={MARGEN.arriba + 36} textAnchor="end" fontSize={13} fontWeight={600} fill="var(--color-dano-tinta)">
          parecida a la de la EPOC
        </text>
        <text x={ANCHO - MARGEN.derecha - 10} y={MARGEN.arriba + 53} textAnchor="end" fontSize={12} fill="var(--color-dano-tinta)">
          puntuación de {num(umbral_dano, 2)} o más (modelo final)
        </text>
        <text x={ANCHO - MARGEN.derecha - 10} y={ALTO - MARGEN.abajo - 12} textAnchor="end" fontSize={12} fill="var(--color-tinta-3)">
          Sin obstrucción y con la TC por debajo del umbral
        </text>

        <text x={(MARGEN.izquierda + ANCHO - MARGEN.derecha) / 2} y={ALTO - 8} textAnchor="middle" fontSize={12.5} fill="var(--color-tinta-2)">
          FEV1/FVC tras broncodilatador
        </text>
        <text transform={`translate(16 ${(MARGEN.arriba + ALTO - MARGEN.abajo) / 2}) rotate(-90)`} textAnchor="middle" fontSize={12.5} fill="var(--color-tinta-2)">
          Puntuación de daño en la TC
        </text>

        {sujetos.map((sujeto) => {
          const apagado = filtro !== null && sujeto.clase !== filtro;
          const activo = encima?.id === sujeto.id;
          return (
            <circle
              key={sujeto.id}
              cx={x(sujeto.cociente)}
              cy={y(sujeto.puntuacion)}
              r={activo ? 9 : 6.5}
              fill={COLOR_CLASE[sujeto.clase]}
              stroke="#fff"
              strokeWidth={1.5}
              opacity={apagado ? 0.12 : 1}
              className="cursor-pointer transition-[r,opacity] duration-150"
              onMouseEnter={() => setEncima(sujeto)}
              onMouseLeave={() => setEncima(null)}
              onClick={() => alElegir(sujeto)}
            />
          );
        })}
      </svg>
      {encima && (
        <div
          className="pointer-events-none absolute z-10 w-64 -translate-x-1/2 -translate-y-full rounded-xl border border-linea bg-white p-3 text-xs shadow-lg"
          style={{ left: `${(x(encima.cociente) / ANCHO) * 100}%`, top: `calc(${(y(encima.puntuacion) / ALTO) * 100}% - 14px)` }}
        >
          <p className="flex items-center justify-between font-semibold">
            {encima.id}
            <span className="font-normal text-tinta-3">{NOMBRE_CLASE[encima.clase]}</span>
          </p>
          <p className="mt-1.5 grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 text-tinta-2">
            <span>Puntuación de daño</span>
            <span className="font-medium text-tinta">{num(encima.puntuacion, 2, true)}</span>
            <span>FEV1/FVC</span>
            <span className="font-medium text-tinta">{num(encima.clinica.fev1_fvc, 2)}</span>
            <span>FEV1, % del predicho</span>
            <span className="font-medium text-tinta">{num(encima.clinica.fev1_pct, 0)}</span>
          </p>
          <p className="mt-1.5 text-tinta-3">Clic para abrir el sujeto</p>
        </div>
      )}
    </div>
  );
}
