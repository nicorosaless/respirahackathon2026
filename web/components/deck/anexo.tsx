"use client";

// Respuestas del anexo que vienen de las comprobaciones de la cohorte: ramas finas, artefactos, SHAP, datos y método,
// y lo que pide el reto. Cada una empieza por la pregunta del jurado. El índice y las demás están en `banco.tsx`.

import { acuerdoClasico, casoDeEntrada, type Cohorte, comparacionDeVias, correlacionPrincipal, filaDeValidacion, modeloConTodas, validacionDelModelo } from "@/lib/cohorte";
import { num, pValor } from "@/lib/formato";
import { AJUSTE_DEL_PRIMER_MODELO, RESERVA_DE_LA_PRIMERA_PRUEBA } from "./diapositivas";
import { Diapositiva, LINEA_2, type PropsDiapositiva, Rotulo, TINTA, TINTA_3 } from "./piezas";

const cabecera = "border-b border-linea-2 pb-[0.6cqw] text-[0.98cqw] leading-[1.25] font-medium text-tinta-3";
const celda = "border-b border-linea py-[0.42cqw] text-[1.15cqw] tabular-nums";

// El corte de 3 mm es aproximado porque el diámetro se mide en una imagen con píxeles de 0,6 a 0,9 mm: `docs/cifras.md`.
const NOTA_DEL_CORTE = "El corte de 3 mm es aproximado: el diámetro se mide en una imagen con píxeles de 0,6 a 0,9 mm.";

// Las ramas finas visibles siguen al cociente más que las gruesas: la tabla de `docs/cifras.md`, leída de la validación con todos los sujetos.
const PUNTUACIONES_DE_VIA: { clave: string; nombre: string; modelo?: boolean; sola?: boolean }[] = [
  { clave: "via_longitud_mm", nombre: "Enfisema + longitud total", modelo: true },
  { clave: "via_longitud_fina_mm", nombre: "Enfisema + ramas de menos de 3 mm de luz" },
  { clave: "via gruesa", nombre: "Enfisema + ramas de 3 mm o más" },
  { clave: "via_extremos", nombre: "Enfisema + número de extremos del árbol" },
  { clave: "solo vía fina", nombre: "Solo las ramas de menos de 3 mm", sola: true },
  { clave: "solo vía gruesa", nombre: "Solo las ramas de 3 mm o más", sola: true },
  { clave: "solo enfisema", nombre: "Solo enfisema" },
];
// Sin los 3 sujetos que entran con el otro filtro del escáner (77): `docs/cifras.md` y `docs/figuras/validacion_anidada_sin_recuperados.json`.
export const SIN_RECUPERADOS = { todos: -0.73, controles: -0.33 };

export function ViasFinas({ cohorte }: PropsDiapositiva) {
  const { validacion } = cohorte;
  const filas = PUNTUACIONES_DE_VIA.flatMap((m) => {
    const datos = filaDeValidacion(cohorte, m.clave);
    return datos ? [{ ...m, datos }] : [];
  });
  const diferencia = comparacionDeVias(cohorte);
  // La mayor ganancia de cualquier candidato sobre el modelo, con su intervalo.
  const mejor = validacion?.resultados.filter((r) => r.mejora_rho !== undefined && r.medida.startsWith("via_")).sort((a, b) => (b.mejora_rho ?? 0) - (a.mejora_rho ?? 0))[0];

  return (
    <Diapositiva
      pregunta="¿Está la señal en las ramas finas visibles (<3 mm)?"
      titular="Las ramas visibles de menos de 3 mm siguen al FEV1/FVC más que las gruesas. Entre los sin obstrucción, no está demostrado."
      entradilla="No es la vía aérea pequeña: la de menos de 2 mm no se ve en la TC. Son las ramas finas que sí se ven."
    >
      {validacion && filas.length > 0 ? (
        <div className="grid min-h-0 flex-1 grid-cols-[1.55fr_1fr] items-start gap-[3.6cqw]">
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left align-bottom">
                <th className={cabecera}>Puntuación hecha con</th>
                <th className={`${cabecera} text-right`}>
                  Correlación con
                  <br />
                  el FEV1/FVC
                </th>
                <th className={`${cabecera} text-right`}>
                  Solo entre los {validacion.controles}
                  <br />
                  sin obstrucción
                </th>
                <th className={`${cabecera} pl-[1.6cqw] text-right`}>p</th>
              </tr>
            </thead>
            <tbody>
              {filas.map(({ clave, nombre, modelo, sola, datos }) => (
                <tr key={clave} className={modelo ? "bg-dano-suave font-semibold" : sola ? "font-semibold" : ""}>
                  <td className={`${celda} !py-[0.6cqw] ${modelo ? "pl-[0.8cqw]" : ""}`}>
                    {nombre}
                    {modelo && <span className="ml-[0.7cqw] text-[0.9cqw] font-medium text-dano-tinta">el modelo</span>}
                  </td>
                  <td className={`${celda} !py-[0.6cqw] text-right`}>{num(datos.rho_media, 2)}</td>
                  <td className={`${celda} !py-[0.6cqw] text-right`}>{num(datos.rho_controles_media, 2)}</td>
                  <td className={`${celda} !py-[0.6cqw] pl-[1.6cqw] text-right font-normal text-tinta-2`}>{pValor(datos.rho_controles_p)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex flex-col gap-[1cqw] text-[1.15cqw] leading-[1.4] text-tinta-2">
            {diferencia && (
              <>
                <p>
                  <strong className="font-semibold text-tinta">
                    En los {validacion.sujetos} sujetos, las ramas finas solas siguen al cociente más que las gruesas solas: diferencia de {num(diferencia.todos.diferencia, 2)}, intervalo del 95&nbsp;% de{" "}
                    {num(diferencia.todos.ic95[0], 2)} a {num(diferencia.todos.ic95[1], 2)}.
                  </strong>
                </p>
                <p>
                  Entre los sin obstrucción va en el mismo sentido y no está demostrada: {num(diferencia.controles.diferencia, 2)}, de {num(diferencia.controles.ic95[0], 2)} a{" "}
                  {num(diferencia.controles.ic95[1], 2)}.
                </p>
              </>
            )}
            {mejor?.mejora_rho !== undefined && mejor.mejora_rho_ic95 && (
              <p>
                Ninguna medida nueva mejora al modelo de forma demostrable: la mayor ganancia es de {num(mejor.mejora_rho, 2)}, de {num(mejor.mejora_rho_ic95[0], 2)} a {num(mejor.mejora_rho_ic95[1], 2)}. Se queda con
                la longitud total.
              </p>
            )}
            <p className="text-[1cqw] text-tinta-3">
              Cada sujeto se puntúa con un modelo que no lo vio: {validacion.vueltas} grupos, {validacion.repeticiones} repeticiones; la p, por permutación. {NOTA_DEL_CORTE} No podemos separar si hay menos ramas
              finas o si las mismas, más estrechas, se segmentan peor.
            </p>
          </div>
        </div>
      ) : (
        <p className="text-[1.4cqw] text-tinta-2">Pendiente: esta cohorte no trae la validación con todos los sujetos.</p>
      )}
    </Diapositiva>
  );
}

// Los subgrupos en los que se mira si la puntuación separa igual: los usa Generalización.
export const NOMBRE_ESTRATO: Record<string, (nivel: string) => string> = {
  kvp: (nivel) => `${nivel} kVp`,
  sexo: (nivel) => (nivel === "hombre" ? "Hombres" : "Mujeres"),
  fuma: (nivel) => (nivel === "fuma" ? "Fuman" : "No fuman"),
};
export const GRUPO_ESTRATO: Record<string, string> = { kvp: "Voltaje del escáner", sexo: "Sexo", fuma: "Tabaco" };

// La misma TC con los dos filtros del escáner: cada línea une el valor de un sujeto con uno y con otro.
// El porcentaje de enfisema se dibuja en logaritmo, como lo compara el modelo: a esta edad casi todos están pegados a cero.
function Pendientes({ cohorte, clave, titulo, acuerdo, fuerte }: { cohorte: Cohorte; clave: "laa950" | "puntuacion"; titulo: string; acuerdo: number; fuerte: boolean }) {
  const medida = clave === "laa950" ? (v: number) => Math.log10(Math.max(v, 0.01)) : (v: number) => v;
  const parejas = cohorte.sujetos.flatMap((s) => {
    const [antes, despues] = s.kernels[clave];
    return antes === null || despues === null ? [] : [{ id: s.id, antes: medida(antes), despues: medida(despues) }];
  });
  const valores = parejas.flatMap((p) => [p.antes, p.despues]);
  const [minimo, maximo] = [Math.min(...valores), Math.max(...valores)];
  const y = (valor: number) => 250 - ((valor - minimo) / (maximo - minimo || 1)) * 230;
  const color = fuerte ? TINTA : TINTA_3;
  return (
    <figure className="flex flex-col items-center">
      <figcaption className="text-[1.25cqw] font-semibold">{titulo}</figcaption>
      <svg viewBox="0 0 200 270" className="mt-[0.4cqw] h-[19cqw]" role="img" aria-label={`${titulo}: cada línea une el valor de un sujeto con un filtro y con el otro.`}>
        {[30, 170].map((x) => (
          <line key={x} x1={x} x2={x} y1={14} y2={258} stroke={LINEA_2} strokeWidth={1.5} />
        ))}
        {parejas.map((p) => (
          <line key={p.id} x1={30} x2={170} y1={y(p.antes)} y2={y(p.despues)} stroke={color} strokeWidth={1.2} opacity={0.55} />
        ))}
      </svg>
      <p className="flex w-[12cqw] justify-between text-[0.95cqw] text-tinta-3">
        <span>estándar</span>
        <span>otro filtro</span>
      </p>
      <p className={`mt-[0.4cqw] text-[3.6cqw] leading-none font-semibold tracking-[-0.045em] ${fuerte ? "" : "text-tinta-3"}`}>{num(acuerdo, 2)}</p>
      <p className="text-[1cqw] text-tinta-3">de acuerdo</p>
    </figure>
  );
}

export function Artefactos({ cohorte }: PropsDiapositiva) {
  const { controles_negativos: negativos, calidad_de_imagen, descontando, recuperados_de_la_otra_reconstruccion: recuperados, otra_reconstruccion } = cohorte.comprobaciones;
  const ruido = calidad_de_imagen?.find((c) => c.variable === "ruido_hu")?.puntuacion;
  const pixel = descontando?.find((d) => d.variable === "pixel_mm");
  const imc = descontando?.find((d) => d.variable === "imc");
  const principal = validacionDelModelo(cohorte);
  const lista = "mt-[0.6cqw] flex flex-col text-[1.12cqw]";
  const fila = "flex items-baseline justify-between gap-[1.4cqw] border-b border-linea py-[0.42cqw]";

  return (
    <Diapositiva
      pregunta="¿Puede ser un artefacto?"
      titular={`No sigue el voltaje, el ruido, el tamaño del píxel ni el IMC, y el acuerdo entre los dos filtros del escáner es ${num(principal?.icc ?? otra_reconstruccion.icc, 2)}.`}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[auto_1fr] items-start gap-[4cqw]">
        <div>
          <Rotulo>La misma TC con dos filtros del escáner</Rotulo>
          <div className="mt-[0.8cqw] flex gap-[2.6cqw]">
            <Pendientes cohorte={cohorte} clave="laa950" titulo="%LAA-950 clásico" acuerdo={acuerdoClasico(cohorte)} fuerte={false} />
            <Pendientes cohorte={cohorte} clave="puntuacion" titulo="Nuestra puntuación" acuerdo={otra_reconstruccion.icc} fuerte />
          </div>
        </div>

        <div>
          <Rotulo>Dentro de los controles, la puntuación no debe distinguir</Rotulo>
          <ul className={lista}>
            {[
              ["El sexo", `AUC ${num(negativos.sexo_auc, 2)}`],
              ["Si fuma", `AUC ${num(negativos.fuma_auc, 2)}`],
              ["El voltaje del escáner", `p = ${pValor(negativos.kvp_kruskal_p)}`],
              ...(ruido ? [["El ruido de la imagen (los 80 sujetos)", num(ruido.rho, 2)]] : []),
              ["El índice de masa corporal", `${num(negativos.imc.rho, 2)} (p = ${pValor(negativos.imc.p)})`],
            ].map(([nombre, cifra]) => (
              <li key={nombre} className={fila}>
                <span>{nombre}</span>
                <span className="font-semibold tabular-nums">{cifra}</span>
              </li>
            ))}
          </ul>
          <p className="mt-[0.5cqw] text-[0.98cqw] text-tinta-3">Un AUC cerca de 0,5 no distingue. Las correlaciones son con la puntuación.</p>

          <Rotulo className="mt-[1.4cqw]">La correlación con el FEV1/FVC se mantiene</Rotulo>
          <ul className={lista}>
            {[
              ...(pixel ? [["Descontando el tamaño del píxel", num(pixel.todos.rho, 2)]] : []),
              ...(imc ? [["Descontando el índice de masa corporal", num(imc.todos.rho, 2)]] : []),
              [`Sin los ${recuperados ?? 3} que entran con el otro filtro`, `${num(SIN_RECUPERADOS.todos, 2)}; sin obstrucción, ${num(SIN_RECUPERADOS.controles, 2)}`],
            ].map(([nombre, cifra]) => (
              <li key={nombre} className={fila}>
                <span>{nombre}</span>
                <span className="font-semibold whitespace-nowrap tabular-nums">{cifra}</span>
              </li>
            ))}
          </ul>
          <p className="mt-[0.5cqw] text-[0.98cqw] leading-[1.4] text-tinta-3">
            El modelo da {num(principal?.rho_media, 2)}. Eso cubre lo que hemos sabido buscar, no todo: los subgrupos son pequeños y los dos filtros salen de la misma adquisición.
          </p>
        </div>
      </div>
    </Diapositiva>
  );
}

// Por qué no un SHAP: cuatro puntos y, como gráfico, lo que cada medida pone en la puntuación de un sujeto.
export function PorQueNoShap({ cohorte }: PropsDiapositiva) {
  const sujeto = casoDeEntrada(cohorte);
  const { enfisema, via } = sujeto.z;
  const hayBarras = enfisema !== null && via !== null;
  // La puntuación es la media de las dos desviaciones: cada una pone la mitad de la suya. No hay nada que aproximar.
  const partes = hayBarras ? [{ nombre: "Enfisema", desviacion: enfisema, pone: enfisema / 2 }, { nombre: "Árbol bronquial", desviacion: via, pone: via / 2 }] : [];
  const suma = partes.reduce((total, parte) => total + parte.pone, 0);
  const tope = Math.max(...partes.map((parte) => Math.abs(parte.pone)), 0.5);
  const elegidos = cohorte.validacion?.elegido_en_cada_vuelta;
  const vueltas = elegidos ? Object.values(elegidos).reduce((total, n) => total + n, 0) : 0;
  const todas = modeloConTodas(cohorte.complejidad);
  const puntos = [
    [
      "Ninguna red entrenada por nosotros.",
      todas
        ? `La segmentación es de una red ya entrenada. Con ${cohorte.comprobaciones.sujetos} personas, aprender los pesos de todas las medidas ya baja la AUC a ${num(todas.auc, 2)} y el acuerdo entre filtros a ${num(todas.icc, 2)}.`
        : "La segmentación es de una red ya entrenada.",
    ],
    ["Un SHAP dice en qué se fija un modelo para acertar una etiqueta.", "No dice qué le pasa al pulmón."],
    ["Nuestra puntuación son dos medidas con el mismo peso.", "Cuánto pone cada una en cada paciente se ve directamente."],
    [
      `Con ${cohorte.comprobaciones.sujetos} sujetos y medidas que se parecen entre sí, el reparto de importancia cambia de un ajuste a otro.`,
      elegidos ? `En nuestra validación, la medida de vía aérea elegida cambió: en ${vueltas} vueltas ganaron ${Object.keys(elegidos).length} combinaciones distintas.` : "",
    ],
    ["Si entre las variables está la espirometría, la barra más larga es el FEV1/FVC.", "Es la definición de la etiqueta."],
  ];

  return (
    <Diapositiva pregunta="¿Por qué no deep learning o un SHAP?" titular="Con 80 personas, aprender los pesos ya es inestable. El nuestro se explica solo: lo que pone cada medida es exacto.">
      <div className="grid min-h-0 flex-1 grid-cols-[1.15fr_1fr] items-start gap-[4cqw]">
        <ol className="flex flex-col gap-[1cqw]">
          {puntos.map(([afirma, sigue], i) => (
            <li key={afirma} className="grid grid-cols-[2.2cqw_1fr] gap-[0.9cqw] text-[1.25cqw] leading-[1.4]">
              <span className="grid size-[2.2cqw] place-items-center rounded-full bg-tinta text-[1.05cqw] font-semibold text-white">{i + 1}</span>
              <p>
                <strong className="font-semibold">{afirma}</strong> <span className="text-tinta-2">{sigue}</span>
              </p>
            </li>
          ))}
        </ol>

        <div className="rounded-[1.1cqw] border border-linea bg-white p-[1.8cqw]">
          <Rotulo>
            Un sujeto{cohorte.aviso ? " simulado" : ""}: {sujeto.id}
          </Rotulo>
          {hayBarras ? (
            <>
              <p className="mt-[0.6cqw] text-[1.4cqw] leading-[1.25] font-semibold tracking-[-0.02em]">Qué pone cada medida en su puntuación de {num(suma, 2, true)}</p>
              <div className="mt-[1.3cqw] flex flex-col gap-[1.2cqw]">
                {partes.map((parte) => (
                  <div key={parte.nombre}>
                    <p className="flex items-baseline justify-between text-[1.15cqw]">
                      <span>
                        {parte.nombre} <span className="text-tinta-3">· {num(parte.desviacion, 2, true)} desviaciones</span>
                      </span>
                      <strong className="text-[1.8cqw] leading-none font-semibold tracking-[-0.03em] tabular-nums">{num(parte.pone, 2, true)}</strong>
                    </p>
                    <div className="relative mt-[0.5cqw] h-[1.4cqw] rounded-full bg-fondo">
                      <span className="absolute inset-y-[-0.25cqw] left-1/2 w-px bg-tinta-3" />
                      <span
                        className={`absolute inset-y-0 rounded-full bg-tinta ${parte.pone < 0 ? "right-1/2" : "left-1/2"}`}
                        style={{ width: `max(${(Math.abs(parte.pone) / tope) * 48}%, 0.3cqw)` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-[1.3cqw] border-t border-linea pt-[1cqw] text-[1.1cqw] leading-[1.4] text-tinta-2">
                {partes.map((parte) => num(parte.pone, 2, true)).join(" y ")} suman {num(suma, 2, true)}. La puntuación es la media de las dos desviaciones: cada medida pone la mitad de la suya.
              </p>
            </>
          ) : (
            <p className="mt-[0.8cqw] text-[1.2cqw] text-tinta-2">Este sujeto no tiene las dos desviaciones: no hay barras que dibujar.</p>
          )}
        </div>
      </div>
    </Diapositiva>
  );
}

// Datos y método: el embudo de sujetos y los seis pasos, por si preguntan de dónde sale cada cosa.
// Los 86 sujetos del reto: `docs/cifras.md`, "Datos". Los 62 y los 15, bloque 3. El resto sale de la cohorte.
const SUJETOS_DEL_RETO = 86;

export function DatosYMetodo({ cohorte }: PropsDiapositiva) {
  const { sujetos, epoc, controles, recuperados_de_la_otra_reconstruccion: recuperados } = cohorte.comprobaciones;
  const reserva = cohorte.reserva?.sujetos ?? RESERVA_DE_LA_PRIMERA_PRUEBA;
  const ajuste = cohorte.congelado?.sujetos_de_ajuste ?? AJUSTE_DEL_PRIMER_MODELO;
  const ancho = (n: number) => `${(n / SUJETOS_DEL_RETO) * 100}%`;
  const barra = "flex h-[3.6cqw] items-center gap-[0.9cqw] rounded-[0.7cqw] px-[1.1cqw]";
  const cifra = "text-[2.2cqw] font-semibold tracking-[-0.04em] tabular-nums";
  const pasos = [
    { nombre: "Segmentar", texto: "Una red ya entrenada separa los lóbulos y el árbol bronquial." },
    { nombre: "Medir", texto: "Cuánto enfisema hay y cuánto árbol bronquial se ve." },
    { nombre: "Comparar", texto: "Con lo esperado para su edad, sexo, talla y tabaco." },
    { nombre: "Puntuación", texto: "Cuánto se aparta de lo esperado. No usa su espirometría." },
    { nombre: "Línea en la TC", texto: `La que mejor separa a quien tiene obstrucción: ${num(cohorte.umbral_dano, 2)}.` },
    { nombre: "Clase", texto: "Con la espirometría: control, posible pre-EPOC o EPOC." },
  ];

  return (
    <Diapositiva
      pregunta="¿De dónde salen los datos y qué hace cada paso?"
      titular={
        <>
          {sujetos} personas con TC. <span className="text-tinta-3">Ninguna red entrenada por nosotros.</span>
        </>
      }
      entradilla={`De 35 a 50 años, fumadores o exfumadores: ${epoc} con obstrucción y ${controles} sin ella.`}
    >
      <div className="grid min-h-0 flex-1 grid-cols-[1fr_1fr] items-start gap-[5cqw]">
        <div className="flex flex-col gap-[0.7cqw]">
          <Rotulo>Los datos</Rotulo>
          <div className={`${barra} bg-fondo`} style={{ width: ancho(SUJETOS_DEL_RETO) }}>
            <span className={cifra}>{SUJETOS_DEL_RETO}</span>
            <span className="text-[1.15cqw] text-tinta-2">sujetos en el reto</span>
          </div>
          <div className={`${barra} bg-fondo`} style={{ width: ancho(sujetos) }}>
            <span className={cifra}>{sujetos}</span>
            <span className="text-[1.15cqw] text-tinta-2">con una TC de tórax utilizable</span>
          </div>

          <Rotulo className="mt-[1.1cqw]">Primero: una prueba con sujetos apartados</Rotulo>
          <div className="grid gap-x-[0.5cqw] gap-y-[0.3cqw]" style={{ width: ancho(ajuste + reserva), gridTemplateColumns: `${ajuste}fr ${reserva}fr` }}>
            <div className={`${barra} bg-tinta text-white`}>
              <span className={cifra}>{ajuste}</span>
              <span className="text-[1.15cqw] text-white/80">para ajustar el primer modelo</span>
            </div>
            <div className={`${barra} justify-center border-[0.16cqw] border-dashed border-tinta !px-0`}>
              <span className={cifra}>{reserva}</span>
            </div>
            <span />
            <span className="text-center text-[0.95cqw] text-tinta-3">apartados</span>
          </div>

          <Rotulo className="mt-[0.6cqw]">Después: el modelo final, con todos</Rotulo>
          <div className={`${barra} bg-tinta text-white`} style={{ width: ancho(sujetos) }}>
            <span className={cifra}>{sujetos}</span>
            <span className="text-[1.15cqw] text-white/80">cada persona, con un modelo que no la vio</span>
          </div>
          {recuperados ? (
            <p className="text-[0.95cqw] text-tinta-3">
              {recuperados} de los {sujetos} entran con la serie del otro filtro del escáner: su serie estándar estaba incompleta.
            </p>
          ) : null}
        </div>

        <div>
          <Rotulo>El método</Rotulo>
          <ol className="mt-[0.5cqw]">
            {pasos.map((paso, i) => (
              <li key={paso.nombre} className="grid grid-cols-[1.9cqw_10cqw_1fr] items-baseline gap-x-[0.8cqw] border-b border-linea py-[0.72cqw] last:border-0">
                <span className="font-mono text-[1cqw] text-tinta-3">{i + 1}</span>
                <span className="text-[1.3cqw] font-semibold tracking-[-0.02em]">{paso.nombre}</span>
                <span className="text-[1.15cqw] leading-[1.3] text-tinta-2">{paso.texto}</span>
              </li>
            ))}
          </ol>
          <p className="mt-[1.1cqw] rounded-[0.9cqw] bg-fondo px-[1.2cqw] py-[0.9cqw] text-[1.15cqw] leading-[1.35]">
            <strong className="font-semibold">Ninguna red entrenada por nosotros.</strong> Una red de segmentación ya entrenada, dos medidas, una regresión y un umbral.
          </p>
        </div>
      </div>
    </Diapositiva>
  );
}

// Lo que pide el reto: sus tres cajas y qué responde MAPS a cada una.
const PRE_EPOC = <span className="whitespace-nowrap">pre-EPOC</span>;

export function LoQuePideElReto({ cohorte }: PropsDiapositiva) {
  const { por_clase: clases, por_medida } = cohorte.comprobaciones;
  const correlacion = correlacionPrincipal(cohorte);
  const pasos: { nombre: string; pide: React.ReactNode; responde: React.ReactNode; estado: string; hecho: boolean }[] = [
    {
      nombre: "Cuantificar la TC",
      pide: "Porcentaje de enfisema, grosor de pared bronquial, disanapsia y rasgos nuevos.",
      responde: `${por_medida.length} medidas automáticas por TC. Dos forman la puntuación de daño.`,
      estado: "Hecho",
      hecho: true,
    },
    {
      nombre: "Asociar y clasificar",
      pide: <>Relacionarlas con la obstrucción, el tabaco y la clínica. Separar control, {PRE_EPOC} y EPOC.</>,
      responde: (
        <>
          La puntuación sigue al FEV1/FVC (correlación de {num(correlacion?.rho, 2)}). Una regla da {clases.control.n} controles, {clases["pre-EPOC"].n} posibles {PRE_EPOC} y {clases.EPOC.n} EPOC.
        </>
      ),
      estado: "Hecho",
      hecho: true,
    },
    {
      nombre: "Conectar con lo molecular",
      pide: "Un flujo que lleve de la TC y la clínica a los datos moleculares.",
      responde: "No hay datos moleculares en la carpeta del reto. Miramos el FENO, el único biomarcador de la tabla, y no se asocia.",
      estado: "Sin datos moleculares",
      hecho: false,
    },
  ];

  return (
    <Diapositiva
      pregunta="¿Qué pedía el reto y qué responde MAPS?"
      titular={
        <>
          Lo que pide el reto: tres pasos. <span className="text-tinta-3">Dos están hechos. Para el tercero no hay datos.</span>
        </>
      }
    >
      <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-stretch gap-[1cqw]">
        {pasos.map((paso, i) => (
          <div key={paso.nombre} className="contents">
            {i > 0 && <span className="self-center text-[2cqw] text-tinta-3">→</span>}
            <div className="flex flex-col rounded-[1.1cqw] border border-linea bg-white p-[1.7cqw]">
              <p className="flex items-center gap-[0.8cqw] text-[1.6cqw] leading-[1.1] font-semibold tracking-[-0.02em] whitespace-nowrap">
                <span className="grid size-[2.3cqw] shrink-0 place-items-center rounded-full bg-tinta text-[1.15cqw] text-white">{i + 1}</span>
                {paso.nombre}
              </p>
              <Rotulo className="mt-[1.6cqw]">El reto pide</Rotulo>
              <p className="mt-[0.4cqw] text-[1.2cqw] leading-[1.35] text-tinta-2">{paso.pide}</p>
              <Rotulo className="mt-[1.4cqw]">MAPS responde</Rotulo>
              <p className="mt-[0.4cqw] mb-[1.6cqw] text-[1.2cqw] leading-[1.35]">{paso.responde}</p>
              <p className={`mt-auto self-start rounded-full border px-[1cqw] py-[0.35cqw] text-[1.05cqw] font-medium ${paso.hecho ? "border-tinta bg-tinta text-white" : "border-dashed border-tinta-3 text-tinta-2"}`}>{paso.estado}</p>
            </div>
          </div>
        ))}
      </div>
    </Diapositiva>
  );
}
