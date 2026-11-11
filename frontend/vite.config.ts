import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Entrega 2: proxy de desarrollo. AGENTFLOW_API_KEY vive SOLO aquí (código de Node, nunca enviado al navegador):
// `loadEnv` la lee del `.env` de la raíz del repo (el mismo que usa FastAPI) dentro de este archivo de configuración,
// que nunca se incluye en el bundle. El cliente React llama a rutas relativas ("/api/v1/...") del propio origen
// 5173; este proxy las reenvía a FastAPI añadiendo la cabecera Authorization. El navegador no ve la clave en
// ningún momento: ni en el código fuente, ni en el bundle construido, ni en las peticiones que emite.
export default defineConfig(({ mode }) => {
  const raiz = `${import.meta.dirname}/..`;
  const env = loadEnv(mode, raiz, ""); // prefijo vacío: lee todas las variables del .env de la raíz
  const clave = env.AGENTFLOW_API_KEY;
  const destino = env.AGENTFLOW_API_URL || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": {
          target: destino,
          changeOrigin: true,
          rewrite: (ruta) => ruta.replace(/^\/api/, ""),
          configure(proxy) {
            proxy.on("proxyReq", (proxyReq) => {
              if (clave) proxyReq.setHeader("Authorization", `Bearer ${clave}`);
            });
          },
        },
      },
    },
  };
});
