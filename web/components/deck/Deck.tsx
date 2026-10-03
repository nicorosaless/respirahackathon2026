"use client";

import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Marca } from "@/components/ui";
import { useCohorte } from "@/lib/cohorte";
import { guardarVuelta, leerReloj, moverReloj, type Reloj, RELOJ_PARADO, SEGUNDOS_DE_DEMO } from "@/lib/sesion";
import { Artefactos, DatosYMetodo, LoQuePideElReto, PorQueNoShap, ViasFinas } from "./anexo";
import { ACiegas, EmbudoEntero, Generalizacion, Indice, Integracion, LimiteInferior, MedidasDelReto, PaquetesAno, Seguimiento, UsoDeIA, Validacion } from "./banco";
import { DosLecturasConCifras, Limites } from "./diapositivas";
import { type Cuadro, geometria as calcularGeometria } from "@/lib/escena";
import type { PropsDiapositiva } from "./piezas";
import { Puntos } from "./Puntos";
import { CurvaYMatriz, ElModelo, PorQueEste } from "./modelo";
import { Ciego, Conclusiones, Cuadrantes, Frontera, MirarLaTC, Nube, RUTA_COHORTE, RUTA_INFERENCIA, Soplar } from "./vivo";

interface Entrada {
  titulo: string;
  /** Cuántos pasos tiene dentro, además del primero, antes de pasar a la siguiente. */
  clics: number;
  Contenido: (props: PropsDiapositiva) => React.ReactNode;
  /** El dibujo en el que se ven los puntos de la cohorte. Sin él, los puntos se apagan. */
  cuadro?: Cuadro;
  /** Se puede saltar con la tecla S si falta tiempo. */
  opcional?: boolean;
}

// El recorrido en vivo: diez dibujos que se construyen por pasos y la aplicación antes de las conclusiones.
const EN_VIVO: Entrada[] = [
  { titulo: "Soplar", clics: 2, Contenido: Soplar, cuadro: "soplar" },
  { titulo: "Al otro lado", clics: 0, Contenido: Frontera, cuadro: "frontera", opcional: true },
  { titulo: "Su TC", clics: 4, Contenido: MirarLaTC },
  { titulo: "El modelo", clics: 2, Contenido: ElModelo },
  { titulo: "A ciegas", clics: 3, Contenido: Ciego, cuadro: "ciego" },
  { titulo: "Correlación", clics: 1, Contenido: Nube, cuadro: "nube" },
  { titulo: "Cuadrantes", clics: 3, Contenido: Cuadrantes, cuadro: "cuadrantes" },
  { titulo: "Validación", clics: 2, Contenido: CurvaYMatriz },
  { titulo: "Por qué este", clics: 1, Contenido: PorQueEste },
  { titulo: "Conclusiones", clics: 4, Contenido: Conclusiones },
];
// Las partes del guion. "Dos lecturas" pasó al anexo; la curva de crecimiento vive dentro de "El modelo".
const PARTES: { nombre: string; diapositivas: number[] }[] = [
  { nombre: "Problema", diapositivas: [0, 1] },
  { nombre: "La idea", diapositivas: [2, 3, 4] },
  { nombre: "Hallazgos", diapositivas: [5, 6] },
  { nombre: "Cómo está hecho", diapositivas: [7, 8] },
  { nombre: "Aplicación", diapositivas: [] },
  { nombre: "Conclusiones", diapositivas: [9] },
];
/** La diapositiva tras la que se abre la aplicación, y por la que se sigue al volver. */
const ANTES_DE_LA_APLICACION = 8;
const TRAS_LA_APLICACION = 9;
// El anexo: un banco de respuestas a las preguntas del jurado, con un índice delante. No cuenta en el cronómetro.
const ANEXO: Entrada[] = [
  { titulo: "Índice", clics: 0, Contenido: Indice },
  { titulo: "Validación", clics: 0, Contenido: Validacion },
  { titulo: "Dos medidas", clics: 0, Contenido: EmbudoEntero },
  { titulo: "A ciegas", clics: 0, Contenido: ACiegas },
  { titulo: "Integración", clics: 0, Contenido: Integracion },
  { titulo: "Artefactos", clics: 0, Contenido: Artefactos },
  { titulo: "Pre-EPOC", clics: 0, Contenido: Limites },
  { titulo: "LLN", clics: 0, Contenido: LimiteInferior },
  { titulo: "Seguimiento", clics: 0, Contenido: Seguimiento },
  { titulo: "Medidas", clics: 0, Contenido: MedidasDelReto },
  { titulo: "Lecturas", clics: 0, Contenido: DosLecturasConCifras },
  { titulo: "Paquetes-año", clics: 0, Contenido: PaquetesAno },
  { titulo: "Generalización", clics: 0, Contenido: Generalizacion },
  { titulo: "SHAP", clics: 0, Contenido: PorQueNoShap },
  { titulo: "Método", clics: 0, Contenido: DatosYMetodo },
  { titulo: "IA", clics: 0, Contenido: UsoDeIA },
  { titulo: "Ramas finas", clics: 0, Contenido: ViasFinas },
  { titulo: "El reto", clics: 0, Contenido: LoQuePideElReto },
];
const TODAS = [...EN_VIVO, ...ANEXO];

/** El número de una diapositiva en vivo, con la sección de la barra: 1.1, 1.2, 2.1… En el anexo, A1, A2… */
function numeroDe(diapositiva: number): string {
  if (diapositiva >= EN_VIVO.length) return `A${diapositiva - EN_VIVO.length + 1}`;
  const parte = PARTES.findIndex((p) => p.diapositivas.includes(diapositiva));
  return `${parte + 1}.${PARTES[parte].diapositivas.indexOf(diapositiva) + 1}`;
}
const PRIMERA_DEL_ANEXO = EN_VIVO.length;
const INDICE = PRIMERA_DEL_ANEXO;

interface Posicion {
  diapositiva: number;
  clic: number;
}

function leerPosicion(): Posicion {
  const parametros = new URLSearchParams(window.location.search);
  const diapositiva = Math.min(Math.max(Number(parametros.get("d") ?? 1) - 1 || 0, 0), TODAS.length - 1);
  const clic = Math.min(Math.max(Number(parametros.get("clicks") ?? 0) || 0, 0), TODAS[diapositiva].clics);
  return { diapositiva, clic };
}

function consulta({ diapositiva, clic }: Posicion): string {
  const parametros = new URLSearchParams();
  if (diapositiva > 0) parametros.set("d", String(diapositiva + 1));
  if (clic > 0) parametros.set("clicks", String(clic));
  const texto = parametros.toString();
  return texto ? `?${texto}` : "";
}

function Cronometro({ reloj }: { reloj: Reloj }) {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const intervalo = setInterval(() => setAhora(Date.now()), 250);
    return () => clearInterval(intervalo);
  }, []);
  const segundos = reloj.inicio === null ? 0 : Math.max(Math.floor(((reloj.fin ?? ahora) - reloj.inicio) / 1000), 0);
  return (
    <span className={`font-mono tabular-nums ${segundos > SEGUNDOS_DE_DEMO ? "text-dano-tinta" : "text-tinta-2"}`}>
      {Math.floor(segundos / 60)}:{String(segundos % 60).padStart(2, "0")}
      {reloj.fin !== null && " · parado"}
    </span>
  );
}

export function Deck() {
  const router = useRouter();
  const { cohorte, error } = useCohorte();
  const [posicion, setPosicion] = useState<Posicion>({ diapositiva: 0, clic: 0 });
  const [saliendo, setSaliendo] = useState(false);
  const [verCronometro, setVerCronometro] = useState(false);
  const [reloj, setReloj] = useState<Reloj>(RELOJ_PARADO);
  // Desde dónde se saltó al anexo con la tecla A, para volver al mismo sitio.
  const [antesDelAnexo, setAntesDelAnexo] = useState<Posicion | null>(null);
  // La URL manda al abrir (`?d=3&clicks=1`); después la posición manda sobre la URL.
  const [leida, setLeida] = useState(false);
  const geometria = useMemo(() => (cohorte ? calcularGeometria(cohorte) : null), [cohorte]);

  useEffect(() => {
    setPosicion(leerPosicion());
    setReloj(leerReloj());
    setLeida(true);
    router.prefetch(RUTA_COHORTE);
    router.prefetch(RUTA_INFERENCIA);
  }, [router]);

  useEffect(() => {
    if (!leida) return;
    window.history.replaceState(null, "", consulta(posicion) || window.location.pathname);
  }, [posicion, leida]);

  const enAnexo = posicion.diapositiva >= PRIMERA_DEL_ANEXO;
  // El cronómetro mide el recorrido en vivo: se para al entrar en el anexo.
  useEffect(() => {
    if (leida && enAnexo) setReloj(moverReloj("parar"));
  }, [leida, enAnexo]);

  const salir = useCallback(
    (ruta: string) => {
      setSaliendo(true);
      setTimeout(() => router.push(ruta), 420);
    },
    [router],
  );

  // Fuera del recorrido: desde las conclusiones o el anexo. Se vuelve a donde se estaba y el reloj se para.
  const abrir = useCallback(
    (ruta: string) => {
      guardarVuelta(consulta(posicion));
      moverReloj("parar");
      salir(ruta);
    },
    [posicion, salir],
  );

  const avanzar = useCallback(() => {
    setReloj(moverReloj("arrancar"));
    const { diapositiva, clic } = posicion;
    if (clic < TODAS[diapositiva].clics) setPosicion({ diapositiva, clic: clic + 1 });
    else if (diapositiva === ANTES_DE_LA_APLICACION) {
      // La cuarta parte del recorrido: la aplicación. El reloj sigue, y de la plataforma se vuelve a las conclusiones.
      guardarVuelta(consulta({ diapositiva: TRAS_LA_APLICACION, clic: 0 }), consulta(posicion));
      salir(RUTA_COHORTE);
    } else if (diapositiva < TODAS.length - 1) setPosicion({ diapositiva: diapositiva + 1, clic: 0 });
    // Tras la última respuesta se vuelve al índice.
    else setPosicion({ diapositiva: INDICE, clic: 0 });
  }, [posicion, salir]);

  const retroceder = useCallback(() => {
    const { diapositiva, clic } = posicion;
    if (clic > 0) setPosicion({ diapositiva, clic: clic - 1 });
    else if (diapositiva > 0) setPosicion({ diapositiva: diapositiva - 1, clic: TODAS[diapositiva - 1].clics });
  }, [posicion]);

  // A abre el índice del anexo desde cualquier sitio. En el índice, A vuelve a donde se estaba en el recorrido.
  const alAnexo = useCallback(() => {
    if (posicion.diapositiva === INDICE) {
      setPosicion(antesDelAnexo ?? { diapositiva: PRIMERA_DEL_ANEXO - 1, clic: TODAS[PRIMERA_DEL_ANEXO - 1].clics });
      setAntesDelAnexo(null);
    } else {
      if (!enAnexo) setAntesDelAnexo(posicion);
      setPosicion({ diapositiva: INDICE, clic: 0 });
    }
  }, [enAnexo, antesDelAnexo, posicion]);

  const volverDelAnexo = useCallback(() => {
    if (!enAnexo) return;
    setPosicion(antesDelAnexo ?? { diapositiva: PRIMERA_DEL_ANEXO - 1, clic: TODAS[PRIMERA_DEL_ANEXO - 1].clics });
    setAntesDelAnexo(null);
  }, [enAnexo, antesDelAnexo]);

  const irA = useCallback(
    (titulo: string) => {
      const indice = ANEXO.findIndex((entrada) => entrada.titulo === titulo);
      if (indice < 0) return;
      if (!enAnexo) setAntesDelAnexo(posicion);
      setPosicion({ diapositiva: PRIMERA_DEL_ANEXO + indice, clic: 0 });
    },
    [enAnexo, posicion],
  );

  // S salta lo que queda de esta diapositiva y las opcionales que vengan detrás. Si salta la última antes de la
  // aplicación, abre la aplicación como lo haría el avance normal.
  const saltar = useCallback(() => {
    if (enAnexo) return;
    let destino = posicion.diapositiva + 1;
    while (destino < PRIMERA_DEL_ANEXO && EN_VIVO[destino].opcional) destino++;
    if (posicion.diapositiva <= ANTES_DE_LA_APLICACION && destino > ANTES_DE_LA_APLICACION) {
      setReloj(moverReloj("arrancar"));
      guardarVuelta(consulta({ diapositiva: TRAS_LA_APLICACION, clic: 0 }), consulta(posicion));
      salir(RUTA_COHORTE);
    } else if (destino < PRIMERA_DEL_ANEXO) {
      setReloj(moverReloj("arrancar"));
      setPosicion({ diapositiva: destino, clic: 0 });
    }
  }, [enAnexo, posicion, salir]);

  useEffect(() => {
    const alPulsar = (evento: KeyboardEvent) => {
      if (evento.metaKey || evento.ctrlKey || evento.altKey) return;
      const tecla = evento.key.length === 1 ? evento.key.toLowerCase() : evento.key;
      if (["ArrowRight", " ", "PageDown", "Enter"].includes(tecla)) {
        evento.preventDefault();
        avanzar();
      } else if (["ArrowLeft", "PageUp", "Backspace"].includes(tecla)) {
        evento.preventDefault();
        retroceder();
      } else if (tecla === "Home") {
        setPosicion({ diapositiva: 0, clic: 0 });
        setAntesDelAnexo(null);
        setReloj(moverReloj("borrar"));
      } else if (tecla === "a") alAnexo();
      else if (tecla === "Escape") volverDelAnexo();
      else if (tecla === "s") saltar();
      else if (tecla === "t") setVerCronometro((visible) => !visible);
      else if (tecla === "f") {
        if (document.fullscreenElement) void document.exitFullscreen();
        else void document.documentElement.requestFullscreen();
      }
    };
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [avanzar, retroceder, alAnexo, volverDelAnexo, saltar]);

  const actual = TODAS[posicion.diapositiva];
  const { Contenido } = actual;
  const tramo = (diapositiva: Entrada, indice: number) => {
    const lleno = indice < posicion.diapositiva ? 1 : indice === posicion.diapositiva ? (posicion.clic + 1) / (diapositiva.clics + 1) : 0;
    return (
      <div key={diapositiva.titulo} className="h-[0.28cqw] flex-1 overflow-hidden rounded-full bg-linea" aria-current={indice === posicion.diapositiva ? "step" : undefined}>
        <motion.div className={`h-full origin-left rounded-full ${diapositiva.opcional ? "bg-tinta-3" : "bg-tinta"}`} initial={false} animate={{ scaleX: lleno }} transition={{ duration: 0.45, ease: [0.4, 0, 0.2, 1] }} />
      </div>
    );
  };
  const rotulo = (activo: boolean) => `mt-[0.5cqw] block truncate text-[0.85cqw] font-medium transition-colors ${activo ? "text-tinta" : "text-tinta-3"}`;

  return (
    <main className="fixed inset-0 grid place-items-center overflow-hidden bg-fondo">
      <motion.div
        className="lienzo relative cursor-default overflow-hidden bg-papel shadow-[0_1px_0_var(--color-linea),0_24px_60px_-30px_rgb(22_22_26/0.25)] select-none"
        animate={saliendo ? { scale: 1.05, opacity: 0 } : { scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
        onClick={avanzar}
      >
        <header className="absolute inset-x-0 top-0 z-20 flex h-[5.6cqw] items-center gap-[2cqw] px-[4cqw]">
          <Marca className="text-[1.5cqw]" />
          {enAnexo ? (
            <>
              <span className="rounded-full bg-tinta px-[0.9cqw] py-[0.25cqw] text-[0.9cqw] font-medium text-white">Anexo</span>
              {/* El índice, siempre a la vista: un clic salta a la respuesta. */}
              <nav className="flex flex-1 flex-wrap items-center gap-x-[0.7cqw] gap-y-[0.2cqw]" aria-label="Índice del anexo">
                {ANEXO.map((diapositiva, indice) => {
                  const activa = PRIMERA_DEL_ANEXO + indice === posicion.diapositiva;
                  return (
                    <button
                      key={diapositiva.titulo}
                      type="button"
                      aria-current={activa ? "page" : undefined}
                      className={`border-b-[0.16cqw] pb-[0.15cqw] text-[0.82cqw] font-medium whitespace-nowrap transition-colors ${activa ? "border-tinta text-tinta" : "border-transparent text-tinta-3 hover:text-tinta"}`}
                      onClick={(evento) => {
                        evento.stopPropagation();
                        setPosicion({ diapositiva: PRIMERA_DEL_ANEXO + indice, clic: 0 });
                      }}
                    >
                      {diapositiva.titulo}
                    </button>
                  );
                })}
              </nav>
            </>
          ) : (
            // Las seis partes del guion. Dentro de cada una, un tramo por diapositiva; la aplicación es un tramo solo.
            <ol className="flex flex-1 items-start gap-[1.1cqw]">
              {PARTES.map((parte, numero) => {
                const activa = parte.diapositivas.includes(posicion.diapositiva);
                return (
                  <li key={parte.nombre} className="min-w-0" style={{ flex: Math.max(parte.diapositivas.length, 1.5) }} aria-current={activa ? "true" : undefined}>
                    <div className="flex gap-[0.35cqw]">
                      {parte.diapositivas.length > 0 ? (
                        parte.diapositivas.map((indice) => tramo(EN_VIVO[indice], indice))
                      ) : (
                        // La aplicación queda hecha cuando se vuelve de ella a las conclusiones.
                        <div className="h-[0.28cqw] flex-1 overflow-hidden rounded-full bg-linea">
                          <motion.div className="h-full origin-left rounded-full bg-tinta" initial={false} animate={{ scaleX: posicion.diapositiva >= TRAS_LA_APLICACION ? 1 : 0 }} />
                        </div>
                      )}
                    </div>
                    <span className={rotulo(activa)}>
                      <span className="mr-[0.4em] font-mono text-tinta-3">{numero + 1}</span>
                      {parte.nombre}
                    </span>
                  </li>
                );
              })}
            </ol>
          )}
          {(!enAnexo || verCronometro) && (
            <span className="flex w-[10.5cqw] justify-end text-[0.9cqw] whitespace-nowrap text-tinta-3">
              {verCronometro ? <Cronometro reloj={reloj} /> : actual.opcional ? "Opcional · S la salta" : "Respira Hackathon 2026"}
            </span>
          )}
        </header>

        <AnimatePresence mode="wait">
          <motion.section
            key={posicion.diapositiva}
            // Los dibujos en vivo ocupan todo el lienzo; las del anexo empiezan debajo de la barra.
            className={enAnexo ? "absolute inset-x-0 top-[5.6cqw] bottom-0" : "absolute inset-0"}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
          >
            {error ? (
              <p className="p-[6cqw] pt-[9cqw] text-[1.6cqw] text-dano-tinta">{error}</p>
            ) : cohorte && geometria ? (
              <Contenido cohorte={cohorte} geometria={geometria} clic={posicion.clic} avanzar={avanzar} abrir={abrir} alAnexo={alAnexo} irA={irA} />
            ) : null}
          </motion.section>
        </AnimatePresence>

        {/* Los puntos de la cohorte no se desmontan al cambiar de diapositiva: se mueven de un dibujo al siguiente. */}
        {geometria && <Puntos geometria={geometria} cuadro={actual.cuadro ?? null} clic={posicion.clic} />}

        {posicion.diapositiva === 0 && posicion.clic === 0 && (
          <span className="absolute right-[6cqw] bottom-[1.3cqw] text-[0.95cqw] text-tinta-3">→ avanza · S salta las opcionales · A preguntas · T cronómetro · F pantalla completa</span>
        )}
        <span className="absolute right-[2.4cqw] bottom-[1.3cqw] font-mono text-[0.95cqw] text-tinta-3 tabular-nums" aria-label="Número de diapositiva">
          {numeroDe(posicion.diapositiva)}
        </span>
        {enAnexo && <span className="absolute right-[6cqw] bottom-[1.3cqw] text-[0.95cqw] text-tinta-3">A índice · Esc vuelve a la presentación</span>}
        {cohorte?.aviso && !enAnexo && actual.cuadro && (
          <span className="absolute bottom-[1.3cqw] left-[6cqw] text-[0.95cqw] text-tinta-3">Los puntos son sujetos simulados.</span>
        )}
      </motion.div>
    </main>
  );
}
