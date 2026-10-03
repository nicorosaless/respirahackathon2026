import { Contraste } from "@/components/Contraste";
import { Criterios } from "@/components/Criterios";
import { type Cohorte, medida, umbralNormalidad, validacionDelModelo } from "@/lib/cohorte";
import { num, porcentaje, pValor } from "@/lib/formato";
import { criteriosDeReserva, tablaDeContraste } from "@/lib/inferencia";

/** Cada bloque de la vista de cohorte: un número de orden, una frase que afirma y la cifra que la respalda. */
export function Bloque({ numero, titulo, detalle, children, className = "" }: { numero: number; titulo: string; detalle?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`tarjeta flex flex-col p-5 ${className}`}>
      <h2 className="flex items-center gap-2.5 text-base font-semibold tracking-tight">
        <span className="grid size-6 shrink-0 place-items-center rounded-full bg-tinta text-xs text-white">{numero}</span>
        {titulo}
      </h2>
      {detalle && <p className="mt-1.5 text-xs leading-relaxed text-tinta-3">{detalle}</p>}
      <div className="mt-3 flex flex-1 flex-col">{children}</div>
    </section>
  );
}

function Barra({ nombre, nota, valor, tono = "gris" }: { nombre: string; nota?: string; valor: number | undefined; tono?: "gris" | "tinta" | "dano" }) {
  const color = tono === "dano" ? "bg-dano" : tono === "tinta" ? "bg-tinta" : "bg-control";
  return (
    <div className="grid grid-cols-[13.5rem_1fr_2.75rem] items-center gap-3 text-sm">
      <span className={tono === "gris" ? "text-tinta-2" : "font-medium"}>
        {nombre}
        {nota && <span className="ml-1.5 rounded-full border border-linea-2 px-1.5 py-px text-[10px] font-normal text-tinta-3">{nota}</span>}
      </span>
      <span className="h-2.5 overflow-hidden rounded-full bg-fondo">
        <span className={`block h-full rounded-full ${color}`} style={{ width: `${Math.max((valor ?? 0) * 100, 2)}%` }} />
      </span>
      <span className={`text-right font-semibold tabular-nums ${tono === "dano" ? "text-dano-tinta" : ""}`}>{num(valor, 2)}</span>
    </div>
  );
}

/** Bloque 2: el acuerdo entre los dos filtros del escáner de la misma TC, con las medidas que nombra el reto. */
export function Estabilidad({ cohorte }: { cohorte: Cohorte }) {
  const acuerdo = (clave: string) => medida(cohorte, clave)?.icc_kernel;
  const { comprobaciones } = cohorte;
  return (
    <Bloque
      numero={2}
      titulo="Acuerdo alto entre los dos filtros del escáner"
      detalle={`La misma TC con dos filtros del escáner. 1 es el mismo valor en cada persona. ${comprobaciones.otra_reconstruccion.separa_epoc.n} sujetos con las dos.`}
    >
      <div className="flex flex-col gap-2">
        <Barra nombre="%LAA-950 clásico" nota="reto" valor={acuerdo("laa950")} />
        <Barra nombre="Grosor de pared, estimado" nota="reto" valor={acuerdo("via_grosor_pared_mm")} />
        <Barra nombre="Disanapsia, aproximada" nota="reto" valor={acuerdo("via_disanapsia")} />
        <Barra nombre="%LAA-950 suavizado" valor={acuerdo("laa950_smooth")} tono="tinta" />
        <Barra nombre="Longitud de vía aérea" valor={acuerdo("via_longitud_mm")} tono="tinta" />
        <Barra nombre="Puntuación de daño" valor={comprobaciones.otra_reconstruccion.icc} tono="dano" />
      </div>
      <p className="mt-2.5 text-xs leading-relaxed text-tinta-3">En negro, las dos medidas de la puntuación. «reto»: las que nombra el reto.</p>
    </Bloque>
  );
}

/** Lo que la TC añade a lo que ya se sabe sin ninguna prueba. Exploratorio: va en un desplegable. */
export function AnadeALaClinica({ cohorte }: { cohorte: Cohorte }) {
  const [clinica, conTC] = cohorte.escalera.escalera;
  const enReserva = cohorte.reserva?.anade_a_la_clinica;
  return (
    <div className="grid max-w-4xl gap-x-10 gap-y-5 md:grid-cols-2">
      <div>
        <p className="mb-2 text-xs font-medium text-tinta-2">Con los {cohorte.comprobaciones.sujetos} sujetos. Validación cruzada; exploratorio</p>
        <div className="flex flex-col gap-2.5">
          <Barra nombre="Edad, sexo, talla, tabaco" valor={clinica.metrica} />
          <Barra nombre="Más las dos medidas de TC" valor={conTC.metrica} tono="dano" />
        </div>
        <p className="mt-2 text-xs leading-relaxed text-tinta-3">
          Correlación entre el FEV1/FVC que se predice y el real. Incremento de {num(conTC.incremento, 2, true)} (intervalo del 95 %: de {num(conTC.incremento_ic95_inf, 2)} a {num(conTC.incremento_ic95_sup, 2)}; p de
          permutación {pValor(conTC.p_permutacion)}).
        </p>
      </div>
      {enReserva && enReserva.length >= 2 && (
        <div>
          <p className="mb-2 text-xs font-medium text-tinta-2">En la primera prueba: {enReserva[0].n} sujetos que los modelos no vieron. Comparación descriptiva</p>
          <div className="flex flex-col gap-2.5">
            <Barra nombre="Edad, sexo, talla, tabaco" valor={enReserva[0].rho} />
            <Barra nombre="Más las dos medidas de TC" valor={enReserva[enReserva.length - 1].rho} tono="dano" />
          </div>
        </div>
      )}
    </div>
  );
}

function Dato({ valor, children }: { valor: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-3xl leading-none font-semibold tracking-tight tabular-nums">{valor}</p>
      <p className="mt-1.5 text-xs leading-relaxed text-tinta-2">{children}</p>
    </div>
  );
}

function Comprobacion({ titulo, detalle, cifras }: { titulo: string; detalle: string; cifras: [string, string][] }) {
  return (
    <div className="border-b border-linea py-3 first:pt-0 last:border-0 last:pb-0">
      <p className="text-sm font-medium">{titulo}</p>
      <p className="text-xs leading-relaxed text-tinta-3">{detalle}</p>
      <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-3">
        {cifras.map(([valor, que]) => (
          <div key={que}>
            <dd className="text-2xl leading-none font-semibold tracking-tight tabular-nums">{valor}</dd>
            <dt className="mt-1 text-[11px] leading-tight text-tinta-3">{que}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** Bloque 3: las dos comprobaciones, en cuatro cifras cada una. El detalle va en un desplegable. */
export function DosComprobaciones({ cohorte }: { cohorte: Cohorte }) {
  const { reserva, validacion } = cohorte;
  const validada = validacionDelModelo(cohorte);
  const criterios = reserva ? criteriosDeReserva(reserva).filter((c) => c.cumple !== null) : [];
  return (
    <Bloque numero={3} titulo="Dos comprobaciones en sujetos que el modelo no vio">
      {validada && validacion ? (
        <Comprobacion
          titulo={`Con los ${validacion.sujetos}: cada persona, con un modelo que no la vio`}
          detalle="Validación cruzada anidada del modelo final."
          cifras={[
            [num(validada.auc, 2), "AUC, fuera de muestra"],
            [num(validada.rho_media, 2), "con el FEV1/FVC"],
            [num(validada.rho_controles_media, 2), `entre los ${validacion.controles} sin obstrucción`],
          ]}
        />
      ) : (
        <Comprobacion titulo="La validación con todos los sujetos" detalle="Pendiente: todavía no se ha hecho." cifras={[]} />
      )}
      {reserva ? (
        <Comprobacion
          titulo={`Antes: ${reserva.sujetos} apartados, con el modelo ajustado sin ellos`}
          detalle={criterios.length > 0 ? `Cumple ${criterios.filter((c) => c.cumple).length} de los ${criterios.length} criterios escritos antes de mirar.` : "La primera prueba."}
          cifras={[
            [num(reserva.separa_epoc.auc, 2), `AUC en los ${reserva.sujetos}`],
            [num(reserva.fev1_fvc.rho, 2), "con el FEV1/FVC"],
            [`${reserva.sensibilidad.aciertos} de ${reserva.sensibilidad.de}`, "con EPOC, por encima del umbral"],
            [`${reserva.especificidad.de - reserva.especificidad.aciertos} de ${reserva.especificidad.de}`, "controles, por encima del umbral"],
          ]}
        />
      ) : (
        <Comprobacion titulo="La primera prueba, en sujetos apartados" detalle="Pendiente: no se ha hecho." cifras={[]} />
      )}
      {validada && (
        <p className="mt-3 rounded-lg bg-fondo px-3 py-2 text-sm leading-snug">
          <strong className="font-semibold">AUC {num(validada.auc, 2)}:</strong> {num(validada.auc * 100, 0)} de cada 100 veces, una persona con EPOC puntúa más alto que una sin ella.
        </p>
      )}
    </Bloque>
  );
}

/** Las dos comprobaciones con todas sus cifras: la validación con los umbrales y la primera prueba con sus criterios. */
export function ComprobacionesEnDetalle({ cohorte }: { cohorte: Cohorte }) {
  const { reserva, validacion } = cohorte;
  const validada = validacionDelModelo(cohorte);
  const normalidad = umbralNormalidad(cohorte);
  return (
    <div className="grid gap-x-10 gap-y-6 xl:grid-cols-[1fr_1.15fr]">
      <div>
        <h3 className="text-sm font-semibold">Validación con los {cohorte.comprobaciones.sujetos} sujetos</h3>
        <p className="mt-1 mb-3 text-xs leading-relaxed text-tinta-3">
          El modelo final se ajusta con todos. Cada persona se puntúa con un modelo que no la vio en ningún paso. Es más débil que una reserva: ya no queda nadie apartado.
        </p>
        {validada && validacion ? (
          <>
            <div className="grid grid-cols-2 gap-x-6 gap-y-5">
              <Dato valor={num(validada.rho_media, 2)}>
                de correlación con el FEV1/FVC. Intervalo del 95 %: de {num(validada.rho_ic95[0], 2)} a {num(validada.rho_ic95[1], 2)}.
              </Dato>
              <Dato valor={num(validada.rho_controles_media, 2)}>
                solo entre los {validacion.controles} sin obstrucción. Intervalo aproximado: de {num(validada.rho_controles_ic95[0], 2)} a {num(validada.rho_controles_ic95[1], 2)}. p = {pValor(validada.rho_controles_p)}, por
                permutación.
              </Dato>
              <Dato valor={num(validada.auc, 2)}>de AUC para separar EPOC de control. 0,5 es azar y 1, perfecto.</Dato>
              <Dato valor={num(validada.icc, 2)}>de acuerdo entre los dos filtros del escáner de la misma TC.</Dato>
            </div>
            <table className="mt-5 w-full text-sm">
              <thead className="text-xs text-tinta-3">
                <tr className="border-b border-linea-2 [&>th]:pb-1.5 [&>th]:font-medium">
                  <th className="text-left">Umbrales del modelo final, {cohorte.comprobaciones.sujetos} sujetos; fuera de muestra</th>
                  <th className="pl-3 text-right">Con EPOC, por encima</th>
                  <th className="pl-3 text-right">Controles, por debajo</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                <tr className="border-b border-linea [&>td]:py-2">
                  <td className="text-tinta-2">TC parecida a la de la EPOC ({num(cohorte.umbral_dano, 2)})</td>
                  <td className="pl-3 text-right font-semibold">{porcentaje(validada.sensibilidad_youden)}</td>
                  <td className="pl-3 text-right font-semibold">{porcentaje(validada.especificidad_youden)}</td>
                </tr>
                <tr className="[&>td]:py-2">
                  <td className="text-tinta-2">Límite superior de lo normal{normalidad !== null && ` (${num(normalidad, 2)})`}</td>
                  <td className="pl-3 text-right font-semibold">{porcentaje(validada.sensibilidad_normalidad)}</td>
                  <td className="pl-3 text-right font-semibold">{porcentaje(validada.especificidad_normalidad)}</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-2 text-xs leading-relaxed text-tinta-3">
              Validación cruzada anidada: {validacion.vueltas} grupos, {validacion.repeticiones} repeticiones.
              {cohorte.aviso && " Estas cifras son las de la cohorte del reto."}
            </p>
          </>
        ) : (
          <p className="text-sm leading-relaxed text-tinta-2">Pendiente: la validación con todos los sujetos todavía no se ha hecho.</p>
        )}
      </div>

      <div className="xl:border-l xl:border-linea xl:pl-10">
        <h3 className="text-sm font-semibold">Antes, la primera prueba: sujetos que el modelo no había visto</h3>
        <p className="mt-1 mb-3 text-xs leading-relaxed text-tinta-3">
          El mismo modelo, ajustado sin los sujetos de reserva. Lo que contaría como éxito se escribió antes de mirar. Estas cifras son de aquel modelo, no del final.
        </p>
        {cohorte.congelado && (
          <p className="mb-3 text-xs font-medium tracking-wide text-tinta-3 uppercase">
            Umbrales del modelo congelado, probado en la reserva: umbral {num(cohorte.congelado.umbral_dano, 2)}
            {cohorte.congelado.umbral_normalidad !== null && `, límite ${num(cohorte.congelado.umbral_normalidad, 2)}`}
          </p>
        )}
        {reserva ? (
          <>
            <Criterios reserva={reserva} className="text-[13px]" />
            <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-3">
              <Contraste casillas={tablaDeContraste(reserva)} className="text-[13px]" />
              <p className="max-w-[15rem] text-xs leading-relaxed text-tinta-3">
                {reserva.sujetos} sujetos, {reserva.epoc} con EPOC. Los intervalos son anchos, y el umbral es la pieza más frágil.
              </p>
            </div>
          </>
        ) : (
          <p className="text-sm leading-relaxed text-tinta-2">Pendiente: la prueba en reserva no se ha hecho.</p>
        )}
      </div>
    </div>
  );
}

const NOMBRE_ESTRATO: Record<string, (nivel: string) => string> = {
  kvp: (nivel) => `${nivel} kVp`,
  sexo: (nivel) => (nivel === "hombre" ? "Hombres" : "Mujeres"),
  fuma: (nivel) => (nivel === "fuma" ? "Fuman" : "No fuman"),
};

/** El AUC para EPOC dentro de cada subgrupo: dónde se ha buscado una relación con el escáner, el sexo o el tabaco. */
export function Subgrupos({ cohorte }: { cohorte: Cohorte }) {
  const { separa_epoc: auc, por_estrato } = cohorte.comprobaciones;
  // Se dibuja de 0,5 (azar) a 1.
  const posicion = (valor: number) => `${Math.min(Math.max((valor - 0.5) / 0.5, 0), 1) * 100}%`;
  return (
    <div className="max-w-2xl">
      <p className="text-sm text-tinta-2">
        AUC para separar EPOC de control, con el modelo ajustado con estos mismos sujetos: <strong className="font-semibold text-tinta">{num(auc.auc, 2)}</strong> en el conjunto (intervalo del 95 %: de{" "}
        {num(auc.ic95[0], 2)} a {num(auc.ic95[1], 2)}). 0,5 es azar y 1, perfecto. Dentro de cada subgrupo:
      </p>
      <ul className="mt-4 flex flex-col gap-1.5">
        {por_estrato.map((estrato) => (
          <li key={`${estrato.variable}${estrato.nivel}`} className="grid grid-cols-[6rem_1fr_2.5rem_7rem] items-center gap-3 text-sm">
            <span className="text-tinta-2">{NOMBRE_ESTRATO[estrato.variable]?.(estrato.nivel) ?? estrato.nivel}</span>
            <span className="relative h-4">
              <span className="absolute inset-x-0 top-1/2 h-px bg-linea" />
              <span className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-tinta-3" style={{ left: posicion(estrato.ic95[0]), right: `calc(100% - ${posicion(estrato.ic95[1])})` }} />
              <span className="absolute top-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-tinta" style={{ left: posicion(estrato.auc) }} />
            </span>
            <span className="text-right font-medium tabular-nums">{num(estrato.auc, 2)}</span>
            <span className="text-xs text-tinta-3">
              {estrato.casos} EPOC de {estrato.n}
            </span>
          </li>
        ))}
        <li className="grid grid-cols-[6rem_1fr_2.5rem_7rem] gap-3 text-[11px] text-tinta-3">
          <span />
          <span className="flex justify-between">
            <span>0,5 (azar)</span>
            <span>1</span>
          </span>
        </li>
      </ul>
    </div>
  );
}
