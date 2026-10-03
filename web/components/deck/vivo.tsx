"use client";

// Las once diapositivas del recorrido en vivo. Cada una es un dibujo que se construye por pasos, con una frase
// corta. Las cifras de respaldo no van aquí: están en la aplicación y en el anexo.
// Los puntos de la cohorte los dibuja `Puntos`, por encima: aquí solo van los ejes, las líneas y los rótulos.

import { motion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { coincidenciaConLaEspirometria, ETIQUETA_LOBULO, type Imagen, type Lobulo, conPuntuacion, correlacionPrincipal, curvaDeComplejidad, fraccionDeTexto, lectura, modeloConTodas, modeloDeComplejidad, validacionDelModelo } from "@/lib/cohorte";
import { azar, metros, num, porcentaje, pValor } from "@/lib/formato";
import { CERCA, DANO, EJE_Y, GRIS, GRIS_OSCURO, LIENZO, NUBE, PAPEL, SITIO_DE_LA_PERSONA, TINTA, xCociente, xNube, yPuntuacion } from "@/lib/escena";
import { LLN } from "@/lib/lln";
import { AJUSTE_DEL_PRIMER_MODELO, RESERVA_DE_LA_PRIMERA_PRUEBA } from "./diapositivas";
import type { PropsDiapositiva } from "./piezas";
import { publica } from "@/lib/ruta";

const SUAVE = [0.4, 0, 0.2, 1] as const;
const LINEA = "#d8d5ce";
const DANO_TINTA = "#b4540a";
const DANO_SUAVE = "#fef1e4";
const FRANJA = "#ebe8e1";
export const RUTA_COHORTE = "/plataforma";
export const RUTA_INFERENCIA = "/plataforma/inferencia";

export function Frase({ children }: { children: React.ReactNode }) {
  return (
    <motion.h1
      className="absolute top-[7.4cqw] left-[6cqw] max-w-[86cqw] text-[4cqw] leading-[1.08] font-semibold tracking-[-0.035em] text-balance"
      initial={{ opacity: 0, y: "0.8cqw" }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: SUAVE }}
    >
      {children}
    </motion.h1>
  );
}

function Dibujo({ children, descripcion }: { children: React.ReactNode; descripcion: string }) {
  return (
    <svg viewBox={`0 0 ${LIENZO.ancho} ${LIENZO.alto}`} className="absolute inset-0 size-full" role="img" aria-label={descripcion}>
      {children}
    </svg>
  );
}

/** Un paso del dibujo: aparece cuando toca y se queda. */
function Paso({ visible, children, retraso = 0 }: { visible: boolean; children: React.ReactNode; retraso?: number }) {
  return (
    <motion.g initial={false} animate={{ opacity: visible ? 1 : 0 }} transition={{ duration: 0.45, delay: visible ? retraso : 0, ease: SUAVE }}>
      {children}
    </motion.g>
  );
}

/** El eje de la espirometría, con su línea en 0,70. Es el mismo en todas las diapositivas que lo usan. */
function EjeDelCociente({ umbral, desde = 330, rotulo = true }: { umbral: number; desde?: number; rotulo?: boolean }) {
  return (
    <>
      <line x1={150} x2={1450} y1={EJE_Y} y2={EJE_Y} stroke={LINEA} strokeWidth={2} />
      {[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9].map((marca) => (
        <text key={marca} x={xCociente(marca)} y={EJE_Y + 38} textAnchor="middle" fontSize={24} fill={marca === umbral ? TINTA : GRIS_OSCURO} fontWeight={marca === umbral ? 600 : 400}>
          {num(marca, 2)}
        </text>
      ))}
      {rotulo && (
        <text x={1450} y={EJE_Y + 78} textAnchor="end" fontSize={24} fill={GRIS_OSCURO}>
          espirometría: FEV1/FVC (índice de Tiffeneau)
        </text>
      )}
      <line x1={xCociente(umbral)} x2={xCociente(umbral)} y1={desde} y2={EJE_Y} stroke={TINTA} strokeWidth={3} strokeDasharray="2 10" strokeLinecap="round" />
    </>
  );
}

/** Qué significa cada lado de la línea de 0,70. */
function LadosDelUmbral({ x, y }: { x: number; y: number }) {
  return (
    <>
      <text x={x - 20} y={y} textAnchor="end" fontSize={28} fontWeight={600} fill={TINTA}>
        por debajo de 0,70: EPOC
      </text>
      <text x={x + 20} y={y} fontSize={28} fontWeight={600} fill={GRIS_OSCURO}>
        0,70 o más: no es EPOC
      </text>
    </>
  );
}

// 1. Una persona sopla, sale un número y cae a un lado de una línea. Después, los 80.
export function Soplar({ cohorte, geometria, clic }: PropsDiapositiva) {
  const { persona, sujetos, cociente } = geometria;
  const umbral = cohorte.umbral_cociente;
  const suyo = persona ? cociente[sujetos.indexOf(persona)] : null;
  const valor = persona?.clinica.fev1_fvc ?? null;
  const { x, y } = SITIO_DE_LA_PERSONA;

  return (
    <>
      <Frase>La EPOC se diagnostica soplando.</Frase>
      <Dibujo descripcion="Una persona sopla y sale un número. Cae a la izquierda de la línea de 0,70. Después aparecen todos los sujetos, a un lado y otro de esa línea.">
        <Paso visible={clic === 0}>
          {[-34, 0, 34].map((desvio, i) => (
            <motion.path
              key={desvio}
              d={`M${x + 60},${y + desvio} C${x + 130},${y + desvio - 22} ${x + 190},${y + desvio + 22} ${x + 270},${y + desvio}`}
              fill="none"
              stroke={GRIS_OSCURO}
              strokeWidth={5}
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.7, delay: 0.3 + 0.12 * i, ease: "easeOut" }}
            />
          ))}
          <motion.text x={x + 330} y={y + 70} fontSize={210} fontWeight={600} fill={TINTA} letterSpacing="-0.04em" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0, duration: 0.5 }}>
            {num(valor, 2)}
          </motion.text>
          <motion.text x={x + 340} y={y + 130} fontSize={36} fontWeight={500} fill={GRIS_OSCURO} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2, duration: 0.5 }}>
            FEV1/FVC (índice de Tiffeneau)
          </motion.text>
        </Paso>

        <Paso visible={clic >= 1}>
          <EjeDelCociente umbral={umbral} />
          {suyo && (
            <>
              <line x1={suyo.x} x2={suyo.x} y1={clic >= 2 ? 438 : suyo.y - 62} y2={suyo.y - 24} stroke={TINTA} strokeWidth={2} />
              <text x={suyo.x} y={clic >= 2 ? 424 : suyo.y - 78} textAnchor="middle" fontSize={44} fontWeight={600} fill={TINTA}>
                {num(valor, 2)}
              </text>
            </>
          )}
        </Paso>

      </Dibujo>
    </>
  );
}

// 2. Los que están justo al otro lado de la línea.
export function Frontera({ cohorte }: PropsDiapositiva) {
  const umbral = cohorte.umbral_cociente;
  const [x0, x1] = [xCociente(umbral) + 6, xCociente(CERCA) + 14];
  return (
    <>
      <Frase>¿Y los que están justo al otro lado?</Frase>
      <Dibujo descripcion="Los sujetos sin obstrucción que quedan pegados a la línea de 0,70 se señalan con un interrogante.">
        <EjeDelCociente umbral={umbral} />
        <LadosDelUmbral x={xCociente(umbral)} y={262} />
        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 0.5 }}>
          <rect x={x0} y={440} width={x1 - x0} height={EJE_Y - 440 - 14} rx={22} fill="none" stroke={TINTA} strokeWidth={3} strokeDasharray="10 10" />
          <text x={(x0 + x1) / 2} y={410} textAnchor="middle" fontSize={150} fontWeight={600} fill={TINTA}>
            ?
          </text>
        </motion.g>
      </Dibujo>
    </>
  );
}

// 3. Su TC: los lóbulos, el árbol bronquial, los dos números que salen de ahí y por qué esos dos.
// La imagen es siempre una TC pública (LIDC-IDRI): las diapositivas no enseñan ninguna TC de la cohorte.
// TotalSegmentator y las definiciones de las medidas: `docs/modelo.md`, apartados 1 y 2. Los criterios: `docs/cifras.md`.
/** Un color suave por lóbulo, ninguno naranja: el naranja es solo daño. */
const COLOR_LOBULO: Record<Lobulo, [number, number, number]> = { LSD: [122, 166, 216], LM: [108, 192, 176], LID: [156, 207, 122], LSI: [179, 157, 219], LII: [230, 161, 192] };

function cargarImagen(url: string): Promise<HTMLImageElement> {
  return new Promise((resolver, rechazar) => {
    const imagen = new Image();
    imagen.onload = () => resolver(imagen);
    imagen.onerror = () => rechazar(new Error(url));
    imagen.src = url;
  });
}

function leerPixeles(imagen: HTMLImageElement, ancho: number, alto: number): Uint8ClampedArray {
  const lienzo = document.createElement("canvas");
  [lienzo.width, lienzo.height] = [ancho, alto];
  const contexto = lienzo.getContext("2d", { willReadFrequently: true })!;
  contexto.imageSmoothingEnabled = false;
  contexto.drawImage(imagen, 0, 0, ancho, alto);
  return contexto.getImageData(0, 0, ancho, alto).data;
}

/**
 * Un corte de la cohorte en tres capas: el gris, los cinco lóbulos con su color y el árbol bronquial en blanco.
 * Lee las mismas vistas previas que la plataforma (`/data/previews`). Si falta alguna, avisa con `alFallar`.
 */
function CorteDeLaCohorte({ clave, imagen, clic, alFallar }: { clave: string; imagen: Imagen; clic: number; alFallar: () => void }) {
  const [gris, lobulos, arbol] = [useRef<HTMLCanvasElement>(null), useRef<HTMLCanvasElement>(null), useRef<HTMLCanvasElement>(null)];
  const corte = Math.floor(imagen.cortes.length / 2);
  useEffect(() => {
    let vivo = true;
    const base = publica(`/data/previews/${clave}-${corte}`);
    Promise.all([cargarImagen(`${base}.png`), cargarImagen(`${base}-lobulos.png`), cargarImagen(publica(`/data/previews/${clave}-arbol.png`)).catch(() => null)]).then(
      ([tono, mapa, ramas]) => {
        if (!vivo || !gris.current || !lobulos.current || !arbol.current) return;
        const [ancho, alto] = [tono.naturalWidth, tono.naturalHeight];
        const etiquetas = leerPixeles(mapa, ancho, alto);
        const via = ramas ? leerPixeles(ramas, ancho, alto) : null;
        const [color, blanco] = [new ImageData(ancho, alto), new ImageData(ancho, alto)];
        for (let i = 0; i < ancho * alto; i++) {
          const lobulo = ETIQUETA_LOBULO[etiquetas[i * 4]];
          if (lobulo) {
            const [r, g, b] = COLOR_LOBULO[lobulo];
            color.data.set([r, g, b, 120], i * 4);
          }
          if (via && via[i * 4] > 127) blanco.data.set([255, 255, 255, 235], i * 4);
        }
        for (const [lienzo, datos] of [[lobulos.current, color], [arbol.current, blanco]] as const) {
          [lienzo.width, lienzo.height] = [ancho, alto];
          lienzo.getContext("2d")!.putImageData(datos, 0, 0);
        }
        [gris.current.width, gris.current.height] = [ancho, alto];
        gris.current.getContext("2d")!.drawImage(tono, 0, 0);
      },
      () => vivo && alFallar(),
    );
    return () => {
      vivo = false;
    };
  }, [clave, corte, alFallar, gris, lobulos, arbol]);
  const capa = "absolute inset-0 size-full";
  const centros = imagen.cortes[corte]?.centros ?? {};
  return (
    <div className="relative h-full" style={{ aspectRatio: `${imagen.ancho} / ${imagen.alto}` }}>
      <canvas ref={gris} className={capa} aria-label="Corte coronal de la TC de una persona de la cohorte" />
      <motion.canvas ref={lobulos} className={capa} initial={false} animate={{ opacity: clic >= 1 ? 1 : 0 }} transition={{ duration: 0.6 }} />
      {/* El árbol crece desde la tráquea hacia abajo. */}
      <motion.canvas ref={arbol} className={capa} initial={false} animate={{ clipPath: clic >= 2 ? "inset(0% 0% 0% 0%)" : "inset(0% 0% 100% 0%)" }} transition={{ duration: 1.4, ease: "easeInOut" }} />
      <motion.div className={capa} initial={false} animate={{ opacity: clic >= 1 ? 1 : 0 }} transition={{ duration: 0.6 }}>
        {(Object.entries(centros) as [Lobulo, [number, number]][]).map(([lobulo, [x, y]]) => (
          <span
            key={lobulo}
            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full px-[0.6cqw] py-[0.15cqw] text-[0.95cqw] font-semibold text-tinta"
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, background: `rgb(${COLOR_LOBULO[lobulo].join(" ")})` }}
          >
            {lobulo}
          </span>
        ))}
      </motion.div>
    </div>
  );
}

export function MirarLaTC({ cohorte, geometria, clic }: PropsDiapositiva) {
  const { persona } = geometria;
  const [falta, setFalta] = useState(false);
  // Una persona de la cohorte con su TC y su árbol: la de ejemplo si los trae, si no la primera con EPOC.
  const conTC = (s: (typeof cohorte.sujetos)[number] | null | undefined) => !!s && !!s.imagen && s.arbol && !!cohorte.imagenes[s.imagen];
  const elegido = conTC(persona) ? persona : (cohorte.sujetos.find((s) => s.caso && conTC(s)) ?? null);
  const [sinCohorte, setSinCohorte] = useState(false);
  const alFallar = useCallback(() => setSinCohorte(true), []);
  const real = elegido && elegido.imagen && !sinCohorte ? { clave: elegido.imagen, imagen: cohorte.imagenes[elegido.imagen] } : null;
  const capa = "absolute inset-0 size-full";
  const aparece = (desde: number, retraso = 0) => ({
    initial: false as const,
    animate: { opacity: clic >= desde ? 1 : 0, y: clic >= desde ? 0 : "0.6cqw" },
    transition: { duration: 0.5, delay: clic >= desde ? retraso : 0, ease: SUAVE },
  });

  return (
    <>
      <Frase>Su TC.</Frase>
      {real ? (
        <div className="absolute top-[14cqw] left-[6cqw] h-[32cqw] overflow-hidden rounded-[1cqw] bg-black">
          <CorteDeLaCohorte clave={real.clave} imagen={real.imagen} clic={clic} alFallar={alFallar} />
        </div>
      ) : (
      <div className="absolute top-[14cqw] left-[6cqw] h-[32cqw] overflow-hidden rounded-[1cqw] bg-black">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={publica("/publica/tc.png")} alt="Corte coronal de una TC de tórax" className="block h-full w-auto" onError={() => setFalta(true)} />
        {falta ? (
          <p className="absolute inset-0 grid w-[33cqw] place-items-center p-[2cqw] text-center text-[1.2cqw] text-white/80">Falta la TC pública de las diapositivas. La escribe scripts/make_fixture.py.</p>
        ) : (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <motion.img src={publica("/publica/tc-lobulos.png")} alt="" className={capa} initial={false} animate={{ opacity: clic >= 1 ? 1 : 0 }} transition={{ duration: 0.6 }} />
            {/* El árbol crece desde la tráquea hacia abajo. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <motion.img
              src={publica("/publica/tc-arbol.png")}
              alt=""
              className={capa}
              initial={false}
              animate={{ clipPath: clic >= 2 ? "inset(0% 0% 0% 0%)" : "inset(0% 0% 100% 0%)" }}
              transition={{ duration: 1.4, ease: "easeInOut" }}
            />
          </>
        )}
      </div>
      )}

      <div className="absolute top-[14cqw] right-[6cqw] left-[42.5cqw] flex flex-col">
        <motion.div {...aparece(1)} className="border-b border-linea pb-[1.3cqw]">
          <p className="text-[0.95cqw] font-medium tracking-[0.05em] text-tinta-3 uppercase">Segmentar</p>
          <p className="mt-[0.4cqw] text-[1.45cqw] leading-[1.35]">
            <strong className="font-semibold">TotalSegmentator</strong>: una red nnU-Net 3D ya entrenada con más de mil TC anotadas. Separa lóbulos, vía aérea y vasos.
          </p>
        </motion.div>
        {[
          {
            valor: persona?.valores.laa950_smooth === null || !persona ? "–" : `${num(persona.valores.laa950_smooth, 2)} %`,
            que: "de enfisema",
            como: "Parte del pulmón, sin vasos ni vías, por debajo de −950 unidades Hounsfield (HU), la escala de densidad de la TC, tras un suavizado gaussiano de 1 mm.",
          },
          {
            valor: metros(persona?.valores.via_longitud_mm),
            que: "de árbol bronquial",
            como: "La vía aérea segmentada se reduce a su línea central (esqueleto), se quitan las ramitas que apenas salen de la pared y se suman, en milímetros, los tramos entre puntos vecinos de esa línea.",
            cita: "Esqueleto 3D por adelgazamiento (Lee, Kashyap y Chu, 1994; scikit-image). Medida afín al recuento total de vías aéreas de Kirby et al., AJRCCM 2018.",
          },
        ].map((medida, i) => (
          <motion.div key={medida.que} {...aparece(3, 0.15 * i)} className="grid grid-cols-[17cqw_1fr] items-center gap-[1.6cqw] border-b border-linea py-[1.3cqw]">
            <div>
              <p className="text-[4.6cqw] leading-none font-semibold tracking-[-0.045em] whitespace-nowrap">{medida.valor}</p>
              <p className="mt-[0.4cqw] text-[1.45cqw] text-tinta-2">{medida.que}</p>
            </div>
            <div>
              <p className="text-[1.25cqw] leading-[1.4] text-tinta-2">{medida.como}</p>
              {medida.cita && <p className="mt-[0.4cqw] text-[0.9cqw] leading-[1.3] text-tinta-3">{medida.cita}</p>}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Los tres criterios del embudo, con la medida que se cae en cada uno: `docs/cifras.md`, sección del embudo. */}
      <motion.div {...aparece(4)} className="absolute top-[46.8cqw] right-[6cqw] left-[6cqw] grid grid-cols-[auto_1fr_1fr_1fr_auto] items-stretch gap-[1cqw] text-[1.05cqw] leading-[1.25]">
        <p className="self-center font-semibold whitespace-nowrap">Por qué estas dos:</p>
        {[
          ["Da lo mismo con los dos filtros del escáner", "se cae el %LAA-950 clásico (acuerdo 0,18)"],
          ["Va con la espirometría", "se cae el grosor de pared (q = 0,42)"],
          ["Dice algo nuevo", "se cae el volumen vascular, que repite lo mismo"],
        ].map(([criterio, cae], i) => (
          <div key={criterio} className="rounded-[0.9cqw] bg-fondo px-[1.1cqw] py-[0.5cqw]">
            <p className="font-semibold">
              <span className="mr-[0.4em] font-mono text-tinta-3">{i + 1}</span>
              {criterio}
            </p>
            <p className="text-tinta-2">{cae}</p>
          </div>
        ))}
        <p className="self-center rounded-full bg-tinta px-[1.1cqw] py-[0.5cqw] font-semibold whitespace-nowrap text-papel">Quedan enfisema y árbol</p>
      </motion.div>
      <p className="absolute bottom-[1.3cqw] left-[6cqw] text-[0.95cqw] text-tinta-3">{real ? (cohorte.aviso ? "TC pública de ejemplo (LIDC-IDRI)." : "TC de la cohorte.") : "TC pública de ejemplo (LIDC-IDRI)."}</p>
    </>
  );
}

// 4. La curva de crecimiento: lo esperado para alguien como ella es una franja, y su punto cae fuera.
export function Crecimiento({ geometria, clic }: PropsDiapositiva) {
  const { franja, persona, sujetos, crecimiento } = geometria;
  const suyo = persona ? crecimiento[sujetos.indexOf(persona)] : null;
  const talla = persona?.clinica.talla ?? null;
  if (!franja)
    return (
      <>
        <Frase>¿Es mucho o poco para alguien como ella?</Frase>
        <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Esta cohorte no trae lo esperado para cada sujeto: no hay franja que dibujar.</p>
      </>
    );
  const [t0, t1] = franja.tallas;
  const borde = (signo: number) => [t0, t1].map((t) => `${franja.x(t)},${franja.y(franja.centro(t) + signo * franja.ancho)}`);
  const [arriba, abajo] = [borde(1), borde(-1).reverse()];

  return (
    <>
      <Frase>¿Es mucho o poco para alguien como ella?</Frase>
      <Dibujo descripcion="La longitud del árbol bronquial frente a la talla. Una franja marca lo esperado. El punto de la persona de ejemplo cae por debajo de la franja.">
        <line x1={300} x2={1410} y1={EJE_Y} y2={EJE_Y} stroke={LINEA} strokeWidth={2} />
        <line x1={300} x2={300} y1={290} y2={EJE_Y} stroke={LINEA} strokeWidth={2} />
        <text x={1410} y={EJE_Y + 42} textAnchor="end" fontSize={26} fill={GRIS_OSCURO}>
          más talla →
        </text>
        <text transform={`translate(268 300) rotate(-90)`} textAnchor="end" fontSize={26} fill={GRIS_OSCURO}>
          más árbol bronquial →
        </text>
        <motion.polygon points={[...arriba, ...abajo].join(" ")} fill={FRANJA} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.2 }} />
        <motion.text
          x={franja.x(t1) - 24}
          y={franja.y(franja.centro(t1) + franja.ancho) - 18}
          textAnchor="end"
          fontSize={34}
          fontWeight={600}
          fill={TINTA}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          lo esperado
        </motion.text>
        {suyo && talla !== null && (
          <Paso visible={clic >= 1} retraso={0.5}>
            <line x1={suyo.x} x2={suyo.x} y1={franja.y(franja.centro(talla) - franja.ancho)} y2={suyo.y - 22} stroke={TINTA} strokeWidth={2.5} strokeDasharray="6 8" />
            <text x={suyo.x + 34} y={suyo.y + 14} fontSize={38} fontWeight={600} fill={TINTA}>
              ella
            </text>
          </Paso>
        )}
      </Dibujo>
    </>
  );
}

// 5. El experimento ciego: los puntos ordenados solo por su TC se parten en dos; después vuelven al eje de la espirometría.
export function Ciego({ cohorte, geometria, clic }: PropsDiapositiva) {
  const natural = cohorte.umbral_natural;
  const coinciden = fraccionDeTexto(natural?.coinciden_con_la_obstruccion);
  const grupos = natural?.dos_grupos_por_la_tc;
  const frontera = geometria.xFronteraCiega;
  const enSuEje = clic >= 2;
  const [x070, altos, bajos] = [xCociente(cohorte.umbral_cociente), fraccionDeTexto(grupos?.con_obstruccion_por_encima), fraccionDeTexto(grupos?.sin_obstruccion_por_debajo)];

  return (
    <>
      {/* Las dos medidas se eligieron antes con la espirometría: aquí no se usa para ajustar ni para cortar, y no se dice más. */}
      <Frase>Validamos nuestra regla con el índice de 0,70.</Frase>
      <p className="absolute top-[12.6cqw] left-[6cqw] max-w-[80cqw] text-[1.55cqw] leading-[1.35] text-tinta-2">
        Comparamos cómo parte la TC a las personas con cómo las parte el índice de Tiffeneau. Aquí se ven nuestros errores.
      </p>
      {!natural && <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Pendiente: esta cohorte no trae la partición por la TC.</p>}
      <Dibujo descripcion="Los sujetos ordenados solo por su TC se parten en dos grupos de color. Después se colocan sobre el eje de la espirometría: los dos colores quedan a un lado y otro de la línea de 0,70.">
        <Paso visible={!enSuEje}>
          <line x1={200} x2={1400} y1={EJE_Y} y2={EJE_Y} stroke={LINEA} strokeWidth={2} />
          <path d={`M1400,${EJE_Y} l-16,-9 M1400,${EJE_Y} l-16,9`} stroke={LINEA} strokeWidth={2} fill="none" />
          <text x={1400} y={EJE_Y + 42} textAnchor="end" fontSize={26} fill={GRIS_OSCURO}>
            TC más alterada →
          </text>
        </Paso>
        {frontera !== null && grupos && (
          <Paso visible={clic === 1} retraso={0.3}>
            <line x1={frontera} x2={frontera} y1={420} y2={EJE_Y} stroke={DANO} strokeWidth={3} strokeDasharray="2 10" strokeLinecap="round" />
            <text x={frontera - 40} y={400} textAnchor="end" fontSize={100} fontWeight={600} fill={GRIS_OSCURO} letterSpacing="-0.04em">
              {grupos.por_debajo}
            </text>
            <text x={frontera + 40} y={400} fontSize={100} fontWeight={600} fill={DANO} letterSpacing="-0.04em">
              {grupos.por_encima}
            </text>
          </Paso>
        )}
        <Paso visible={enSuEje} retraso={0.3}>
          <EjeDelCociente umbral={cohorte.umbral_cociente} />
          <LadosDelUmbral x={x070} y={292} />
        </Paso>
        {/* El desglose a cada lado de la línea de 0,70, con su nombre: no es el 64 de 80 del modelo final de la diapositiva 7. */}
        {coinciden && altos && bajos && (
          <Paso visible={clic >= 3} retraso={0.2}>
            <text x={x070 - 36} y={400} textAnchor="end" fontSize={80} fontWeight={600} fill={DANO_TINTA} letterSpacing="-0.04em">
              {altos.aciertos} de {altos.de}
            </text>
            <text x={x070 - 36} y={438} textAnchor="end" fontSize={24} fill={DANO_TINTA}>
              con obstrucción, en el grupo alto
            </text>
            <text x={x070 + 36} y={400} fontSize={80} fontWeight={600} fill={TINTA} letterSpacing="-0.04em">
              {bajos.aciertos} de {bajos.de}
            </text>
            <text x={x070 + 36} y={438} fontSize={24} fill={TINTA}>
              sin obstrucción, en el grupo bajo
            </text>
            <circle cx={x070 + 47} cy={472} r={11} fill={PAPEL} stroke={GRIS_OSCURO} strokeWidth={3} />
            <text x={x070 + 67} y={480} fontSize={24} fill={GRIS_OSCURO}>
              {coinciden.de - coinciden.aciertos} errores frente al 0,70
            </text>
          </Paso>
        )}
      </Dibujo>
    </>
  );
}

// 6 y 7. La nube de dos dimensiones: cada sujeto por su espirometría (horizontal) y por su TC (vertical).
/** Los ejes de la nube. La línea de 0,70 solo se dibuja cuando se pide. */
function EjesDeLaNube({ linea, umbral }: { linea: boolean; umbral: number }) {
  return (
    <>
      <line x1={NUBE.x0} x2={NUBE.x1} y1={EJE_Y} y2={EJE_Y} stroke={LINEA} strokeWidth={2} />
      {[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9].map((marca) => (
        <text key={marca} x={xNube(marca)} y={EJE_Y + 38} textAnchor="middle" fontSize={24} fill={linea && marca === umbral ? TINTA : GRIS_OSCURO} fontWeight={linea && marca === umbral ? 600 : 400}>
          {num(marca, 2)}
        </text>
      ))}
      <text x={NUBE.x1} y={EJE_Y + 78} textAnchor="end" fontSize={24} fill={GRIS_OSCURO}>
        espirometría: FEV1/FVC (índice de Tiffeneau)
      </text>
      {/* El eje de la TC: la puntuación de daño, con sus marcas. */}
      <line x1={NUBE.x0} x2={NUBE.x0} y1={290} y2={EJE_Y} stroke={LINEA} strokeWidth={2} />
      {[0, 2, 4].map((marca) => (
        <g key={marca}>
          <line x1={NUBE.x0 - 8} x2={NUBE.x0} y1={yPuntuacion(marca)} y2={yPuntuacion(marca)} stroke={GRIS_OSCURO} strokeWidth={2} />
          <text x={NUBE.x0 - 14} y={yPuntuacion(marca) + 8} textAnchor="end" fontSize={22} fill={GRIS_OSCURO}>
            {marca === 0 ? "0" : `+${marca}`}
          </text>
        </g>
      ))}
      <text transform={`translate(80 ${EJE_Y - 10}) rotate(-90)`} fontSize={24} fill={GRIS_OSCURO}>
        puntuación de la TC (más alterada →)
      </text>
      <Paso visible={linea}>
        <line x1={xNube(umbral)} x2={xNube(umbral)} y1={290} y2={EJE_Y} stroke={TINTA} strokeWidth={3} strokeDasharray="2 10" strokeLinecap="round" />
        <text x={xNube(umbral) - 16} y={318} textAnchor="end" fontSize={28} fontWeight={600} fill={TINTA}>
          la línea de la espirometría
        </text>
      </Paso>
    </>
  );
}

/** Una nube pequeña de ejemplo, con su correlación al lado. Los puntos van de 0 a 1 en los dos ejes. */
function NubePequena({ y, puntos, valor, nombre, fuerte = false }: { y: number; puntos: [number, number][]; valor: string; nombre: string; fuerte?: boolean }) {
  const [x0, ancho, alto] = [1190, 190, 120];
  return (
    <g>
      <line x1={x0} x2={x0 + ancho} y1={y + alto} y2={y + alto} stroke={LINEA} strokeWidth={2} />
      <line x1={x0} x2={x0} y1={y} y2={y + alto} stroke={LINEA} strokeWidth={2} />
      {puntos.map(([px, py], i) => (
        <circle key={i} cx={x0 + 10 + px * (ancho - 20)} cy={y + alto - 10 - py * (alto - 20)} r={4.5} fill={fuerte ? TINTA : GRIS_OSCURO} />
      ))}
      <text x={x0 + ancho + 26} y={y + 66} fontSize={64} fontWeight={600} fill={fuerte ? TINTA : GRIS_OSCURO} letterSpacing="-0.04em">
        {valor}
      </text>
      <text x={x0 + ancho + 28} y={y + 102} fontSize={22} fill={fuerte ? TINTA : GRIS_OSCURO}>
        {nombre}
      </text>
    </g>
  );
}

export function Nube({ cohorte, clic }: PropsDiapositiva) {
  const rho = correlacionPrincipal(cohorte)?.rho;
  // La nuestra, en pequeño: los mismos sujetos. Las otras dos son de mentira y lo dicen.
  const nuestra = useMemo(
    () =>
      conPuntuacion(cohorte).flatMap((s): [number, number][] => {
        const cociente = s.clinica.fev1_fvc;
        return cociente === null ? [] : [[Math.min(Math.max((cociente - 0.3) / 0.6, 0), 1), Math.min(Math.max((s.puntuacion + 2.4) / 7.4, 0), 1)]];
      }),
    [cohorte],
  );
  const linea = useMemo(() => Array.from({ length: 14 }, (_, i): [number, number] => [i / 13, 1 - i / 13]), []);
  const redonda = useMemo(() => {
    const aleatorio = azar(3);
    return Array.from({ length: 40 }, (): [number, number] => {
      const [angulo, radio] = [aleatorio() * 2 * Math.PI, Math.sqrt(aleatorio()) * 0.48];
      return [0.5 + radio * Math.cos(angulo), 0.5 + radio * Math.sin(angulo)];
    });
  }, []);

  return (
    <>
      <Frase>{rho === undefined ? "Cuanto peor sopla, peor su TC." : `Cuanto peor sopla, peor su TC: ${num(rho, 2)}.`}</Frase>
      <Dibujo descripcion="Cada sujeto por lo que sopla, en horizontal, y por la puntuación de su TC, en vertical. La nube baja hacia la derecha: cuanto peor sopla, más alta la puntuación. Al lado, tres nubes de ejemplo: una línea perfecta, una nube redonda sin relación y la nuestra.">
        <EjesDeLaNube linea={false} umbral={cohorte.umbral_cociente} />
        <text x={NUBE.x0 + 10} y={268} fontSize={26} fontWeight={600} fill={DANO_TINTA}>
          ↖ sopla peor y su TC está más alterada
        </text>
        <text x={NUBE.x1 - 10} y={EJE_Y - 22} textAnchor="end" fontSize={26} fontWeight={600} fill={TINTA}>
          sopla bien y su TC es normal ↘
        </text>
        <Paso visible={clic >= 1} retraso={0.2}>
          <text x={1190} y={282} fontSize={22} fill={GRIS_OSCURO}>
            la correlación, de −1 a 1
          </text>
          <NubePequena y={305} puntos={linea} valor="−1" nombre="una línea perfecta" />
          <NubePequena y={475} puntos={redonda} valor="0" nombre="sin relación" />
          {rho !== undefined && <NubePequena y={645} puntos={nuestra} valor={num(rho, 2)} nombre="la nuestra" fuerte />}
        </Paso>
      </Dibujo>
    </>
  );
}

export function Cuadrantes({ cohorte, geometria, clic }: PropsDiapositiva) {
  const [x070, yUmbral] = [xNube(cohorte.umbral_cociente), yPuntuacion(cohorte.umbral_dano)];
  const senalados = geometria.sujetos.filter((s, i) => geometria.cuadrantes[i] && !s.caso && s.dano_tc).length;
  const { epocPorEncima, epoc, controlesPorDebajo, controles } = coincidenciaConLaEspirometria(cohorte);
  const panel = 1180;

  return (
    <>
      <Frase>Nuestra línea en la TC reconstruye la de la espirometría.</Frase>
      <Dibujo descripcion="La misma nube. Primero, la línea vertical de la espirometría en 0,70. Después, la línea horizontal que trazamos en la TC. Las dos coinciden en la mayoría de los sujetos. Se ilumina el cuadrante de quienes no tienen obstrucción y sí la TC de la EPOC.">
        <Paso visible={clic >= 3}>
          <rect x={x070} y={290} width={NUBE.x1 - x070} height={yUmbral - 290} fill={DANO_SUAVE} />
        </Paso>
        <EjesDeLaNube linea umbral={cohorte.umbral_cociente} />
        <Paso visible={clic >= 1}>
          <motion.line x1={NUBE.x0} y1={yUmbral} y2={yUmbral} stroke={DANO} strokeWidth={3} strokeDasharray="2 10" strokeLinecap="round" initial={false} animate={{ x2: clic >= 1 ? NUBE.x1 : NUBE.x0 }} transition={{ duration: 0.8, ease: SUAVE }} />
          <text x={NUBE.x1 + 12} y={yUmbral + 9} fontSize={26} fontWeight={600} fill={DANO_TINTA}>
            nuestra línea en la TC
          </text>
          <text x={NUBE.x1 + 12} y={yUmbral - 26} fontSize={20} fill={DANO_TINTA}>
            puntuación {num(cohorte.umbral_dano, 2)}: el umbral de 2.2
          </text>
        </Paso>
        {/* Desglosado y sin sumar: el 64 de 80 es el del experimento ciego, y no se repite aquí con otro significado. */}
        <Paso visible={clic >= 2} retraso={0.3}>
          <text x={panel + 4} y={302} fontSize={22} fontWeight={600} fill={GRIS_OSCURO} letterSpacing="0.08em">
            MODELO FINAL, EN LOS {epoc + controles}
          </text>
          <text x={panel} y={384} fontSize={72} fontWeight={600} fill={TINTA} letterSpacing="-0.045em">
            {epocPorEncima} de {epoc}
          </text>
          <text x={panel + 4} y={420} fontSize={24} fill={TINTA}>
            con EPOC, por encima
          </text>
          <text x={panel} y={500} fontSize={72} fontWeight={600} fill={TINTA} letterSpacing="-0.045em">
            {controlesPorDebajo} de {controles}
          </text>
          <text x={panel + 4} y={536} fontSize={24} fill={TINTA}>
            sin obstrucción, por debajo
          </text>
        </Paso>
        <Paso visible={clic >= 3} retraso={0.3}>
          <text x={panel} y={700} fontSize={120} fontWeight={600} fill={DANO_TINTA} letterSpacing="-0.05em">
            {senalados}
          </text>
        </Paso>
      </Dibujo>
      {/* Qué son los señalados, en HTML para que el texto se parta dentro del lienzo. */}
      <motion.div
        className="absolute top-[44.6cqw] left-[73.75cqw] w-[22.5cqw] text-[1cqw] leading-[1.3]"
        initial={false}
        animate={{ opacity: clic >= 3 ? 1 : 0 }}
        transition={{ duration: 0.45, delay: clic >= 3 ? 0.3 : 0, ease: SUAVE }}
      >
        <p className="font-semibold text-dano-tinta">
          Posible pre-EPOC: espirometría sin obstrucción (FEV1/FVC ≥ {num(cohorte.umbral_cociente, 2)}) y TC alterada (puntuación ≥ {num(cohorte.umbral_dano, 2)}).
        </p>
        {senalados === LLN.pre_epoc && (
          <p className="mt-[0.4cqw] text-tinta-2">
            No son EPOC escondidos: con los valores de referencia GLI-2012 (límite inferior de normalidad por edad, sexo y talla), {LLN.pre_epoc - LLN.pre_epoc_bajo_lln} de los {LLN.pre_epoc} siguen sin obstrucción.
          </p>
        )}
      </motion.div>
    </>
  );
}

// 8. Cómo está hecho: la validación en dos tiempos.
/** Una rejilla de puntos: `llenos` en tinta y el resto en contorno. */
function Rejilla({ x, y, columnas, cuantos, color, hueco = false, discontinuo = false }: { x: number; y: number; columnas: number; cuantos: number; color: string; hueco?: boolean; discontinuo?: boolean }) {
  return (
    <>
      {Array.from({ length: cuantos }, (_, i) => (
        <circle
          key={i}
          cx={x + (i % columnas) * 24}
          cy={y + Math.floor(i / columnas) * 24}
          r={8.5}
          fill={hueco ? PAPEL : color}
          stroke={color}
          strokeWidth={hueco ? 2.5 : 0}
          strokeDasharray={discontinuo ? "3 3" : undefined}
        />
      ))}
    </>
  );
}

const deCada100 = (auc: number) => num(auc * 100, 0);

export function ComoSeValido({ cohorte, clic }: PropsDiapositiva) {
  const { reserva, validacion } = cohorte;
  const fila = validacionDelModelo(cohorte);
  const ajuste = cohorte.congelado?.sujetos_de_ajuste ?? AJUSTE_DEL_PRIMER_MODELO;
  const apartados = reserva?.sujetos ?? RESERVA_DE_LA_PRIMERA_PRUEBA;
  const grupos = validacion?.vueltas ?? 5;
  const total = validacion?.sujetos ?? cohorte.comprobaciones.sujetos;
  const porGrupo = Math.ceil(total / grupos);
  // El grupo que se puntúa va rotando: cada uno, con un modelo hecho con los demás.
  const [turno, setTurno] = useState(0);
  useEffect(() => {
    if (clic < 1) return;
    const intervalo = setInterval(() => setTurno((t) => (t + 1) % grupos), 1100);
    return () => clearInterval(intervalo);
  }, [clic, grupos]);
  const resultado = 1110;

  return (
    <>
      <Frase>Probado en personas que el modelo no había visto.</Frase>
      <Dibujo descripcion="Dos tiempos. Primero, el modelo se construye con unos sujetos y se prueba una sola vez en otros apartados. Después, los ochenta en validación cruzada: cada grupo se puntúa con un modelo hecho con los demás.">
        <text x={96} y={330} fontSize={34} fontWeight={600} fill={TINTA}>
          Primero
        </text>
        <text x={96} y={366} fontSize={22} fill={GRIS_OSCURO}>
          una sola prueba
        </text>
        <Rejilla x={330} y={300} columnas={21} cuantos={ajuste} color={TINTA} />
        <Rejilla x={860} y={300} columnas={5} cuantos={apartados} color={TINTA} hueco discontinuo />
        <text x={330} y={400} fontSize={22} fill={TINTA}>
          {ajuste} para construir
        </text>
        <text x={860} y={400} fontSize={22} fill={TINTA}>
          {apartados} apartados
        </text>
        <text x={1010} y={346} fontSize={40} fill={GRIS_OSCURO}>
          →
        </text>
        {reserva ? (
          <>
            <text x={resultado} y={340} fontSize={64} fontWeight={600} fill={TINTA} letterSpacing="-0.03em">
              AUC {num(reserva.separa_epoc.auc, 2)}
            </text>
            {/* Las dos filas pesan lo mismo: los controles que el umbral deja por encima se ven igual que los EPOC. */}
            <text x={resultado + 2} y={380} fontSize={24} fill={TINTA}>
              {reserva.sensibilidad.aciertos} de {reserva.sensibilidad.de} EPOC, por encima
            </text>
            <text x={resultado + 2} y={412} fontSize={24} fill={TINTA}>
              {reserva.especificidad.de - reserva.especificidad.aciertos} de {reserva.especificidad.de} controles, por encima
            </text>
          </>
        ) : (
          <text x={resultado} y={346} fontSize={26} fill={GRIS_OSCURO}>
            Pendiente: no hay prueba en reserva.
          </text>
        )}

        <Paso visible={clic >= 1}>
          <line x1={96} x2={1504} y1={448} y2={448} stroke={LINEA} strokeWidth={2} />
          <text x={96} y={530} fontSize={34} fontWeight={600} fill={TINTA}>
            Después
          </text>
          <text x={96} y={566} fontSize={22} fill={GRIS_OSCURO}>
            los {total}, sin verlos
          </text>
          {Array.from({ length: grupos }, (_, g) => {
            const cuantos = Math.min(porGrupo, total - g * porGrupo);
            const puntuado = g === turno;
            return (
              <g key={g}>
                <Rejilla x={330 + g * 118} y={500} columnas={4} cuantos={cuantos} color={puntuado ? DANO_TINTA : TINTA} hueco={puntuado} />
                <text x={330 + g * 118 + 36} y={610} textAnchor="middle" fontSize={19} fill={puntuado ? DANO_TINTA : GRIS_OSCURO}>
                  {puntuado ? "se puntúa" : "construye"}
                </text>
              </g>
            );
          })}
          <text x={330} y={652} fontSize={22} fill={TINTA}>
            {grupos} grupos, por turnos; {validacion?.repeticiones ?? 10} repeticiones
          </text>
          <text x={1010} y={546} fontSize={40} fill={GRIS_OSCURO}>
            →
          </text>
          {fila ? (
            <>
              <text x={resultado} y={540} fontSize={64} fontWeight={600} fill={TINTA} letterSpacing="-0.03em">
                AUC {num(fila.auc, 2)}
              </text>
              <text x={resultado + 2} y={580} fontSize={24} fill={TINTA}>
                {porcentaje(fila.sensibilidad_youden)} de los EPOC, por encima
              </text>
              <text x={resultado + 2} y={612} fontSize={24} fill={TINTA}>
                {porcentaje(fila.especificidad_youden)} de los controles, por debajo
              </text>
            </>
          ) : (
            <text x={resultado} y={546} fontSize={26} fill={GRIS_OSCURO}>
              Pendiente: no hay validación cruzada.
            </text>
          )}
        </Paso>

        {/* Llega con el segundo tiempo, sin un clic propio: así la diapositiva se cuenta en dos pasos. */}
        {fila && (
          <Paso visible={clic >= 1} retraso={0.8}>
            <rect x={96} y={706} width={1408} height={110} rx={22} fill="#f3f1ec" />
            <text x={132} y={774} fontSize={34} fill={TINTA}>
              <tspan fontWeight={600}>AUC {num(fila.auc, 2)}:</tspan> en {deCada100(fila.auc)} de cada 100 parejas, quien tiene EPOC puntúa más alto.
            </text>
          </Paso>
        )}
      </Dibujo>
    </>
  );
}

// 9. Más medidas no mejoran el modelo: el embudo, dos ejemplos y la curva.
function ConQue({ si, children }: { si: boolean; children: React.ReactNode }) {
  return (
    <li className="flex gap-[0.6cqw]">
      <span className={`w-[1.2cqw] shrink-0 font-semibold ${si ? "text-tinta" : "text-tinta-3"}`}>{si ? "✓" : "✗"}</span>
      <span className={si ? "" : "text-tinta-2"}>{children}</span>
    </li>
  );
}

function FilaDelEmbudo({ y, cuantos, siguen, salenALaIzquierda, retraso, final = false }: { y: number; cuantos: number; siguen: number; salenALaIzquierda: boolean; retraso: number; final?: boolean }) {
  const paso = final ? 40 : 26;
  const x0 = 800 - ((cuantos - 1) * paso) / 2;
  return (
    <>
      {Array.from({ length: cuantos }, (_, i) => {
        const sigue = salenALaIzquierda ? i >= cuantos - siguen : i < siguen;
        return (
          <motion.circle
            key={i}
            cx={x0 + i * paso}
            cy={y}
            r={final ? 15 : 10.5}
            fill={sigue ? TINTA : GRIS}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: retraso + i * 0.012, duration: 0.35 }}
          />
        );
      })}
    </>
  );
}

export function MenosEsMas({ cohorte, clic }: PropsDiapositiva) {
  const { embudo, complejidad } = cohorte;
  const paso = (medida: string) => embudo?.pasos.find((p) => p.medida === medida);
  const [clasico, pi10, grosor, vascular] = [paso("laa950"), paso("via_pi10_mm"), paso("via_grosor_pared_mm"), paso("vasos_por_litro")];
  const curva = complejidad ? curvaDeComplejidad(complejidad) : [];
  const todas = modeloConTodas(complejidad);
  const q = (valor: number | undefined) => (valor === undefined ? "–" : valor < 0.001 ? "q < 0,001" : `q = ${pValor(valor)}`);
  const caja = "absolute top-[17.5cqw] w-[20.5cqw] rounded-[1.1cqw] border border-linea bg-white px-[1.4cqw] py-[1.2cqw] text-[1.25cqw] leading-[1.35]";

  // La curva: AUC fuera de muestra según el número de medidas, y aparte el modelo que aprende los pesos con todas.
  const xMedidas = (n: number) => 300 + (n - 1) * 104;
  const xTodas = 1360;
  const yAuc = (auc: number) => 690 - ((auc - 0.8) / 0.15) * 350;

  return (
    <>
      <Frase>Más medidas no mejoran el modelo.</Frase>
      {!embudo && clic < 2 && <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Pendiente: esta cohorte no trae el embudo de medidas.</p>}

      {embudo && (
        <motion.div initial={false} animate={{ opacity: clic < 2 ? 1 : 0 }} transition={{ duration: 0.4 }} className="pointer-events-none absolute inset-0">
          <Dibujo descripcion="Un embudo: de las medidas de la TC, se quedan las estables entre los dos filtros del escáner, de esas las que se asocian con el FEV1/FVC y de esas las que aportan algo nuevo. Quedan dos.">
            {[
              { cuantos: embudo.medidas, siguen: embudo.estables, texto: "medidas de la TC", izquierda: true },
              { cuantos: embudo.estables, siguen: embudo.estables_y_asociadas, texto: "estables con los dos filtros del escáner", izquierda: true },
              { cuantos: embudo.estables_y_asociadas, siguen: embudo.elegidas.length, texto: "que además se asocian con el FEV1/FVC", izquierda: false },
              { cuantos: embudo.elegidas.length, siguen: embudo.elegidas.length, texto: "que aportan algo nuevo: una de vía aérea y el enfisema", izquierda: false },
            ].map((fila, i) => (
              <g key={fila.texto}>
                <motion.text x={800} y={318 + i * 130} textAnchor="middle" fontSize={26} fill={TINTA} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 + i * 0.4 }}>
                  <tspan fontWeight={600}>{fila.cuantos}</tspan> {fila.texto}
                </motion.text>
                <FilaDelEmbudo y={352 + i * 130} cuantos={fila.cuantos} siguen={fila.siguen} salenALaIzquierda={fila.izquierda} retraso={0.3 + i * 0.4} final={i === 3} />
              </g>
            ))}
          </Dibujo>
          <motion.div className={`${caja} left-[6cqw]`} initial={false} animate={{ opacity: clic === 1 ? 1 : 0, x: clic === 1 ? 0 : "-1cqw" }} transition={{ duration: 0.45, ease: SUAVE }}>
            <p className="text-[1.5cqw] font-semibold tracking-[-0.02em]">Fuera por inestable</p>
            {clasico && (
              <>
                <p className="mt-[0.8cqw] font-semibold">%LAA-950 clásico</p>
                <ul className="mt-[0.3cqw]">
                  <ConQue si={false}>estable: {num(clasico.icc, 2)}</ConQue>
                  <ConQue si>se asocia: {q(clasico.q)}</ConQue>
                </ul>
              </>
            )}
            {pi10 && grosor && (
              <>
                <p className="mt-[0.8cqw] font-semibold">Pi10 y grosor de pared</p>
                <ul className="mt-[0.3cqw]">
                  <ConQue si={false}>
                    estables: {num(pi10.icc, 2)} y {num(grosor.icc, 2)}
                  </ConQue>
                  <ConQue si={false}>
                    se asocian: q = {num(pi10.q, 2)} y {num(grosor.q, 2)}
                  </ConQue>
                </ul>
              </>
            )}
            <p className="mt-[0.8cqw] text-[1.05cqw] text-tinta-3">Estable: acuerdo de {num(embudo.criterios.acuerdo_minimo, 2)} o más entre los dos filtros.</p>
          </motion.div>
          <motion.div className={`${caja} right-[6cqw]`} initial={false} animate={{ opacity: clic === 1 ? 1 : 0, x: clic === 1 ? 0 : "1cqw" }} transition={{ duration: 0.45, ease: SUAVE }}>
            <p className="text-[1.5cqw] font-semibold tracking-[-0.02em]">Fuera por redundante</p>
            {vascular && (
              <>
                <p className="mt-[0.8cqw] font-semibold">Volumen vascular</p>
                <ul className="mt-[0.3cqw]">
                  <ConQue si>estable: {num(vascular.icc, 2)}</ConQue>
                  <ConQue si>se asocia: {q(vascular.q)}</ConQue>
                  <ConQue si={false}>
                    aporta algo nuevo: descontando las dos,
                    <br />
                    <span className="whitespace-nowrap">
                      {num(vascular.rho_descontando, 2)} (p = {pValor(vascular.p_descontando)})
                    </span>
                  </ConQue>
                </ul>
              </>
            )}
          </motion.div>
        </motion.div>
      )}

      {curva.length > 0 && (
        <motion.div initial={false} animate={{ opacity: clic >= 2 ? 1 : 0 }} transition={{ duration: 0.5, delay: clic >= 2 ? 0.25 : 0 }} className="pointer-events-none absolute inset-0">
          <Dibujo descripcion="La AUC fuera de muestra según cuántas medidas entran en el modelo. Ninguna medida añadida supera a las dos. Aparte, el modelo que aprende los pesos de todas las medidas, más bajo y mucho menos estable entre los dos filtros del escáner.">
            <text x={96} y={300} fontSize={24} fill={GRIS_OSCURO}>
              AUC fuera de muestra
            </text>
            {[0.8, 0.85, 0.9, 0.95].map((marca) => (
              <g key={marca}>
                <line x1={250} x2={1450} y1={yAuc(marca)} y2={yAuc(marca)} stroke={LINEA} strokeWidth={1.5} />
                <text x={232} y={yAuc(marca) + 8} textAnchor="end" fontSize={22} fill={GRIS_OSCURO}>
                  {num(marca, 2)}
                </text>
              </g>
            ))}
            <polyline points={curva.map((m) => `${xMedidas(m.n)},${yAuc(m.auc)}`).join(" ")} fill="none" stroke={TINTA} strokeWidth={3} />
            {curva.map((m) => (
              <g key={m.n}>
                <circle cx={xMedidas(m.n)} cy={yAuc(m.auc)} r={m.n === 2 ? 15 : 10} fill={m.n === 2 ? TINTA : PAPEL} stroke={TINTA} strokeWidth={3} />
                <text x={xMedidas(m.n)} y={yAuc(m.auc) - 26} textAnchor="middle" fontSize={m.n === 2 ? 34 : 26} fontWeight={m.n === 2 ? 600 : 400} fill={TINTA}>
                  {num(m.auc, 2)}
                </text>
                <text x={xMedidas(m.n)} y={736} textAnchor="middle" fontSize={26} fontWeight={m.n === 2 ? 600 : 400} fill={TINTA}>
                  {m.n}
                </text>
                <text x={xMedidas(m.n)} y={772} textAnchor="middle" fontSize={20} fill={GRIS_OSCURO}>
                  {num(m.icc, 2)}
                </text>
              </g>
            ))}
            <text x={xMedidas(2)} y={yAuc(curva.find((m) => m.n === 2)?.auc ?? 0.9) + 46} textAnchor="middle" fontSize={22} fontWeight={600} fill={TINTA}>
              el modelo
            </text>
            {(() => {
              const [una, dos] = [curva.find((m) => m.n === 1), curva.find((m) => m.n === 2)];
              return una && dos ? (
                <text x={470} y={318} fontSize={20} fill={GRIS_OSCURO}>
                  Una sola separa igual, pero sigue peor el cociente: {num(una.rho_fev1_fvc, 2)} frente a {num(dos.rho_fev1_fvc, 2)}.
                </text>
              ) : null;
            })()}

            <text x={xMedidas(1)} y={736} textAnchor="end" dx={-40} fontSize={22} fill={GRIS_OSCURO}>
              medidas
            </text>
            <text x={xMedidas(1)} y={772} textAnchor="end" dx={-40} fontSize={20} fill={GRIS_OSCURO}>
              acuerdo entre filtros
            </text>
            {todas && (
              <g>
                <line x1={1240} x2={1240} y1={330} y2={790} stroke={LINEA} strokeWidth={2} strokeDasharray="4 8" />
                <rect x={xTodas - 10} y={yAuc(todas.auc) - 10} width={20} height={20} fill={PAPEL} stroke={TINTA} strokeWidth={3} transform={`rotate(45 ${xTodas} ${yAuc(todas.auc)})`} />
                <text x={xTodas} y={yAuc(todas.auc) - 26} textAnchor="middle" fontSize={26} fill={TINTA}>
                  {num(todas.auc, 2)}
                </text>
                <text x={xTodas} y={736} textAnchor="middle" fontSize={22} fill={TINTA}>
                  todas, pesos aprendidos
                </text>
                <text x={xTodas} y={772} textAnchor="middle" fontSize={20} fontWeight={600} fill={TINTA}>
                  {num(todas.icc, 2)}
                </text>
              </g>
            )}
            {/* La curva no baja en cada paso (de 3 a 4 medidas sube): lo que se afirma es que ninguna supera a las dos. */}
            <text x={96} y={836} fontSize={30} fontWeight={600} fill={TINTA}>
              Ninguna medida añadida supera a las dos fuera de muestra.
            </text>
            {todas && (
              <text x={96} y={874} fontSize={24} fill={TINTA}>
                Con pesos aprendidos, el acuerdo entre los dos filtros del escáner cae a {num(todas.icc, 2)}.
              </text>
            )}
            <text x={1504} y={836} textAnchor="end" fontSize={18} fill={GRIS_OSCURO}>
              Validación cruzada de 5 grupos, {complejidad?.repeticiones ?? 5} repeticiones.
            </text>
          </Dibujo>
        </motion.div>
      )}
      {clic >= 2 && curva.length === 0 && <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Pendiente: esta cohorte no trae la comparación por número de medidas.</p>}
    </>
  );
}

// 10. La misma puntuación, dos lecturas (opcional). Las cifras de cada barra están en el anexo.
function BarraDeLectura({ x0, y, nombre, rho, fuerte }: { x0: number; y: number; nombre: string; rho: number | undefined; fuerte: boolean }) {
  if (rho === undefined) return null;
  const centro = x0 + 500;
  const largo = Math.max(Math.min(Math.abs(rho), 1) * 170, 4);
  return (
    <g>
      <text x={x0} y={y + 12} fontSize={36} fontWeight={fuerte ? 600 : 400} fill={fuerte ? TINTA : GRIS_OSCURO}>
        {nombre}
      </text>
      <rect x={centro - 170} y={y - 20} width={340} height={40} rx={20} fill="#f3f1ec" />
      <motion.rect x={rho < 0 ? centro - largo : centro} y={y - 20} height={40} rx={20} fill={fuerte ? TINTA : GRIS} initial={{ width: 0 }} animate={{ width: largo }} transition={{ duration: 0.7, delay: 0.3, ease: SUAVE }} />
      <line x1={centro} x2={centro} y1={y - 30} y2={y + 30} stroke={GRIS_OSCURO} strokeWidth={2} />
    </g>
  );
}

export function DosLecturas({ cohorte, clic }: PropsDiapositiva) {
  const filas = (grupo: "casos" | "controles", variables: [string, string][]) => variables.map(([clave, nombre]) => ({ nombre, rho: lectura(cohorte, grupo, clave)?.rho }));
  // Dos barras por lado. Las demás (enfisema visible, fumar ahora) y todas las cifras están en el anexo.
  const epoc = filas("casos", [["Disnea", "Disnea"], ["DLCO", "Difusión (DLCO)"]]);
  const sin = filas("controles", [["Calibre central", "Calibre estrecho"], ["Paquetes-año", "Tabaco"]]);
  const titulo = { fontSize: 44, fontWeight: 600, fill: TINTA, letterSpacing: "-0.02em" };

  return (
    <>
      <Frase>
        La misma puntuación, dos lecturas.
        <span className="ml-[1.2cqw] inline-block rounded-full border-[0.14cqw] border-dashed border-tinta-3 px-[1cqw] py-[0.3cqw] align-middle text-[1.2cqw] font-medium tracking-normal text-tinta-2">exploratorio</span>
      </Frase>
      {!cohorte.discordantes && <p className="absolute top-[24cqw] left-[6cqw] text-[1.6cqw] text-tinta-2">Pendiente: esta cohorte no trae este análisis.</p>}
      <Dibujo descripcion="Con qué va la puntuación. En quien tiene EPOC, con más disnea y una peor difusión. En quien no tiene obstrucción, la hipótesis es que pese más el calibre de la vía que los paquetes-año de tabaco.">
        <text x={96} y={350} {...titulo}>
          Con EPOC: gravedad
        </text>
        {epoc.map((fila, i) => (
          <BarraDeLectura key={fila.nombre} x0={96} y={490 + 150 * i} nombre={fila.nombre} rho={fila.rho} fuerte />
        ))}
        <Paso visible={clic >= 1}>
          <line x1={800} x2={800} y1={300} y2={770} stroke={LINEA} strokeWidth={2} />
          {/* Una hipótesis, no una explicación: son correlaciones exploratorias con pocos sujetos. */}
          <text x={860} y={350} {...titulo}>
            Sin obstrucción
          </text>
          <text x={860} y={394} fontSize={26} fill={GRIS_OSCURO}>
            Hipótesis: calibre de la vía más que tabaco
          </text>
          {clic >= 1 && sin.map((fila, i) => <BarraDeLectura key={fila.nombre} x0={860} y={490 + 150 * i} nombre={fila.nombre} rho={fila.rho} fuerte={i === 0} />)}
        </Paso>
        <text x={96} y={840} fontSize={22} fill={GRIS_OSCURO}>
          A la derecha del centro, más puntuación va con más de eso. A la izquierda, con menos.
        </text>
      </Dibujo>
    </>
  );
}

// 11. Tres conclusiones y una pregunta para el jurado.
function Glifo({ tipo }: { tipo: "estable" | "sigue" | "duda" }) {
  return (
    <svg viewBox="0 0 60 60" className="size-[4.2cqw] shrink-0" aria-hidden>
      <circle cx={30} cy={30} r={29} fill="#f3f1ec" />
      {tipo === "estable" &&
        [20, 30, 40].map((y) => <line key={y} x1={14} x2={46} y1={y} y2={y} stroke={y === 30 ? DANO : TINTA} strokeWidth={3} strokeLinecap="round" />)}
      {tipo === "sigue" &&
        [
          [15, 16],
          [22, 24],
          [29, 27],
          [36, 36],
          [44, 43],
        ].map(([x, y]) => <circle key={x} cx={x} cy={y} r={4} fill={TINTA} />)}
      {tipo === "duda" && (
        <text x={30} y={42} textAnchor="middle" fontSize={34} fontWeight={600} fill={TINTA}>
          ?
        </text>
      )}
    </svg>
  );
}

export function Conclusiones({ cohorte, clic, abrir, alAnexo }: PropsDiapositiva) {
  // La integración con la clínica: `docs/cifras.md`, "Menos es más". La clínica básica es edad, sexo, talla, IMC y tabaco.
  const sola = modeloDeComplejidad(cohorte.complejidad, "2 medidas");
  const conClinica = modeloDeComplejidad(cohorte.complejidad, "clínica y las dos medidas de TC");
  const ampliada = modeloDeComplejidad(cohorte.complejidad, "clínica ampliada y las dos medidas de TC");
  const todas = modeloDeComplejidad(cohorte.complejidad, "logística con todas las medidas de TC");
  const conclusiones: { tipo: "estable" | "sigue" | "duda"; frase: string; detalle?: string }[] = [
    {
      tipo: "sigue",
      frase: "Dos medidas de la TC reproducen la espirometría.",
      detalle: `AUC ${num(sola?.auc, 2)} en gente que el modelo no vio. Correlación con el FEV1/FVC: 0,17 con la clínica sola, ${num(Math.abs(correlacionPrincipal(cohorte)?.rho ?? NaN), 2)} con la TC.`,
    },
    {
      tipo: "estable",
      frase: "Un poco de clínica ayuda; más medidas, no.",
      detalle: `Con edad, sexo, talla, IMC y tabaco, ${num(conClinica?.auc, 2)}. Con síntomas, DLCO y FENO baja a ${num(ampliada?.auc, 2)}; con las 27 medidas de TC, ${num(todas?.auc, 2)}.`,
    },
    {
      tipo: "estable",
      frase: "Es una medida objetiva.",
      detalle: "Da lo mismo con los dos filtros del escáner: 0,98, frente a 0,18 del %LAA-950 clásico.",
    },
    {
      tipo: "duda",
      // Es un corte transversal: no se dice "antes de que aparezca".
      frase: "14 posibles pre-EPOC. Falta saber si la TC se adelanta.",
      detalle: "Sin obstrucción y con la TC alterada. Para saber si enferman antes hace falta seguir a la cohorte entera.",
    },
  ];
  return (
    <>
      <Frase>Conclusiones.</Frase>
      <ol className="absolute top-[13cqw] left-[6cqw] flex w-[50cqw] flex-col gap-[1.4cqw]">
        {conclusiones.map((conclusion, i) => (
          <motion.li key={i} className="flex items-center gap-[1.4cqw]" initial={false} animate={{ opacity: clic >= i ? 1 : 0, x: clic >= i ? 0 : "-1cqw" }} transition={{ duration: 0.45, ease: SUAVE }}>
            <Glifo tipo={conclusion.tipo} />
            <span>
              <span className="block text-[1.9cqw] leading-[1.15] font-semibold tracking-[-0.02em]">{conclusion.frase}</span>
              {conclusion.detalle && <span className="mt-[0.3cqw] block text-[1.25cqw] leading-[1.25] text-tinta-2">{conclusion.detalle}</span>}
            </span>
          </motion.li>
        ))}
      </ol>
      <motion.div className="absolute top-[13cqw] right-[6cqw] w-[32cqw] rounded-[1.2cqw] bg-fondo px-[2cqw] py-[1.8cqw]" initial={false} animate={{ opacity: clic >= 4 ? 1 : 0, y: clic >= 4 ? 0 : "1cqw" }} transition={{ duration: 0.5, ease: SUAVE }}>
        <p className="text-[0.95cqw] font-medium tracking-[0.05em] text-tinta-3 uppercase">El tabaco</p>
        <p className="mt-[0.4cqw] text-[2cqw] leading-[1.15] font-semibold tracking-[-0.02em]">
          Más tabaco apenas separa <span className="text-dano-tinta">a quién tiene EPOC.</span>
        </p>
        <ul className="mt-[1cqw] flex flex-col gap-[0.7cqw] text-[1.15cqw] leading-[1.35] text-tinta-2">
          <li>
            <strong className="font-semibold text-tinta">Por cómo es la cohorte:</strong> todos fuman o fumaron más de 10 paquetes-año y tienen de 35 a 50 años. Los paquetes-año separan poco la EPOC (AUC 0,66).
          </li>
          <li>Dentro de la EPOC, la TC está más alterada en quien fumó <strong className="font-semibold text-tinta">menos</strong> (−0,58, descontando edad y fumar ahora).</li>
          <li>Hipótesis: susceptibilidad. Sin obstrucción, la puntuación va con vías estrechas para su pulmón, no con el tabaco; la vía aérea pequeña multiplica el riesgo de EPOC (Smith, JAMA 2020).</li>
        </ul>
        <p className="mt-[1cqw] border-t border-linea pt-[0.9cqw] text-[1cqw] leading-[1.35] text-tinta-3">
          Alternativa: los más graves fumaron menos o lo dejaron antes. Con un solo corte no se distinguen.
        </p>
      </motion.div>
      <motion.div className="absolute right-[6cqw] bottom-[2.6cqw] flex gap-[0.8cqw]" initial={false} animate={{ opacity: clic >= 4 ? 1 : 0 }}>
        <button
          type="button"
          className="btn btn-linea !h-[3cqw] !px-[1.5cqw] !text-[1.1cqw]"
          onClick={(evento) => {
            evento.stopPropagation();
            alAnexo();
          }}
        >
          Anexo para preguntas
        </button>
        <button
          type="button"
          className="btn btn-tinta !h-[3cqw] !px-[1.6cqw] !text-[1.1cqw]"
          onClick={(evento) => {
            evento.stopPropagation();
            abrir(RUTA_COHORTE);
          }}
        >
          Abrir la aplicación <span aria-hidden>→</span>
        </button>
      </motion.div>
    </>
  );
}
