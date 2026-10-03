"use client";

// Lo que explica la puntuación de una persona: de qué sale (la cascada), dónde queda entre los 80 y cómo está cada lóbulo.

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { type Capas, CorteTC, opacidadDano, TINTE_DESDE } from "@/components/plataforma/CorteTC";
import { COLOR_CLASE } from "@/components/ui";
import { type Cohorte, conPuntuacion, LOBULOS, NOMBRE_LOBULO, type Sujeto } from "@/lib/cohorte";
import { metros, num } from "@/lib/formato";
import type { Lectura } from "@/lib/inferencia";

const DESPLAZAMIENTO = { duration: 0.8, ease: [0.22, 1, 0.36, 1] as const };

/** De 0 a la puntuación: cuánto suma el enfisema y cuánto el árbol bronquial. Cada uno pesa la mitad. */
export function Cascada({ lectura }: { lectura: Lectura }) {
  const { z, valores, esperado, puntuacion, umbral } = lectura;
  if (puntuacion === null || z.enfisema === null || z.via === null) {
    return <p className="rounded-md bg-fondo px-4 py-3 text-sm text-tinta-2">Sin las dos desviaciones no se puede desglosar la puntuación.</p>;
  }
  const [enfisema, via] = [z.enfisema / 2, z.via / 2];
  const pasos = [
    { nombre: "Lo esperado", desde: 0, hasta: 0, aporte: null, detalle: "una persona como ella" },
    { nombre: "Enfisema", desde: 0, hasta: enfisema, aporte: enfisema, detalle: `${num(valores.laa950_smooth, 2)} % frente a ${num(esperado.laa950_smooth, 2)} %` },
    { nombre: "Árbol bronquial", desde: enfisema, hasta: enfisema + via, aporte: via, detalle: `${metros(valores.via_longitud_mm)} frente a ${metros(esperado.via_longitud_mm)}` },
    { nombre: "Puntuación", desde: 0, hasta: puntuacion, aporte: null, detalle: "la media de las dos" },
  ];
  const extremos = [0, enfisema, enfisema + via, puntuacion, umbral];
  const [z0, z1] = [Math.min(-0.5, ...extremos) - 0.2, Math.max(1.5, ...extremos) + 0.25];
  const x = (valor: number) => ((valor - z0) / (z1 - z0)) * 100;
  const colorAporte = (aporte: number) => (aporte > 0 ? "bg-dano" : "bg-control");
  // La pista de las barras va entre la columna de los nombres y la de los valores; las líneas de los umbrales la cruzan entera.
  const columnas = "grid grid-cols-[6.5rem_1fr_8.75rem] gap-x-3";
  const pista = "absolute inset-y-0 left-[calc(6.5rem+0.75rem)] right-[calc(8.75rem+0.75rem)]";

  return (
    <div className="rounded-md border border-linea px-4 pt-3 pb-2.5">
      <p className="text-sm font-semibold">Por qué esta puntuación</p>
      <p className="mt-0.5 text-xs leading-snug text-tinta-3">Parte de 0: lo esperado para alguien de su edad, sexo, talla, volumen pulmonar, tabaco y kVp. Cada medida suma la mitad de su desviación.</p>
      <div className="relative mt-2 pt-5 pb-4">
        <div className={pista} aria-hidden>
          <div className="absolute top-5 bottom-4 right-0 bg-dano-suave" style={{ left: `${x(umbral)}%` }} />
          <div className="absolute top-5 bottom-4 w-px bg-tinta-3" style={{ left: `${x(0)}%` }} />
          <span className="absolute bottom-0 -translate-x-1/2 text-[11px] text-tinta-3" style={{ left: `${x(0)}%` }}>
            0
          </span>
          <div className="absolute top-5 bottom-4 border-l-[1.5px] border-dashed border-dano" style={{ left: `${x(umbral)}%` }} />
          <span className="absolute top-0 pl-1 text-[11px] font-medium whitespace-nowrap text-dano-tinta" style={{ left: `${x(umbral)}%` }}>
            umbral {num(umbral, 2)}
          </span>
        </div>
        {pasos.map((paso, i) => {
          const final = i === pasos.length - 1;
          const [izquierda, derecha] = [Math.min(paso.desde, paso.hasta), Math.max(paso.desde, paso.hasta)];
          const relleno = final ? (lectura.dano_tc ? "bg-dano" : "bg-tinta") : paso.aporte !== null ? colorAporte(paso.aporte) : "bg-tinta";
          return (
            <div key={paso.nombre} className={`${columnas} relative h-10 items-center`}>
              <span className={`text-sm ${final ? "font-semibold" : "font-medium"}`}>{paso.nombre}</span>
              <span className="relative h-full">
                {i > 0 && !final && <span className="absolute -top-2 h-4 border-l border-dashed border-tinta-3" style={{ left: `${x(paso.desde)}%` }} />}
                {paso.aporte === null && !final ? (
                  <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-tinta" style={{ left: `${x(0)}%` }} />
                ) : (
                  <motion.span
                    className={`absolute top-1/2 h-[18px] -translate-y-1/2 rounded ${relleno}`}
                    initial={false}
                    animate={{ left: `${x(izquierda)}%`, width: `max(${x(derecha) - x(izquierda)}%, 2px)` }}
                    transition={DESPLAZAMIENTO}
                  />
                )}
              </span>
              <span className="leading-tight">
                <span className={`block font-semibold tabular-nums ${final ? `text-lg ${lectura.dano_tc ? "text-dano-tinta" : ""}` : `text-base ${paso.aporte !== null && paso.aporte < 0 ? "text-tinta-3" : ""}`}`}>
                  {paso.aporte !== null ? num(paso.aporte, 2, true) : final ? num(puntuacion, 2, true) : "0"}
                </span>
                <span className="block text-[11px] whitespace-nowrap text-tinta-3">{paso.detalle}</span>
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-xs leading-snug text-tinta-3">Naranja: suma hacia la EPOC. Gris: resta. En el árbol, menos longitud de la esperada suma.</p>
    </div>
  );
}

const D = { ancho: 520, alto: 330, izquierda: 52, derecha: 12, arriba: 34, abajo: 40 };

/** La nube de los 80, puntuación frente a FEV1/FVC, con esta persona resaltada. Al cambiar de persona, el punto se mueve. */
export function DondeEsta({ cohorte, sujeto }: { cohorte: Cohorte; sujeto: Sujeto }) {
  const puntos = conPuntuacion(cohorte).flatMap((s) => (s.clinica.fev1_fvc === null ? [] : [{ ...s, cociente: s.clinica.fev1_fvc }]));
  const yo = puntos.find((s) => s.id === sujeto.id);
  if (puntos.length === 0) return null;
  const { umbral_dano, umbral_cociente } = cohorte;
  const [x0, x1] = [Math.min(...puntos.map((s) => s.cociente)) - 0.02, Math.max(...puntos.map((s) => s.cociente)) + 0.02];
  const [y0, y1] = [Math.min(...puntos.map((s) => s.puntuacion)) - 0.3, Math.max(...puntos.map((s) => s.puntuacion)) + 0.3];
  const x = (v: number) => D.izquierda + ((v - x0) / (x1 - x0)) * (D.ancho - D.izquierda - D.derecha);
  const y = (v: number) => D.alto - D.abajo - ((v - y0) / (y1 - y0)) * (D.alto - D.arriba - D.abajo);
  const [xu, yu] = [x(umbral_cociente), y(umbral_dano)];
  // Su puesto entre quienes no tienen obstrucción (la referencia del modelo), sin contarse a sí misma.
  const controles = puntos.filter((s) => !s.caso && s.id !== sujeto.id);
  const porDebajo = sujeto.puntuacion === null ? 0 : controles.filter((s) => s.puntuacion < (sujeto.puntuacion as number)).length;
  const percentil = controles.length > 0 ? Math.round((porDebajo / controles.length) * 100) : null;

  return (
    <div>
      <p className="text-lg font-semibold tracking-tight">Dónde está entre los {puntos.length}</p>
      <p className="text-sm text-tinta-3">Puntuación de daño de la TC frente a FEV1/FVC. Cada punto es una persona.</p>
      <svg viewBox={`0 0 ${D.ancho} ${D.alto}`} className="mt-1 w-full" role="img" aria-label="Su punto en la nube de la cohorte">
        <rect x={xu} y={D.arriba} width={D.ancho - D.derecha - xu} height={Math.max(yu - D.arriba, 0)} fill="var(--color-dano-suave)" />
        {[0.4, 0.5, 0.6, 0.7, 0.8].filter((m) => m >= x0 && m <= x1).map((m) => (
          <text key={m} x={x(m)} y={D.alto - D.abajo + 16} textAnchor="middle" fontSize={12} fill="var(--color-tinta-3)">
            {num(m, 1)}
          </text>
        ))}
        {[-2, 0, 2, 4, 6].filter((m) => m >= y0 && m <= y1).map((m) => (
          <g key={m}>
            <line x1={D.izquierda} x2={D.ancho - D.derecha} y1={y(m)} y2={y(m)} stroke="var(--color-linea)" />
            <text x={D.izquierda - 8} y={y(m) + 4} textAnchor="end" fontSize={12} fill="var(--color-tinta-3)">
              {num(m, 0, true)}
            </text>
          </g>
        ))}
        <text x={(D.izquierda + D.ancho) / 2} y={D.alto - 4} textAnchor="middle" fontSize={13} fill="var(--color-tinta-2)">
          FEV1/FVC
        </text>
        <text transform={`translate(14 ${(D.arriba + D.alto - D.abajo) / 2}) rotate(-90)`} textAnchor="middle" fontSize={13} fill="var(--color-tinta-2)">
          TC más alterada →
        </text>
        <text x={xu} y={D.arriba - 20} textAnchor="middle" fontSize={12} fontWeight={600} fill="var(--color-tinta)">
          {num(umbral_cociente, 2)}
        </text>
        <text x={xu - 7} y={D.arriba - 5} textAnchor="end" fontSize={12.5} fontWeight={600} fill="var(--color-tinta)">
          EPOC
        </text>
        <text x={xu} y={D.arriba - 5} textAnchor="middle" fontSize={12.5} fill="var(--color-tinta-3)">
          |
        </text>
        <text x={xu + 7} y={D.arriba - 5} fontSize={12.5} fontWeight={600} fill="var(--color-tinta)">
          no es EPOC
        </text>
        {yu - D.arriba > 24 && (
          <text x={D.ancho - D.derecha - 6} y={D.arriba + 16} textAnchor="end" fontSize={12.5} fontWeight={600} fill="var(--color-dano-tinta)">
            zona de posible pre-EPOC
          </text>
        )}
        <line x1={xu} x2={xu} y1={D.arriba} y2={D.alto - D.abajo} stroke="var(--color-tinta)" strokeDasharray="2 4" strokeLinecap="round" />
        <line x1={D.izquierda} x2={D.ancho - D.derecha} y1={yu} y2={yu} stroke="var(--color-dano)" strokeDasharray="2 4" strokeLinecap="round" strokeWidth={1.5} />
        <text x={D.ancho - D.derecha - 6} y={yu - 6} textAnchor="end" fontSize={12} fill="var(--color-dano-tinta)">
          umbral {num(umbral_dano, 2)}
        </text>
        {puntos.map((s) => (
          <circle key={s.id} cx={x(s.cociente)} cy={y(s.puntuacion)} r={4.5} fill={COLOR_CLASE[s.clase]} opacity={s.id === sujeto.id ? 0 : 0.45} />
        ))}
        {yo && (
          <motion.g initial={false} animate={{ x: x(yo.cociente), y: y(yo.puntuacion) }} transition={DESPLAZAMIENTO}>
            <circle r={14} fill="none" stroke="var(--color-tinta)" strokeWidth={2} />
            <circle r={8.5} fill={COLOR_CLASE[yo.clase]} stroke="#fff" strokeWidth={1.5} />
          </motion.g>
        )}
      </svg>
      {!yo ? (
        <p className="mt-1 text-xs text-tinta-3">Sin puntuación o sin FEV1/FVC no hay dónde ponerla.</p>
      ) : (
        percentil !== null && (
          <p className="mt-2 text-base leading-snug text-tinta-2">
            Su puntuación supera la de <strong className="font-semibold text-tinta">{porDebajo}</strong> de {sujeto.caso ? "las " : "las otras "}
            {controles.length} personas sin obstrucción: percentil{" "}
            <strong className="font-semibold text-tinta">{percentil}</strong>.
          </p>
        )
      )}
    </div>
  );
}

const TENIDA: Capas = { lobulos: true, tinte: true, arbol: false, rotulos: "desviaciones", colores: true, enfisema: true };
const SOLO_CONTORNO: Capas = { lobulos: true, tinte: false, arbol: false, rotulos: "ninguno" };

/** Sube de 0 a la cifra real mientras el árbol se dibuja, y se queda en ella. */
function Contador({ hasta, duracion }: { hasta: number; duracion: number }) {
  const [valor, setValor] = useState(0);
  useEffect(() => {
    let marco = 0;
    const inicio = performance.now();
    const paso = (ahora: number) => {
      const t = Math.min((ahora - inicio) / duracion, 1);
      setValor(hasta * (1 - (1 - t) ** 3));
      if (t < 1) marco = requestAnimationFrame(paso);
    };
    marco = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(marco);
  }, [hasta, duracion]);
  return <>{metros(valor)}</>;
}

/** El corte de la persona con dos vistas: la segmentación con el árbol, o cada lóbulo teñido por su enfisema. Debajo, la tabla lobular. */
export function MapaLobular({ cohorte, sujeto }: { cohorte: Cohorte; sujeto: Sujeto }) {
  const [vista, setVista] = useState<"arbol" | "lobulos">("lobulos");
  const imagen = sujeto.imagen ? cohorte.imagenes[sujeto.imagen] : undefined;
  const pildora = (activa: boolean) =>
    `h-7 cursor-pointer rounded-full border px-2.5 text-xs font-medium transition-colors ${activa ? "border-tinta bg-tinta text-white" : "border-linea-2 bg-white text-tinta hover:border-tinta"}`;
  const tenidos = LOBULOS.filter((l) => sujeto.lobulos[l] >= TINTE_DESDE).length;

  return (
    <div>
      <div className="mb-2 flex gap-1.5">
        <button type="button" className={pildora(vista === "lobulos")} onClick={() => setVista("lobulos")}>
          Lóbulos y enfisema
        </button>
        <button type="button" className={pildora(vista === "arbol")} onClick={() => setVista("arbol")} disabled={!sujeto.arbol}>
          Árbol bronquial
        </button>
      </div>
      {!imagen || !sujeto.imagen ? (
        <p className="grid aspect-square place-items-center rounded-md bg-fondo p-6 text-center text-sm text-tinta-3">Esta persona no tiene vista previa de la TC. Las medidas sí están.</p>
      ) : (
        <div className="relative">
          <CorteTC clave={sujeto.imagen} imagen={imagen} corte={Math.floor(imagen.cortes.length / 2)} z={sujeto.lobulos} capas={vista === "lobulos" ? TENIDA : SOLO_CONTORNO} />
          {vista === "arbol" && sujeto.arbol && (
            <>
              <motion.div
                key={`${sujeto.id}-arbol`}
                className="pointer-events-none absolute inset-0 bg-[#4f8fe0]"
                style={{ maskImage: `url(/data/previews/${sujeto.imagen}-arbol.png)`, maskMode: "luminance", maskSize: "100% 100%", WebkitMaskImage: `url(/data/previews/${sujeto.imagen}-arbol.png)`, WebkitMaskSize: "100% 100%" }}
                initial={{ clipPath: "inset(0 0 100% 0)" }}
                animate={{ clipPath: "inset(0 0 0% 0)" }}
                transition={{ duration: 2.4, ease: [0.4, 0, 0.2, 1] }}
              />
              <p key={`${sujeto.id}-cifra`} className="absolute right-3 bottom-3 rounded bg-white/90 px-2.5 py-1 text-right">
                <span className="block text-2xl font-semibold tracking-tight tabular-nums">
                  {sujeto.valores.via_longitud_mm === null ? "sin dato" : <Contador hasta={sujeto.valores.via_longitud_mm} duracion={2400} />}
                </span>
                <span className="block text-[11px] text-tinta-3">de árbol bronquial medido</span>
              </p>
            </>
          )}
        </div>
      )}
      <div className="mt-2.5 grid grid-cols-5 gap-1">
        {LOBULOS.map((lobulo) => {
          const z = sujeto.lobulos[lobulo];
          const alfa = opacidadDano(z);
          return (
            <div key={lobulo} className="rounded border border-linea px-1.5 py-1 text-center" style={{ background: alfa > 0 ? `rgb(246 130 31 / ${alfa})` : undefined }} title={NOMBRE_LOBULO[lobulo]}>
              <span className={`block text-[11px] font-semibold ${alfa > 0.4 ? "text-white" : "text-tinta-2"}`}>{lobulo}</span>
              <span className={`block text-sm font-semibold tabular-nums ${alfa > 0.4 ? "text-white" : "text-tinta"}`}>{num(z, 1, true)}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-1.5 text-xs leading-snug text-tinta-3">
        {vista === "lobulos"
          ? `En rojo, los puntos de este corte por debajo de −950 HU tras el suavizado de 1 mm; la cifra se mide en todo el pulmón. Cada lóbulo en su color, con su desviación del enfisema. Se tiñe de naranja desde ${num(TINTE_DESDE, 0, true)}: más enfisema del esperado. ${tenidos === 0 ? "Ningún lóbulo llega." : tenidos === 1 ? "Llega un lóbulo." : `Llegan ${tenidos} lóbulos.`}`
          : "En azul, el árbol bronquial segmentado, de la tráquea hacia abajo. La cifra es la suma de las ramas que se ven."}
      </p>
    </div>
  );
}
