import { defineConfig } from "vitest/config";

// `pool: "vmThreads"` es necesario en este entorno: con el pool por defecto ("threads"/"forks"), vitest 5.1.0
// pierde el contexto de "current suite" en este sandbox (falla con o sin archivos, incluso una prueba trivial
// sin imports) y vmThreads lo resuelve de forma estable. Si al actualizar vitest deja de hacer falta, se puede
// quitar; mientras tanto es necesario para que `npm test` funcione aquí.
export default defineConfig({ test: { environment: "node", pool: "vmThreads" } });
