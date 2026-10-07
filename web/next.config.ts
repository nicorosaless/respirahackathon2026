import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Estático: `out/` se sirve con cualquier servidor de ficheros, sin Node.
  output: "export",
  // `plataforma/index.html` en vez de `plataforma.html`: cualquier servidor de ficheros lo sirve.
  trailingSlash: true,
  devIndicators: false,
  // Para publicarla en una subcarpeta: `NEXT_PUBLIC_BASE_PATH=/maps/slides pnpm build`.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || undefined,
};

export default nextConfig;
