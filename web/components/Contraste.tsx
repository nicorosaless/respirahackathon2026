import type { Contraste as Casillas } from "@/lib/inferencia";

function Casilla({ cuantos, coincide }: { cuantos: number; coincide: boolean }) {
  return (
    <td className={`rounded-[0.6em] border text-center align-middle ${coincide ? "border-tinta bg-white font-semibold" : "border-linea-2 bg-transparent text-tinta-3"}`}>
      <span className="block py-[0.28em] text-[2.1em] leading-none tracking-tight tabular-nums">{cuantos}</span>
    </td>
  );
}

/**
 * Si la TC se parece a la de la EPOC frente a si la espirometría encuentra obstrucción. En la diagonal marcada, las dos pruebas dicen lo mismo.
 * Se mide en em: la presentación y la plataforma la dibujan a su tamaño con `text-[…]`.
 */
export function Contraste({ casillas, className = "" }: { casillas: Casillas; className?: string }) {
  return (
    <table className={`border-separate border-spacing-[0.45em] ${className}`}>
      <thead>
        <tr className="text-[0.82em] font-medium text-tinta-2">
          <td />
          <th className="px-[0.6em] pb-[0.1em] font-medium">Con obstrucción</th>
          <th className="px-[0.6em] pb-[0.1em] font-medium">Sin obstrucción</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th className="pr-[0.6em] text-right text-[0.82em] leading-tight font-medium whitespace-nowrap text-dano-tinta">
            TC parecida
            <br />a la de la EPOC
          </th>
          <Casilla cuantos={casillas.danoConObstruccion} coincide />
          <Casilla cuantos={casillas.danoSinObstruccion} coincide={false} />
        </tr>
        <tr>
          <th className="pr-[0.6em] text-right text-[0.82em] leading-tight font-medium whitespace-nowrap text-tinta-2">TC no parecida</th>
          <Casilla cuantos={casillas.sinDanoConObstruccion} coincide={false} />
          <Casilla cuantos={casillas.sinDanoSinObstruccion} coincide />
        </tr>
      </tbody>
    </table>
  );
}
