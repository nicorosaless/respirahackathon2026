"use client";

// Cómo está hecho, en tres diapositivas en vivo: el modelo por dentro, la curva ROC que acaba en sus matrices de
// confusión y la comparación con las alternativas. Las cifras salen de `cohorte` (complejidad, validación y reserva)
// y de `docs/cifras.md`. Las de la ResNet salen de `docs/experimento-resnet.md`, que no está en la exportación.

import { motion } from "motion/react";
import { useMemo } from "react";
import { type Cohorte, validacionDelModelo } from "@/lib/cohorte";
import { num } from "@/lib/formato";
import { Simulado, SUAVE } from "./piezas";
import { Frase } from "./vivo";

/** Aparece cuando toca y se queda. Para bloques HTML; `Paso` de `vivo.tsx` es para el SVG. */
function Bloque({ visible, children, className = "", retraso = 0 }: { visible: boolean; children: React.ReactNode; className?: string; retraso?: number }) {
  return (
    <motion.div
      className={className}
      initial={false}
      animate={{ opacity: visible ? 1 : 0, y: visible ? 0 : "0.6cqw" }}
      transition={{ duration: 0.45, delay: visible ? retraso : 0, ease: SUAVE }}
    >
      {children}
    </motion.div>
  );
}

// El umbral entre vueltas con los 52 controles: `docs/modelo.md`, "De dónde sale 0,48".
const UMBRAL_ENTRE_VUELTAS = "0,45 a 0,50";

/** La franja de lo esperado, en pequeño: la misma idea que la curva de crecimiento, sin ejes. */
function FranjaPequena() {
  return (
    <svg viewBox="0 0 120 64" className="h-[6cqw] w-auto" aria-hidden>
      <polygon points="4,40 116,22 116,46 4,62" fill="#ebe8e1" />
      <line x1={4} y1={51} x2={116} y2={34} stroke="#8e8e96" strokeWidth={1.5} strokeDasharray="3 4" />
      {[
        [18, 50],
        [34, 44],
        [52, 46],
        [70, 38],
        [90, 36],
        [104, 32],
      ].map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r={3.2} fill="#cfcdc7" />
      ))}
      <circle cx={62} cy={60} r={4.5} fill="#16161a" />
    </svg>
  );
}

/** Una fracción de verdad: numerador sobre denominador, con su raya. */
function Fraccion({ arriba, abajo }: { arriba: React.ReactNode; abajo: React.ReactNode }) {
  return (
    <span className="inline-flex flex-col items-center align-middle leading-[1.2]">
      <span className="px-[0.3em] pb-[0.15em]">{arriba}</span>
      <span className="w-full border-t-[0.12cqw] border-tinta px-[0.3em] pt-[0.15em] text-center">{abajo}</span>
    </span>
  );
}

// 4. El modelo por dentro: lo esperado, el z, la puntuación y el umbral. Fusiona la antigua curva de crecimiento.
export function ElModelo({ cohorte, clic }: { cohorte: Cohorte; clic: number }) {
  const umbral = num(cohorte.umbral_dano, 2);
  const tarjeta = "flex flex-col rounded-[1.1cqw] border border-linea bg-white px-[1.5cqw] pt-[1.3cqw] pb-[1.4cqw]";
  const paso = "text-[0.95cqw] font-medium tracking-[0.05em] text-tinta-3 uppercase";
  const titulo = "mt-[0.4cqw] text-[1.7cqw] leading-[1.15] font-semibold tracking-[-0.02em]";
  const formula = "mt-[1.2cqw] flex items-center gap-[0.5cqw] text-[1.35cqw] font-medium whitespace-nowrap tabular-nums";
  const nota = "mt-auto pt-[1cqw] text-[1.1cqw] leading-[1.35] text-tinta-2";
  const flecha = <span className="self-center text-[2cqw] text-tinta-3">→</span>;

  return (
    <>
      <Frase>Modelo seleccionado.</Frase>
      <div className="absolute top-[17.6cqw] right-[6cqw] left-[6cqw] grid h-[24cqw] grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] gap-[1cqw]">
        <Bloque visible className={tarjeta}>
          <p className={paso}>1 · Lo esperado</p>
          <p className={titulo}>Para alguien como esa persona</p>
          <div className="mt-[0.9cqw]">
            <FranjaPequena />
          </div>
          <p className={nota}>Regresión lineal ajustada con los controles: edad, sexo, talla, volumen pulmonar, tabaco activo y kVp.</p>
        </Bloque>
        {flecha}
        <Bloque visible={clic >= 1} className={tarjeta}>
          <p className={paso}>2 · Cuánto se aparta</p>
          <p className={titulo}>Un z por medida</p>
          <div className={formula}>
            <span className="italic">z</span> =
            <Fraccion arriba="medido − esperado" abajo="dispersión" />
          </div>
          <p className={nota}>Dispersión robusta (MAD). Cada control se compara con un ajuste hecho sin él.</p>
        </Bloque>
        {flecha}
        <Bloque visible={clic >= 1} retraso={0.15} className={tarjeta}>
          <p className={paso}>3 · Puntuación</p>
          <p className={titulo}>Media de los dos z</p>
          <div className={formula}>
            <Fraccion
              arriba={
                <>
                  <span className="italic">z</span> enfisema + <span className="italic">z</span> árbol
                </>
              }
              abajo="2"
            />
          </div>
          <p className={nota}>Sube con más enfisema y con menos árbol bronquial del esperado.</p>
        </Bloque>
        {flecha}
        <Bloque visible={clic >= 2} className={tarjeta}>
          <p className={paso}>4 · Umbral</p>
          <p className={titulo}>Puntuación ≥ {umbral}</p>
          <p className="mt-[1cqw] self-start rounded-full bg-dano-suave px-[1cqw] py-[0.35cqw] text-[1.2cqw] font-semibold text-dano-tinta">TC alterada</p>
          <p className={nota}>
            El punto de la curva ROC que maximiza sensibilidad + especificidad (índice de Youden) entre EPOC y control. Se movió de {UMBRAL_ENTRE_VUELTAS} entre vueltas.
          </p>
        </Bloque>
      </div>
      <Bloque visible={clic >= 2} retraso={0.3} className="absolute right-[6cqw] bottom-[4.2cqw] left-[6cqw] rounded-[1.2cqw] bg-fondo px-[2.2cqw] py-[1.4cqw] text-[1.55cqw] leading-[1.35]">
        <strong className="font-semibold">TC alterada:</strong> se aparta de lo esperado hacia el daño (más enfisema o menos árbol). Lo esperado se aprende con los controles; el umbral, con EPOC frente a control.
      </Bloque>
    </>
  );
}

// 8. De la AUC a la matriz de confusión. La curva se calcula con la puntuación fuera de muestra de cada sujeto.
interface Cuenta {
  vp: number;
  fn: number;
  fp: number;
  vn: number;
}

interface Curva {
  puntos: [number, number][];
  auc: number;
  /** Con el umbral de cribado: que no se escape ninguna EPOC. */
  cribado: Cuenta;
  /** Con el umbral del modelo, el de la regla de pre-EPOC. */
  diagnostico: Cuenta;
}

// El umbral de cribado, elegido con los 80 para no dejar escapar ninguna EPOC fuera de muestra.
const UMBRAL_DE_CRIBADO = 0.2;

function curvaROC(cohorte: Cohorte): Curva | null {
  const sujetos = cohorte.sujetos.filter((s): s is typeof s & { fuera_de_muestra: number } => typeof s.fuera_de_muestra === "number");
  const casos = sujetos.filter((s) => s.caso).map((s) => s.fuera_de_muestra);
  const sanos = sujetos.filter((s) => !s.caso).map((s) => s.fuera_de_muestra);
  if (casos.length === 0 || sanos.length === 0) return null;
  const cortes = [...new Set(sujetos.map((s) => s.fuera_de_muestra))].sort((a, b) => b - a);
  const puntos: [number, number][] = [[0, 0], ...cortes.map((c): [number, number] => [sanos.filter((v) => v >= c).length / sanos.length, casos.filter((v) => v >= c).length / casos.length])];
  let pares = 0;
  for (const p of casos) for (const n of sanos) pares += p > n ? 1 : p === n ? 0.5 : 0;
  const contar = (u: number): Cuenta => {
    const vp = casos.filter((v) => v >= u).length;
    const fp = sanos.filter((v) => v >= u).length;
    return { vp, fn: casos.length - vp, fp, vn: sanos.length - fp };
  };
  return { puntos, auc: pares / (casos.length * sanos.length), cribado: contar(UMBRAL_DE_CRIBADO), diagnostico: contar(cohorte.umbral_dano) };
}

function Casilla({ valor, nombre, que, fuerte = false, grande = false }: { valor: number; nombre: string; que: string; fuerte?: boolean; grande?: boolean }) {
  return (
    <div className={`flex flex-col justify-center rounded-[0.9cqw] px-[1.3cqw] py-[0.8cqw] ${fuerte ? "border-[0.22cqw] border-tinta bg-white" : "border border-linea bg-white"}`}>
      <p className={`leading-none font-semibold tracking-[-0.04em] tabular-nums ${grande ? "text-[5.2cqw]" : "text-[3cqw]"}`}>{valor}</p>
      <p className="mt-[0.5cqw] text-[1.15cqw] leading-[1.2] font-semibold">{nombre}</p>
      <p className="text-[1cqw] leading-[1.25] text-tinta-2">{que}</p>
    </div>
  );
}

function Matriz({ titulo, detalle, vp, fn, fp, vn, umbral, destacarFN = false }: { titulo: string; detalle: string; vp: number; fn: number; fp: number; vn: number; umbral: string; destacarFN?: boolean }) {
  return (
    <div className="w-[40cqw]">
      <p className="text-[1.7cqw] leading-[1.15] font-semibold tracking-[-0.02em]">{titulo}</p>
      <p className="mt-[0.2cqw] mb-[0.6cqw] text-[1.1cqw] text-tinta-2">{detalle}</p>
      <div className="grid grid-cols-[8.5cqw_1fr_1fr] gap-[0.7cqw]">
        <span />
        <p className="text-center text-[1cqw] font-medium text-tinta-3">TC ≥ {umbral}</p>
        <p className="text-center text-[1cqw] font-medium text-tinta-3">TC por debajo</p>
        <p className="self-center text-[1.15cqw] leading-[1.2] font-semibold">Con EPOC ({vp + fn})</p>
        <Casilla valor={vp} nombre="Verdaderos positivos" que="EPOC, y la TC lo ve" />
        <Casilla valor={fn} nombre="Falsos negativos" que="EPOC que se escapa" fuerte={destacarFN} grande={destacarFN} />
        <p className="self-center text-[1.15cqw] leading-[1.2] font-semibold">Sin EPOC ({fp + vn})</p>
        <Casilla valor={fp} nombre="Falsos positivos" que="sin EPOC, TC alterada" />
        <Casilla valor={vn} nombre="Verdaderos negativos" que="sin EPOC, TC normal" />
      </div>
    </div>
  );
}

export function CurvaYMatriz({ cohorte, clic }: { cohorte: Cohorte; clic: number }) {
  const curva = useMemo(() => curvaROC(cohorte), [cohorte]);
  const auc = validacionDelModelo(cohorte)?.auc ?? curva?.auc;
  const reserva = cohorte.reserva;
  const umbral = num(cohorte.umbral_dano, 2);
  const cribado = num(UMBRAL_DE_CRIBADO, 2);
  const sitio = (c: Cuenta) => [c.fp / (c.fp + c.vn), c.vp / (c.vp + c.fn)];
  // El lienzo de la curva: 0..100 en los dos ejes, con el origen abajo a la izquierda.
  const xy = ([x, y]: number[]) => `${8 + x * 90},${94 - y * 90}`;

  return (
    <>
      <Frase>Para cribar no se nos escapa nadie: umbral {cribado}.</Frase>
      <p className="absolute top-[17.2cqw] left-[6cqw] max-w-[86cqw] text-[1.55cqw] leading-[1.35] text-tinta-2">
        {auc !== undefined && (
          <>
            <strong className="font-semibold text-tinta">AUC {num(auc, 2)}:</strong> si coges al azar una persona con EPOC y una sin ella, en {num(auc * 100, 0)} de cada 100 parejas la de EPOC tiene la puntuación más alta.
          </>
        )}
      </p>

      {curva ? (
        <>
          <motion.div className="absolute top-[21.5cqw] left-[6cqw] h-[29cqw] w-[34cqw]" initial={false} animate={{ opacity: clic >= 2 ? 0 : 1 }} transition={{ duration: 0.45, ease: SUAVE }}>
            <svg viewBox="0 0 100 100" className="size-full overflow-visible" role="img" aria-label="Curva ROC fuera de muestra, con el punto del umbral marcado.">
              <motion.polygon points={[...curva.puntos.map(xy), xy([1, 0])].join(" ")} fill="#ebe8e1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 1.2 }} />
              <text x={60} y={80} textAnchor="middle" fontSize={4.2} fontWeight={600} fill="#55555e">
                AUC = área bajo la curva
              </text>
              <line x1={8} y1={94} x2={98} y2={4} stroke="#d8d5ce" strokeWidth={0.4} strokeDasharray="1.5 1.5" />
              <line x1={8} y1={94} x2={98} y2={94} stroke="#d8d5ce" strokeWidth={0.5} />
              <line x1={8} y1={4} x2={8} y2={94} stroke="#d8d5ce" strokeWidth={0.5} />
              <motion.polyline
                points={curva.puntos.map(xy).join(" ")}
                fill="none"
                stroke="#16161a"
                strokeWidth={1.1}
                strokeLinejoin="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.2, ease: SUAVE, delay: 0.2 }}
              />
              {[
                { c: curva.cribado, nombre: `cribado ${cribado}`, desde: 1, fuerte: true },
                { c: curva.diagnostico, nombre: `diagnóstico ${umbral}`, desde: 2, fuerte: false },
              ].map(({ c, nombre, desde, fuerte }) => {
                const [px, py] = sitio(c);
                return (
                  <motion.g key={nombre} initial={false} animate={{ opacity: clic >= desde ? 1 : 0 }} transition={{ duration: 0.4 }}>
                    <circle cx={8 + px * 90} cy={94 - py * 90} r={2.6} fill={fuerte ? "#16161a" : "#fbfaf7"} stroke="#16161a" strokeWidth={0.8} />
                    <text x={8 + px * 90 + 4} y={94 - py * 90 + 7} fontSize={3.6} fontWeight={600} fill="#16161a">
                      {nombre}
                    </text>
                  </motion.g>
                );
              })}
            </svg>
            <p className="absolute bottom-[-2.4cqw] left-[3cqw] text-[1cqw] text-tinta-3">controles por encima del umbral →</p>
            <p className="absolute top-[0cqw] left-[-0.4cqw] origin-top-left translate-y-[20cqw] -rotate-90 text-[1cqw] whitespace-nowrap text-tinta-3">EPOC por encima del umbral →</p>
          </motion.div>

          <motion.div
            className="absolute top-[21.5cqw]"
            initial={false}
            animate={{ left: clic >= 2 ? "6cqw" : "52cqw", opacity: clic >= 1 ? 1 : 0 }}
            transition={{ duration: 0.7, ease: SUAVE }}
          >
            <Matriz
              titulo={`Cribado: umbral ${cribado}`}
              detalle={`Fuera de muestra, los ${curva.cribado.vp + curva.cribado.fn + curva.cribado.fp + curva.cribado.vn}: cada persona, puntuada por un modelo que no la vio.`}
              umbral={cribado}
              {...curva.cribado}
              destacarFN
            />
          </motion.div>
          <Bloque visible={clic >= 2} retraso={0.35} className="absolute top-[21.5cqw] left-[52cqw] origin-top-left scale-[0.8]">
            <Matriz titulo={`Umbral ${umbral}`} detalle="Para la regla de pre-EPOC: equilibrio." umbral={umbral} {...curva.diagnostico} />
          </Bloque>
        </>
      ) : (
        <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Pendiente: esta cohorte no trae la puntuación fuera de muestra de cada sujeto.</p>
      )}

      {reserva && (
        <p className="absolute bottom-[3.2cqw] left-[52cqw] max-w-[40cqw] text-[1cqw] leading-[1.35] text-tinta-3">
          Umbral de cribado elegido con estos {cohorte.comprobaciones.sujetos}; en la reserva, con el umbral del modelo, {reserva.sensibilidad.de - reserva.sensibilidad.aciertos} de {reserva.sensibilidad.de} EPOC se escaparon.
        </p>
      )}
      <Simulado cohorte={cohorte} que="La curva y la matriz de fuera de muestra" />
    </>
  );
}

// 9. Por qué este modelo: frente a la clínica, a aprender pesos con todas las medidas y a una red profunda.
// `docs/experimento-resnet.md`: ResNet-50 RadImageNet con etiquetas débiles, en una base pública de enfisema.
const RESNET = { auc: "0,81", conPerc15: "−0,95" };
// EPOC de 28 que se escapan si cada modelo deja por debajo al 75 % de los controles (`scripts/complexity_cv.py`, media de 5 repeticiones).
const ESCAPAN: Record<string, string> = { "clínica sola": "15,8", "logística con todas las medidas de TC": "5,6", "2 medidas": "4,6" };

export function PorQueEste({ cohorte, clic }: { cohorte: Cohorte; clic: number }) {
  const modelos = cohorte.complejidad?.modelos ?? [];
  const buscar = (nombre: string) => modelos.find((m) => m.modelo === nombre);
  const filas = [
    { nombre: "Clínica sola", detalle: "edad, sexo, talla, IMC, tabaco", m: buscar("clínica sola"), escapan: ESCAPAN["clínica sola"] },
    { nombre: "Las 27 medidas, pesos aprendidos", detalle: "regresión logística", m: buscar("logística con todas las medidas de TC"), escapan: ESCAPAN["logística con todas las medidas de TC"] },
    { nombre: "MAPS: 2 medidas", detalle: "el modelo", m: buscar("2 medidas"), nuestro: true, escapan: ESCAPAN["2 medidas"] },
  ];
  const conClinica = buscar("clínica y las dos medidas de TC");
  const ocho = buscar("8 medidas");
  const desde = 0.5;
  const ancho = (auc: number) => `${((auc - desde) / (1 - desde)) * 100}%`;

  return (
    <>
      <Frase>Más simple, y mejor que las alternativas.</Frase>
      {modelos.length === 0 ? (
        <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Pendiente: esta cohorte no trae la comparación de modelos.</p>
      ) : (
        <div className="absolute top-[16cqw] left-[6cqw] w-[52cqw]">
          <div className="grid grid-cols-[17cqw_1fr_7cqw] items-end gap-x-[1.4cqw] pb-[0.6cqw] text-[1cqw] text-tinta-3">
            <span />
            <span>AUC fuera de muestra</span>
            <span className="text-right">EPOC que se escapan (de 28)</span>
          </div>
          {filas.map((f, i) => (
            <div key={f.nombre} className="grid grid-cols-[17cqw_1fr_7cqw] items-center gap-x-[1.4cqw] border-t border-linea py-[1.2cqw]">
              <div>
                <p className={`text-[1.45cqw] leading-[1.2] ${f.nuestro ? "font-semibold" : "font-medium"}`}>{f.nombre}</p>
                <p className="text-[1.05cqw] text-tinta-3">{f.detalle}</p>
              </div>
              <div className="flex items-center gap-[1cqw]">
                <span className="relative h-[1.6cqw] flex-1 rounded-full bg-fondo">
                  <motion.span
                    className={`absolute inset-y-0 left-0 origin-left rounded-full ${f.nuestro ? "bg-tinta" : "bg-[#cfcdc7]"}`}
                    style={{ width: f.m ? ancho(f.m.auc) : 0 }}
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ delay: 0.3 + 0.2 * i, duration: 0.6, ease: SUAVE }}
                  />
                </span>
                <strong className={`w-[5.4cqw] text-right text-[2.6cqw] leading-none font-semibold tracking-[-0.03em] tabular-nums ${f.nuestro ? "" : "text-tinta-2"}`}>{num(f.m?.auc, 2)}</strong>
              </div>
              <strong className={`text-right text-[2cqw] leading-none font-semibold tabular-nums ${f.nuestro ? "" : "text-tinta-2"}`}>{f.escapan}</strong>
            </div>
          ))}
          <div className="border-t border-linea pt-[1.2cqw] text-[1.3cqw] leading-[1.4] text-tinta-2">
            {conClinica && (
              <p>
                <strong className="font-semibold text-tinta">Con la clínica añadida, {num(conClinica.auc, 2)}.</strong>
              </p>
            )}
            <p className="mt-[0.3cqw]">El AUC no depende de dónde se ponga el umbral: compara modelos de forma justa. Los que se escapan, con todos marcando al mismo 25 % de los controles.</p>
            {ocho && <p className="mt-[0.3cqw]">Sumar medidas de una en una tampoco ayuda: con 8, {num(ocho.auc, 2)}. Con 80 personas, cada medida de más aprende ruido.</p>}
          </div>
        </div>
      )}
      <Bloque visible={clic >= 1} className="absolute top-[16cqw] right-[6cqw] w-[28cqw] rounded-[1.1cqw] border border-linea bg-white px-[1.8cqw] pt-[1.5cqw] pb-[1.6cqw]">
        <p className="text-[0.95cqw] font-medium tracking-[0.05em] text-tinta-3 uppercase">Lo probamos antes</p>
        <p className="mt-[0.4cqw] text-[1.7cqw] leading-[1.15] font-semibold tracking-[-0.02em]">Una red profunda (ResNet-50)</p>
        <ul className="mt-[1cqw] flex flex-col gap-[0.7cqw] text-[1.2cqw] leading-[1.35] text-tinta-2">
          <li>
            Detecta enfisema mínimo: <strong className="font-semibold text-tinta">AUC {RESNET.auc}</strong>.
          </li>
          <li>Pero aprende sobre todo densidad: correlación {RESNET.conPerc15} con Perc15.</li>
          <li>No supera a la densitometría y no funciona en otro escáner.</li>
        </ul>
        <p className="mt-[1.2cqw] border-t border-linea pt-[1cqw] text-[1.25cqw] leading-[1.35] font-semibold">Por eso nos quedamos con dos medidas que se pueden leer.</p>
        <p className="mt-[0.5cqw] text-[0.95cqw] text-tinta-3">En una base pública de enfisema, con etiquetas débiles.</p>
      </Bloque>
    </>
  );
}
