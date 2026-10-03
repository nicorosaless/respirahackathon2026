import { type Clase, type NivelTC, NOMBRE_CLASE, NOMBRE_NIVEL } from "@/lib/cohorte";

export const COLOR_CLASE: Record<Clase, string> = {
  control: "var(--color-control)",
  "pre-EPOC": "var(--color-dano)",
  EPOC: "var(--color-tinta)",
};

export function Marca({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-[0.5em] font-semibold tracking-tight ${className}`}>
      <span aria-hidden className="inline-block size-[0.72em] rounded-[0.2em] bg-dano" />
      MAPS
    </span>
  );
}

/** La clase de un sujeto. La intermedia es "posible pre-EPOC": sin obstrucción y con la TC parecida a la de la EPOC. */
export function EtiquetaClase({ clase, className = "" }: { clase: Clase; className?: string }) {
  const estilo =
    clase === "EPOC"
      ? "bg-tinta text-white border-tinta"
      : clase === "pre-EPOC"
        ? "bg-dano-suave text-dano-tinta border-dano/40"
        : "bg-white text-tinta-2 border-linea-2";
  return <span className={`inline-flex h-6 items-center rounded-full border px-2.5 text-xs font-medium whitespace-nowrap ${estilo} ${className}`}>{NOMBRE_CLASE[clase]}</span>;
}

/**
 * El nivel de la TC de un sujeto, en tres bandas. El naranja empieza donde la TC se parece a la de la EPOC
 * y se llena cuando pasa del límite de lo normal.
 */
export function EtiquetaNivel({ nivel, className = "" }: { nivel: NivelTC | null; className?: string }) {
  if (nivel === null) return <span className={`inline-flex items-center rounded-full border border-dashed border-tinta-3 px-2.5 text-tinta-2 ${className}`}>sin puntuación</span>;
  const estilo = nivel === "alta" ? "bg-dano text-white border-dano" : nivel === "intermedia" ? "bg-dano-suave text-dano-tinta border-dano/40" : "bg-white text-tinta border-linea-2";
  return <span className={`inline-flex items-center rounded-full border px-2.5 whitespace-nowrap ${estilo} ${className}`}>{NOMBRE_NIVEL[nivel]}</span>;
}
