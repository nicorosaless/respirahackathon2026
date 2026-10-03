"use client";

// Inferencia, persona a persona. Primero tres personas de la cohorte, una de cada clase, con todo a la vista.
// Después, una persona que el modelo probado no vio, paso a paso hasta revelar su espirometría.

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Contraste } from "@/components/Contraste";
import { Criterios } from "@/components/Criterios";
import { Cascada, DondeEsta, MapaLobular } from "@/components/plataforma/Explicacion";
import { DosMedidas, Entra, Espirometria, NivelDeLaTC, TCDeLaPersona } from "@/components/plataforma/Persona";
import { EtiquetaClase } from "@/components/ui";
import { CLASES, type Clase, type Cohorte, ejemplosDeClase, ejemplosDeInferencia, NOMBRE_CLASE, type Sujeto, useCohorte } from "@/lib/cohorte";
import { num } from "@/lib/formato";
import { describirPersona, lecturaDeInferencia, lecturaDelModeloFinal, tablaDeContraste, veredicto } from "@/lib/inferencia";
import { leerVuelta, type Vuelta } from "@/lib/sesion";

// Las cuatro personas de la sección: una de cada clase y la que el modelo no vio.
type Vista = Clase | "nueva";
const VISTAS: Vista[] = [...CLASES, "nueva"];
// El recorrido de la persona nueva: cada paso añade una cosa y el último revela la espirometría.
const PASOS = ["La TC", "Segmentación", "Medidas", "Lo esperado", "Su TC es", "Espirometría"];
const ULTIMO = PASOS.length;

/** Un selector discreto para cambiar de persona entre las que también valdrían. */
function OtraPersona({ sujetos, elegido, alElegir }: { sujetos: Sujeto[]; elegido: Sujeto; alElegir: (id: string) => void }) {
  if (sujetos.length < 2) return null;
  return (
    <label className="flex items-center gap-2 text-xs text-tinta-3">
      Otra persona
      <select className="cursor-pointer rounded-full border border-linea-2 bg-white px-2.5 py-1 text-xs text-tinta" value={elegido.id} onChange={(evento) => alElegir(evento.target.value)}>
        {sujetos.map((s) => (
          <option key={s.id} value={s.id}>
            {s.id}
          </option>
        ))}
      </select>
    </label>
  );
}

// El recorrido de una persona de la cohorte: cada flecha descubre una pieza más, y la última es su espirometría.
const PASOS_COHORTE = ["La persona", "Enfisema", "Árbol bronquial", "Por qué esta puntuación", "Su TC es", "La espirometría"];

/** Un dato de la persona, grande para leerse desde lejos. */
function Dato({ nombre, valor }: { nombre: string; valor: string }) {
  return (
    <div className="min-w-0 rounded-md bg-fondo px-3 py-3">
      <p className="text-xs font-medium tracking-wide text-tinta-3 uppercase">{nombre}</p>
      <p className="mt-0.5 truncate text-xl font-semibold tracking-tight tabular-nums">{valor}</p>
    </div>
  );
}

/** Una persona de la cohorte, paso a paso: quién es, sus dos medidas, de qué sale su puntuación, si su TC pasa el umbral y, al final, su espirometría y su clase. */
function PersonaDeLaCohorte({ cohorte, sujeto, paso }: { cohorte: Cohorte; sujeto: Sujeto; paso: number }) {
  const lectura = lecturaDelModeloFinal(sujeto, cohorte);
  const { clinica } = sujeto;
  const hombre = clinica.sexo === "H";
  // Lo último que se descubre queda a la vista aunque el panel ya sea más alto que la pantalla.
  const final = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (paso > 1) final.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [paso]);
  return (
    <div className="flex flex-col gap-3">
      <p className="flex flex-wrap items-center gap-2.5 text-sm text-tinta-2">
        <strong className="text-lg font-semibold text-tinta">{sujeto.id}</strong>
        {paso >= 6 && <EtiquetaClase clase={sujeto.clase} />}
      </p>
      {paso === 1 ? (
        <div className="grid grid-cols-4 gap-2">
          <Dato nombre="Edad" valor={clinica.edad === null ? "sin dato" : `${num(clinica.edad, 0)} años`} />
          <Dato nombre="Sexo" valor={hombre ? "Hombre" : "Mujer"} />
          <Dato nombre="Talla" valor={clinica.talla === null ? "sin dato" : `${num(clinica.talla, 0)} cm`} />
          <Dato nombre="Tabaco" valor={clinica.fuma ? (hombre ? "Fumador" : "Fumadora") : hombre ? "Exfumador" : "Exfumadora"} />
        </div>
      ) : (
        <p className="-mt-2 text-base text-tinta-2">
          {describirPersona(clinica)[0].toUpperCase()}
          {describirPersona(clinica).slice(1)}.
        </p>
      )}
      {paso === 1 && <p className="text-sm text-tinta-3">Con la flecha derecha se ve qué dice su TC frente a lo esperado para alguien así.</p>}
      {paso >= 2 && (
        <Entra>
          <DosMedidas sujeto={sujeto} lectura={lectura} conEsperado solo="enfisema" />
        </Entra>
      )}
      {paso >= 3 && (
        <Entra>
          <DosMedidas sujeto={sujeto} lectura={lectura} conEsperado solo="via" />
        </Entra>
      )}
      {paso >= 4 && (
        <Entra>
          <Cascada lectura={lectura} />
        </Entra>
      )}
      {paso >= 5 && (
        <Entra>
          <NivelDeLaTC lectura={lectura} nota="La puntuación no usa su espirometría." />
        </Entra>
      )}
      {paso >= 6 && (
        <Entra>
          <Espirometria sujeto={sujeto}>
            <p className="mt-1.5 text-sm leading-snug text-tinta-2">
              <strong className="font-semibold text-tinta">Clase: {NOMBRE_CLASE[sujeto.clase]}.</strong> {sujeto.motivo}
            </p>
          </Espirometria>
        </Entra>
      )}
      <div ref={final} className="h-px" aria-hidden />
    </div>
  );
}

/** La persona que el modelo no vio, paso a paso. Todo lo que se enseña de ella sale del modelo que se probó sin ella. */
function PasoAPaso({ cohorte, sujeto, paso, revelar, vuelta }: { cohorte: Cohorte; sujeto: Sujeto; paso: number; revelar: () => void; vuelta: string | null }) {
  const lectura = lecturaDeInferencia(sujeto, cohorte);
  const resultado = veredicto({ dano_tc: lectura.dano_tc, caso: sujeto.caso });

  return (
    <div className="flex min-h-[24rem] flex-col">
      <p className="text-sm text-tinta-2">
        <strong className="text-base font-semibold text-tinta">{sujeto.id}</strong>: {describirPersona(sujeto.clinica)}.
        {lectura.delModeloProbado && ` El modelo se ajustó con ${lectura.sujetosDeAjuste} sujetos, sin esta persona.`}
      </p>

      {paso === 1 && <p className="mt-3 text-sm leading-relaxed text-tinta-3">Su TC, tal como sale del escáner. Se avanza con la flecha derecha o con los pasos de arriba.</p>}
      {paso === 2 && (
        <Entra className="mt-3 text-sm leading-relaxed text-tinta-2">Una red ya entrenada separa los cinco lóbulos y el árbol bronquial.</Entra>
      )}
      {paso >= 3 && (
        <Entra className="mt-1">
          <DosMedidas sujeto={sujeto} lectura={lectura} conEsperado={paso >= 4} />
        </Entra>
      )}
      {paso >= 5 && (
        <Entra className="mt-3">
          <NivelDeLaTC
            lectura={lectura}
            nota={`${lectura.puntuacion === null ? "" : lectura.dano_tc ? "Por encima del umbral: se parece a las de la EPOC. No demuestra una lesión." : "Por debajo del umbral."} ${
              lectura.delModeloProbado
                ? "Lo esperado y los umbrales se fijaron sin ver a esta persona."
                : "Esta cohorte no trae la lectura del modelo que se probó en reserva: estos valores son del modelo final, que sí se ajustó con esta persona."
            }`}
          />
        </Entra>
      )}
      {paso >= 5 && (
        <Entra className="mt-3">
          <Cascada lectura={lectura} />
        </Entra>
      )}
      {paso === 5 && (
        <Entra className="mt-3">
          <button type="button" className="btn btn-tinta" onClick={revelar}>
            Revelar espirometría
          </button>
        </Entra>
      )}
      {paso >= ULTIMO && (
        <Entra className="mt-3">
          <Espirometria sujeto={sujeto}>
            <div className="mt-1.5 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
              <p className="max-w-xl text-sm leading-snug">
                {lectura.puntuacion === null ? (
                  <span className="text-tinta-2">Sin puntuación de la TC no hay nada que contrastar con la espirometría.</span>
                ) : (
                  <>
                    <strong className="font-semibold">{resultado.titulo}.</strong> <span className="text-tinta-2">{resultado.texto}</span>
                  </>
                )}
              </p>
              {vuelta && (
                <Link href={vuelta} className="btn btn-tinta btn-s">
                  Conclusiones →
                </Link>
              )}
            </div>
          </Espirometria>
        </Entra>
      )}
    </div>
  );
}

function PrimeraPrueba({ cohorte }: { cohorte: Cohorte }) {
  const { reserva } = cohorte;
  if (!reserva) return null;
  return (
    <details className="tarjeta group">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
        <span className="grid size-6 place-items-center rounded-full border border-linea-2 text-xs text-tinta-2 transition-transform group-open:rotate-90">→</span>
        <span className="text-sm font-semibold">El resultado en los {reserva.sujetos} que el modelo no vio</span>
        <span className="text-sm text-tinta-3">La primera prueba, con lo que se fijó antes de mirar</span>
      </summary>
      <div className="grid items-start gap-x-10 gap-y-5 border-t border-linea p-5 lg:grid-cols-[auto_1fr]">
        <Contraste casillas={tablaDeContraste(reserva)} className="text-base" />
        <div>
          <Criterios reserva={reserva} className="text-sm" />
          <p className="mt-3 text-xs leading-relaxed text-tinta-3">
            La clase EPOC la pone la espirometría, no la TC: lo que se contrasta es si la TC se parece a la de la EPOC y si hay obstrucción. Son {reserva.sujetos} sujetos: los intervalos son anchos. Después el modelo se reajustó con todos.
            {cohorte.aviso && " Estas cifras son las de la cohorte del reto; las personas de arriba son simuladas."}
          </p>
        </div>
      </div>
    </details>
  );
}

export default function VistaInferencia() {
  const router = useRouter();
  const { cohorte } = useCohorte();
  const [vista, setVista] = useState<Vista>("control");
  const [paso, setPaso] = useState(1);
  // La persona elegida en cada vista, si no es la que se abre por defecto.
  const [elegidos, setElegidos] = useState<Partial<Record<Vista, string>>>({});
  const [vuelta, setVuelta] = useState<Vuelta>({ ruta: "/", anterior: "/", desdePresentacion: false });
  // La URL manda al abrir (`?persona=nueva&id=…&paso=3`); después manda lo que se elige.
  const [leida, setLeida] = useState(false);

  useEffect(() => {
    const parametros = new URLSearchParams(window.location.search);
    const pedida = parametros.get("persona") as Vista | null;
    const inicial = pedida && VISTAS.includes(pedida) ? pedida : "control";
    setVista(inicial);
    const id = parametros.get("id");
    if (id) setElegidos({ [inicial]: id });
    setPaso(Math.min(Math.max(Number(parametros.get("paso") ?? 1) || 1, 1), ULTIMO));
    setVuelta(leerVuelta());
    setLeida(true);
  }, []);

  const candidatos = cohorte ? (vista === "nueva" ? ejemplosDeInferencia(cohorte) : ejemplosDeClase(cohorte, vista)) : [];
  const sujeto = candidatos.find((s) => s.id === elegidos[vista]) ?? cohorte?.sujetos.find((s) => s.id === elegidos[vista] && (vista === "nueva" || s.clase === vista)) ?? candidatos[0];

  useEffect(() => {
    if (!leida) return;
    const parametros = new URLSearchParams({ persona: vista });
    if (sujeto) parametros.set("id", sujeto.id);
    if (paso > 1) parametros.set("paso", String(paso));
    window.history.replaceState(null, "", `?${parametros.toString()}`);
  }, [leida, vista, sujeto, paso]);

  /** Un paso adelante o atrás por la sección: las tres personas y, después, los seis pasos de la que el modelo no vio. */
  const mover = useCallback(
    (cuanto: 1 | -1) => {
      const indice = VISTAS.indexOf(vista);
      if ((cuanto === 1 && paso < ULTIMO) || (cuanto === -1 && paso > 1)) return setPaso(paso + cuanto);
      const destino = VISTAS[indice + cuanto];
      if (destino) {
        setVista(destino);
        setPaso(cuanto === 1 ? 1 : ULTIMO);
      } else if (vuelta.desdePresentacion) router.push(cuanto === 1 ? vuelta.ruta : "/plataforma");
    },
    [vista, paso, vuelta, router],
  );

  useEffect(() => {
    const alPulsar = (evento: KeyboardEvent) => {
      if (evento.metaKey || evento.ctrlKey || evento.altKey || evento.target instanceof HTMLSelectElement) return;
      if (evento.key !== "ArrowRight" && evento.key !== "ArrowLeft") return;
      evento.preventDefault();
      mover(evento.key === "ArrowRight" ? 1 : -1);
    };
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [mover]);

  if (!cohorte) return null;
  const pestana = (activa: boolean) =>
    `flex h-9 cursor-pointer items-center gap-2 rounded-full border px-3.5 text-sm font-medium whitespace-nowrap transition-colors ${activa ? "border-tinta bg-tinta text-white" : "border-linea-2 bg-white text-tinta hover:border-tinta"}`;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
        <Link href={vuelta.ruta} className="flex h-9 items-center text-sm text-tinta-2 hover:text-tinta">
          ← Presentación
        </Link>
        {/* La diapositiva de conclusiones es la 10 del recorrido en vivo (`components/deck/Deck.tsx`). */}
        <Link href="/?d=10" className="order-last ml-auto flex h-9 items-center gap-1.5 rounded-full bg-tinta px-4 text-sm font-medium text-white hover:bg-tinta/85">
          Conclusiones <span aria-hidden>→</span>
        </Link>
        <div>
          <p className="mb-1.5 text-xs font-medium tracking-wide text-tinta-3 uppercase">Tres personas de la cohorte</p>
          <div className="flex gap-1.5" role="tablist" aria-label="Una persona de cada clase">
            {CLASES.map((clase) => (
              <button key={clase} type="button" role="tab" aria-selected={vista === clase} className={pestana(vista === clase)} onClick={() => (setVista(clase), setPaso(1))}>
                {NOMBRE_CLASE[clase][0].toUpperCase()}
                {NOMBRE_CLASE[clase].slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-medium tracking-wide text-tinta-3 uppercase">Una que el modelo no vio</p>
          <button
            type="button"
            role="tab"
            aria-selected={vista === "nueva"}
            className={pestana(vista === "nueva")}
            onClick={() => {
              setVista("nueva");
              setPaso(1);
            }}
          >
            Paso a paso
          </button>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {sujeto && <OtraPersona sujetos={candidatos} elegido={sujeto} alElegir={(id) => (setElegidos({ ...elegidos, [vista]: id }), setPaso(1))} />}
          <div className="flex gap-1.5">
            <button type="button" className="btn btn-linea btn-s !px-2.5" onClick={() => mover(-1)} aria-label="Anterior" title="Anterior (flecha izquierda)">
              ←
            </button>
            <button type="button" className="btn btn-tinta btn-s !px-2.5" onClick={() => mover(1)} aria-label="Siguiente" title="Siguiente (flecha derecha)">
              →
            </button>
          </div>
        </div>
      </div>

      {!sujeto ? (
        <div className="tarjeta p-6">
          <h1 className="text-xl font-semibold tracking-tight">{vista === "nueva" ? "Esta cohorte no trae personas apartadas" : `No hay nadie de la clase ${NOMBRE_CLASE[vista]} que enseñar`}</h1>
          <p className="mt-1.5 text-sm text-tinta-2">
            {vista === "nueva" ? "Ningún sujeto de cohorte.json tiene la partición «reserva». Las tres personas de la cohorte sí se pueden ver." : "cohorte.json no tiene ningún sujeto con puntuación en esa clase."}
          </p>
        </div>
      ) : (
        <div className="grid items-start gap-5 min-[1100px]:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
          {vista === "nueva" ? (
            <section className="tarjeta p-4">
              <TCDeLaPersona cohorte={cohorte} sujeto={sujeto} segmentada={paso >= 2} />
            </section>
          ) : (
            <div className="flex flex-col gap-5">
              <section className="tarjeta p-4">
                <MapaLobular cohorte={cohorte} sujeto={sujeto} />
              </section>
              <section className="tarjeta p-5">
                <DondeEsta cohorte={cohorte} sujeto={sujeto} />
              </section>
            </div>
          )}
          <section className="tarjeta p-5">
            {vista === "nueva" && (
              <ol className="mb-4 flex flex-wrap gap-1" aria-label="Pasos">
                {PASOS.map((nombre, i) => (
                  <li key={nombre}>
                    <button
                      type="button"
                      className={`flex h-7 cursor-pointer items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium whitespace-nowrap transition-colors ${
                        i + 1 === paso ? "border-tinta bg-tinta text-white" : i + 1 < paso ? "border-tinta bg-white text-tinta" : "border-linea-2 bg-white text-tinta-3"
                      }`}
                      aria-current={i + 1 === paso ? "step" : undefined}
                      onClick={() => setPaso(i + 1)}
                    >
                      <span className="font-mono text-[10px] opacity-70">{i + 1}</span>
                      {nombre}
                    </button>
                  </li>
                ))}
              </ol>
            )}
            {vista !== "nueva" && (
              <div className="mb-4 flex items-center gap-3 border-b border-linea pb-3">
                <p className="text-sm font-semibold">{PASOS_COHORTE[paso - 1]}</p>
                <div className="ml-auto flex items-center gap-2">
                  <span className="text-sm text-tinta-3 tabular-nums" aria-live="polite">
                    {paso} / {ULTIMO}
                  </span>
                  <button type="button" className="btn btn-linea btn-s !px-2.5" onClick={() => mover(-1)} aria-label="Paso anterior" title="Paso anterior (flecha izquierda)">
                    ←
                  </button>
                  <button type="button" className="btn btn-tinta btn-s !px-2.5" onClick={() => mover(1)} aria-label="Paso siguiente" title="Paso siguiente (flecha derecha)">
                    →
                  </button>
                </div>
              </div>
            )}
            <AnimatePresence mode="wait">
              <motion.div key={`${vista}-${sujeto.id}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                {vista === "nueva" ? (
                  <PasoAPaso cohorte={cohorte} sujeto={sujeto} paso={paso} revelar={() => setPaso(ULTIMO)} vuelta={vuelta.desdePresentacion ? vuelta.ruta : null} />
                ) : (
                  <PersonaDeLaCohorte cohorte={cohorte} sujeto={sujeto} paso={paso} />
                )}
              </motion.div>
            </AnimatePresence>
          </section>
        </div>
      )}

      {vista === "nueva" && <PrimeraPrueba cohorte={cohorte} />}
    </div>
  );
}
