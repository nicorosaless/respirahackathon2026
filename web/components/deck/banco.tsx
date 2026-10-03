"use client";

// El anexo como banco de respuestas. Cada diapositiva empieza por la pregunta tal como la haría el jurado, sigue con
// la respuesta corta y después la evidencia. El índice agrupa las preguntas y salta a cada una.
// Las cifras salen de los agregados de `docs/figuras/` (validación, reserva, experimento ciego, complejidad y embudo).

import { Contraste } from "@/components/Contraste";
import {
  conexionConPuntuacion,
  curvaDeComplejidad,
  modeloDeComplejidad,
  type PasoDelEmbudo,
  salidaDelEmbudo,
  type SalidaDelEmbudo,
  validacionDelModelo,
} from "@/lib/cohorte";
import { num, porcentaje, pValor } from "@/lib/formato";
import { tablaDeContraste } from "@/lib/inferencia";
import { LLN, PAQUETES_ANO } from "@/lib/lln";
import { GRUPO_ESTRATO, NOMBRE_ESTRATO } from "./anexo";
import { AJUSTE_DEL_PRIMER_MODELO, RESERVA_DE_LA_PRIMERA_PRUEBA } from "./diapositivas";
import { Cifra, Diapositiva, type PropsDiapositiva, Rotulo } from "./piezas";

const cabecera = "border-b border-linea-2 pb-[0.5cqw] text-[0.95cqw] leading-[1.25] font-medium text-tinta-3";
const celda = "border-b border-linea py-[0.45cqw] text-[1.12cqw] tabular-nums";
const nota = "text-[0.98cqw] leading-[1.4] text-tinta-3";

/** Las preguntas del jurado, agrupadas, y la diapositiva del anexo que las responde (por su título). */
export const PREGUNTAS: { grupo: string; preguntas: { pregunta: string; destino: string }[] }[] = [
  {
    grupo: "Cómo está hecho",
    preguntas: [
      { pregunta: "¿Cómo lo validasteis? ¿Por qué ese reparto?", destino: "Validación" },
      { pregunta: "¿Cuántos falsos negativos?", destino: "Validación" },
      { pregunta: "¿Por qué solo dos medidas?", destino: "Dos medidas" },
      { pregunta: "¿No es circular? ¿Usáis la espirometría?", destino: "A ciegas" },
      { pregunta: "¿Por qué no usáis toda la tabla? ¿Y lo molecular?", destino: "Integración" },
      { pregunta: "¿Por qué no deep learning o un SHAP?", destino: "SHAP" },
      { pregunta: "¿De dónde salen los datos y qué hace cada paso?", destino: "Método" },
      { pregunta: "¿Habéis usado IA?", destino: "IA" },
    ],
  },
  {
    grupo: "¿Es real?",
    preguntas: [
      { pregunta: "¿Puede ser un artefacto?", destino: "Artefactos" },
      { pregunta: "¿El experimento ciego reproduce la relación dentro de los no obstruidos?", destino: "A ciegas" },
      { pregunta: "¿Y si usáis el límite inferior de normalidad (LLN) en vez del 0,70?", destino: "LLN" },
      { pregunta: "¿Funcionaría en otro hospital?", destino: "Generalización" },
      { pregunta: "¿Y el grosor de pared, el Pi10 y la disanapsia?", destino: "Medidas" },
    ],
  },
  {
    grupo: "Qué significa",
    preguntas: [
      { pregunta: "¿Qué es pre-EPOC para vosotros?", destino: "Pre-EPOC" },
      { pregunta: "¿Y los paquetes-año?", destino: "Paquetes-año" },
      { pregunta: "¿Se adelanta la TC? ¿Predice la caída del FEV1?", destino: "Seguimiento" },
      { pregunta: "¿Es lesión o un árbol pequeño de origen?", destino: "Lecturas" },
      { pregunta: "¿Está la señal en las ramas finas visibles (<3 mm)?", destino: "Ramas finas" },
      { pregunta: "¿Qué pedía el reto y qué responde MAPS?", destino: "El reto" },
    ],
  },
];

export function Indice({ irA }: PropsDiapositiva) {
  return (
    <div className="flex h-full flex-col px-[6cqw] pt-[2.2cqw] pb-[3.4cqw]">
      <h1 className="text-[2.6cqw] leading-[1.08] font-semibold tracking-[-0.035em]">Preguntas del jurado</h1>
      <p className="mt-[0.5cqw] text-[1.3cqw] text-tinta-2">Clic en una pregunta para ir a su respuesta. A vuelve a la presentación.</p>
      <div className="mt-[2cqw] grid min-h-0 flex-1 grid-cols-3 items-start gap-[2.6cqw]">
        {PREGUNTAS.map((grupo) => (
          <section key={grupo.grupo}>
            <Rotulo>{grupo.grupo}</Rotulo>
            <ul className="mt-[0.6cqw] flex flex-col">
              {grupo.preguntas.map((p) => (
                <li key={p.pregunta}>
                  <button
                    type="button"
                    className="group flex w-full items-baseline justify-between gap-[1cqw] border-b border-linea py-[0.75cqw] text-left text-[1.3cqw] leading-[1.3] hover:text-tinta"
                    onClick={(evento) => {
                      evento.stopPropagation();
                      irA(p.destino);
                    }}
                  >
                    <span className="font-medium">{p.pregunta}</span>
                    <span className="shrink-0 text-[1cqw] text-tinta-3 group-hover:text-tinta">{p.destino} →</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

// Validación: la primera prueba en 15 apartados y la validación cruzada anidada con los 80.
export function Validacion({ cohorte }: PropsDiapositiva) {
  const { reserva, validacion } = cohorte;
  const fila = validacionDelModelo(cohorte);
  const ajuste = cohorte.congelado?.sujetos_de_ajuste ?? AJUSTE_DEL_PRIMER_MODELO;
  const apartados = reserva?.sujetos ?? RESERVA_DE_LA_PRIMERA_PRUEBA;
  const ic = (par: [number, number] | undefined) => (par ? ` (IC de ${num(par[0], 2)} a ${num(par[1], 2)})` : "");
  const filas: [string, string, string][] = [
    ["El modelo", `ajustado con ${ajuste}`, "el final; cada persona, con un modelo que no la vio"],
    ["Separa EPOC de control (AUC)", reserva ? `${num(reserva.separa_epoc.auc, 2)}${ic(reserva.separa_epoc.ic95)}` : "–", fila ? num(fila.auc, 2) : "–"],
    [
      "Con EPOC, por encima del umbral",
      reserva ? `${reserva.sensibilidad.aciertos} de ${reserva.sensibilidad.de}${ic(reserva.sensibilidad.ic95)}` : "–",
      fila ? porcentaje(fila.sensibilidad_youden) : "–",
    ],
    [
      "Controles, por debajo",
      reserva ? `${reserva.especificidad.aciertos} de ${reserva.especificidad.de}${ic(reserva.especificidad.ic95)}` : "–",
      fila ? porcentaje(fila.especificidad_youden) : "–",
    ],
    ["Relación con el FEV1/FVC", reserva ? num(reserva.fev1_fvc.rho, 2) : "–", fila ? `${num(fila.rho_media, 2)}${ic(fila.rho_ic95)}` : "–"],
    [
      "Con el límite superior de lo normal",
      reserva?.limite_de_normalidad ? `${reserva.limite_de_normalidad.sensibilidad.aciertos} de ${reserva.limite_de_normalidad.sensibilidad.de} y ${reserva.limite_de_normalidad.especificidad.aciertos} de ${reserva.limite_de_normalidad.especificidad.de}` : "–",
      fila ? `${porcentaje(fila.sensibilidad_normalidad)} y ${porcentaje(fila.especificidad_normalidad)}` : "–",
    ],
  ];

  return (
    <Diapositiva
      pregunta="¿Cómo lo validasteis? ¿Por qué ese reparto? ¿Cuántos falsos negativos?"
      titular={`Primero, ${apartados} apartados y una sola prueba. Después, validación cruzada anidada con los ${validacion?.sujetos ?? cohorte.comprobaciones.sujetos}.`}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1.55fr_1fr] items-start gap-[3.4cqw]">
        <div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left align-bottom">
                <th className={cabecera} />
                <th className={`${cabecera} pl-[1.2cqw]`}>Primera prueba: {apartados} apartados</th>
                <th className={`${cabecera} pl-[1.2cqw]`}>Con los {validacion?.sujetos ?? 80}, fuera de muestra</th>
              </tr>
            </thead>
            <tbody>
              {filas.map(([que, primera, despues]) => (
                <tr key={que} className="align-baseline">
                  <td className={`${celda} pr-[1cqw] text-tinta-2`}>{que}</td>
                  <td className={`${celda} pl-[1.2cqw] font-semibold`}>{primera}</td>
                  <td className={`${celda} pl-[1.2cqw] font-semibold`}>{despues}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className={`mt-[0.8cqw] ${nota}`}>
            Con los {validacion?.sujetos ?? 80}: {validacion?.vueltas ?? 5} grupos y {validacion?.repeticiones ?? 10} repeticiones. Cada sujeto se puntúa con un modelo que no lo vio en ningún paso. La
            validación no trae intervalo para el {fila ? porcentaje(fila.sensibilidad_youden) : "–"} y el {fila ? porcentaje(fila.especificidad_youden) : "–"}.
          </p>
        </div>

        <div className="flex flex-col gap-[1.4cqw]">
          {reserva && (
            <div>
              <Rotulo>Los {apartados} de la primera prueba</Rotulo>
              <Contraste casillas={tablaDeContraste(reserva)} className="mt-[0.4cqw] text-[1.1cqw]" />
            </div>
          )}
          <div>
            <Rotulo>Por qué ese reparto</Rotulo>
            <ul className="mt-[0.5cqw] flex flex-col gap-[0.5cqw] text-[1.12cqw] leading-[1.4]">
              <li>Uno de cada cinco se apartó antes de elegir nada, con los criterios escritos.</li>
              <li className="text-tinta-2">Con {apartados} sujetos la cifra es muy ruidosa{reserva?.separa_epoc.ic95 ? `: el intervalo de la AUC va de ${num(reserva.separa_epoc.ic95[0], 2)} a ${num(reserva.separa_epoc.ic95[1], 2)}` : ""}. Por eso, después, la validación con todos.</li>
              <li className="text-tinta-2">El umbral equilibra las dos cifras: es el que maximiza sensibilidad más especificidad (Youden).</li>
            </ul>
          </div>
        </div>
      </div>
    </Diapositiva>
  );
}

// Menos es más: el embudo entero, medida a medida.
const SALIDAS: { salida: SalidaDelEmbudo; titulo: string }[] = [
  { salida: "inestable", titulo: "Fuera en el filtro 1: inestables entre los dos filtros del escáner" },
  { salida: "sin asociación", titulo: "Fuera en el filtro 2: no se asocian con el FEV1/FVC" },
  { salida: "redundante", titulo: "Fuera en el filtro 3: dicen lo mismo que las elegidas" },
  { salida: "dentro", titulo: "Dentro" },
];

function TablaDelEmbudo({ grupos, conDescontando, delModelo }: { grupos: { titulo: string; pasos: PasoDelEmbudo[] }[]; conDescontando: boolean; delModelo: string }) {
  const q = (valor: number) => (valor < 0.001 ? "< 0,001" : pValor(valor));
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-left align-bottom">
          <th className={cabecera}>Medida</th>
          <th className={`${cabecera} text-right`}>Acuerdo</th>
          <th className={`${cabecera} text-right`}>Relación</th>
          <th className={`${cabecera} text-right`}>q</th>
          {conDescontando && <th className={`${cabecera} pl-[0.8cqw] text-right`}>Descontando</th>}
        </tr>
      </thead>
      {grupos.map((grupo) => (
        <tbody key={grupo.titulo}>
          <tr>
            <td colSpan={conDescontando ? 5 : 4} className="pt-[0.7cqw] pb-[0.15cqw] text-[0.95cqw] font-semibold">
              {grupo.titulo} ({grupo.pasos.length})
            </td>
          </tr>
          {grupo.pasos.map((paso) => (
            <tr key={paso.medida} className="[&>td]:py-[0.18cqw] [&>td]:text-[0.98cqw]">
              <td className="border-b border-linea">
                {paso.nombre}
                {paso.medida === delModelo && <span className="ml-[0.4cqw] text-tinta-3">· la del modelo</span>}
              </td>
              <td className="border-b border-linea text-right tabular-nums">{num(paso.icc, 2)}</td>
              <td className="border-b border-linea text-right tabular-nums">{num(paso.rho, 2)}</td>
              <td className="border-b border-linea text-right tabular-nums">{q(paso.q)}</td>
              {conDescontando && (
                <td className="border-b border-linea pl-[0.8cqw] text-right tabular-nums">
                  {paso.rho_descontando === undefined ? "–" : `${num(paso.rho_descontando, 2)} (p = ${pValor(paso.p_descontando)})`}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      ))}
    </table>
  );
}

export function EmbudoEntero({ cohorte }: PropsDiapositiva) {
  const { embudo, complejidad } = cohorte;
  const curva = complejidad ? curvaDeComplejidad(complejidad) : [];
  const dos = curva.find((m) => m.n === 2);
  const ultima = curva.at(-1);
  if (!embudo)
    return (
      <Diapositiva pregunta="¿Por qué solo dos medidas?" titular="Pendiente: esta cohorte no trae el embudo de medidas.">
        {null}
      </Diapositiva>
    );
  const grupos = SALIDAS.map(({ salida, titulo }) => ({ titulo, pasos: embudo.pasos.filter((p) => salidaDelEmbudo(p, embudo) === salida) }));

  return (
    <Diapositiva
      pregunta="¿Por qué solo dos medidas?"
      titular={
        dos && ultima
          ? `Tres filtros dejan dos de ${embudo.medidas}. Ninguna medida añadida supera a las dos fuera de muestra: ${num(dos.auc, 2)} con dos, ${num(ultima.auc, 2)} con ${ultima.n}.`
          : `Tres filtros dejan dos de ${embudo.medidas} medidas.`
      }
    >
      <div className="grid min-h-0 flex-1 grid-cols-2 items-start gap-[3cqw]">
        <div>
          <TablaDelEmbudo grupos={grupos.slice(0, 1)} conDescontando={false} delModelo="via_longitud_mm" />
          <p className={`mt-[0.8cqw] ${nota}`}>
            Acuerdo entre los dos filtros del escáner: {num(embudo.criterios.acuerdo_minimo, 2)} o más. Relación con el FEV1/FVC: q menor que {num(embudo.criterios.q_maximo, 2)}. Descontando las ya elegidas: p menor que{" "}
            {num(embudo.criterios.p_descontando_maximo, 2)}. El embudo elige los extremos del árbol; el modelo usa la longitud total, fijada antes: se parecen y fuera de muestra dan lo mismo.
          </p>
        </div>
        <TablaDelEmbudo grupos={grupos.slice(1)} conDescontando delModelo="via_longitud_mm" />
      </div>
    </Diapositiva>
  );
}

// A ciegas: la puntuación de cada persona no usa su espirometría, y el experimento ciego quita también las otras dos entradas.
export function ACiegas({ cohorte }: PropsDiapositiva) {
  const natural = cohorte.umbral_natural;
  const grupos = natural?.dos_grupos_por_la_tc;
  const modelo = validacionDelModelo(cohorte);
  const dentro = natural?.fev1_fvc_sin_obstruccion;
  return (
    <Diapositiva
      pregunta="¿No es circular? ¿Usáis la espirometría? ¿Reproduce la relación dentro de los no obstruidos?"
      titular={
        natural
          ? `La puntuación de cada persona no usa su espirometría. Sin usarla para ajustar ni para cortar, la TC coincide en ${natural.coinciden_con_la_obstruccion}.`
          : "La puntuación de cada persona no usa su espirometría."
      }
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1fr_1.15fr] items-start gap-[4cqw]">
        <div>
          <Rotulo>Dónde entra la espirometría en el modelo</Rotulo>
          <ol className="mt-[0.6cqw] flex flex-col gap-[0.6cqw] text-[1.2cqw] leading-[1.4]">
            <li>
              <strong className="font-semibold">1. Para decidir quién define lo normal.</strong> <span className="text-tinta-2">Lo esperado se aprende de quienes no tienen obstrucción.</span>
            </li>
            <li>
              <strong className="font-semibold">2. Para colocar la línea en la TC.</strong> <span className="text-tinta-2">Es la que mejor separa a quien tiene obstrucción de quien no.</span>
            </li>
          </ol>
          <p className="mt-[1.2cqw] text-[1.2cqw] leading-[1.4]">
            <strong className="font-semibold">El experimento ciego quita las dos.</strong>{" "}
            <span className="text-tinta-2">Lo esperado se ajusta con todos sin saber quién es caso, y la frontera sale de partir la puntuación en dos grupos, sin usar la espirometría para ajustar ni para cortar.</span>
          </p>
          <p className={`mt-[1.2cqw] ${nota}`}>
            Las dos medidas sí se eligieron antes con ella. No es el modelo: funciona peor, porque los enfermos entran en lo que se toma como esperado. Es la prueba de que la línea de la TC no viene de haberle enseñado
            dónde cortar.
          </p>
          {dentro && (
            <p className="mt-[1.2cqw] rounded-[0.9cqw] bg-fondo px-[1.2cqw] py-[0.9cqw] text-[1.2cqw] leading-[1.4]">
              <strong className="font-semibold">Entre los {dentro.n ?? cohorte.validacion?.controles ?? cohorte.comprobaciones.controles} sin obstrucción, no reproduce la relación:</strong>{" "}
              <span className="text-tinta-2">
                {num(dentro.rho, 2)} <span className="whitespace-nowrap">(p = {pValor(dentro.p)})</span>. El modelo, {num(modelo?.rho_controles_media, 2)}{" "}
                <span className="whitespace-nowrap">(p = {pValor(modelo?.rho_controles_p)})</span>.
              </span>
            </p>
          )}
        </div>

        {natural && grupos ? (
          <table className="w-full border-collapse">
            <tbody>
              {[
                ["Coinciden con la obstrucción", natural.coinciden_con_la_obstruccion],
                ["Grupo alto por la TC", `${grupos.por_encima} personas; ahí están ${grupos.con_obstruccion_por_encima} con obstrucción`],
                ["Grupo bajo por la TC", `${grupos.por_debajo} personas; ahí están ${grupos.sin_obstruccion_por_debajo} sin obstrucción`],
                ...(grupos.fev1_fvc_mediana_por_encima !== undefined && grupos.fev1_fvc_mediana_por_debajo !== undefined
                  ? [["FEV1/FVC mediano, alto y bajo", `${num(grupos.fev1_fvc_mediana_por_encima, 3)} y ${num(grupos.fev1_fvc_mediana_por_debajo, 3)}`]]
                  : []),
                ...(natural.fev1_fvc ? [["Relación de la puntuación ciega con el FEV1/FVC", `${num(natural.fev1_fvc.rho, 2)} (el modelo, ${num(modelo?.rho_media, 2)})`]] : []),
              ].map(([que, cifra]) => (
                <tr key={que} className="align-baseline">
                  <td className={`${celda} pr-[1.4cqw] text-tinta-2`}>{que}</td>
                  <td className={`${celda} text-right font-semibold`}>{cifra}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-[1.3cqw] text-tinta-2">Pendiente: esta cohorte no trae el experimento ciego.</p>
        )}
      </div>
    </Diapositiva>
  );
}

// Integración: la TC con la clínica, y por qué el resto de la tabla no entra.
function BarraDeAuc({ nombre, detalle, auc, fuerte = false }: { nombre: string; detalle?: string; auc: number | undefined; fuerte?: boolean }) {
  if (auc === undefined) return null;
  // De 0,5 (azar) a 1.
  const ancho = `${Math.min(Math.max((auc - 0.5) / 0.5, 0.02), 1) * 100}%`;
  return (
    <div className="grid grid-cols-[17cqw_1fr_4.4cqw] items-center gap-[1.2cqw] border-b border-linea py-[0.7cqw]">
      <div>
        <p className={`text-[1.2cqw] leading-[1.2] ${fuerte ? "font-semibold" : ""}`}>{nombre}</p>
        {detalle && <p className="text-[0.92cqw] text-tinta-3">{detalle}</p>}
      </div>
      <span className="h-[1.3cqw] rounded-full bg-fondo">
        <span className={`block h-full rounded-full ${fuerte ? "bg-tinta" : "bg-control"}`} style={{ width: ancho }} />
      </span>
      <strong className={`text-right text-[2cqw] leading-none font-semibold tracking-[-0.03em] tabular-nums ${fuerte ? "" : "text-tinta-2"}`}>{num(auc, 2)}</strong>
    </div>
  );
}

export function Integracion({ cohorte }: PropsDiapositiva) {
  const { complejidad } = cohorte;
  const modelo = (nombre: string) => modeloDeComplejidad(complejidad, nombre)?.auc;
  const [clinica, conTC, ampliada, ampliadaConTC, tc] = [modelo("clínica sola"), modelo("clínica y las dos medidas de TC"), modelo("clínica ampliada sola"), modelo("clínica ampliada y las dos medidas de TC"), modelo("2 medidas")];
  const feno = conexionConPuntuacion(cohorte);

  return (
    <Diapositiva
      pregunta="¿Por qué no usáis toda la tabla? ¿Y lo molecular?"
      titular={
        conTC !== undefined && ampliadaConTC !== undefined
          ? `La clínica básica con la TC sube a ${num(conTC, 2)}. Añadir síntomas, DLCO y FENO no ayuda: ${num(ampliadaConTC, 2)}.`
          : "Pendiente: esta cohorte no trae la comparación con la clínica."
      }
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1.45fr_1fr] items-start gap-[4cqw]">
        <div>
          <Rotulo>Separa EPOC de control, fuera de muestra (AUC; 0,5 es azar)</Rotulo>
          <div className="mt-[0.4cqw]">
            <BarraDeAuc nombre="Clínica básica sola" detalle="edad, sexo, talla, IMC, paquetes-año y fumar" auc={clinica} />
            <BarraDeAuc nombre="La TC: las dos medidas" auc={tc} />
            <BarraDeAuc nombre="Clínica básica y TC" auc={conTC} fuerte />
            <BarraDeAuc nombre="Clínica ampliada sola" detalle="además DLCO, CAT, mMRC, COPD-PS, FENO y asma" auc={ampliada} />
            <BarraDeAuc nombre="Clínica ampliada y TC" auc={ampliadaConTC} />
          </div>
          <p className={`mt-[0.6cqw] ${nota}`}>Validación cruzada de 5 grupos, repetida {complejidad?.repeticiones ?? 5} veces, con los {complejidad?.sujetos ?? 80}.</p>
        </div>
        <div className="flex flex-col gap-[1.2cqw] text-[1.2cqw] leading-[1.4]">
          <p>
            <strong className="font-semibold">El FEV1 y la FVC no pueden entrar.</strong> <span className="text-tinta-2">La obstrucción es su cociente: meterlos sería darle la respuesta al modelo.</span>
          </p>
          <p>
            <strong className="font-semibold">Los síntomas y la DLCO no son independientes.</strong> <span className="text-tinta-2">Son en parte consecuencia de la enfermedad, no una medida de ella.</span>
          </p>
          <p className="rounded-[0.9cqw] bg-fondo px-[1.2cqw] py-[0.9cqw]">
            <strong className="font-semibold">Lo molecular:</strong> miramos el FENO, el único biomarcador de la tabla, y no se asocia
            {feno ? ` (p = ${pValor(feno.p)}, ${feno.n} sujetos)` : ""}.
          </p>
        </div>
      </div>
    </Diapositiva>
  );
}

// Seguimiento: si la puntuación anuncia una caída acelerada del FEV1 entre visitas.
const CAIDAS: { clave: string; definicion: string; grupo: string }[] = [
  { clave: "30 mL al año, todos", definicion: "Más de 30 mL al año", grupo: "Todos" },
  { clave: "30 mL al año, sin obstrucción", definicion: "Más de 30 mL al año", grupo: "Sin obstrucción" },
  { clave: "60 mL al año, todos", definicion: "Más de 60 mL al año", grupo: "Todos" },
  { clave: "60 mL al año, sin obstrucción", definicion: "Más de 60 mL al año", grupo: "Sin obstrucción" },
];

export function Seguimiento({ cohorte }: PropsDiapositiva) {
  const caidas = cohorte.complejidad?.caida_acelerada_del_fev1;
  const clave = caidas?.["30 mL al año, sin obstrucción"];
  const marcados = cohorte.comprobaciones.controles_por_dano;
  const cambio = marcados.seguimiento.find((f) => f.variable === "Cambio del FEV1 %");

  return (
    <Diapositiva
      pregunta="¿Se adelanta la TC? ¿Predice la caída del FEV1?"
      titular={clave ? `No lo demostramos: con una caída de más de 30 mL al año, AUC ${num(clave.auc, 2)} entre los sin obstrucción.` : "No lo demostramos."}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1.5fr_1fr] items-start gap-[4cqw]">
        {caidas ? (
          <div>
            <table className="w-full border-collapse">
              <thead>
                <tr className="text-left align-bottom">
                  <th className={cabecera}>Caída acelerada del FEV1</th>
                  <th className={cabecera}>Quiénes</th>
                  <th className={`${cabecera} text-right`}>Con seguimiento</th>
                  <th className={`${cabecera} text-right`}>Con la caída</th>
                  <th className={`${cabecera} text-right`}>AUC</th>
                  <th className={`${cabecera} text-right`}>p</th>
                </tr>
              </thead>
              <tbody>
                {CAIDAS.flatMap((fila) => {
                  const datos = caidas[fila.clave];
                  return datos
                    ? [
                        <tr key={fila.clave}>
                          <td className={celda}>{fila.definicion}</td>
                          <td className={`${celda} text-tinta-2`}>{fila.grupo}</td>
                          <td className={`${celda} text-right`}>{datos.con_seguimiento}</td>
                          <td className={`${celda} text-right`}>{datos.caida_acelerada}</td>
                          <td className={`${celda} text-right font-semibold`}>{num(datos.auc, 2)}</td>
                          <td className={`${celda} text-right`}>{pValor(datos.p_mann_whitney)}</td>
                        </tr>,
                      ]
                    : [];
                })}
              </tbody>
            </table>
            <p className={`mt-[0.8cqw] ${nota}`}>
              AUC: si la puntuación fuera de muestra separa a quien cae deprisa de quien no; 0,5 es azar. La investigadora del reto propone 30 mL al año; la definición publicada dice 60.
            </p>
          </div>
        ) : (
          <p className="text-[1.3cqw] text-tinta-2">Pendiente: esta cohorte no trae el análisis de la caída del FEV1.</p>
        )}
        {cambio && (
          <div>
            <Rotulo>Los posibles pre-EPOC, a 3,6 años</Rotulo>
            <p className="mt-[0.6cqw] text-[1.2cqw] leading-[1.4]">
              El FEV1, en puntos del % predicho, cambió <strong className="font-semibold">{num(cambio.con_dano, 1, true)}</strong> en los {marcados.con_dano} y{" "}
              <strong className="font-semibold">{num(cambio.sin_dano, 1, true)}</strong> en los otros {marcados.sin_dano} (p = {pValor(cambio.p)}).
            </p>
            <p className="mt-[0.8cqw] text-[1.2cqw] leading-[1.4] text-tinta-2">No detectamos una caída mayor. Con este seguimiento no se puede decir que la TC se adelante.</p>
          </div>
        )}
      </div>
    </Diapositiva>
  );
}

// Medidas del reto: el %LAA-950 clásico, el grosor de pared, el Pi10 y la disanapsia.
// Las de pared y la disanapsia salen de la máscara de la segmentación, no del método de referencia: "estimado" y "aproximada".
const DEL_RETO: { medida: string; nombre: string; anadida?: string }[] = [
  { medida: "laa950", nombre: "%LAA-950 clásico" },
  { medida: "via_grosor_pared_mm", nombre: "Grosor de pared, estimado", anadida: "4 medidas" },
  { medida: "via_pi10_mm", nombre: "Pi10, aproximado", anadida: "7 medidas" },
  { medida: "via_disanapsia", nombre: "Disanapsia, aproximada", anadida: "3 medidas" },
];

const POR_QUE_SALE: Record<SalidaDelEmbudo, string> = {
  inestable: "inestable",
  "sin asociación": "no se asocia",
  redundante: "dice lo mismo",
  dentro: "dentro",
};

export function MedidasDelReto({ cohorte }: PropsDiapositiva) {
  const { embudo, complejidad } = cohorte;
  const dos = modeloDeComplejidad(complejidad, "2 medidas");
  const filas = DEL_RETO.flatMap((m) => {
    const paso = embudo?.pasos.find((p) => p.medida === m.medida);
    return paso && embudo ? [{ ...m, paso, salida: salidaDelEmbudo(paso, embudo), conElla: m.anadida ? modeloDeComplejidad(complejidad, m.anadida) : undefined }] : [];
  });

  return (
    <Diapositiva
      pregunta="¿Y el grosor de pared, el Pi10 y la disanapsia?"
      titular="Están medidos, como aproximaciones. Son inestables entre los dos filtros del escáner y no aportan."
    >
      {filas.length > 0 ? (
        <div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left align-bottom">
                <th className={cabecera}>Medida</th>
                <th className={`${cabecera} text-right`}>Acuerdo entre los dos filtros</th>
                <th className={`${cabecera} text-right`}>Relación con el FEV1/FVC</th>
                <th className={`${cabecera} text-right`}>q</th>
                <th className={`${cabecera} pl-[1.4cqw]`}>En el embudo</th>
                <th className={`${cabecera} text-right`}>AUC si se añade al modelo</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.medida}>
                  <td className={celda}>{f.nombre}</td>
                  <td className={`${celda} text-right font-semibold`}>{num(f.paso.icc, 2)}</td>
                  <td className={`${celda} text-right`}>{num(f.paso.rho, 2)}</td>
                  <td className={`${celda} text-right`}>{f.paso.q < 0.001 ? "< 0,001" : pValor(f.paso.q)}</td>
                  <td className={`${celda} pl-[1.4cqw] text-tinta-2`}>{POR_QUE_SALE[f.salida]}</td>
                  <td className={`${celda} text-right`}>{f.conElla ? `${num(f.conElla.auc, 2)} (${f.anadida})` : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className={`mt-[0.8cqw] ${nota}`}>
            Estable quiere decir un acuerdo de {num(embudo?.criterios.acuerdo_minimo, 2)} o más. El modelo, con dos medidas, da {num(dos?.auc, 2)}; las demás se añaden por orden, así que la de 7 medidas lleva también las
            anteriores. La pared y la disanapsia salen de la máscara de la segmentación, no del método de referencia.
          </p>
        </div>
      ) : (
        <p className="text-[1.3cqw] text-tinta-2">Pendiente: esta cohorte no trae el embudo de medidas.</p>
      )}
    </Diapositiva>
  );
}

// Generalización: si separa igual por voltaje, sexo y tabaco, y con el otro filtro del escáner.
export function Generalizacion({ cohorte }: PropsDiapositiva) {
  const { por_estrato, otra_reconstruccion } = cohorte.comprobaciones;
  // De 0,5 (azar) a 1.
  const posicion = (valor: number) => `${Math.min(Math.max((valor - 0.5) / 0.5, 0), 1) * 100}%`;
  const grupos = Object.keys(GRUPO_ESTRATO).map((variable) => ({ variable, filas: por_estrato.filter((e) => e.variable === variable) }));
  const kvp = por_estrato.filter((e) => e.variable === "kvp").length;

  return (
    <Diapositiva
      pregunta="¿Funcionaría en otro hospital?"
      titular={`Separa igual en ${kvp === 3 ? "los tres" : "los"} voltajes y con los dos filtros del escáner. La referencia es de fumadores de 35 a 50 años, en escáneres GE.`}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1.3fr_1fr] items-start gap-[4cqw]">
        <div>
          <Rotulo>Separa EPOC de control dentro de cada subgrupo (AUC, con su intervalo del 95 %)</Rotulo>
          <div className="mt-[0.8cqw] flex flex-col gap-[1cqw]">
            {grupos.map((grupo) => (
              <div key={grupo.variable}>
                <p className="mb-[0.2cqw] text-[1.1cqw] font-semibold">{GRUPO_ESTRATO[grupo.variable]}</p>
                {grupo.filas.map((estrato) => (
                  <div key={estrato.nivel} className="grid grid-cols-[9cqw_1fr_3.4cqw_7cqw] items-center gap-[1cqw] py-[0.24cqw] text-[1.12cqw]">
                    <span className="text-tinta-2">{NOMBRE_ESTRATO[estrato.variable]?.(estrato.nivel) ?? estrato.nivel}</span>
                    <span className="relative h-[1.3cqw]">
                      <span className="absolute inset-x-0 top-1/2 h-px bg-linea-2" />
                      <span className="absolute top-1/2 h-[0.2cqw] -translate-y-1/2 rounded-full bg-tinta-3" style={{ left: posicion(estrato.ic95[0]), right: `calc(100% - ${posicion(estrato.ic95[1])})` }} />
                      <span className="absolute top-1/2 size-[0.9cqw] -translate-x-1/2 -translate-y-1/2 rounded-full bg-tinta" style={{ left: posicion(estrato.auc) }} />
                    </span>
                    <span className="text-right font-semibold tabular-nums">{num(estrato.auc, 2)}</span>
                    <span className="text-[0.95cqw] text-tinta-3">
                      {estrato.casos} EPOC de {estrato.n}
                    </span>
                  </div>
                ))}
              </div>
            ))}
            <p className="grid grid-cols-[9cqw_1fr_3.4cqw_7cqw] gap-[1cqw] text-[0.92cqw] text-tinta-3">
              <span />
              <span className="flex justify-between">
                <span>0,5: azar</span>
                <span>1</span>
              </span>
            </p>
          </div>
        </div>
        <div className="flex flex-col gap-[1.2cqw] text-[1.2cqw] leading-[1.4]">
          <p>
            <strong className="font-semibold">Con el otro filtro del escáner</strong>{" "}
            <span className="text-tinta-2">
              la puntuación separa con una AUC de {num(otra_reconstruccion.separa_epoc.auc, 2)}, y el acuerdo entre los dos es {num(otra_reconstruccion.icc, 2)}.
            </span>
          </p>
          <p>
            <strong className="font-semibold">Lo que no hemos probado:</strong>{" "}
            <span className="text-tinta-2">otras marcas de escáner, otras edades y quien nunca fumó. Lo esperado se aprendió de esta cohorte; en otro sitio habría que volver a ajustarlo.</span>
          </p>
        </div>
      </div>
    </Diapositiva>
  );
}

// LLN: la obstrucción por el límite inferior de normalidad (GLI-2012) en vez del 0,70. Las cifras no vienen en
// `cohorte.json`: son las de `docs/cifras.md`, en `lib/lln.ts`.
export function LimiteInferior({ cohorte }: PropsDiapositiva) {
  const filas: [string, string][] = [
    ["LLN del FEV1/FVC en esta cohorte", `${num(LLN.mediana, 2)} de mediana (${num(LLN.rango[0], 2)} a ${num(LLN.rango[1], 2)})`],
    ["Sin obstrucción por el 0,70 y por debajo de su LLN", `${LLN.sin_obstruccion_bajo_lln} de ${LLN.sin_obstruccion}`],
    [`De ellos, entre los ${LLN.pre_epoc} posibles pre-EPOC`, `${LLN.pre_epoc_bajo_lln} de ${LLN.pre_epoc}`],
    [`Entre los otros ${LLN.otros} sin obstrucción`, `${LLN.otros_bajo_lln} de ${LLN.otros} (p = ${pValor(LLN.fisher_p)})`],
    ["Con EPOC por el 0,70 que el LLN no confirma", `${LLN.epoc_no_confirmados} de ${LLN.epoc}`],
    [`Puntuación frente al z del cociente, entre los ${LLN.sin_obstruccion} sin obstrucción`, `${num(LLN.z_cociente.rho, 2)} (p = ${pValor(LLN.z_cociente.p)})`],
  ];
  const modelo = validacionDelModelo(cohorte);
  return (
    <Diapositiva
      pregunta="¿Y si usáis el límite inferior de normalidad (LLN) en vez del 0,70?"
      titular={`Casi nada cambia. En esta cohorte el LLN cae casi encima del 0,70: reclasifica a 1 de ${LLN.sin_obstruccion + LLN.epoc}.`}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1.4fr_1fr] items-start gap-[4cqw]">
        <div>
          <table className="w-full border-collapse">
            <tbody>
              {filas.map(([que, cifra]) => (
                <tr key={que} className="align-baseline">
                  <td className={`${celda} pr-[1.4cqw] text-tinta-2`}>{que}</td>
                  <td className={`${celda} text-right font-semibold`}>{cifra}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className={`mt-[0.8cqw] ${nota}`}>
            GLI-2012 (caucásica), con la edad, el sexo y la talla de cada persona. El FEV1 en % del predicho que calculan esas ecuaciones coincide con el de la tabla: diferencia mediana de {num(LLN.diferencia_fev1_pct, 1)} puntos.
          </p>
        </div>
        <div className="flex flex-col gap-[1.2cqw] text-[1.2cqw] leading-[1.4]">
          <p>
            <strong className="font-semibold">
              Los {LLN.pre_epoc} posibles pre-EPOC no son obstruidos que se escapan del 0,70.
            </strong>{" "}
            <span className="text-tinta-2">
              {LLN.pre_epoc - LLN.pre_epoc_bajo_lln} de {LLN.pre_epoc} tienen el cociente normal para su edad, sexo y talla.
            </span>
          </p>
          <p>
            <strong className="font-semibold">La relación dentro de los no obstruidos se mantiene con el z.</strong>{" "}
            <span className="text-tinta-2">
              El z ya descuenta la edad, el sexo y la talla: {num(LLN.z_cociente.rho, 2)}, frente a {num(modelo?.rho_controles_media, 2)} con el cociente.
            </span>
          </p>
        </div>
      </div>
    </Diapositiva>
  );
}

// Paquetes-año: más tabaco acumulado no va con más puntuación. Las cifras ajustadas no vienen en `cohorte.json`.
export function PaquetesAno() {
  return (
    <Diapositiva
      pregunta="¿Y los paquetes-año?"
      titular="Más paquetes-año no van con más puntuación. Dentro de la EPOC, van con menos."
    >
      <div className="grid grid-cols-3 items-start gap-[4cqw]">
        <Cifra valor={num(PAQUETES_ANO.epoc_ajustado.rho, 2)}>
          <strong className="font-semibold text-tinta">Dentro de la EPOC, descontando la edad y fumar ahora.</strong> <span className="whitespace-nowrap">p = {pValor(PAQUETES_ANO.epoc_ajustado.p)}</span>, <span className="whitespace-nowrap">n = {PAQUETES_ANO.epoc_ajustado.n}</span>.
        </Cifra>
        <Cifra valor={num(PAQUETES_ANO.epoc.rho, 2)}>Dentro de la EPOC, sin descontar nada. <span className="whitespace-nowrap">p = {pValor(PAQUETES_ANO.epoc.p)}</span>.</Cifra>
        <Cifra valor={num(PAQUETES_ANO.controles.rho, 2)}>Dentro de los controles. <span className="whitespace-nowrap">p = {pValor(PAQUETES_ANO.controles.p)}</span>: no hemos encontrado relación.</Cifra>
      </div>
      <p className="mt-[3cqw] max-w-[70cqw] rounded-[0.9cqw] bg-fondo px-[1.4cqw] py-[1.1cqw] text-[1.3cqw] leading-[1.4]">
        <strong className="font-semibold">Pregunta abierta.</strong>{" "}
        <span className="text-tinta-2">¿Enferman con poco tabaco quienes tienen el árbol pequeño, o los más graves dejaron de fumar antes? Con un corte transversal no se distingue.</span>
      </p>
    </Diapositiva>
  );
}

// IA: qué papel tuvo en el trabajo. El método no tiene ningún componente generativo.
export function UsoDeIA() {
  const puntos: [string, string][] = [
    ["El método no tiene ningún componente generativo.", "Una red de segmentación ya entrenada, dos medidas, una regresión y un umbral."],
    ["Usamos agentes de IA como asistentes de código.", ""],
    ["Y como revisores automáticos.", "Proponían correcciones. Cada una la comprobamos nosotros."],
    ["No es una revisión científica independiente.", ""],
  ];
  return (
    <Diapositiva pregunta="¿Habéis usado IA?" titular="Sí, para programar y revisar. El análisis no tiene ninguna parte generativa.">
      <ol className="flex max-w-[72cqw] flex-col gap-[1.4cqw]">
        {puntos.map(([afirma, sigue], i) => (
          <li key={afirma} className="grid grid-cols-[2.4cqw_1fr] gap-[1cqw] text-[1.45cqw] leading-[1.4]">
            <span className="grid size-[2.4cqw] place-items-center rounded-full bg-tinta text-[1.1cqw] font-semibold text-white">{i + 1}</span>
            <p>
              <strong className="font-semibold">{afirma}</strong> <span className="text-tinta-2">{sigue}</span>
            </p>
          </li>
        ))}
      </ol>
    </Diapositiva>
  );
}
