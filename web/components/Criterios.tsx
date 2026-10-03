import type { Reserva } from "@/lib/cohorte";
import { criteriosDeReserva } from "@/lib/inferencia";

/**
 * La prueba en reserva, pregunta a pregunta: el resultado, lo que se escribió antes de mirar y si se cumple.
 * Se mide en em: la presentación y la plataforma la dibujan a su tamaño con `text-[…]`.
 */
export function Criterios({ reserva, className = "" }: { reserva: Reserva; className?: string }) {
  const filas = criteriosDeReserva(reserva);
  const hayCriterios = filas.some((fila) => fila.cumple !== null);
  const celda = "border-b border-linea py-[0.5em] align-baseline";
  return (
    <table className={`w-full table-fixed border-collapse ${className}`}>
      <colgroup>
        <col className={hayCriterios ? "w-[30%]" : "w-[45%]"} />
        <col />
        {hayCriterios && <col className="w-[33%]" />}
      </colgroup>
      <thead>
        <tr className="text-left text-[0.82em] text-tinta-3">
          <th className="border-b border-linea-2 pb-[0.4em] font-medium">Qué se pregunta</th>
          <th className="border-b border-linea-2 pb-[0.4em] pl-[1em] font-medium">En la reserva</th>
          {hayCriterios && <th className="border-b border-linea-2 pb-[0.4em] pl-[1em] font-medium">Fijado antes de mirar</th>}
        </tr>
      </thead>
      <tbody>
        {filas.map((fila) => (
          <tr key={fila.pregunta}>
            <td className={`${celda} text-tinta-2`}>{fila.pregunta}</td>
            <td className={`${celda} pl-[1em] font-semibold tabular-nums`}>{fila.resultado}</td>
            {hayCriterios && (
              <td className={`${celda} pl-[1em]`}>
                {fila.esperado === null ? (
                  <span className="text-tinta-3">sin criterio</span>
                ) : (
                  <span className="flex flex-wrap items-baseline justify-between gap-x-[0.6em] gap-y-[0.2em]">
                    <span className="text-tinta-2">{fila.esperado}</span>
                    {fila.cumple !== null && (
                      <span
                        className={`rounded-full px-[0.7em] py-[0.1em] text-[0.82em] font-medium whitespace-nowrap ${
                          !fila.cumple ? "border border-tinta text-tinta" : fila.porPoco ? "border border-dashed border-tinta-3 text-tinta-2" : "bg-tinta text-white"
                        }`}
                      >
                        {!fila.cumple ? "no cumple" : fila.porPoco ? "cumple por poco" : "cumple"}
                      </span>
                    )}
                  </span>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
