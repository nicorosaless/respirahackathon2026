/** La subcarpeta en la que se publica la web (por ejemplo `/maps`), o vacío si va en la raíz. La fija `next.config.ts`. */
export const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Una ruta de `public/` con la subcarpeta delante: `fetch` e `<img>` no la añaden solos, a diferencia de `Link`. */
export const publica = (ruta: string) => `${BASE}${ruta}`;
