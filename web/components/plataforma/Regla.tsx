import { num } from "@/lib/formato";

// La regla de desviación va de −3 a +6: lo esperado queda a la izquierda y las puntuaciones altas tienen sitio.
const Z_MINIMO = -3;
const Z_MAXIMO = 6;
const enRegla = (z: number) => `${((Math.min(Math.max(z, Z_MINIMO), Z_MAXIMO) - Z_MINIMO) / (Z_MAXIMO - Z_MINIMO)) * 100}%`;

/**
 * Dónde cae una desviación. La marca fina es el 0: lo esperado para esa persona.
 * Solo la puntuación de daño tiene umbral: por encima, la TC se parece a la de la EPOC; por debajo, no.
 * Una medida suelta no decide nada, así que su punto nunca cambia de color.
 */
export function Regla({ z, umbral, escala = false }: { z: number | null; umbral?: number; escala?: boolean }) {
  const porEncima = umbral !== undefined && z !== null && z >= umbral;
  return (
    <span className="block">
      {umbral !== undefined && (
        <span className="relative block h-4 text-[11px] font-medium whitespace-nowrap text-dano-tinta">
          <span className="absolute pl-1" style={{ left: enRegla(umbral) }}>
            umbral: {num(umbral, 2)}
          </span>
        </span>
      )}
      <span className="relative block h-6">
        <span className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-fondo" />
        {umbral !== undefined && <span className="absolute top-1/2 right-0 h-1.5 -translate-y-1/2 rounded-r-full bg-dano/20" style={{ left: enRegla(umbral) }} />}
        <span className="absolute top-1 bottom-1 w-px bg-tinta-3" style={{ left: enRegla(0) }} />
        {umbral !== undefined && <span className="absolute top-0 bottom-0 w-0.5 -translate-x-1/2 rounded-full bg-dano" style={{ left: enRegla(umbral) }} />}
        {z !== null && Number.isFinite(z) && (
          <span className={`absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white ${porEncima ? "bg-dano" : "bg-tinta"}`} style={{ left: enRegla(z) }} />
        )}
      </span>
      {escala && (
        <span className="relative block h-4 text-[11px] text-tinta-3">
          <span className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: enRegla(0) }}>
            0: lo esperado
          </span>
          {[3, 6].map((marca) => (
            <span key={marca} className="absolute -translate-x-full" style={{ left: enRegla(marca) }}>
              {num(marca, 0, true)}
            </span>
          ))}
          <span className="absolute left-0">{num(Z_MINIMO, 0)}</span>
        </span>
      )}
    </span>
  );
}
